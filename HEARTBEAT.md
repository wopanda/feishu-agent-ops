# HEARTBEAT.md

## 目标
仅做「主题监控日报」最小健康检查：发现异常就提醒，正常就保持安静。

## 执行规则
- 每次收到 heartbeat poll 时执行以下检查。
- **全部正常**：回复 `HEARTBEAT_OK`。
- **有异常**：仅输出异常摘要（不输出 HEARTBEAT_OK）。
- 默认不自动修复，不主动重跑任务，只做告警。

## 检查项（最小版）

### 1) Stage1 任务是否在 26 小时内成功运行
- 任务 ID：`62971099-561d-42fa-804c-d00c2fa56f85`
- 条件：`state.lastRunStatus == "ok"` 且 `now - state.lastRunAtMs <= 26h`

### 2) 今日日报文件是否存在
- 路径：`/root/obsidian-vault/Input/TopicReports/$(date +%F)-主题监控日报.md`
- 条件：文件存在，且非空

### 3) Stage2 推送是否在 26 小时内成功
- 任务 ID：`fb69f0e2-c228-4c9d-80ca-703ac9f2115e`
- 条件：`state.lastRunStatus == "ok"` 且 `state.lastDeliveryStatus == "delivered"` 且 `now - state.lastRunAtMs <= 26h`

## 异常输出格式
- 标题：`⚠️ 主题监控健康检查异常`
- 列表：
  - Stage1：正常/异常（原因）
  - 日报文件：正常/异常（原因）
  - Stage2：正常/异常（原因）
- 结尾给 1 条建议动作（例如："建议手动触发 Stage1"）
