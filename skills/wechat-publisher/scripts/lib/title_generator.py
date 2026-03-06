"""Title candidates generation using OpenAI-compatible LLM (DeepSeek / OpenAI / etc.)"""
import logging
import re
from pathlib import Path
from typing import List, Optional

from openai import AsyncOpenAI


class TitleGenerator:
    """基于 OpenAI 兼容接口的爆款标题生成器"""

    def __init__(self, api_key: str, base_url: str, model: str, templates_dir: Optional[Path] = None):
        """初始化标题生成器

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

    async def generate(self, content: str, count: int = 6) -> List[str]:
        """为已生成的文章生成标题候选列表

        Args:
            content: 文章正文（Markdown 格式）
            count: 生成标题数量（默认 6 个）

        Returns:
            标题候选列表

        Raises:
            ValueError: API Key 未配置
        """
        client = self._get_client()

        formulas_path = self.templates_dir / "title-formulas.md"
        formulas = (
            formulas_path.read_text(encoding="utf-8") if formulas_path.exists() else ""
        )

        content_preview = content[:2000] + ("..." if len(content) > 2000 else "")

        prompt = f"""请为以下文章生成 {count} 个风格各异的爆款标题候选。

## 标题公式库

{formulas}

## 文章内容（节选）

{content_preview}

## 输出要求

- 生成 {count} 个标题
- 覆盖至少 3-5 种不同公式类型
- 严格基于原文事实，不可虚构或夸大
- 每个标题约 20 字以内（适合手机端单行显示）
- **直接输出标题列表，每行一个，不要编号、破折号或其他前缀**"""

        self.logger.info(f"正在生成 {count} 个标题候选...")

        response = await client.chat.completions.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = (response.choices[0].message.content or "").strip()
        titles = [line.strip() for line in raw.split("\n") if line.strip()]
        titles = [re.sub(r"^[\d]+[.、]\s*|^[-*]\s*", "", t).strip() for t in titles]
        titles = [t for t in titles if t]

        self.logger.info(f"标题生成完成，共 {len(titles)} 个候选")
        return titles[:count]
