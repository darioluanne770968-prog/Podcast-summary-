"""
专家网络模块

构建嘉宾关系图，发现隐藏联系
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
import json
import uuid

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class ExpertProfile:
    """专家档案"""
    id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    expertise_areas: List[str] = field(default_factory=list)
    podcast_appearances: List[Dict] = field(default_factory=list)
    quotes: List[str] = field(default_factory=list)
    social_links: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def appearance_count(self) -> int:
        return len(self.podcast_appearances)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "aliases": self.aliases,
            "titles": self.titles,
            "organizations": self.organizations,
            "expertise_areas": self.expertise_areas,
            "podcast_appearances": self.podcast_appearances,
            "quotes": self.quotes,
            "social_links": self.social_links,
            "appearance_count": self.appearance_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ExpertConnection:
    """专家关联"""
    expert1_id: str
    expert2_id: str
    connection_type: str  # co_appearance, same_podcast, same_topic, cited
    strength: float = 1.0
    contexts: List[Dict] = field(default_factory=list)


class ExpertNetwork:
    """
    专家网络

    功能：
    - 构建嘉宾关系图
    - 发现隐藏联系
    - 推荐潜在嘉宾
    - 专家影响力分析
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "expert_network"
        ensure_dir(self.storage_dir)
        self._experts: Dict[str, ExpertProfile] = {}
        self._connections: List[ExpertConnection] = []
        self._name_index: Dict[str, str] = {}  # name/alias -> expert_id
        self._load_data()

    def _load_data(self):
        """加载数据"""
        data_file = self.storage_dir / "network.json"
        if data_file.exists():
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for expert_data in data.get("experts", []):
                        expert = ExpertProfile(
                            id=expert_data["id"],
                            name=expert_data["name"],
                            aliases=expert_data.get("aliases", []),
                            titles=expert_data.get("titles", []),
                            organizations=expert_data.get("organizations", []),
                            expertise_areas=expert_data.get("expertise_areas", []),
                            podcast_appearances=expert_data.get("podcast_appearances", []),
                            quotes=expert_data.get("quotes", []),
                            social_links=expert_data.get("social_links", {}),
                        )
                        self._experts[expert.id] = expert
                        self._index_expert(expert)

                    for conn_data in data.get("connections", []):
                        self._connections.append(ExpertConnection(
                            expert1_id=conn_data["expert1_id"],
                            expert2_id=conn_data["expert2_id"],
                            connection_type=conn_data["connection_type"],
                            strength=conn_data.get("strength", 1.0),
                            contexts=conn_data.get("contexts", []),
                        ))
            except Exception as e:
                logger.error(f"加载专家网络失败: {e}")

    def _save_data(self):
        """保存数据"""
        data_file = self.storage_dir / "network.json"
        try:
            data = {
                "experts": [e.to_dict() for e in self._experts.values()],
                "connections": [
                    {
                        "expert1_id": c.expert1_id,
                        "expert2_id": c.expert2_id,
                        "connection_type": c.connection_type,
                        "strength": c.strength,
                        "contexts": c.contexts,
                    }
                    for c in self._connections
                ],
            }
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存专家网络失败: {e}")

    def _index_expert(self, expert: ExpertProfile):
        """索引专家"""
        self._name_index[expert.name.lower()] = expert.id
        for alias in expert.aliases:
            self._name_index[alias.lower()] = expert.id

    def add_expert(self, expert: ExpertProfile) -> ExpertProfile:
        """添加专家"""
        if not expert.id:
            expert.id = str(uuid.uuid4())[:8]
        self._experts[expert.id] = expert
        self._index_expert(expert)
        self._save_data()
        logger.info(f"添加专家: {expert.name}")
        return expert

    def find_expert(self, name: str) -> Optional[ExpertProfile]:
        """查找专家"""
        expert_id = self._name_index.get(name.lower())
        if expert_id:
            return self._experts.get(expert_id)
        return None

    def get_or_create_expert(self, name: str) -> ExpertProfile:
        """获取或创建专家"""
        expert = self.find_expert(name)
        if not expert:
            expert = self.add_expert(ExpertProfile(
                id=str(uuid.uuid4())[:8],
                name=name,
            ))
        return expert

    def add_appearance(
        self,
        expert_name: str,
        podcast_name: str,
        episode_title: str,
        date: str,
        topics: List[str] = None,
        quotes: List[str] = None,
    ):
        """记录嘉宾出场"""
        expert = self.get_or_create_expert(expert_name)

        appearance = {
            "podcast": podcast_name,
            "episode": episode_title,
            "date": date,
            "topics": topics or [],
        }

        expert.podcast_appearances.append(appearance)

        if topics:
            for topic in topics:
                if topic not in expert.expertise_areas:
                    expert.expertise_areas.append(topic)

        if quotes:
            expert.quotes.extend(quotes)

        expert.updated_at = datetime.now().isoformat()
        self._save_data()

    def add_connection(
        self,
        expert1_name: str,
        expert2_name: str,
        connection_type: str,
        context: Dict = None,
    ):
        """添加专家关联"""
        expert1 = self.get_or_create_expert(expert1_name)
        expert2 = self.get_or_create_expert(expert2_name)

        # 检查是否已存在
        existing = None
        for conn in self._connections:
            if (conn.expert1_id == expert1.id and conn.expert2_id == expert2.id) or \
               (conn.expert1_id == expert2.id and conn.expert2_id == expert1.id):
                existing = conn
                break

        if existing:
            existing.strength += 0.5
            if context:
                existing.contexts.append(context)
        else:
            self._connections.append(ExpertConnection(
                expert1_id=expert1.id,
                expert2_id=expert2.id,
                connection_type=connection_type,
                contexts=[context] if context else [],
            ))

        self._save_data()

    def detect_co_appearances(self, podcast_data: Dict):
        """
        检测同期出场

        Args:
            podcast_data: 包含 guests 列表的播客数据
        """
        guests = podcast_data.get("guests", [])
        podcast_name = podcast_data.get("podcast_name", "")
        episode_title = podcast_data.get("episode_title", "")
        date = podcast_data.get("date", datetime.now().isoformat())

        # 记录每个嘉宾的出场
        for guest in guests:
            self.add_appearance(
                guest,
                podcast_name,
                episode_title,
                date,
                podcast_data.get("topics", []),
            )

        # 记录同期出场关系
        for i, guest1 in enumerate(guests):
            for guest2 in guests[i + 1:]:
                self.add_connection(
                    guest1,
                    guest2,
                    "co_appearance",
                    {
                        "podcast": podcast_name,
                        "episode": episode_title,
                        "date": date,
                    },
                )

    def get_connections(self, expert_name: str) -> List[Tuple[ExpertProfile, ExpertConnection]]:
        """获取专家的所有关联"""
        expert = self.find_expert(expert_name)
        if not expert:
            return []

        connections = []
        for conn in self._connections:
            if conn.expert1_id == expert.id:
                other = self._experts.get(conn.expert2_id)
                if other:
                    connections.append((other, conn))
            elif conn.expert2_id == expert.id:
                other = self._experts.get(conn.expert1_id)
                if other:
                    connections.append((other, conn))

        return sorted(connections, key=lambda x: x[1].strength, reverse=True)

    def find_path(
        self,
        expert1_name: str,
        expert2_name: str,
        max_depth: int = 4,
    ) -> List[ExpertProfile]:
        """
        查找两个专家之间的关联路径

        Args:
            expert1_name: 专家1名称
            expert2_name: 专家2名称
            max_depth: 最大搜索深度

        Returns:
            路径上的专家列表
        """
        expert1 = self.find_expert(expert1_name)
        expert2 = self.find_expert(expert2_name)

        if not expert1 or not expert2:
            return []

        if expert1.id == expert2.id:
            return [expert1]

        # BFS 搜索
        from collections import deque
        queue = deque([(expert1.id, [expert1])])
        visited = {expert1.id}

        while queue:
            current_id, path = queue.popleft()

            if len(path) > max_depth:
                continue

            for conn in self._connections:
                next_id = None
                if conn.expert1_id == current_id:
                    next_id = conn.expert2_id
                elif conn.expert2_id == current_id:
                    next_id = conn.expert1_id

                if next_id and next_id not in visited:
                    next_expert = self._experts.get(next_id)
                    if next_expert:
                        new_path = path + [next_expert]
                        if next_id == expert2.id:
                            return new_path
                        visited.add(next_id)
                        queue.append((next_id, new_path))

        return []

    def recommend_guests(
        self,
        topic: str,
        exclude: List[str] = None,
        limit: int = 10,
    ) -> List[ExpertProfile]:
        """
        推荐潜在嘉宾

        Args:
            topic: 话题
            exclude: 排除的专家名称
            limit: 返回数量

        Returns:
            推荐的专家列表
        """
        exclude = exclude or []
        exclude_lower = [e.lower() for e in exclude]

        candidates = []
        topic_lower = topic.lower()

        for expert in self._experts.values():
            if expert.name.lower() in exclude_lower:
                continue

            # 计算相关性分数
            score = 0

            # 专业领域匹配
            for area in expert.expertise_areas:
                if topic_lower in area.lower() or area.lower() in topic_lower:
                    score += 2

            # 历史出场话题匹配
            for appearance in expert.podcast_appearances:
                for t in appearance.get("topics", []):
                    if topic_lower in t.lower() or t.lower() in topic_lower:
                        score += 1

            # 出场次数加分
            score += expert.appearance_count * 0.1

            if score > 0:
                candidates.append((expert, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in candidates[:limit]]

    def calculate_influence(self, expert_name: str) -> Dict[str, Any]:
        """
        计算专家影响力

        Args:
            expert_name: 专家名称

        Returns:
            影响力分析
        """
        expert = self.find_expert(expert_name)
        if not expert:
            return {}

        connections = self.get_connections(expert_name)

        # 计算各项指标
        appearance_score = expert.appearance_count * 10
        connection_score = len(connections) * 5
        expertise_breadth = len(expert.expertise_areas) * 2
        quote_impact = len(expert.quotes) * 1

        # 加权计算
        total_score = (
            appearance_score * 0.4 +
            connection_score * 0.3 +
            expertise_breadth * 0.2 +
            quote_impact * 0.1
        )

        return {
            "expert": expert.to_dict(),
            "metrics": {
                "appearance_score": appearance_score,
                "connection_score": connection_score,
                "expertise_breadth": expertise_breadth,
                "quote_impact": quote_impact,
                "total_score": total_score,
            },
            "connections_count": len(connections),
            "top_connections": [
                {"name": c[0].name, "strength": c[1].strength}
                for c in connections[:5]
            ],
        }

    def export_to_gephi(self) -> Tuple[str, str]:
        """导出为 Gephi 格式"""
        # 节点 CSV
        nodes_lines = ["Id,Label,Appearances,Expertise"]
        for expert in self._experts.values():
            expertise = "|".join(expert.expertise_areas[:5])
            nodes_lines.append(
                f'{expert.id},"{expert.name}",{expert.appearance_count},"{expertise}"'
            )

        # 边 CSV
        edges_lines = ["Source,Target,Weight,Type"]
        for conn in self._connections:
            edges_lines.append(
                f'{conn.expert1_id},{conn.expert2_id},{conn.strength},{conn.connection_type}'
            )

        return "\n".join(nodes_lines), "\n".join(edges_lines)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_appearances = sum(e.appearance_count for e in self._experts.values())

        return {
            "total_experts": len(self._experts),
            "total_connections": len(self._connections),
            "total_appearances": total_appearances,
            "top_experts": sorted(
                [{"name": e.name, "appearances": e.appearance_count} for e in self._experts.values()],
                key=lambda x: x["appearances"],
                reverse=True,
            )[:10],
            "connection_types": {},
        }
