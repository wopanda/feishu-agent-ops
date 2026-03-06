"""Content image generation pipeline using Seedream (Ark API)"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
import httpx
from openai import AsyncOpenAI


class ImageGenerator:
    """内容图片生成器（使用 Seedream）"""

    def __init__(
        self,
        llm_api_key: str,
        llm_base_url: str,
        llm_model: str,
        ark_api_key: Optional[str] = None,
        ark_base_url: Optional[str] = None,
        ark_model: Optional[str] = None,
    ):
        """初始化图片生成器

        Args:
            llm_api_key: LLM API Key（用于生成图片提示词）
            llm_base_url: LLM API Base URL
            llm_model: LLM 模型 ID
            ark_api_key: 火山引擎 Ark API Key（可选）
            ark_base_url: Ark API Base URL（可选）
            ark_model: Ark 模型 ID（可选）
        """
        self.llm_api_key = llm_api_key
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.ark_api_key = ark_api_key
        self.ark_base_url = ark_base_url
        self.ark_model = ark_model
        self.logger = logging.getLogger(__name__)
        self._llm_client: Optional[AsyncOpenAI] = None

    def _get_llm_client(self) -> AsyncOpenAI:
        """获取 LLM 客户端（用于生成图片提示词）"""
        if self._llm_client is None:
            self._llm_client = AsyncOpenAI(
                api_key=self.llm_api_key,
                base_url=self.llm_base_url,
            )
        return self._llm_client

    async def _analyze_article_structure(self, content: str) -> List[Dict[str, Any]]:
        """分析文章结构，确定需要配图的章节

        Args:
            content: Markdown 格式的文章内容

        Returns:
            章节信息列表
        """
        pattern = r'^(#{2,3})\s+(.+)$'
        lines = content.split('\n')
        sections = []

        for i, line in enumerate(lines):
            match = re.match(pattern, line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()

                # 获取章节内容预览
                preview_lines = []
                for j in range(i + 1, min(i + 6, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith('#'):
                        preview_lines.append(next_line)
                        if len(preview_lines) >= 3:
                            break

                preview = '\n'.join(preview_lines)

                sections.append({
                    'level': level,
                    'title': title,
                    'line_index': i,
                    'preview': preview,
                })

        # 最多选择前 4 个章节配图
        selected_sections = sections[:4]
        self.logger.info(f"分析出 {len(sections)} 个章节，选择前 {len(selected_sections)} 个配图")
        return selected_sections

    async def _generate_image_prompts(
        self,
        sections: List[Dict[str, Any]],
        article_topic: str,
    ) -> List[str]:
        """调用 LLM 为每个章节生成图片提示词"""
        client = self._get_llm_client()
        prompts = []

        for section in sections:
            system_prompt = """你是一个专业的信息可视化设计师。根据文章章节的标题和内容，生成一个信息可视化图片的英文提示词。

重要原则：
1. 这是信息可视化图片，不是装饰性插画
2. 使用图标、色块、箭头等元素呈现信息结构
3. 避免具体人物面孔（用图标/剪影代替）
4. 统一视觉风格：扁平设计，暖色调（橙色、珊瑚色、米黄色），柔和渐变背景

可视化形式选择：
- 多个并列要点 → 卡片式布局、图标列表
- 流程/步骤 → 时间轴、流程图
- 对比关系 → 对比图、VS布局
- 层级关系 → 同心圆、金字塔
- 核心概念 → 中心辐射图

提示词结构：[可视化类型] + [结构化内容] + [视觉风格]

示例：
"Information visualization card layout, three horizontal blocks with icons, first block shows policy document icon, second shows AI chip icon, third shows network icon, arrows converging upward, flat design style, warm color palette with orange coral and beige gradient, modern minimalist"

只返回英文提示词，不要解释。"""

            user_prompt = f"""文章主题：{article_topic}
章节标题：{section['title']}
章节内容预览：{section['preview'][:200]}

