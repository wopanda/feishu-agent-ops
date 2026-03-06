---
name: wechat-publisher
description: 生成并发布微信公众号文章（支持参考文章迁移、标题选择、人设覆盖、自动配图与样式增强）。当用户提到“公众号文章/微信草稿箱/发布文章/选标题/人设提示词”时使用。
---

# WeChat Publisher

用于「生成+发布」微信公众号文章的本地技能。

## 目录

- 根目录：`skills/wechat-publisher/`
- 生成脚本：`scripts/generate_only.py`
- 发布脚本：`scripts/publish_only.py`
- 人设模板：`templates/persona.md`

## 核心能力

- 参考文章抽象迁移（`--reference`）
- 生成标题候选 + **强制选择标题**（交互/参数）
- 人设覆盖（`--persona-file` 或 `--persona-text`）
- 可选自动配图（`--generate-images`）
- 微信草稿发布（发布前自动上传封面图；正文图建议先转微信URL）

## 推荐工作流

1) 生成文章（含标题候选，可交互选择）

```bash
cd /root/.openclaw/workspace/skills/wechat-publisher
python3 scripts/generate_only.py --topic "你的主题" --reference "参考文本" --generate-images
```

2) 发布到草稿箱（标题默认取文章正文 H1）

```bash
cd /root/.openclaw/workspace/skills/wechat-publisher
python3 scripts/publish_only.py --content-file "output/xxx.md"
```

## 常用参数

### generate_only.py

- `--topic` 主题
- `--reference` 参考文章文本
- `--generate-images` 生成配图
- `--persona-file` 指定人设文件
- `--persona-text` 直接传人设文本
- `--title` 手动指定最终标题
- `--title-index` 按候选索引选标题

优先级：`--title` > `--title-index` > 交互选择 > 第1个候选（非交互）

### publish_only.py

- `--content-file` 文章 markdown 文件（推荐）
- `--title` 可覆盖标题（不传则自动取正文首个 H1）
- `--author` 作者署名
- `--cover-image` 封面图路径（可选）

## 配置文件

- `config/credentials.json`（密钥）
- `config/settings.json`（作者等）

> 注意：敏感配置和 output 已在 workspace 根 `.gitignore` 忽略，不要提交密钥。
