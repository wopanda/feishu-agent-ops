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


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def safe_run(cmd: List[str], timeout: int = 8) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }


def parse_openclaw_version(text: str) -> Dict[str, Optional[str]]:
    m = re.search(r"OpenClaw\s+([^\s]+)(?:\s+\(([^)]+)\))?", text or "")
    if not m:
        return {"raw": text or None, "version": None, "commit": None}
    return {
        "raw": text,
        "version": m.group(1),
        "commit": m.group(2),
    }


def read_package_json(path: str) -> Optional[Dict[str, Any]]:
    p = Path(expand(path))
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None
    return {
        "path": str(p),
        "name": data.get("name"),
        "version": data.get("version"),
    }


def list_existing(paths: List[str]) -> List[str]:
    out = []
    for raw in paths:
        p = Path(expand(raw))
        if p.exists():
            out.append(str(p))
    return out


def classify_config_shape(feishu_cfg: Dict[str, Any]) -> str:
    has_top_level_creds = bool(feishu_cfg.get("appId") or feishu_cfg.get("appSecret"))
    has_accounts = bool(feishu_cfg.get("accounts"))
    if has_top_level_creds and has_accounts:
        return "mixed-credential-shape"
    if has_accounts:
        return "accounts-multi"
    if has_top_level_creds:
        return "top-level-credentials"
    return "minimal-or-empty"


