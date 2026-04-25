#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple


JsonValue = Any
REDACTED_SECRET = "<redacted-at-preview>"


def load_json(path: str) -> JsonValue:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def ensure_container(parent: JsonValue, token: str, next_token: str) -> JsonValue:
    if isinstance(parent, dict):
        key = decode_pointer_token(token)
        if key not in parent or parent[key] is None:
            parent[key] = [] if next_token in {"-"} or next_token.isdigit() else {}
        return parent[key]
    if isinstance(parent, list):
        index = int(token)
        while len(parent) <= index:
            parent.append(None)
        if parent[index] is None:
            parent[index] = [] if next_token in {"-"} or next_token.isdigit() else {}
        return parent[index]
    raise TypeError(f"Cannot traverse into non-container at token: {token}")


def apply_add_op(document: JsonValue, path: str, value: JsonValue) -> JsonValue:
    if path == "":
        return value
    if not path.startswith("/"):
        raise ValueError(f"Unsupported JSON pointer: {path}")

    tokens = [decode_pointer_token(t) for t in path.lstrip("/").split("/")]
    current = document

    for i, token in enumerate(tokens[:-1]):
        next_token = tokens[i + 1]
        current = ensure_container(current, token, next_token)

    final_token = tokens[-1]
    if isinstance(current, dict):
        current[final_token] = value
        return document
    if isinstance(current, list):
        if final_token == "-":
            current.append(value)
        else:
            current.insert(int(final_token), value)
        return document
    raise TypeError(f"Cannot apply add op at non-container path: {path}")


def build_backup_path(config_path: Path) -> Path:
    stamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return config_path.with_name(f"{config_path.name}.bak-{stamp}-feishu-agent-ops")


def load_secrets_map(path: str | None) -> Dict[str, str]:
    if not path:
        return {}

    payload = load_json(path)
    accounts = payload.get("accounts") or {}
    if not isinstance(accounts, dict) or not accounts:
        raise ValueError("Secrets file must contain a non-empty 'accounts' object")

    secrets_map: Dict[str, str] = {}
    for account_id, account_payload in accounts.items():
        if not isinstance(account_payload, dict):
            raise ValueError(f"accounts.{account_id} must be an object")
        app_secret = account_payload.get("appSecret")
        if not isinstance(app_secret, str) or not app_secret:
            raise ValueError(f"accounts.{account_id}.appSecret must be a non-empty string")
        secrets_map[str(account_id)] = app_secret

    return secrets_map


def extract_account_id_from_account_path(path: str) -> str | None:
    prefix = "/channels/feishu/accounts/"
    if not path.startswith(prefix):
        return None
    suffix = path[len(prefix):]
    if not suffix or "/" in suffix:
        return None
    return decode_pointer_token(suffix)


def resolve_redacted_secrets(
    json_ops: List[Dict[str, Any]], secrets_map: Dict[str, str]
) -> Tuple[List[Dict[str, Any]], List[str], int]:
    resolved_ops = deepcopy(json_ops)
    missing_accounts: List[str] = []
    resolved_count = 0

    for op in resolved_ops:
        account_id = extract_account_id_from_account_path(op.get("path") or "")
        if not account_id:
            continue

        value = op.get("value")
        if not isinstance(value, dict):
            continue

        if value.get("appSecret") != REDACTED_SECRET:
            continue

        secret = secrets_map.get(account_id)
        if secret:
            value["appSecret"] = secret
            resolved_count += 1
        else:
            missing_accounts.append(account_id)

    return resolved_ops, sorted(set(missing_accounts)), resolved_count


def apply_patch_preview(
    patch_preview: Dict[str, Any], config_override: str | None, secrets_override: str | None, execute: bool
) -> Dict[str, Any]:
    raw_config_path = config_override or patch_preview.get("configPath") or "~/.openclaw/openclaw.json"
    config_path = Path(raw_config_path).expanduser()
    original_json_ops = patch_preview.get("jsonPatchPreview") or []
    fs_ops = patch_preview.get("filesystemPreview") or []
    warnings: List[str] = list(patch_preview.get("warnings") or [])

    secrets_map = load_secrets_map(secrets_override)
    json_ops, missing_secret_accounts, resolved_secret_count = resolve_redacted_secrets(original_json_ops, secrets_map)

    if missing_secret_accounts and execute:
        missing_str = ", ".join(missing_secret_accounts)
        raise ValueError(
            f"Missing real appSecret for accounts: {missing_str}. "
            "Provide --secrets <path> with an accounts.<accountId>.appSecret map before --execute."
        )

    if secrets_override and missing_secret_accounts:
        warnings.append(
            "secrets file did not cover all redacted appSecret entries: " + ", ".join(missing_secret_accounts)
        )

    if secrets_override and resolved_secret_count == 0:
        warnings.append("secrets file was provided but no redacted appSecret entries were matched")

    existed_before = config_path.exists()
    if existed_before:
        document = load_json(str(config_path))
    else:
        document = {}
        warnings.append("config file did not exist before apply; starting from empty object")

    applied_json_ops = 0
    applied_fs_ops = 0

    for op in json_ops:
        if op.get("op") != "add":
            raise ValueError(f"Unsupported patch op: {op.get('op')}")
        document = apply_add_op(document, op["path"], op.get("value"))
        applied_json_ops += 1

    created_paths: List[str] = []
    for op in fs_ops:
        if op.get("op") != "mkdir":
            raise ValueError(f"Unsupported filesystem op: {op.get('op')}")
        fs_path = Path(op["path"]).expanduser()
        created_paths.append(str(fs_path))
        applied_fs_ops += 1

    backup_path = build_backup_path(config_path)

    if execute:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if existed_before:
            shutil.copy2(config_path, backup_path)
        for fs_path_str in created_paths:
            Path(fs_path_str).mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        status = "applied"
    else:
        status = "ready"

    return {
        "status": status,
        "configPath": str(config_path),
        "backupPath": str(backup_path) if existed_before else None,
        "summary": {
            "jsonOpsApplied": applied_json_ops,
            "filesystemOpsApplied": applied_fs_ops,
            "configExistedBefore": existed_before,
            "resolvedSecretsApplied": resolved_secret_count,
        },
        "createdPaths": created_paths,
        "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply patch preview to config and filesystem.")
    ap.add_argument("--patch-preview", required=True, help="Path to patch-preview JSON")
    ap.add_argument("--config", help="Override target config path")
    ap.add_argument("--secrets", help="Path to secret map JSON used to restore redacted appSecret values")
    ap.add_argument("--execute", action="store_true", help="Actually write config and create directories")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    patch_preview = load_json(args.patch_preview)
    result = apply_patch_preview(patch_preview, args.config, args.secrets, args.execute)

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
