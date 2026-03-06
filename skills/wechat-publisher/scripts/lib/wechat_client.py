"""WeChat Official Account API client"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any
import httpx


class AccessTokenCache:
    """access_token缓存管理"""

    def __init__(self):
        self._token: Optional[str] = None
        self._expires_at: float = 0
        self._lock = asyncio.Lock()

    def is_valid(self) -> bool:
        """检查token是否有效"""
        return self._token is not None and time.time() < self._expires_at

    def get(self) -> Optional[str]:
        """获取token"""
        if self.is_valid():
            return self._token
        return None

    def set(self, token: str, ttl_seconds: int):
        """设置token"""
        self._token = token
        self._expires_at = time.time() + ttl_seconds

    def clear(self):
        """清除token"""
        self._token = None
        self._expires_at = 0

    async def get_lock(self):
        """获取锁"""
        return self._lock


class WeChatClient:
    """微信公众号API客户端"""

    BASE_URL = "https://api.weixin.qq.com"

    def __init__(self, appid: str, secret: str, cache_seconds: int = 7000):
        """初始化微信客户端

        Args:
            appid: 微信公众号AppID
            secret: 微信公众号AppSecret
            cache_seconds: access_token缓存时长(秒)
        """
        if not appid or not secret:
            raise ValueError("WECHAT_APPID 和 WECHAT_SECRET 未配置")

        self.appid = appid
        self.secret = secret
        self.cache_seconds = cache_seconds
        self.logger = logging.getLogger(__name__)
        self._token_cache = AccessTokenCache()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_access_token(self, force_refresh: bool = False) -> str:
        """获取access_token

        Args:
            force_refresh: 是否强制刷新

        Returns:
            access_token

        Raises:
            RuntimeError: 获取失败
        """
        # 如果缓存有效且不强制刷新,直接返回
        if not force_refresh:
            cached_token = self._token_cache.get()
            if cached_token:
                return cached_token

        # 使用锁避免并发请求
        async with await self._token_cache.get_lock():
            # 双重检查
            if not force_refresh:
                cached_token = self._token_cache.get()
                if cached_token:
                    return cached_token

            # 请求新token
            self.logger.info(f"Requesting new access_token{' (force refresh)' if force_refresh else ''}")

            url = f"{self.BASE_URL}/cgi-bin/stable_token"
            payload = {
                "grant_type": "client_credential",
                "appid": self.appid,
                "secret": self.secret,
                "force_refresh": force_refresh,
            }

            try:
                client = await self._get_client()
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

                if "errcode" in data and data["errcode"] != 0:
                    errcode = data["errcode"]
                    errmsg = data.get("errmsg", "Unknown error")
                    raise RuntimeError(f"获取access_token失败: {errmsg} (errcode={errcode})")

                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 7200)

                if not access_token:
                    raise RuntimeError("access_token为空")

                # 预留 200 秒安全窗口
                cache_duration = max(1, min(expires_in - 200, self.cache_seconds))
                self._token_cache.set(access_token, cache_duration)
                self.logger.info(f"access_token获取成功,缓存时长: {cache_duration}秒")

                return access_token

            except httpx.HTTPError as e:
                self.logger.error(f"HTTP请求失败: {str(e)}")
                raise RuntimeError(f"网络请求失败: {str(e)}")

    async def publish_to_draft(
        self,
        title: str,
        content: str,
        author: str = "日新",
        thumb_media_id: str = "",
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """发布文章到草稿箱

        Args:
            title: 文章标题
            content: 文章内容(HTML格式)
            author: 作者
            thumb_media_id: 封面图片media_id
            max_retries: 最大重试次数

        Returns:
            发布结果

        Raises:
            RuntimeError: 发布失败
        """
        for attempt in range(max_retries + 1):
            try:
                # 获取access_token
                access_token = await self.get_access_token()

                url = f"{self.BASE_URL}/cgi-bin/draft/add"
                params = {"access_token": access_token}

                # 构建请求体
                article = {
                    "title": title,
                    "author": author,
                    "content": content,
                    "digest": "",
                    "content_source_url": "",
                    "need_open_comment": 0,
                    "only_fans_can_comment": 0,
                }

                # 只有提供了封面图时才添加相关字段
                if thumb_media_id:
                    article["thumb_media_id"] = thumb_media_id
                    article["show_cover_pic"] = 1

                payload = {"articles": [article]}

                client = await self._get_client()
                response = await client.post(url, params=params, json=payload)
                response.raise_for_status()
                data = response.json()

                if "errcode" in data and data["errcode"] != 0:
                    errcode = data["errcode"]
                    errmsg = data.get("errmsg", "Unknown error")

                    # Token失效错误码: 40001, 40014, 42001
                    if errcode in [40001, 40014, 42001] and attempt < max_retries:
                        self.logger.warning(f"Token失效(errcode={errcode}),刷新并重试...")
                        self._token_cache.clear()
                        await asyncio.sleep(1)
                        continue

                    raise RuntimeError(f"发布失败: {errmsg} (errcode={errcode})")

                media_id = data.get("media_id", "")
                self.logger.info(f"文章发布成功,media_id: {media_id}")

                return {
                    "media_id": media_id,
                    "draft_id": media_id,
                    "draft_url": "https://mp.weixin.qq.com/",
                    "created_at": datetime.utcnow(),
                }

            except httpx.HTTPError as e:
                if attempt < max_retries:
                    self.logger.warning(f"HTTP请求失败,重试中... (尝试 {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(2 ** attempt)
                    continue
                self.logger.error(f"HTTP请求失败: {str(e)}")
                raise RuntimeError(f"网络请求失败: {str(e)}")

        raise RuntimeError("发布失败: 超过最大重试次数")

    async def upload_image(
        self,
        image_bytes: bytes,
        filename: str = "image.jpg",
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """上传图片到微信永久素材

        Args:
            image_bytes: 图片二进制数据
            filename: 文件名
            max_retries: 最大重试次数

        Returns:
            包含 media_id 和 url 的字典

        Raises:
            RuntimeError: 上传失败
        """
        for attempt in range(max_retries + 1):
            try:
                # 获取access_token
                access_token = await self.get_access_token()

                url = f"{self.BASE_URL}/cgi-bin/material/add_material"
                params = {"access_token": access_token, "type": "image"}

                # 构建multipart/form-data
                files = {
                    "media": (filename, image_bytes, "image/jpeg"),
                }

                client = await self._get_client()
                response = await client.post(url, params=params, files=files)
                response.raise_for_status()
                data = response.json()

                if "errcode" in data and data["errcode"] != 0:
                    errcode = data["errcode"]
                    errmsg = data.get("errmsg", "Unknown error")

                    # Token失效错误码
                    if errcode in [40001, 40014, 42001] and attempt < max_retries:
                        self.logger.warning(f"Token失效(errcode={errcode}),刷新并重试...")
                        self._token_cache.clear()
                        await asyncio.sleep(1)
                        continue

                    raise RuntimeError(f"上传失败: {errmsg} (errcode={errcode})")

                media_id = data.get("media_id", "")
                url = data.get("url", "")
                self.logger.info(f"图片上传成功, media_id: {media_id}")

                return {
                    "media_id": media_id,
                    "url": url,
                }

            except httpx.HTTPError as e:
                if attempt < max_retries:
                    self.logger.warning(f"HTTP请求失败,重试中... (尝试 {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(2 ** attempt)
                    continue
                self.logger.error(f"HTTP请求失败: {str(e)}")
                raise RuntimeError(f"网络请求失败: {str(e)}")

        raise RuntimeError("图片上传失败: 超过最大重试次数")