请生成一个信息可视化图片的英文提示词："""

            try:
                response = await client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=150,
                )
                prompt = response.choices[0].message.content.strip()
                prompts.append(prompt)
                self.logger.info(f"章节 '{section['title']}' 的图片提示词: {prompt}")
            except Exception as e:
                self.logger.warning(f"生成章节 '{section['title']}' 的图片提示词失败: {e}")
                # 使用信息可视化风格的备用提示词
                fallback = f"Information visualization infographic about {section['title']}, flat design style, warm color palette with orange and coral, modern minimalist, clean layout with icons and color blocks"
                prompts.append(fallback)

        self.logger.info(f"已为 {len(prompts)} 个章节生成图片提示词")
        return prompts

    async def _generate_image_with_seedream(self, prompt: str) -> Optional[bytes]:
        """调用 Seedream API 生成图片"""
        if not self.ark_api_key:
            self.logger.warning("未配置 ARK_API_KEY，跳过图片生成")
            return None

        url = self.ark_base_url
        headers = {
            "Authorization": f"Bearer {self.ark_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.ark_model,
            "prompt": prompt,
            "size": "2560x1440",
            "response_format": "url",
            "watermark": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                # 获取图片 URL 并下载
                image_url = data.get("data", [{}])[0].get("url")
                if not image_url:
                    self.logger.error(f"Seedream API 返回数据格式异常: {data}")
                    return None

                # 下载图片
                img_response = await client.get(image_url)
                img_response.raise_for_status()
                self.logger.info(f"图片生成成功: {len(img_response.content)} bytes")
                return img_response.content

        except Exception as e:
            self.logger.error(f"调用 Seedream API 生成图片失败: {e}")
            return None

    def _insert_images_into_content(
        self,
        content: str,
        sections: List[Dict[str, Any]],
        image_urls: List[Optional[str]],
    ) -> str:
        """将图片 URL 插入到文章内容中"""
        if not sections or not any(image_urls):
            return content

        lines = content.split('\n')
        section_index_map = {
            section['line_index']: i for i, section in enumerate(sections)
        }

        new_lines = []

        for line_index, line in enumerate(lines):
            new_lines.append(line)

            # 检查是否是章节标题位置
            if line_index in section_index_map:
                idx = section_index_map[line_index]
                url = image_urls[idx] if idx < len(image_urls) else None

                if url:
                    # 插入图片（HTML 格式，微信支持）
                    image_html = f'<p><img src="{url}" style="width: 100%; max-width: 900px; display: block; margin: 20px auto;"/></p>'
                    new_lines.append(image_html)

        return '\n'.join(new_lines)

    async def generate_and_embed(
        self,
        content: str,
        article_topic: str,
        wechat_client=None,
        local_image_prefix: Optional[str] = None,
    ) -> tuple[str, List[Optional[bytes]]]:
        """生成内容图片并嵌入到文章中

        Args:
            content: 原始 Markdown 内容
            article_topic: 文章主题
            wechat_client: 微信客户端（用于上传图片）

        Returns:
            (嵌入图片后的内容, 生成的图片列表)
        """
        self.logger.info("开始内容图片生成流程")

        # Step 1: 分析文章结构
        sections = await self._analyze_article_structure(content)
        if not sections:
            self.logger.info("未找到需要配图的章节，跳过图片生成")
            return content, []

        # Step 2: 生成图片提示词
        prompts = await self._generate_image_prompts(sections, article_topic)

        # Step 3: 并发生成图片
        image_tasks = [self._generate_image_with_seedream(p) for p in prompts]
        images = await asyncio.gather(*image_tasks, return_exceptions=False)

        # Step 4: 如果提供了微信客户端，上传图片并获取URL
        if wechat_client:
            wechat_urls = []
            for i, image_bytes in enumerate(images):
                if image_bytes is None:
                    wechat_urls.append(None)
                    continue

                try:
                    result = await wechat_client.upload_image(
                        image_bytes=image_bytes,
                        filename=f"section_{i + 1}.jpg",
                    )
                    wechat_urls.append(result.get("url"))
                except Exception as e:
                    self.logger.error(f"上传图片 {i + 1} 到微信失败: {e}")
                    wechat_urls.append(None)

            # Step 5: 插入图片到文章
            enhanced_content = self._insert_images_into_content(content, sections, wechat_urls)
            embedded_count = sum(1 for url in wechat_urls if url is not None)
            self.logger.info(f"内容图片生成完成，已嵌入 {embedded_count} 张图片")
            return enhanced_content, images

        # 本地测试：使用本地图片路径
        elif local_image_prefix and any(images):
            local_urls = []
            for i, image_bytes in enumerate(images):
                if image_bytes:
                    # 使用本地图片路径
                    local_urls.append(f"{local_image_prefix}_image_{i + 1}.jpg")
                else:
                    local_urls.append(None)

            # 插入本地图片路径到文章
            enhanced_content = self._insert_images_into_content(content, sections, local_urls)
            embedded_count = sum(1 for url in local_urls if url is not None)
            self.logger.info(f"生成了 {len(images)} 张图片，已使用本地路径插入 {embedded_count} 张")
            return enhanced_content, images

        else:
            self.logger.info(f"生成了 {len(images)} 张图片，但未插入到文章中")
            return content, images
