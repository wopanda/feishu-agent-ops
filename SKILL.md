---
name: feishu-agent-ops
description: 当用户要把一批已创建好的飞书机器人接入 OpenClaw，完成多 Agent 新增、扩容、巡检或修复时使用。默认按场景先判断：1）从 1 个扩到多个；2）已有多个继续扩容；3）已有多个但配置异常。前台采用渐进式披露；如存在 OpenClaw 版本、Feishu/Lark 插件链或字段结构漂移，先做兼容探测，再决定后续 diagnose / repair 路径。
---

# Feishu Agent Ops

这是一个把多个飞书机器人整理并接入 OpenClaw 多 Agent 的部署编排 skill。

它优先负责：
- 新增多 Agent
- 扩容现有多 Agent
- 巡检配置健康度
- 修复常见接入异常

## 前台先按场景进入

默认先判断用户属于哪种场景，而不是先让用户选 action：

### 场景 A：一只龙虾变多只（bootstrap）
适用于：
- 当前主要还是单 bot / 单 Agent
- 想拆成多个专职机器人
- 希望先看预览再落地

### 场景 B：多只龙虾继续扩更多（expand）
适用于：
- 已经有多 Agent / 多 bot
- 想继续增量扩进去
- 不想覆盖旧配置

### 场景 C：多只龙虾出了问题（diagnose）
适用于：
- 串会话
- 某个 bot 不回复
- 路由偶尔跑错
- 升级后插件链 / 字段结构漂移，担心修偏

## 渐进式披露规则

### 第 1 步：先识别场景
只先判断属于 `bootstrap / expand / diagnose` 哪一类。

### 第 2 步：只问最少问题

#### bootstrap / expand 默认只问：
- 绑定已有 Agent，还是新建 Agent？
- 账户级绑定，还是群聊级绑定？
- 新 bot 的基础信息是什么？

#### diagnose 默认只问：
- 异常现象是什么？
- 哪几个 bot 受影响？
- 是否允许先做只读扫描？

### 第 3 步：必要时先 compat-scan
如果满足这些情况，先做兼容探测：
- 不确定当前 OpenClaw 是哪个版本
- 不确定生效的是旧 `feishu` 还是官方 `openclaw-lark`
- 升级后怀疑字段结构有变化
- 当前现场存在插件覆盖、历史残留、多版本混用

推荐脚本：

```bash
python3 scripts/scan_openclaw_compat.py --config ~/.openclaw/openclaw.json
```

### 第 4 步：再扫当前现场
兼容探测确认没走偏后，再把当前现场压成结构化 observed state：

```bash
python3 scripts/scan_current_state.py --config ~/.openclaw/openclaw.json --pretty
```

### 第 5 步：再构造目标预览
把“归一化请求 + 当前现场”合成目标预览：

```bash
python3 scripts/build_desired_state.py \
  --request examples/output-normalized-bootstrap.json \
  --observed examples/output-observed-state.json \
  --pretty
```

### 第 6 步：先校验预览
在真正 apply 前，先对目标预览做静态校验：

```bash
python3 scripts/validate_plan.py \
  --request examples/output-normalized-bootstrap.json \
  --desired examples/output-desired-state-preview.json \
  --pretty
```

### 第 7 步：生成拟变更预览
在真正 apply 前，把目标预览翻成 patch preview：

```bash
python3 scripts/generate_patch.py \
  --desired examples/output-desired-state-preview.json \
  --pretty
```

### 第 8 步：生成 dry-run 执行计划
在真正写配置前，先把 patch preview 翻成 dry-run apply plan：

```bash
python3 scripts/apply_patch.py \
  --patch-preview examples/output-patch-preview.json \
  --pretty
```

### 第 9 步：生成落地后验证清单
在真正 apply 后，先按 checklist 验证配置、目录和目标 bot：

```bash
python3 scripts/verify_setup.py \
  --desired examples/output-desired-state-preview.json \
  --pretty
```

### 第 10 步：最小执行骨架（可选）
如果已经确认 patch preview 没问题，可用最小执行骨架做真正 apply：

```bash
python3 scripts/apply_real.py \
  --patch-preview examples/output-patch-preview.json \
  --config /tmp/openclaw-apply-real-test.json \
  --execute \
  --pretty
```

当前只支持：
- `jsonPatchPreview` 中的 `add`
- `filesystemPreview` 中的 `mkdir`

### 第 11 步：确认通过后再收口
- 至少验证配置可读
- 至少验证目录存在
- 至少验证 1 个目标 bot 在待验证列表中

## 后台动作仍然保留

虽然前台改成场景入口，但后台仍然会调用这些阶段：
- `compat-scan`
- `normalize-request`
- `scan-current-state`
- `build-desired-state`
- `validate-plan`
- `generate-patch`
- `apply-patch-dry-run`
- `verify-setup`
- `apply-real-minimal`
- `plan`
- `apply`
- `inspect`
- `root-cause`
- `repair`

只是现在的顺序变成：

> 先判场景，再决定动作链。

## 请求归一化（新增）

