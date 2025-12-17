"""
Obsidian 导出模块

生成适合 Obsidian 的笔记格式，支持双向链接和标签
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

from ...utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class ObsidianConfig:
    """Obsidian 导出配置"""
    vault_path: Path
    folder: str = "Podcasts"
    template: str = "default"
    use_daily_notes: bool = False
    daily_notes_folder: str = "Daily Notes"
    use_dataview: bool = True
    use_tags: bool = True
    tag_prefix: str = "#"
    link_style: str = "wikilink"  # wikilink or markdown
    frontmatter: bool = True


class ObsidianExporter:
    """Obsidian 导出器"""

    def __init__(self, config: Optional[ObsidianConfig] = None):
        self.config = config or ObsidianConfig(
            vault_path=Path.home() / "Obsidian" / "PodcastNotes"
        )
        ensure_dir(self.config.vault_path / self.config.folder)

    def export(
        self,
        analysis_result: Dict[str, Any],
        podcast_name: str,
        episode_title: str,
    ) -> Path:
        """导出分析结果到 Obsidian"""
        # 清理文件名
        safe_title = self._sanitize_filename(episode_title)
        note_path = self.config.vault_path / self.config.folder / f"{safe_title}.md"

        content = self._generate_note(
            analysis_result,
            podcast_name,
            episode_title,
        )

        with open(note_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"导出 Obsidian 笔记: {note_path}")

        # 更新索引
        self._update_index(podcast_name, episode_title, note_path)

        return note_path

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名"""
        # 移除不允许的字符
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # 限制长度
        return name[:100]

    def _generate_note(
        self,
        result: Dict[str, Any],
        podcast_name: str,
        episode_title: str,
    ) -> str:
        """生成笔记内容"""
        lines = []

        # YAML Frontmatter
        if self.config.frontmatter:
            lines.extend(self._generate_frontmatter(result, podcast_name, episode_title))

        # 标题
        lines.append(f"# {episode_title}\n")

        # 元信息
        lines.append(f"**播客**: {self._make_link(podcast_name)}")
        lines.append(f"**日期**: {datetime.now().strftime('%Y-%m-%d')}")

        if result.get("duration"):
            lines.append(f"**时长**: {result['duration']}")

        lines.append("")

        # 摘要
        if result.get("summary"):
            lines.append("## 📝 摘要\n")
            lines.append(result["summary"])
            lines.append("")

        # 关键词/标签
        if result.get("keywords"):
            keywords = result["keywords"]
            if self.config.use_tags:
                tags = " ".join([f"{self.config.tag_prefix}{kw}" for kw in keywords])
                lines.append(f"**关键词**: {tags}\n")
            else:
                links = " ".join([self._make_link(kw) for kw in keywords])
                lines.append(f"**关键词**: {links}\n")

        # 章节
        if result.get("chapters"):
            lines.append("## 📑 章节\n")
            for chapter in result["chapters"]:
                title = chapter.get("title", "")
                timestamp = chapter.get("start_time", "")
                summary = chapter.get("summary", "")

                if timestamp:
                    lines.append(f"### {self._format_timestamp(timestamp)} {title}\n")
                else:
                    lines.append(f"### {title}\n")

                if summary:
                    lines.append(summary)
                    lines.append("")

        # 金句
        if result.get("quotes"):
            lines.append("## 💬 金句\n")
            for quote in result["quotes"]:
                text = quote.get("text", "")
                speaker = quote.get("speaker", "")
                timestamp = quote.get("timestamp", "")

                lines.append(f"> {text}")
                if speaker:
                    lines.append(f"> — {self._make_link(speaker)}")
                if timestamp:
                    lines.append(f"> _{self._format_timestamp(timestamp)}_")
                lines.append("")

        # Q&A
        if result.get("qa_pairs"):
            lines.append("## ❓ 问答\n")
            for qa in result["qa_pairs"]:
                lines.append(f"**Q: {qa.get('question', '')}**\n")
                lines.append(f"A: {qa.get('answer', '')}\n")

        # 实体
        if result.get("entities"):
            lines.append("## 🏷️ 提及\n")
            entities_by_type: Dict[str, List[str]] = {}
            for entity in result["entities"]:
                etype = entity.get("type", "other")
                name = entity.get("name", "")
                if etype not in entities_by_type:
                    entities_by_type[etype] = []
                if name not in entities_by_type[etype]:
                    entities_by_type[etype].append(name)

            type_names = {
                "person": "👤 人物",
                "organization": "🏢 组织",
                "location": "📍 地点",
                "product": "📦 产品",
                "book": "📚 书籍",
            }

            for etype, names in entities_by_type.items():
                type_label = type_names.get(etype, etype)
                links = ", ".join([self._make_link(n) for n in names])
                lines.append(f"- {type_label}: {links}")
            lines.append("")

        # Dataview 查询块
        if self.config.use_dataview:
            lines.extend(self._generate_dataview_block(podcast_name))

        # 相关笔记
        lines.append("## 🔗 相关\n")
        lines.append(f"- {self._make_link(podcast_name)}")
        if result.get("keywords"):
            for kw in result["keywords"][:5]:
                lines.append(f"- {self._make_link(kw)}")

        return "\n".join(lines)

    def _generate_frontmatter(
        self,
        result: Dict[str, Any],
        podcast_name: str,
        episode_title: str,
    ) -> List[str]:
        """生成 YAML frontmatter"""
        lines = ["---"]
        lines.append(f"title: \"{episode_title}\"")
        lines.append(f"podcast: \"{podcast_name}\"")
        lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("type: podcast-note")

        if result.get("keywords"):
            tags = [f"\"{kw}\"" for kw in result["keywords"]]
            lines.append(f"tags: [{', '.join(tags)}]")

        if result.get("duration"):
            lines.append(f"duration: \"{result['duration']}\"")

        if result.get("speakers"):
            speakers = [f"\"{s}\"" for s in result["speakers"]]
            lines.append(f"speakers: [{', '.join(speakers)}]")

        lines.append("---\n")
        return lines

    def _make_link(self, text: str) -> str:
        """生成链接"""
        if self.config.link_style == "wikilink":
            return f"[[{text}]]"
        else:
            return f"[{text}]({text.replace(' ', '%20')}.md)"

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _generate_dataview_block(self, podcast_name: str) -> List[str]:
        """生成 Dataview 查询块"""
        lines = [
            "\n## 📊 统计\n",
            "```dataview",
            "TABLE date, duration",
            f"FROM \"{self.config.folder}\"",
            f"WHERE podcast = \"{podcast_name}\"",
            "SORT date DESC",
            "LIMIT 10",
            "```\n",
        ]
        return lines

    def _update_index(
        self,
        podcast_name: str,
        episode_title: str,
        note_path: Path,
    ):
        """更新播客索引页"""
        index_path = self.config.vault_path / self.config.folder / f"{self._sanitize_filename(podcast_name)}.md"

        # 读取或创建索引
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = f"""---
type: podcast-index
podcast: "{podcast_name}"
---

# {podcast_name}

## 节目列表

"""

        # 添加新节目链接
        link = self._make_link(episode_title)
        date = datetime.now().strftime("%Y-%m-%d")
        new_entry = f"- {date} {link}\n"

        if new_entry not in content:
            # 在节目列表后添加
            if "## 节目列表" in content:
                parts = content.split("## 节目列表")
                content = parts[0] + "## 节目列表\n\n" + new_entry + parts[1].lstrip("\n")
            else:
                content += f"\n## 节目列表\n\n{new_entry}"

            with open(index_path, "w", encoding="utf-8") as f:
                f.write(content)

    def export_batch(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Path]:
        """批量导出"""
        paths = []
        for result in results:
            try:
                path = self.export(
                    result.get("analysis", {}),
                    result.get("podcast_name", "Unknown"),
                    result.get("episode_title", "Untitled"),
                )
                paths.append(path)
            except Exception as e:
                logger.error(f"导出失败: {e}")
        return paths

    def create_moc(self) -> Path:
        """创建 Map of Content 页面"""
        moc_path = self.config.vault_path / self.config.folder / "MOC.md"

        lines = [
            "---",
            "type: moc",
            "---",
            "",
            "# 🎙️ 播客笔记 MOC\n",
            "## 按播客\n",
        ]

        # 扫描所有索引页
        folder = self.config.vault_path / self.config.folder
        for file in folder.glob("*.md"):
            if file.name in ["MOC.md"]:
                continue

            # 检查是否是索引页
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
                if "type: podcast-index" in content:
                    name = file.stem
                    lines.append(f"- {self._make_link(name)}")

        lines.append("\n## 最近笔记\n")
        lines.append("```dataview")
        lines.append("TABLE podcast, date")
        lines.append(f"FROM \"{self.config.folder}\"")
        lines.append("WHERE type = \"podcast-note\"")
        lines.append("SORT date DESC")
        lines.append("LIMIT 20")
        lines.append("```")

        lines.append("\n## 标签云\n")
        lines.append("```dataview")
        lines.append("TABLE length(rows) as Count")
        lines.append(f"FROM \"{self.config.folder}\"")
        lines.append("FLATTEN tags")
        lines.append("GROUP BY tags")
        lines.append("SORT Count DESC")
        lines.append("LIMIT 30")
        lines.append("```")

        with open(moc_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"创建 MOC: {moc_path}")
        return moc_path
