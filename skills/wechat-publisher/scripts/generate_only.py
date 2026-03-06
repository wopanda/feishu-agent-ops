#!/usr/bin/env python3
"""
微信公众号文章生成脚本（仅生成，不发布）

适用场景：本地生成内容，保存到文件，稍后在云服务器上发布
"""
import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 添加lib目录到路径
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from content_generator import ContentGenerator
from title_generator import TitleGenerator
from image_generator import ImageGenerator


def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件（支持新旧两种格式）"""
    project_root = Path(__file__).parent.parent

    # 优先尝试新格式（config/credentials.json + config/settings.json）
    credentials_file = project_root / "config" / "credentials.json"
    settings_file = project_root / "config" / "settings.json"
    prompts_file = project_root / "config" / "prompts.default.json"

    if credentials_file.exists() and settings_file.exists():
        # 新格式
        with open(credentials_file, "r", encoding="utf-8") as f:
            credentials = json.load(f)
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)

        # 加载提示词配置
        prompts = {}
        if prompts_file.exists():
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts = json.load(f)

        # 转换为统一格式
        config = {
            "llm_api_key": credentials["llm"]["api_key"],
            "llm_base_url": credentials["llm"]["base_url"],
            "llm_model": credentials["llm"]["model"],
            "ark_api_key": credentials["image"]["api_key"],
            "ark_base_url": credentials["image"]["base_url"],
            "ark_model": credentials["image"]["model"],
            "wechat_appid": credentials["wechat"]["appid"],
            "wechat_secret": credentials["wechat"]["secret"],
            "default_author": settings.get("author", "日新"),
            "output_dir": settings.get("output_dir"),
            "server_ip": settings.get("server_ip"),
            "prompts": prompts,
        }
        return config

    # 回退到旧格式
    config_file = project_root / config_path
    if not config_file.exists():
        raise FileNotFoundError(
            f"配置文件不存在\n"
            f"请运行配置向导: python setup.py\n"
            f"或手动创建配置文件: config/credentials.json 和 config/settings.json"
        )

    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_logging(level: str = "INFO"):
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def is_tty() -> bool:
    return sys.stdin.isatty()


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    default_text = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{prompt} ({default_text}): ").strip().lower()
        if not answer:
            return default
        if answer in ["y", "yes", "是"]:
            return True
        if answer in ["n", "no", "否"]:
            return False
        print("  ⚠️  请输入 y 或 n")


def prompt_multiline(prompt: str) -> Optional[str]:
    print(prompt)
    print("（输入 done 结束）")
    lines: List[str] = []
    while True:
        line = input()
        if line.strip().lower() == "done":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    return text or None


def choose_title(titles: List[str]) -> str:
    print("\n=== 标题选择 ===")
    for i, t in enumerate(titles):
        print(f"  [{i}] {t}")

    while True:
        raw = input("请选择标题编号: ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 0 <= idx < len(titles):
                return titles[idx]
        print(f"  ⚠️  请输入 0 ~ {len(titles)-1} 之间的数字")


def apply_selected_title(content: str, selected_title: str) -> str:
    """将正文第一行标题替换为选定标题（如果不存在则追加）"""
    heading_re = re.compile(r"^#\s+.+$", flags=re.M)
    if heading_re.search(content):
        return heading_re.sub(f"# {selected_title}", content, count=1)
    return f"# {selected_title}\n\n{content}"


async def main():
    parser = argparse.ArgumentParser(description="微信公众号文章生成（仅生成不发布）")
    parser.add_argument("--topic", help="文章主题/角度（可选，不提供则交互式输入）")
    parser.add_argument("--reference", help="参考文章内容（可选，用于抽象层迁移）")
    parser.add_argument("--author", help="作者署名（默认从配置读取）")
    parser.add_argument("--persona-file", help="人设文件路径（可选，优先级高于默认模板）")
    parser.add_argument("--persona-text", help="人设文本（可选，优先级最高）")
    parser.add_argument("--title", help="手动指定最终标题（可选，优先级最高）")
    parser.add_argument("--title-index", type=int, help="按候选标题索引选择（0-based）")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--title-count", type=int, default=6, help="生成标题数量")
    parser.add_argument("--output-dir", default="output", help="输出目录")
    parser.add_argument("--generate-images", action="store_true", help="是否生成内容图片")

    args = parser.parse_args()

    # 配置日志
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # 加载配置
        logger.info("加载配置文件...")
        config = load_config(args.config)

        # 交互式输入主题（如果未通过参数提供）
        topic = args.topic
        if not topic and is_tty():
            print("\n" + "=" * 60)
            print("  微信公众号文章生成器")
            print("=" * 60)
            topic = input("\n请输入文章主题: ").strip()

        if not topic:
            logger.error("主题不能为空")
            sys.exit(1)

        # 交互式参考文章
        if not args.reference and is_tty():
            use_reference = input("\n是否使用参考文章进行抽象层迁移？(y/N): ").strip().lower()
            if use_reference == "y":
                reference_text = prompt_multiline("\n请输入参考文章路径，或直接粘贴内容")
                if reference_text:
                    # 如果是文件路径且文件存在，则读取文件
                    ref_path = Path(reference_text)
                    if "\n" not in reference_text and ref_path.exists() and ref_path.is_file():
                        args.reference = ref_path.read_text(encoding="utf-8")
                    else:
                        args.reference = reference_text

        # 交互式图片选项
        if not args.generate_images and is_tty():
            args.generate_images = ask_yes_no("\n是否生成内容图片？", default=False)

        # 获取作者
        author = args.author or config.get("default_author", "日新")

        # 获取人设覆盖
        persona_override = None
        persona_source = "default-template"

        if args.persona_text:
            persona_override = args.persona_text
            persona_source = "cli-text"
        elif args.persona_file:
            p = Path(args.persona_file)
            if not p.exists():
                raise FileNotFoundError(f"人设文件不存在: {p}")
            persona_override = p.read_text(encoding="utf-8")
            persona_source = f"file:{p}"
        elif is_tty():
            use_default_persona = ask_yes_no("\n是否使用默认人设模板（templates/persona.md）？", default=True)
            if not use_default_persona:
                text = prompt_multiline("请输入你的临时人设文本")
                if text:
                    persona_override = text
                    persona_source = "interactive-text"

        total_steps = 4 if args.generate_images else 3
        logger.info(f"开始生成文章: 主题={topic}, 作者={author}, 人设来源={persona_source}")

        # Step 1: 生成文章内容
        logger.info(f"Step 1/{total_steps}: 生成文章内容...")
        content_gen = ContentGenerator(
            api_key=config["llm_api_key"],
            base_url=config["llm_base_url"],
            model=config["llm_model"],
        )
        content = await content_gen.generate(
            topic=topic,
            author=author,
            reference_article=args.reference,
            persona_override=persona_override,
        )
        logger.info(f"✅ 文章生成完成，字符数: {len(content)}")

        # Step 2: 生成标题候选
        logger.info(f"Step 2/{total_steps}: 生成 {args.title_count} 个标题候选...")
        title_gen = TitleGenerator(
            api_key=config["llm_api_key"],
            base_url=config["llm_base_url"],
            model=config["llm_model"],
        )
        titles = await title_gen.generate(content, count=args.title_count)

        if not titles:
            raise RuntimeError("标题生成失败")

        logger.info("✅ 标题候选:")
        for i, title in enumerate(titles):
            logger.info(f"  [{i}] {title}")

        # 标题选择逻辑（优先级：--title > --title-index > 交互选择 > 默认第一个）
        if args.title:
            selected_title = args.title.strip()
            if not selected_title:
                raise ValueError("--title 不能为空")
            selected_title_source = "cli-title"
        elif args.title_index is not None:
            if args.title_index < 0 or args.title_index >= len(titles):
                raise ValueError(f"--title-index 超出范围: {args.title_index}，有效范围 0 ~ {len(titles)-1}")
            selected_title = titles[args.title_index]
            selected_title_source = f"index:{args.title_index}"
        elif is_tty():
            selected_title = choose_title(titles)
            selected_title_source = "interactive"
        else:
            selected_title = titles[0]
            selected_title_source = "default-first"
            logger.warning("非交互模式且未指定标题，自动使用第1个候选标题")

        logger.info(f"✅ 已选标题: {selected_title} (source={selected_title_source})")

        # Step 3: 生成内容图片（可选）
        images = []
        final_content = content  # 默认使用原始内容

        # 使用配置中的输出目录，如果没有则使用参数指定的
        output_dir_path = config.get("output_dir") or args.output_dir

        if args.generate_images:
            logger.info(f"Step 3/{total_steps}: 生成内容图片...")
            image_gen = ImageGenerator(
                llm_api_key=config["llm_api_key"],
                llm_base_url=config["llm_base_url"],
                llm_model=config["llm_model"],
                ark_api_key=config.get("ark_api_key"),
                ark_base_url=config.get("ark_base_url"),
                ark_model=config.get("ark_model"),
            )

            # 生成时间戳用于图片文件名
            img_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 生成图片但不上传到微信（本地测试）
            enhanced_content, images = await image_gen.generate_and_embed(
                content=content,
                article_topic=topic,
                wechat_client=None,  # 不上传到微信
                local_image_prefix=f"{output_dir_path}/{img_timestamp}",  # 使用本地图片路径
            )

            # 如果生成了图片，使用包含图片的内容
            if images and any(images):
                final_content = enhanced_content
                logger.info(f"✅ 生成了 {len([img for img in images if img])} 张图片，已插入到文章中")
            else:
                logger.warning("未生成任何图片，使用原始内容")

            if images:
                # 保存图片到本地
                output_dir = Path(__file__).parent.parent / output_dir_path
                output_dir.mkdir(exist_ok=True)

                for i, img_bytes in enumerate(images):
                    if img_bytes:
                        img_file = output_dir / f"{img_timestamp}_image_{i+1}.jpg"
                        with open(img_file, "wb") as f:
                            f.write(img_bytes)
                        logger.info(f"  图片 {i+1} 已保存: {img_file}")

        # 将正文标题替换为选定标题
        final_content = apply_selected_title(final_content, selected_title)

        # Step 4: 保存到本地
        logger.info(f"Step {total_steps}/{total_steps}: 保存到本地...")

        output_dir = Path(__file__).parent.parent / output_dir_path
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = selected_title[:30].replace("/", "-").replace("\\", "-")
        output_file = output_dir / f"{timestamp}_{safe_title}.md"

        # 保存完整内容
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# 文章信息\n\n")
            f.write(f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- 主题: {topic}\n")
            f.write(f"- 作者: {author}\n")
            f.write(f"- 选定标题: {selected_title}\n")
            f.write(f"- 选题来源: {selected_title_source}\n")
            f.write(f"- 人设来源: {persona_source}\n")
            f.write(f"- 字符数: {len(final_content)}\n")
            if images:
                f.write(f"- 生成图片: {len([img for img in images if img])} 张\n")
            f.write("\n")

            f.write("# 标题候选\n\n")
            for i, title in enumerate(titles):
                prefix = "✅ " if title == selected_title else ""
                f.write(f"{i}. {prefix}{title}\n")

            f.write("\n---\n\n")
            f.write(final_content)

        logger.info(f"✅ 文章已保存到: {output_file}")

        # 同时保存一个 JSON 格式，方便程序读取
        json_file = output_file.with_suffix(".json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": timestamp,
                    "topic": topic,
                    "author": author,
                    "titles": titles,
                    "selected_title": selected_title,
                    "selected_title_source": selected_title_source,
                    "persona_source": persona_source,
                    "content": final_content,
                    "char_count": len(final_content),
                    "has_images": len(images) > 0,
                    "image_count": len([img for img in images if img]),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(f"✅ JSON 数据已保存到: {json_file}")

        logger.info("\n🎉 生成完成!")
        logger.info("\n下一步：")
        logger.info(f"1. 查看生成的文章: {output_file}")
        logger.info("2. 已完成标题选择（可直接发布）")
        if images:
            logger.info(f"3. 查看生成的图片: {output_dir}/{timestamp}_image_*.jpg")
            logger.info("4. 在云服务器上运行发布脚本:")
        else:
            logger.info("3. 在云服务器上运行发布脚本:")
        logger.info(f"   python scripts/publish_only.py --content-file \"{output_file}\"")

    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
