#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

SEV_CRITICAL = "CRITICAL"
SEV_HIGH = "HIGH"
SEV_MED = "MEDIUM"
SEV_LOW = "LOW"
SEV_INFO = "INFO"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def add_issue(issues, sev, code, message, evidence=None, fix=None):
    issues.append(
        {
            "severity": sev,
            "code": code,
            "message": message,
            "evidence": evidence or {},
            "suggested_fix": fix or "",
        }
    )


def has_credentials(v):
    v = v or {}
    return bool(v.get("appId")) and bool(v.get("appSecret"))


def detect_plugin_override(openclaw_home: Path):
    found = []
    for pid in ["feishu", "qqbot"]:
        p = openclaw_home / "extensions" / pid
        if p.exists():
            found.append(str(p))
    return found


def analyze(cfg, config_path: Path):
    issues = []

    agents = ((cfg.get("agents") or {}).get("list") or [])
    agent_ids = [a.get("id") for a in agents if a.get("id")]
    agent_id_set = set(agent_ids)

    fei = ((cfg.get("channels") or {}).get("feishu") or {})
    accounts = fei.get("accounts") or {}
    account_keys = list(accounts.keys())

    feishu_bindings = []
    all_bindings = cfg.get("bindings") or []
    for b in all_bindings:
        m = b.get("match") or {}
        if m.get("channel") == "feishu":
            feishu_bindings.append(b)

    binding_account_ids = []
    for b in feishu_bindings:
        m = b.get("match") or {}
        if "accountId" in m:
            binding_account_ids.append(m.get("accountId"))

    session_scope = (cfg.get("session") or {}).get("dmScope")

    # 1) dmScope for multi account
    valid_nondefault_accounts = [k for k, v in accounts.items() if k != "default" and has_credentials(v)]
    if len(valid_nondefault_accounts) >= 2:
        if session_scope != "per-account-channel-peer":
            add_issue(
                issues,
                SEV_HIGH,
                "DM_SCOPE_NOT_ISOLATED",
                "多账号飞书场景下 dmScope 不是 per-account-channel-peer，可能导致会话串扰。",
                {
                    "current": session_scope,
                    "recommended": "per-account-channel-peer",
                    "accounts": valid_nondefault_accounts,
                },
                "将 session.dmScope 调整为 per-account-channel-peer（变更前先确认会话连续性影响）。",
            )

    # 2) accounts vs bindings closure
    missing_binding_accounts = [k for k in valid_nondefault_accounts if k not in binding_account_ids]
    if missing_binding_accounts:
        add_issue(
            issues,
            SEV_HIGH,
            "ACCOUNT_WITHOUT_BINDING",
            "存在已配置凭据的 Feishu 账号没有对应 binding。",
            {
                "accounts_with_credentials": valid_nondefault_accounts,
                "binding_account_ids": binding_account_ids,
                "missing": missing_binding_accounts,
            },
            "为缺失账号补齐 bindings（match.channel=feishu + match.accountId）。",
        )

    # 3) binding refers to missing account
    for b in feishu_bindings:
        m = b.get("match") or {}
        aid = m.get("accountId")
        if aid and aid not in accounts:
            add_issue(
                issues,
                SEV_HIGH,
                "BINDING_ACCOUNT_MISSING",
                "binding 指向了不存在的 accountId。",
                {"binding": b},
                "修正 binding.accountId 或补充该账号配置。",
            )

    # 4) binding refers to missing agent
    for b in feishu_bindings:
        agent_id = b.get("agentId")
        if agent_id and agent_id not in agent_id_set:
            add_issue(
                issues,
                SEV_HIGH,
                "BINDING_AGENT_MISSING",
                "binding 指向了不存在的 agentId。",
                {"binding": b, "known_agents": agent_ids},
                "修正 binding.agentId 或新增对应 agent。",
            )

    # 5) account default placeholder (informational)
    if "default" in accounts and not has_credentials(accounts.get("default")):
        add_issue(
            issues,
            SEV_INFO,
            "DEFAULT_PLACEHOLDER_ACCOUNT",
            "检测到 accounts.default 是占位账号（无 appId/appSecret）。",
            {"default_account": accounts.get("default")},
            "若无实际用途可保留占位；若造成认知混乱可在文档中明确其用途。",
        )

    # 6) duplicate plugin override risk (filesystem heuristic)
    openclaw_home = config_path.parent
    overrides = detect_plugin_override(openclaw_home)
    if overrides:
        add_issue(
            issues,
            SEV_MED,
            "PLUGIN_OVERRIDE_RISK",
            "检测到全局 extensions 目录下存在与内置同名插件，可能触发插件覆盖告警。",
            {"paths": overrides},
            "统一插件来源（保留一种来源），并在变更后复测 channels/status。",
        )

    # 7) workspace/agentDir quick check
    missing_workspace = []
    missing_agent_dir = []
    for a in agents:
        aid = a.get("id")
        ws = a.get("workspace")
        ad = a.get("agentDir")
        if ws:
            ws_path = Path(os.path.expanduser(ws))
            if not ws_path.exists():
                missing_workspace.append({"agentId": aid, "workspace": ws})
        if ad:
            ad_path = Path(os.path.expanduser(ad))
            if not ad_path.exists():
                missing_agent_dir.append({"agentId": aid, "agentDir": ad})

    if missing_workspace:
        add_issue(
            issues,
            SEV_MED,
            "MISSING_WORKSPACE",
            "存在 agent 缺少 workspace 目录。",
            {"missing": missing_workspace},
            "按 agent 配置创建 workspace 目录，并复测路由行为。",
        )

    if missing_agent_dir:
        add_issue(
            issues,
            SEV_MED,
            "MISSING_AGENT_DIR",
            "存在 agent 缺少 agentDir 目录。",
            {"missing": missing_agent_dir},
            "按 agent 配置创建 agentDir 目录并补最小启动文件。",
        )

    # priority root causes
    by_priority = []
    for code in [
        "DM_SCOPE_NOT_ISOLATED",
        "ACCOUNT_WITHOUT_BINDING",
        "BINDING_ACCOUNT_MISSING",
        "BINDING_AGENT_MISSING",
        "MISSING_WORKSPACE",
        "MISSING_AGENT_DIR",
        "PLUGIN_OVERRIDE_RISK",
    ]:
        for i in issues:
            if i["code"] == code:
                by_priority.append(i)

    summary = {
        "agents": len(agents),
        "feishu_accounts_total": len(account_keys),
        "feishu_accounts_with_credentials": len(valid_nondefault_accounts),
        "feishu_bindings": len(feishu_bindings),
        "session_dmScope": session_scope,
        "issues_total": len(issues),
        "issues_by_severity": {
            s: sum(1 for i in issues if i["severity"] == s)
            for s in [SEV_CRITICAL, SEV_HIGH, SEV_MED, SEV_LOW, SEV_INFO]
        },
    }

    return {
        "summary": summary,
        "root_causes_priority": by_priority,
        "all_issues": issues,
    }


