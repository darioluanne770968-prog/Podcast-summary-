"""
音频下载模块

支持：
- 本地文件
- YouTube 视频/音频
- 播客 RSS 订阅
- 小宇宙播客
- 直接 URL
"""

import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse

import feedparser

from ..utils import get_logger, sanitize_filename, ensure_dir

logger = get_logger(__name__)


class SourceType(str, Enum):
    """音频来源类型"""
    LOCAL = "local"
    YOUTUBE = "youtube"
    RSS = "rss"
    XIAOYUZHOU = "xiaoyuzhou"
    DIRECT_URL = "direct_url"


@dataclass
class PodcastSource:
    """播客来源信息"""
    source_type: SourceType
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[float] = None
    publish_date: Optional[str] = None
    author: Optional[str] = None
    local_path: Optional[Path] = None
    metadata: dict = field(default_factory=dict)


class AudioDownloader:
    """音频下载器"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        初始化下载器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "podcast_summary"
        ensure_dir(self.output_dir)

    def detect_source_type(self, source: str) -> SourceType:
        """
        检测音频来源类型

        Args:
            source: 来源字符串（URL 或文件路径）

        Returns:
            SourceType 枚举
        """
        # 本地文件
        if Path(source).exists():
            return SourceType.LOCAL

        # URL 解析
        parsed = urlparse(source)

        # YouTube
        if parsed.netloc in ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"]:
            return SourceType.YOUTUBE

        # 小宇宙
        if "xiaoyuzhou" in parsed.netloc or "xyzfm" in parsed.netloc:
            return SourceType.XIAOYUZHOU

        # RSS Feed（检查内容）
        if source.endswith(".xml") or source.endswith(".rss") or "/feed" in source:
            return SourceType.RSS

        # 默认为直接 URL
        return SourceType.DIRECT_URL

    async def download(
        self,
        source: str,
        output_filename: Optional[str] = None,
    ) -> PodcastSource:
        """
        下载音频

        Args:
            source: 来源（URL 或文件路径）
            output_filename: 输出文件名（可选）

        Returns:
            PodcastSource 对象
        """
        source_type = self.detect_source_type(source)
        logger.info(f"检测到来源类型: {source_type.value}")

        if source_type == SourceType.LOCAL:
            return await self._handle_local(source)
        elif source_type == SourceType.YOUTUBE:
            return await self._download_youtube(source, output_filename)
        elif source_type == SourceType.RSS:
            return await self._download_from_rss(source, output_filename)
        elif source_type == SourceType.XIAOYUZHOU:
            return await self._download_xiaoyuzhou(source, output_filename)
        else:
            return await self._download_direct_url(source, output_filename)

    async def _handle_local(self, file_path: str) -> PodcastSource:
        """处理本地文件"""
        path = Path(file_path)
        logger.info(f"使用本地文件: {path}")

        return PodcastSource(
            source_type=SourceType.LOCAL,
            url=str(path.absolute()),
            title=path.stem,
            local_path=path,
        )

    async def _download_youtube(
        self,
        url: str,
        output_filename: Optional[str] = None,
    ) -> PodcastSource:
        """
        从 YouTube 下载音频

        Args:
            url: YouTube URL
            output_filename: 输出文件名

        Returns:
            PodcastSource 对象
        """
        try:
            import yt_dlp
        except ImportError:
            raise ImportError("请安装 yt-dlp: pip install yt-dlp")

        logger.info(f"从 YouTube 下载: {url}")

        # 配置 yt-dlp
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": str(self.output_dir / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }

        if output_filename:
            ydl_opts["outtmpl"] = str(self.output_dir / f"{output_filename}.%(ext)s")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 获取视频信息
            info = ydl.extract_info(url, download=True)

            # 获取下载后的文件路径
            title = sanitize_filename(info.get("title", "unknown"))
            output_path = self.output_dir / f"{title}.mp3"

            return PodcastSource(
                source_type=SourceType.YOUTUBE,
                url=url,
                title=info.get("title"),
                description=info.get("description"),
                duration=info.get("duration"),
                publish_date=info.get("upload_date"),
                author=info.get("uploader"),
                local_path=output_path,
                metadata={
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "channel": info.get("channel"),
                    "thumbnail": info.get("thumbnail"),
                },
            )

    async def _download_from_rss(
        self,
        rss_url: str,
        output_filename: Optional[str] = None,
        episode_index: int = 0,
    ) -> PodcastSource:
        """
        从 RSS 订阅下载最新一期

        Args:
            rss_url: RSS 订阅 URL
            output_filename: 输出文件名
            episode_index: 要下载的期数索引（0 为最新）

        Returns:
            PodcastSource 对象
        """
        logger.info(f"解析 RSS 订阅: {rss_url}")

        feed = feedparser.parse(rss_url)

        if not feed.entries:
            raise ValueError("RSS 订阅中没有找到任何节目")

        # 获取指定期数
        entry = feed.entries[episode_index]

        # 查找音频链接
        audio_url = None
        for link in entry.get("links", []):
            if link.get("type", "").startswith("audio/"):
                audio_url = link.get("href")
                break

        # 尝试从 enclosures 获取
        if not audio_url and entry.get("enclosures"):
            for enc in entry.enclosures:
                if enc.get("type", "").startswith("audio/"):
                    audio_url = enc.get("href")
                    break

        if not audio_url:
            raise ValueError("未找到音频链接")

        # 下载音频
        result = await self._download_direct_url(audio_url, output_filename)

        # 更新元数据
        result.source_type = SourceType.RSS
        result.title = entry.get("title", result.title)
        result.description = entry.get("summary", "")
        result.publish_date = entry.get("published", "")
        result.author = feed.feed.get("author", feed.feed.get("title", ""))
        result.metadata.update({
            "feed_title": feed.feed.get("title"),
            "feed_link": feed.feed.get("link"),
            "episode_link": entry.get("link"),
        })

        return result

    async def _download_xiaoyuzhou(
        self,
        url: str,
        output_filename: Optional[str] = None,
    ) -> PodcastSource:
        """
        从小宇宙下载音频

        Args:
            url: 小宇宙 URL
            output_filename: 输出文件名

        Returns:
            PodcastSource 对象
        """
        import aiohttp

        logger.info(f"从小宇宙下载: {url}")

        # 提取节目 ID
        match = re.search(r"episode/([a-zA-Z0-9]+)", url)
        if not match:
            raise ValueError("无法解析小宇宙 URL")

        episode_id = match.group(1)

        # 获取节目信息（使用小宇宙 API）
        api_url = f"https://www.xiaoyuzhoufm.com/episode/{episode_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status != 200:
                    raise ValueError(f"获取小宇宙节目信息失败: {response.status}")

                html = await response.text()

                # 从 HTML 中提取音频 URL（简化处理）
                audio_match = re.search(r'"enclosure":\s*{\s*"url":\s*"([^"]+)"', html)
                if not audio_match:
                    audio_match = re.search(r'<audio[^>]+src="([^"]+)"', html)

                if not audio_match:
                    raise ValueError("无法从小宇宙页面提取音频 URL")

                audio_url = audio_match.group(1)

        # 下载音频
        result = await self._download_direct_url(audio_url, output_filename)
        result.source_type = SourceType.XIAOYUZHOU
        result.url = url

        return result

    async def _download_direct_url(
        self,
        url: str,
        output_filename: Optional[str] = None,
    ) -> PodcastSource:
        """
        直接下载 URL

        Args:
            url: 音频 URL
            output_filename: 输出文件名

        Returns:
            PodcastSource 对象
        """
        import aiohttp

        logger.info(f"下载音频: {url}")

        # 确定文件名
        if output_filename:
            filename = sanitize_filename(output_filename)
        else:
            parsed = urlparse(url)
            filename = sanitize_filename(Path(parsed.path).stem or "audio")

        # 确定扩展名
        ext = Path(urlparse(url).path).suffix or ".mp3"
        output_path = self.output_dir / f"{filename}{ext}"

        # 下载文件
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"下载失败: HTTP {response.status}")

                with open(output_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)

        logger.info(f"下载完成: {output_path}")

        return PodcastSource(
            source_type=SourceType.DIRECT_URL,
            url=url,
            title=filename,
            local_path=output_path,
        )

    def list_rss_episodes(self, rss_url: str, limit: int = 10) -> List[dict]:
        """
        列出 RSS 订阅中的节目

        Args:
            rss_url: RSS 订阅 URL
            limit: 最大返回数量

        Returns:
            节目列表
        """
        feed = feedparser.parse(rss_url)

        episodes = []
        for i, entry in enumerate(feed.entries[:limit]):
            episodes.append({
                "index": i,
                "title": entry.get("title", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")[:200] + "...",
                "link": entry.get("link", ""),
            })

        return episodes