为了兼容旧输入和新场景输入，后台新增：
- `schemas/request.schema.json`
- `scripts/normalize_request.py`

它会把：
- 旧的 action-first 输入
- 新的 scenario-first 输入

统一归一化成内部请求对象，避免后面每一步都重复猜用户意思。

示例：

```bash
python3 scripts/normalize_request.py --input examples/input-minimal.json --pretty
```

归一化输出样例：
- `examples/output-normalized-bootstrap.json`

## 当前现场扫描（新增）

为了把 diagnose / inspect / repair 的前置输入变成稳定结构，后台新增：
- `schemas/observed-state.schema.json`
- `scripts/scan_current_state.py`

它会输出：
- 当前 `session.dmScope`
- `channels.feishu` 顶层字段
- 账号列表
- Feishu bindings
- agents / workspace / agentDir 存在性
- warnings

输出样例：
- `examples/output-observed-state.json`

## 目标预览构造（新增）

为了把 bootstrap / expand 的预览逻辑从 prompt 挪到确定性层，后台新增：
- `schemas/desired-state.schema.json`
- `scripts/build_desired_state.py`

它会基于：
- normalized request
- observed state

生成：
- plannedAgents
- plannedAccounts
- plannedBindings
- planSummary
- nextActions
- warnings

输出样例：
- `examples/output-desired-state-preview.json`

如果要验证“空白 bootstrap 现场”的目标预览，可搭配：
- `examples/observed-state-bootstrap-empty.json`

## 预览校验（新增）

为了避免把明显冲突的预览推进到 apply，后台新增：
- `scripts/validate_plan.py`

它当前会检查：
- 重复 `agentId`
- 重复 `accountId`
- 重复 binding
- group routing 缺少 `chatId`
- `bind-existing` 缺少 `agentId`
- bootstrap / expand 预览为空

输出样例：
- `examples/output-plan-validation-pass.json`

## 拟变更预览（新增）

为了让 apply 前的风险可视化，后台新增：
- `schemas/patch-preview.schema.json`
- `scripts/generate_patch.py`

它会输出：
- 将新增哪些 accounts
- 将新增哪些 bindings
- 将新增哪些 agents
- 将创建哪些目录

输出样例：
- `examples/output-patch-preview.json`

## dry-run 执行计划（新增）

为了在真正 apply 前把执行顺序和确认点说明白，后台新增：
- `scripts/apply_patch.py`

它当前不会真正写配置，只会输出：
- 备份计划
- 执行步骤顺序
- 哪些步骤需要确认
- 最后怎么验证

输出样例：
- `examples/output-apply-plan-dry-run.json`

## 落地后验证清单（新增）

为了把 apply 后“怎么验”结构化，后台新增：
- `scripts/verify_setup.py`

它当前不会真正发消息验证，只会输出：
- 配置文件可读检查
- workspace / agentDir 存在性检查
- bindings 目标数量检查
- 至少 1 个目标 bot 的待验证探针

输出样例：
- `examples/output-verify-setup-checklist.json`

## 最小执行骨架（新增）

为了开始把 preview 接到真实落地入口，后台新增：
- `scripts/apply_real.py`
- `schemas/apply-result.schema.json`

它当前只支持最小范围：
- `jsonPatchPreview` 里的 `add`
- `filesystemPreview` 里的 `mkdir`

并支持：
- `--config` 覆盖目标配置路径
- `--execute` 真正执行写入

输出样例：
- `examples/output-apply-result-ready.json`

## Root-Cause-First（根因优先）规则

在 `diagnose` 场景中，必须按下面顺序排查：

### 第 1 层：会话隔离层
- 检查 `session.dmScope`
- 多账号飞书场景优先关注：`per-account-channel-peer`

### 第 2 层：账号与路由闭环层
- 对齐 `channels.feishu.accounts` 与 `bindings`
- 检查 `accountId -> agentId` 是否闭环
- 检查默认 Agent 是否抢路由

### 第 3 层：目录与 agent 结构层
- 检查 `workspace-*`
- 检查 `agents/<id>/agent`
- 检查目录与路由映射是否一致

### 第 4 层：插件与运行层
- 检查插件重复覆盖告警
- 检查 status / logs 中的运行告警

## 自动修复 vs 需确认

### 默认可自动修复
- 缺少 binding
- 缺少 `workspace` / `agentDir`
- 可确定且无歧义的映射缺口

### 必须先确认再修
- 修改 `session.dmScope`
- 调整默认 Agent
- 涉及插件层配置切换
- 可能影响已有对话连续性的改动

## 安全护栏

- 未备份，不执行 `apply`
- 未预览，不直接改配置
- 遇到命名冲突 / 默认 Agent 冲突 / binding 冲突时先停下
- `repair` 默认只做最小修复，不大范围重写
- 当 compat-scan 结果是 `mixed-transition` / `broken-state` 时，不允许按单一版本心智盲改
- 没有验证依据，不说“已完成可用”

## 默认输出结构

1. 已做改动
2. 验证依据
3. 风险 / 未完成项
4. 下一步建议

## 一句话心法

> 先判场景，再决定动作；先看兼容，再谈修复。
