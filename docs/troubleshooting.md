# Troubleshooting

## 常见问题

### 0. 接入过程跑很久，还连续出 JSON 错
优先检查：
- 是否让 LLM 同时跑了两套 plan 链（如 `bind-existing` 与 `create-new`）
- 是否存在单入口流水线；若没有，应统一改为 `run_plan_pipeline.py`
- 每一阶段输出是否都做了 schema / 结构校验，失败后是否立即停止

处理原则：
- 新增 / 扩容类请求只允许一条确定性流水线
- `validate_plan` fail 时直接停，不继续让 LLM 手工补洞

### 1. bot 已创建，但不回复
优先检查：
- `channels.feishu.accounts` 是否存在该 `accountId`
- `bindings` 是否把该 `accountId` 绑定到正确 `agentId`
- `appId / appSecret` 是否填错
- 是否完成真实飞书侧接入与权限配置
- **是否出现 `not paired` / `sender not allowed`，以及 allowFrom / pairing 是否命中真实 sender**
- `allowFrom / pairing` 是否放行了**真实入站 sender_id**（日志若出现 `not paired`，先查这里）

### 2. 回复了，但走错 Agent
优先检查：
- `bindings` 优先级
- 是否有默认 Agent 抢路由
- 是否存在更具体的 `peer` 匹配规则

### 3. 多个 bot 串会话
优先检查：
- `session.dmScope` 是否为 `per-account-channel-peer`
- 是否把多个账号错误地共享到了同一条会话策略

### 4. `openclaw status` 显示 Feishu `accounts 6/7`
不要直接下结论说“少了一个 binding”。
先区分：
- `default` 是否只是占位账号
- 非 default 账号是否都已有 binding
- 顶层 `appId / appSecret` 是否为空

### 5. 配置写进去了，但目录不完整
优先检查：
- `workspace-*` 是否存在
- `agents/<id>/agent` 是否存在
- 是否只 patch 了配置，没有补目录

### 6. 明明配置对了，但行为还是怪
优先检查：
- 插件重复覆盖告警
- 是否存在全局扩展覆盖 bundled 插件
- 排障是不是只看了 `openclaw.json`，没看插件层

## 处理原则
- 先 inspect，再 repair
- 先修高频根因，再修表象
- 先最小修复，不大范围重写
- 没证据，不说已恢复
