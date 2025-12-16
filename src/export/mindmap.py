"""
思维导图生成模块
"""

from pathlib import Path
from typing import Optional, List

from .markdown import PodcastAnalysisResult
from ..utils import get_logger, ensure_dir, sanitize_filename

logger = get_logger(__name__)


class MindmapGenerator:
    """思维导图生成器"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        初始化生成器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or Path("./output")
        ensure_dir(self.output_dir)

    def generate_mermaid(
        self,
        result: PodcastAnalysisResult,
        filename: Optional[str] = None,
    ) -> Path:
        """
        生成 Mermaid 格式的思维导图

        Args:
            result: 分析结果
            filename: 文件名

        Returns:
            输出文件路径
        """
        logger.info("生成思维导图 (Mermaid)...")

        if not filename:
            filename = sanitize_filename(result.title or "mindmap")

        output_path = self.output_dir / f"{filename}_mindmap.md"

        content = self._build_mermaid_content(result)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"思维导图生成完成: {output_path}")
        return output_path

    def _build_mermaid_content(self, result: PodcastAnalysisResult) -> str:
        """构建 Mermaid 内容"""
        title = result.title or "Podcast"
        # 清理标题中的特殊字符
        title = title.replace('"', "'").replace("[", "(").replace("]", ")")

        lines = [
            f"# {title} - 思维导图\n",
            "```mermaid",
            "mindmap",
            f'  root(("{title}"))',
        ]

        # 添加摘要分支
        if result.summary:
            lines.append("    summary[📝 内容摘要]")
            if hasattr(result.summary, "key_points") and result.summary.key_points:
                for i, point in enumerate(result.summary.key_points[:5], 1):
                    # 清理文本
                    point = point[:30].replace('"', "'").replace("[", "(").replace("]", ")")
                    lines.append(f"      point{i}[{point}...]")

        # 添加章节分支
        if result.chapters:
            lines.append("    chapters[📑 章节]")
            for i, chapter in enumerate(result.chapters[:8], 1):
                if hasattr(chapter, "title"):
                    title = chapter.title
                else:
                    title = chapter.get("title", f"章节{i}")
                title = title[:20].replace('"', "'").replace("[", "(").replace("]", ")")
                lines.append(f"      ch{i}[{title}]")

        # 添加关键词分支
        if result.keywords:
            lines.append("    keywords[🏷️ 关键词]")
            for i, kw in enumerate(result.keywords[:8], 1):
                if hasattr(kw, "word"):
                    word = kw.word
                elif isinstance(kw, str):
                    word = kw
                else:
                    word = kw.get("word", "")
                word = word.replace('"', "'").replace("[", "(").replace("]", ")")
                lines.append(f"      kw{i}[{word}]")

        # 添加金句分支
        if result.quotes:
            lines.append("    quotes[💬 金句]")
            for i, quote in enumerate(result.quotes[:5], 1):
                if hasattr(quote, "text"):
                    text = quote.text
                else:
                    text = quote.get("text", "")
                text = text[:25].replace('"', "'").replace("[", "(").replace("]", ")")
                lines.append(f'      q{i}["{text}..."]')

        lines.append("```\n")

        # 添加使用说明
        lines.extend([
            "## 查看方式\n",
            "1. **VS Code**: 安装 Mermaid 插件",
            "2. **GitHub/GitLab**: 直接渲染",
            "3. **在线工具**: [Mermaid Live Editor](https://mermaid.live/)",
        ])

        return "\n".join(lines)

    def generate_markmap(
        self,
        result: PodcastAnalysisResult,
        filename: Optional[str] = None,
    ) -> Path:
        """
        生成 Markmap 格式的思维导图（纯 Markdown 大纲）

        Args:
            result: 分析结果
            filename: 文件名

        Returns:
            输出文件路径
        """
        logger.info("生成思维导图 (Markmap)...")

        if not filename:
            filename = sanitize_filename(result.title or "mindmap")

        output_path = self.output_dir / f"{filename}_markmap.md"

        content = self._build_markmap_content(result)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Markmap 生成完成: {output_path}")
        return output_path

    def _build_markmap_content(self, result: PodcastAnalysisResult) -> str:
        """构建 Markmap 内容（Markdown 大纲格式）"""
        title = result.title or "Podcast"

        lines = [
            f"# {title}\n",
        ]

        # 内容摘要
        if result.summary:
            lines.append("## 📝 内容摘要")
            if hasattr(result.summary, "brief") and result.summary.brief:
                lines.append(f"### 概述")
                lines.append(f"- {result.summary.brief}")

            if hasattr(result.summary, "key_points") and result.summary.key_points:
                lines.append("### 核心要点")
                for point in result.summary.key_points:
                    lines.append(f"- {point}")

            if hasattr(result.summary, "takeaways") and result.summary.takeaways:
                lines.append("### 收获启发")
                for takeaway in result.summary.takeaways:
                    lines.append(f"- {takeaway}")

        # 章节
        if result.chapters:
            lines.append("\n## 📑 章节目录")
            for chapter in result.chapters:
                if hasattr(chapter, "title"):
                    title = chapter.title
                    time = chapter.start_formatted
                else:
                    title = chapter.get("title", "")
                    time = chapter.get("start_formatted", "")
                lines.append(f"### [{time}] {title}")

        # 关键词
        if result.keywords:
            lines.append("\n## 🏷️ 关键词")
            # 按分类分组
            categories = {}
            for kw in result.keywords:
                if hasattr(kw, "category"):
                    cat = kw.category
                    word = kw.word
                else:
                    cat = kw.get("category", "其他")
                    word = kw.get("word", "")

                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(word)

            for cat, words in categories.items():
                lines.append(f"### {cat}")
                for word in words:
                    lines.append(f"- {word}")

        # 金句
        if result.quotes:
            lines.append("\n## 💬 金句摘录")
            for quote in result.quotes:
                if hasattr(quote, "text"):
                    text = quote.text
                    speaker = getattr(quote, "speaker", "")
                else:
                    text = quote.get("text", "")
                    speaker = quote.get("speaker", "")

                speaker_part = f" ({speaker})" if speaker else ""
                lines.append(f"- {text}{speaker_part}")

        lines.extend([
            "\n---",
            "*使用 [Markmap](https://markmap.js.org/) 查看交互式思维导图*",
        ])

        return "\n".join(lines)
