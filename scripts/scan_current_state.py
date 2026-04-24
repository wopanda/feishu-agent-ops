#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List


def expand(path: str) -> str:
    return os.path.expanduser(path or "")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


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


def detect_implicit_default_main(feishu_cfg: Dict[str, Any], feishu_accounts: List[Dict[str, Any]], feishu_bindings: List[Dict[str, Any]], agents: List[Dict[str, Any]]) -> Dict[str, Any]:
    has_top_level_credentials = bool(feishu_cfg.get("appId") and feishu_cfg.get("appSecret"))
    account_ids = {a.get("accountId") for a in feishu_accounts if a.get("accountId")}
    has_default_account = "default" in account_ids
    default_binding = next((b for b in feishu_bindings if b.get("accountId") == "default"), None)

    agent_ids = [a.get("id") for a in agents if a.get("id")]
    inferred_main_agent = "main" if "main" in agent_ids else (agent_ids[0] if len(agent_ids) == 1 else None)

    needs_migration = bool(
        has_top_level_credentials
        and not has_default_account
        and not default_binding
        and inferred_main_agent
    )

    return {
        "hasTopLevelCredentials": has_top_level_credentials,
        "hasDefaultAccount": has_default_account,
        "hasDefaultBinding": bool(default_binding),
        "inferredMainAgentId": inferred_main_agent,
        "needsSingleToMultiMigration": needs_migration,
    }


def build_warnings(session_dm_scope: str, feishu_accounts: List[Dict[str, Any]], feishu_bindings: List[Dict[str, Any]], agents: List[Dict[str, Any]], migration: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    nondefault_accounts = [a for a in feishu_accounts if a.get("accountId") != "default"]
    bound_accounts = {b.get("accountId") for b in feishu_bindings if b.get("accountId")}

    if len(nondefault_accounts) > 1 and session_dm_scope != "per-account-channel-peer":
        warnings.append("multi-account dmScope is not per-account-channel-peer")

    missing_binding = [a.get("accountId") for a in nondefault_accounts if a.get("accountId") not in bound_accounts]
    if missing_binding:
        warnings.append(f"accounts without bindings: {missing_binding}")

    for agent in agents:
        if agent.get("workspace") and not agent.get("workspaceExists"):
            warnings.append(f"workspace missing: {agent.get('id')}")
        if agent.get("agentDir") and not agent.get("agentDirExists"):
            warnings.append(f"agentDir missing: {agent.get('id')}")

    if migration.get("needsSingleToMultiMigration"):
        warnings.append("single-to-multi migration needed: top-level feishu credentials are not yet solidified into accounts.default + explicit binding")

    return warnings


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
    migration = detect_implicit_default_main(feishu_cfg, feishu_accounts, feishu_bindings, agents)
    warnings = build_warnings(session.get("dmScope"), feishu_accounts, feishu_bindings, agents, migration)

    return {
        "config": str(config_path_obj),
        "session": {
            "dmScope": session.get("dmScope")
        },
        "feishu": {
            "topLevelKeys": sorted(feishu_cfg.keys()),
            "hasTopLevelCredentials": migration.get("hasTopLevelCredentials"),
            "topLevelCredentialPreview": {
                "appId": feishu_cfg.get("appId"),
                "name": feishu_cfg.get("name") or feishu_cfg.get("botName"),
            } if migration.get("hasTopLevelCredentials") else None,
            "accounts": feishu_accounts,
            "bindings": feishu_bindings,
        },
        "agents": agents,
        "bindings": feishu_bindings,
        "migration": migration,
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
