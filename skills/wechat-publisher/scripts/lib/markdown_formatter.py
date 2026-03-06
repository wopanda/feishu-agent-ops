"""Markdown formatter for WeChat Official Account"""
import logging
import re
import markdown


class WeChatMarkdownFormatter:
    """微信公众号Markdown格式化器（增强样式版）"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 配置markdown扩展
        self.md = markdown.Markdown(
            extensions=[
                "tables",
                "fenced_code",
                "codehilite",
                "nl2br",  # 换行转<br>
            ],
            extension_configs={
                "codehilite": {
                    "noclasses": True,  # 使用内联样式
                    "linenums": False,  # 不显示行号
                }
            },
        )

        # 统一主题色（可按需继续细化）
        self.colors = {
            "text": "#2f3441",
            "title": "#1f2d3d",
            "sub_title": "#243b53",
            "accent": "#2f7cf6",
            "light_bg": "#f7f9fc",
            "quote_bg": "#f3f7ff",
            "quote_border": "#7da2ff",
            "hr": "#dbe4f0",
        }

    def format(self, content: str) -> str:
        """格式化Markdown为微信支持的HTML"""
        try:
            if not content or not content.strip():
                raise ValueError("内容不能为空")

            # 1. 转换Markdown为HTML
            html = self.md.convert(content)

            # 2. 应用微信样式
            html = self._apply_wechat_styles(html)

            # 3. 清理不支持标签
            html = self._clean_unsupported_tags(html)

            # 4. 包一层文章容器，确保统一视觉基线
            html = self._wrap_article(html)

            self.logger.info("Markdown格式化成功（增强样式版）")
            return html

        except Exception as e:
            self.logger.error(f"Markdown格式化失败: {str(e)}")
            raise ValueError(f"Markdown格式化失败: {str(e)}")

    def _wrap_article(self, html: str) -> str:
        return (
            f'<section style="'
            f'font-size:16px;'
            f'line-height:1.85;'
            f'color:{self.colors["text"]};'
            f'letter-spacing:0.2px;'
            f'word-break:break-word;'
            f'">{html}</section>'
        )

    def _apply_wechat_styles(self, html: str) -> str:
        """应用微信公众号样式"""

        # 分割线
        html = re.sub(
            r"<hr\s*/?>",
            (
                f'<section style="text-align:center; margin:28px 0 22px;">'
                f'<section style="display:inline-block; width:64px; border-top:2px solid {self.colors["hr"]};"></section>'
                f'</section>'
            ),
            html,
            flags=re.IGNORECASE,
        )

        # 标题样式
        html = re.sub(
            r"<h1>(.*?)</h1>",
            (
                f'<h1 style="font-size:30px; line-height:1.35; font-weight:800; margin:10px 0 24px; '
                f'color:{self.colors["title"]}; letter-spacing:0.5px;">\\1</h1>'
            ),
            html,
            flags=re.DOTALL,
        )

        html = re.sub(
            r"<h2>(.*?)</h2>",
            (
                f'<h2 style="font-size:22px; line-height:1.45; font-weight:700; margin:30px 0 14px; '
                f'padding-left:12px; border-left:4px solid {self.colors["accent"]}; '
                f'color:{self.colors["sub_title"]};">\\1</h2>'
            ),
            html,
            flags=re.DOTALL,
        )

        html = re.sub(
            r"<h3>(.*?)</h3>",
            (
                f'<h3 style="font-size:19px; line-height:1.45; font-weight:700; margin:22px 0 10px; '
                f'color:{self.colors["sub_title"]};">\\1</h3>'
            ),
            html,
            flags=re.DOTALL,
        )

        # 段落样式
        html = re.sub(
            r"<p>(.*?)</p>",
            (
                f'<p style="font-size:16px; line-height:1.9; margin:12px 0; '
                f'color:{self.colors["text"]}; text-align:justify;">\\1</p>'
            ),
            html,
            flags=re.DOTALL,
        )

        # 强调
        html = re.sub(
            r"<strong>(.*?)</strong>",
            (
                f'<strong style="color:{self.colors["title"]}; font-weight:700; '
                f'background:linear-gradient(transparent 62%, #eaf1ff 0);">\\1</strong>'
            ),
            html,
            flags=re.DOTALL,
        )

        html = re.sub(
            r"<em>(.*?)</em>",
            f'<em style="color:{self.colors["accent"]}; font-style:italic;">\\1</em>',
            html,
            flags=re.DOTALL,
        )

        # 代码块样式
        html = re.sub(
            r'<pre><code class="([^"]*)">(.*?)</code></pre>',
            (
                '<pre style="background-color:#0f172a; color:#e2e8f0; padding:14px 16px; '
                'border-radius:10px; overflow-x:auto; font-family:Consolas, Monaco, monospace; '
                'font-size:13px; line-height:1.7; margin:14px 0;"><code>\\2</code></pre>'
            ),
            html,
            flags=re.DOTALL,
        )

        # 行内代码样式
        html = re.sub(
            r"<code>(.*?)</code>",
            (
                '<code style="background-color:#eef2ff; padding:2px 6px; border-radius:4px; '
                'font-family:Consolas, Monaco, monospace; font-size:13px; color:#334155;">\\1</code>'
            ),
            html,
            flags=re.DOTALL,
        )

        # 引用样式
        html = re.sub(
            r"<blockquote>(.*?)</blockquote>",
            (
                f'<blockquote style="border-left:4px solid {self.colors["quote_border"]}; '
                f'background:{self.colors["quote_bg"]}; padding:10px 14px; border-radius:8px; '
                f'margin:16px 0; color:{self.colors["text"]};">\\1</blockquote>'
            ),
            html,
            flags=re.DOTALL,
        )

        # 列表样式
        html = re.sub(
            r"<ul>(.*?)</ul>",
            '<ul style="margin:12px 0; padding-left:22px;">\\1</ul>',
            html,
            flags=re.DOTALL,
        )
        html = re.sub(
            r"<ol>(.*?)</ol>",
            '<ol style="margin:12px 0; padding-left:22px;">\\1</ol>',
            html,
            flags=re.DOTALL,
        )
        html = re.sub(
            r"<li>(.*?)</li>",
            f'<li style="margin:8px 0; line-height:1.8; color:{self.colors["text"]};">\\1</li>',
            html,
            flags=re.DOTALL,
        )

        # 表格样式
        html = re.sub(
            r"<table>",
            '<table style="border-collapse:collapse; width:100%; margin:16px 0; font-size:14px;">',
            html,
            flags=re.IGNORECASE,
        )
        html = re.sub(
            r"<th>(.*?)</th>",
            '<th style="border:1px solid #dbe4f0; padding:8px; background:#f8fbff; text-align:left;">\\1</th>',
            html,
            flags=re.DOTALL,
        )
        html = re.sub(
            r"<td>(.*?)</td>",
            '<td style="border:1px solid #dbe4f0; padding:8px;">\\1</td>',
            html,
            flags=re.DOTALL,
        )

        # 链接样式
        html = re.sub(
            r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>',
            f'<a href="\\1" style="color:{self.colors["accent"]}; text-decoration:none; border-bottom:1px solid #c7d7ff;">\\2</a>',
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # 图片样式：已有style则追加；没有style则补齐
        img_default_style = "width:100%; border-radius:10px; display:block; margin:18px auto;"

        def _append_style(m):
            before = m.group(1)
            old_style = m.group(2).strip().rstrip(';')
            after = m.group(3)
            merged = f"{old_style}; {img_default_style}" if old_style else img_default_style
            return f'<img{before}style="{merged}"{after}>'

        html = re.sub(
            r'<img([^>]*?)style="([^"]*)"([^>]*?)>',
            _append_style,
            html,
            flags=re.IGNORECASE,
        )

        html = re.sub(
            r'<img(?![^>]*\bstyle=)([^>]*?)(/?)>',
            rf'<img\1 style="{img_default_style}"\2>',
            html,
            flags=re.IGNORECASE,
        )

        return html

    def _clean_unsupported_tags(self, html: str) -> str:
        """清理微信不支持的标签"""
        unsupported_tags = ["script", "iframe", "form", "input", "button", "video", "audio", "style"]
        for tag in unsupported_tags:
            html = re.sub(f"<{tag}[^>]*>.*?</{tag}>", "", html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(f"<{tag}[^>]*/>", "", html, flags=re.IGNORECASE)

        # 清理空段落
        html = re.sub(r'<p[^>]*>\s*</p>', '', html, flags=re.IGNORECASE)

        return html
