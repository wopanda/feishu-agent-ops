---
name: feishu-agent-ops
description: 当用户要把飞书机器人接入 OpenClaw,或排查多机器人 / 多 Agent 环境异常时使用。前台只保留两个入口:新增/扩容龙虾、排查/修复问题。默认主打新增/扩容;排障作为次入口。LLM 负责识别场景、补最少信息、解释结果;确定性脚本负责扫描、校验、patch、执行、验证。
---

# Feishu Agent Ops

这是一个把飞书机器人接入 OpenClaw 多 Agent 的 **双支线 skill**。

它前台只做两类事:
- **新增 / 扩容龙虾**
- **排查 / 修复问题**

其中:
- **新增 / 扩容** 是主入口
- **排查 / 修复** 是次入口

不要再把它当成一个让用户手工拼配置的运维工具箱。
它的目标是:

> 用户先说目标和最少必要信息;系统先判断、先扫描、先给预览;真正需要改配置时,再确认和执行。

---

## 一、前台心智:保留两个入口,但新增线内部按场景分流

### 入口 A:新增 / 扩容龙虾(主入口)

入口 A 内部自动判断当前是哪种场景:

**场景 A1:bootstrap(1 → 2)** - 当前只有 1 只龙虾,首次扩展为多只
- 别名:`scenario: bootstrap`, `goal: from_one_to_many`
- 关键差异:现有 bot 可能没有显式 binding、`session.dmScope` 可能未设为 `per-account-channel-peer`、`agents.list` / `bindings` 数组可能需要从无到有初始化
- 流程:扫描识别单龙虾 → 先升级基础结构(dmScope、binding 补齐) → 再追加新龙虾

**场景 A2:expand(N → N+1)** - 已经多龙虾,再扩一只
- 别名:`scenario: expand`, `goal: add_more_agents`
- 关键差异:结构已稳定,直接追加 agent + account + binding 即可
- 流程:扫描 → 追加预览 → 写入 → 等热加载

默认目标:
- 先扫描判断场景(bootstrap vs expand),再做对应处理
- 让用户尽量只给最少必要信息
- 先给预览,不直接改
- 让首次成功路径尽量顺滑

### 入口 B:排查 / 修复问题(次入口)
适用场景:
- 某个 bot 不回复
- 会话串了
- 路由错了
- 多龙虾环境异常

默认目标:
- 先进入只读扫描
- 先给根因判断
- 修复前必须确认

---

## 二、最少必要信息

### 新增 / 扩容默认只先收
1. `appId`
2. `appSecret`
3. `botName`

⚠️ **必填约束**:`channels.feishu.accounts.<accountId>.name` 字段 **必须填写**(取 `botName`),不可省略。
缺此字段会导致 OpenClaw 的 bot 发现机制输出 `No valid account config for accountId=... skipping agent=...`,该 bot 无法接收和回复消息。此前 rixin10/rixin11 因此被 skip 就是典型踩坑。

- 收到后先扫描当前环境,判断是 **bootstrap(1→2)还是 expand(N→N+1)**
- 若是 bootstrap:预览中需明确列出**结构升级项**(dmScope、现有 bot binding 补登记等),不能只加新 bot
- 若是 expand:环境已成熟,追加 agent + account + binding 即可。追加 account 时强制包含 `name` 字段。

如果用户已经给了这 3 个信息:
- 不要继续表单式追问
- 先扫描当前环境
- 再给接入预览

### 这些信息默认可后补 / 可推断
- `accountId`
- `agentId`
- `roleName`
- `model`
- `isDefault`
- `chatId`

规则:
- `accountId` 不会填时,由系统基于 `botName` 给建议值
- `agentId` 只有用户明确说要绑定已有 Agent 时才需要
- `chatId` 只有明确做群聊级绑定时才需要
- 其余高级字段默认后置,不要一开始就压给用户

### 排查 / 修复默认只先收
- 异常现象
- 哪几个 bot 受影响(如果用户知道)

如果用户说不清受影响 bot:
- 不要卡住
- 先做只读扫描

---

## 三、渐进式披露规则

### 第 1 步:先识别属于哪条支线
只先判断:
- 新增 / 扩容
- 排查 / 修复

不要一上来让用户选:
- `plan`
- `apply`
- `inspect`
- `root-cause`
- `repair`

这些词是内部执行阶段,不是前台主入口。

### 第 2 步:只补最少缺失信息
#### 对新增 / 扩容
默认只补:
- `appId`
- `appSecret`
- `botName`

只有在这些情况下再追问:
- 用户明确要绑定已有 Agent → 追问 `agentId`
- 用户明确要群聊级绑定 → 追问 `chatId`
- 当前环境存在冲突,必须用户拍板 → 提一个最小决策问题

#### 对排查 / 修复
默认只补:
- 现象是什么

规则:
- 默认直接开始只读扫描
- 只有用户明确说"先不要检查"时才停下

### 第 3 步:先出预览 / 诊断,不直接改
- 新增 / 扩容:先出目标结构预览 + patch 预览 + 验证路径
- 排查 / 修复:先出根因判断 + 修复建议 + 风险说明

### 第 4 步:影响真实环境时才确认
必须确认的情况:
- 真正写配置并执行 apply
- 修改 `session.dmScope`
- 调整默认 Agent
- 处理可能影响已有会话连续性的改动
- 涉及插件切换或兼容链重定向

---

## 四、代码与 LLM 的边界

## A. LLM 负责什么
LLM 负责:
- 识别用户属于哪条支线
- 把模糊自然语言整理成结构化请求
- 把 `interaction_contract` 的确定性结果翻译成简洁的人话
- 优先使用 `userReply.message` 回复用户;不得展示 `canProceed` / `confirmationRequired` / `nextAction` 等内部字段名
- 给出风险解释与下一步建议

