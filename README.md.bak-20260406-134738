# Feishu Agent Ops

把飞书机器人接成 OpenClaw 多 Agent。  
支持添加机器人、巡检、根因排查和修复。

---

## 当前改造重点

这版不再把 LLM 当编排器主脑。
现在的原则是：

- **LLM 负责理解用户意图和补最少信息**
- **脚本负责归一化、状态扫描、计划构造、校验、patch 预览、执行、验证**
- **一旦 schema / 分支不合法，就失败即停，不继续让 LLM 猜**

### 已下沉到代码层的关键逻辑
- 场景收敛：`bootstrap / expand / diagnose`
- 路由模式：`account / group / mixed`
- Agent 模式：`bind-existing / create-new`
- `accountId` 自动生成
- 当前状态扫描（observed state）
- 目标状态构造（desired state）
- patch 预览生成
- 计划校验
- 接入后验证清单生成

### 特别修正
本次接入 `rixin8` 暴露出两个真实问题，这版已针对性修正：

1. **不能再让同一轮里同时漂出 `bind-existing` 和 `create-new` 两条链**
2. **新 bot 不回复时，必须把 `allowFrom / pairing / not paired` 提到高优先级验证项**

---

## 先说重点：你只管提供必要信息

前台只保留 2 个入口：
- 添加机器人
- 排查问题

你不需要判断这是“新增”还是“扩容”。
系统会先扫描当前环境，再给你最合适的接入方案或排查结论。

### 入口 1：添加机器人
最低只需要这些：

1. **appId**  
   去哪找：飞书开放平台 → 对应应用 → **凭证与基础信息** → App ID
2. **appSecret**  
   去哪找：同一页 → App Secret
3. **botName**  
   直接给我机器人名称 / 应用名称就行

### 这些信息现在默认可选
- **accountId**：OpenClaw 里的内部代号，**你不会起名也没关系，我可以帮你生成**
- **agentId**：只有你明确想绑定到某个已有 Agent 时才需要
- **roleName / model / isDefault**：没有就先不填
- **chatId**：只有你明确要做“群聊级绑定”时才需要

### 入口 2：排查问题
默认连上面这些都不用先给。

你只要直接说：

```text
这套多飞书机器人有问题，你先帮我检查。
```

我应该先做只读扫描，再决定后面要不要补信息。

---

## 现在内部固定流水线

### 新增 / 扩容
`normalize_request -> scan_current_state -> build_desired_state -> validate_plan -> generate_patch -> verify_setup`

### 排障 / 修复
`compat / state scan -> root-cause -> minimal repair plan -> verify`

### 硬约束
- 中间 JSON 必须合法
- 非法就停，不继续 apply
- 预览先于写入
- 写入先于验证
- 运行不回复时，优先检查 `allowFrom / pairing`

---

## 你现在可以直接这样用

### 场景 A：我想添加一个机器人
直接发：

```text
我想添加一个飞书机器人。
appId：xxx
appSecret：xxx
botName：日新调研
其他你帮我补。
```

### 场景 B：我不清楚 accountId / agentId 怎么填
直接发：

```text
我不会填 accountId / agentId，你先根据当前环境帮我判断，再给我预览。
```

### 场景 C：我这套环境有异常
直接发：

```text
这套多飞书机器人现在有异常，你先检查，不要直接乱改。
```

---

## 你会得到什么

### 添加机器人
- 自动补 accountId
- 判断绑已有 Agent 还是新建 Agent
- 变更预览
- 确认后再落地
- 接入后验证清单（含 allowFrom / pairing 检查）

### 排障
- 当前现场扫描结果
- 根因判断
- 修复优先级
- 最小修复建议
- 修后验证路径

---

## 一句话原则

> 你只需要把需求和必要信息说出来；系统先扫描当前环境，再给最合适的方案和预览；判断与 patch 尽量代码化，解释与确认留在 skill 层。

---

## 推荐的确定性执行方式（新）

新增 / 扩容类请求，默认不要再手工串：
- normalize
- observed-state scan
- desired-state build
- validate
- patch preview
- verify checklist

现在统一建议走单入口：

```bash
python3 scripts/run_plan_pipeline.py \
  --input <request.json> \
  --config ~/.openclaw/openclaw.json \
  --pretty
```

这样可以避免：
- 同一轮里同时跑出 `bind-existing` / `create-new` 两套互相冲突的链
- 中间 JSON 一步错了，后面还继续让 LLM 猜
- 校验失败后仍然进入 apply / 手工补洞

## 运行层验证（新）

如果 bot 已接入但“不回复”，不要只查配置；先直接查运行放行链：

```bash
python3 scripts/verify_setup.py \
  --config ~/.openclaw/openclaw.json \
  --account-id <accountId> \
  --sender-id <sender_open_id> \
  --pretty
```

这一步会直接检查：
- account 是否存在
- binding 是否存在
- workspace / agentDir 是否存在
- allowFrom 文件是否存在
- 当前 sender 是否已被 allowFrom 放行
- pairing 是否仍有 pending 请求

---

## 推荐的确定性执行方式（新）

新增 / 扩容类请求，默认不要再手工串：
- normalize
- observed-state scan
- desired-state build
- validate
- patch preview
- verify checklist

现在统一建议走单入口：

```bash
python3 scripts/run_plan_pipeline.py \
  --input <request.json> \
  --config ~/.openclaw/openclaw.json \
  --pretty
```

这样可以避免：
- 同一轮里同时跑出 `bind-existing` / `create-new` 两套互相冲突的链
- 中间 JSON 一步错了，后面还继续让 LLM 猜
- 校验失败后仍然进入 apply / 手工补洞

## 运行层验证（新）

如果 bot 已接入但“不回复”，不要只查配置；先直接查运行放行链：

```bash
python3 scripts/verify_setup.py \
  --config ~/.openclaw/openclaw.json \
  --account-id <accountId> \
  --sender-id <sender_open_id> \
  --pretty
```

这一步会直接检查：
- account 是否存在
- binding 是否存在
- workspace / agentDir 是否存在
- allowFrom 文件是否存在
- 当前 sender 是否已被 allowFrom 放行
- pairing 是否仍有 pending 请求
