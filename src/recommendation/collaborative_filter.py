"""
协同过滤
基于用户行为的协同过滤推荐
"""
from typing import List, Dict, Tuple
import numpy as np


class CollaborativeFilter:
    """协同过滤器"""

    def __init__(self):
        self.user_item_matrix: Dict[str, Dict[str, float]] = {}

    def add_interaction(self, user_id: str, item_id: str, score: float):
        """记录交互"""
        if user_id not in self.user_item_matrix:
            self.user_item_matrix[user_id] = {}
        self.user_item_matrix[user_id][item_id] = score

    def get_similar_users(self, user_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """获取相似用户"""
        if user_id not in self.user_item_matrix:
            return []

        user_vector = self.user_item_matrix[user_id]
        similarities = []

        for other_id, other_vector in self.user_item_matrix.items():
            if other_id == user_id:
                continue
            sim = self._cosine_similarity(user_vector, other_vector)
            similarities.append((other_id, sim))

        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_n]

    def recommend(self, user_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """生成推荐"""
        similar_users = self.get_similar_users(user_id, 20)
        user_items = set(self.user_item_matrix.get(user_id, {}).keys())

        candidates = {}
        for sim_user_id, similarity in similar_users:
            for item_id, score in self.user_item_matrix[sim_user_id].items():
                if item_id not in user_items:
                    if item_id not in candidates:
                        candidates[item_id] = []
                    candidates[item_id].append(similarity * score)

        # 计算加权平均分
        recommendations = [
            (item_id, np.mean(scores))
            for item_id, scores in candidates.items()
        ]

        return sorted(recommendations, key=lambda x: x[1], reverse=True)[:top_n]

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        common = set(vec1.keys()) & set(vec2.keys())
        if not common:
            return 0.0
        dot = sum(vec1[k] * vec2[k] for k in common)
        norm1 = np.sqrt(sum(v**2 for v in vec1.values()))
        norm2 = np.sqrt(sum(v**2 for v in vec2.values()))
        return dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0.0
