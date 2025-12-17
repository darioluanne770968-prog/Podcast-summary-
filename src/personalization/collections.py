"""
收藏管理模块

管理用户收藏的播客、金句、片段等
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Union
import json
from datetime import datetime
from enum import Enum

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


class CollectionItemType(str, Enum):
    """收藏项类型"""
    PODCAST = "podcast"
    QUOTE = "quote"
    CLIP = "clip"
    CHAPTER = "chapter"
    NOTE = "note"


@dataclass
class CollectionItem:
    """收藏项"""
    id: str
    type: CollectionItemType
    title: str
    content: str
    source_podcast: Optional[str] = None
    source_url: Optional[str] = None
    timestamp: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "content": self.content,
            "source_podcast": self.source_podcast,
            "source_url": self.source_url,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "notes": self.notes,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CollectionItem":
        data["type"] = CollectionItemType(data.get("type", "note"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Collection:
    """收藏夹"""
    id: str
    name: str
    description: str = ""
    items: List[CollectionItem] = field(default_factory=list)
    is_public: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_item(self, item: CollectionItem):
        """添加项目"""
        self.items.append(item)
        self.updated_at = datetime.now().isoformat()

    def remove_item(self, item_id: str) -> bool:
        """移除项目"""
        original_len = len(self.items)
        self.items = [i for i in self.items if i.id != item_id]
        if len(self.items) < original_len:
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def get_item(self, item_id: str) -> Optional[CollectionItem]:
        """获取项目"""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def search(
        self,
        query: str = None,
        item_type: CollectionItemType = None,
        tags: List[str] = None,
    ) -> List[CollectionItem]:
        """搜索项目"""
        results = []

        for item in self.items:
            if item_type and item.type != item_type:
                continue

            if tags and not any(tag in item.tags for tag in tags):
                continue

            if query:
                query_lower = query.lower()
                if (query_lower not in item.title.lower() and
                    query_lower not in item.content.lower()):
                    continue

            results.append(item)

        return results

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "items": [i.to_dict() for i in self.items],
            "is_public": self.is_public,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Collection":
        items = [CollectionItem.from_dict(i) for i in data.get("items", [])]
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            items=items,
            is_public=data.get("is_public", False),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class CollectionManager:
    """收藏夹管理器"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "collections"
        ensure_dir(self.storage_dir)
        self._collections: Dict[str, Collection] = {}
        self._load_collections()

    def _load_collections(self):
        """加载收藏夹"""
        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    collection = Collection.from_dict(data)
                    self._collections[collection.id] = collection
            except Exception as e:
                logger.error(f"加载收藏夹失败 [{file}]: {e}")

    def _save_collection(self, collection: Collection):
        """保存收藏夹"""
        file_path = self.storage_dir / f"{collection.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(collection.to_dict(), f, ensure_ascii=False, indent=2)

    def create_collection(
        self,
        name: str,
        description: str = "",
    ) -> Collection:
        """创建收藏夹"""
        import uuid
        collection_id = str(uuid.uuid4())[:8]

        collection = Collection(
            id=collection_id,
            name=name,
            description=description,
        )

        self._collections[collection_id] = collection
        self._save_collection(collection)
        logger.info(f"创建收藏夹: {name}")
        return collection

    def get_collection(self, collection_id: str) -> Optional[Collection]:
        """获取收藏夹"""
        return self._collections.get(collection_id)

    def list_collections(self) -> List[Collection]:
        """列出所有收藏夹"""
        return list(self._collections.values())

    def delete_collection(self, collection_id: str) -> bool:
        """删除收藏夹"""
        if collection_id not in self._collections:
            return False

        file_path = self.storage_dir / f"{collection_id}.json"
        if file_path.exists():
            file_path.unlink()

        del self._collections[collection_id]
        logger.info(f"删除收藏夹: {collection_id}")
        return True

    def add_to_collection(
        self,
        collection_id: str,
        item: CollectionItem,
    ) -> bool:
        """添加项目到收藏夹"""
        collection = self.get_collection(collection_id)
        if not collection:
            return False

        collection.add_item(item)
        self._save_collection(collection)
        return True

    def remove_from_collection(
        self,
        collection_id: str,
        item_id: str,
    ) -> bool:
        """从收藏夹移除项目"""
        collection = self.get_collection(collection_id)
        if not collection:
            return False

        if collection.remove_item(item_id):
            self._save_collection(collection)
            return True
        return False

    def quick_save_quote(
        self,
        quote_text: str,
        source_podcast: str,
        speaker: str = None,
        timestamp: float = None,
    ) -> CollectionItem:
        """快速保存金句"""
        import uuid

        # 确保有默认收藏夹
        default = self._get_or_create_default_collection()

        item = CollectionItem(
            id=str(uuid.uuid4())[:8],
            type=CollectionItemType.QUOTE,
            title=quote_text[:50] + "..." if len(quote_text) > 50 else quote_text,
            content=quote_text,
            source_podcast=source_podcast,
            timestamp=timestamp,
            metadata={"speaker": speaker} if speaker else {},
        )

        self.add_to_collection(default.id, item)
        return item

    def _get_or_create_default_collection(self) -> Collection:
        """获取或创建默认收藏夹"""
        for collection in self._collections.values():
            if collection.name == "默认收藏":
                return collection

        return self.create_collection("默认收藏", "自动创建的默认收藏夹")

    def export_collection(
        self,
        collection_id: str,
        format: str = "markdown",
    ) -> str:
        """导出收藏夹"""
        collection = self.get_collection(collection_id)
        if not collection:
            return ""

        if format == "markdown":
            return self._export_markdown(collection)
        elif format == "json":
            return json.dumps(collection.to_dict(), ensure_ascii=False, indent=2)
        else:
            return ""

    def _export_markdown(self, collection: Collection) -> str:
        """导出为 Markdown"""
        lines = [f"# 📚 {collection.name}\n"]

        if collection.description:
            lines.append(f"*{collection.description}*\n")

        # 按类型分组
        by_type = {}
        for item in collection.items:
            if item.type not in by_type:
                by_type[item.type] = []
            by_type[item.type].append(item)

        type_titles = {
            CollectionItemType.PODCAST: "🎙️ 播客",
            CollectionItemType.QUOTE: "💬 金句",
            CollectionItemType.CLIP: "🎬 片段",
            CollectionItemType.CHAPTER: "📑 章节",
            CollectionItemType.NOTE: "📝 笔记",
        }

        for item_type, items in by_type.items():
            lines.append(f"\n## {type_titles.get(item_type, '其他')}\n")

            for item in items:
                lines.append(f"### {item.title}\n")
                lines.append(item.content)

                if item.source_podcast:
                    lines.append(f"\n*来源: {item.source_podcast}*")

                if item.notes:
                    lines.append(f"\n> 笔记: {item.notes}")

                lines.append("")

        return "\n".join(lines)
