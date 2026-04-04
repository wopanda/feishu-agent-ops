# Repair Priority

多 Agent / 多小龙虾异常，默认按下面顺序排查与修复：

## 第 1 层：会话隔离
先看：
- `session.dmScope`

多账号飞书场景，优先检查是否应为：
- `per-account-channel-peer`

## 第 2 层：账号与路由闭环
先对齐：
- `channels.feishu.accounts`
- `bindings`
- `agentId`
- `accountId`

高频问题：
- account 已存在，但没有 binding
- binding 指向错误 agent
- 默认 agent 抢路由

## 第 3 层：目录与 agent 结构
检查：
- `workspace-*`
- `agents/<id>/agent`
- 目录是否和 binding / agent 对应

## 第 4 层：插件与运行层告警
检查：
- 插件重复覆盖
- 版本混装
- status / logs 告警

## 原则
- 先 inspect，再 repair
- 先修高频根因，再修表象
- 先最小修复，再考虑结构重写
