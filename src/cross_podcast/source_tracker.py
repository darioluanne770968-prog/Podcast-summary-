"""
信息溯源模块

追踪一个观点最早出自哪期播客
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import uuid

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class SourceOrigin:
    """信息源头"""
    id: str
    content: str  # 观点/信息内容
    content_hash: str  # 内容哈希，用于匹配
    first_appearance: Dict  # 首次出现
    all_appearances: List[Dict] = field(default_factory=list)
    variations: List[str] = field(default_factory=list)  # 变体表述
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "content_hash": self.content_hash,
            "first_appearance": self.first_appearance,
            "all_appearances": self.all_appearances,
            "variations": self.variations,
            "tags": self.tags,
            "spread_count": len(self.all_appearances),
            "created_at": self.created_at,
        }


class SourceTracker:
    """
    信息溯源器

    功能：
    - 追踪观点的最早出处
    - 记录观点的传播路径
    - 发现信息变异
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "source_tracker"
        ensure_dir(self.storage_dir)
        self._origins: Dict[str, SourceOrigin] = {}
        self._content_index: Dict[str, str] = {}  # content_hash -> origin_id
        self._load_data()

    def _load_data(self):
        """加载数据"""
        data_file = self.storage_dir / "origins.json"
        if data_file.exists():
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for origin_data in data:
                        origin = SourceOrigin(
                            id=origin_data["id"],
                            content=origin_data["content"],
                            content_hash=origin_data["content_hash"],
                            first_appearance=origin_data["first_appearance"],
                            all_appearances=origin_data.get("all_appearances", []),
                            variations=origin_data.get("variations", []),
                            tags=origin_data.get("tags", []),
                        )
                        self._origins[origin.id] = origin
                        self._content_index[origin.content_hash] = origin.id
            except Exception as e:
                logger.error(f"加载溯源数据失败: {e}")

    def _save_data(self):
        """保存数据"""
        data_file = self.storage_dir / "origins.json"
        try:
            data = [o.to_dict() for o in self._origins.values()]
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存溯源数据失败: {e}")

    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        import hashlib
        # 简化内容后计算哈希
        simplified = content.lower().strip()
        return hashlib.md5(simplified.encode()).hexdigest()[:16]

    async def _compute_semantic_hash(
        self,
        content: str,
        llm_provider: str = "openai",
    ) -> str:
        """计算语义哈希（用于匹配相似表述）"""
        # 使用 LLM 提取核心观点
        try:
            if llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "提取以下内容的核心观点，用一句话概括。只输出概括。"},
                        {"role": "user", "content": content},
                    ],
                    max_tokens=100,
                )
                core_content = response.choices[0].message.content
                return self._compute_hash(core_content)
        except:
            pass
        return self._compute_hash(content)

    def record_appearance(
        self,
        content: str,
        podcast_name: str,
        episode_title: str,
        speaker: str,
        date: str,
        timestamp: Optional[float] = None,
    ) -> SourceOrigin:
        """
        记录信息出现

        Args:
            content: 信息内容
            podcast_name: 播客名称
            episode_title: 节目标题
            speaker: 说话人
            date: 日期
            timestamp: 时间戳

        Returns:
            信息源头
        """
        content_hash = self._compute_hash(content)

        appearance = {
            "podcast": podcast_name,
            "episode": episode_title,
            "speaker": speaker,
            "date": date,
            "timestamp": timestamp,
        }

        # 检查是否已存在
        if content_hash in self._content_index:
            origin_id = self._content_index[content_hash]
            origin = self._origins[origin_id]

            # 检查是否更早
            if date < origin.first_appearance.get("date", ""):
                origin.all_appearances.insert(0, origin.first_appearance)
                origin.first_appearance = appearance
            else:
                origin.all_appearances.append(appearance)

            self._save_data()
            return origin

        # 创建新记录
        origin = SourceOrigin(
            id=str(uuid.uuid4())[:8],
            content=content,
            content_hash=content_hash,
            first_appearance=appearance,
            all_appearances=[],
        )

        self._origins[origin.id] = origin
        self._content_index[content_hash] = origin.id
        self._save_data()

        logger.info(f"记录新信息源: {content[:50]}...")
        return origin

    async def find_similar(
        self,
        content: str,
        threshold: float = 0.7,
    ) -> List[SourceOrigin]:
        """
        查找相似信息

        Args:
            content: 内容
            threshold: 相似度阈值

        Returns:
            相似的信息源列表
        """
        results = []

        # 精确匹配
        content_hash = self._compute_hash(content)
        if content_hash in self._content_index:
            origin_id = self._content_index[content_hash]
            results.append(self._origins[origin_id])

        # 模糊匹配（使用简单的词重叠）
        content_words = set(content.lower().split())

        for origin in self._origins.values():
            if origin.id in [r.id for r in results]:
                continue

            origin_words = set(origin.content.lower().split())
            if not origin_words:
                continue

            overlap = len(content_words & origin_words)
            similarity = overlap / max(len(content_words), len(origin_words))

            if similarity >= threshold:
                results.append(origin)

        return results

    def trace_origin(self, content: str) -> Optional[Dict]:
        """
        追溯信息源头

        Args:
            content: 内容

        Returns:
            源头信息
        """
        content_hash = self._compute_hash(content)

        if content_hash in self._content_index:
            origin_id = self._content_index[content_hash]
            origin = self._origins[origin_id]

            return {
                "found": True,
                "origin": origin.to_dict(),
                "first_appearance": origin.first_appearance,
                "spread_path": [origin.first_appearance] + origin.all_appearances,
                "spread_count": len(origin.all_appearances) + 1,
            }

        return {
            "found": False,
            "content": content,
            "message": "未找到该信息的历史记录",
        }

    def get_spread_timeline(self, origin_id: str) -> List[Dict]:
        """
        获取传播时间线

        Args:
            origin_id: 源头 ID

        Returns:
            时间线
        """
        origin = self._origins.get(origin_id)
        if not origin:
            return []

        timeline = [origin.first_appearance] + origin.all_appearances
        timeline.sort(key=lambda x: x.get("date", ""))

        return timeline

    def analyze_spread_pattern(self, origin_id: str) -> Dict[str, Any]:
        """
        分析传播模式

        Args:
            origin_id: 源头 ID

        Returns:
            传播分析
        """
        origin = self._origins.get(origin_id)
        if not origin:
            return {}

        all_appearances = [origin.first_appearance] + origin.all_appearances

        # 统计
        podcasts = list(set(a.get("podcast", "") for a in all_appearances))
        speakers = list(set(a.get("speaker", "") for a in all_appearances))

        dates = [a.get("date", "") for a in all_appearances if a.get("date")]
        if dates:
            dates.sort()
            first_date = dates[0]
            last_date = dates[-1]
        else:
            first_date = last_date = ""

        return {
            "origin_id": origin_id,
            "content": origin.content,
            "total_appearances": len(all_appearances),
            "unique_podcasts": len(podcasts),
            "unique_speakers": len(speakers),
            "podcasts": podcasts,
            "speakers": speakers,
            "first_date": first_date,
            "last_date": last_date,
            "timeline": self.get_spread_timeline(origin_id),
        }

    def add_variation(self, origin_id: str, variation: str):
        """添加变体表述"""
        origin = self._origins.get(origin_id)
        if origin and variation not in origin.variations:
            origin.variations.append(variation)
            self._save_data()

    def get_most_cited(self, limit: int = 20) -> List[SourceOrigin]:
        """获取被引用最多的信息"""
        origins = list(self._origins.values())
        origins.sort(key=lambda o: len(o.all_appearances) + 1, reverse=True)
        return origins[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_appearances = sum(
            len(o.all_appearances) + 1
            for o in self._origins.values()
        )

        return {
            "total_origins": len(self._origins),
            "total_appearances": total_appearances,
            "avg_spread": total_appearances / len(self._origins) if self._origins else 0,
            "most_spread": [
                {"content": o.content[:50], "count": len(o.all_appearances) + 1}
                for o in self.get_most_cited(5)
            ],
        }
