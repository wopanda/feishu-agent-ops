#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

SEV_ORDER = {"P1": 1, "P2": 2, "P3": 3, "INFO": 4}


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def add_issue(issues: List[Dict[str, Any]], severity: str, code: str, title: str, evidence: str, fix: str) -> None:
    issues.append({
        "severity": severity,
        "code": code,
        "title": title,
        "evidence": evidence,
        "fix": fix,
    })


def find_duplicates(values: List[str]) -> List[str]:
    seen = set()
    dup = set()
    for v in values:
        if not v:
            continue
        if v in seen:
            dup.add(v)
        seen.add(v)
    return sorted(dup)


def validate_plan(request: Dict[str, Any], desired: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    planned_agents = desired.get("plannedAgents") or []
    planned_accounts = desired.get("plannedAccounts") or []
    planned_bindings = desired.get("plannedBindings") or []
    scenario = desired.get("scenario")
    routing_mode = desired.get("routingMode")
    agent_mode = desired.get("agentMode")
    request_bots = request.get("bots") or []
    desired_warnings = desired.get("warnings") or []

    noop_existing = (
        scenario in {"bootstrap", "expand"}
        and bool(request_bots)
        and not planned_agents
        and not planned_accounts
        and not planned_bindings
        and any("already exists" in str(w) for w in desired_warnings)
    )

    dup_agents = find_duplicates([a.get("id") for a in planned_agents])
    if dup_agents:
        add_issue(issues, "P1", "duplicate_agent_ids", "plannedAgents 中存在重复 agentId", f"duplicate agent ids = {dup_agents}", "修正 agentId 生成规则，确保 plannedAgents 中每个 id 唯一。")

    dup_accounts = find_duplicates([a.get("accountId") for a in planned_accounts])
    if dup_accounts:
        add_issue(issues, "P1", "duplicate_account_ids", "plannedAccounts 中存在重复 accountId", f"duplicate account ids = {dup_accounts}", "修正 accountId，确保新增账号唯一。")

    binding_pairs = [f"{b.get('accountId')}->{b.get('agentId')}:{b.get('routingKind')}" for b in planned_bindings]
    dup_bindings = find_duplicates(binding_pairs)
    if dup_bindings:
        add_issue(issues, "P1", "duplicate_bindings", "plannedBindings 中存在重复 binding", f"duplicate bindings = {dup_bindings}", "去重 plannedBindings，避免同一 routing 被重复写入。")

    if routing_mode == "group":
        missing_chat = [b for b in planned_bindings if b.get("routingKind") == "group" and not b.get("chatId")]
        if missing_chat:
            add_issue(issues, "P1", "group_binding_missing_chat_id", "群聊路由缺少 chatId", f"group bindings without chatId = {len(missing_chat)}", "为 group routing 提供 chatId，否则无法生成稳定群聊绑定。")

    if agent_mode == "bind-existing":
        request_missing_agent = [bot.get("accountId") or f"bot[{idx}]" for idx, bot in enumerate(request_bots) if not bot.get("agentId")]
        if request_missing_agent:
            add_issue(
                issues,
                "P1",
                "bind_existing_missing_agent_id",
                "bind-existing 模式下缺少显式 agentId",
                f"request bots missing agentId = {request_missing_agent}",
                "bind-existing 模式必须由用户或上游流程明确指定 agentId，不能由脚本自动猜测。",
            )

        missing_agent = [b for b in planned_bindings if not b.get("agentId")]
        if missing_agent:
            add_issue(
                issues,
                "P1",
                "planned_binding_missing_agent_id",
                "plannedBindings 中存在缺失 agentId 的 binding",
                f"bindings missing agentId = {len(missing_agent)}",
                "在生成 plannedBindings 前先阻断非法 bind-existing 请求。",
            )

    if scenario in {"bootstrap", "expand"} and request_bots and not planned_bindings and not noop_existing:
        add_issue(issues, "P2", "no_planned_bindings", "当前预览没有生成任何 binding", "plannedBindings is empty", "检查 request 与 observed-state 是否导致预览被全部判定为已存在。")

    if scenario in {"bootstrap", "expand"} and request_bots and not planned_accounts and not noop_existing:
        add_issue(issues, "P2", "no_planned_accounts", "当前预览没有生成任何 account", "plannedAccounts is empty while request contains bots", "确认这批 bot 是否都已存在；若只是做预览，应区分空白现场与真实现场。")

    for idx, bot in enumerate(request_bots):
        missing = [k for k in ["botName", "appId", "appSecret"] if not bot.get(k)]
        if missing:
            add_issue(issues, "P1", f"request_bot_missing_fields:{idx}", "请求中 bot 缺少必要字段", f"bots[{idx}] missing = {missing}", "补齐 botName / appId / appSecret 后再继续。")

    if any("unknown agentId" in w for w in (request.get("warnings") or [])):
        add_issue(issues, "P1", "unknown_agent_reference", "请求引用了不存在的 agentId", str(request.get("warnings")), "若是绑定已有 Agent，先从扫描结果中选择合法 agentId；否则改成 create-new。")

    status = "pass" if not issues else "fail"
    return {
        "status": status,
        "summary": {
            "issues": len(issues),
            "scenario": scenario,
            "routingMode": routing_mode,
            "agentMode": agent_mode,
            "noopExisting": noop_existing,
        },
        "issues": sorted(issues, key=lambda x: (SEV_ORDER[x["severity"]], x["code"])),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate desired-state preview before apply.")
    ap.add_argument("--request", required=True, help="Path to normalized request JSON")
    ap.add_argument("--desired", required=True, help="Path to desired-state JSON")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args()

    request = load_json(args.request)
    desired = load_json(args.desired)
    report = validate_plan(request, desired)

    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

