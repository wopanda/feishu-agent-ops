#!/usr/bin/env python3
"""
微信公众号文章生成和发布主脚本

完整流程：生成文章 -> 生成标题 -> 生成封面图 -> 格式化 -> 发布到草稿箱
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加lib目录到路径
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from content_generator import ContentGenerator
from title_generator import TitleGenerator
from markdown_formatter import WeChatMarkdownFormatter
from wechat_client import WeChatClient
from image_compressor import ImageCompressor


def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件"""
    config_file = Path(__file__).parent.parent / config_path
    if not config_file.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {config_file}\\n"
            f"请复制 config.json.example 为 config.json 并填写配置"
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


async def main():
    parser = argparse.ArgumentParser(description="微信公众号文章生成和发布")
    parser.add_argument("--topic", required=True, help="文章主题/角度")
    parser.add_argument("--reference", help="参考文章内容（可选，用于抽象层迁移）")
    parser.add_argument("--author", help="作者署名（默认从配置读取）")
    parser.add_argument("--style", help="文章风格（默认从配置读取）")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--title-count", type=int, default=6, help="生成标题数量")
    parser.add_argument("--title-index", type=int, default=0, help="选择第几个标题（0-based）")

    args = parser.parse_args()

    # 配置日志
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # 加载配置
        logger.info("加载配置文件...")
        config = load_config(args.config)

        # 获取作者和风格
        author = args.author or config.get("default_author", "日新")
        style = args.style or config.get("default_style", "干货")

        logger.info(f"开始生成文章: 主题={args.topic}, 作者={author}, 风格={style}")

        # Step 1: 生成文章内容
        logger.info("Step 1/7: 生成文章内容...")
        content_gen = ContentGenerator(
            api_key=config["llm_api_key"],
            base_url=config["llm_base_url"],
            model=config["llm_model"],
        )
        content = await content_gen.generate(
            topic=args.topic,
            author=author,
            reference_article=args.reference,
        )
        logger.info(f"文章生成完成，字符数: {len(content)}")

        # Step 2: 生成标题候选
        logger.info(f"Step 2/7: 生成 {args.title_count} 个标题候选...")
        title_gen = TitleGenerator(
            api_key=config["llm_api_key"],
            base_url=config["llm_base_url"],
            model=config["llm_model"],
        )
        titles = await title_gen.generate(content, count=args.title_count)

        if not titles:
            raise RuntimeError("标题生成失败")

        logger.info(f"标题候选:")
        for i, title in enumerate(titles):
            logger.info(f"  [{i}] {title}")

        # 选择标题
        selected_title = titles[min(args.title_index, len(titles) - 1)]
        logger.info(f"选择标题: {selected_title}")

        # Step 3: 格式化 Markdown
        logger.info("Step 3/7: 格式化 Markdown...")
        formatter = WeChatMarkdownFormatter()
        html_content = formatter.format(content)
        logger.info("Markdown 格式化完成")

        # Step 4: 发布到草稿箱（暂不支持封面图）
        logger.info("Step 4/7: 发布到微信草稿箱...")
        wechat_client = WeChatClient(
            appid=config["wechat_appid"],
            secret=config["wechat_secret"],
        )

        result = await wechat_client.publish_to_draft(
            title=selected_title,
            content=html_content,
            author=author,
        )

        logger.info(f"✅ 发布成功!")
        logger.info(f"  Media ID: {result['media_id']}")
        logger.info(f"  草稿链接: {result['draft_url']}")

        # Step 5: 保存到本地
        logger.info("Step 5/7: 保存到本地...")
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{timestamp}_{selected_title[:20]}.md"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {selected_title}\\n\\n")
            f.write(f"作者: {author}\\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"Media ID: {result['media_id']}\\n\\n")
            f.write("---\\n\\n")
            f.write(content)

        logger.info(f"文章已保存到: {output_file}")

        # 关闭客户端
        await wechat_client.close()

        logger.info("\\n🎉 全部完成!")

    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())