"""
章节自动生成模块
智能分割播客章节，生成时间戳目录
"""

from .chapter_detector import ChapterDetector
from .timestamp_generator import TimestampGenerator
from .chapter_namer import ChapterNamer

__all__ = ['ChapterDetector', 'TimestampGenerator', 'ChapterNamer']
