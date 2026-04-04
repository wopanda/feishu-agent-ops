# Repair Playbook

## 目标
把“多 Agent / 多小龙虾异常”从模糊感受，转成可执行修复链。

## 执行顺序（固定）

### Step 1. 抓全局证据
- `openclaw status`
- 当前 `session.dmScope`
- Feishu accounts 数量
- bindings 数量
- 插件重复覆盖告警

### Step 2. 判定一级根因
优先判断：
1. 会话隔离是否不匹配（高频）
2. 账号与路由是否闭环（高频）
3. 目录是否缺失或错配
4. 插件层是否覆盖冲突

### Step 3. 生成修复优先级
- P1：会话隔离 / 路由闭环
- P2：目录缺失
- P3：插件层与复杂冲突

### Step 4. 先修可自动修项
- 缺少 binding
- 缺少 workspace / agentDir
- 明确无歧义的映射缺口

### Step 5. 再处理需确认项
- 改 `dmScope`
- 改默认 Agent
- 改插件层

### Step 6. 修后验证
- 配置闭环是否恢复
- 至少 1 个目标 bot 实测回复
- 是否还有高优先级告警

## 输出模板
按 `templates/root-cause-report.md` + `templates/repair-report.md` 输出。
