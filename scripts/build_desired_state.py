#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def suggest_agent_id(bot: Dict[str, Any]) -> str:
    return (bot.get("agentId") or bot.get("accountId") or bot.get("roleName") or "agent").strip().lower().replace(" ", "-")


def build_workspace(agent_id: str) -> str:
    return f"~/.openclaw/workspace-{agent_id}"


def build_agent_dir(agent_id: str) -> str:
    return f"~/.openclaw/agents/{agent_id}/agent"


def build_desired_state(req: Dict[str, Any], obs: Dict[str, Any]) -> Dict[str, Any]:
    scenario = req.get("scenario")
    routing_mode = req.get("routingMode") or "account"
    agent_mode = req.get("agentMode") or "create-new"

    existing_agent_ids = {a.get("id") for a in (obs.get("agents") or []) if a.get("id")}
    existing_account_ids = {a.get("accountId") for a in ((obs.get("feishu") or {}).get("accounts") or []) if a.get("accountId")}
    existing_pairs = {(b.get("accountId"), b.get("agentId")) for b in ((obs.get("feishu") or {}).get("bindings") or [])}

    planned_agents: List[Dict[str, Any]] = []
    planned_accounts: List[Dict[str, Any]] = []
    planned_bindings: List[Dict[str, Any]] = []
    warnings: List[str] = []

    if scenario == "diagnose":
        return {
            "scenario": scenario,
            "routingMode": routing_mode,
            "agentMode": agent_mode,
            "configPath": req.get("configPath"),
            "planSummary": {
                "createAgents": 0,
                "createAccounts": 0,
                "createBindings": 0,
                "mode": "diagnose-only",
            },
            "plannedAgents": [],
            "plannedAccounts": [],
            "plannedBindings": [],
            "nextActions": [
                "run compat-scan if needed",
                "inspect root-cause candidates",
                "prepare minimal repair plan",
            ],
            "warnings": req.get("warnings") or [],
        }

    for bot in req.get("bots") or []:
        account_id = bot.get("accountId")
        agent_id = bot.get("agentId") if agent_mode == "bind-existing" and bot.get("agentId") else suggest_agent_id(bot)

        if account_id not in existing_account_ids:
            planned_accounts.append({
                "accountId": account_id,
                "botName": bot.get("botName"),
                "appId": bot.get("appId"),
                "dmPolicy": "open",
                "source": "request",
            })
        else:
            warnings.append(f"account already exists: {account_id}")

        if agent_mode == "create-new":
            if agent_id not in existing_agent_ids:
                planned_agents.append({
                    "id": agent_id,
                    "workspace": build_workspace(agent_id),
                    "agentDir": build_agent_dir(agent_id),
                    "source": "request",
                })
            else:
                warnings.append(f"agent already exists: {agent_id}")

        pair = (account_id, agent_id)
        if pair not in existing_pairs:
            planned_bindings.append({
                "agentId": agent_id,
                "accountId": account_id,
                "routingKind": "group" if routing_mode == "group" else "account",
                "chatId": bot.get("chatId"),
                "source": "request",
            })
        else:
            warnings.append(f"binding already exists: {account_id} -> {agent_id}")

    return {
        "scenario": scenario,
        "routingMode": routing_mode,
        "agentMode": agent_mode,
        "configPath": req.get("configPath"),
        "planSummary": {
            "createAgents": len(planned_agents),
            "createAccounts": len(planned_accounts),
            "createBindings": len(planned_bindings),
            "mode": "preview",
        },
        "plannedAgents": planned_agents,
        "plannedAccounts": planned_accounts,
        "plannedBindings": planned_bindings,
        "nextActions": [
            "review preview",
            "confirm before apply",
            "backup config before patch",
            "verify at least one target bot after apply",
        ],
        "warnings": (req.get("warnings") or []) + warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build desired-state preview from normalized request + observed state.")
    ap.add_argument("--request", required=True, help="Path to normalized request JSON")
    ap.add_argument("--observed", required=True, help="Path to observed-state JSON")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    req = load_json(args.request)
    obs = load_json(args.observed)
    desired = build_desired_state(req, obs)

    if args.pretty:
        print(json.dumps(desired, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(desired, ensure_ascii=False))


if __name__ == "__main__":
    main()
