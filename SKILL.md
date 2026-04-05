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

### 第 4 步：先给预览，不直接改
- bootstrap / expand：输出目标结构预览、增量 diff、验证路径
- diagnose：输出根因诊断、修复优先级、风险说明

### 第 5 步：确认后再 apply / repair
- 变更前先备份
- 变更后强制验证

## 后台动作仍然保留

虽然前台改成场景入口，但后台仍然会调用这些阶段：
- `compat-scan`
- `plan`
- `apply`
- `inspect`
- `root-cause`
- `repair`

只是现在的顺序变成：

> 先判场景，再决定动作链。

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
