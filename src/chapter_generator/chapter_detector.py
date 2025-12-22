"""
章节检测器
自动检测播客中的章节分界点
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np


class ChapterType(Enum):
    INTRO = "intro"
    MAIN_CONTENT = "main_content"
    SEGMENT = "segment"
    INTERVIEW = "interview"
    QA = "qa"
    SPONSOR = "sponsor"
    OUTRO = "outro"


@dataclass
class Chapter:
    start_time: float
    end_time: float
    title: str
    chapter_type: ChapterType
    confidence: float
    summary: str
    keywords: List[str]


@dataclass
class ChapterDetectionResult:
    chapters: List[Chapter]
    total_duration: float
    chapter_count: int
    has_intro: bool
    has_outro: bool


class ChapterDetector:
    """章节检测器"""

    def __init__(self):
        self.min_chapter_duration = 60  # 最短章节60秒
        self.max_chapters = 20

    def detect_chapters(
        self,
        transcript: str,
        audio_features: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None
    ) -> ChapterDetectionResult:
        """检测章节"""
        # 估算时长
        if duration is None:
            duration = len(transcript) / 175 * 60

        chapters = []

        # 检测开场
        intro_end = self._detect_intro(transcript, duration)
        if intro_end > 0:
            chapters.append(Chapter(
                start_time=0,
                end_time=intro_end,
                title="开场介绍",
                chapter_type=ChapterType.INTRO,
                confidence=0.9,
                summary="节目开场和主题介绍",
                keywords=["开场", "介绍"]
            ))

        # 检测主要内容分段
        main_chapters = self._detect_main_chapters(transcript, intro_end, duration * 0.9)
        chapters.extend(main_chapters)

        # 检测结尾
        if duration > 300:
            chapters.append(Chapter(
                start_time=duration - 60,
                end_time=duration,
                title="总结与结尾",
                chapter_type=ChapterType.OUTRO,
                confidence=0.85,
                summary="节目总结和结束语",
                keywords=["总结", "结尾"]
            ))

        return ChapterDetectionResult(
            chapters=chapters,
            total_duration=duration,
            chapter_count=len(chapters),
            has_intro=any(c.chapter_type == ChapterType.INTRO for c in chapters),
            has_outro=any(c.chapter_type == ChapterType.OUTRO for c in chapters)
        )

    def _detect_intro(self, transcript: str, duration: float) -> float:
        """检测开场结束点"""
        intro_indicators = ["今天", "欢迎", "开始", "本期", "这一期"]
        first_500_chars = transcript[:500]

        for indicator in intro_indicators:
            if indicator in first_500_chars:
                return min(120, duration * 0.1)  # 最多2分钟
        return 60

    def _detect_main_chapters(
        self,
        transcript: str,
        start_time: float,
        end_time: float
    ) -> List[Chapter]:
        """检测主要章节"""
        chapters = []
        duration = end_time - start_time

        # 基于话题转换检测
        topic_markers = ["接下来", "另外", "第一", "第二", "首先", "然后", "最后"]

        # 简化实现：均匀分割
        num_chapters = min(5, int(duration / 300))  # 每5分钟一个章节
        chapter_duration = duration / num_chapters

        for i in range(num_chapters):
            chapter_start = start_time + i * chapter_duration
            chapter_end = start_time + (i + 1) * chapter_duration

            chapters.append(Chapter(
                start_time=chapter_start,
                end_time=chapter_end,
                title=f"第{i + 1}部分",
                chapter_type=ChapterType.MAIN_CONTENT,
                confidence=0.7,
                summary=f"主要内容第{i + 1}部分",
                keywords=[]
            ))

        return chapters

    def format_chapters_for_youtube(self, chapters: List[Chapter]) -> str:
        """格式化为YouTube时间戳"""
        lines = []
        for chapter in chapters:
            minutes = int(chapter.start_time // 60)
            seconds = int(chapter.start_time % 60)
            lines.append(f"{minutes:02d}:{seconds:02d} {chapter.title}")
        return "\n".join(lines)
