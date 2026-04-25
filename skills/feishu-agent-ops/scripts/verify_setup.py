#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple


def expand(path: str) -> str:
    return os.path.expanduser(path or "")


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(expand(path)).read_text(encoding='utf-8'))


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


def collect_accounts_map(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    accounts = ((cfg.get("channels") or {}).get("feishu") or {}).get("accounts") or {}
    if isinstance(accounts, dict):
        return {k: (v or {}) for k, v in accounts.items()}

    out: Dict[str, Dict[str, Any]] = {}
    for item in accounts:
        if isinstance(item, dict) and item.get("accountId"):
            out[item["accountId"]] = item
    return out


def account_has_binding(cfg: Dict[str, Any], account_id: str) -> bool:
    for binding in cfg.get("bindings") or []:
        match = (binding or {}).get("match") or {}
        if match.get("channel") == "feishu" and match.get("accountId") == account_id:
            return True
    return False


def read_allow_from(account_id: str) -> Tuple[bool, List[str]]:
    path = Path(expand(f"~/.openclaw/credentials/feishu-{account_id}-allowFrom.json"))
    if not path.exists():
        return False, []
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
        return True, list(obj.get("allowFrom") or [])
    except Exception:
        return True, []


def read_pairing_request(account_id: str, sender_id: str | None) -> bool:
    if not sender_id:
        return False
    path = Path(expand("~/.openclaw/credentials/feishu-pairing.json"))
    if not path.exists():
        return False
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return False

    for req in obj.get("requests") or []:
        if req.get("id") == sender_id and ((req.get("meta") or {}).get("accountId") == account_id):
            return True
    return False


def probe_runtime_logs(account_id: str, limit: int) -> Dict[str, Any]:
    cmd = [
        "openclaw",
        "logs",
        "--plain",
        "--limit",
        str(limit),
        "--max-bytes",
        "1000000",
        "--timeout",
        "12000",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "notPairedCount": 0,
            "samples": [],
        }

    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    lines = [line for line in text.splitlines() if f"feishu[{account_id}]" in line]
    not_paired = [line for line in lines if "not paired" in line]

    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "notPairedCount": len(not_paired),
        "samples": not_paired[-5:],
    }


def runtime_verify(config_path: str, account_id: str, sender_id: str | None, log_limit: int) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    warnings: List[str] = []

    cfg_path = Path(expand(config_path)).resolve()
    cfg = load_json(str(cfg_path))

    accounts_map = collect_accounts_map(cfg)
    account = accounts_map.get(account_id)
    binding_ok = account_has_binding(cfg, account_id)

    allow_exists, allow_list = read_allow_from(account_id)
    sender_allowed = None if not sender_id else sender_id in allow_list
    pairing_pending = read_pairing_request(account_id, sender_id)

    log_probe = probe_runtime_logs(account_id, log_limit)

    def push(check_id: str, status: str, evidence: str, fix: str | None = None) -> None:
        item: Dict[str, Any] = {"id": check_id, "status": status, "evidence": evidence}
        if fix:
            item["fix"] = fix
        checks.append(item)

    push("config-readable", "pass", f"config loaded: {cfg_path}")

    if account:
        display_name = account.get("name") or account.get("botName")
        push("account-exists", "pass", f"account found: {account_id} ({display_name})")
    else:
        push("account-exists", "fail", f"account missing: {account_id}", "补齐 channels.feishu.accounts.<accountId> 配置")

    if binding_ok:
        push("binding-closed", "pass", f"binding exists for account: {account_id}")
    else:
        push("binding-closed", "fail", f"binding missing for account: {account_id}", "补齐 accountId -> agentId 的 feishu binding")

    if allow_exists:
        push("allowFrom-file", "pass", f"allowFrom exists: feishu-{account_id}-allowFrom.json")
    else:
        push("allowFrom-file", "warn", f"allowFrom missing for account: {account_id}", "建议补 allowFrom，避免 pairing 阻塞")

    if sender_id:
        if sender_allowed:
            push("sender-allowed", "pass", f"sender is allowed: {sender_id}")
        else:
            fix = "把 sender_id 加入 allowFrom，或执行 pairing 放行"
            if pairing_pending:
                fix = "已有 pairing request，可直接按 pairing code 放行"
            push("sender-allowed", "fail", f"sender NOT in allowFrom: {sender_id}", fix)

    if pairing_pending:
        push("pairing-pending", "warn", f"pairing request exists for sender/account: {sender_id}/{account_id}")

    if log_probe.get("ok"):
        count = int(log_probe.get("notPairedCount") or 0)
        if count > 0:
            push("runtime-not-paired", "fail", f"recent logs show not paired x{count}", "优先修 allowFrom/pairing，再做其它路由排障")
        else:
            push("runtime-not-paired", "pass", "no recent 'not paired' logs for this account")
    else:
        warnings.append(f"runtime log probe unavailable: {log_probe.get('error') or log_probe.get('returncode')}")

    failed = len([c for c in checks if c["status"] == "fail"])
    warn = len([c for c in checks if c["status"] == "warn"])
    passed = len([c for c in checks if c["status"] == "pass"])

    return {
        "mode": "runtime-verification",
        "configPath": str(cfg_path),
        "target": {
            "accountId": account_id,
            "senderId": sender_id,
        },
        "summary": {
            "checkCount": len(checks),
            "passed": passed,
            "failed": failed,
            "warn": warn,
            "status": "pass" if failed == 0 else "fail",
        },
        "checks": checks,
        "runtimeLogProbe": log_probe,
        "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build post-apply verification checklist or runtime verification report.")
    ap.add_argument("--desired", help="Path to desired-state JSON (legacy checklist mode)")
    ap.add_argument("--config", default="~/.openclaw/openclaw.json", help="Path to openclaw.json (runtime mode)")
    ap.add_argument("--account-id", help="Feishu accountId to verify in runtime mode")
    ap.add_argument("--sender-id", help="Optional sender open_id for allowFrom/pairing verification")
    ap.add_argument("--log-limit", type=int, default=400, help="Number of recent log lines for runtime probe")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    if args.desired:
        desired = load_json(args.desired)
        result = build_verification_checklist(desired)
    else:
        if not args.account_id:
            raise SystemExit("runtime mode requires --account-id (or provide --desired for checklist mode)")
        result = runtime_verify(args.config, args.account_id, args.sender_id, args.log_limit)

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
