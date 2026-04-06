# Feishu Agent Ops

把飞书机器人整理并接入 OpenClaw 多 Agent。

它前台只处理两件事：
- **添加机器人**
- **排查问题**

重点不是让用户先理解一堆配置项，
而是：**先给最少必要信息，系统先扫描当前环境，再给方案预览或排查结论。**

---

## 这是什么

这是一个偏产品化的 Feishu 接入 / 排障 skill。

它适合的场景：
- 你想新增一个飞书机器人接进 OpenClaw
- 你已经有多机器人环境，但出现了不回复 / 串路由 / 绑错 Agent / 配置不闭环
- 你想先看预览，再决定要不要真正改配置

它不要求用户先理解这些内部概念：
- `accountId`
- `agentId`
- `routingMode`
- `bind-existing / create-new`
- patch / desired-state / observed-state

这些都应该尽量由 skill 先判断、先扫描、先给建议。

---

## 第一次成功路径

README 首页只保留两条主入口。

### 入口 A：添加机器人

你最低只需要准备 3 个信息：

1. **appId**
2. **appSecret**
3. **botName**

去哪里找：

**飞书开放平台 → 对应应用 → 凭证与基础信息**

你会在那里看到：
- App ID
- App Secret

### 直接这样发

```text
我想添加一个飞书机器人：
- appId：cli_xxx
- appSecret：xxx
- botName：日新调研
其他你帮我补。
```

### 你会得到什么

系统应该先扫描当前环境，再给你：
- 建议的 `accountId`
- 是绑定已有 Agent，还是新建 Agent
- 变更预览
- 确认后再落地
- 接入后的验证清单

---

### 入口 B：排查问题

排障时，默认不要先让用户补一堆字段。

### 直接这样发

```text
这套多飞书机器人有问题：
- 现象：某个 bot 不回复 / 串会话 / 路由错
- 先帮我检查，不要直接改
```

如果用户连 bot 名都说不清，也不应该卡住。
应先做只读扫描，再决定后面要不要补信息。

### 你会得到什么

- 当前现场扫描结果
- 根因判断
- 最小修复建议
- 修后验证路径

---

## 默认哪些信息不用先问

第一次接入时，默认只先收：
- `appId`
- `appSecret`
- `botName`

这些信息默认可后补 / 可推断：
- **accountId**：OpenClaw 里的内部代号，不会填可以让 skill 生成建议值
- **agentId**：只有用户明确说“绑定已有 Agent”时才需要
- **roleName / model / isDefault**：没有就先不填
- **chatId**：只有明确要做群聊级绑定时才需要

原则：
- 能扫描，就先扫描
- 能推断，就不要追问
- 能安全自动做，就不要把用户拖进内部实现细节里

---

## 这个 skill 内部怎么工作

对用户来说，它只有两个入口。

对系统来说，它背后是确定性流水线：

### 新增 / 扩容

```text
normalize_request
-> scan_current_state
-> build_desired_state
-> validate_plan
-> generate_patch
-> verify_setup
```

### 排障 / 修复

```text
compat / state scan
-> root-cause
-> minimal repair plan
-> verify
```

设计原则：
- 中间 JSON 不合法就失败即停
- 预览先于写入
- 写入先于验证
- 不再让 LLM 在非法分支上继续猜

---

## 重要行为约束

### 1. 不要让用户在一开始就选内部模式

尤其不要一上来就逼用户判断：
- 我这是 bootstrap 还是 expand
- 我这是 bind-existing 还是 create-new
- 我该填哪个 agentId

这类判断应优先由 skill 结合当前环境来完成。

### 2. 绑定已有 Agent 时，才需要显式 `agentId`

如果用户明确说：
- “绑定到已有 Agent”
- “挂到某个现成 Agent 上”

才进入 `bind-existing` 模式。

否则默认应该先扫描，再判断要不要新建 Agent。

### 3. bot 不回复时，运行层检查要提前

遇到“配置看起来都对，但 bot 不回复”，优先检查：
- `allowFrom`
- pairing / not paired
- workspace / agentDir 是否存在
- account 与 binding 是否闭环

不要只停留在配置层。

---

## 推荐的最小调用模板

### 模板 1：新增一个机器人

```text
我想添加一个飞书机器人：
- appId：cli_xxx
- appSecret：xxx
- botName：日新调研
其他你帮我补。
```

### 模板 2：我不会填 accountId / agentId

```text
我不会填 accountId / agentId，你先根据当前环境帮我判断，再给我预览。
```

### 模板 3：先排障，不要直接改

```text
这套多飞书机器人有异常，你先检查，不要直接乱改。
```

---

## 给维护者的确定性执行方式

如果你是在仓库里手工验证，新增 / 扩容默认走单入口：

```bash
python3 scripts/run_plan_pipeline.py \
  --input <request.json> \
  --config ~/.openclaw/openclaw.json \
  --pretty
```

这样可以避免：
- 同一轮里同时漂出 `bind-existing` / `create-new` 两套冲突链路
- 中间 JSON 已经非法，但后面还继续让模型补洞
- 校验失败后仍然误入 apply

### 运行层验证

如果 bot 已接入但“不回复”，优先直接查运行放行链：

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

## 当前版本的产品化改造重点

这版重点不是继续堆概念，
而是把首次接入路径收窄成：

1. 用户只给最少必要信息
2. 系统先扫描当前环境
3. 系统先给方案预览或排查结论
4. 真正会影响现有路由 / 默认 Agent / 会话连续性的改动，再确认

换句话说：

> 这不是一个让用户手工拼配置的 skill，
> 而是一个先帮用户判断、再帮用户落地的 Feishu 接入 / 排障 skill。
