# Troubleshooting

## 常见问题

### 1. bot 已创建，但不回复
优先检查：
- `channels.feishu.accounts` 是否存在该 `accountId`
- `bindings` 是否把该 `accountId` 绑定到正确 `agentId`
- `appId / appSecret` 是否填错
- 是否完成真实飞书侧接入与权限配置

### 2. 回复了，但走错 Agent
优先检查：
- `bindings` 优先级
- 是否有默认 Agent 抢路由
- 是否存在更具体的 `peer` 匹配规则

### 3. 多个 bot 串会话
优先检查：
- `session.dmScope` 是否为 `per-account-channel-peer`
- 是否把多个账号错误地共享到了同一条会话策略

### 4. 配置写进去了，但目录不完整
优先检查：
- `workspace-*` 是否存在
- `agents/<id>/agent` 是否存在
- 是否只 patch 了配置，没有补目录

## 处理原则
- 先 inspect，再 repair
- 先最小修复，不大范围重写
- 没证据，不说已恢复