LLM 不负责:
- 自己决定还能不能继续
- 自己决定要不要 apply
- 自己发明需要追问的字段
- 在校验失败时绕过脚本继续补洞

## B. 确定性脚本负责什么
这些部分尽量交给代码,不让 LLM 猜:
- 配置读取与结构判断
- 插件兼容探测
- 当前状态扫描
- desired state 构造
- diff / patch 生成
- 冲突检测
- 过程交互契约:缺什么、是否可继续、是否需要确认、下一步问什么
- 用户可见文案渲染:把内部契约转成可直接发送的人话,并检查内部字段泄漏
- apply 前备份
- apply 执行
- apply 后验证
- allowFrom / pairing / logs 探针

### 边界原则
> LLM 决定"现在走哪条线、还缺什么信息、怎么讲给用户听";
> 代码决定"现场是什么、能不能改、该怎么改、改完是否真的成功"。

---

## 五、内部执行模型

### 支线 A：新增 / 扩容流水线

默认先判断场景，再走对应流：

**场景 A1 — bootstrap（1→2）**：

```text
normalize_request
-> scan_current_state → 识别为单龙虾
-> bootstrap_checklist:
   - 检查 dmScope 是否为 per-account-channel-peer
   - 检查现有 bot 是否有显式 binding
   - 检查 agents.list / bindings 结构是否就绪
-> build_bootstrap_plan (结构升级 + 新 bot 追加)
-> validate_plan
-> generate_patch
-> interaction_contract
-> render_user_reply
-> apply
-> verify_setup
-> wait_for_reload
```

**场景 A2 — expand（N→N+1）**：

```text
normalize_request
-> scan_current_state → 识别为多龙虾
-> build_desired_state (仅追加,account 必须含 name 字段)
-> validate_plan (校验 accounts.<id>.name 不为空)
-> generate_patch
-> interaction_contract
-> render_user_reply
-> apply
-> verify_setup
-> wait_for_reload
```

设计要求：
- 中间 JSON 非法就失败即停
- 先预览，再写入
- 写入后再验证
- 过程交互由 `interaction_contract` 给出确定性口径：缺什么、能不能继续、是否要确认、下一句该问什么
- `interaction_contract` 是内部控制结果，**禁止原样展示给用户**；用户可见回复必须使用 `render_user_reply` 的 `message`
- 不允许 LLM 在非法分支上继续补洞硬猜
- bootstrap 场景下，结构升级项（dmScope、现有 bot binding）必须在预览中显式列出，不能静默跳过

### 写入后无需重启(关键)

OpenClaw Gateway 会自动检测 `openclaw.json` 变更并热加载飞书 channel:

- 日志中出现 `[reload] config change detected` 即表示已捕获变更
- 热加载会在当前活跃操作完成后自动执行(通常 30-60 秒内)
- **严禁写入配置后手动执行 `openclaw gateway restart`**--这会打断正在进行的自动热加载流程,反而拖慢生效
- 验证方式:`journalctl --user -u openclaw-gateway.service -f` 观察日志,看到 `[plugins] [feishu-bot-chat] N bots active: ..., <new_id>` 即完成

### 支线 B:排查 / 修复流水线
默认走:

```text
scan_openclaw_compat
-> scan_current_state / runtime verify
-> root-cause
-> minimal repair plan
-> verify
```

设计要求:
- 兼容探测优先
- 根因优先于表面修补
- 默认最小修复,不做大范围重写

---

## 六、Root-Cause-First 只用于排障线

在 diagnose / repair 场景,优先按这 4 层排查:

### 第 1 层:会话隔离层
- 检查 `session.dmScope`
- 多账号飞书优先关注:`per-account-channel-peer`

### 第 2 层:账号与路由闭环层
- 对齐 `channels.feishu.accounts` 与 `bindings`
- 检查 `accountId -> agentId` 是否闭环
- 检查默认 Agent 是否抢路由
- **检查 `accounts.<id>.name` 是否缺失**→ 日志关键字:`No valid account config for accountId=... skipping agent=...`,缺 name 会导致 bot 发现被跳过,完全无法收发消息

### 第 3 层:目录与 agent 结构层
- 检查 `workspace-*`
- 检查 `agents/<id>/agent`
- 检查目录与路由映射是否一致

### 第 4 层:插件与运行层
- 检查插件链和 duplicate warning
- 检查 allowFrom / pairing / logs 中的运行告警

注意:
- 不要把这套重型排障链强塞给新增 / 扩容用户
- 新增线只有在扫描检测到异常冲突时,才转入排障思路

---

## 七、完成反馈契约

执行完成后,必须主动回用户,不要停在内部执行完成。

默认只用这 3 行:
1. 结论:已完成 / 已发现问题
2. 依据:一句最关键验证依据
3. 下一步:只有真的需要用户决定时才写

禁止:
- 做完不报结果
- 让用户靠等待来猜状态
- 大段复述内部步骤

---

## 八、安全护栏

- 未备份,不执行 apply
- 未预览,不直接改配置
- 遇到命名冲突 / 默认 Agent 冲突 / binding 冲突时先停下
- repair 默认只做最小修复,不大范围重写
- 没有验证依据,不说"已完成可用"
- 扫描失败后,不允许 LLM 继续自由脑补 patch
- **写入配置后禁止手动重启 Gateway**--依靠自动热加载;手动重启会打断热加载流程,延迟生效

---

## 九、一句话心法

> 主打顺滑新增,保留明确排障;
> 让 LLM 回到协调层,让代码成为主引擎。
