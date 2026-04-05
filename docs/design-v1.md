# Design V1

> 注：当前仓库已开始进入 V2 重构过渡期。V1 的核心动作仍保留，但新增了“兼容探测优先”这一步，用来处理 OpenClaw 版本、Feishu/Lark 插件链和字段结构漂移问题。

## 定位
`feishu-agent-ops` 是一个面向 OpenClaw + 飞书场景的多 Agent 接入 / 扩容 / 巡检 / 根因排查 / 修复 skill。

它不负责替用户去飞书开放平台创建机器人。
它负责把用户已经拿到的机器人信息，整理成 OpenClaw 可运行的多 Agent 系统；当系统反复异常时，它还要先找根因，而不是只做表面修补。

## V1 范围

### 支持
- 从 1 个 Agent 扩到多个
- 从多个 Agent 继续扩容
- 巡检 `agents / accounts / bindings / workspace / agentDir / dmScope`
- 根因排查多 Agent / 多小龙虾反复异常
- 修复常见配置异常
- 默认先 `plan`，后 `apply`
- 遇到异常先 `root-cause`，再决定是否 `repair`

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
- `root-cause`: 先定位根因，产出证据和修复优先级
- `repair`: 最小修复

## 首次成功路径
1. 用户贴出机器人信息或异常症状
2. skill 识别当前现状
3. 先输出规划预览或根因诊断
4. 用户确认后再执行
5. 至少 1 个新 bot 完成真实回复验证，或异常链路得到可验证解释

## 设计原则
- 少填、少想、可控、安心
- 先预览，再执行
- 默认增量 patch，不粗暴重写
- 没证据，不宣布完成
- 默认给用户可验证的下一步
- 遇到反复异常，优先找根因，不直接堆修补动作

## 当前识别出的高频根因
基于当前 OpenClaw 现场排查，高频问题优先看：

1. `session.dmScope` 仍为 `per-channel-peer`，不适合多账号飞书隔离
2. Feishu 存在 `default` 占位账号，但并未真正配置顶层默认账号，状态输出易误导
3. 同时启用 `feishu` 与 `openclaw-lark`，出现 duplicate plugin warning，排障时不易判断哪条链路真正生效
4. OpenClaw 升级后，插件链路或字段结构已经漂移，但仍按旧心智 patch

## 新增：兼容探测优先
在 diagnose / repair 之前，优先判断：
- 当前 OpenClaw 是哪个版本
- 生效的是旧 `feishu` 还是官方 `openclaw-lark`
- `channels.feishu` 当前字段结构更像哪一代
- 当前现场属于 `old-feishu / official-lark / mixed-transition / broken-state` 哪一类

推荐脚本：

```bash
python3 scripts/scan_openclaw_compat.py --config ~/.openclaw/openclaw.json
```