def print_text(report):
    s = report["summary"]
    print("# OpenClaw Multi-Agent Root Cause Inspect")
    print()
    print("## Summary")
    for k, v in s.items():
        print(f"- {k}: {v}")
    print()
    print("## Priority Root Causes")
    if not report["root_causes_priority"]:
        print("- none")
    for i in report["root_causes_priority"]:
        print(f"- [{i['severity']}] {i['code']}: {i['message']}")
        if i.get("evidence"):
            print(f"  evidence: {json.dumps(i['evidence'], ensure_ascii=False)}")
        if i.get("suggested_fix"):
            print(f"  fix: {i['suggested_fix']}")


def main():
    ap = argparse.ArgumentParser(description="Inspect OpenClaw multi-agent Feishu config and report root causes.")
    ap.add_argument("--config", default=os.path.expanduser("~/.openclaw/openclaw.json"), help="Path to openclaw.json")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--strict", action="store_true", help="Exit non-zero when HIGH/CRITICAL issues exist")
    args = ap.parse_args()

    config_path = Path(os.path.expanduser(args.config)).resolve()
    cfg = load_json(config_path)
    report = analyze(cfg, config_path)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)

    if args.strict:
        high = report["summary"]["issues_by_severity"][SEV_HIGH]
        critical = report["summary"]["issues_by_severity"][SEV_CRITICAL]
        if high or critical:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
