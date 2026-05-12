# Multi-Agent Root Cause Examples

## 当前环境中已经观察到的高频风险示例

### 示例 1：`session.dmScope` 不够细
- 当前值：`per-channel-peer`
- 多账号飞书场景更稳妥的目标值：`per-account-channel-peer`
- 风险：不同飞书账号下的会话隔离不够彻底，容易出现串上下文或排障误判。

### 示例 2：Feishu status 显示 `accounts 6/7`
- 这不一定等于“少了一个 binding”
- 当前环境里实际 6 个非 default 账号都已有 binding
- 这里更像是：`default` 账号占位存在，但没有有效凭据
- 说明：异常排查时，不能只看总数，还要区分 `default` 与实际启用账号

### 示例 3：插件重复覆盖告警
- 已观察到 `plugin feishu: duplicate plugin id detected`
- 这意味着运行时插件可能被全局扩展覆盖
- 排障不能只看 `openclaw.json`，还要把插件层纳入一级检查
