"""
知识图谱构建模块

从播客内容中提取实体和关系，构建知识图谱
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Tuple
import json

from ..analysis import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class GraphNode:
    """图谱节点"""
    id: str
    label: str
    type: str  # person, organization, concept, product, event, location
    properties: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "properties": self.properties,
        }


@dataclass
class GraphEdge:
    """图谱边（关系）"""
    source: str  # 源节点 ID
    target: str  # 目标节点 ID
    relation: str  # 关系类型
    weight: float = 1.0
    properties: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "properties": self.properties,
        }


@dataclass
class KnowledgeGraph:
    """知识图谱"""
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def add_node(self, node: GraphNode):
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: GraphEdge):
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_neighbors(self, node_id: str) -> List[Tuple[GraphNode, GraphEdge]]:
        """获取节点的所有邻居"""
        neighbors = []
        for edge in self.edges:
            if edge.source == node_id:
                target = self.get_node(edge.target)
                if target:
                    neighbors.append((target, edge))
            elif edge.target == node_id:
                source = self.get_node(edge.source)
                if source:
                    neighbors.append((source, edge))
        return neighbors

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_mermaid(self) -> str:
        """导出为 Mermaid 图表格式"""
        lines = ["graph LR"]

        # 节点样式
        node_styles = {
            "person": "([{label}])",
            "organization": "[/{label}/]",
            "concept": "(({label}))",
            "product": "[{label}]",
            "event": ">{label}]",
            "location": "[({label})]",
        }

        # 添加节点
        for node in self.nodes:
            style = node_styles.get(node.type, "[{label}]")
            node_str = style.format(label=node.label)
            lines.append(f"    {node.id}{node_str}")

        # 添加边
        for edge in self.edges:
            lines.append(f"    {edge.source} -->|{edge.relation}| {edge.target}")

        return "\n".join(lines)

    def to_cytoscape(self) -> dict:
        """导出为 Cytoscape.js 格式"""
        elements = []

        for node in self.nodes:
            elements.append({
                "data": {
                    "id": node.id,
                    "label": node.label,
                    "type": node.type,
                    **node.properties,
                }
            })

        for edge in self.edges:
            elements.append({
                "data": {
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.relation,
                    "weight": edge.weight,
                    **edge.properties,
                }
            })

        return {"elements": elements}


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    SYSTEM_PROMPT = """你是一个知识图谱构建专家。从文本中提取实体和关系，构建结构化的知识图谱。

实体类型：
- person: 人物
- organization: 组织/公司
- concept: 概念/理论
- product: 产品/技术
- event: 事件
- location: 地点

关系类型示例：
- works_at, founded, invested_in
- is_a, part_of, related_to
- created, developed, uses
- happened_at, occurred_in

提取原则：
1. 实体名称应标准化
2. 关系应具体明确
3. 避免过度抽象的关系
4. 保持图谱的连通性"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def build(
        self,
        transcript: str,
        title: Optional[str] = None,
        existing_graph: Optional[KnowledgeGraph] = None,
    ) -> KnowledgeGraph:
        """
        从转录文本构建知识图谱

        Args:
            transcript: 转录文本
            title: 播客标题
            existing_graph: 现有图谱（用于增量构建）

        Returns:
            KnowledgeGraph 对象
        """
        logger.info("构建知识图谱...")

        graph = existing_graph or KnowledgeGraph()
        graph.metadata["title"] = title

        # 1. 提取实体和关系
        extracted = self._extract_entities_and_relations(transcript)

        # 2. 添加到图谱
        for entity in extracted.get("entities", []):
            node = GraphNode(
                id=self._generate_id(entity["name"]),
                label=entity["name"],
                type=entity["type"],
                properties={"mentions": entity.get("mentions", 1)},
            )
            graph.add_node(node)

        for relation in extracted.get("relations", []):
            edge = GraphEdge(
                source=self._generate_id(relation["source"]),
                target=self._generate_id(relation["target"]),
                relation=relation["type"],
                weight=relation.get("confidence", 1.0),
            )
            graph.add_edge(edge)

        logger.info(f"知识图谱构建完成: {len(graph.nodes)} 节点, {len(graph.edges)} 边")
        return graph

    def _extract_entities_and_relations(self, transcript: str) -> dict:
        """提取实体和关系"""
        prompt = f"""分析以下播客转录文本，提取实体和关系。

文本：
---
{transcript[:25000]}
---

请按以下 JSON 格式输出：

```json
{{
  "entities": [
    {{"name": "实体名称", "type": "person/organization/concept/product/event/location", "mentions": 3}}
  ],
  "relations": [
    {{"source": "实体A", "target": "实体B", "type": "关系类型", "confidence": 0.9}}
  ]
}}
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.2)
            return self.llm.parse_json_response(response)
        except Exception as e:
            logger.error(f"提取实体关系失败: {e}")
            return {"entities": [], "relations": []}

    def _generate_id(self, name: str) -> str:
        """生成节点 ID"""
        import re
        # 移除特殊字符，转小写，用下划线连接
        clean = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '_', name)
        return clean.lower().strip('_')

    def merge_graphs(self, graphs: List[KnowledgeGraph]) -> KnowledgeGraph:
        """合并多个知识图谱"""
        merged = KnowledgeGraph()

        for graph in graphs:
            # 合并节点
            for node in graph.nodes:
                existing = merged.get_node(node.id)
                if existing:
                    # 合并属性
                    existing.properties["mentions"] = (
                        existing.properties.get("mentions", 1) +
                        node.properties.get("mentions", 1)
                    )
                else:
                    merged.add_node(node)

            # 合并边
            for edge in graph.edges:
                merged.add_edge(edge)

        return merged

    def find_central_nodes(
        self,
        graph: KnowledgeGraph,
        top_k: int = 10,
    ) -> List[Tuple[GraphNode, float]]:
        """找出图谱中最重要的节点（基于度中心性）"""
        degree_count = {}

        for edge in graph.edges:
            degree_count[edge.source] = degree_count.get(edge.source, 0) + 1
            degree_count[edge.target] = degree_count.get(edge.target, 0) + 1

        # 排序
        sorted_nodes = sorted(
            degree_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        result = []
        for node_id, degree in sorted_nodes:
            node = graph.get_node(node_id)
            if node:
                result.append((node, degree))

        return result

    def export_to_neo4j_cypher(self, graph: KnowledgeGraph) -> str:
        """导出为 Neo4j Cypher 语句"""
        lines = ["// 创建节点"]

        for node in graph.nodes:
            props = json.dumps(node.properties, ensure_ascii=False)
            lines.append(
                f"CREATE (:{node.type.capitalize()} {{id: '{node.id}', name: '{node.label}', properties: {props}}})"
            )

        lines.append("\n// 创建关系")
        for edge in graph.edges:
            lines.append(
                f"MATCH (a {{id: '{edge.source}'}}), (b {{id: '{edge.target}'}}) "
                f"CREATE (a)-[:{edge.relation.upper()}]->(b)"
            )

        return "\n".join(lines)
