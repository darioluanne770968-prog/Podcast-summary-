"""
观点图谱模块

追踪同一话题在不同播客中的观点演变
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
import json
import uuid

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class ViewpointNode:
    """观点节点"""
    id: str
    topic: str
    viewpoint: str
    speaker: str
    podcast_name: str
    episode_title: str
    timestamp: Optional[float] = None
    confidence: float = 1.0
    supporting_evidence: List[str] = field(default_factory=list)
    date: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "viewpoint": self.viewpoint,
            "speaker": self.speaker,
            "podcast_name": self.podcast_name,
            "episode_title": self.episode_title,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "supporting_evidence": self.supporting_evidence,
            "date": self.date,
            "tags": self.tags,
        }


@dataclass
class ViewpointEdge:
    """观点关系边"""
    source_id: str
    target_id: str
    relation: str  # agrees, disagrees, extends, references, contradicts
    strength: float = 1.0
    description: str = ""


class ViewpointGraph:
    """
    观点图谱

    功能：
    - 构建跨播客观点网络
    - 追踪观点演变
    - 发现观点关系
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "viewpoint_graph"
        ensure_dir(self.storage_dir)
        self._nodes: Dict[str, ViewpointNode] = {}
        self._edges: List[ViewpointEdge] = []
        self._topic_index: Dict[str, Set[str]] = {}  # topic -> node_ids
        self._speaker_index: Dict[str, Set[str]] = {}  # speaker -> node_ids
        self._load_data()

    def _load_data(self):
        """加载数据"""
        data_file = self.storage_dir / "graph.json"
        if data_file.exists():
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for node_data in data.get("nodes", []):
                        node = ViewpointNode(**node_data)
                        self._nodes[node.id] = node
                        self._index_node(node)
                    for edge_data in data.get("edges", []):
                        self._edges.append(ViewpointEdge(**edge_data))
            except Exception as e:
                logger.error(f"加载观点图谱失败: {e}")

    def _save_data(self):
        """保存数据"""
        data_file = self.storage_dir / "graph.json"
        try:
            data = {
                "nodes": [n.to_dict() for n in self._nodes.values()],
                "edges": [
                    {
                        "source_id": e.source_id,
                        "target_id": e.target_id,
                        "relation": e.relation,
                        "strength": e.strength,
                        "description": e.description,
                    }
                    for e in self._edges
                ],
            }
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存观点图谱失败: {e}")

    def _index_node(self, node: ViewpointNode):
        """索引节点"""
        # 话题索引
        topic_key = node.topic.lower()
        if topic_key not in self._topic_index:
            self._topic_index[topic_key] = set()
        self._topic_index[topic_key].add(node.id)

        # 说话人索引
        speaker_key = node.speaker.lower()
        if speaker_key not in self._speaker_index:
            self._speaker_index[speaker_key] = set()
        self._speaker_index[speaker_key].add(node.id)

    def add_viewpoint(self, node: ViewpointNode) -> ViewpointNode:
        """添加观点"""
        if not node.id:
            node.id = str(uuid.uuid4())[:8]
        self._nodes[node.id] = node
        self._index_node(node)
        self._save_data()
        logger.info(f"添加观点: {node.topic} - {node.viewpoint[:50]}")
        return node

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        strength: float = 1.0,
        description: str = "",
    ) -> ViewpointEdge:
        """添加关系"""
        edge = ViewpointEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            strength=strength,
            description=description,
        )
        self._edges.append(edge)
        self._save_data()
        return edge

    def get_viewpoint(self, node_id: str) -> Optional[ViewpointNode]:
        """获取观点"""
        return self._nodes.get(node_id)

    def get_by_topic(self, topic: str) -> List[ViewpointNode]:
        """按话题获取观点"""
        topic_key = topic.lower()
        node_ids = self._topic_index.get(topic_key, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def get_by_speaker(self, speaker: str) -> List[ViewpointNode]:
        """按说话人获取观点"""
        speaker_key = speaker.lower()
        node_ids = self._speaker_index.get(speaker_key, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def get_relations(self, node_id: str) -> List[ViewpointEdge]:
        """获取节点的所有关系"""
        return [
            e for e in self._edges
            if e.source_id == node_id or e.target_id == node_id
        ]

    def find_evolution(
        self,
        topic: str,
        speaker: Optional[str] = None,
    ) -> List[ViewpointNode]:
        """
        追踪观点演变

        Args:
            topic: 话题
            speaker: 说话人（可选，不指定则追踪所有人）

        Returns:
            按时间排序的观点列表
        """
        viewpoints = self.get_by_topic(topic)

        if speaker:
            viewpoints = [v for v in viewpoints if v.speaker.lower() == speaker.lower()]

        # 按日期排序
        viewpoints.sort(key=lambda v: v.date)
        return viewpoints

    def find_related(
        self,
        node_id: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        查找相关观点

        Args:
            node_id: 节点 ID
            depth: 搜索深度

        Returns:
            相关观点图
        """
        visited = set()
        result = {
            "center": self.get_viewpoint(node_id),
            "related": [],
            "relations": [],
        }

        def explore(nid: str, current_depth: int):
            if nid in visited or current_depth > depth:
                return
            visited.add(nid)

            for edge in self.get_relations(nid):
                related_id = edge.target_id if edge.source_id == nid else edge.source_id
                if related_id not in visited:
                    related_node = self.get_viewpoint(related_id)
                    if related_node:
                        result["related"].append(related_node.to_dict())
                        result["relations"].append({
                            "from": nid,
                            "to": related_id,
                            "relation": edge.relation,
                        })
                        explore(related_id, current_depth + 1)

        explore(node_id, 0)
        return result

    async def auto_detect_relations(
        self,
        node_id: str,
        llm_provider: str = "openai",
    ):
        """
        自动检测与其他观点的关系

        Args:
            node_id: 节点 ID
            llm_provider: LLM 提供者
        """
        node = self.get_viewpoint(node_id)
        if not node:
            return

        # 获取同话题的其他观点
        related_nodes = self.get_by_topic(node.topic)
        related_nodes = [n for n in related_nodes if n.id != node_id]

        if not related_nodes:
            return

        # 使用 LLM 分析关系
        prompt = f"""分析以下观点之间的关系：

主观点：
- 说话人：{node.speaker}
- 观点：{node.viewpoint}

其他观点：
"""
        for i, other in enumerate(related_nodes[:5], 1):
            prompt += f"{i}. {other.speaker}: {other.viewpoint}\n"

        prompt += """
请分析主观点与每个其他观点的关系，返回 JSON 格式：
[
  {"index": 1, "relation": "agrees/disagrees/extends/references", "strength": 0.8, "reason": "理由"}
]"""

        try:
            if llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是观点关系分析专家。"},
                        {"role": "user", "content": prompt},
                    ],
                )
                result_text = response.choices[0].message.content

                import re
                json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
                if json_match:
                    relations = json.loads(json_match.group())
                    for rel in relations:
                        idx = rel.get("index", 0) - 1
                        if 0 <= idx < len(related_nodes):
                            self.add_relation(
                                node_id,
                                related_nodes[idx].id,
                                rel.get("relation", "references"),
                                rel.get("strength", 0.5),
                                rel.get("reason", ""),
                            )
        except Exception as e:
            logger.error(f"自动检测关系失败: {e}")

    def export_to_mermaid(self, topic: Optional[str] = None) -> str:
        """导出为 Mermaid 图"""
        lines = ["graph TD"]

        nodes_to_include = set()

        if topic:
            for node in self.get_by_topic(topic):
                nodes_to_include.add(node.id)
        else:
            nodes_to_include = set(self._nodes.keys())

        # 添加节点
        for nid in nodes_to_include:
            node = self._nodes.get(nid)
            if node:
                label = f"{node.speaker}: {node.viewpoint[:30]}..."
                label = label.replace('"', "'")
                lines.append(f'    {nid}["{label}"]')

        # 添加边
        for edge in self._edges:
            if edge.source_id in nodes_to_include and edge.target_id in nodes_to_include:
                arrow = {
                    "agrees": "-->|同意|",
                    "disagrees": "-.->|反对|",
                    "extends": "-->|扩展|",
                    "references": "-->|引用|",
                    "contradicts": "-.->|矛盾|",
                }.get(edge.relation, "-->")
                lines.append(f"    {edge.source_id} {arrow} {edge.target_id}")

        return "\n".join(lines)

    def get_topic_summary(self, topic: str) -> Dict[str, Any]:
        """获取话题摘要"""
        viewpoints = self.get_by_topic(topic)

        speakers = list(set(v.speaker for v in viewpoints))
        podcasts = list(set(v.podcast_name for v in viewpoints))

        # 分析观点倾向
        positions = {}
        for v in viewpoints:
            key = v.viewpoint[:50]
            if key not in positions:
                positions[key] = []
            positions[key].append(v.speaker)

        return {
            "topic": topic,
            "total_viewpoints": len(viewpoints),
            "speakers": speakers,
            "podcasts": podcasts,
            "positions": positions,
            "timeline": [
                {"date": v.date, "speaker": v.speaker, "viewpoint": v.viewpoint[:100]}
                for v in sorted(viewpoints, key=lambda x: x.date)
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_viewpoints": len(self._nodes),
            "total_relations": len(self._edges),
            "topics": len(self._topic_index),
            "speakers": len(self._speaker_index),
            "top_topics": sorted(
                [(t, len(ids)) for t, ids in self._topic_index.items()],
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }
