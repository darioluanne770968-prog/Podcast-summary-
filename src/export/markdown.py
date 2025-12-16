"""
Markdown 导出模块
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..utils import get_logger, ensure_dir, sanitize_filename

logger = get_logger(__name__)


@dataclass
class PodcastAnalysisResult:
    """播客分析结果"""
    title: str
    source_url: Optional[str] = None
    duration: Optional[float] = None
    publish_date: Optional[str] = None
    author: Optional[str] = None
    transcript: Optional[str] = None
    transcript_with_timestamps: Optional[str] = None
    summary: Optional[Any] = None
    chapters: Optional[List[Any]] = None
    keywords: Optional[List[Any]] = None
    quotes: Optional[List[Any]] = None
    sentiment: Optional[Any] = None
    qa_pairs: Optional[List[Any]] = None
    speaker_stats: Optional[Dict] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MarkdownExporter:
    """Markdown 导出器"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        初始化导出器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or Path("./output")
        ensure_dir(self.output_dir)

    def export(
        self,
        result: PodcastAnalysisResult,
        filename: Optional[str] = None,
        include_transcript: bool = False,
    ) -> Path:
        """
        导出为 Markdown 文件

        Args:
            result: 分析结果
            filename: 文件名（不含扩展名）
            include_transcript: 是否包含完整转录文本

        Returns:
            导出文件路径
        """
        logger.info("导出 Markdown...")

        # 生成文件名
        if not filename:
            filename = sanitize_filename(result.title or "podcast_notes")

        output_path = self.output_dir / f"{filename}.md"

        # 生成内容
        content = self._generate_content(result, include_transcript)

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Markdown 导出完成: {output_path}")
        return output_path

    def _generate_content(
        self,
        result: PodcastAnalysisResult,
        include_transcript: bool,
    ) -> str:
        """生成 Markdown 内容"""
        sections = []

        # 标题
        sections.append(f"# 🎙️ {result.title}\n")

        # 基本信息
        sections.append(self._generate_metadata_section(result))

        # 内容摘要
        if result.summary:
            sections.append(self._generate_summary_section(result.summary))

        # 章节目录
        if result.chapters:
            sections.append(self._generate_chapters_section(result.chapters))

        # 关键词
        if result.keywords:
            sections.append(self._generate_keywords_section(result.keywords))

        # 金句
        if result.quotes:
            sections.append(self._generate_quotes_section(result.quotes))

        # 情感分析
        if result.sentiment:
            sections.append(self._generate_sentiment_section(result.sentiment))

        # 问答
        if result.qa_pairs:
            sections.append(self._generate_qa_section(result.qa_pairs))

        # 说话人统计
        if result.speaker_stats:
            sections.append(self._generate_speaker_stats_section(result.speaker_stats))

        # 完整转录
        if include_transcript and result.transcript_with_timestamps:
            sections.append(self._generate_transcript_section(result.transcript_with_timestamps))

        # 页脚
        sections.append(self._generate_footer())

        return "\n".join(sections)

    def _generate_metadata_section(self, result: PodcastAnalysisResult) -> str:
        """生成元数据部分"""
        lines = ["## 📋 基本信息\n"]

        if result.duration:
            hours = int(result.duration // 3600)
            minutes = int((result.duration % 3600) // 60)
            seconds = int(result.duration % 60)
            if hours > 0:
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes}:{seconds:02d}"
            lines.append(f"- **时长**: {duration_str}")

        if result.publish_date:
            lines.append(f"- **发布日期**: {result.publish_date}")

        if result.author:
            lines.append(f"- **作者/频道**: {result.author}")

        if result.source_url:
            lines.append(f"- **来源**: [{result.source_url}]({result.source_url})")

        lines.append("")
        return "\n".join(lines)

    def _generate_summary_section(self, summary) -> str:
        """生成摘要部分"""
        lines = ["## 📝 内容摘要\n"]

        if hasattr(summary, "brief") and summary.brief:
            lines.append(f"**一句话概括**: {summary.brief}\n")

        if hasattr(summary, "detailed") and summary.detailed:
            lines.append(summary.detailed)
            lines.append("")

        if hasattr(summary, "key_points") and summary.key_points:
            lines.append("### 核心要点\n")
            for point in summary.key_points:
                lines.append(f"- {point}")
            lines.append("")

        if hasattr(summary, "takeaways") and summary.takeaways:
            lines.append("### 💡 收获与启发\n")
            for takeaway in summary.takeaways:
                lines.append(f"- {takeaway}")
            lines.append("")

        return "\n".join(lines)

    def _generate_chapters_section(self, chapters: List) -> str:
        """生成章节部分"""
        lines = ["## 📑 章节目录\n"]

        for chapter in chapters:
            if hasattr(chapter, "start_formatted"):
                time_str = chapter.start_formatted
            else:
                time_str = str(chapter.get("start_formatted", ""))

            if hasattr(chapter, "title"):
                title = chapter.title
            else:
                title = chapter.get("title", "")

            lines.append(f"- **[{time_str}]** {title}")

            # 章节摘要
            summary = getattr(chapter, "summary", None) or chapter.get("summary")
            if summary:
                lines.append(f"  - {summary}")

        lines.append("")
        return "\n".join(lines)

    def _generate_keywords_section(self, keywords: List) -> str:
        """生成关键词部分"""
        lines = ["## 🏷️ 关键词\n"]

        # 转换为标签格式
        tags = []
        for kw in keywords:
            if hasattr(kw, "word"):
                tags.append(f"`{kw.word}`")
            elif isinstance(kw, str):
                tags.append(f"`{kw}`")
            else:
                tags.append(f"`{kw.get('word', '')}`")

        lines.append(" ".join(tags))
        lines.append("")
        return "\n".join(lines)

    def _generate_quotes_section(self, quotes: List) -> str:
        """生成金句部分"""
        lines = ["## 💬 金句摘录\n"]

        for quote in quotes:
            if hasattr(quote, "text"):
                text = quote.text
                speaker = getattr(quote, "speaker", None)
                timestamp = getattr(quote, "timestamp_formatted", "")
            else:
                text = quote.get("text", "")
                speaker = quote.get("speaker")
                timestamp = quote.get("timestamp_formatted", "")

            speaker_part = f" — {speaker}" if speaker else ""
            time_part = f" [{timestamp}]" if timestamp else ""

            lines.append(f"> \"{text}\"{speaker_part}{time_part}\n")

        return "\n".join(lines)

    def _generate_sentiment_section(self, sentiment) -> str:
        """生成情感分析部分"""
        lines = ["## 😊 情感分析\n"]

        if hasattr(sentiment, "tone"):
            lines.append(f"**整体基调**: {sentiment.tone}\n")

        if hasattr(sentiment, "emotions") and sentiment.emotions:
            lines.append("**情感分布**:\n")
            for emotion, score in sorted(
                sentiment.emotions.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                if score > 0.05:  # 只显示大于5%的情感
                    bar_length = int(score * 20)
                    bar = "█" * bar_length + "░" * (20 - bar_length)
                    lines.append(f"- {emotion}: {bar} {score * 100:.0f}%")

        lines.append("")
        return "\n".join(lines)

    def _generate_qa_section(self, qa_pairs: List) -> str:
        """生成问答部分"""
        lines = ["## ❓ 问答复习\n"]

        for i, qa in enumerate(qa_pairs, 1):
            if hasattr(qa, "question"):
                question = qa.question
                answer = qa.answer
            else:
                question = qa.get("question", "")
                answer = qa.get("answer", "")

            lines.append(f"**Q{i}: {question}**\n")
            lines.append(f"A: {answer}\n")

        return "\n".join(lines)

    def _generate_speaker_stats_section(self, speaker_stats: Dict) -> str:
        """生成说话人统计部分"""
        lines = ["## 👥 说话人统计\n"]

        for speaker, stats in speaker_stats.items():
            duration = stats.get("total_duration_formatted", "")
            percentage = stats.get("percentage", 0)
            lines.append(f"- **{speaker}**: {duration} ({percentage:.1f}%)")

        lines.append("")
        return "\n".join(lines)

    def _generate_transcript_section(self, transcript: str) -> str:
        """生成转录文本部分"""
        lines = [
            "## 📜 完整转录\n",
            "<details>",
            "<summary>点击展开完整转录文本</summary>\n",
            "```",
            transcript,
            "```",
            "</details>\n",
        ]
        return "\n".join(lines)

    def _generate_footer(self) -> str:
        """生成页脚"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"\n---\n*Generated by Podcast Summary Tool on {now}*\n"
