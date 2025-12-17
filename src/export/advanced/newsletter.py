"""
Newsletter 邮件生成模块

生成适合邮件发送的 Newsletter 格式内容
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import html

from ...utils import get_logger, ensure_dir

logger = get_logger(__name__)


class NewsletterGenerator:
    """Newsletter 生成器"""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("./output/newsletters")
        ensure_dir(self.output_dir)

    def generate(
        self,
        analysis_result: Dict[str, Any],
        title: str,
        template: str = "default",
        include_sections: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        生成 Newsletter

        Args:
            analysis_result: 分析结果
            title: 标题
            template: 模板名称
            include_sections: 包含的部分

        Returns:
            {"html": html_content, "text": text_content, "subject": subject}
        """
        if include_sections is None:
            include_sections = ["summary", "keywords", "chapters", "quotes", "qa"]

        # 生成 HTML 版本
        html_content = self._generate_html(
            analysis_result,
            title,
            include_sections,
        )

        # 生成纯文本版本
        text_content = self._generate_text(
            analysis_result,
            title,
            include_sections,
        )

        # 生成主题
        subject = self._generate_subject(title, analysis_result)

        # 保存文件
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:50]
        html_path = self.output_dir / f"{safe_title}.html"
        text_path = self.output_dir / f"{safe_title}.txt"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_content)

        logger.info(f"Newsletter 生成完成: {html_path}")

        return {
            "html": html_content,
            "text": text_content,
            "subject": subject,
            "html_path": str(html_path),
            "text_path": str(text_path),
        }

    def _generate_subject(self, title: str, result: Dict[str, Any]) -> str:
        """生成邮件主题"""
        keywords = result.get("keywords", [])[:3]
        if keywords:
            tags = " | ".join(keywords)
            return f"🎙️ {title[:30]} - {tags}"
        return f"🎙️ 播客摘要: {title[:40]}"

    def _generate_html(
        self,
        result: Dict[str, Any],
        title: str,
        sections: List[str],
    ) -> str:
        """生成 HTML 内容"""
        date_str = datetime.now().strftime("%Y年%m月%d日")

        html_parts = [
            self._html_header(),
            self._html_hero(title, date_str),
        ]

        if "summary" in sections and result.get("summary"):
            html_parts.append(self._html_summary(result["summary"]))

        if "keywords" in sections and result.get("keywords"):
            html_parts.append(self._html_keywords(result["keywords"]))

        if "chapters" in sections and result.get("chapters"):
            html_parts.append(self._html_chapters(result["chapters"]))

        if "quotes" in sections and result.get("quotes"):
            html_parts.append(self._html_quotes(result["quotes"]))

        if "qa" in sections and result.get("qa_pairs"):
            html_parts.append(self._html_qa(result["qa_pairs"]))

        html_parts.append(self._html_footer())

        return "\n".join(html_parts)

    def _html_header(self) -> str:
        """HTML 头部"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>播客摘要 Newsletter</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .hero {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .hero h1 {
            margin: 0 0 10px 0;
            font-size: 28px;
        }
        .hero .date {
            opacity: 0.8;
            font-size: 14px;
        }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 30px;
        }
        .section-title {
            font-size: 20px;
            color: #6366f1;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }
        .summary {
            background-color: #f8fafc;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #6366f1;
        }
        .keywords {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .keyword {
            background-color: #eef2ff;
            color: #6366f1;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 14px;
        }
        .chapter {
            padding: 15px 0;
            border-bottom: 1px solid #e5e7eb;
        }
        .chapter:last-child {
            border-bottom: none;
        }
        .chapter-title {
            font-weight: 600;
            color: #1f2937;
        }
        .chapter-time {
            color: #6366f1;
            font-size: 14px;
        }
        .chapter-summary {
            margin-top: 8px;
            color: #6b7280;
            font-size: 14px;
        }
        .quote {
            background-color: #faf5ff;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #8b5cf6;
        }
        .quote-text {
            font-style: italic;
            font-size: 16px;
            color: #374151;
        }
        .quote-speaker {
            margin-top: 10px;
            color: #6b7280;
            font-size: 14px;
        }
        .qa {
            margin-bottom: 20px;
        }
        .qa-question {
            font-weight: 600;
            color: #6366f1;
            margin-bottom: 8px;
        }
        .qa-answer {
            color: #4b5563;
            padding-left: 15px;
            border-left: 2px solid #e5e7eb;
        }
        .footer {
            text-align: center;
            padding: 20px 30px;
            background-color: #f8fafc;
            color: #9ca3af;
            font-size: 12px;
        }
        .footer a {
            color: #6366f1;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
"""

    def _html_hero(self, title: str, date: str) -> str:
        """Hero 区域"""
        return f"""
        <div class="hero">
            <h1>🎙️ {html.escape(title)}</h1>
            <div class="date">{date}</div>
        </div>
        <div class="content">
"""

    def _html_summary(self, summary: str) -> str:
        """摘要区域"""
        return f"""
            <div class="section">
                <h2 class="section-title">📝 内容摘要</h2>
                <div class="summary">
                    {html.escape(summary).replace(chr(10), '<br>')}
                </div>
            </div>
"""

    def _html_keywords(self, keywords: List[str]) -> str:
        """关键词区域"""
        tags = "".join([
            f'<span class="keyword">{html.escape(kw)}</span>'
            for kw in keywords[:10]
        ])
        return f"""
            <div class="section">
                <h2 class="section-title">🏷️ 关键词</h2>
                <div class="keywords">
                    {tags}
                </div>
            </div>
"""

    def _html_chapters(self, chapters: List[Dict]) -> str:
        """章节区域"""
        items = []
        for chapter in chapters[:6]:
            title = html.escape(chapter.get("title", ""))
            time = self._format_timestamp(chapter.get("start_time", 0))
            summary = html.escape(chapter.get("summary", "")[:150])

            items.append(f"""
                <div class="chapter">
                    <div class="chapter-title">{title}</div>
                    <div class="chapter-time">{time}</div>
                    <div class="chapter-summary">{summary}</div>
                </div>
""")

        return f"""
            <div class="section">
                <h2 class="section-title">📑 章节导航</h2>
                {"".join(items)}
            </div>
"""

    def _html_quotes(self, quotes: List[Dict]) -> str:
        """金句区域"""
        items = []
        for quote in quotes[:5]:
            text = html.escape(quote.get("text", ""))
            speaker = html.escape(quote.get("speaker", ""))

            speaker_html = f'<div class="quote-speaker">— {speaker}</div>' if speaker else ""

            items.append(f"""
                <div class="quote">
                    <div class="quote-text">"{text}"</div>
                    {speaker_html}
                </div>
""")

        return f"""
            <div class="section">
                <h2 class="section-title">💬 精彩金句</h2>
                {"".join(items)}
            </div>
"""

    def _html_qa(self, qa_pairs: List[Dict]) -> str:
        """Q&A 区域"""
        items = []
        for qa in qa_pairs[:4]:
            question = html.escape(qa.get("question", ""))
            answer = html.escape(qa.get("answer", ""))

            items.append(f"""
                <div class="qa">
                    <div class="qa-question">Q: {question}</div>
                    <div class="qa-answer">{answer}</div>
                </div>
""")

        return f"""
            <div class="section">
                <h2 class="section-title">❓ 问答精选</h2>
                {"".join(items)}
            </div>
"""

    def _html_footer(self) -> str:
        """页脚"""
        return """
        </div>
        <div class="footer">
            <p>此邮件由 <strong>Podcast Summary Tool</strong> 自动生成</p>
            <p>如有问题，请回复此邮件</p>
        </div>
    </div>
</body>
</html>
"""

    def _generate_text(
        self,
        result: Dict[str, Any],
        title: str,
        sections: List[str],
    ) -> str:
        """生成纯文本内容"""
        lines = [
            "=" * 50,
            f"🎙️ {title}",
            f"📅 {datetime.now().strftime('%Y年%m月%d日')}",
            "=" * 50,
            "",
        ]

        if "summary" in sections and result.get("summary"):
            lines.extend([
                "📝 内容摘要",
                "-" * 30,
                result["summary"],
                "",
            ])

        if "keywords" in sections and result.get("keywords"):
            lines.extend([
                "🏷️ 关键词",
                "-" * 30,
                ", ".join(result["keywords"][:10]),
                "",
            ])

        if "chapters" in sections and result.get("chapters"):
            lines.extend([
                "📑 章节导航",
                "-" * 30,
            ])
            for chapter in result["chapters"][:6]:
                title_text = chapter.get("title", "")
                time = self._format_timestamp(chapter.get("start_time", 0))
                lines.append(f"[{time}] {title_text}")
                if chapter.get("summary"):
                    lines.append(f"    {chapter['summary'][:100]}")
            lines.append("")

        if "quotes" in sections and result.get("quotes"):
            lines.extend([
                "💬 精彩金句",
                "-" * 30,
            ])
            for quote in result["quotes"][:5]:
                lines.append(f'"{quote.get("text", "")}"')
                if quote.get("speaker"):
                    lines.append(f"    — {quote['speaker']}")
                lines.append("")

        if "qa" in sections and result.get("qa_pairs"):
            lines.extend([
                "❓ 问答精选",
                "-" * 30,
            ])
            for qa in result["qa_pairs"][:4]:
                lines.append(f"Q: {qa.get('question', '')}")
                lines.append(f"A: {qa.get('answer', '')}")
                lines.append("")

        lines.extend([
            "=" * 50,
            "此邮件由 Podcast Summary Tool 自动生成",
            "=" * 50,
        ])

        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def generate_digest(
        self,
        episodes: List[Dict[str, Any]],
        digest_title: str = "本周播客精选",
    ) -> Dict[str, str]:
        """
        生成多期播客的摘要合集

        Args:
            episodes: 多期播客的分析结果列表
            digest_title: 合集标题

        Returns:
            {"html": html_content, "text": text_content, "subject": subject}
        """
        date_str = datetime.now().strftime("%Y年%m月%d日")

        html_parts = [
            self._html_header(),
            f"""
        <div class="hero">
            <h1>📬 {html.escape(digest_title)}</h1>
            <div class="date">{date_str} | {len(episodes)} 期精选</div>
        </div>
        <div class="content">
""",
        ]

        for episode in episodes[:10]:
            title = episode.get("title", "")
            summary = episode.get("analysis", {}).get("summary", "")[:200]
            keywords = episode.get("analysis", {}).get("keywords", [])[:5]

            tags = "".join([
                f'<span class="keyword">{html.escape(kw)}</span>'
                for kw in keywords
            ])

            html_parts.append(f"""
            <div class="section" style="border-bottom: 1px solid #e5e7eb; padding-bottom: 20px;">
                <h3 style="color: #1f2937; margin-bottom: 10px;">🎙️ {html.escape(title)}</h3>
                <p style="color: #6b7280; font-size: 14px; margin-bottom: 10px;">{html.escape(summary)}...</p>
                <div class="keywords" style="margin-top: 10px;">{tags}</div>
            </div>
""")

        html_parts.append(self._html_footer())

        return {
            "html": "\n".join(html_parts),
            "text": self._generate_digest_text(episodes, digest_title),
            "subject": f"📬 {digest_title} - {len(episodes)}期精选内容",
        }

    def _generate_digest_text(
        self,
        episodes: List[Dict[str, Any]],
        digest_title: str,
    ) -> str:
        """生成合集纯文本版本"""
        lines = [
            "=" * 50,
            f"📬 {digest_title}",
            f"📅 {datetime.now().strftime('%Y年%m月%d日')} | {len(episodes)} 期精选",
            "=" * 50,
            "",
        ]

        for i, episode in enumerate(episodes[:10], 1):
            title = episode.get("title", "")
            summary = episode.get("analysis", {}).get("summary", "")[:200]
            keywords = episode.get("analysis", {}).get("keywords", [])[:5]

            lines.extend([
                f"{i}. 🎙️ {title}",
                "-" * 30,
                summary + "...",
                f"关键词: {', '.join(keywords)}",
                "",
            ])

        lines.extend([
            "=" * 50,
            "此邮件由 Podcast Summary Tool 自动生成",
        ])

        return "\n".join(lines)
