# Feishu Agent Ops

把你已经创建好的多个飞书机器人，接成 OpenClaw 多 Agent。  
支持新增、扩容、巡检、根因排查和修复。

---

## 现在这个 skill 真正解决什么

它不只是告诉你“怎么配”。
它更重要的价值是：

1. 先识别当前 OpenClaw 多 Agent / 多飞书账号现状
2. 先判断当前到底是哪个 OpenClaw 版本、哪条 Feishu/Lark 插件链、字段结构是否漂移
3. 找出反复异常的根本原因
4. 再决定该怎么修，而不是先拍脑袋改配置

如果你现在的问题是：
- 多个小龙虾偶尔串会话
- 某个机器人不回复
- 路由偶尔跑错
- 配置看起来都在，但就是不稳定
- 升级后字段名字/插件链路变了，担心修偏

那就不要只做 `repair`，先做 **compat scan + root cause**。

---

## 最简单的开始方式

如果你是要新增或扩容，直接把机器人信息贴给我，我会先：

1. 识别你当前的 OpenClaw 现状
2. 必要时先跑一轮 **compat scan**，判断当前版本 / 插件 / 字段形态
3. 给你一份多 Agent 规划预览
4. 等你确认后再落地
5. 最后带你完成第一次真实验证

如果你是要排异常，直接说：

```text
帮我先扫描一下当前 OpenClaw + Feishu 插件兼容形态，再找这套多 Agent / 多小龙虾异常的根本原因，不要只给表面修法。
```

你不需要先手改一大堆 JSON。

---

## 你只需要准备

每个飞书机器人至少提供：

- `accountId`
- `appId`
- `appSecret`
- `botName`

如果是根因排查，最好还能提供：
- 当前 `openclaw.json` 路径
- 异常现象
- 哪几个 bot 受影响

---

## 你可以直接这样说

```text
我已经创建好了这批飞书机器人，帮我接成 OpenClaw 多 Agent，先给我预览，再执行。
```

```text
我现在已经有几个 Agent 了，下面是新机器人的信息，帮我增量扩进去，不要覆盖旧配置。
```

```text
帮我检查一下当前这套飞书多 Agent 配置有没有问题。
```

```text
帮我找一下这套多 Agent / 多小龙虾异常的根本原因，不要只给表面修法。
```

---

## 兼容探测优先（新增）

当满足任一条件时，默认先跑：

```bash
python3 scripts/scan_openclaw_compat.py --config ~/.openclaw/openclaw.json
```

适用条件：
- 不确定当前 OpenClaw 是哪个版本
- 不确定当前生效的是旧 `feishu` 还是官方 `openclaw-lark`
- 怀疑升级后字段结构变了
- 现场存在历史残留 / 多版本混用 / 插件覆盖告警

这个扫描器会输出：
- OpenClaw 版本
- 当前生效的 Feishu/Lark 插件链
- 插件版本
- `session.dmScope`
- `channels.feishu` 顶层字段形态
- `accounts / bindings` 数量
- `compatMode`（`old-feishu | official-lark | mixed-transition | broken-state`）
- 风险标记

示例输出见：
- `examples/output-compat-scan.json`

---

## 你会得到什么

- 多 Agent 接入规划预览
- 自动生成的 `accounts + bindings` 方案
- 建议的 `workspace / agentDir` 结构
- 兼容扫描结果（版本 / 插件 / 字段形态）
- 根因诊断结论
- 修复优先级建议
- 部署结果、巡检结果和下一步测试建议

---

## 第一次成功是什么

第一次成功不是“改完配置”，而是：

- 生成正确的规划预览
- 或者给出带证据的根因诊断
- 安全落地配置
- 至少 1 个新 bot 完成真实回复验证

---

## 支持的 5 类动作

### 1. `plan`
只分析，不落地。

### 2. `apply`
正式执行新增或扩容。

### 3. `inspect`
巡检现有多 Agent 配置。

### 4. `root-cause`
先找根本原因，再决定修不修。

### 5. `repair`
修复常见接入异常。

### 6. `compat-scan`
先识别 OpenClaw 版本、Feishu/Lark 插件链和字段结构偏差，避免按错版本修配置。

---

## 当前这个 skill 默认先盯的 3 个高频根因

1. `session.dmScope` 不适合多账号隔离  
2. Feishu `accounts` 与 `bindings` 没有真正闭环  
3. 飞书插件链路重复覆盖、实际生效实现不清楚  
4. OpenClaw 版本 / 插件版本 / 字段结构已经漂移，但还按旧心智在修

---

## 最小输入示例

```json
{
  "action": "plan",
  "defaultModel": "huandutech/gpt-5.4-high",
  "bots": [
    {
      "accountId": "manager",
      "botName": "总控机器人",
      "appId": "cli_xxx_manager",
      "appSecret": "secret_manager",
      "roleName": "总控",
      "isDefault": true
    },
    {
      "accountId": "research",
      "botName": "调研机器人",
      "appId": "cli_xxx_research",
      "appSecret": "secret_research",
      "roleName": "调研"
    }
  ]
}
```

---

## 后面再看什么

如果你第一次已经跑通，再继续看：

- 输入格式扩展
- 命名规则
- `workspace / agentDir` 约定
- `bindings` 与 `dmScope` 说明
- 巡检与根因排查脚本
- 兼容探测脚本 `scripts/scan_openclaw_compat.py`
- 回滚与发布说明
