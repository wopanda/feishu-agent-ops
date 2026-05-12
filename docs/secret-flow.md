# Secret Flow

## 这份文档解决什么问题

`feishu-agent-ops` 现在已经有：
- request 归一化
- desired-state 预览
- patch preview
- dry-run apply plan
- minimal apply executor

但这里有一个关键边界：

> **预览链可以脱敏，真实落地链不能丢 secret。**

也就是说：
- `preview` 阶段需要尽量不泄露 `appSecret`
- `apply` 阶段又必须拿到真实 `appSecret`

如果这条边界不写清楚，后面很容易出现：
- 预览可跑，但真实配置落不下去
- 不小心把 secret 写进样例 / 文档 / 日志
- 错把 `patch preview` 当成真实 secret 来源

---

## 当前已经确定的规则

### 1. request 输入层可以带真实 secret
用户原始输入、场景输入、归一化输入里，允许存在真实：
- `appId`
- `appSecret`

这是因为这些字段本来就是飞书 bot 接入所必需的原始材料。

### 2. desired-state 不以 secret 为核心差异对象
`desired-state` 的重点是规划：
- 要创建哪些 account
- 要创建哪些 binding
- 要创建哪些 agent
- 路由如何组织

它不是用来公开展示 secret 的，因此后续链路不应依赖在 `desired-state` 中回显 secret。

### 3. patch preview 必须脱敏
当前 `scripts/generate_patch.py` 已明确把：

```json
"appSecret": "<redacted-at-preview>"
```

写进 preview。

这条规则是故意的，目的是：
- 避免在预览输出中泄露真实密钥
- 避免样例文件成为 secret 泄露面
- 让 review / commit / 文档展示更安全

### 4. dry-run / verify 阶段都不能把 secret 再还原出来
这些阶段只负责：
- 看计划
- 看顺序
- 看验证清单

它们都不应该负责恢复真实 `appSecret`。

### 5. real apply 不能只依赖 patch preview
这是一条最关键规则：

> **`apply_real.py` 未来真正用于生产写入时，不能只拿 `output-patch-preview.json` 作为唯一输入。**

原因很简单：
- preview 里的 secret 已经被脱敏
- `"<redacted-at-preview>"` 不能写进真实配置
- 真实 apply 如果只吃 preview，必然丢 secret

---

## 当前阶段的安全边界

截至目前，仓库中的执行链可以分成两类：

### A. 可公开 / 可示例链
这些阶段可以安全保留样例：
- `normalize_request.py`（仅样例环境）
- `build_desired_state.py`
- `validate_plan.py`
- `generate_patch.py`
- `apply_patch.py`
- `verify_setup.py`

但其中最需要注意的是：
- `generate_patch.py` 输出给 review 的 preview **必须脱敏**

### B. 不应直接依赖样例落真实配置的链
这些阶段一旦接近真实生产写入，就必须重新处理 secret：
- `apply_real.py`
- 后续任何真正写 `~/.openclaw/openclaw.json` 的执行器

---

## 未来真实 apply 的推荐 secret 来源

后面如果把 `apply_real.py` 做成真正可生产使用，推荐只允许从下面几类来源拿真实 secret：

### 方案 1：直接读取原始 normalized request
由真实的 request / normalized request 提供：
- `accountId`
- `appId`
- `appSecret`

再由 apply 阶段把：
- 规划结果
- patch 结果
- 原始 secret

在内存里重新合并后写配置。

**优点**：
- 最直接
- 不需要引入额外 secret 存储层

**缺点**：
- request 文件本身就变成敏感材料
- 不能随便落样例、随便 commit

### 方案 2：单独的 secret map 输入
给 real apply 单独传一个 secrets 文件或对象，例如：

```json
{
  "accounts": {
    "manager": { "appSecret": "..." },
    "research": { "appSecret": "..." },
    "writer": { "appSecret": "..." }
  }
}
```

可参考：
- schema：`schemas/apply-secrets.schema.json`
- example：`examples/input-apply-secrets.json`

然后按 `accountId` 合并。

**优点**：
- 预览与 secret 解耦更彻底
- 更适合分阶段审批

**缺点**：
- 调用链更复杂
- 需要额外的 secret 文件管理规则

### 方案 3：环境变量 / 密钥管理器
由：
- 环境变量
- 外部密钥管理器
- 受控 vault

提供真实 secret，再由 apply 阶段解析。

**优点**：
- 最接近生产级安全模型

**缺点**：
- 当前仓库阶段还太早
- 超出这版最小骨架范围

---

## 明确禁止的 secret 来源

下面这些来源，**不能**作为真实 apply 的可信 secret 源：

### 1. `output-patch-preview.json`
因为其中的 secret 已经被替换成：
- `"<redacted-at-preview>"`

### 2. README / SKILL / examples 里的展示样例
这些文件天然会被：
- 阅读
- diff
- commit
- 发布

不应承载生产 secret。

### 3. 聊天记录 / 评审记录 / 日志回放
哪怕用户在对话里贴过 secret，也不应该把聊天记录当成稳定 secret 来源。

### 4. 任何被脱敏后再“猜回去”的字段
脱敏是单向边界，不允许后续阶段尝试从 preview 恢复真实值。

---

## 对 `apply_real.py` 的当前结论

当前 `scripts/apply_real.py` 只是：
- 最小执行骨架
- 支持 `add + mkdir`
- 支持 `--execute`
- 支持 `--secrets <path>` 按 `accountId` 注入真实 `appSecret`

但它**还不能被视为真正可生产使用的 apply 引擎**，原因之一就是：

> 它当前没有完整的真实 secret 注入机制。

所以在 secret flow 设计没补完之前，应把它视为：
- 结构验证工具
- 本地受控实验工具
- 带显式 secret 注入 contract 的最小执行骨架

而不是生产级落地器。

---

## 推荐的后续演进顺序

建议按下面顺序继续补：

1. 明确 real apply 的 secret 输入 contract
2. 再决定 secret 来源是 `normalized request` 还是 `secret map`
3. 再扩 `apply_real.py` 的真实写入能力
4. 最后再补 live verification

---

## 一句话原则

> **Preview 可以脱敏，Real Apply 必须显式注入真实 secret；绝不能把脱敏 preview 当成生产密钥来源。**
