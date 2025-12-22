"""
推荐引擎
综合多种算法提供个性化推荐
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np


class RecommendationType(Enum):
    """推荐类型"""
    CONTENT_BASED = "content_based"  # 基于内容
    COLLABORATIVE = "collaborative"  # 协同过滤
    TRENDING = "trending"  # 热门趋势
    SIMILAR_USERS = "similar_users"  # 相似用户
    DISCOVERY = "discovery"  # 探索发现
    CONTINUE_LISTENING = "continue_listening"  # 继续收听


@dataclass
class PodcastFeatures:
    """播客特征"""
    podcast_id: str
    title: str
    topics: List[str]
    duration: float
    language: str
    host_style: str
    content_type: str  # interview, solo, panel
    difficulty_level: str  # beginner, intermediate, advanced
    release_date: datetime
    popularity_score: float
    quality_score: float
    embedding: Optional[List[float]] = None


@dataclass
class UserPreferences:
    """用户偏好"""
    user_id: str
    favorite_topics: List[str]
    preferred_duration: Tuple[float, float]
    preferred_languages: List[str]
    preferred_styles: List[str]
    listening_history: List[str]
    liked_podcasts: List[str]
    disliked_podcasts: List[str]
    skip_patterns: Dict[str, float]
    engagement_scores: Dict[str, float]


@dataclass
class Recommendation:
    """推荐结果"""
    podcast_id: str
    title: str
    score: float
    recommendation_type: RecommendationType
    reason: str
    match_factors: List[str]
    predicted_engagement: float
    confidence: float


@dataclass
class RecommendationResult:
    """推荐结果集"""
    user_id: str
    recommendations: List[Recommendation]
    generated_at: datetime
    algorithm_used: List[str]
    personalization_level: float
    diversity_score: float


class RecommendationEngine:
    """推荐引擎"""

    def __init__(self):
        self.podcasts: Dict[str, PodcastFeatures] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.interaction_matrix: Dict[str, Dict[str, float]] = {}

        # 算法权重
        self.algorithm_weights = {
            RecommendationType.CONTENT_BASED: 0.35,
            RecommendationType.COLLABORATIVE: 0.25,
            RecommendationType.TRENDING: 0.15,
            RecommendationType.SIMILAR_USERS: 0.15,
            RecommendationType.DISCOVERY: 0.10
        }

    def add_podcast(self, podcast: PodcastFeatures):
        """添加播客到推荐库"""
        self.podcasts[podcast.podcast_id] = podcast

    def update_user_preferences(self, preferences: UserPreferences):
        """更新用户偏好"""
        self.user_preferences[preferences.user_id] = preferences

    def record_interaction(
        self,
        user_id: str,
        podcast_id: str,
        interaction_score: float
    ):
        """记录用户交互"""
        if user_id not in self.interaction_matrix:
            self.interaction_matrix[user_id] = {}
        self.interaction_matrix[user_id][podcast_id] = interaction_score

    def get_recommendations(
        self,
        user_id: str,
        count: int = 10,
        exclude_listened: bool = True,
        recommendation_types: Optional[List[RecommendationType]] = None
    ) -> RecommendationResult:
        """
        获取推荐

        Args:
            user_id: 用户ID
            count: 推荐数量
            exclude_listened: 是否排除已听
            recommendation_types: 指定推荐类型

        Returns:
            推荐结果
        """
        all_recommendations = []
        algorithms_used = []

        user_prefs = self.user_preferences.get(user_id)

        # 获取已听列表用于排除
        listened = set()
        if exclude_listened and user_prefs:
            listened = set(user_prefs.listening_history)

        # 基于内容的推荐
        if not recommendation_types or RecommendationType.CONTENT_BASED in recommendation_types:
            content_recs = self._content_based_recommendations(user_id, listened)
            all_recommendations.extend(content_recs)
            algorithms_used.append("content_based")

        # 协同过滤推荐
        if not recommendation_types or RecommendationType.COLLABORATIVE in recommendation_types:
            collab_recs = self._collaborative_recommendations(user_id, listened)
            all_recommendations.extend(collab_recs)
            algorithms_used.append("collaborative")

        # 热门推荐
        if not recommendation_types or RecommendationType.TRENDING in recommendation_types:
            trending_recs = self._trending_recommendations(listened)
            all_recommendations.extend(trending_recs)
            algorithms_used.append("trending")

        # 探索发现
        if not recommendation_types or RecommendationType.DISCOVERY in recommendation_types:
            discovery_recs = self._discovery_recommendations(user_id, listened)
            all_recommendations.extend(discovery_recs)
            algorithms_used.append("discovery")

        # 合并和排序推荐
        final_recommendations = self._merge_recommendations(all_recommendations, count)

        # 计算多样性分数
        diversity_score = self._calculate_diversity(final_recommendations)

        # 计算个性化程度
        personalization_level = self._calculate_personalization(user_id, final_recommendations)

        return RecommendationResult(
            user_id=user_id,
            recommendations=final_recommendations,
            generated_at=datetime.now(),
            algorithm_used=algorithms_used,
            personalization_level=personalization_level,
            diversity_score=diversity_score
        )

    def _content_based_recommendations(
        self,
        user_id: str,
        exclude: set
    ) -> List[Recommendation]:
        """基于内容的推荐"""
        recommendations = []
        user_prefs = self.user_preferences.get(user_id)

        if not user_prefs:
            return []

        for podcast_id, podcast in self.podcasts.items():
            if podcast_id in exclude:
                continue

            # 计算匹配分数
            score, factors = self._calculate_content_match(user_prefs, podcast)

            if score > 0.3:
                recommendations.append(Recommendation(
                    podcast_id=podcast_id,
                    title=podcast.title,
                    score=score,
                    recommendation_type=RecommendationType.CONTENT_BASED,
                    reason=self._generate_reason(factors),
                    match_factors=factors,
                    predicted_engagement=score * 0.8,
                    confidence=0.7
                ))

        return recommendations

    def _calculate_content_match(
        self,
        user_prefs: UserPreferences,
        podcast: PodcastFeatures
    ) -> Tuple[float, List[str]]:
        """计算内容匹配度"""
        score = 0.0
        factors = []

        # 话题匹配
        topic_overlap = set(user_prefs.favorite_topics) & set(podcast.topics)
        if topic_overlap:
            topic_score = len(topic_overlap) / max(len(user_prefs.favorite_topics), 1)
            score += topic_score * 0.4
            factors.append(f"话题匹配: {', '.join(topic_overlap)}")

        # 时长匹配
        min_dur, max_dur = user_prefs.preferred_duration
        if min_dur <= podcast.duration <= max_dur:
            score += 0.2
            factors.append("时长适合")

        # 语言匹配
        if podcast.language in user_prefs.preferred_languages:
            score += 0.2
            factors.append("语言匹配")

        # 风格匹配
        if podcast.host_style in user_prefs.preferred_styles:
            score += 0.2
            factors.append("风格匹配")

        return min(1.0, score), factors

    def _collaborative_recommendations(
        self,
        user_id: str,
        exclude: set
    ) -> List[Recommendation]:
        """协同过滤推荐"""
        recommendations = []

        if user_id not in self.interaction_matrix:
            return []

        user_interactions = self.interaction_matrix[user_id]

        # 找相似用户
        similar_users = self._find_similar_users(user_id)

        # 收集相似用户喜欢的播客
        candidate_podcasts = {}
        for sim_user_id, similarity in similar_users[:10]:
            if sim_user_id in self.interaction_matrix:
                for podcast_id, score in self.interaction_matrix[sim_user_id].items():
                    if podcast_id not in exclude and podcast_id not in user_interactions:
                        if podcast_id not in candidate_podcasts:
                            candidate_podcasts[podcast_id] = []
                        candidate_podcasts[podcast_id].append((similarity, score))

        # 计算推荐分数
        for podcast_id, scores in candidate_podcasts.items():
            if podcast_id not in self.podcasts:
                continue

            weighted_score = sum(sim * score for sim, score in scores) / sum(sim for sim, _ in scores)

            recommendations.append(Recommendation(
                podcast_id=podcast_id,
                title=self.podcasts[podcast_id].title,
                score=weighted_score,
                recommendation_type=RecommendationType.COLLABORATIVE,
                reason="相似用户也喜欢",
                match_factors=["协同过滤"],
                predicted_engagement=weighted_score * 0.75,
                confidence=0.6
            ))

        return recommendations

    def _find_similar_users(self, user_id: str) -> List[Tuple[str, float]]:
        """找到相似用户"""
        if user_id not in self.interaction_matrix:
            return []

        user_vector = self.interaction_matrix[user_id]
        similarities = []

        for other_id, other_vector in self.interaction_matrix.items():
            if other_id == user_id:
                continue

            similarity = self._cosine_similarity(user_vector, other_vector)
            if similarity > 0.1:
                similarities.append((other_id, similarity))

        return sorted(similarities, key=lambda x: x[1], reverse=True)

    def _cosine_similarity(
        self,
        vec1: Dict[str, float],
        vec2: Dict[str, float]
    ) -> float:
        """计算余弦相似度"""
        common_keys = set(vec1.keys()) & set(vec2.keys())
        if not common_keys:
            return 0.0

        dot_product = sum(vec1[k] * vec2[k] for k in common_keys)
        norm1 = np.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = np.sqrt(sum(v ** 2 for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _trending_recommendations(self, exclude: set) -> List[Recommendation]:
        """热门推荐"""
        recommendations = []

        # 按热度排序
        sorted_podcasts = sorted(
            self.podcasts.values(),
            key=lambda x: x.popularity_score,
            reverse=True
        )

        for podcast in sorted_podcasts[:20]:
            if podcast.podcast_id in exclude:
                continue

            recommendations.append(Recommendation(
                podcast_id=podcast.podcast_id,
                title=podcast.title,
                score=podcast.popularity_score,
                recommendation_type=RecommendationType.TRENDING,
                reason="热门播客",
                match_factors=["高人气", "热门趋势"],
                predicted_engagement=podcast.popularity_score * 0.6,
                confidence=0.5
            ))

        return recommendations

    def _discovery_recommendations(
        self,
        user_id: str,
        exclude: set
    ) -> List[Recommendation]:
        """探索发现推荐"""
        recommendations = []
        user_prefs = self.user_preferences.get(user_id)

        # 找到用户不常听的类型中高质量的播客
        user_topics = set(user_prefs.favorite_topics) if user_prefs else set()

        for podcast_id, podcast in self.podcasts.items():
            if podcast_id in exclude:
                continue

            # 检查是否是新领域
            podcast_topics = set(podcast.topics)
            if not (podcast_topics & user_topics):
                # 新领域，但质量要高
                if podcast.quality_score > 0.7:
                    recommendations.append(Recommendation(
                        podcast_id=podcast_id,
                        title=podcast.title,
                        score=podcast.quality_score * 0.8,
                        recommendation_type=RecommendationType.DISCOVERY,
                        reason="发现新领域",
                        match_factors=["新话题", "高质量"],
                        predicted_engagement=0.5,
                        confidence=0.4
                    ))

        return recommendations

    def _merge_recommendations(
        self,
        all_recommendations: List[Recommendation],
        count: int
    ) -> List[Recommendation]:
        """合并推荐结果"""
        # 按播客ID去重，保留最高分
        unique_recs = {}
        for rec in all_recommendations:
            if rec.podcast_id not in unique_recs or rec.score > unique_recs[rec.podcast_id].score:
                unique_recs[rec.podcast_id] = rec

        # 应用算法权重
        for rec in unique_recs.values():
            weight = self.algorithm_weights.get(rec.recommendation_type, 0.5)
            rec.score *= weight

        # 排序并返回
        sorted_recs = sorted(unique_recs.values(), key=lambda x: x.score, reverse=True)
        return sorted_recs[:count]

    def _generate_reason(self, factors: List[str]) -> str:
        """生成推荐理由"""
        if not factors:
            return "为你推荐"
        return "、".join(factors[:2])

    def _calculate_diversity(self, recommendations: List[Recommendation]) -> float:
        """计算推荐多样性"""
        if len(recommendations) < 2:
            return 1.0

        # 计算话题多样性
        all_topics = set()
        for rec in recommendations:
            if rec.podcast_id in self.podcasts:
                all_topics.update(self.podcasts[rec.podcast_id].topics)

        # 多样性 = 不同话题数 / 推荐数
        return min(1.0, len(all_topics) / len(recommendations))

    def _calculate_personalization(
        self,
        user_id: str,
        recommendations: List[Recommendation]
    ) -> float:
        """计算个性化程度"""
        if not recommendations:
            return 0.0

        # 基于内容和协同过滤的推荐占比
        personalized_count = sum(
            1 for rec in recommendations
            if rec.recommendation_type in [
                RecommendationType.CONTENT_BASED,
                RecommendationType.COLLABORATIVE,
                RecommendationType.SIMILAR_USERS
            ]
        )

        return personalized_count / len(recommendations)

    def explain_recommendation(self, recommendation: Recommendation) -> Dict[str, Any]:
        """解释推荐原因"""
        return {
            "podcast_id": recommendation.podcast_id,
            "title": recommendation.title,
            "recommendation_type": recommendation.recommendation_type.value,
            "main_reason": recommendation.reason,
            "match_factors": recommendation.match_factors,
            "score_breakdown": {
                "raw_score": recommendation.score,
                "predicted_engagement": recommendation.predicted_engagement,
                "confidence": recommendation.confidence
            },
            "explanation": f"我们推荐「{recommendation.title}」是因为{recommendation.reason}"
        }
