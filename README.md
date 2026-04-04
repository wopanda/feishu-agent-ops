# Feishu Agent Ops

把你已经创建好的多个飞书机器人，接成 OpenClaw 多 Agent。  
支持新增、扩容、巡检和修复。

---

## 最简单的开始方式

把你已有的机器人信息贴给我，我会先：

1. 识别你当前的 OpenClaw 现状
2. 给你一份多 Agent 规划预览
3. 等你确认后再落地
4. 最后带你完成第一次真实验证

你不需要先手改一大堆 JSON。

---

## 你只需要准备

每个飞书机器人至少提供：

- `accountId`
- `appId`
- `appSecret`
- `botName`

可选再补：
- `roleName`
- `agentId`
- `model`
- `isDefault`

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

---

## 你会得到什么

- 多 Agent 接入规划预览
- 自动生成的 `accounts + bindings` 方案
- 建议的 `workspace / agentDir` 结构
- 安全落地前的确认步骤
- 部署结果、巡检结果和下一步测试建议

---

## 第一次成功是什么

第一次成功不是“改完配置”，而是：

- 生成正确的规划预览
- 安全落地配置
- 至少 1 个新 bot 完成真实回复验证

---

## 支持的 4 类动作

### 1. `plan`
只分析，不落地。

### 2. `apply`
正式执行新增或扩容。

### 3. `inspect`
巡检现有多 Agent 配置。

### 4. `repair`
修复常见接入异常。

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
- 巡检与修复思路
- 回滚与发布说明
