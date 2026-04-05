#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def build_verification_checklist(desired: Dict[str, Any]) -> Dict[str, Any]:
    planned_agents = desired.get("plannedAgents") or []
    planned_accounts = desired.get("plannedAccounts") or []
    planned_bindings = desired.get("plannedBindings") or []

    checks: List[Dict[str, Any]] = []

    checks.append(
        {
            "id": "config-readable",
            "kind": "config",
            "target": desired.get("configPath") or "~/.openclaw/openclaw.json",
            "expectation": "配置文件可读取，且 JSON 结构有效",
            "autoCheck": False,
        }
    )

    for agent in planned_agents:
        if agent.get("workspace"):
            checks.append(
                {
                    "id": f"workspace:{agent.get('id')}",
                    "kind": "filesystem",
                    "target": agent.get("workspace"),
                    "expectation": "workspace 目录存在",
                    "autoCheck": False,
                }
            )
        if agent.get("agentDir"):
            checks.append(
                {
                    "id": f"agentDir:{agent.get('id')}",
                    "kind": "filesystem",
                    "target": agent.get("agentDir"),
                    "expectation": "agentDir 目录存在",
                    "autoCheck": False,
                }
            )

    if planned_bindings:
        checks.append(
            {
                "id": "bindings-count",
                "kind": "config",
                "target": "bindings",
                "expectation": f"bindings 至少新增 {len(planned_bindings)} 条目标映射",
                "autoCheck": False,
            }
        )

    if planned_accounts:
        probe_accounts = [a.get("accountId") for a in planned_accounts[:3] if a.get("accountId")]
        checks.append(
            {
                "id": "bot-probe",
                "kind": "runtime",
                "target": probe_accounts,
                "expectation": "至少 1 个目标 bot 能进入待验证列表并完成回复验证",
                "autoCheck": False,
            }
        )

    return {
        "mode": "verification-checklist",
        "configPath": desired.get("configPath") or "~/.openclaw/openclaw.json",
        "summary": {
            "checkCount": len(checks),
            "plannedAgents": len(planned_agents),
            "plannedAccounts": len(planned_accounts),
            "plannedBindings": len(planned_bindings),
        },
        "checks": checks,
        "warnings": desired.get("warnings") or [],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build post-apply verification checklist from desired-state preview.")
    ap.add_argument("--desired", required=True, help="Path to desired-state JSON")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    desired = load_json(args.desired)
    result = build_verification_checklist(desired)

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
