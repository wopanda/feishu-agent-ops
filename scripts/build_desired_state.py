#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def slugify_identifier(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if text and text[0].isdigit():
        text = f"agent-{text}"
    return text


def suggest_agent_id(bot: Dict[str, Any]) -> str:
    explicit = bot.get("agentId")
    if explicit:
        return explicit
    for candidate in [bot.get("accountId"), bot.get("roleName"), bot.get("botName")]:
        slug = slugify_identifier(candidate or "")
        if slug:
            return slug
    return "agent"


def build_workspace(agent_id: str) -> str:
    return f"~/.openclaw/workspace-{agent_id}"


def build_agent_dir(agent_id: str) -> str:
    return f"~/.openclaw/agents/{agent_id}/agent"


def _existing_account_ids(obs: Dict[str, Any]) -> set[str]:
    return {a.get("accountId") for a in ((obs.get("feishu") or {}).get("accounts") or []) if a.get("accountId")}


def _existing_agent_ids(obs: Dict[str, Any]) -> set[str]:
    return {a.get("id") for a in (obs.get("agents") or []) if a.get("id")}


def _existing_pairs(obs: Dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (b.get("accountId"), b.get("agentId"))
        for b in ((obs.get("feishu") or {}).get("bindings") or [])
        if b.get("accountId") and b.get("agentId")
    }


def _build_diagnose_actions(req: Dict[str, Any], obs: Dict[str, Any]) -> List[str]:
    actions: List[str] = []
    warnings = obs.get("warnings") or []
    if any("dmScope" in w for w in warnings):
        actions.append("inspect dmScope before any repair")
    actions.append("inspect account-binding closure")
    actions.append("inspect workspace and agentDir completeness")
    actions.append("inspect allowFrom/pairing evidence for target bot if runtime says not paired")
    if req.get("repairAfterDiagnosis"):
        actions.append("prepare minimal repair plan after root-cause confirmation")
    return actions


def build_desired_state(req: Dict[str, Any], obs: Dict[str, Any]) -> Dict[str, Any]:
    scenario = req.get("scenario")
    routing_mode = req.get("routingMode") or "account"
    agent_mode = req.get("agentMode") or "create-new"

    existing_agent_ids = _existing_agent_ids(obs)
    existing_account_ids = _existing_account_ids(obs)
    existing_pairs = _existing_pairs(obs)

    planned_agents: List[Dict[str, Any]] = []
    planned_accounts: List[Dict[str, Any]] = []
    planned_bindings: List[Dict[str, Any]] = []
    warnings: List[str] = list(req.get("warnings") or [])

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
            "nextActions": _build_diagnose_actions(req, obs),
            "warnings": warnings,
        }

    for bot in req.get("bots") or []:
        account_id = bot.get("accountId")
        requested_agent_id = bot.get("agentId")

        if requested_agent_id:
            effective_agent_mode = "bind-existing"
        else:
            effective_agent_mode = agent_mode

        agent_id = requested_agent_id if effective_agent_mode == "bind-existing" else suggest_agent_id(bot)

        if account_id not in existing_account_ids:
            planned_accounts.append({
                "accountId": account_id,
                "botName": bot.get("botName"),
                "appId": bot.get("appId"),
                "name": bot.get("botName"),
                "dmPolicy": "open",
                "source": "request",
            })
        else:
            warnings.append(f"account already exists: {account_id}")

        if effective_agent_mode == "bind-existing" and not agent_id:
            warnings.append(f"bind-existing requires explicit agentId: {account_id}")
            continue

        if effective_agent_mode == "create-new":
            if agent_id not in existing_agent_ids:
                planned_agents.append({
                    "id": agent_id,
                    "workspace": build_workspace(agent_id),
                    "agentDir": build_agent_dir(agent_id),
                    "source": "request",
                })
            else:
                warnings.append(f"agent already exists: {agent_id}")
        elif agent_id not in existing_agent_ids:
            warnings.append(f"bind-existing requested but agent does not exist yet: {agent_id}")

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
            "verify runtime path including allowFrom/pairing after apply",
        ],
        "warnings": warnings,
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
