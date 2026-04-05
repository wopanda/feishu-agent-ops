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
    for account_id, cfg in accounts.items():
        cfg = cfg or {}
        out.append({
            "accountId": account_id,
            "botName": cfg.get("botName"),
            "enabled": bool(cfg.get("enabled", True)),
            "hasCredentials": bool(cfg.get("appId") and cfg.get("appSecret")),
            "dmPolicy": cfg.get("dmPolicy"),
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
        warnings.append(f"accounts without bindings: {missing_binding}")

    for agent in agents:
        if agent.get("workspace") and not agent.get("workspaceExists"):
            warnings.append(f"workspace missing: {agent.get('id')}")
        if agent.get("agentDir") and not agent.get("agentDirExists"):
            warnings.append(f"agentDir missing: {agent.get('id')}")

    return warnings


def main() -> None:
    ap = argparse.ArgumentParser(description="Scan current OpenClaw config into observed-state structure.")
    ap.add_argument("--config", default="~/.openclaw/openclaw.json", help="Path to openclaw.json")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    config_path = Path(expand(args.config)).resolve()
    obj = load_json(config_path)

    session = obj.get("session") or {}
    bindings = obj.get("bindings") or []
    feishu_cfg = ((obj.get("channels") or {}).get("feishu") or {})
    agent_list = ((obj.get("agents") or {}).get("list") or [])

    feishu_accounts = collect_accounts(feishu_cfg)
    feishu_bindings = [b for b in collect_bindings(bindings) if b.get("channel") == "feishu"]
    agents = collect_agents(agent_list)
    warnings = build_warnings(session.get("dmScope"), feishu_accounts, feishu_bindings, agents)

    observed = {
        "config": str(config_path),
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
        "warnings": warnings,
    }

    if args.pretty:
        print(json.dumps(observed, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(observed, ensure_ascii=False))


if __name__ == "__main__":
    main()
