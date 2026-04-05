#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple


def expand(path: str) -> str:
    return os.path.expanduser(path or "")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def infer_scenario(payload: Dict[str, Any]) -> str:
    if payload.get("scenario") in {"bootstrap", "expand", "diagnose"}:
        return payload["scenario"]

    action = payload.get("action")
    mode = payload.get("mode")
    symptoms = payload.get("symptoms") or []

    if action in {"inspect", "root-cause", "repair"} or mode == "root-cause-first" or symptoms:
        return "diagnose"

    existing_agents = payload.get("existingAgents") or []
    if action == "plan" and existing_agents:
        return "expand"

    return "bootstrap"


def infer_routing_mode(payload: Dict[str, Any], bots: List[Dict[str, Any]]) -> str:
    raw = payload.get("routingMode") or payload.get("routing_mode")
    if raw in {"account", "group", "mixed"}:
        return raw

    has_group = any((bot.get("chatId") or bot.get("chat_id")) for bot in bots)
    if has_group:
        return "group"
    return "account"


def infer_agent_mode(payload: Dict[str, Any], scenario: str, bots: List[Dict[str, Any]]) -> str:
    raw = payload.get("agentMode") or payload.get("agent_mode")
    if raw in {"bind-existing", "create-new"}:
        return raw

    if scenario == "expand":
        return "bind-existing"

    has_agent_ids = any(bot.get("agentId") for bot in bots)
    if has_agent_ids:
        return "bind-existing"
    return "create-new"


def normalize_bots(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    bots = payload.get("bots") or []
    warnings: List[str] = []
    normalized: List[Dict[str, Any]] = []

    for idx, bot in enumerate(bots):
        item = {
            "accountId": bot.get("accountId") or bot.get("account_id"),
            "botName": bot.get("botName") or bot.get("bot_name"),
            "appId": bot.get("appId") or bot.get("app_id"),
            "appSecret": bot.get("appSecret") or bot.get("app_secret"),
            "roleName": bot.get("roleName") or bot.get("role_name"),
            "agentId": bot.get("agentId") or bot.get("agent_id"),
            "chatId": bot.get("chatId") or bot.get("chat_id"),
            "isDefault": bool(bot.get("isDefault", False)),
        }
        missing = [k for k in ["accountId", "botName", "appId", "appSecret"] if not item.get(k)]
        if missing:
            warnings.append(f"bots[{idx}] missing required fields: {', '.join(missing)}")
        normalized.append(item)

    return normalized, warnings


def normalize_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    bots, warnings = normalize_bots(payload)
    scenario = infer_scenario(payload)
    routing_mode = infer_routing_mode(payload, bots)
    agent_mode = infer_agent_mode(payload, scenario, bots)

    normalized = {
        "scenario": scenario,
        "goal": payload.get("goal") or payload.get("mode") or payload.get("action") or None,
        "routingMode": routing_mode,
        "agentMode": agent_mode,
        "defaultModel": payload.get("defaultModel"),
        "configPath": payload.get("configPath") or payload.get("config") or "~/.openclaw/openclaw.json",
        "existingAgents": payload.get("existingAgents") or [],
        "bots": bots,
        "symptoms": payload.get("symptoms") or [],
        "affectedBots": payload.get("affectedBots") or [],
        "allowReadOnlyScan": bool(payload.get("allowReadOnlyScan", scenario == "diagnose")),
        "repairAfterDiagnosis": bool(payload.get("repairAfterDiagnosis", False)),
        "sourceAction": payload.get("action"),
        "sourceMode": payload.get("mode"),
        "warnings": warnings,
    }

    return normalized


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalize Feishu Agent Ops request into scenario-first internal shape.")
    ap.add_argument("--input", required=True, help="Path to input JSON")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    payload = load_json(Path(expand(args.input)).resolve())
    normalized = normalize_request(payload)

    if args.pretty:
        print(json.dumps(normalized, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(normalized, ensure_ascii=False))


if __name__ == "__main__":
    main()
