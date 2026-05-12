#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable

INTERNAL_FIELD_NAMES = {
    "canProceed",
    "confirmationRequired",
    "nextAction",
    "nextQuestion",
    "modelGuardrail",
    "patchSummary",
    "missingRequiredFields",
    "validationIssues",
    "userStateLabel",
}


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _format_missing_fields(items: Iterable[Dict[str, Any]]) -> str:
    parts = []
    for item in items:
        label = item.get("botName") or item.get("accountId") or f"第 {int(item.get('botIndex') or 0) + 1} 只龙虾"
        missing = "、".join(item.get("missing") or [])
        parts.append(f"{label} 缺少：{missing}")
    return "；".join(parts)


def render_user_reply(interaction: Dict[str, Any]) -> Dict[str, Any]:
    action = interaction.get("nextAction")

    if action == "ask_apply_confirmation":
        patch = interaction.get("patchSummary") or {}
        existing = int(interaction.get("existingLobsters") or 0)
        add_accounts = int(patch.get("addAccounts") or 0)
        add_agents = int(patch.get("addAgents") or 0)
        add_bindings = int(patch.get("addBindings") or 0)
        mkdir_count = int(patch.get("mkdirCount") or 0)
        message = (
            f"我检查过了：当前已有 {existing} 只龙虾，这次只会追加 {add_accounts} 只新龙虾，不会动旧龙虾。\n\n"
            f"确认后我会新增 {add_accounts} 个飞书账号配置、{add_agents} 个 Agent、{add_bindings} 条路由绑定，并创建 {mkdir_count} 个目录。\n"
            "要现在应用吗？"
        )
        return {"message": message, "requiresUserReply": True, "safeToSend": True}

    if action == "ask_missing_required_fields":
        missing = _format_missing_fields(interaction.get("missingRequiredFields") or [])
        detail = f"目前缺少：{missing}。" if missing else "目前缺少必要信息。"
        message = (
            f"还差一点信息，先不生成新增配置。{detail}\n\n"
            "新增一只龙虾最低只需要：botName、appId、appSecret。其他字段我可以先帮你推断。"
        )
        return {"message": message, "requiresUserReply": True, "safeToSend": True}

    if action == "explain_validation_issues":
        issues = interaction.get("validationIssues") or []
        if issues:
            lines = []
            for issue in issues[:5]:
                title = issue.get("title") or issue.get("code") or "校验问题"
                fix = issue.get("fix")
                lines.append(f"- {title}" + (f"：{fix}" if fix else ""))
            issue_text = "\n".join(lines)
        else:
            issue_text = "- 校验未通过，但没有拿到具体问题。请重新生成预览。"
        message = f"新增预览没有通过校验，我不会落地配置。\n\n需要先处理：\n{issue_text}"
        return {"message": message, "requiresUserReply": False, "safeToSend": True}

    if action == "explain_noop_existing":
        message = "我检查过了：这次没有生成新增项，通常表示目标龙虾已经存在，或这次请求没有需要新增的内容。我不会重复创建已有配置。"
        return {"message": message, "requiresUserReply": False, "safeToSend": True}

    if action == "run_readonly_diagnosis":
        message = "我会先做只读检查，不直接改配置。会先看会话隔离、账号绑定、目录结构和插件运行层，再给你根因判断。"
        return {"message": message, "requiresUserReply": False, "safeToSend": True}

    message = "我已经拿到流程结果，但还缺少可展示的下一步文案；先不执行写入。"
    return {"message": message, "requiresUserReply": False, "safeToSend": False}


def assert_no_internal_fields(rendered: Dict[str, Any]) -> None:
    text = rendered.get("message") or ""
    leaked = sorted([name for name in INTERNAL_FIELD_NAMES if name in text])
    if leaked:
        raise ValueError("user-visible message leaked internal fields: " + ", ".join(leaked))


def main() -> None:
    ap = argparse.ArgumentParser(description="Render user-visible reply from interaction contract.")
    ap.add_argument("--interaction", required=True)
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument("--assert-no-internal-fields", action="store_true")
    args = ap.parse_args()

    rendered = render_user_reply(load_json(args.interaction))
    if args.assert_no_internal_fields:
        assert_no_internal_fields(rendered)
    print(json.dumps(rendered, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
