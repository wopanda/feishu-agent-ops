#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def generate_patch_preview(desired: Dict[str, Any]) -> Dict[str, Any]:
    config_path = desired.get("configPath") or "~/.openclaw/openclaw.json"
    planned_agents = desired.get("plannedAgents") or []
    planned_accounts = desired.get("plannedAccounts") or []
    planned_bindings = desired.get("plannedBindings") or []

    json_patch_preview: List[Dict[str, Any]] = []
    filesystem_preview: List[Dict[str, Any]] = []

    for account in planned_accounts:
        account_id = account.get("accountId")
        json_patch_preview.append({
            "op": "add",
            "path": f"/channels/feishu/accounts/{account_id}",
            "value": {
                "appId": account.get("appId"),
                "appSecret": "<redacted-at-preview>",
                "botName": account.get("botName"),
                "enabled": True,
            },
        })

    for binding in planned_bindings:
        value = {
            "agentId": binding.get("agentId"),
            "match": {
                "channel": "feishu",
                "accountId": binding.get("accountId"),
            },
        }
        if binding.get("routingKind") == "group" and binding.get("chatId"):
            value["match"]["peer"] = {"kind": "group", "id": binding.get("chatId")}
        json_patch_preview.append({
            "op": "add",
            "path": "/bindings/-",
            "value": value,
        })

    for agent in planned_agents:
        value = {
            "id": agent.get("id"),
            "workspace": agent.get("workspace"),
            "agentDir": agent.get("agentDir"),
        }
        json_patch_preview.append({
            "op": "add",
            "path": "/agents/list/-",
            "value": value,
        })
        filesystem_preview.append({
            "op": "mkdir",
            "path": agent.get("workspace"),
            "reason": f"workspace for {agent.get('id')}",
        })
        filesystem_preview.append({
            "op": "mkdir",
            "path": agent.get("agentDir"),
            "reason": f"agentDir for {agent.get('id')}",
        })

    return {
        "configPath": config_path,
        "summary": {
            "addAccounts": len(planned_accounts),
            "addBindings": len(planned_bindings),
            "addAgents": len(planned_agents),
            "mkdirCount": len(filesystem_preview),
        },
        "jsonPatchPreview": json_patch_preview,
        "filesystemPreview": filesystem_preview,
        "warnings": desired.get("warnings") or [],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate patch preview from desired-state output.")
    ap.add_argument("--desired", required=True, help="Path to desired-state JSON")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    desired = load_json(args.desired)
    patch_preview = generate_patch_preview(desired)

    if args.pretty:
        print(json.dumps(patch_preview, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(patch_preview, ensure_ascii=False))


if __name__ == "__main__":
    main()
