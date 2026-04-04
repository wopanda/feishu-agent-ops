# Repair Priority

多 Agent / 多小龙虾异常，默认按这个优先级处理：

## P1
- `session.dmScope` 是否适合多账号隔离
- `accounts` 与 `bindings` 是否真正闭环
- `accountId -> agentId` 是否稳定一一映射

## P2
- `workspace` 是否缺失
- `agentDir` 是否缺失
- 目录结构与配置是否一致

## P3
- 插件层重复覆盖
- 版本混装
- 更深层渠道实现差异

## 原则
- 先打掉总开关，再补局部问题
- 先修高频根因，再碰深层复杂问题
- 先给证据，再动修复
