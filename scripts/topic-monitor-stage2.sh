#!/bin/bash

# 主题监控 Stage2：文件级硬校验 + 摘要输出（供 cron announce 直接投递）
set -euo pipefail

REPORT_DIR="/root/obsidian-vault/Input/TopicReports"
TODAY="$(TZ=Asia/Shanghai date +%F)"
FILE="${REPORT_DIR}/${TODAY}-主题监控日报.md"

if [ ! -s "$FILE" ]; then
  echo "Stage2跳过：未找到今日日报文件，不推送摘要。"
  exit 0
fi

for kw in "今日发现" "今日洞察" "明日建议" "统计"; do
  if ! grep -q "$kw" "$FILE"; then
    echo "Stage2跳过：日报模板不完整，不推送摘要。"
    exit 0
  fi
done

python3 - "$FILE" "$TODAY" <<'PY'
import re, sys

file_path = sys.argv[1]
today = sys.argv[2]
text = open(file_path, 'r', encoding='utf-8').read()

m = re.search(r'##\s*📰\s*今日发现\s*\((\d+)\s*条\)', text)
count = m.group(1) if m else "?"

# 提取条目标题与“为什么重要”
entries = []
blocks = re.split(r'\n###\s+\d+\.\s+', "\n" + text)
for b in blocks[1:]:
    title = b.splitlines()[0].strip()
    why_m = re.search(r'\*\*💡\s*为什么重要\*\*:\s*(.+)', b)
    why = why_m.group(1).strip() if why_m else "可补充主题最新动态，建议关注后续演进。"
    if title:
        entries.append((title, why))

top3 = entries[:3]

insight = "围绕该主题的新增内容持续活跃，建议优先跟踪高质量来源。"
sec = re.search(r'##\s*💡\s*今日洞察\n([\s\S]*?)(?:\n##\s|\Z)', text)
if sec:
    lines = [ln.strip() for ln in sec.group(1).splitlines() if ln.strip()]
    # 优先第一条项目符号
    bullets = [ln.lstrip('-').strip() for ln in lines if ln.startswith('-')]
    if bullets:
        insight = bullets[0]
    elif lines:
        insight = lines[0]

print(f"【主题监控摘要｜{today}】")
print(f"今日发现：{count} 条（模板质检通过）")

if not top3:
    print("1) 未提取到可用条目")
    print("   价值：请检查日报正文结构是否变更")
else:
    for idx, (title, why) in enumerate(top3, 1):
        print(f"{idx}) {title}")
        print(f"   价值：{why}")

print(f"洞察：{insight}")
PY
