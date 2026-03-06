#!/usr/bin/env python3
"""
微信公众号AI写作助手 - OpenClaw Skill

用法：
  python skill.py "文章主题"
  python skill.py "文章主题" --publish              # 生成并发布到微信草稿箱
  python skill.py --publish --content-file "output/x.md"  # 直接发布已生成文章
  python skill.py --setup                            # 运行配置向导
"""
import argparse
import subprocess
import sys
from pathlib import Path


def check_config() -> bool:
    """检查配置文件是否存在（新格式）"""
    config_dir = Path(__file__).parent / "config"
    credentials_file = config_dir / "credentials.json"
    settings_file = config_dir / "settings.json"

    return credentials_file.exists() and settings_file.exists()


def run_setup() -> bool:
    """运行配置向导"""
    setup_script = Path(__file__).parent / "setup.py"
    result = subprocess.run([sys.executable, str(setup_script)])
    return result.returncode == 0


def run_generate(topic: str = None, reference: str = None, **kwargs) -> bool:
    """运行生成脚本"""
    script_path = Path(__file__).parent / "scripts" / "generate_only.py"

    cmd = [sys.executable, str(script_path)]

    # 添加主题或参考文章
    if topic:
        cmd.extend(["--topic", topic])
    if reference:
        cmd.extend(["--reference", reference])

    # 默认生成配图（保留你当前习惯）
    if kwargs.get("generate_images", True):
        cmd.append("--generate-images")

    # 透传可选参数
    for key in ["log_level", "output_dir", "author", "title", "persona_file", "persona_text"]:
        val = kwargs.get(key)
        if val:
            flag = "--" + key.replace("_", "-")
            cmd.extend([flag, str(val)])

    # title_index 允许 0
    if kwargs.get("title_index") is not None:
        cmd.extend(["--title-index", str(kwargs["title_index"])])

    result = subprocess.run(cmd)
    return result.returncode == 0


def run_publish(content_file: str = None, title: str = None, author: str = None, cover_image: str = None, log_level: str = "INFO") -> bool:
    """运行发布脚本"""
    script_path = Path(__file__).parent / "scripts" / "publish_only.py"
    cmd = [sys.executable, str(script_path), "--log-level", log_level]

    if content_file:
        cmd.extend(["--content-file", content_file])
    if title:
        cmd.extend(["--title", title])
    if author:
        cmd.extend(["--author", author])
    if cover_image:
        cmd.extend(["--cover-image", cover_image])

    result = subprocess.run(cmd)
    return result.returncode == 0


def latest_output_markdown() -> str | None:
    out_dir = Path(__file__).parent / "output"
    if not out_dir.exists():
        return None
    candidates = sorted(out_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else None


def main():
    parser = argparse.ArgumentParser(
        description="微信公众号AI写作助手 - OpenClaw Skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
OpenClaw调用示例：
  # 主题模式（交互选择标题）
  python skill.py "AI写作的3个实用技巧"

  # 指定参考文章 + 指定标题索引
  python skill.py --reference "参考文章内容..." --title-index 2

  # 人设覆盖
  python skill.py "AI工作流" --persona-file templates/persona.md

  # 生成并发布（自动发布到草稿箱）
  python skill.py "AI写作技巧" --publish

  # 直接发布已有文件
  python skill.py --publish --content-file "output/xxx.md"

  # 初次配置
  python skill.py --setup
        """,
    )

    parser.add_argument("topic", nargs="?", help="文章主题")
    parser.add_argument("--reference", help="参考文章内容（用于生成类似风格的文章）")
    parser.add_argument("--publish", action="store_true", help="生成后自动发布，或直接发布 --content-file")
    parser.add_argument("--content-file", help="直接发布指定 markdown 文件（配合 --publish）")
    parser.add_argument("--title", help="手动指定标题")
    parser.add_argument("--title-index", type=int, help="按候选标题索引选择（0-based）")
    parser.add_argument("--author", help="作者署名")
    parser.add_argument("--persona-file", help="人设文件路径")
    parser.add_argument("--persona-text", help="人设文本")
    parser.add_argument("--cover-image", help="封面图片路径")
    parser.add_argument("--setup", action="store_true", help="运行配置向导")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--output-dir", help="输出目录")

    args = parser.parse_args()

    try:
        # setup
        if args.setup:
            if not run_setup():
                sys.exit(1)
            return

        # 配置检查
        if not check_config():
            print("\n" + "=" * 60)
            print("  ✨ 欢迎使用AI写作助手！")
            print("=" * 60)
            print("\n检测到首次使用，让我们先完成一些简单的设置...\n")

            if not run_setup():
                print("\n❌ 设置失败，请重试")
                sys.exit(1)

            print("\n✅ 设置完成！\n")

        # 分支A：直接发布现有内容
        if args.publish and args.content_file:
            print("\n🚀 正在发布已有文章到微信草稿箱...\n")
            ok = run_publish(
                content_file=args.content_file,
                title=args.title,
                author=args.author,
                cover_image=args.cover_image,
                log_level=args.log_level,
            )
            if not ok:
                print("\n❌ 发布失败")
                sys.exit(1)
            return

        # 分支B：先生成
        if not args.topic and not args.reference:
            print("\n❌ 请提供文章主题或参考文章")
            print("\n用法：")
            print("  主题模式：python skill.py \"你的主题\"")
            print("  参考文章模式：python skill.py --reference \"文章内容\"")
            print("  直接发布：python skill.py --publish --content-file \"output/xxx.md\"")
            sys.exit(1)

        if args.reference and not args.topic:
            print("\n✨ 正在参考文章风格创作...\n")
        elif args.topic:
            print(f"\n✨ 正在创作关于「{args.topic}」的文章...\n")

        ok = run_generate(
            topic=args.topic,
            reference=args.reference,
            log_level=args.log_level,
            output_dir=args.output_dir,
            author=args.author,
            title=args.title,
            title_index=args.title_index,
            persona_file=args.persona_file,
            persona_text=args.persona_text,
            generate_images=True,
        )

        if not ok:
            print("\n❌ 文章生成失败")
            sys.exit(1)

        # 需要发布则自动发布最新生成稿
        if args.publish:
            latest_md = latest_output_markdown()
            if not latest_md:
                print("\n❌ 未找到可发布的生成稿")
                sys.exit(1)

            print("\n🚀 正在发布到微信草稿箱...\n")
            ok = run_publish(
                content_file=latest_md,
                title=args.title,
                author=args.author,
                cover_image=args.cover_image,
                log_level=args.log_level,
            )
            if not ok:
                print("\n❌ 发布失败")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n👋 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 出错了: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
