# Feishu Agent Ops V2 重构方案（渐进式披露版）

## 为什么要重构
当前版本把“新增/扩容/巡检/根因排查/修复”都塞进一个 action 列表里。
这对技术视角是清晰的，但对用户视角不够顺：

- 用户先想到的是 **我现在处于什么状态**，不是先想到 `plan / inspect / repair`
- 从 1 只龙虾变多只，和多只龙虾已经异常，本质不是同一类任务
- 文档承诺偏“安装/接入型体验”，当前实现已经漂到“排障/运维型体验”

因此 V2 应改成：

> **场景优先（scenario-first） + 渐进式披露（progressive disclosure） + 能代码化的尽量代码化。**

---

## 第一性原理拆解

### 用户真正要解决的不是“配置”，而是 3 类状态迁移

#### 场景 A：1 → N（从一只龙虾变多只）
目标：在现有单 Agent / 单 bot 基础上，新增多个 bot / Agent。

用户关心：
- 我要准备什么
- 会新增哪些 bot / Agent
- 会不会影响当前正在用的那只龙虾
- 第一次成功怎么验证

#### 场景 B：N → N + M（已有多只，再扩更多）
目标：在现有多 Agent 体系上增量扩容。

用户关心：
- 不要覆盖旧配置
- 新增 bot 跟旧 bot 的路由别打架
- workspace / agentDir 命名别乱
- 扩进去后能快速验证

#### 场景 C：N 出问题（多只龙虾已经异常）
目标：诊断并修复现有多 Agent 环境。

用户关心：
- 到底哪里出问题
- 根因是什么，不要只给表面修法
- 修完会不会影响已有会话
- 能不能最小修复、可回滚

---

## V2 总体设计

## 1. 前台改成“场景入口”，不是“动作入口”
用户入口不再主打：
- `plan`
- `apply`
- `inspect`
- `root-cause`
- `repair`

而改成 3 个主入口：

1. **新增多龙虾**（bootstrap）
2. **继续扩容**（expand）
3. **排查修复**（diagnose/repair）

动作仍然保留，但作为内部执行阶段，不作为用户主心智入口。

---

## 2. 渐进式披露交互模型

### Level 1：先识别场景
只做 1 件事：
- 判断用户属于 A / B / C 哪种场景

### Level 2：只问最少问题

#### bootstrap / expand 只先问：
- 你是绑定已有 Agent，还是要新建 Agent？
- 这批 bot 的基础信息是什么？
- 你想按账户级绑定，还是群聊级绑定？

#### diagnose / repair 只先问：
- 当前异常现象是什么？
- 哪几个 bot 受影响？
- 是否允许我先做只读巡检？

### Level 3：先出预览，不直接改
- 新增/扩容：出 **目标结构预览 + 配置 diff 预览 + 验证路径**
- 排障：出 **根因诊断 + 修复优先级 + 风险说明**

### Level 4：只有用户确认后才 apply / repair
- 变更前强制备份
- 变更后强制验证

### Level 5：高级选项后置
高级项不要一上来打到用户脸上：
- `dmScope`
- 默认 Agent 争抢
- plugin duplicate warning
- `workspace / agentDir` 规范
- 群聊路由优先级

这些只在：
- 用户主动展开
- 系统检测到冲突
- 进入异常修复场景
时再披露。

---

## 3. 能代码化的尽量代码化

### 应该代码化的部分

#### 3.1 场景识别后的结构化输入归一化
输入可能来自自然语言 / JSON / YAML，但落地前应统一成一个内部请求对象：

```json
{
  "scenario": "bootstrap | expand | diagnose",
  "routingMode": "account | group",
  "agentMode": "bind-existing | create-new",
  "bots": [],
  "symptoms": [],
  "configPath": "~/.openclaw/openclaw.json"
}
```

#### 3.2 当前状态扫描器（Observed State）
统一扫描并标准化输出：
- agents
- feishu accounts
- bindings
- session.dmScope
- workspace / agentDir
- plugin warnings

输出为机器可判断的数据，不只是自然语言报告。

#### 3.3 目标状态构造器（Desired State Builder）
根据场景生成目标结构：
- 该新增哪些 account
- 该绑定哪些 agent
- 是否新建 agent
- 该生成哪些 workspace / agentDir
- 是否需要建议调整 `dmScope`

#### 3.4 Diff / Patch 生成器
不要直接硬改配置，先生成：
- 计划新增项
- 计划变更项
- 风险项
- 冲突项

#### 3.5 校验器（Validator）
必须程序化检查：
- accountId 唯一性
- botName/agentId 冲突
- bindings 闭环
- 群聊路由优先级冲突
- workspace / agentDir 是否存在
- 默认 Agent 是否会抢路由

#### 3.6 执行器（Apply / Repair Executor）
只做确定性动作：
- 备份
- patch openclaw.json
- 建目录
- 输出变更报告
- 调用重启
- 调用验证

#### 3.7 验证器（Verifier）
按场景输出不同验证链：
- bootstrap / expand：至少 1 个新 bot 成功回复
- diagnose / repair：原高优先级告警是否消失

---

## 4. 不必过度代码化的部分
这些适合保留在 skill 层：
- 自然语言意图理解
- 用户问答与确认
- 最终报告生成
- 风险解释与下一步建议

