#!/usr/bin/env python3
"""
微信公众号文章发布脚本（仅发布已有内容）

增强点：
1) 支持新配置格式（config/credentials.json + config/settings.json）
2) 自动从生成稿中提取正文（跳过“文章信息/标题候选”区块）
3) 自动从正文 H1 提取标题（未传 --title 时）
4) 自动上传正文本地图片并替换为微信URL（避免图片不显示）
5) 自动使用第一张正文图作为封面（未传 --cover-image 时）
"""
import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

# 添加lib目录到路径
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from markdown_formatter import WeChatMarkdownFormatter
from wechat_client import WeChatClient
from image_compressor import ImageCompressor


IMG_SRC_RE = re.compile(r'(<img[^>]+src=")([^"]+)("[^>]*>)', flags=re.I)
H1_RE = re.compile(r"^#\s+(.+)$", flags=re.M)


def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件（支持新旧两种格式）"""
    project_root = Path(__file__).parent.parent

    # 新格式
    credentials_file = project_root / "config" / "credentials.json"
    settings_file = project_root / "config" / "settings.json"

    if credentials_file.exists() and settings_file.exists():
        with open(credentials_file, "r", encoding="utf-8") as f:
            credentials = json.load(f)
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)

        return {
            "wechat_appid": credentials["wechat"]["appid"],
            "wechat_secret": credentials["wechat"]["secret"],
            "default_author": settings.get("author", "日新"),
        }

    # 旧格式
    config_file = project_root / config_path
    if not config_file.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {config_file}\n"
            f"请先运行: python setup.py"
        )

    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def extract_main_body(markdown_text: str) -> str:
    """从生成稿中提取正文。

    generate_only.py 输出格式为：
    - 文章信息
    - 标题候选
    ---
    正文

    若不匹配该结构，则返回原文。
    """
    marker = "\n---\n"
    if marker in markdown_text:
        return markdown_text.split(marker, 1)[1].strip()
    return markdown_text.strip()


def extract_title(markdown_text: str) -> Optional[str]:
    m = H1_RE.search(markdown_text)
    return m.group(1).strip() if m else None


def resolve_local_image(src: str, project_root: Path, content_file_path: Optional[Path]) -> Optional[Path]:
    if src.startswith("http://") or src.startswith("https://"):
        return None

    # 1) 相对项目根
    p1 = (project_root / src).resolve()
    if p1.exists() and p1.is_file():
        return p1

    # 2) 相对内容文件目录
    if content_file_path is not None:
        p2 = (content_file_path.parent / src).resolve()
        if p2.exists() and p2.is_file():
            return p2

    return None


async def upload_body_images(
    markdown_body: str,
    wechat_client: WeChatClient,
    project_root: Path,
    content_file_path: Optional[Path],
    logger: logging.Logger,
) -> Tuple[str, Optional[str]]:
    """上传正文里的本地图片，替换为微信URL。

    Returns:
      (替换后的markdown, 第一张上传图的 media_id 作为封面候选)
    """
    src_to_url: Dict[str, str] = {}
    src_to_media: Dict[str, str] = {}

    matches = list(IMG_SRC_RE.finditer(markdown_body))
    if not matches:
        return markdown_body, None

    for mt in matches:
        src = mt.group(2)
        if src in src_to_url:
            continue

        local = resolve_local_image(src, project_root=project_root, content_file_path=content_file_path)
        if local is None:
            if src.startswith("http://") or src.startswith("https://"):
                src_to_url[src] = src
                continue
            logger.warning(f"图片未找到，跳过替换: {src}")
            continue

        img_bytes = local.read_bytes()
        upload_result = await wechat_client.upload_image(img_bytes, filename=local.name)
        url = upload_result.get("url")
        media_id = upload_result.get("media_id")

        if not url:
            logger.warning(f"图片上传成功但未返回URL，跳过替换: {src}")
            continue

        src_to_url[src] = url
        if media_id:
            src_to_media[src] = media_id

        logger.info(f"正文图片已上传: {src} -> {url[:80]}...")

    def repl(match):
        pre, src, post = match.group(1), match.group(2), match.group(3)
        return f'{pre}{src_to_url.get(src, src)}{post}'

    replaced = IMG_SRC_RE.sub(repl, markdown_body)

    cover_media_id = None
    for mt in matches:
        s = mt.group(2)
        if s in src_to_media:
            cover_media_id = src_to_media[s]
            break

    return replaced, cover_media_id


async def main():
    parser = argparse.ArgumentParser(description="微信公众号文章发布（仅发布）")
    parser.add_argument("--title", help="文章标题（可选，不传则从正文H1提取）")
    parser.add_argument("--content", help="文章内容（Markdown格式）")
    parser.add_argument("--content-file", help="文章内容文件路径")
    parser.add_argument("--author", help="作者署名（默认从配置读取）")
    parser.add_argument("--cover-image", help="封面图路径（可选）")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--log-level", default="INFO", help="日志级别")

    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        project_root = Path(__file__).parent.parent

        # 加载配置
        logger.info("加载配置文件...")
        config = load_config(args.config)

        author = args.author or config.get("default_author", "日新")

        # 读取内容
        content_file_path: Optional[Path] = None
        if args.content:
            raw_content = args.content
        elif args.content_file:
            content_file_path = Path(args.content_file)
            if not content_file_path.exists():
                raise FileNotFoundError(f"文章文件不存在: {content_file_path}")
            raw_content = content_file_path.read_text(encoding="utf-8")
        else:
            raise ValueError("必须提供 --content 或 --content-file 参数")

        body_markdown = extract_main_body(raw_content)
        title = (args.title or extract_title(body_markdown) or "未命名文章").strip()

        logger.info(f"开始发布文章: 标题={title}, 作者={author}")

        wechat_client = WeChatClient(
            appid=config["wechat_appid"],
            secret=config["wechat_secret"],
        )

        try:
            # Step 1: 上传正文本地图并替换为微信URL
            logger.info("Step 1/4: 处理正文图片...")
            body_markdown_remote, auto_cover_media_id = await upload_body_images(
                markdown_body=body_markdown,
                wechat_client=wechat_client,
                project_root=project_root,
                content_file_path=content_file_path,
                logger=logger,
            )

            # Step 2: 格式化 Markdown
            logger.info("Step 2/4: 格式化 Markdown...")
            formatter = WeChatMarkdownFormatter()
            html_content = formatter.format(body_markdown_remote)
            logger.info("Markdown 格式化完成")

            # Step 3: 处理封面图
            thumb_media_id = ""
            if args.cover_image:
                logger.info("Step 3/4: 上传指定封面图...")
                cover_path = Path(args.cover_image)
                if not cover_path.exists():
                    logger.warning(f"封面图不存在: {cover_path}，改用自动封面")
                else:
                    image_bytes = cover_path.read_bytes()
                    compressor = ImageCompressor()
                    compressed = compressor.compress(image_bytes, max_size_kb=64)
                    upload_result = await wechat_client.upload_image(compressed, "cover.jpg")
                    thumb_media_id = upload_result.get("media_id", "")
                    logger.info(f"封面图上传成功: {thumb_media_id}")

            if not thumb_media_id and auto_cover_media_id:
                thumb_media_id = auto_cover_media_id
                logger.info(f"Step 3/4: 使用正文首图作为封面: {thumb_media_id}")
            elif not thumb_media_id:
                logger.info("Step 3/4: 无封面图（保持为空）")

            # Step 4: 发布到草稿箱
            logger.info("Step 4/4: 发布到微信草稿箱...")
            result = await wechat_client.publish_to_draft(
                title=title,
                content=html_content,
                author=author,
                thumb_media_id=thumb_media_id,
            )

            logger.info("✅ 发布成功!")
            logger.info(f"  Media ID: {result['media_id']}")
            logger.info(f"  草稿链接: {result['draft_url']}")
            logger.info("\n🎉 全部完成!")

        finally:
            await wechat_client.close()

    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
