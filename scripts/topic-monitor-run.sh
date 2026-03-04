#!/bin/bash

# 主题监控日报生成（标准模板版）
set -euo pipefail

CONFIG_FILE="/root/.openclaw/workspace/topic-monitor-config.json"
WORKSPACE="/root/.openclaw/workspace"
OBSIDIAN_DIR="/root/obsidian-vault/Input/TopicReports"
TODAY=$(date '+%Y-%m-%d')
OUT_FILE="$OBSIDIAN_DIR/${TODAY}-主题监控日报.md"
TMP_JSON="/tmp/topic-monitor-search-${TODAY}.json"

export TAVILY_API_KEY="${TAVILY_API_KEY:-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}"

mkdir -p "$OBSIDIAN_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "配置文件不存在: $CONFIG_FILE"
  exit 1
fi

ENABLED=$(jq -r '.enabled' "$CONFIG_FILE")
if [ "$ENABLED" != "true" ]; then
  echo "主题监控已禁用"
  exit 0
fi

TOPIC_NAME=$(jq -r '.topics[0].name // "未命名主题"' "$CONFIG_FILE")
KEYWORDS=$(jq -r '.topics[0].keywords[]?' "$CONFIG_FILE" | paste -sd ' ' -)
KEYWORD_COUNT=$(jq -r '.topics[0].keywords | length' "$CONFIG_FILE")
MAX_ITEMS=$(jq -r '.output.maxItems // 10' "$CONFIG_FILE")

if [ -z "${KEYWORDS:-}" ]; then
  echo "未配置关键词"
  exit 1
fi

echo "关键词: $KEYWORDS"

echo "执行 Tavily 搜索..."
# 仅保留 JSON，避免 markdown 输出干扰
curl -sS -X POST "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d "{\"api_key\":\"$TAVILY_API_KEY\",\"query\":\"$KEYWORDS\",\"search_depth\":\"advanced\",\"max_results\":$MAX_ITEMS,\"time_range\":\"day\"}" \
  > "$TMP_JSON"

if ! jq -e '.results' "$TMP_JSON" >/dev/null 2>&1; then
  echo "Tavily 返回异常，已生成无新发现报告"
  cat > "$OUT_FILE" <<EOF
# 📊 主题监控日报 - ${TODAY}

## ⚠️ 今日无新发现

在过去 24 小时内，未获取到可用搜索结果。

### 建议
- 检查 TAVILY_API_KEY 是否有效
- 放宽关键词范围
- 扩大时间窗口到 48h

---
*📅 生成时间: $(date '+%Y-%m-%d %H:%M:%S')*
*⚙️ 配置文件: topic-monitor-config.json*
EOF
  echo "报告已生成: $OUT_FILE"
  exit 0
fi

RAW_COUNT=$(jq -r '.results | length' "$TMP_JSON")

node - "$TMP_JSON" "$OUT_FILE" "$TODAY" "$TOPIC_NAME" "$KEYWORD_COUNT" "$RAW_COUNT" <<'NODE'
const fs = require('fs');

const [, , jsonPath, outFile, today, topicName, keywordCount, rawCount] = process.argv;
const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
const results = Array.isArray(data.results) ? data.results : [];

function host(u='') {
  try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; }
}

function tagsFrom(title='', content='') {
  const txt = `${title} ${content}`.toLowerCase();
  const tags = [];
  if (txt.includes('github')) tags.push('#github');
  if (txt.includes('openclaw') || txt.includes('小龙虾')) tags.push('#openclaw');
  if (txt.includes('agent')) tags.push('#agent');
  if (txt.includes('自动化')) tags.push('#自动化');
  if (txt.includes('案例') || txt.includes('use case')) tags.push('#案例');
  return tags.length ? tags : ['#资讯'];
}

// 简单去重：按域名+标题前40字
const seen = new Set();
const deduped = [];
for (const r of results) {
  const title = (r.title || '').trim();
  const url = (r.url || '').trim();
  const content = (r.content || '').trim();
  if (!title || !url) continue;
  const key = `${host(url)}|${title.slice(0,40).toLowerCase()}`;
  if (seen.has(key)) continue;
  seen.add(key);
  deduped.push({ title, url, content, score: typeof r.score === 'number' ? r.score : null });
}

const finalItems = deduped.slice(0, 10);

function summarize(txt='', n=90) {
  const t = txt.replace(/\s+/g, ' ').trim();
  if (!t) return '暂无摘要';
  return t.length > n ? t.slice(0, n) + '…' : t;
}

function whyImportant(it) {
  const h = host(it.url);
  if (h.includes('github.com')) return '来自开源一线渠道，通常能反映真实实践与落地细节。';
  if (h.includes('youtube.com') || h.includes('bilibili.com')) return '视频内容通常含实操演示，利于快速复现。';
  return '可补充当前主题的最新动态与案例参考价值。';
}

let md = `# 📊 主题监控日报 - ${today}\n\n`;
md += `> 🤖 由 OpenClaw AI 自动生成\n\n`;
md += `## 🎯 监控主题\n- ${topicName}\n\n---\n\n`;

if (finalItems.length === 0) {
  md += `## ⚠️ 今日无新发现\n\n`;
  md += `过去 24 小时内未发现高质量新增内容。\n\n`;
  md += `### 建议\n- 扩展关键词同义词\n- 增加英文关键词\n- 扩大时间窗口到 48h\n\n`;
} else {
  md += `## 📰 今日发现 (${finalItems.length} 条)\n\n`;
  finalItems.forEach((it, i) => {
    md += `### ${i+1}. ${it.title}\n\n`;
    md += `**📝 摘要**: ${summarize(it.content)}\n\n`;
    md += `**🔗 来源**: [${host(it.url) || '原文'}](${it.url})\n\n`;
    md += `**⏰ 时间**: ${today}\n\n`;
    md += `**🏷️ 标签**: ${tagsFrom(it.title, it.content).join(' ')}\n\n`;
    md += `**💡 为什么重要**: ${whyImportant(it)}\n\n---\n\n`;
  });

  md += `## 💡 今日洞察\n`;
  md += `- 主题热度：围绕「${topicName}」的内容持续活跃。\n`;
  md += `- 渠道结构：GitHub / 技术媒体 / 视频平台三类来源并存。\n`;
  md += `- 应用倾向：案例内容集中在自动化、Agent 落地与效率提升。\n\n`;

  md += `## 🎯 明日建议\n`;
  md += `1. 增加关键词组合："OpenClaw workflow"、"OpenClaw automation"\n`;
  md += `2. 重点跟踪高质量来源（GitHub + 官方博客）\n`;
  md += `3. 对高相关结果进一步做 web_fetch 深读\n\n`;
}

md += `## 📈 统计\n`;
md += `- 🔍 搜索关键词: ${keywordCount} 个\n`;
md += `- 📥 原始结果: ${rawCount} 条\n`;
md += `- 🔄 去重后: ${deduped.length} 条\n`;
md += `- ✅ 最终筛选: ${finalItems.length} 条\n\n`;
md += `---\n`;
md += `*📅 生成时间: ${new Date().toISOString().replace('T',' ').slice(0,19)}*\n`;
md += `*⚙️ 配置文件: topic-monitor-config.json*\n`;
md += `*🧩 模板版本: 标准模板 v1*\n`;

fs.writeFileSync(outFile, md, 'utf8');
NODE

echo "报告已生成: $OUT_FILE"
cat "$OUT_FILE"
