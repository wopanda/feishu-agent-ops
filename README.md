# Feishu Agent Ops

把飞书机器人接入 OpenClaw 多 Agent。

它现在的主定位很简单：
- **主入口：新增 / 扩容龙虾**
- **次入口：排查 / 修复问题**

也就是说，它不再主打一堆运维动作名，
而是主打：**先把龙虾顺滑加进去；有问题时，再进入排障模式。**

---

## 你可以拿它做什么

### 1. 新增 / 扩容龙虾（主入口）
适合：
- 新增一个飞书机器人接进 OpenClaw
- 已有 1 只 / 多只龙虾，再继续扩容
- 不会填 `accountId` / `agentId`，想先让系统判断

### 2. 排查 / 修复问题（次入口）
适合：
- 某个 bot 不回复
- 会话串了
- 路由错了
- 多龙虾环境异常

---

## 第一次成功路径：先加一个龙虾

你最低只需要准备 3 个信息：
1. `appId`
2. `appSecret`
3. `botName`

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

### 系统应该怎么处理
1. 识别为新增 / 扩容线
2. 扫描当前环境
3. 给出建议的 `accountId`
4. 判断是绑定已有 Agent，还是新建 Agent
5. 给出变更预览
6. 用户确认后再落地
7. 给验证清单

### 第一次成功至少要满足
- 预览可生成
- patch 通过校验
- 配置成功写入
- 目录成功创建
- 至少 1 个新 bot 完成真实回复验证

---

## 如果是出问题了

### 直接这样发

```text
这套多飞书机器人有问题：
- 现象：某个 bot 不回复 / 串会话 / 路由错
- 先帮我检查，不要直接改
```

如果用户连 bot 名都说不清：
- 不要卡住
- 先做只读扫描

### 系统应该怎么处理
1. 识别为排障 / 修复线
2. 先做兼容探测和只读扫描
3. 给出根因判断
4. 给出最小修复建议
5. 用户确认后再修
6. 修后再验证

---

## 默认哪些信息不用先问

新增 / 扩容时，默认只先收：
- `appId`
- `appSecret`
- `botName`

这些信息默认可后补 / 可推断：
- `accountId`
- `agentId`
- `roleName`
- `model`
- `isDefault`
- `chatId`

原则：
- 能扫描就先扫描
- 能推断就不要追问
- 能预览就先预览
- 只有真正影响现有路由 / 默认 Agent / 会话连续性的改动才确认

---

## 这套能力怎么分层

### LLM 层
负责：
- 识别用户当前属于新增 / 扩容 / 排障哪一类
- 最少必要追问
- 把模糊描述整理成结构化请求
- 把结果翻译成简洁的人话

### 确定性脚本层
负责：
- 配置读取与结构判断
- 插件兼容探测
- 当前状态扫描
- desired state 构造
- 校验
- patch 生成
- apply
- verify

### 一句话边界
> LLM 决定怎么跟用户交互；代码决定现场是什么、能不能改、怎么改、改完是否成功。

---

## 内部流水线

### 新增 / 扩容线

```text
normalize_request
-> scan_current_state
-> build_desired_state
-> validate_plan
-> generate_patch
-> verify_setup
```

### 排障 / 修复线

```text
scan_openclaw_compat
-> scan_current_state / runtime verify
-> root-cause
-> minimal repair plan
-> verify
```

设计要求：
- 中间 JSON 非法就失败即停
- 预览先于写入
- 写入先于验证
- 不让 LLM 在非法分支上继续补洞

---

## 给维护者的确定性执行方式

### 1. 新增 / 扩容预览

```bash
python3 scripts/run_plan_pipeline.py \
  --input <request.json> \
  --config ~/.openclaw/openclaw.json \
  --pretty
```

用途：
- 统一走单入口规划链
- 避免同一轮里同时漂出 `bind-existing` / `create-new` 两套冲突链路
- 避免中间 JSON 已非法却继续补洞

### 2. 兼容探测

```bash
python3 scripts/scan_openclaw_compat.py \
  --config ~/.openclaw/openclaw.json
```

用途：
- 判断当前 OpenClaw / Feishu / Lark 插件链路属于哪种现场
- 在 diagnose / repair 前先确认现场不是漂移状态

### 3. 运行层验证

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
- 最近日志里是否有 `not paired`

---

## 当前版本的产品化结论

这一版最重要的不是继续堆内部概念，
而是完成 3 个切换：

1. **从单一重型运维 skill，切换成双支线能力**
2. **从 LLM 主导，切换成代码主引擎 + LLM 协调层**
3. **从“排障 / 运维感”首页，切换成“新增 / 扩容优先”首页**

一句话说完：

> 主打顺滑新增，保留明确排障；
> 让重型能力留在后台，不再拖垮首次成功路径。
