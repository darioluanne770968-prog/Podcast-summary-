"""
知识库管理模块

管理播客内容知识库
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import uuid

from .semantic_search import SemanticSearch, SearchResult
from .vector_store import VectorStore, VectorDocument
from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: str
    title: str
    content: str
    entry_type: str = "general"  # general, quote, fact, concept, insight
    source_podcast: Optional[str] = None
    source_episode: Optional[str] = None
    timestamp: Optional[float] = None
    speakers: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    related_entries: List[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "entry_type": self.entry_type,
            "source_podcast": self.source_podcast,
            "source_episode": self.source_episode,
            "timestamp": self.timestamp,
            "speakers": self.speakers,
            "topics": self.topics,
            "tags": self.tags,
            "related_entries": self.related_entries,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class KnowledgeBase:
    """知识库"""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        embedding_provider: str = "openai",
    ):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "knowledge"
        ensure_dir(self.storage_dir)

        self._entries: Dict[str, KnowledgeEntry] = {}
        self._search_engine = SemanticSearch(
            storage_dir=self.storage_dir / "search",
            embedding_provider=embedding_provider,
        )
        self._load_entries()

    def _load_entries(self):
        """加载知识条目"""
        entries_file = self.storage_dir / "entries.json"
        if entries_file.exists():
            try:
                with open(entries_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for entry_data in data:
                        entry = KnowledgeEntry.from_dict(entry_data)
                        self._entries[entry.id] = entry
            except Exception as e:
                logger.error(f"加载知识库失败: {e}")

    def _save_entries(self):
        """保存知识条目"""
        entries_file = self.storage_dir / "entries.json"
        try:
            data = [entry.to_dict() for entry in self._entries.values()]
            with open(entries_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存知识库失败: {e}")

    def add_entry(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """添加知识条目"""
        if not entry.id:
            entry.id = str(uuid.uuid4())[:8]

        self._entries[entry.id] = entry
        self._save_entries()

        # 添加到搜索索引
        self._search_engine.add_document(
            doc_id=entry.id,
            title=entry.title,
            content=entry.content,
            metadata={
                "type": entry.entry_type,
                "podcast": entry.source_podcast,
                "topics": entry.topics,
                "tags": entry.tags,
            },
        )

        logger.info(f"添加知识条目: {entry.title}")
        return entry

    def add_entries(self, entries: List[KnowledgeEntry]):
        """批量添加知识条目"""
        for entry in entries:
            if not entry.id:
                entry.id = str(uuid.uuid4())[:8]
            self._entries[entry.id] = entry

        self._save_entries()

        # 批量添加到搜索索引
        docs = [
            {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "metadata": {
                    "type": entry.entry_type,
                    "podcast": entry.source_podcast,
                    "topics": entry.topics,
                    "tags": entry.tags,
                },
            }
            for entry in entries
        ]
        self._search_engine.add_documents(docs)
        logger.info(f"批量添加 {len(entries)} 个知识条目")

    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """获取知识条目"""
        return self._entries.get(entry_id)

    def update_entry(self, entry: KnowledgeEntry):
        """更新知识条目"""
        entry.updated_at = datetime.now().isoformat()
        self._entries[entry.id] = entry
        self._save_entries()

        # 更新搜索索引
        self._search_engine.remove_document(entry.id)
        self._search_engine.add_document(
            doc_id=entry.id,
            title=entry.title,
            content=entry.content,
            metadata={
                "type": entry.entry_type,
                "podcast": entry.source_podcast,
                "topics": entry.topics,
                "tags": entry.tags,
            },
        )

    def delete_entry(self, entry_id: str) -> bool:
        """删除知识条目"""
        if entry_id in self._entries:
            del self._entries[entry_id]
            self._save_entries()
            self._search_engine.remove_document(entry_id)
            return True
        return False

    def search(
        self,
        query: str,
        top_k: int = 10,
        entry_type: Optional[str] = None,
        topics: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[KnowledgeEntry]:
        """搜索知识库"""
        filters = {}
        if entry_type:
            filters["type"] = entry_type

        results = self._search_engine.search(query, top_k=top_k * 2, filters=filters)

        entries = []
        for result in results:
            entry = self._entries.get(result.id)
            if not entry:
                continue

            # 话题过滤
            if topics and not any(t in entry.topics for t in topics):
                continue

            # 标签过滤
            if tags and not any(t in entry.tags for t in tags):
                continue

            entries.append(entry)
            if len(entries) >= top_k:
                break

        return entries

    def find_related(
        self,
        entry_id: str,
        top_k: int = 5,
    ) -> List[KnowledgeEntry]:
        """查找相关条目"""
        similar_results = self._search_engine.find_similar(entry_id, top_k=top_k)
        entries = []
        for result in similar_results:
            entry = self._entries.get(result.id)
            if entry:
                entries.append(entry)
        return entries

    def get_by_podcast(self, podcast_name: str) -> List[KnowledgeEntry]:
        """按播客获取条目"""
        return [
            entry for entry in self._entries.values()
            if entry.source_podcast == podcast_name
        ]

    def get_by_topic(self, topic: str) -> List[KnowledgeEntry]:
        """按话题获取条目"""
        return [
            entry for entry in self._entries.values()
            if topic in entry.topics
        ]

    def get_by_type(self, entry_type: str) -> List[KnowledgeEntry]:
        """按类型获取条目"""
        return [
            entry for entry in self._entries.values()
            if entry.entry_type == entry_type
        ]

    def extract_from_analysis(
        self,
        analysis_result: Dict[str, Any],
        podcast_name: str,
        episode_title: str,
    ) -> List[KnowledgeEntry]:
        """从分析结果中提取知识"""
        entries = []

        # 提取摘要作为概述
        if "summary" in analysis_result:
            entries.append(KnowledgeEntry(
                id=str(uuid.uuid4())[:8],
                title=f"{episode_title} - 概述",
                content=analysis_result["summary"],
                entry_type="general",
                source_podcast=podcast_name,
                source_episode=episode_title,
                topics=analysis_result.get("keywords", []),
            ))

        # 提取章节
        for chapter in analysis_result.get("chapters", []):
            entries.append(KnowledgeEntry(
                id=str(uuid.uuid4())[:8],
                title=chapter.get("title", ""),
                content=chapter.get("summary", ""),
                entry_type="concept",
                source_podcast=podcast_name,
                source_episode=episode_title,
                timestamp=chapter.get("start_time"),
            ))

        # 提取金句
        for quote in analysis_result.get("quotes", []):
            entries.append(KnowledgeEntry(
                id=str(uuid.uuid4())[:8],
                title=quote.get("text", "")[:50],
                content=quote.get("text", ""),
                entry_type="quote",
                source_podcast=podcast_name,
                source_episode=episode_title,
                speakers=[quote.get("speaker")] if quote.get("speaker") else [],
                timestamp=quote.get("timestamp"),
            ))

        # 提取关键见解
        for insight in analysis_result.get("insights", []):
            entries.append(KnowledgeEntry(
                id=str(uuid.uuid4())[:8],
                title=insight.get("title", ""),
                content=insight.get("content", ""),
                entry_type="insight",
                source_podcast=podcast_name,
                source_episode=episode_title,
            ))

        return entries

    def build_topic_graph(self) -> Dict[str, List[str]]:
        """构建话题关系图"""
        topic_entries: Dict[str, List[str]] = {}

        for entry in self._entries.values():
            for topic in entry.topics:
                if topic not in topic_entries:
                    topic_entries[topic] = []
                topic_entries[topic].append(entry.id)

        # 计算话题关联
        topic_relations: Dict[str, List[str]] = {}
        topics = list(topic_entries.keys())

        for i, topic1 in enumerate(topics):
            related = []
            for j, topic2 in enumerate(topics):
                if i == j:
                    continue
                # 计算共现次数
                entries1 = set(topic_entries[topic1])
                entries2 = set(topic_entries[topic2])
                overlap = len(entries1 & entries2)
                if overlap > 0:
                    related.append(topic2)
            topic_relations[topic1] = related

        return topic_relations

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        type_counts = {}
        topic_counts = {}
        podcast_counts = {}

        for entry in self._entries.values():
            # 类型统计
            type_counts[entry.entry_type] = type_counts.get(entry.entry_type, 0) + 1

            # 话题统计
            for topic in entry.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

            # 播客统计
            if entry.source_podcast:
                podcast_counts[entry.source_podcast] = podcast_counts.get(entry.source_podcast, 0) + 1

        return {
            "total_entries": len(self._entries),
            "entries_by_type": type_counts,
            "top_topics": sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:20],
            "podcasts_indexed": len(podcast_counts),
            "entries_by_podcast": podcast_counts,
        }

    def export_markdown(self, output_path: Optional[Path] = None) -> str:
        """导出为 Markdown"""
        lines = ["# 播客知识库\n"]

        # 按类型分组
        by_type: Dict[str, List[KnowledgeEntry]] = {}
        for entry in self._entries.values():
            if entry.entry_type not in by_type:
                by_type[entry.entry_type] = []
            by_type[entry.entry_type].append(entry)

        type_names = {
            "general": "📝 概述",
            "quote": "💬 金句",
            "fact": "📊 事实",
            "concept": "💡 概念",
            "insight": "🔍 见解",
        }

        for entry_type, entries in by_type.items():
            lines.append(f"\n## {type_names.get(entry_type, entry_type)}\n")

            for entry in sorted(entries, key=lambda e: e.created_at, reverse=True):
                lines.append(f"### {entry.title}\n")
                lines.append(entry.content)

                if entry.source_podcast:
                    lines.append(f"\n*来源: {entry.source_podcast}*")
                    if entry.source_episode:
                        lines.append(f" - {entry.source_episode}")

                if entry.topics:
                    lines.append(f"\n**话题**: {', '.join(entry.topics)}")

                lines.append("\n---\n")

        content = "\n".join(lines)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"知识库已导出: {output_path}")

        return content

    def ask(
        self,
        question: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """基于知识库回答问题"""
        # 搜索相关知识
        relevant_entries = self.search(question, top_k=top_k)

        if not relevant_entries:
            return {
                "answer": "抱歉，知识库中没有找到相关信息。",
                "sources": [],
            }

        # 构建上下文
        context_parts = []
        sources = []
        for entry in relevant_entries:
            context_parts.append(f"【{entry.title}】\n{entry.content}")
            sources.append({
                "title": entry.title,
                "podcast": entry.source_podcast,
                "episode": entry.source_episode,
            })

        context = "\n\n".join(context_parts)

        # 返回搜索结果（实际回答生成可以调用 LLM）
        return {
            "context": context,
            "sources": sources,
            "entries": relevant_entries,
        }
