"""
多媒体内容生成模块

功能：
- 短视频/片段生成
- 封面/配图生成
- 语音摘要生成（TTS）
- 社交媒体帖子生成
- 文章/博客生成
- 信息图表生成
"""

from .video_clipper import VideoClipper, VideoClip
from .cover_generator import CoverGenerator
from .tts_summary import TTSSummaryGenerator
from .social_posts import SocialPostGenerator, SocialPlatform
from .article_generator import ArticleGenerator
from .infographic import InfographicGenerator

__all__ = [
    "VideoClipper",
    "VideoClip",
    "CoverGenerator",
    "TTSSummaryGenerator",
    "SocialPostGenerator",
    "SocialPlatform",
    "ArticleGenerator",
    "InfographicGenerator",
]
