# Root Cause Analysis

## 这版 skill 为什么对多 Agent / 多小龙虾异常修复不够强

根因不是“不会写 README”，而是产品重心放偏了。

### 根因 1：过度偏向部署，低估了运行态异常
第一版更像“接入/扩容说明”，而不是“异常修复作战手册”。
它会讲：
- 怎么新增 agent
- 怎么扩容 bot
- 怎么写 bindings

但它没有把真实高频异常的排查顺序写死。

### 根因 2：没有把真实环境证据变成默认检查项
当前环境里已经能看到几个非常典型的多 Agent 风险：

- `session.dmScope` 当前是 `per-channel-peer`
- Feishu 账号数为 `7`，但 bindings 只有 `6`
- `openclaw status` 显示 Feishu 为 `accounts 6/7`
- 存在 `plugin feishu: duplicate plugin id detected` 告警

这些都属于“多 Agent 真实异常”的高优先级根因，但第一版 skill 还没有把它们变成 inspect / repair 的默认主链。

### 根因 3：repair 设计过于抽象
第一版只写了“repair 支持最小修复”，但没具体规定：
- 先查什么
- 再查什么
- 哪些是一级根因
- 哪些是表象
- 哪些修复可以自动做，哪些必须先停

结果是 repair 更像概念，不像可执行 playbook。

### 根因 4：没有把“账号层、路由层、会话层、插件层”拆开
多 Agent 异常常常不是一个点，而是四层问题混在一起：

1. 账号层：account 存在不存在，配置完整不完整
2. 路由层：binding 是否覆盖、是否丢失、是否抢路由
3. 会话层：`dmScope` 是否导致串会话
4. 插件层：插件冲突、覆盖、版本混装

第一版 skill 没把这四层拆开，所以很容易泛泛而谈。

---

## 当前确认到的高优先级真实风险

### 风险 1：`dmScope` 不适合多账号隔离
当前环境：
- `session.dmScope = per-channel-peer`

这意味着：
- 同一 channel 下不同账号可能没有做到完全隔离
- 对“多飞书机器人 -> 多 Agent”场景来说，不是最稳妥配置

多账号场景更推荐：
- `per-account-channel-peer`

### 风险 2：账号数与 bindings 数不一致
当前环境：
- Feishu accounts: `7`
- bindings: `6`
- `openclaw status` 显示：`accounts 6/7`

这意味着至少有一个账号没有形成完整路由闭环。

### 风险 3：插件重复覆盖
当前环境告警：
- `plugin feishu: duplicate plugin id detected`
- `plugin qqbot: duplicate plugin id detected`

这意味着：
- 运行时插件来源可能存在覆盖关系
- 渠道行为可能不是用户直觉中的“官方默认那份”
- 多 Agent 故障排查时，不能只看 `openclaw.json`，还要看插件层是否被覆盖

---

## 修复版 skill 应该如何调整

### 1. 把 inspect 变成“证据优先的固定顺序”
默认先查：
1. `openclaw status`
2. `session.dmScope`
3. Feishu accounts 数 vs bindings 数
4. 默认 Agent / accountId / agentId 映射
5. workspace / agentDir 完整性
6. 插件重复与覆盖告警
7. 再看日志

### 2. 把 repair 变成“分层修复”
按顺序修：
1. 先修配置缺口
2. 再修路由错配
3. 再修会话隔离
4. 再修目录缺失
5. 最后才碰插件层和更深问题

### 3. 把高频根因写进首页
至少要让用户一眼知道：
- `dmScope` 是高频根因
- `accounts != bindings` 是高频根因
- 插件重复覆盖是高频根因

### 4. 把“自动修”和“先确认再修”分开
例如：
- 自动可修：缺少 binding、缺少目录、缺少 agentDir
- 先确认再修：修改 `dmScope`、调整默认 Agent、处理插件层
