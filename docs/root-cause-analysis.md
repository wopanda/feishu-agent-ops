# Root Cause Analysis

## 这类 skill 之前为什么“看起来能修”，但不够会修

根本问题不是没有写到 `repair`。
而是之前的设计更像：

- 配置说明
- 常见问题清单
- 修复建议集合

但还不够像：

- **根因诊断器**
- **证据驱动的修复编排器**

这会导致一个典型后果：

> 看起来列了很多修法，但真正遇到“多小龙虾偶发异常、串会话、错路由、部分不回复”时，不能先把问题收束成 1~3 个真正根因。

## 之前版本的结构性短板

### 1. 先天偏“部署视角”，不是“排障视角”
前一版更擅长：
- 新增
- 扩容
- 巡检

但在排障上，更多是：
- 告诉你检查什么
- 告诉你可能修什么

还不够擅长：
- 明确哪个问题是 **P1 根因**
- 哪些只是症状
- 修复顺序为什么必须这样排

### 2. `inspect` 和 `repair` 中间缺了 `root-cause`
如果只有：
- `inspect`
- `repair`

那么很容易出现：
- inspect 看到了很多问题
- repair 开始逐个补
- 但没有先判断哪个是总开关

这会让修复动作变成“补洞”，不是“打掉主因”。

### 3. 没把高频根因固化成默认优先级
多 Agent / 多飞书账号环境里，高频主因往往不是随机的。

通常优先看：
1. `session.dmScope`
2. `accounts ↔ bindings` 是否闭环
3. 插件链路是否重复覆盖
4. `workspace / agentDir` 是否缺失

如果 skill 不把这套优先级写死，它就会显得“懂很多，但不够会判断轻重”。

## 当前版本的修正思路

### 0. 先把编排顺序代码化
对新增 / 扩容类请求，先统一走单入口流水线：

`normalize -> scan_current_state -> build_desired_state -> validate_plan -> generate_patch -> verify_setup`

不再让 LLM 自己决定这几步谁先谁后，也不允许同一轮同时产出两套互相冲突的 `agentMode` 计划。

### 1. 新增 `root-cause`
让技能先给：
- 表面症状
- 根因候选
- 证据
- 修复优先级
- 不修会继续发生什么

### 2. 增加 inspect script
通过 `scripts/inspect_openclaw_multi_agent.py`，先把现场压缩成几条高频根因，而不是直接给一堆散点检查项。

### 3. 把 repair 变成“后手”
默认顺序改为：

`inspect -> root-cause -> repair`

而不是：

`inspect -> repair`

### 4. 把 access/pairing 检查前置到接入验证
新增 / 扩容后，验证链必须显式检查：
- allowFrom 文件是否存在
- 当前 sender 是否已放行
- pairing 是否仍有 pending 请求

这样可以在 bot “不回复” 时第一时间定位到 `not paired`，而不是先怀疑模型、目录或配置 patch。

## 当前真实环境中已识别的高频根因示例

### 根因 1：`session.dmScope` 仍是 `per-channel-peer`
这会导致多账号飞书下的会话隔离不够细，出现串小龙虾 / 串上下文风险。

### 根因 2：存在误导性的 `accounts.default` 占位账号
它不一定是故障源，但会让 status / channels 输出在排障时产生错误心智。

### 根因 3：飞书插件链路重复覆盖
当内置插件与全局插件并存，且 CLI 已经提示 duplicate plugin warning 时，后续很多现象会变得难以归因。

## 结论
这个 skill 要真正“会修”，不是继续往 README 里加问题列表，
而是必须先把：

> **根因优先级 + 证据链 + 修复顺序**

做成默认行为。

这也是本次优化的核心。
