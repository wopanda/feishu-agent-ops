"""Image compressor for WeChat Official Account"""
import io
import logging
from typing import Tuple
from PIL import Image


class ImageCompressor:
    """图片压缩器，确保符合微信要求"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def compress(
        self,
        image_bytes: bytes,
        max_size_kb: int = 64,
        target_dimensions: Tuple[int, int] = (900, 500),
        quality: int = 85,
    ) -> bytes:
        """压缩图片

        Args:
            image_bytes: 原始图片二进制数据
            max_size_kb: 最大文件大小(KB)
            target_dimensions: 目标尺寸 (width, height)
            quality: 初始质量 (1-100)

        Returns:
            压缩后的图片二进制数据

        Raises:
            ValueError: 图片处理失败
        """
        try:
            # 打开图片
            img = Image.open(io.BytesIO(image_bytes))

            # 转换为RGB模式（如果是RGBA或其他模式）
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 调整尺寸
            img.thumbnail(target_dimensions, Image.Resampling.LANCZOS)

            # 尝试压缩到目标大小
            current_quality = quality
            output = io.BytesIO()

            while current_quality > 10:
                output.seek(0)
                output.truncate()
                img.save(output, format="JPEG", quality=current_quality, optimize=True)

                size_kb = output.tell() / 1024

                if size_kb <= max_size_kb:
                    self.logger.info(
                        f"图片压缩成功: {size_kb:.1f}KB (质量={current_quality}, 尺寸={img.size})"
                    )
                    return output.getvalue()

                # 降低质量继续尝试
                current_quality -= 5

            # 如果还是太大，进一步缩小尺寸
            self.logger.warning(f"质量降低到10仍超过{max_size_kb}KB，尝试缩小尺寸")
            scale_factor = 0.8
            new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

            output.seek(0)
            output.truncate()
            img.save(output, format="JPEG", quality=75, optimize=True)

            size_kb = output.tell() / 1024
            self.logger.info(f"图片压缩成功(缩小尺寸): {size_kb:.1f}KB (尺寸={img.size})")

            return output.getvalue()

        except Exception as e:
            self.logger.error(f"图片压缩失败: {str(e)}")
            raise ValueError(f"图片压缩失败: {str(e)}")