#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from normalize_request import expand, load_json as load_request_json, normalize_request  # type: ignore
from scan_current_state import scan_current_state  # type: ignore
from build_desired_state import build_desired_state  # type: ignore
from validate_plan import validate_plan  # type: ignore
from generate_patch import generate_patch_preview  # type: ignore
from verify_setup import build_verification_checklist  # type: ignore


def maybe_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def run_pipeline(request_path: str, config_path: str) -> Dict[str, Any]:
    request_obj = load_request_json(Path(expand(request_path)).resolve())
    normalized = normalize_request(request_obj)
    observed = scan_current_state(config_path)
    desired = build_desired_state(normalized, observed)
    validation = validate_plan(normalized, desired)
    patch_preview = generate_patch_preview(desired)
    verification = build_verification_checklist(desired)

    return {
        "request": normalized,
        "observed": observed,
        "desired": desired,
        "validation": validation,
        "patchPreview": patch_preview,
        "verification": verification,
        "status": validation.get("status"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run deterministic Feishu Agent Ops planning pipeline end-to-end.")
    ap.add_argument("--input", required=True, help="Path to request JSON")
    ap.add_argument("--config", default="~/.openclaw/openclaw.json", help="Path to openclaw.json")
    ap.add_argument("--output-dir", help="Optional directory to persist stage outputs")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    ap.add_argument("--no-fail-on-validation", action="store_true", help="Always exit 0 even if validation fails")
    args = ap.parse_args()

    result = run_pipeline(args.input, args.config)

    if args.output_dir:
        outdir = Path(expand(args.output_dir)).resolve()
        maybe_write_json(outdir / "normalized.json", result["request"])
        maybe_write_json(outdir / "observed.json", result["observed"])
        maybe_write_json(outdir / "desired.json", result["desired"])
        maybe_write_json(outdir / "validation.json", result["validation"])
        maybe_write_json(outdir / "patch-preview.json", result["patchPreview"])
        maybe_write_json(outdir / "verification.json", result["verification"])

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))

    if result.get("status") != "pass" and not args.no_fail_on_validation:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
