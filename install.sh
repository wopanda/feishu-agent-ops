#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="${OPENCLAW_SKILLS_DIR:-$HOME/.openclaw/skills}"
SKILL_NAME="feishu-agent-ops"
DEST_DIR="$TARGET_DIR/$SKILL_NAME"

mkdir -p "$TARGET_DIR"
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

copy_if_exists() {
  local item="$1"
  if [ -e "$REPO_DIR/$item" ]; then
    cp -a "$REPO_DIR/$item" "$DEST_DIR/"
  fi
}

copy_if_exists "SKILL.md"
copy_if_exists "README.md"
copy_if_exists "references"
copy_if_exists "templates"
copy_if_exists "examples"
copy_if_exists "docs"
copy_if_exists "scripts"
copy_if_exists "evals"
copy_if_exists "LICENSE"
copy_if_exists ".gitignore"

chmod -R u+rwX "$DEST_DIR"

echo "installed: $SKILL_NAME"
echo
echo "安装完成。下一步："
echo "1) 到 $DEST_DIR 阅读 README.md"
echo "2) 直接告诉 OpenClaw：我已经创建好了这批飞书机器人，帮我接成 OpenClaw 多 Agent，先给我预览，再执行。"
echo "3) 如果要排查根因，先运行：python3 $DEST_DIR/scripts/inspect_openclaw_multi_agent.py --config ~/.openclaw/openclaw.json"
echo "4) 如果要巡检，直接说：帮我检查一下当前这套飞书多 Agent 配置有没有问题。"
