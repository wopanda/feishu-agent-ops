#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List


JsonValue = Any


def load_json(path: str) -> JsonValue:
    return json.loads(Path(path).read_text())


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


def apply_patch_preview(patch_preview: Dict[str, Any], config_override: str | None, execute: bool) -> Dict[str, Any]:
    raw_config_path = config_override or patch_preview.get("configPath") or "~/.openclaw/openclaw.json"
    config_path = Path(raw_config_path).expanduser()
    json_ops = patch_preview.get("jsonPatchPreview") or []
    fs_ops = patch_preview.get("filesystemPreview") or []
    warnings: List[str] = list(patch_preview.get("warnings") or [])

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
        },
        "createdPaths": created_paths,
        "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply patch preview to config and filesystem.")
    ap.add_argument("--patch-preview", required=True, help="Path to patch-preview JSON")
    ap.add_argument("--config", help="Override target config path")
    ap.add_argument("--execute", action="store_true", help="Actually write config and create directories")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    patch_preview = load_json(args.patch_preview)
    result = apply_patch_preview(patch_preview, args.config, args.execute)

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
