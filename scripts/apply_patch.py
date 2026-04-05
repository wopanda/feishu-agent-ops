#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def build_backup_path(config_path: str) -> str:
    now = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return f"{config_path}.bak-{now}-feishu-agent-ops"


def build_apply_plan(patch_preview: Dict[str, Any]) -> Dict[str, Any]:
    config_path = patch_preview.get("configPath") or "~/.openclaw/openclaw.json"
    backup_path = build_backup_path(config_path)
    fs_ops = patch_preview.get("filesystemPreview") or []
    json_ops = patch_preview.get("jsonPatchPreview") or []

    steps: List[Dict[str, Any]] = [
        {
            "step": 1,
            "action": "backup-config",
            "target": config_path,
            "output": backup_path,
            "requiresConfirmation": False,
        },
        {
            "step": 2,
            "action": "review-json-patch",
            "target": config_path,
            "count": len(json_ops),
            "requiresConfirmation": True,
        },
        {
            "step": 3,
            "action": "prepare-directories",
            "count": len(fs_ops),
            "requiresConfirmation": False,
        },
        {
            "step": 4,
            "action": "apply-config-patch",
            "target": config_path,
            "count": len(json_ops),
            "requiresConfirmation": True,
        },
        {
            "step": 5,
            "action": "verify-after-apply",
            "target": "at least one target bot response + config sanity",
            "requiresConfirmation": False,
        },
    ]

    return {
        "mode": "dry-run",
        "configPath": config_path,
        "backupPlan": {
            "source": config_path,
            "backup": backup_path,
        },
        "summary": patch_preview.get("summary") or {},
        "steps": steps,
        "warnings": patch_preview.get("warnings") or [],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build dry-run apply plan from patch preview.")
    ap.add_argument("--patch-preview", required=True, help="Path to patch-preview JSON")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    patch_preview = load_json(args.patch_preview)
    apply_plan = build_apply_plan(patch_preview)

    if args.pretty:
        print(json.dumps(apply_plan, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(apply_plan, ensure_ascii=False))


if __name__ == "__main__":
    main()
