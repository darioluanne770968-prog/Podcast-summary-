"""
病毒传播预测器
预测内容的传播潜力和优化建议
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from datetime import datetime


class ViralFactor(Enum):
    """病毒传播因素"""
    EMOTIONAL_IMPACT = "emotional_impact"  # 情感冲击
    NOVELTY = "novelty"  # 新颖性
    RELATABILITY = "relatability"  # 相关性/共鸣
    SHAREABILITY = "shareability"  # 分享意愿
    TIMING = "timing"  # 时机
    CONTROVERSY = "controversy"  # 争议性
    UTILITY = "utility"  # 实用价值
    ENTERTAINMENT = "entertainment"  # 娱乐价值
    SOCIAL_CURRENCY = "social_currency"  # 社交货币
    TRIGGER = "trigger"  # 触发因素


@dataclass
class ViralPrediction:
    """病毒传播预测结果"""
    overall_score: float  # 0-100
    confidence: float  # 预测置信度
    predicted_reach: Dict[str, int]  # 预估触达
    factor_scores: Dict[ViralFactor, float]
    strengths: List[str]
    weaknesses: List[str]
    optimization_suggestions: List[Dict[str, Any]]
    comparable_content: List[Dict[str, Any]]
    risk_factors: List[str]
    best_platforms: List[str]
    predicted_timeline: Dict[str, Any]


@dataclass
class ContentFeatures:
    """内容特征"""
    duration: float
    has_hook: bool
    hook_strength: float
    emotional_peaks: int
    humor_score: float
    controversy_score: float
    novelty_score: float
    clarity_score: float
    production_quality: float
    speaker_charisma: float
    topic_trending: float
    call_to_action_strength: float


class ViralPredictor:
    """病毒传播预测器"""

    # 各因素权重
    FACTOR_WEIGHTS = {
        ViralFactor.EMOTIONAL_IMPACT: 0.20,
        ViralFactor.NOVELTY: 0.12,
        ViralFactor.RELATABILITY: 0.15,
        ViralFactor.SHAREABILITY: 0.13,
        ViralFactor.TIMING: 0.08,
        ViralFactor.CONTROVERSY: 0.07,
        ViralFactor.UTILITY: 0.10,
        ViralFactor.ENTERTAINMENT: 0.08,
        ViralFactor.SOCIAL_CURRENCY: 0.04,
        ViralFactor.TRIGGER: 0.03
    }

    # 平台特征
    PLATFORM_CHARACTERISTICS = {
        "tiktok": {
            "preferred_duration": (15, 60),
            "key_factors": [ViralFactor.ENTERTAINMENT, ViralFactor.EMOTIONAL_IMPACT],
            "audience": "young",
            "virality_multiplier": 1.5
        },
        "instagram": {
            "preferred_duration": (15, 90),
            "key_factors": [ViralFactor.SHAREABILITY, ViralFactor.SOCIAL_CURRENCY],
            "audience": "mixed",
            "virality_multiplier": 1.2
        },
        "youtube": {
            "preferred_duration": (30, 600),
            "key_factors": [ViralFactor.UTILITY, ViralFactor.NOVELTY],
            "audience": "mixed",
            "virality_multiplier": 1.0
        },
        "twitter": {
            "preferred_duration": (15, 140),
            "key_factors": [ViralFactor.CONTROVERSY, ViralFactor.TIMING],
            "audience": "news_focused",
            "virality_multiplier": 1.3
        },
        "linkedin": {
            "preferred_duration": (30, 300),
            "key_factors": [ViralFactor.UTILITY, ViralFactor.SOCIAL_CURRENCY],
            "audience": "professional",
            "virality_multiplier": 0.8
        },
        "douyin": {
            "preferred_duration": (15, 60),
            "key_factors": [ViralFactor.ENTERTAINMENT, ViralFactor.TRIGGER],
            "audience": "chinese_young",
            "virality_multiplier": 1.6
        },
        "bilibili": {
            "preferred_duration": (60, 600),
            "key_factors": [ViralFactor.ENTERTAINMENT, ViralFactor.UTILITY],
            "audience": "chinese_young",
            "virality_multiplier": 1.1
        }
    }

    def __init__(self):
        self.historical_data = self._load_historical_data()
        self.trending_topics = self._load_trending_topics()

    def _load_historical_data(self) -> Dict[str, Any]:
        """加载历史数据用于预测"""
        return {
            "avg_viral_score": 45,
            "viral_threshold": 70,
            "super_viral_threshold": 85,
            "typical_reach_multipliers": {
                "low": 1,
                "medium": 10,
                "high": 100,
                "viral": 1000
            }
        }

    def _load_trending_topics(self) -> List[str]:
        """加载热门话题"""
        return [
            "AI", "人工智能", "ChatGPT", "创业", "职场",
            "心理健康", "投资", "教育", "科技", "元宇宙",
            "新能源", "Web3", "远程工作", "副业", "自媒体"
        ]

    def predict_virality(
        self,
        content: Dict[str, Any],
        transcript: str,
        audio_features: Dict[str, Any],
        target_platforms: Optional[List[str]] = None
    ) -> ViralPrediction:
        """
        预测内容的病毒传播潜力

        Args:
            content: 内容信息
            transcript: 转录文本
            audio_features: 音频特征
            target_platforms: 目标平台列表

        Returns:
            病毒传播预测结果
        """
        # 提取内容特征
        features = self._extract_features(content, transcript, audio_features)

        # 计算各因素分数
        factor_scores = self._calculate_factor_scores(features, transcript)

        # 计算总体分数
        overall_score = self._calculate_overall_score(factor_scores)

        # 评估优劣势
        strengths, weaknesses = self._evaluate_strengths_weaknesses(factor_scores)

        # 生成优化建议
        suggestions = self._generate_optimization_suggestions(
            features, factor_scores, weaknesses
        )

        # 预测触达
        predicted_reach = self._predict_reach(overall_score, target_platforms)

        # 找到可比较的内容
        comparable = self._find_comparable_content(features, overall_score)

        # 评估风险
        risk_factors = self._assess_risks(content, transcript)

        # 推荐平台
        best_platforms = self._recommend_platforms(features, factor_scores)

        # 预测传播时间线
        timeline = self._predict_timeline(overall_score)

        # 计算置信度
        confidence = self._calculate_confidence(features)

        return ViralPrediction(
            overall_score=overall_score,
            confidence=confidence,
            predicted_reach=predicted_reach,
            factor_scores=factor_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            optimization_suggestions=suggestions,
            comparable_content=comparable,
            risk_factors=risk_factors,
            best_platforms=best_platforms,
            predicted_timeline=timeline
        )

    def _extract_features(
        self,
        content: Dict[str, Any],
        transcript: str,
        audio_features: Dict[str, Any]
    ) -> ContentFeatures:
        """提取内容特征"""
        duration = content.get("duration", 30)

        # 分析开头钩子
        hook_analysis = self._analyze_hook(transcript)

        # 分析情感峰值
        emotional_peaks = len(audio_features.get("volume_peaks", []))

        # 分析幽默分数
        humor_score = self._analyze_humor(transcript)

        # 分析争议性
        controversy_score = self._analyze_controversy(transcript)

        # 分析新颖性
        novelty_score = self._analyze_novelty(transcript)

        # 分析清晰度
        clarity_score = self._analyze_clarity(transcript)

        # 分析制作质量
        production_quality = self._analyze_production_quality(audio_features)

        # 分析演讲者魅力
        speaker_charisma = self._analyze_charisma(audio_features)

        # 分析话题热度
        topic_trending = self._analyze_topic_trending(transcript)

        # 分析行动号召
        cta_strength = self._analyze_cta(transcript)

        return ContentFeatures(
            duration=duration,
            has_hook=hook_analysis["has_hook"],
            hook_strength=hook_analysis["strength"],
            emotional_peaks=emotional_peaks,
            humor_score=humor_score,
            controversy_score=controversy_score,
            novelty_score=novelty_score,
            clarity_score=clarity_score,
            production_quality=production_quality,
            speaker_charisma=speaker_charisma,
            topic_trending=topic_trending,
            call_to_action_strength=cta_strength
        )

    def _analyze_hook(self, transcript: str) -> Dict[str, Any]:
        """分析开头钩子"""
        if not transcript:
            return {"has_hook": False, "strength": 0.0}

        # 钩子关键词
        hook_indicators = [
            "你知道吗", "想象一下", "让我告诉你", "震惊",
            "秘密", "真相", "不敢相信", "必须", "一定要",
            "从来没有", "改变了", "这就是为什么"
        ]

        first_50_chars = transcript[:50].lower()

        hook_found = any(indicator in first_50_chars for indicator in hook_indicators)

        # 计算钩子强度
        strength = 0.0
        if hook_found:
            strength = 0.7
            # 如果是问句开头，加分
            if "?" in first_50_chars or "？" in first_50_chars:
                strength += 0.2
        elif "?" in first_50_chars or "？" in first_50_chars:
            hook_found = True
            strength = 0.5

        return {"has_hook": hook_found, "strength": min(1.0, strength)}

    def _analyze_humor(self, transcript: str) -> float:
        """分析幽默分数"""
        humor_indicators = [
            "哈哈", "笑", "搞笑", "有趣", "逗", "段子",
            "笑死", "太好笑", "幽默"
        ]

        count = sum(1 for indicator in humor_indicators if indicator in transcript)

        return min(1.0, count * 0.15)

    def _analyze_controversy(self, transcript: str) -> float:
        """分析争议性"""
        controversy_indicators = [
            "但是", "然而", "不同意", "争议", "反对",
            "错误", "其实不是", "真相是", "被误解"
        ]

        count = sum(1 for indicator in controversy_indicators if indicator in transcript)

        return min(1.0, count * 0.12)

    def _analyze_novelty(self, transcript: str) -> float:
        """分析新颖性"""
        novelty_indicators = [
            "首次", "独家", "从未", "创新", "突破",
            "新发现", "最新", "前所未有", "革命性"
        ]

        count = sum(1 for indicator in novelty_indicators if indicator in transcript)
        base_score = min(1.0, count * 0.2)

        # 检查是否涉及热门话题
        trending_boost = 0.0
        for topic in self.trending_topics:
            if topic.lower() in transcript.lower():
                trending_boost += 0.1

        return min(1.0, base_score + trending_boost)

    def _analyze_clarity(self, transcript: str) -> float:
        """分析清晰度"""
        if not transcript:
            return 0.5

        # 简单的清晰度启发式
        sentences = transcript.split("。")
        if not sentences:
            return 0.5

        avg_sentence_length = np.mean([len(s) for s in sentences if s])

        # 理想句子长度：15-30字
        if 15 <= avg_sentence_length <= 30:
            clarity = 0.9
        elif 10 <= avg_sentence_length <= 40:
            clarity = 0.7
        else:
            clarity = 0.5

        return clarity

    def _analyze_production_quality(self, audio_features: Dict[str, Any]) -> float:
        """分析制作质量"""
        # 基于音频特征估算质量
        sample_rate = audio_features.get("sample_rate", 44100)

        if sample_rate >= 44100:
            quality = 0.8
        elif sample_rate >= 22050:
            quality = 0.6
        else:
            quality = 0.4

        # 检查是否有静音区域（可能是剪辑过的）
        silence_regions = audio_features.get("silence_regions", [])
        if len(silence_regions) < 3:
            quality += 0.1

        return min(1.0, quality)

    def _analyze_charisma(self, audio_features: Dict[str, Any]) -> float:
        """分析演讲者魅力"""
        # 基于音量变化和节奏变化
        volume_peaks = audio_features.get("volume_peaks", [])
        tempo_changes = audio_features.get("tempo_changes", [])

        # 有变化的演讲更有魅力
        variation_score = min(1.0, (len(volume_peaks) + len(tempo_changes)) * 0.1)

        return 0.5 + variation_score * 0.5

    def _analyze_topic_trending(self, transcript: str) -> float:
        """分析话题热度"""
        trending_count = 0

        for topic in self.trending_topics:
            if topic.lower() in transcript.lower():
                trending_count += 1

        return min(1.0, trending_count * 0.15)

    def _analyze_cta(self, transcript: str) -> float:
        """分析行动号召强度"""
        cta_indicators = [
            "关注", "点赞", "分享", "订阅", "评论",
            "收藏", "转发", "点击", "了解更多"
        ]

        count = sum(1 for indicator in cta_indicators if indicator in transcript)

        return min(1.0, count * 0.2)

    def _calculate_factor_scores(
        self,
        features: ContentFeatures,
        transcript: str
    ) -> Dict[ViralFactor, float]:
        """计算各因素分数"""
        return {
            ViralFactor.EMOTIONAL_IMPACT: min(1.0, features.emotional_peaks * 0.2 + features.speaker_charisma * 0.5),
            ViralFactor.NOVELTY: features.novelty_score,
            ViralFactor.RELATABILITY: 0.6 + features.clarity_score * 0.3,  # 默认较高
            ViralFactor.SHAREABILITY: features.hook_strength * 0.4 + features.call_to_action_strength * 0.3 + 0.3,
            ViralFactor.TIMING: features.topic_trending,
            ViralFactor.CONTROVERSY: features.controversy_score,
            ViralFactor.UTILITY: features.clarity_score * 0.6 + features.novelty_score * 0.4,
            ViralFactor.ENTERTAINMENT: features.humor_score * 0.6 + features.speaker_charisma * 0.4,
            ViralFactor.SOCIAL_CURRENCY: features.novelty_score * 0.5 + features.controversy_score * 0.3 + 0.2,
            ViralFactor.TRIGGER: features.hook_strength
        }

    def _calculate_overall_score(self, factor_scores: Dict[ViralFactor, float]) -> float:
        """计算总体分数"""
        weighted_sum = sum(
            factor_scores[factor] * self.FACTOR_WEIGHTS[factor]
            for factor in ViralFactor
        )

        # 转换为0-100分
        return round(weighted_sum * 100, 1)

    def _evaluate_strengths_weaknesses(
        self,
        factor_scores: Dict[ViralFactor, float]
    ) -> Tuple[List[str], List[str]]:
        """评估优劣势"""
        strengths = []
        weaknesses = []

        factor_names = {
            ViralFactor.EMOTIONAL_IMPACT: "情感冲击力",
            ViralFactor.NOVELTY: "新颖性",
            ViralFactor.RELATABILITY: "共鸣度",
            ViralFactor.SHAREABILITY: "分享意愿",
            ViralFactor.TIMING: "时机把握",
            ViralFactor.CONTROVERSY: "话题性",
            ViralFactor.UTILITY: "实用价值",
            ViralFactor.ENTERTAINMENT: "娱乐价值",
            ViralFactor.SOCIAL_CURRENCY: "社交价值",
            ViralFactor.TRIGGER: "注意力钩子"
        }

        for factor, score in factor_scores.items():
            name = factor_names[factor]
            if score >= 0.7:
                strengths.append(f"✓ {name}很强 ({score:.0%})")
            elif score <= 0.3:
                weaknesses.append(f"✗ {name}较弱 ({score:.0%})")

        return strengths, weaknesses

    def _generate_optimization_suggestions(
        self,
        features: ContentFeatures,
        factor_scores: Dict[ViralFactor, float],
        weaknesses: List[str]
    ) -> List[Dict[str, Any]]:
        """生成优化建议"""
        suggestions = []

        # 钩子建议
        if not features.has_hook or features.hook_strength < 0.5:
            suggestions.append({
                "category": "开头优化",
                "priority": "high",
                "suggestion": "添加更强的开头钩子",
                "details": "尝试用提问、惊人事实或故事开场，前3秒决定用户是否继续观看",
                "examples": ["你知道为什么...", "如果我告诉你...", "99%的人都不知道..."]
            })

        # 时长建议
        if features.duration > 60:
            suggestions.append({
                "category": "时长优化",
                "priority": "medium",
                "suggestion": "考虑缩短视频时长",
                "details": "短视频平台的最佳时长是15-30秒，考虑剪辑成更短的版本"
            })

        # 情感建议
        if factor_scores[ViralFactor.EMOTIONAL_IMPACT] < 0.5:
            suggestions.append({
                "category": "情感优化",
                "priority": "high",
                "suggestion": "增加情感元素",
                "details": "添加个人故事、幽默或惊喜元素来增加情感冲击"
            })

        # 行动号召建议
        if features.call_to_action_strength < 0.3:
            suggestions.append({
                "category": "互动优化",
                "priority": "medium",
                "suggestion": "添加清晰的行动号召",
                "details": "告诉观众下一步该做什么：关注、点赞、评论或分享"
            })

        # 话题建议
        if factor_scores[ViralFactor.TIMING] < 0.4:
            suggestions.append({
                "category": "话题优化",
                "priority": "low",
                "suggestion": "关联热门话题",
                "details": f"考虑关联当前热门话题：{', '.join(self.trending_topics[:5])}"
            })

        return suggestions

    def _predict_reach(
        self,
        score: float,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """预测触达人数"""
        base_reach = 1000  # 基础触达

        # 根据分数计算乘数
        if score >= 85:
            multiplier = 1000  # 超级病毒式传播
        elif score >= 70:
            multiplier = 100  # 病毒式传播
        elif score >= 50:
            multiplier = 10  # 中等传播
        else:
            multiplier = 1  # 普通传播

        total_reach = base_reach * multiplier

        # 按平台分配
        platforms = platforms or ["tiktok", "instagram", "youtube"]
        reach_by_platform = {}

        for platform in platforms:
            platform_multiplier = self.PLATFORM_CHARACTERISTICS.get(
                platform, {}
            ).get("virality_multiplier", 1.0)

            reach_by_platform[platform] = int(total_reach * platform_multiplier / len(platforms))

        reach_by_platform["total"] = sum(reach_by_platform.values())

        return reach_by_platform

    def _find_comparable_content(
        self,
        features: ContentFeatures,
        score: float
    ) -> List[Dict[str, Any]]:
        """找到可比较的成功内容"""
        # 模拟历史数据
        return [
            {
                "title": "类似主题的病毒视频",
                "platform": "TikTok",
                "views": "1.2M",
                "similarity": 0.85,
                "success_factors": ["强钩子", "热门话题", "幽默"]
            },
            {
                "title": "同类型播客片段",
                "platform": "YouTube Shorts",
                "views": "500K",
                "similarity": 0.78,
                "success_factors": ["专业洞见", "清晰表达"]
            }
        ]

    def _assess_risks(
        self,
        content: Dict[str, Any],
        transcript: str
    ) -> List[str]:
        """评估风险因素"""
        risks = []

        # 检查敏感内容
        sensitive_keywords = ["政治", "宗教", "暴力", "歧视"]
        for keyword in sensitive_keywords:
            if keyword in transcript:
                risks.append(f"⚠️ 内容可能涉及敏感话题：{keyword}")

        # 检查版权风险
        if content.get("has_music"):
            risks.append("⚠️ 包含背景音乐，注意版权问题")

        # 检查时长风险
        duration = content.get("duration", 0)
        if duration > 180:
            risks.append("⚠️ 视频较长，可能影响完播率")

        return risks

    def _recommend_platforms(
        self,
        features: ContentFeatures,
        factor_scores: Dict[ViralFactor, float]
    ) -> List[str]:
        """推荐最佳平台"""
        platform_scores = {}

        for platform, config in self.PLATFORM_CHARACTERISTICS.items():
            score = 0.0

            # 检查时长是否合适
            min_dur, max_dur = config["preferred_duration"]
            if min_dur <= features.duration <= max_dur:
                score += 0.3
            elif features.duration < min_dur * 2 and features.duration > max_dur * 0.5:
                score += 0.15

            # 检查关键因素匹配
            for key_factor in config["key_factors"]:
                score += factor_scores.get(key_factor, 0) * 0.3

            # 应用平台乘数
            score *= config["virality_multiplier"]

            platform_scores[platform] = score

        # 排序返回前5个
        sorted_platforms = sorted(
            platform_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [p[0] for p in sorted_platforms[:5]]

    def _predict_timeline(self, score: float) -> Dict[str, Any]:
        """预测传播时间线"""
        if score >= 85:
            return {
                "initial_surge": "2-4小时",
                "peak_time": "24-48小时",
                "total_cycle": "7-14天",
                "pattern": "explosive",
                "milestones": [
                    {"time": "4小时", "expected_views": "10K+"},
                    {"time": "24小时", "expected_views": "100K+"},
                    {"time": "7天", "expected_views": "1M+"}
                ]
            }
        elif score >= 70:
            return {
                "initial_surge": "6-12小时",
                "peak_time": "48-72小时",
                "total_cycle": "5-7天",
                "pattern": "viral",
                "milestones": [
                    {"time": "12小时", "expected_views": "5K+"},
                    {"time": "48小时", "expected_views": "50K+"},
                    {"time": "7天", "expected_views": "200K+"}
                ]
            }
        elif score >= 50:
            return {
                "initial_surge": "24-48小时",
                "peak_time": "3-5天",
                "total_cycle": "7-10天",
                "pattern": "steady",
                "milestones": [
                    {"time": "24小时", "expected_views": "1K+"},
                    {"time": "5天", "expected_views": "10K+"},
                    {"time": "10天", "expected_views": "30K+"}
                ]
            }
        else:
            return {
                "initial_surge": "48-72小时",
                "peak_time": "5-7天",
                "total_cycle": "7天",
                "pattern": "slow",
                "milestones": [
                    {"time": "48小时", "expected_views": "500+"},
                    {"time": "7天", "expected_views": "2K+"}
                ]
            }

    def _calculate_confidence(self, features: ContentFeatures) -> float:
        """计算预测置信度"""
        # 基于特征完整性计算置信度
        completeness = 0.0

        if features.duration > 0:
            completeness += 0.2
        if features.hook_strength > 0:
            completeness += 0.2
        if features.emotional_peaks > 0:
            completeness += 0.2
        if features.production_quality > 0:
            completeness += 0.2
        if features.topic_trending > 0:
            completeness += 0.2

        # 添加随机波动模拟真实情况
        noise = np.random.uniform(-0.1, 0.1)

        return min(0.95, max(0.5, completeness + noise))

    def compare_variants(
        self,
        variants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        比较多个内容变体的病毒潜力

        Args:
            variants: 内容变体列表

        Returns:
            比较结果
        """
        results = []

        for i, variant in enumerate(variants):
            prediction = self.predict_virality(
                content=variant.get("content", {}),
                transcript=variant.get("transcript", ""),
                audio_features=variant.get("audio_features", {})
            )

            results.append({
                "variant_id": i + 1,
                "name": variant.get("name", f"变体 {i + 1}"),
                "score": prediction.overall_score,
                "confidence": prediction.confidence,
                "best_platforms": prediction.best_platforms[:3]
            })

        # 排序
        results.sort(key=lambda x: x["score"], reverse=True)

        return {
            "ranking": results,
            "winner": results[0] if results else None,
            "recommendation": f"推荐使用 {results[0]['name']}" if results else "无数据"
        }
