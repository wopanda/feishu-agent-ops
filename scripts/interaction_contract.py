#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _missing_required_bot_fields(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    missing_items: List[Dict[str, Any]] = []
    for idx, bot in enumerate(request.get("bots") or []):
        missing = [field for field in ["botName", "appId", "appSecret"] if not bot.get(field)]
        if missing:
            missing_items.append({
                "botIndex": idx,
                "accountId": bot.get("accountId"),
                "botName": bot.get("botName"),
                "missing": missing,
            })
    return missing_items


def _summarize_patch(patch_preview: Dict[str, Any]) -> Dict[str, int]:
    summary = patch_preview.get("summary") or {}
    return {
        "addAccounts": int(summary.get("addAccounts") or 0),
        "addAgents": int(summary.get("addAgents") or 0),
        "addBindings": int(summary.get("addBindings") or 0),
        "mkdirCount": int(summary.get("mkdirCount") or 0),
    }


def build_interaction_contract(
    request: Dict[str, Any],
    observed: Dict[str, Any],
    desired: Dict[str, Any],
    validation: Dict[str, Any],
    patch_preview: Dict[str, Any],
) -> Dict[str, Any]:
    scenario = request.get("scenario") or desired.get("scenario")
    missing_required = _missing_required_bot_fields(request)
    validation_status = validation.get("status")
    patch_summary = _summarize_patch(patch_preview)
    collab_summary = ((observed.get("collabReadiness") or {}).get("summary") or {})
    existing_lobsters = int(collab_summary.get("nondefaultEnabledAccounts") or 0)
    planned_total = patch_summary["addAccounts"] + patch_summary["addAgents"] + patch_summary["addBindings"]

    if scenario == "diagnose":
        return {
            "mode": "diagnose",
            "userStateLabel": "排查 / 修复",
            "canProceed": True,
            "confirmationRequired": False,
            "nextAction": "run_readonly_diagnosis",
            "nextQuestion": None,
            "replyBullets": [
                "我会先做只读扫描，不直接改配置。",
                "先判断会话隔离、账号绑定、目录结构和插件运行层。",
            ],
            "modelGuardrail": "LLM 只能解释扫描结果；不能在扫描失败时自行脑补修复 patch。",
        }

    if missing_required:
        return {
            "mode": "expand",
            "userStateLabel": "新增 / 扩容",
            "canProceed": False,
            "confirmationRequired": False,
            "nextAction": "ask_missing_required_fields",
            "nextQuestion": "请补齐 botName、appId、appSecret 这 3 项；其他字段我可以先帮你推断。",
            "missingRequiredFields": missing_required,
            "replyBullets": [
                "新增一只龙虾最低只需要 botName、appId、appSecret。",
                "accountId / agentId / roleName 默认后置，能推断就不追问。",
            ],
            "modelGuardrail": "LLM 不得额外追问 accountId 或 agentId，除非用户明确要求绑定已有 Agent 或存在冲突。",
        }

    if validation_status != "pass":
        return {
            "mode": "expand",
            "userStateLabel": "新增 / 扩容",
            "canProceed": False,
            "confirmationRequired": False,
            "nextAction": "explain_validation_issues",
            "nextQuestion": None,
            "replyBullets": [
                "新增预览没有通过校验，先不落地。",
                "需要先处理 validation issues，再重新生成预览。",
            ],
            "validationIssues": validation.get("issues") or [],
            "modelGuardrail": "LLM 必须按 validation issues 解释，不能绕过校验继续 apply。",
        }

    if planned_total == 0:
        return {
            "mode": "expand",
            "userStateLabel": "新增 / 扩容",
            "canProceed": True,
            "confirmationRequired": False,
            "nextAction": "explain_noop_existing",
            "nextQuestion": None,
            "replyBullets": [
                "这次没有生成新增项，通常表示目标龙虾已经存在或请求是空操作。",
                "我不会重复创建已有 account / agent / binding。",
            ],
            "modelGuardrail": "LLM 需要解释 noop 原因，不得说成已新增。",
        }

    return {
        "mode": "expand",
        "userStateLabel": "新增 / 扩容",
        "canProceed": True,
        "confirmationRequired": True,
        "nextAction": "ask_apply_confirmation",
        "nextQuestion": "预览已通过。确认后我再写配置、建目录，并生成验证清单。是否现在应用？",
        "existingLobsters": existing_lobsters,
        "patchSummary": patch_summary,
        "replyBullets": [
            f"当前检测到 {existing_lobsters} 只已启用龙虾；旧龙虾不动。",
            f"本次准备新增 {patch_summary['addAccounts']} 个 account、{patch_summary['addAgents']} 个 agent、{patch_summary['addBindings']} 条 binding。",
            "真正写配置前必须用户确认。",
        ],
        "modelGuardrail": "LLM 只能基于 patchSummary 汇报预览；未确认前不得调用 apply。",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build deterministic user interaction contract from pipeline outputs.")
    ap.add_argument("--request", required=True)
    ap.add_argument("--observed", required=True)
    ap.add_argument("--desired", required=True)
    ap.add_argument("--validation", required=True)
    ap.add_argument("--patch-preview", required=True)
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args()

    result = build_interaction_contract(
        load_json(args.request),
        load_json(args.observed),
        load_json(args.desired),
        load_json(args.validation),
        load_json(args.patch_preview),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
