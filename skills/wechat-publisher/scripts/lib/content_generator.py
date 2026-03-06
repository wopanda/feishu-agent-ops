"""Article content generation using OpenAI-compatible LLM (DeepSeek / OpenAI / etc.)"""
import logging
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI


class ContentGenerator:
    """基于 OpenAI 兼容接口的文章内容生成器（支持 DeepSeek / OpenAI）"""

    def __init__(self, api_key: str, base_url: str, model: str, templates_dir: Optional[Path] = None):
        """初始化内容生成器

        Args:
            api_key: LLM API Key
            base_url: LLM API Base URL
            model: LLM 模型 ID
            templates_dir: 模板文件目录，默认为相对路径
        """
        if not api_key:
            raise ValueError("LLM_API_KEY 未配置，请在 config.json 中添加")

        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.logger = logging.getLogger(__name__)

        # 设置模板目录
        if templates_dir is None:
            self.templates_dir = Path(__file__).parent.parent.parent / "templates"
        else:
            self.templates_dir = templates_dir

    def _get_client(self) -> AsyncOpenAI:
        """获取 OpenAI 客户端"""
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _load_template(self, filename: str) -> str:
        """加载模板文件

        Args:
            filename: 模板文件名

        Returns:
            模板内容

        Raises:
            FileNotFoundError: 模板文件不存在
        """
        path = self.templates_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"模板文件不存在: {path}，请检查 templates/ 目录")
        return path.read_text(encoding="utf-8")

    async def generate(
        self,
        topic: str,
        author: str = "日新",
        reference_article: Optional[str] = None,
        persona_override: Optional[str] = None,
    ) -> str:
        """生成文章内容

        Args:
            topic: 文章主题/角度
            author: 作者名（用于日志）
            reference_article: 可选参考文章内容，用于抽象层迁移模式
            persona_override: 可选的人设覆盖文本（优先于 templates/persona.md）

        Returns:
            Markdown 格式的完整文章（含 # 标题行）

        Raises:
            ValueError: API Key 未配置
            FileNotFoundError: 模板文件不存在
        """
        client = self._get_client()

        persona = persona_override.strip() if persona_override and persona_override.strip() else self._load_template("persona.md")
        writing_guide = self._load_template("writing-guide.md")

        if reference_article:
            abstract_transfer = self._load_template("abstract-transfer.md")
            prompt = self._build_transfer_prompt(
                topic, persona, writing_guide, abstract_transfer, reference_article
            )
            self.logger.info(f"使用抽象层迁移模式生成文章，主题: {topic}")
        else:
            prompt = self._build_standard_prompt(topic, persona, writing_guide)
            self.logger.info(f"使用标准模式生成文章，主题: {topic}")

        response = await client.chat.completions.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.choices[0].message.content or ""
        self.logger.info(f"文章生成完成，字符数: {len(content)}")
        return content

    def _build_standard_prompt(self, topic: str, persona: str, writing_guide: str) -> str:
        """构建标准模式提示词"""
        return f"""你是一位微信公众号作者，请根据以下信息撰写一篇完整的文章。

## 作者人设

{persona}

## 写作框架与风格指南

{writing_guide}

## 写作任务

主题：{topic}

请直接输出完整的文章内容（Markdown 格式），第一行为 # 标题，之后是正文。不要有任何前言、说明或总结性话语。"""

    def _build_transfer_prompt(
        self,
        topic: str,
        persona: str,
        writing_guide: str,
        abstract_transfer: str,
        reference_article: str,
    ) -> str:
        """构建抽象层迁移模式提示词"""
        return f"""你是一位微信公众号作者，请根据以下信息，使用抽象层迁移方法撰写一篇完整的文章。

## 作者人设

{persona}

## 写作框架与风格指南

{writing_guide}

## 抽象层迁移方法论

{abstract_transfer}

## 参考文章

{reference_article}

## 写作任务

在参考文章的叙事结构基础上，以「{topic}」为主题，生成全新的原创文章。

请直接输出完整的文章内容（Markdown 格式），第一行为 # 标题，之后是正文。不要有任何前言或说明。"""
