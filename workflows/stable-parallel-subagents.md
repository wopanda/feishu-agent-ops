# 稳定版并行子Agent工作流（WeCom 友好）

## 目标
在企业微信等通道上，避免依赖子Agent自动 announce 直接回前台，改为：

1. **子Agent并行产出**
2. **结果落盘到 workspace**
3. **主Agent负责进度提示与最终统一汇总回复**

这样可以规避：
- 并行 announce 乱序
- 子Agent结果漏显
- 前台重复消息
- 不同通道展示不一致

## 推荐目录结构

```text
.parallel-runs/<run-id>/
  manifest.md
  task-a.md
  task-b.md
  summary.md
```

## 标准步骤

### 1) 主Agent创建 run 目录
给每次并行任务创建唯一 run-id。

示例：
`/root/.openclaw/workspace/.parallel-runs/2026-03-07-apple-banana-test/`

### 2) 为每个子Agent分配唯一输出文件
每个子Agent只负责一件事，并写入自己的结果文件，例如：
- `task-a.md`
- `task-b.md`

### 3) 子Agent prompt 约束
对子Agent明确要求：
- 只完成分配任务
- 把最终结果写入指定文件
- 输出尽量简短
- 不要写额外解释
- 不要假设自己的输出会稳定显示给最终用户

### 4) 主Agent作为唯一对外交付者
主Agent读取全部结果文件后：
- 检查是否齐全
- 必要时补充整理
- 最后只发一条统一结果给用户

## 适用场景
- 并行检索
- 并行写草稿
- 并行拆分列表型任务
- 多个子任务同时分析

## 不推荐的模式
不推荐把“子Agent自动 announce 到聊天前台”当成最终交付手段，尤其是在：
- WeCom
- 多子Agent并发
- 需要稳定、可核对、可复盘的任务

## 默认约定
今后在这个环境里，若用户要求“并行子Agent”：
- 默认走 **落盘 + 主Agent汇总**
- 子Agent announce 只当作后台事件，不当作最终交付依据
- 最终以主Agent汇总消息为准

## 交付模式

### 默认模式：方案B（进度模式）
- 子Agent并行执行
- 某个子任务先完成时，由主Agent发一句进度提示
- 全部完成后，由主Agent统一汇总结果

### 说明
- 不依赖子Agent自动回前台
- 进度提示由主Agent负责，对用户可见
- 最终交付以主Agent汇总消息为准
