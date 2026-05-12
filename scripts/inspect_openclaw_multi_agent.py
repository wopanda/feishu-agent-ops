#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

SEV_ORDER = {"P1": 1, "P2": 2, "P3": 3, "INFO": 4}


def expand(p: str) -> str:
    return os.path.expanduser(p or "")


def add_issue(issues, severity, code, title, evidence, fix):
    issues.append({
        "severity": severity,
        "code": code,
        "title": title,
        "evidence": evidence,
        "fix": fix,
    })


def main():
    ap = argparse.ArgumentParser(description="Inspect OpenClaw multi-agent / Feishu config for root causes.")
    ap.add_argument("--config", required=True, help="Path to openclaw.json")
    ap.add_argument("--json", action="store_true", help="Output as JSON")
    args = ap.parse_args()

    config_path = Path(expand(args.config)).resolve()
    obj = json.loads(config_path.read_text(encoding='utf-8'))

    agents = ((obj.get("agents") or {}).get("list") or [])
    bindings = obj.get("bindings") or []
    session = obj.get("session") or {}
    dm_scope = session.get("dmScope")
    fei = ((obj.get("channels") or {}).get("feishu") or {})
    accounts = fei.get("accounts") or {}
    top_app_id = fei.get("appId")
    top_app_secret = fei.get("appSecret")

    nondefault_accounts = {k: v for k, v in accounts.items() if k != "default"}
    feishu_bindings = []
    binding_accounts = []
    binding_agents = []
    for b in bindings:
        m = b.get("match") or {}
        if m.get("channel") == "feishu":
            feishu_bindings.append(b)
            if "accountId" in m:
                binding_accounts.append(m.get("accountId"))
            if b.get("agentId"):
                binding_agents.append(b.get("agentId"))

    issues = []

    if dm_scope != "per-account-channel-peer":
        add_issue(
            issues,
            "P1",
            "dm_scope_not_account_isolated",
            "多账号飞书场景未使用最稳妥的会话隔离粒度",
            f"current session.dmScope = {dm_scope!r}",
            "多账号多 Agent 场景优先改为 per-account-channel-peer；变更前先确认是否会影响既有会话连续性。",
        )

    missing_binding_accounts = sorted([k for k in nondefault_accounts.keys() if k not in binding_accounts])
    if missing_binding_accounts:
        add_issue(
            issues,
            "P1",
            "accounts_without_binding",
            "存在飞书账号但没有形成 routing 闭环",
            f"accounts without bindings = {missing_binding_accounts}",
            "为每个实际启用的 accountId 补齐对应 binding，确保 accountId -> agentId 闭环。",
        )

    missing_agent_bindings = sorted([a.get("id") for a in agents if a.get("id") not in binding_agents])
    if missing_agent_bindings:
        add_issue(
            issues,
            "P2",
            "agents_without_feishu_binding",
            "存在 Agent，但未看到对应的 Feishu 绑定",
            f"agents without feishu binding = {missing_agent_bindings}",
            "确认这些 Agent 是否本来就不接 Feishu；若需要接入，则补绑定。",
        )

    dangling_binding_accounts = sorted([acc for acc in binding_accounts if acc not in nondefault_accounts and acc != "default" and acc is not None])
    if dangling_binding_accounts:
        add_issue(
            issues,
            "P1",
            "bindings_to_missing_accounts",
            "存在 binding 指向不存在的 accountId",
            f"dangling binding accountIds = {dangling_binding_accounts}",
            "移除悬空 binding 或补齐对应 account 配置。",
        )

    if "default" in accounts and not top_app_id and not top_app_secret:
        default_cfg = accounts.get("default") or {}
        if not default_cfg.get("appId") and not default_cfg.get("appSecret"):
            add_issue(
                issues,
                "P3",
                "empty_default_account",
                "default 飞书账号占位存在，但未配置可用凭据",
                "accounts.default exists, but top-level appId/appSecret and default account credentials are all empty",
                "若不需要 default 路径，可在文档中明确其仅为占位；若需要 default，需补齐凭据。",
            )

    for agent in agents:
        aid = agent.get("id")
        ws = expand(agent.get("workspace") or "")
        ad = expand(agent.get("agentDir") or "")
        if ws and not Path(ws).exists():
            add_issue(
                issues,
                "P2",
                f"workspace_missing:{aid}",
                f"Agent {aid} 的 workspace 不存在",
                ws,
                "补建 workspace 目录，或修正 workspace 路径。",
            )
        if ad and not Path(ad).exists():
            add_issue(
                issues,
                "P2",
                f"agentdir_missing:{aid}",
                f"Agent {aid} 的 agentDir 不存在",
                ad,
                "补建 agentDir 目录，或修正 agentDir 路径。",
            )

    report = {
        "config": str(config_path),
        "summary": {
            "agents": len(agents),
            "feishu_accounts_total": len(accounts),
            "feishu_accounts_nondefault": len(nondefault_accounts),
            "feishu_bindings": len(feishu_bindings),
            "session_dmScope": dm_scope,
        },
        "issues": sorted(issues, key=lambda x: (SEV_ORDER[x["severity"]], x["code"])),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("OpenClaw Multi-Agent Root Cause Report")
    print(f"config: {report['config']}")
    print()
    print("Summary")
    for k, v in report["summary"].items():
        print(f"- {k}: {v}")
    print()
    if not report["issues"]:
        print("No obvious root-cause-level issues found from config-only inspection.")
        return
    print("Issues")
    for i, issue in enumerate(report["issues"], 1):
        print(f"{i}. [{issue['severity']}] {issue['title']}")
        print(f"   code: {issue['code']}")
        print(f"   evidence: {issue['evidence']}")
        print(f"   suggested fix: {issue['fix']}")
        print()


if __name__ == "__main__":
    main()
