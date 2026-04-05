---
name: feishu-agent-ops
description: 当用户要把一批已创建好的飞书机器人接入 OpenClaw，完成多 Agent 新增、扩容、巡检或修复时使用。适用于“从 1 个扩到多个”“从多个扩到更多个”“检查多 Agent 异常”“修复 bindings / workspace / 会话隔离问题”这类场景。默认先做规划预览，再执行落地；当 OpenClaw 版本、Feishu/Lark 插件链或字段结构可能存在漂移时，先做兼容探测，再决定后续 diagnose / repair 路径。
---

# Feishu Agent Ops

这是一个把多个飞书机器人整理并接入 OpenClaw 多 Agent 的部署编排 skill。

它优先负责：
- 新增多 Agent
- 扩容现有多 Agent
- 巡检配置健康度
- 修复常见接入异常

> 关键升级：异常场景默认启用 **Root-Cause-First（根因优先）**，先抓证据，再修复，不做拍脑袋 repair。

## 何时使用

以下场景优先使用本 skill：

- 用户已经创建好多个飞书机器人，并拿到了 `appId` / `appSecret` / `accountId`
- 用户想把 1 个 Agent 扩成多个
- 用户已经有多 Agent，想继续扩容
- 用户怀疑 `bindings` / `workspace` / `dmScope` / 路由有异常，想巡检或修复

## 不适用场景

- 还没有创建飞书机器人，也还没拿到 `appId` / `appSecret`
- 只是想了解 OpenClaw 配置结构，不打算实际接入
- 需要自动去飞书开放平台创建机器人（不在 V1 范围）

## 默认工作方式

1. 先识别当前 OpenClaw / Feishu 配置现状
2. 如怀疑存在版本 / 插件 / 字段结构偏差，先做兼容探测
3. 再整理用户提供的机器人信息
4. 先生成规划预览（`plan`）
5. 用户确认后再执行写入（`apply`）
6. 异常场景先 `compat-scan` / `inspect`，再 `repair`

## 兼容探测优先（新增）

当满足任一条件时，先跑兼容探测，再决定后续 `inspect / root-cause / repair`：

- 不确定当前 OpenClaw 是哪个版本
- 不确定生效的是旧 `feishu` 还是官方 `openclaw-lark`
- 升级后怀疑字段结构有变化
- 当前现场存在插件覆盖、历史残留、多版本混用

推荐脚本：

```bash
python3 scripts/scan_openclaw_compat.py --config ~/.openclaw/openclaw.json
```

该脚本会输出：
- OpenClaw 版本与包版本
- 当前生效的 Feishu/Lark 插件链
- 插件版本与残留情况
- `session.dmScope`
- `channels.feishu` 顶层字段形态
- `accounts / bindings` 数量
- `compatMode`（`old-feishu | official-lark | mixed-transition | broken-state`）
- 风险标记

## Root-Cause-First（根因优先）规则

在 `inspect / repair` 场景，必须按下面顺序排查：

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

## 支持的动作

### 1. `plan`
只分析，不落地。

### 2. `apply`
正式执行接入或扩容。

### 3. `inspect`
巡检当前多 Agent 配置。
输出必须包含：
- 发现的一级根因（不是只列症状）
- 根因证据
- 修复优先级

### 4. `repair`
做最小修复。
输出必须包含：
- 已修复项
- 未修复项
- 不能自动修复的确认点
- 修后验证结果

### 5. `compat-scan`
做只读兼容探测，先判断版本 / 插件 / 字段结构偏差，再决定后续修复路径。

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

## 输入协议

每个机器人至少包含：
- `accountId`
- `appId`
- `appSecret`
- `botName`

可选：
- `roleName`
- `agentId`
- `model`
- `isDefault`

输入形式：
- 自然语言
- JSON
- YAML

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

> 先找根因，再修症状；先闭环证据，再宣布恢复。
