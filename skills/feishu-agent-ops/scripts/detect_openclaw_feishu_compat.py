#!/usr/bin/env python3
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def expand(path: str) -> str:
    return os.path.expanduser(path or "")


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None


def run_command(command: List[str]) -> Dict[str, Any]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=20)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}


def detect_openclaw_version() -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "cli_path": shutil.which("openclaw"),
        "version": None,
        "source": None,
    }

    if result["cli_path"]:
        cli = run_command(["openclaw", "--version"])
        text = cli.get("stdout") or cli.get("stderr") or ""
        m = re.search(r"OpenClaw\s+([^\s]+)", text)
        if m:
            result["version"] = m.group(1)
            result["source"] = "cli"
            result["raw"] = text
            return result

    pkg_paths = sorted(
        glob.glob(
            expand("~/.local/share/pnpm/global/5/.pnpm/openclaw@*/node_modules/openclaw/package.json")
        )
    )
    if pkg_paths:
        pkg = read_json(Path(pkg_paths[-1])) or {}
        if pkg.get("version"):
            result["version"] = pkg.get("version")
            result["source"] = "package.json"
            result["package_json"] = pkg_paths[-1]

    return result


def detect_plugin_package_version(package_path: str) -> Optional[str]:
    pkg = read_json(Path(expand(package_path)))
    if not pkg:
        return None
    return pkg.get("version")


def plugin_file_exists(base_dir: Path, plugin_name: str) -> bool:
    return (base_dir / plugin_name).exists()


def build_risk_flags(*, active_plugin: Optional[str], legacy_enabled: bool, lark_enabled: bool,
                     legacy_present: bool, lark_present: bool, dm_scope: Optional[str],
                     accounts_count: int, bindings_count: int, feishu_keys: List[str]) -> List[str]:
    flags: List[str] = []

    if active_plugin is None:
        flags.append("no_active_feishu_plugin")
    if legacy_present and lark_present:
        flags.append("duplicate_plugin_risk")
    if dm_scope != "per-account-channel-peer":
        flags.append("dm_scope_not_account_isolated")
    if accounts_count > bindings_count:
        flags.append("accounts_bindings_not_closed")
    if bindings_count > 0 and accounts_count == 0:
        flags.append("bindings_without_accounts")
    if accounts_count > 0 and not feishu_keys:
        flags.append("feishu_channel_shape_unreadable")
    if active_plugin == "openclaw-lark" and legacy_enabled:
        flags.append("legacy_feishu_still_enabled")
    if active_plugin == "feishu" and lark_enabled:
        flags.append("official_lark_also_enabled")

    return flags


def classify_compat_mode(*, active_plugin: Optional[str], legacy_present: bool, lark_present: bool,
                         legacy_enabled: bool, lark_enabled: bool, risk_flags: List[str]) -> str:
    if not active_plugin:
        return "broken-state"

    if active_plugin == "feishu" and legacy_enabled and not lark_enabled:
        return "old-feishu"

    if active_plugin == "openclaw-lark" and lark_enabled and not legacy_enabled:
        if legacy_present:
            return "mixed-transition"
        return "official-lark"

    if "duplicate_plugin_risk" in risk_flags:
        return "mixed-transition"

    return "broken-state"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Detect OpenClaw / Feishu compatibility shape before multi-agent diagnose or repair."
    )
    ap.add_argument(
        "--config",
        default="~/.openclaw/openclaw.json",
        help="Path to openclaw.json (default: ~/.openclaw/openclaw.json)",
    )
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = ap.parse_args()

    config_path = Path(expand(args.config)).resolve()
    obj = read_json(config_path)
    if obj is None:
        raise SystemExit(f"failed to read config: {config_path}")

    plugins_entries = ((obj.get("plugins") or {}).get("entries") or {})
    feishu_entry = plugins_entries.get("feishu") or {}
    lark_entry = plugins_entries.get("openclaw-lark") or {}

    channels_feishu = ((obj.get("channels") or {}).get("feishu") or {})
    accounts = channels_feishu.get("accounts") or {}
    bindings = obj.get("bindings") or []
    session_dm_scope = ((obj.get("session") or {}).get("dmScope"))

    ext_dir = Path(expand("~/.openclaw/extensions"))
    legacy_present = plugin_file_exists(ext_dir, "feishu")
    lark_present = plugin_file_exists(ext_dir, "openclaw-lark")
    legacy_enabled = bool(feishu_entry.get("enabled"))
    lark_enabled = bool(lark_entry.get("enabled"))

    active_plugin: Optional[str] = None
    if lark_enabled:
        active_plugin = "openclaw-lark"
    elif legacy_enabled:
        active_plugin = "feishu"

    plugin_versions = {
        "feishu": detect_plugin_package_version("~/.openclaw/extensions/feishu/package.json") if legacy_present else None,
        "openclaw-lark": detect_plugin_package_version("~/.openclaw/extensions/openclaw-lark/package.json") if lark_present else None,
    }

    openclaw = detect_openclaw_version()

    risk_flags = build_risk_flags(
        active_plugin=active_plugin,
        legacy_enabled=legacy_enabled,
        lark_enabled=lark_enabled,
        legacy_present=legacy_present,
        lark_present=lark_present,
        dm_scope=session_dm_scope,
        accounts_count=len(accounts),
        bindings_count=len(bindings),
        feishu_keys=sorted(channels_feishu.keys()),
    )

    compat_mode = classify_compat_mode(
        active_plugin=active_plugin,
        legacy_present=legacy_present,
        lark_present=lark_present,
        legacy_enabled=legacy_enabled,
        lark_enabled=lark_enabled,
        risk_flags=risk_flags,
    )

    result = {
        "config": str(config_path),
        "openclaw": openclaw,
        "feishu_plugin": {
            "active": active_plugin,
            "compat_mode": compat_mode,
            "legacy_feishu": {
                "present": legacy_present,
                "enabled": legacy_enabled,
                "version": plugin_versions.get("feishu"),
            },
            "openclaw_lark": {
                "present": lark_present,
                "enabled": lark_enabled,
                "version": plugin_versions.get("openclaw-lark"),
            },
        },
        "config_shape": {
            "session_dmScope": session_dm_scope,
            "feishu_top_level_keys": sorted(channels_feishu.keys()),
            "accounts_count": len(accounts),
            "bindings_count": len(bindings),
        },
        "risk_flags": risk_flags,
    }

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
