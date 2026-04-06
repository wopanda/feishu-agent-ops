#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from scan_current_state import scan_current_state


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def expand(path: str) -> str:
    return os.path.expanduser(path or "")


def _exists(path: str) -> bool:
    return bool(path) and Path(expand(path)).exists()


def _check_account_present(observed: Dict[str, Any], account_id: str) -> bool:
    accounts = ((observed.get("feishu") or {}).get("accounts") or [])
    return any(a.get("accountId") == account_id for a in accounts)


def _check_binding_present(observed: Dict[str, Any], account_id: str, agent_id: str) -> bool:
    bindings = ((observed.get("feishu") or {}).get("bindings") or [])
    return any(b.get("accountId") == account_id and b.get("agentId") == agent_id for b in bindings)


def _allowfrom_path(account_id: str) -> str:
    return f"~/.openclaw/credentials/feishu-{account_id}-allowFrom.json"


def build_verification_checklist(desired: Dict[str, Any], config_path: str | None = None) -> Dict[str, Any]:
    config_path = config_path or desired.get("configPath") or "~/.openclaw/openclaw.json"
    observed = scan_current_state(config_path)
    planned_agents = desired.get("plannedAgents") or []
    planned_accounts = desired.get("plannedAccounts") or []
    planned_bindings = desired.get("plannedBindings") or []

    checks: List[Dict[str, Any]] = []

    config_ok = Path(expand(config_path)).exists()
    checks.append({
        "id": "config-readable",
        "kind": "config",
        "target": config_path,
        "expectation": "配置文件可读取，且 JSON 结构有效",
        "autoCheck": True,
        "status": "pass" if config_ok else "fail",
    })

    for agent in planned_agents:
        workspace = agent.get("workspace")
        agent_dir = agent.get("agentDir")
        if workspace:
            checks.append({
                "id": f"workspace:{agent.get('id')}",
                "kind": "filesystem",
                "target": workspace,
                "expectation": "workspace 目录存在",
                "autoCheck": True,
                "status": "pass" if _exists(workspace) else "fail",
            })
        if agent_dir:
            checks.append({
                "id": f"agentDir:{agent.get('id')}",
                "kind": "filesystem",
                "target": agent_dir,
                "expectation": "agentDir 目录存在",
                "autoCheck": True,
                "status": "pass" if _exists(agent_dir) else "fail",
            })

    for account in planned_accounts:
        account_id = account.get("accountId")
        checks.append({
            "id": f"account:{account_id}",
            "kind": "config",
            "target": account_id,
            "expectation": "account 已写入 channels.feishu.accounts",
            "autoCheck": True,
            "status": "pass" if _check_account_present(observed, account_id) else "fail",
        })
        checks.append({
            "id": f"allowFrom:{account_id}",
            "kind": "runtime-guard",
            "target": _allowfrom_path(account_id),
            "expectation": "建议存在 allowFrom/pairing 放行配置，避免 not paired",
            "autoCheck": True,
            "status": "pass" if _exists(_allowfrom_path(account_id)) else "warn",
        })

    for binding in planned_bindings:
        account_id = binding.get("accountId")
        agent_id = binding.get("agentId")
        checks.append({
            "id": f"binding:{account_id}->{agent_id}",
            "kind": "config",
            "target": f"{account_id}->{agent_id}",
            "expectation": "binding 已形成 accountId -> agentId 闭环",
            "autoCheck": True,
            "status": "pass" if _check_binding_present(observed, account_id, agent_id) else "fail",
        })

    if planned_accounts:
        probe_accounts = [a.get("accountId") for a in planned_accounts[:3] if a.get("accountId")]
        checks.append({
            "id": "bot-probe",
            "kind": "runtime",
            "target": probe_accounts,
            "expectation": "至少 1 个目标 bot 能完成真实回复验证；若不回复先查 allowFrom/pairing",
            "autoCheck": False,
            "status": "todo",
        })

    pass_count = sum(1 for c in checks if c.get("status") == "pass")
    warn_count = sum(1 for c in checks if c.get("status") == "warn")
    fail_count = sum(1 for c in checks if c.get("status") == "fail")

    return {
        "mode": "verification-checklist",
        "configPath": config_path,
        "summary": {
            "checkCount": len(checks),
            "passCount": pass_count,
            "warnCount": warn_count,
            "failCount": fail_count,
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
    ap.add_argument("--config", help="Override config path for live verification")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    desired = load_json(args.desired)
    result = build_verification_checklist(desired, args.config)

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
