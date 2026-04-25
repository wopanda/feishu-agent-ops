#!/usr/bin/env python3
import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List


_REQUIRED_BOT_FIELDS = ["botName", "appId", "appSecret"]
_SCENARIOS = {"bootstrap", "expand", "diagnose"}
_ROUTING_MODES = {"account", "group", "mixed"}
_AGENT_MODES = {"bind-existing", "create-new"}


def expand(path: str) -> str:
    return os.path.expanduser(path or "")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def slugify_identifier(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if text and text[0].isdigit():
        text = f"bot-{text}"
    return text


def suggest_account_id(bot: Dict[str, Any], idx: int, seen: set[str]) -> str:
    explicit = bot.get("accountId") or bot.get("account_id")
    if explicit:
        seen.add(explicit)
        return explicit

    candidates = [
        bot.get("botName") or bot.get("bot_name"),
        bot.get("roleName") or bot.get("role_name"),
    ]
    base = ""
    for candidate in candidates:
        base = slugify_identifier(candidate or "")
        if base:
            break
    if not base:
        base = f"feishu-bot-{idx + 1}"

    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}-{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def infer_scenario(payload: Dict[str, Any]) -> str:
    if payload.get("scenario") in _SCENARIOS:
        return payload["scenario"]

    action = payload.get("action")
    mode = payload.get("mode")
    symptoms = payload.get("symptoms") or []
    if action in {"inspect", "root-cause", "repair"} or mode == "root-cause-first" or symptoms:
        return "diagnose"

    if payload.get("existingAgents"):
        return "expand"

    return "bootstrap"


def infer_routing_mode(payload: Dict[str, Any], bots: List[Dict[str, Any]]) -> str:
    raw = payload.get("routingMode") or payload.get("routing_mode")
    if raw in _ROUTING_MODES:
        return raw

    if any(bot.get("chatId") for bot in bots):
        return "group"
    return "account"


def infer_agent_mode(payload: Dict[str, Any], scenario: str, bots: List[Dict[str, Any]]) -> str:
    raw = payload.get("agentMode") or payload.get("agent_mode")
    if raw in _AGENT_MODES:
        return raw

    if any(bot.get("agentId") for bot in bots):
        return "bind-existing"

    if scenario == "diagnose":
        return "create-new"

    return "create-new"


def normalize_bots(payload: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[str]]:
    bots = payload.get("bots") or []
    warnings: List[str] = []
    normalized: List[Dict[str, Any]] = []
    seen_account_ids: set[str] = set()
    existing_agents = set(payload.get("existingAgents") or [])

    for idx, bot in enumerate(bots):
        account_id = suggest_account_id(bot, idx, seen_account_ids)
        item = {
            "accountId": account_id,
            "botName": bot.get("botName") or bot.get("bot_name"),
            "appId": bot.get("appId") or bot.get("app_id"),
            "appSecret": bot.get("appSecret") or bot.get("app_secret"),
            "roleName": bot.get("roleName") or bot.get("role_name"),
            "agentId": bot.get("agentId") or bot.get("agent_id"),
            "chatId": bot.get("chatId") or bot.get("chat_id"),
            "isDefault": bool(bot.get("isDefault", False)),
        }

        if not (bot.get("accountId") or bot.get("account_id")):
            warnings.append(f"bots[{idx}] accountId missing; generated deterministic accountId = {account_id}")

        missing = [k for k in _REQUIRED_BOT_FIELDS if not item.get(k)]
        if missing:
            warnings.append(f"bots[{idx}] missing required fields: {', '.join(missing)}")

        if item.get("agentId") and existing_agents and item.get("agentId") not in existing_agents:
            warnings.append(f"bots[{idx}] references unknown agentId: {item.get('agentId')}")

        normalized.append(item)

    return normalized, warnings


def normalize_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    bots, warnings = normalize_bots(payload)
    scenario = infer_scenario(payload)
    routing_mode = infer_routing_mode(payload, bots)
    agent_mode = infer_agent_mode(payload, scenario, bots)

    if scenario == "diagnose" and bots:
        warnings.append("diagnose scenario ignores bot creation unless repairAfterDiagnosis=true")

    return {
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
