"""
章节分割模块
"""

from dataclasses import dataclass, field
from typing import Optional, List

from .llm_client import LLMClient
from ..utils import get_logger, format_timestamp

logger = get_logger(__name__)


@dataclass
class Chapter:
    """章节"""
    index: int
    title: str
    start_time: float
    end_time: Optional[float] = None
    summary: Optional[str] = None
    keywords: List[str] = field(default_factory=list)

    @property
    def start_formatted(self) -> str:
        return format_timestamp(self.start_time)

    @property
    def end_formatted(self) -> str:
        return format_timestamp(self.end_time) if self.end_time else ""

    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "start_formatted": self.start_formatted,
            "end_formatted": self.end_formatted,
            "duration": self.duration,
            "summary": self.summary,
            "keywords": self.keywords,
        }


class ChapterGenerator:
    """章节生成器"""

    SYSTEM_PROMPT = """你是一个专业的播客编辑，擅长将播客内容分割成有意义的章节。

分割章节时请：
1. 识别话题转换点
2. 为每个章节提供简洁的标题
3. 确保章节划分逻辑清晰
4. 每个章节应该有明确的主题"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """初始化章节生成器"""
        self.llm = llm_client or LLMClient()

    def generate(
        self,
        transcript_with_timestamps: str,
        min_chapter_duration: float = 60.0,
        max_chapters: int = 15,
    ) -> List[Chapter]:
        """
        生成章节

        Args:
            transcript_with_timestamps: 带时间戳的转录文本
            min_chapter_duration: 最小章节时长（秒）
            max_chapters: 最大章节数量

        Returns:
            Chapter 列表
        """
        logger.info("生成章节...")

        prompt = f"""分析以下带时间戳的播客转录文本，将其分割成有意义的章节。

文本（格式：[时间戳] 内容）：
---
{transcript_with_timestamps[:40000]}
---

要求：
1. 每个章节至少 {min_chapter_duration} 秒
2. 最多 {max_chapters} 个章节
3. 章节标题应简洁明了（5-15个字）
4. 识别话题的自然转换点

请按以下 JSON 格式输出：

```json
[
  {{
    "title": "章节标题",
    "start_time": 0.0,
    "summary": "简短描述该章节内容",
    "keywords": ["关键词1", "关键词2"]
  }},
  ...
]
```

注意：start_time 使用秒数（浮点数），从转录文本的时间戳中提取。
只输出 JSON，不要其他内容。"""

        response = self.llm.complete(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.3,
        )

        chapters = self._parse_response(response)

        # 计算结束时间
        for i, chapter in enumerate(chapters):
            if i < len(chapters) - 1:
                chapter.end_time = chapters[i + 1].start_time

        logger.info(f"生成了 {len(chapters)} 个章节")
        return chapters

    def _parse_response(self, response: str) -> List[Chapter]:
        """解析响应"""
        try:
            data = self.llm.parse_json_response(response)

            chapters = []
            for i, item in enumerate(data):
                chapters.append(
                    Chapter(
                        index=i,
                        title=item.get("title", f"章节 {i + 1}"),
                        start_time=float(item.get("start_time", 0)),
                        summary=item.get("summary"),
                        keywords=item.get("keywords", []),
                    )
                )
            return chapters

        except Exception as e:
            logger.error(f"解析章节响应失败: {e}")
            return []

    def generate_toc(self, chapters: List[Chapter]) -> str:
        """
        生成目录（Table of Contents）

        Args:
            chapters: 章节列表

        Returns:
            Markdown 格式的目录
        """
        lines = ["## 📑 章节目录\n"]

        for chapter in chapters:
            lines.append(f"- [{chapter.start_formatted}] {chapter.title}")

        return "\n".join(lines)

    def generate_youtube_chapters(self, chapters: List[Chapter]) -> str:
        """
        生成 YouTube 章节格式

        Args:
            chapters: 章节列表

        Returns:
            YouTube 章节格式文本
        """
        lines = []
        for chapter in chapters:
            lines.append(f"{chapter.start_formatted} {chapter.title}")
        return "\n".join(lines)
