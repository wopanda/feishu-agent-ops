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

## 默认根因排查顺序
1. `openclaw status`
2. `session.dmScope`
3. Feishu `accounts` 数与 `bindings` 数是否闭环
4. `accountId -> agentId` 是否一一稳定映射
5. `workspace / agentDir` 是否齐全
6. 插件重复覆盖告警
7. 最后再看日志

## 当前现场已识别的高频根因

### 根因 1：多账号飞书仍使用 `per-channel-peer`
这会让不同机器人下的同一用户仍可能共享会话，导致串小龙虾、串记忆。

### 根因 2：存在误导性的 Feishu `default` 占位账号
状态里会显示 `default not configured`，容易让人误判成某个机器人少配了，但实际上它可能只是占位对象。

### 根因 3：飞书插件链路重复覆盖
同时存在 `feishu` 与 `openclaw-lark`，而 CLI 已报 duplicate plugin warning。排障时如果不先钉死真实生效插件，后面很多修法都可能漂。

## 处理原则
- 先 inspect，再 root-cause，再 repair
- 先最小修复，不大范围重写
- 没证据，不说已恢复
- 先修高频根因，再碰深层问题
