"""
内容分析器
分析播客内容特征用于推荐
"""
from typing import List, Dict, Any
from dataclasses import dataclass
import numpy as np


@dataclass
class ContentFeatures:
    """内容特征"""
    podcast_id: str
    topics: List[str]
    keywords: List[str]
    sentiment: float
    complexity: float
    embedding: List[float]


class ContentAnalyzer:
    """内容分析器"""

    def __init__(self):
        self.analyzed_content: Dict[str, ContentFeatures] = {}

    def analyze(self, podcast_id: str, transcript: str, title: str) -> ContentFeatures:
        """分析播客内容"""
        topics = self._extract_topics(transcript)
        keywords = self._extract_keywords(transcript)
        sentiment = self._analyze_sentiment(transcript)
        complexity = self._calculate_complexity(transcript)
        embedding = self._generate_embedding(transcript)

        features = ContentFeatures(
            podcast_id=podcast_id,
            topics=topics,
            keywords=keywords,
            sentiment=sentiment,
            complexity=complexity,
            embedding=embedding
        )
        self.analyzed_content[podcast_id] = features
        return features

    def _extract_topics(self, text: str) -> List[str]:
        topic_keywords = {
            "科技": ["AI", "人工智能", "技术", "互联网", "软件"],
            "商业": ["创业", "投资", "管理", "营销", "公司"],
            "教育": ["学习", "教育", "知识", "课程", "培训"],
            "生活": ["健康", "生活", "心理", "情感", "成长"]
        }
        found_topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                found_topics.append(topic)
        return found_topics or ["综合"]

    def _extract_keywords(self, text: str) -> List[str]:
        # 简化的关键词提取
        words = text.split()[:100]
        return list(set(w for w in words if len(w) > 2))[:20]

    def _analyze_sentiment(self, text: str) -> float:
        positive = ["好", "棒", "喜欢", "优秀", "成功"]
        negative = ["差", "坏", "失败", "糟糕", "问题"]
        pos_count = sum(1 for w in positive if w in text)
        neg_count = sum(1 for w in negative if w in text)
        total = pos_count + neg_count
        return (pos_count - neg_count) / total if total > 0 else 0

    def _calculate_complexity(self, text: str) -> float:
        avg_sentence_len = len(text) / max(1, text.count("。") + text.count("."))
        return min(1.0, avg_sentence_len / 50)

    def _generate_embedding(self, text: str) -> List[float]:
        # 简化的embedding生成
        np.random.seed(hash(text[:100]) % 2**32)
        return list(np.random.rand(64))

    def calculate_similarity(self, podcast_id1: str, podcast_id2: str) -> float:
        """计算两个播客的相似度"""
        if podcast_id1 not in self.analyzed_content or podcast_id2 not in self.analyzed_content:
            return 0.0

        f1 = self.analyzed_content[podcast_id1]
        f2 = self.analyzed_content[podcast_id2]

        # 话题重叠
        topic_overlap = len(set(f1.topics) & set(f2.topics)) / max(len(set(f1.topics) | set(f2.topics)), 1)

        # embedding相似度
        emb_sim = np.dot(f1.embedding, f2.embedding) / (np.linalg.norm(f1.embedding) * np.linalg.norm(f2.embedding))

        return topic_overlap * 0.5 + emb_sim * 0.5