原则：
> **判断与 patch 尽量代码化；解释与交互保留在 skill 层。**

---

## V2 推荐模块结构

```text
feishu-agent-ops/
├── SKILL.md                      # 用户入口（场景优先）
├── README.md
├── docs/
│   ├── scenario-model.md
│   ├── bootstrap-flow.md
│   ├── expand-flow.md
│   ├── diagnose-flow.md
│   └── routing-strategies.md
├── schemas/
│   ├── request.schema.json
│   ├── observed-state.schema.json
│   ├── desired-state.schema.json
│   └── plan-preview.schema.json
├── scripts/
│   ├── scan_state.py
│   ├── normalize_request.py
│   ├── build_desired_state.py
│   ├── validate_plan.py
│   ├── generate_patch.py
│   ├── apply_patch.py
│   ├── verify_setup.py
│   └── verify_repair.py
├── templates/
│   ├── scenario-preview.md
│   ├── bootstrap-plan.md
│   ├── expand-plan.md
│   ├── diagnose-report.md
│   ├── repair-report.md
│   └── apply-report.md
└── examples/
    ├── bootstrap-account-routing.json
    ├── bootstrap-group-routing.json
    ├── expand-existing-system.json
    └── diagnose-routing-conflict.json
```

---

## V2 的路由抽象
V1 太偏账户级绑定闭环，V2 应显式把路由策略抽象出来：

### Routing Strategy A：账户级绑定
- 一个 bot 对一个 Agent
- 最适合私聊机器人一对一

### Routing Strategy B：群聊级绑定
- 特定群聊路由到特定 Agent
- 优先级高于账户级绑定

### Routing Strategy C：混合策略
- 默认账户级
- 局部群聊覆盖

这样就能把文档里的“账户级 / 群聊级”重新纳回主能力，而不是变成边角说明。

---

## V2 的 Agent 策略抽象
也要显式拆成两条：

### Agent Mode A：绑定已有 Agent
用户已经有 Agent，只需要把 bot 接过去。

### Agent Mode B：创建新 Agent 并绑定
用户只知道自己想要一个“日程小助手 / 运维助手 / 写作助手”，这时 skill 要生成：
- agentId 建议
- workspace 建议
- agentDir 建议
- 绑定方案预览

这正是旧文档承诺、但 V1 没有前台化做强的地方。

---

## 推荐的前台对话体验

### 场景 A：新增多龙虾
用户：
> 我想从 1 只龙虾扩成 4 只。

Skill：
1. 识别为 `bootstrap`
2. 只追问：
   - 绑定已有 Agent 还是新建 Agent？
   - 账户级还是群聊级？
   - bot 信息发我
3. 输出规划预览
4. 用户确认后 apply
5. 给第一次成功验证清单

### 场景 B：继续扩容
用户：
> 我已经有 5 只了，再帮我加 2 只。

Skill：
1. 识别为 `expand`
2. 先扫描现状
3. 只展示增量 diff
4. 用户确认后 apply
5. 验证新增 bot，不重讲全套

### 场景 C：多龙虾异常
用户：
> 现在多只龙虾偶尔串会话，有时候某个 bot 不回。

Skill：
1. 识别为 `diagnose`
2. 进入只读巡检
3. 输出根因优先级
4. 用户确认后最小 repair
5. 修后验证

---

## V2 的执行原则

1. **场景优先**：先判断用户状态，不先抛 action 列表。
2. **最少提问**：每个场景先问最小闭环问题。
3. **先预览后执行**：任何写入前必须出 preview。
4. **能代码化就代码化**：尤其是扫描、校验、patch、验证。
5. **路由与 Agent 双解耦**：
   - 路由模式（账户级 / 群聊级）
   - Agent 模式（绑定已有 / 新建）
6. **异常场景才根因优先**：不要把 root-cause-first 强塞给新增/扩容用户。
7. **前台简洁，后台扎实**：用户看到的是流畅分步，底层是确定性引擎。
8. **单入口流水线**：plan 类请求统一走 `run_plan_pipeline.py`，不要让 LLM 自己拼 stage 顺序或同时跑两套模式。

---

## 建议的重构顺序

### Phase 1：先重写心智模型
- 重写 `SKILL.md`
- 重写 `README.md`
- 明确 3 个场景入口
- 把 action 降为内部执行阶段

### Phase 2：先补确定性脚本层
优先补：
- `scan_state.py`
- `build_desired_state.py`
- `validate_plan.py`
- `generate_patch.py`
- `run_plan_pipeline.py`（单入口串起 normalize → observed → desired → validate → patch → verify，失败即停）

### Phase 3：再补体验层
- 场景化 examples
- 预览模板
- 报告模板
- 更 reader-facing 的安装说明

### Phase 4：最后补高级修复链
- plugin duplicate 诊断
- dmScope 风险确认
- routing conflict 分析
- rollback 完善

---

## 一句话结论
V2 不该再是“把 action 列给用户选”的 skill，
而应该变成：

> **一个按场景自动收口、按阶段渐进披露、底层由确定性脚本驱动的多飞书机器人接入/扩容/修复引擎。**