def detect_active_plugin(plugin_entries: Dict[str, Any], lark_pkg: Optional[Dict[str, Any]], legacy_pkg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    feishu_entry = plugin_entries.get("feishu") or {}
    lark_entry = plugin_entries.get("openclaw-lark") or {}
    feishu_enabled = bool(feishu_entry.get("enabled"))
    lark_enabled = bool(lark_entry.get("enabled"))

    if lark_enabled and not feishu_enabled:
        active = "openclaw-lark"
    elif feishu_enabled and not lark_enabled:
        active = "feishu"
    elif lark_enabled and feishu_enabled:
        active = "ambiguous-both-enabled"
    elif lark_pkg and not feishu_enabled:
        active = "openclaw-lark-installed-but-disabled"
    elif legacy_pkg and not lark_enabled:
        active = "feishu-installed-but-disabled"
    else:
        active = "unknown"

    return {
        "active": active,
        "legacyFeishuEnabled": feishu_enabled,
        "openclawLarkEnabled": lark_enabled,
        "entriesPresent": {
            "feishu": "feishu" in plugin_entries,
            "openclaw-lark": "openclaw-lark" in plugin_entries,
        },
    }


def collect_binding_info(bindings: List[Dict[str, Any]]) -> Dict[str, Any]:
    feishu_bindings = []
    binding_accounts = []
    peer_group_bindings = 0
    for binding in bindings:
        match = binding.get("match") or {}
        if match.get("channel") != "feishu":
            continue
        feishu_bindings.append(binding)
        if match.get("accountId") is not None:
            binding_accounts.append(match.get("accountId"))
        peer = match.get("peer") or {}
        if peer.get("kind") == "group":
            peer_group_bindings += 1
    return {
        "feishuBindings": feishu_bindings,
        "bindingAccounts": binding_accounts,
        "groupBindingCount": peer_group_bindings,
    }


def build_risk_flags(
    dm_scope: Optional[str],
    accounts: Dict[str, Any],
    binding_accounts: List[str],
    active_plugin: Dict[str, Any],
    legacy_pkg: Optional[Dict[str, Any]],
    lark_pkg: Optional[Dict[str, Any]],
    feishu_cfg: Dict[str, Any],
) -> List[str]:
    flags = []
    nondefault_accounts = {k: v for k, v in (accounts or {}).items() if k != "default"}
    missing_binding_accounts = sorted([k for k in nondefault_accounts if k not in binding_accounts])
    dangling_binding_accounts = sorted([acc for acc in binding_accounts if acc not in nondefault_accounts and acc not in (None, "default")])

    if len(nondefault_accounts) > 1 and dm_scope != "per-account-channel-peer":
        flags.append("dmScope_not_per_account_channel_peer")
    if missing_binding_accounts:
        flags.append("accounts_without_bindings")
    if dangling_binding_accounts:
        flags.append("bindings_to_missing_accounts")
    if legacy_pkg and lark_pkg:
        flags.append("legacy_and_lark_both_present")
    if active_plugin["legacyFeishuEnabled"] and active_plugin["openclawLarkEnabled"]:
        flags.append("both_plugins_enabled")

    has_top_level_creds = bool(feishu_cfg.get("appId") or feishu_cfg.get("appSecret"))
    has_accounts = bool(feishu_cfg.get("accounts"))
    if has_top_level_creds and has_accounts:
        flags.append("mixed_credential_shape")

    default_cfg = (accounts or {}).get("default") or {}
    if "default" in (accounts or {}) and not has_top_level_creds and not default_cfg.get("appId") and not default_cfg.get("appSecret"):
        flags.append("empty_default_account_placeholder")

    if active_plugin["active"] in {"unknown", "ambiguous-both-enabled"}:
        flags.append("plugin_selection_ambiguous")

    return sorted(set(flags))


def classify_compat_mode(
    active_plugin: Dict[str, Any],
    risk_flags: List[str],
    feishu_cfg: Dict[str, Any],
) -> str:
    has_feishu_cfg = bool(feishu_cfg)
    active = active_plugin["active"]

    if not has_feishu_cfg and active in {"unknown", "feishu-installed-but-disabled", "openclaw-lark-installed-but-disabled"}:
        return "broken-state"
    if active == "feishu" and "legacy_and_lark_both_present" not in risk_flags:
        return "old-feishu"
    if active == "openclaw-lark" and not any(flag in risk_flags for flag in ["legacy_and_lark_both_present", "mixed_credential_shape", "plugin_selection_ambiguous"]):
        return "official-lark"
    if active in {"openclaw-lark", "feishu", "ambiguous-both-enabled"} and has_feishu_cfg:
        return "mixed-transition"
    return "broken-state"


def main() -> None:
    ap = argparse.ArgumentParser(description="Scan OpenClaw + Feishu/Lark compatibility and config-shape drift.")
    ap.add_argument("--config", default="~/.openclaw/openclaw.json", help="Path to openclaw.json")
    ap.add_argument("--text", action="store_true", help="Print a human-readable summary instead of JSON")
    args = ap.parse_args()

    config_path = Path(expand(args.config)).resolve()
    obj = load_json(config_path)

    plugins = ((obj.get("plugins") or {}).get("entries") or {})
    session = obj.get("session") or {}
    bindings = obj.get("bindings") or []
    feishu_cfg = ((obj.get("channels") or {}).get("feishu") or {})
    accounts = feishu_cfg.get("accounts") or {}

    openclaw_bin = shutil.which("openclaw")
    openclaw_version_raw = safe_run([openclaw_bin or "openclaw", "--version"]) if openclaw_bin or shutil.which("openclaw") else {"ok": False, "stdout": "", "stderr": "openclaw binary not found"}
    openclaw_version = parse_openclaw_version(openclaw_version_raw.get("stdout", ""))

    legacy_pkg = read_package_json("~/.openclaw/extensions/feishu/package.json")
    lark_pkg = read_package_json("~/.openclaw/extensions/openclaw-lark/package.json")
    bundled_openclaw_paths = sorted(glob.glob(expand("~/.local/share/pnpm/global/5/.pnpm/openclaw@*/node_modules/openclaw/package.json")))
    bundled_openclaw_pkg = None
    if bundled_openclaw_paths:
        bundled_openclaw_pkg = read_package_json(bundled_openclaw_paths[-1])

    active_plugin = detect_active_plugin(plugins, lark_pkg, legacy_pkg)
    binding_info = collect_binding_info(bindings)
    risk_flags = build_risk_flags(
        dm_scope=session.get("dmScope"),
        accounts=accounts,
        binding_accounts=binding_info["bindingAccounts"],
        active_plugin=active_plugin,
        legacy_pkg=legacy_pkg,
        lark_pkg=lark_pkg,
        feishu_cfg=feishu_cfg,
    )
    compat_mode = classify_compat_mode(active_plugin, risk_flags, feishu_cfg)

    report = {
        "config": str(config_path),
        "openclaw": {
            "bin": openclaw_bin,
            "version": openclaw_version.get("version"),
            "commit": openclaw_version.get("commit"),
            "raw": openclaw_version.get("raw"),
            "packageVersion": (bundled_openclaw_pkg or {}).get("version"),
            "packagePath": (bundled_openclaw_pkg or {}).get("path"),
        },
        "feishuPlugin": {
            **active_plugin,
            "legacyPackage": legacy_pkg,
            "openclawLarkPackage": lark_pkg,
            "duplicatePluginRisk": bool(legacy_pkg and lark_pkg),
            "globalExtensionPaths": list_existing([
                "~/.openclaw/extensions/feishu/package.json",
                "~/.openclaw/extensions/openclaw-lark/package.json",
            ]),
        },
        "configShape": {
            "sessionDmScope": session.get("dmScope"),
            "channelsFeishuTopLevelKeys": sorted(feishu_cfg.keys()),
            "shape": classify_config_shape(feishu_cfg),
            "accountsCount": len(accounts),
            "nondefaultAccountsCount": len([k for k in accounts.keys() if k != "default"]),
            "bindingsCount": len(bindings),
            "feishuBindingsCount": len(binding_info["feishuBindings"]),
            "groupBindingCount": binding_info["groupBindingCount"],
        },
        "compatMode": compat_mode,
        "riskFlags": risk_flags,
        "notes": {
            "why": "Run this scan before diagnose/repair/apply when OpenClaw version, plugin chain, or field shape may differ.",
            "modes": {
                "old-feishu": "Legacy feishu plugin is the main active chain.",
                "official-lark": "Official openclaw-lark plugin is the main active chain with no obvious transition drift.",
                "mixed-transition": "Looks like a migration or mixed environment; inspect field shape and plugin chain before patching.",
                "broken-state": "Active plugin/config shape cannot be determined cleanly; do not patch blindly.",
            },
        },
    }

    if args.text:
        print("OpenClaw / Feishu Compatibility Scan")
        print(f"- config: {report['config']}")
        print(f"- openclaw version: {report['openclaw']['version']} ({report['openclaw']['commit']})")
        print(f"- active plugin: {report['feishuPlugin']['active']}")
        print(f"- compat mode: {report['compatMode']}")
        print(f"- session.dmScope: {report['configShape']['sessionDmScope']}")
        print(f"- feishu top-level keys: {', '.join(report['configShape']['channelsFeishuTopLevelKeys'])}")
        print(f"- accounts: {report['configShape']['accountsCount']}")
        print(f"- bindings: {report['configShape']['bindingsCount']}")
        if report['riskFlags']:
            print(f"- risk flags: {', '.join(report['riskFlags'])}")
        else:
            print("- risk flags: none")
        return

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
