---
name: feishu-agent-ops
description: 当用户要把一批已创建好的飞书机器人接入 OpenClaw，完成多 Agent 新增、扩容、巡检或修复时使用。前台默认走最小必要信息收集：能从当前环境推断的，不先让用户填表；新增/扩容默认只先要 appId、appSecret、botName；排障默认先做只读扫描。
---

# Feishu Agent Ops

这是一个把多个飞书机器人整理并接入 OpenClaw 多 Agent 的部署编排 skill。

它优先负责：
- 新增多 Agent
- 扩容现有多 Agent
- 巡检配置健康度
- 修复常见接入异常

## 前台规则：不要一上来收很多信息

默认先按场景进入，而不是先让用户理解 action 或填大表。

### 场景 A：新增 / 扩容
先只收 **最少必要信息**。

默认最少只要：
- `appId`
- `appSecret`
- `botName`

### 场景 B：排障 / 巡检
默认先不要让用户补很多字段。

先收：
- 异常现象
- 哪几个 bot 受影响（如果用户知道）
- 是否允许先做只读扫描

如果用户连 bot 名都说不清，也不要卡住，先扫描当前环境。

## 哪些信息是“必要的”，哪些不是

### 新增 / 扩容时的必要信息
1. `appId`
2. `appSecret`
3. `botName`

### 默认可后补 / 可推断的信息
- `accountId`
- `agentId`
- `roleName`
- `model`
- `isDefault`
- `chatId`

规则：
- `accountId` 用户不会填时，由 agent 根据 `botName` 自动生成建议值
- `agentId` 只有用户明确要“绑定已有 Agent”时才追问
- `chatId` 只有用户明确要做“群聊级绑定”时才追问
- 用户不确定时，优先先扫描当前环境，再给建议，不让用户盲填

## 必须给示例，不要只丢字段名

如果用户要新增机器人，优先给这种最小模板：

```text
我想新增一个飞书机器人：
- appId：cli_xxx
- appSecret：xxx
- botName：日新调研
其他你帮我补。
```

如果用户要扩容，优先给这种模板：

```text
我已经有多机器人了，下面这个帮我增量加进去：
- appId：cli_xxx
- appSecret：xxx
- botName：内容助手
不要覆盖旧配置。
```

如果用户要排障，优先给这种模板：

```text
这套多飞书机器人有问题：
- 现象：某个 bot 不回复 / 串会话 / 路由错
- 先帮我检查，不要直接改
```

## 必须告诉用户“去哪里找”

当用户缺少 `appId` / `appSecret` 时，必须明确告诉他：

路径：
**飞书开放平台 → 对应应用 → 凭证与基础信息**

可在那里找到：
- App ID
- App Secret

当用户不知道 `botName` 时：
- 直接用飞书开放平台里的应用名称
- 或飞书里看到的机器人名字

当用户不知道 `accountId` 是什么时，必须说明：
- 这是 OpenClaw 本地配置里的内部代号
- 不是飞书官方字段
- 不会填可以不填，由 agent 生成建议值

## 渐进式披露

### 第 1 步：先识别场景
只先判断属于：
- bootstrap（1 → N）
- expand（N → N+M）
- diagnose（N 出问题）

### 第 2 步：只问最少问题
#### bootstrap / expand 默认只问：
- 这是新增还是继续扩容？
- 你现在有没有 `appId / appSecret / botName`？
- 是想绑定已有 Agent，还是我先帮你判断？

#### diagnose 默认只问：
- 现象是什么？
- 是否允许先做只读扫描？

### 第 3 步：能扫描就先扫描
如果用户不会填 `accountId / agentId / chatId`：
- 不要先让用户查很多资料
- 先扫描当前环境
- 再给他最小决策问题

## Root-Cause-First（根因优先）

在 diagnose / repair 场景，必须按下面顺序排查：

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
- 没有验证依据，不说“已完成可用”

## 默认输出结构

1. 已做改动
2. 验证依据
3. 风险 / 未完成项
4. 下一步建议

## 一句话心法

> 先让用户把事说出来，再只补必要信息；能从当前环境推断的，不先让用户填表。
