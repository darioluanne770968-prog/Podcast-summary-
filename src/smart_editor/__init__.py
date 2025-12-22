"""
智能剪辑工具模块
自动识别精彩片段，生成短视频/社交媒体内容
"""

from .highlight_detector import HighlightDetector
from .clip_generator import ClipGenerator
from .social_media_formatter import SocialMediaFormatter
from .viral_predictor import ViralPredictor

__all__ = [
    'HighlightDetector',
    'ClipGenerator',
    'SocialMediaFormatter',
    'ViralPredictor'
]
