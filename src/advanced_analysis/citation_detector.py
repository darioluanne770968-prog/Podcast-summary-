"""
引用检测模块

识别播客中引用的书籍、文章、研究、人物言论等
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from ..analysis import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


class CitationType(str, Enum):
    """引用类型"""
    BOOK = "book"
    PAPER = "paper"
    ARTICLE = "article"
    QUOTE = "quote"  # 人物引言
    STUDY = "study"
    STATISTIC = "statistic"
    PODCAST = "podcast"
    VIDEO = "video"
    WEBSITE = "website"
    OTHER = "other"


@dataclass
class Citation:
    """引用"""
    type: CitationType
    title: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    year: Optional[str] = None
    quote_text: Optional[str] = None  # 引用的原文
    context: Optional[str] = None  # 引用的上下文
    timestamp: Optional[float] = None
    url: Optional[str] = None  # 如果能找到链接
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "title": self.title,
            "author": self.author,
            "source": self.source,
            "year": self.year,
            "quote_text": self.quote_text,
            "context": self.context,
            "timestamp": self.timestamp,
            "url": self.url,
            "confidence": self.confidence,
        }

    def to_citation_string(self) -> str:
        """生成引用字符串"""
        parts = []
        if self.author:
            parts.append(self.author)
        if self.title:
            parts.append(f"《{self.title}》" if self.type == CitationType.BOOK else f'"{self.title}"')
        if self.source:
            parts.append(self.source)
        if self.year:
            parts.append(f"({self.year})")

        return ", ".join(parts) if parts else "Unknown source"


class CitationDetector:
    """引用检测器"""

    SYSTEM_PROMPT = """你是一个引用检测专家，擅长识别文本中引用的各类来源。

识别的引用类型：
- book: 书籍
- paper: 学术论文
- article: 文章（新闻、博客等）
- quote: 人物言论引用
- study: 研究/调查
- statistic: 统计数据
- podcast: 播客引用
- video: 视频引用
- website: 网站引用

识别原则：
1. 准确识别引用的来源信息
2. 区分直接引用和间接提及
3. 提取引用的具体内容
4. 如果信息不完整，标记为低置信度"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def detect(
        self,
        transcript_with_timestamps: str,
        citation_types: Optional[List[CitationType]] = None,
    ) -> List[Citation]:
        """
        检测播客中的引用

        Args:
            transcript_with_timestamps: 带时间戳的转录文本
            citation_types: 要检测的引用类型（None 表示全部）

        Returns:
            Citation 列表
        """
        logger.info("开始引用检测...")

        types_str = ""
        if citation_types:
            types_str = f"只检测以下类型：{', '.join(t.value for t in citation_types)}"

        prompt = f"""分析以下播客转录文本，识别其中引用的所有来源。

{types_str}

文本：
---
{transcript_with_timestamps[:30000]}
---

请识别所有引用，按以下 JSON 格式输出：

```json
[
  {{
    "type": "book/paper/article/quote/study/statistic/podcast/video/website/other",
    "title": "标题/名称",
    "author": "作者",
    "source": "来源出处",
    "year": "年份",
    "quote_text": "引用的具体内容",
    "context": "引用的上下文（为什么提到这个）",
    "timestamp": 123.5,
    "confidence": 0.9
  }}
]
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.2)
            data = self.llm.parse_json_response(response)

            citations = []
            for item in data:
                citation = Citation(
                    type=CitationType(item.get("type", "other")),
                    title=item.get("title"),
                    author=item.get("author"),
                    source=item.get("source"),
                    year=item.get("year"),
                    quote_text=item.get("quote_text"),
                    context=item.get("context"),
                    timestamp=item.get("timestamp"),
                    confidence=float(item.get("confidence", 0.8)),
                )
                citations.append(citation)

            logger.info(f"检测到 {len(citations)} 个引用")
            return citations

        except Exception as e:
            logger.error(f"引用检测失败: {e}")
            return []

    def group_by_type(self, citations: List[Citation]) -> dict:
        """按类型分组引用"""
        groups = {}
        for citation in citations:
            if citation.type not in groups:
                groups[citation.type] = []
            groups[citation.type].append(citation)
        return groups

    def generate_bibliography(
        self,
        citations: List[Citation],
        style: str = "simple",
    ) -> str:
        """
        生成参考文献列表

        Args:
            citations: 引用列表
            style: 格式风格 (simple, apa, chicago)

        Returns:
            格式化的参考文献
        """
        lines = ["## 📚 参考文献\n"]

        groups = self.group_by_type(citations)

        type_titles = {
            CitationType.BOOK: "📖 书籍",
            CitationType.PAPER: "📄 论文",
            CitationType.ARTICLE: "📰 文章",
            CitationType.QUOTE: "💬 人物引言",
            CitationType.STUDY: "🔬 研究",
            CitationType.STATISTIC: "📊 统计数据",
            CitationType.PODCAST: "🎙️ 播客",
            CitationType.VIDEO: "🎬 视频",
            CitationType.WEBSITE: "🌐 网站",
        }

        for citation_type, type_citations in groups.items():
            title = type_titles.get(citation_type, "其他")
            lines.append(f"### {title}\n")

            for i, citation in enumerate(type_citations, 1):
                if style == "simple":
                    lines.append(f"{i}. {citation.to_citation_string()}")
                    if citation.context:
                        lines.append(f"   - 上下文: {citation.context[:100]}...")
                elif style == "apa":
                    # APA 格式简化版
                    apa = f"{citation.author or 'Unknown'}. "
                    if citation.year:
                        apa += f"({citation.year}). "
                    if citation.title:
                        apa += f"*{citation.title}*. "
                    if citation.source:
                        apa += citation.source
                    lines.append(f"{i}. {apa}")

            lines.append("")

        return "\n".join(lines)

    def generate_reading_list(self, citations: List[Citation]) -> str:
        """生成推荐阅读列表（仅书籍和论文）"""
        books_papers = [
            c for c in citations
            if c.type in [CitationType.BOOK, CitationType.PAPER]
        ]

        if not books_papers:
            return "没有检测到书籍或论文引用。"

        lines = ["## 📖 推荐阅读\n"]
        lines.append("*以下是播客中提到的书籍和论文：*\n")

        for citation in books_papers:
            emoji = "📕" if citation.type == CitationType.BOOK else "📄"
            lines.append(f"- {emoji} **{citation.title or 'Unknown'}**")
            if citation.author:
                lines.append(f"  - 作者: {citation.author}")
            if citation.context:
                lines.append(f"  - 提及原因: {citation.context[:100]}...")
            lines.append("")

        return "\n".join(lines)
