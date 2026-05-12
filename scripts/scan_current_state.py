#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List


def expand(path: str) -> str:
    return os.path.expanduser(path or "")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def exists(path: str) -> bool:
    return bool(path) and Path(expand(path)).exists()


def collect_accounts(feishu_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    accounts = feishu_cfg.get("accounts") or {}

    if isinstance(accounts, list):
        iterable = []
        for item in accounts:
            if isinstance(item, dict) and item.get("accountId"):
                iterable.append((item.get("accountId"), item))
    else:
        iterable = list(accounts.items())

    for account_id, cfg in iterable:
        cfg = cfg or {}
        display_name = cfg.get("name") or cfg.get("botName")
        allow_from_path = Path(expand(f"~/.openclaw/credentials/feishu-{account_id}-allowFrom.json"))
        out.append({
            "accountId": account_id,
            "botName": display_name,
            "name": display_name,
            "enabled": bool(cfg.get("enabled", True)),
            "hasCredentials": bool(cfg.get("appId") and cfg.get("appSecret")),
            "dmPolicy": cfg.get("dmPolicy"),
            "allowFromExists": allow_from_path.exists(),
        })
    return out


def collect_bindings(bindings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for binding in bindings:
        match = binding.get("match") or {}
        peer = match.get("peer") or {}
        routing_kind = "other"
        if match.get("accountId") is not None:
            routing_kind = "account"
        elif peer.get("kind") == "group":
            routing_kind = "group"
        out.append({
            "agentId": binding.get("agentId"),
            "accountId": match.get("accountId"),
            "routingKind": routing_kind,
            "channel": match.get("channel"),
        })
    return out


def collect_agents(agent_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for agent in agent_list:
        workspace = agent.get("workspace")
        agent_dir = agent.get("agentDir")
        out.append({
            "id": agent.get("id"),
            "workspace": workspace,
            "workspaceExists": exists(workspace or ""),
            "agentDir": agent_dir,
            "agentDirExists": exists(agent_dir or ""),
        })
    return out


def build_warnings(session_dm_scope: str, feishu_accounts: List[Dict[str, Any]], feishu_bindings: List[Dict[str, Any]], agents: List[Dict[str, Any]]) -> List[str]:
    warnings: List[str] = []
    nondefault_accounts = [a for a in feishu_accounts if a.get("accountId") != "default"]
    bound_accounts = {b.get("accountId") for b in feishu_bindings if b.get("accountId")}

    if len(nondefault_accounts) > 1 and session_dm_scope != "per-account-channel-peer":
        warnings.append("multi-account dmScope is not per-account-channel-peer")

    missing_binding = [a.get("accountId") for a in nondefault_accounts if a.get("accountId") not in bound_accounts]
    if missing_binding:
        warnings.append(f"nondefault accounts without bindings: {missing_binding}")

    for agent in agents:
        if agent.get("workspace") and not agent.get("workspaceExists"):
            warnings.append(f"workspace missing: {agent.get('id')}")
        if agent.get("agentDir") and not agent.get("agentDirExists"):
            warnings.append(f"agentDir missing: {agent.get('id')}")

    return warnings


def collect_collab_readiness(obj: Dict[str, Any], session_dm_scope: str, feishu_accounts: List[Dict[str, Any]], feishu_bindings: List[Dict[str, Any]]) -> Dict[str, Any]:
    plugins = ((obj.get("plugins") or {}).get("entries") or {})
    messages = obj.get("messages") or {}
    accounts = [a for a in feishu_accounts if a.get("accountId") != "default" and a.get("enabled", True)]
    bound_accounts = {b.get("accountId") for b in feishu_bindings if b.get("accountId")}

    checks: List[Dict[str, Any]] = []

    def push(check_id: str, status: str, evidence: str, fix: str | None = None) -> None:
        item: Dict[str, Any] = {"id": check_id, "status": status, "evidence": evidence}
        if fix:
            item["fix"] = fix
        checks.append(item)

    lark_enabled = bool((plugins.get("openclaw-lark") or {}).get("enabled"))
    legacy_enabled = bool((plugins.get("feishu") or {}).get("enabled"))
    bot_chat_enabled = bool((plugins.get("feishu-bot-chat") or {}).get("enabled"))

    push(
        "openclaw-lark-enabled",
        "pass" if lark_enabled else "fail",
        f"openclaw-lark enabled = {lark_enabled}",
        None if lark_enabled else "启用 openclaw-lark 插件，作为当前飞书主链。",
    )
    if legacy_enabled:
        push("legacy-feishu-disabled", "warn", "legacy feishu plugin is still enabled", "多龙虾主链建议只保留 openclaw-lark 启用，避免插件链歧义。")
    else:
        push("legacy-feishu-disabled", "pass", "legacy feishu plugin is disabled")

    if len(accounts) > 1:
        push(
            "feishu-bot-chat-enabled",
            "pass" if bot_chat_enabled else "warn",
            f"feishu-bot-chat enabled = {bot_chat_enabled}",
            None if bot_chat_enabled else "群内多龙虾协作建议启用 feishu-bot-chat。",
        )
        push(
            "dm-scope-account-isolated",
            "pass" if session_dm_scope == "per-account-channel-peer" else "fail",
            f"session.dmScope = {session_dm_scope!r}",
            None if session_dm_scope == "per-account-channel-peer" else "多账号飞书建议使用 per-account-channel-peer。",
        )
    else:
        push("single-lobster-path", "pass", f"nondefault enabled accounts = {len(accounts)}; single lobster does not require multi-agent collaboration checks")

    missing = sorted([a.get("accountId") for a in accounts if a.get("accountId") not in bound_accounts])
    push(
        "nondefault-account-binding-closure",
        "pass" if not missing else "fail",
        "all nondefault accounts have bindings" if not missing else f"missing bindings: {missing}",
        None if not missing else "补齐 accountId -> agentId 的 feishu binding。",
    )

    ack_scope = messages.get("ackReactionScope")
    if len(accounts) > 1:
        push(
            "group-mention-ack-scope",
            "pass" if ack_scope == "group-mentions" else "warn",
            f"messages.ackReactionScope = {ack_scope!r}",
            None if ack_scope == "group-mentions" else "群聊多 bot 场景建议设置为 group-mentions，降低误反应噪音。",
        )

    failed = len([c for c in checks if c["status"] == "fail"])
    warned = len([c for c in checks if c["status"] == "warn"])
    return {
        "summary": {
            "status": "fail" if failed else ("warn" if warned else "pass"),
            "checks": len(checks),
            "failed": failed,
            "warn": warned,
            "nondefaultEnabledAccounts": len(accounts),
        },
        "checks": checks,
    }


def scan_current_state(config_path: str) -> Dict[str, Any]:
    config_path_obj = Path(expand(config_path)).resolve()
    obj = load_json(config_path_obj)

    session = obj.get("session") or {}
    bindings = obj.get("bindings") or []
    feishu_cfg = ((obj.get("channels") or {}).get("feishu") or {})
    agent_list = ((obj.get("agents") or {}).get("list") or [])

    feishu_accounts = collect_accounts(feishu_cfg)
    feishu_bindings = [b for b in collect_bindings(bindings) if b.get("channel") == "feishu"]
    agents = collect_agents(agent_list)
    warnings = build_warnings(session.get("dmScope"), feishu_accounts, feishu_bindings, agents)
    collab_readiness = collect_collab_readiness(obj, session.get("dmScope"), feishu_accounts, feishu_bindings)

    return {
        "config": str(config_path_obj),
        "session": {
            "dmScope": session.get("dmScope")
        },
        "feishu": {
            "topLevelKeys": sorted(feishu_cfg.keys()),
            "accounts": feishu_accounts,
            "bindings": feishu_bindings,
        },
        "agents": agents,
        "bindings": feishu_bindings,
        "collabReadiness": collab_readiness,
        "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Scan current OpenClaw config into observed-state structure.")
    ap.add_argument("--config", default="~/.openclaw/openclaw.json", help="Path to openclaw.json")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    observed = scan_current_state(args.config)

    if args.pretty:
        print(json.dumps(observed, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(observed, ensure_ascii=False))


if __name__ == "__main__":
    main()
