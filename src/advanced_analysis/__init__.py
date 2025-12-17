"""
高级分析模块

功能：
- 事实核查
- 知识图谱构建
- 实体识别
- 观点对比分析
- 引用检测
- 话题追踪
- 行动建议提取
"""

from .fact_checker import FactChecker, FactCheckResult
from .knowledge_graph import KnowledgeGraphBuilder, KnowledgeGraph
from .entity_recognition import EntityRecognizer, Entity
from .opinion_analysis import OpinionAnalyzer, OpinionComparison
from .citation_detector import CitationDetector, Citation
from .topic_tracker import TopicTracker, TopicEvolution
from .action_extractor import ActionExtractor, ActionItem

__all__ = [
    "FactChecker",
    "FactCheckResult",
    "KnowledgeGraphBuilder",
    "KnowledgeGraph",
    "EntityRecognizer",
    "Entity",
    "OpinionAnalyzer",
    "OpinionComparison",
    "CitationDetector",
    "Citation",
    "TopicTracker",
    "TopicEvolution",
    "ActionExtractor",
    "ActionItem",
]
