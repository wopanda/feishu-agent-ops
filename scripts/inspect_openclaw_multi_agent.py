#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def exists_path(raw: str) -> bool:
    if not raw:
        return False
    expanded = os.path.expanduser(raw)
    return Path(expanded).exists()


def main():
    ap = argparse.ArgumentParser(description='Inspect OpenClaw multi-agent / multi-Feishu configuration.')
    ap.add_argument('--config', default='~/.openclaw/openclaw.json')
    args = ap.parse_args()

    config_path = Path(os.path.expanduser(args.config))
    data = load_json(config_path)

    channels = data.get('channels', {})
    feishu = channels.get('feishu', {})
    bindings = data.get('bindings', [])
    session = data.get('session', {})
    agents = data.get('agents', {}).get('list', [])

    findings = []
    fixes = []
    facts = []

    account_ids = list((feishu.get('accounts') or {}).keys())
    feishu_binding_accounts = []
    for b in bindings:
        m = b.get('match', {})
        if m.get('channel') == 'feishu' and m.get('accountId'):
            feishu_binding_accounts.append(m.get('accountId'))

    facts.append(f'feishu accounts: {len(account_ids)} -> {account_ids}')
    facts.append(f'feishu bindings: {len(feishu_binding_accounts)} -> {feishu_binding_accounts}')
    facts.append(f'session.dmScope: {session.get("dmScope")}')

    # Root cause 1: wrong session isolation for multi-account feishu
    dm_scope = session.get('dmScope')
    if len(account_ids) > 1 and dm_scope != 'per-account-channel-peer':
        findings.append({
            'severity': 'high',
            'code': 'DM_SCOPE_NOT_PER_ACCOUNT',
            'root_cause': '多账号飞书场景下，会话隔离仍不是 per-account-channel-peer，容易导致不同机器人共享同一用户会话。',
            'evidence': dm_scope,
            'fix': 'set session.dmScope to per-account-channel-peer'
        })
        fixes.append('把 session.dmScope 从 %s 调整为 per-account-channel-peer' % dm_scope)

    # Root cause 2: default feishu account placeholder / misconfigured default
    default_account = (feishu.get('accounts') or {}).get('default')
    if 'default' in account_ids and not feishu.get('appId'):
        findings.append({
            'severity': 'medium',
            'code': 'DEFAULT_FEISHU_ACCOUNT_PLACEHOLDER',
            'root_cause': '存在 Feishu default 账号占位，但 channels.feishu 顶层没有 appId/appSecret，channels status 会显示 default not configured，易误导排障。',
            'evidence': {'default_account': default_account, 'top_level_appId': feishu.get('appId')},
            'fix': 'remove unused default placeholder or fully configure top-level default account'
        })
        fixes.append('删除未使用的 default 占位账号，或把顶层 default 账号补齐为真实可用账号')

    # Root cause 3: duplicate plugin ids warning affecting diagnosis confidence
    plugin_ids = []
    for e in data.get('plugins', {}).get('entries', []):
        if isinstance(e, dict):
            plugin_ids.append(e.get('id'))
        else:
            plugin_ids.append(e)
    if 'feishu' in plugin_ids and 'openclaw-lark' in plugin_ids:
        findings.append({
            'severity': 'medium',
            'code': 'DUPLICATE_FEISHU_PLUGIN_STACK',
            'root_cause': '同时启用了 feishu 与 openclaw-lark，且状态里已有 duplicate plugin id warning，排障时容易混淆真实生效实现。',
            'evidence': plugin_ids,
            'fix': 'pin one effective Feishu plugin path and document which plugin is authoritative'
        })
        fixes.append('明确当前真正生效的飞书插件链路，减少 duplicate plugin warning')

    # Root cause 4: every feishu account should map cleanly to exactly one agent
    account_to_agent = {}
    for b in bindings:
        m = b.get('match', {})
        if m.get('channel') == 'feishu' and m.get('accountId'):
            account_to_agent.setdefault(m.get('accountId'), []).append(b.get('agentId'))

    for aid, agent_ids in account_to_agent.items():
        if len(agent_ids) != 1:
            findings.append({
                'severity': 'high',
                'code': 'ACCOUNT_BINDING_AMBIGUOUS',
                'root_cause': '同一个 feishu accountId 绑定到了多个 agent，或存在重复路由。',
                'evidence': {aid: agent_ids},
                'fix': 'keep exactly one stable accountId -> agentId binding unless peer-level overrides are explicitly documented'
            })
            fixes.append(f'让 {aid} 只稳定绑定到一个 agent')

    # Root cause 5: workspace / agentDir missing
    known_agents = {a.get('id'): a for a in agents}
    for aid, a in known_agents.items():
        workspace = a.get('workspace')
        agent_dir = a.get('agentDir')
        if workspace and not exists_path(workspace):
            findings.append({
                'severity': 'high',
                'code': 'WORKSPACE_MISSING',
                'root_cause': 'agent 配置存在，但 workspace 目录缺失。',
                'evidence': {aid: workspace},
                'fix': 'create workspace directory or correct path'
            })
            fixes.append(f'补齐 {aid} 的 workspace: {workspace}')
        if agent_dir and not exists_path(agent_dir):
            findings.append({
                'severity': 'high',
                'code': 'AGENT_DIR_MISSING',
                'root_cause': 'agent 配置存在，但 agentDir 目录缺失。',
                'evidence': {aid: agent_dir},
                'fix': 'create agentDir or correct path'
            })
            fixes.append(f'补齐 {aid} 的 agentDir: {agent_dir}')

    summary = {
        'config': str(config_path),
        'facts': facts,
        'findings': findings,
        'fixes': fixes,
        'overall': 'ok' if not findings else 'needs_attention'
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
