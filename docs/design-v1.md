# Design V1

## 定位
`feishu-agent-ops` 是一个面向 OpenClaw + 飞书场景的多 Agent 接入 / 扩容 / 巡检 / 修复 skill。

它不负责替用户去飞书开放平台创建机器人。
它负责把用户已经拿到的机器人信息，整理成 OpenClaw 可运行的多 Agent 系统。

## V1 范围

### 支持
- 从 1 个 Agent 扩到多个
- 从多个 Agent 继续扩容
- 巡检 `agents / accounts / bindings / workspace / agentDir / dmScope`
- 修复常见配置异常
- 默认先 `plan`，后 `apply`

### 暂不支持
- 自动创建飞书机器人
- 自动获取 `appId / appSecret`
- 全自动完成所有授权链
- 可视化后台
- 高复杂度群路由编排

## 核心动作
- `plan`: 只分析，不落地
- `apply`: 备份、patch、建目录、校验
- `inspect`: 巡检健康度
- `repair`: 最小修复
- `root-cause`: 对多 Agent / 多小龙虾异常做一级根因归类与证据收口

## 首次成功路径
1. 用户贴出机器人信息
2. skill 识别当前现状
3. 先输出规划预览
4. 用户确认后再执行
5. 至少 1 个新 bot 完成真实回复验证

## 设计原则
- 少填、少想、可控、安心
- 先预览，再执行
- 默认增量 patch，不粗暴重写
- 没证据，不宣布完成
- 默认给用户可验证的下一步
- inspect / repair 必须按固定顺序先查高频根因，不随机排查

## 高优先级真实根因
当前这类多 Agent 场景，至少要优先覆盖：
- `session.dmScope` 配错导致串会话
- `accounts` 与 `bindings` 不闭环
- 默认 Agent / binding 抢路由
- `workspace / agentDir` 缺口
- 插件重复覆盖 / 版本混装
