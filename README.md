# Feishu Agent Ops

把你已经创建好的多个飞书机器人，接成 OpenClaw 多 Agent。  
支持新增、扩容、巡检、根因排查和修复。

---

## 这版先改什么

这版开始把前台心智从 **action-first** 改成 **scenario-first**。

也就是说，用户不用先理解：
- `plan`
- `apply`
- `inspect`
- `repair`

而是先判断自己属于哪种场景：

1. **一只龙虾变多只**
2. **多只龙虾继续扩更多**
3. **多只龙虾出了问题**

动作还在，但它们退到后台，作为内部执行阶段。

---

## 三个主场景

### 场景 A：一只龙虾变多只
适合：
- 现在只有 1 个 bot / 1 个 Agent
- 想扩成多个专职机器人
- 希望先看规划，再落地

你可以直接说：

```text
我现在只有一只龙虾，想扩成多只。先帮我判断该怎么拆，再给我预览。
```

### 场景 B：多只龙虾继续扩更多
适合：
- 已经有多 Agent / 多 bot
- 想继续增量扩容
- 不想覆盖旧配置

你可以直接说：

```text
我已经有多只龙虾了，下面是新机器人的信息，帮我增量扩进去，不要覆盖旧配置。
```

### 场景 C：多只龙虾出了问题
适合：
- 串会话
- 某个 bot 不回复
- 路由偶尔跑错
- 升级后字段/插件链路变了，担心修偏

你可以直接说：

```text
这套多龙虾现在有异常，先帮我判断当前环境，再找根因，不要直接硬修。
```

---

## 渐进式披露怎么做

### 第 1 步：先识别场景
先判断你属于：
- bootstrap（1 → N）
- expand（N → N+M）
- diagnose（N 出问题）

### 第 2 步：只问最少问题

#### bootstrap / expand 默认只问：
- 绑定已有 Agent，还是新建 Agent？
- 账户级绑定，还是群聊级绑定？
- 新 bot 的基本信息是什么？

#### diagnose 默认只问：
- 异常现象是什么？
- 哪几个 bot 受影响？
- 是否允许先做只读扫描？

### 第 3 步：必要时先做兼容探测
满足这些情况就先跑 compat scan：
- 不确定当前 OpenClaw 版本
- 不确定当前生效的是旧 `feishu` 还是官方 `openclaw-lark`
- 怀疑升级后字段结构变了
- 现场存在插件覆盖、历史残留、多版本混用

命令：

```bash
python3 scripts/scan_openclaw_compat.py --config ~/.openclaw/openclaw.json
```

### 第 4 步：再扫当前现场
兼容探测确认没走偏后，再把当前现场压成结构化 observed state：

```bash
python3 scripts/scan_current_state.py --config ~/.openclaw/openclaw.json --pretty
```

### 第 5 步：再构造目标预览
把“归一化请求 + 当前现场”合成目标预览：

```bash
python3 scripts/build_desired_state.py \
  --request examples/output-normalized-bootstrap.json \
  --observed examples/output-observed-state.json \
  --pretty
```

### 第 6 步：确认后再 apply / repair
- 先备份
- 再 patch
- 最后验证

---

## 你会得到什么

### bootstrap / expand
- 建议的 bot → agent 映射
- 建议的 `accounts + bindings`
- 建议的 `workspace / agentDir`
- 增量变更预览
- 第一次成功验证清单

### diagnose
- 兼容探测结果
- 当前现场结构化扫描结果
- 根因诊断结论
- 修复优先级
- 最小修复建议
- 修后验证路径

---

## 后台动作仍然保留

虽然前台改成按场景进入，但后台仍然会用这些动作：

- `compat-scan`
- `normalize-request`
- `scan-current-state`
- `build-desired-state`
- `plan`
- `apply`
- `inspect`
- `root-cause`
- `repair`

只是现在的顺序变成：

- **先判场景**
- **再决定动作链**

而不是让用户自己先选动作。

---

## 后台现在已经开始代码化

已经落下来的后台骨架：
- `scripts/scan_openclaw_compat.py`：兼容探测
- `schemas/request.schema.json`：统一请求结构
- `scripts/normalize_request.py`：把旧输入 / 场景输入统一归一化成内部请求对象
- `schemas/observed-state.schema.json`：当前现场结构
- `scripts/scan_current_state.py`：把当前配置压成 observed state
- `schemas/desired-state.schema.json`：目标预览结构
- `scripts/build_desired_state.py`：从 request + observed 生成目标预览

示例：

```bash
python3 scripts/normalize_request.py --input examples/input-minimal.json --pretty
python3 scripts/scan_current_state.py --config ~/.openclaw/openclaw.json --pretty
python3 scripts/build_desired_state.py --request examples/output-normalized-bootstrap.json --observed examples/output-observed-state.json --pretty
```

归一化输出样例见：
- `examples/output-normalized-bootstrap.json`

现场扫描输出样例见：
- `examples/output-observed-state.json`

目标预览输出样例见：
- `examples/output-desired-state-preview.json`

如果你要验证“真正从空白单体开始 bootstrap”的情况，还可以看：
- `examples/observed-state-bootstrap-empty.json`

---

## 推荐输入方式

### 场景 A：bootstrap
见：
- `examples/scenario-bootstrap.json`

### 场景 B：expand
见：
- `examples/scenario-expand.json`

### 场景 C：diagnose
见：
- `examples/scenario-diagnose.json`

兼容探测输出样例见：
- `examples/output-compat-scan.json`

归一化输出样例见：
- `examples/output-normalized-bootstrap.json`

现场扫描输出样例见：
- `examples/output-observed-state.json`

目标预览输出样例见：
- `examples/output-desired-state-preview.json`

空白 bootstrap 现场样例见：
- `examples/observed-state-bootstrap-empty.json`

---

## 当前默认先盯的高频风险

1. `session.dmScope` 不适合多账号隔离  
2. `accounts` 与 `bindings` 没有真正闭环  
3. 插件链路重复覆盖、实际生效实现不清楚  
4. OpenClaw 版本 / 插件版本 / 字段结构已经漂移，但还按旧心智在修

---

## 下一阶段再做什么

下一阶段会继续把后台也做成更确定性的结构：
- plan 校验
- patch 生成
- apply / verify 分离

一句话：

> 前台先变流畅，后台再变确定性。
