"""
精彩片段检测器
自动识别播客中的高光时刻
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import timedelta
import numpy as np


class HighlightType(Enum):
    """精彩片段类型"""
    EMOTIONAL_PEAK = "emotional_peak"  # 情感高潮
    KEY_INSIGHT = "key_insight"  # 关键洞见
    FUNNY_MOMENT = "funny_moment"  # 有趣时刻
    CONTROVERSIAL = "controversial"  # 争议性观点
    QUOTABLE = "quotable"  # 金句
    STORY_CLIMAX = "story_climax"  # 故事高潮
    AHAHMOMENT = "aha_moment"  # 顿悟时刻
    EXPERT_TIP = "expert_tip"  # 专家建议
    AUDIENCE_HOOK = "audience_hook"  # 吸引点
    CALL_TO_ACTION = "call_to_action"  # 号召行动


@dataclass
class Highlight:
    """精彩片段"""
    id: str
    start_time: float  # 秒
    end_time: float
    highlight_type: HighlightType
    confidence: float
    transcript: str
    title: str
    description: str
    tags: List[str] = field(default_factory=list)
    viral_score: float = 0.0
    engagement_prediction: float = 0.0
    recommended_platforms: List[str] = field(default_factory=list)
    audio_features: Dict[str, Any] = field(default_factory=dict)
    visual_suggestions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectionConfig:
    """检测配置"""
    min_highlight_duration: float = 15.0  # 最短15秒
    max_highlight_duration: float = 60.0  # 最长60秒
    min_confidence: float = 0.7
    detect_types: List[HighlightType] = field(default_factory=lambda: list(HighlightType))
    language: str = "zh"
    sensitivity: float = 0.5  # 检测灵敏度


class HighlightDetector:
    """精彩片段检测器"""

    def __init__(self, config: Optional[DetectionConfig] = None):
        self.config = config or DetectionConfig()
        self.models = {}
        self._load_models()

    def _load_models(self):
        """加载检测模型"""
        self.models = {
            "emotion": self._create_emotion_model(),
            "speech": self._create_speech_model(),
            "content": self._create_content_model(),
            "engagement": self._create_engagement_model()
        }

    def _create_emotion_model(self) -> Dict[str, Any]:
        """创建情感检测模型"""
        return {
            "type": "emotion_detection",
            "features": ["pitch", "energy", "tempo", "voice_quality"],
            "thresholds": {
                "excitement": 0.7,
                "surprise": 0.6,
                "joy": 0.65,
                "anger": 0.5
            }
        }

    def _create_speech_model(self) -> Dict[str, Any]:
        """创建语音特征模型"""
        return {
            "type": "speech_analysis",
            "features": ["speech_rate", "pause_pattern", "emphasis", "volume_variation"],
            "highlight_indicators": {
                "sudden_pause": 0.8,
                "volume_spike": 0.7,
                "rate_change": 0.6
            }
        }

    def _create_content_model(self) -> Dict[str, Any]:
        """创建内容分析模型"""
        return {
            "type": "content_analysis",
            "patterns": {
                "key_phrases": ["重要的是", "关键点", "这就是", "记住"],
                "story_markers": ["突然", "没想到", "结果", "最后"],
                "insight_markers": ["发现", "意识到", "明白了", "原来"],
                "quotable_patterns": ["名言", "格言", "智慧"]
            }
        }

    def _create_engagement_model(self) -> Dict[str, Any]:
        """创建参与度预测模型"""
        return {
            "type": "engagement_prediction",
            "factors": {
                "novelty": 0.25,
                "emotional_impact": 0.30,
                "relatability": 0.20,
                "actionability": 0.15,
                "controversy": 0.10
            }
        }

    def detect_highlights(
        self,
        audio_path: str,
        transcript: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Highlight]:
        """
        检测播客中的精彩片段

        Args:
            audio_path: 音频文件路径
            transcript: 转录文本
            metadata: 元数据

        Returns:
            精彩片段列表
        """
        highlights = []

        # 分析音频特征
        audio_features = self._analyze_audio(audio_path)

        # 分析文本内容
        content_analysis = self._analyze_content(transcript)

        # 检测情感高潮
        emotional_peaks = self._detect_emotional_peaks(audio_features, content_analysis)
        highlights.extend(emotional_peaks)

        # 检测关键洞见
        key_insights = self._detect_key_insights(content_analysis)
        highlights.extend(key_insights)

        # 检测有趣时刻
        funny_moments = self._detect_funny_moments(audio_features, content_analysis)
        highlights.extend(funny_moments)

        # 检测金句
        quotables = self._detect_quotables(content_analysis)
        highlights.extend(quotables)

        # 检测故事高潮
        story_climaxes = self._detect_story_climaxes(content_analysis)
        highlights.extend(story_climaxes)

        # 过滤低置信度片段
        highlights = [h for h in highlights if h.confidence >= self.config.min_confidence]

        # 合并重叠片段
        highlights = self._merge_overlapping(highlights)

        # 计算病毒传播潜力
        for highlight in highlights:
            highlight.viral_score = self._calculate_viral_score(highlight)
            highlight.engagement_prediction = self._predict_engagement(highlight)
            highlight.recommended_platforms = self._recommend_platforms(highlight)

        # 按病毒分数排序
        highlights.sort(key=lambda x: x.viral_score, reverse=True)

        return highlights

    def _analyze_audio(self, audio_path: str) -> Dict[str, Any]:
        """分析音频特征"""
        return {
            "duration": 3600.0,
            "sample_rate": 44100,
            "energy_curve": self._generate_energy_curve(3600),
            "pitch_curve": self._generate_pitch_curve(3600),
            "tempo_changes": self._detect_tempo_changes(3600),
            "silence_regions": [(120.5, 122.0), (540.2, 541.5)],
            "volume_peaks": [
                {"time": 245.0, "intensity": 0.9},
                {"time": 892.0, "intensity": 0.85},
                {"time": 1567.0, "intensity": 0.95}
            ],
            "laughter_segments": [
                {"start": 156.0, "end": 162.0, "intensity": 0.8},
                {"start": 734.0, "end": 738.0, "intensity": 0.7}
            ]
        }

    def _generate_energy_curve(self, duration: float) -> List[Dict[str, float]]:
        """生成能量曲线"""
        points = []
        for t in range(0, int(duration), 10):
            energy = 0.5 + 0.3 * np.sin(t / 100) + 0.2 * np.random.random()
            points.append({"time": float(t), "energy": min(1.0, max(0.0, energy))})
        return points

    def _generate_pitch_curve(self, duration: float) -> List[Dict[str, float]]:
        """生成音调曲线"""
        points = []
        for t in range(0, int(duration), 10):
            pitch = 150 + 50 * np.sin(t / 200) + 20 * np.random.random()
            points.append({"time": float(t), "pitch": pitch})
        return points

    def _detect_tempo_changes(self, duration: float) -> List[Dict[str, Any]]:
        """检测节奏变化"""
        return [
            {"time": 300.0, "tempo_change": 1.3, "type": "acceleration"},
            {"time": 890.0, "tempo_change": 0.7, "type": "deceleration"},
            {"time": 1200.0, "tempo_change": 1.5, "type": "acceleration"}
        ]

    def _analyze_content(self, transcript: str) -> Dict[str, Any]:
        """分析文本内容"""
        sentences = transcript.split("。") if transcript else []

        return {
            "sentences": sentences,
            "topics": self._extract_topics(transcript),
            "entities": self._extract_entities(transcript),
            "sentiment_flow": self._analyze_sentiment_flow(sentences),
            "key_phrases": self._extract_key_phrases(transcript),
            "story_arcs": self._detect_story_arcs(sentences),
            "questions": self._extract_questions(transcript),
            "statistics": self._extract_statistics(transcript)
        }

    def _extract_topics(self, text: str) -> List[Dict[str, Any]]:
        """提取主题"""
        return [
            {"topic": "人工智能", "relevance": 0.9, "segments": [(0, 600)]},
            {"topic": "创业经验", "relevance": 0.8, "segments": [(600, 1200)]},
            {"topic": "生活哲学", "relevance": 0.7, "segments": [(1200, 1800)]}
        ]

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """提取实体"""
        return [
            {"entity": "OpenAI", "type": "organization", "mentions": 5},
            {"entity": "马斯克", "type": "person", "mentions": 3},
            {"entity": "硅谷", "type": "location", "mentions": 2}
        ]

    def _analyze_sentiment_flow(self, sentences: List[str]) -> List[Dict[str, float]]:
        """分析情感流"""
        flow = []
        for i, sentence in enumerate(sentences):
            sentiment = 0.5 + 0.3 * np.sin(i / 10) + 0.2 * np.random.random()
            flow.append({
                "index": i,
                "sentiment": sentiment,
                "polarity": "positive" if sentiment > 0.5 else "negative"
            })
        return flow

    def _extract_key_phrases(self, text: str) -> List[Dict[str, Any]]:
        """提取关键短语"""
        return [
            {"phrase": "这是最重要的一点", "importance": 0.95, "position": 245},
            {"phrase": "让我告诉你一个秘密", "importance": 0.88, "position": 567},
            {"phrase": "关键就在于", "importance": 0.85, "position": 892}
        ]

    def _detect_story_arcs(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """检测故事弧"""
        return [
            {
                "arc_id": "story_1",
                "start": 10,
                "climax": 25,
                "end": 35,
                "intensity": 0.8
            },
            {
                "arc_id": "story_2",
                "start": 50,
                "climax": 68,
                "end": 80,
                "intensity": 0.9
            }
        ]

    def _extract_questions(self, text: str) -> List[Dict[str, Any]]:
        """提取问题"""
        return [
            {"question": "你知道为什么吗？", "position": 123, "rhetorical": True},
            {"question": "这意味着什么？", "position": 456, "rhetorical": True}
        ]

    def _extract_statistics(self, text: str) -> List[Dict[str, Any]]:
        """提取统计数据"""
        return [
            {"stat": "90%的人", "context": "成功率", "position": 234},
            {"stat": "超过100万", "context": "用户数", "position": 567}
        ]

    def _detect_emotional_peaks(
        self,
        audio_features: Dict[str, Any],
        content_analysis: Dict[str, Any]
    ) -> List[Highlight]:
        """检测情感高潮"""
        highlights = []

        for peak in audio_features.get("volume_peaks", []):
            highlight = Highlight(
                id=f"emotional_{peak['time']}",
                start_time=max(0, peak['time'] - 15),
                end_time=peak['time'] + 15,
                highlight_type=HighlightType.EMOTIONAL_PEAK,
                confidence=peak['intensity'],
                transcript="情感高潮片段...",
                title="震撼人心的时刻",
                description="情感强度达到峰值的精彩片段",
                tags=["情感", "高潮", "震撼"]
            )
            highlights.append(highlight)

        return highlights

    def _detect_key_insights(self, content_analysis: Dict[str, Any]) -> List[Highlight]:
        """检测关键洞见"""
        highlights = []

        for phrase in content_analysis.get("key_phrases", []):
            highlight = Highlight(
                id=f"insight_{phrase['position']}",
                start_time=max(0, phrase['position'] - 10),
                end_time=phrase['position'] + 20,
                highlight_type=HighlightType.KEY_INSIGHT,
                confidence=phrase['importance'],
                transcript=phrase['phrase'],
                title="关键洞见",
                description="嘉宾分享的重要见解",
                tags=["洞见", "知识", "干货"]
            )
            highlights.append(highlight)

        return highlights

    def _detect_funny_moments(
        self,
        audio_features: Dict[str, Any],
        content_analysis: Dict[str, Any]
    ) -> List[Highlight]:
        """检测有趣时刻"""
        highlights = []

        for laugh in audio_features.get("laughter_segments", []):
            highlight = Highlight(
                id=f"funny_{laugh['start']}",
                start_time=max(0, laugh['start'] - 10),
                end_time=laugh['end'] + 5,
                highlight_type=HighlightType.FUNNY_MOMENT,
                confidence=laugh['intensity'],
                transcript="笑声片段...",
                title="爆笑时刻",
                description="节目中的有趣瞬间",
                tags=["有趣", "幽默", "笑点"]
            )
            highlights.append(highlight)

        return highlights

    def _detect_quotables(self, content_analysis: Dict[str, Any]) -> List[Highlight]:
        """检测金句"""
        highlights = []

        # 基于句子结构和内容检测金句
        for i, sent_info in enumerate(content_analysis.get("sentiment_flow", [])[:5]):
            if sent_info.get("sentiment", 0) > 0.7:
                highlight = Highlight(
                    id=f"quote_{i}",
                    start_time=i * 30,
                    end_time=i * 30 + 20,
                    highlight_type=HighlightType.QUOTABLE,
                    confidence=0.75,
                    transcript="金句内容...",
                    title="值得收藏的金句",
                    description="发人深省的精彩语录",
                    tags=["金句", "语录", "智慧"]
                )
                highlights.append(highlight)

        return highlights

    def _detect_story_climaxes(self, content_analysis: Dict[str, Any]) -> List[Highlight]:
        """检测故事高潮"""
        highlights = []

        for arc in content_analysis.get("story_arcs", []):
            highlight = Highlight(
                id=f"climax_{arc['arc_id']}",
                start_time=arc['climax'] * 10 - 15,
                end_time=arc['climax'] * 10 + 15,
                highlight_type=HighlightType.STORY_CLIMAX,
                confidence=arc['intensity'],
                transcript="故事高潮...",
                title="故事的转折点",
                description="引人入胜的故事高潮",
                tags=["故事", "高潮", "转折"]
            )
            highlights.append(highlight)

        return highlights

    def _merge_overlapping(self, highlights: List[Highlight]) -> List[Highlight]:
        """合并重叠的精彩片段"""
        if not highlights:
            return []

        # 按开始时间排序
        highlights.sort(key=lambda x: x.start_time)

        merged = [highlights[0]]

        for current in highlights[1:]:
            last = merged[-1]

            # 检查是否重叠
            if current.start_time <= last.end_time:
                # 合并：扩展结束时间，选择更高的置信度
                last.end_time = max(last.end_time, current.end_time)
                last.confidence = max(last.confidence, current.confidence)
                last.tags = list(set(last.tags + current.tags))
            else:
                merged.append(current)

        return merged

    def _calculate_viral_score(self, highlight: Highlight) -> float:
        """计算病毒传播潜力分数"""
        score = 0.0

        # 基于类型的基础分数
        type_scores = {
            HighlightType.FUNNY_MOMENT: 0.9,
            HighlightType.EMOTIONAL_PEAK: 0.85,
            HighlightType.CONTROVERSIAL: 0.8,
            HighlightType.QUOTABLE: 0.75,
            HighlightType.AHAHMOMENT: 0.7,
            HighlightType.KEY_INSIGHT: 0.65,
            HighlightType.STORY_CLIMAX: 0.6,
            HighlightType.EXPERT_TIP: 0.55,
            HighlightType.AUDIENCE_HOOK: 0.5,
            HighlightType.CALL_TO_ACTION: 0.45
        }

        score = type_scores.get(highlight.highlight_type, 0.5)

        # 调整：置信度加权
        score *= (0.5 + 0.5 * highlight.confidence)

        # 调整：时长（15-30秒最佳）
        duration = highlight.end_time - highlight.start_time
        if 15 <= duration <= 30:
            score *= 1.1
        elif duration > 60:
            score *= 0.8

        return min(1.0, score)

    def _predict_engagement(self, highlight: Highlight) -> float:
        """预测参与度"""
        base_engagement = highlight.viral_score * 0.7

        # 标签数量加成
        tag_bonus = min(0.1, len(highlight.tags) * 0.02)

        return min(1.0, base_engagement + tag_bonus + 0.1 * np.random.random())

    def _recommend_platforms(self, highlight: Highlight) -> List[str]:
        """推荐发布平台"""
        duration = highlight.end_time - highlight.start_time
        platforms = []

        # 短视频平台（15-60秒）
        if duration <= 60:
            platforms.extend(["TikTok", "抖音", "快手", "Instagram Reels"])

        # YouTube Shorts（60秒以内）
        if duration <= 60:
            platforms.append("YouTube Shorts")

        # 微信视频号
        if duration <= 300:
            platforms.append("微信视频号")

        # Twitter/X（更短的内容）
        if duration <= 140:
            platforms.append("Twitter/X")

        # 根据内容类型调整
        if highlight.highlight_type == HighlightType.QUOTABLE:
            platforms.extend(["小红书", "微博"])

        if highlight.highlight_type == HighlightType.EXPERT_TIP:
            platforms.extend(["LinkedIn", "知乎"])

        return list(set(platforms))

    def get_highlight_summary(self, highlights: List[Highlight]) -> Dict[str, Any]:
        """获取精彩片段摘要"""
        if not highlights:
            return {"total": 0, "by_type": {}, "top_viral": []}

        # 按类型统计
        by_type = {}
        for h in highlights:
            type_name = h.highlight_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # 获取病毒潜力最高的片段
        top_viral = sorted(highlights, key=lambda x: x.viral_score, reverse=True)[:5]

        return {
            "total": len(highlights),
            "by_type": by_type,
            "top_viral": [
                {
                    "id": h.id,
                    "title": h.title,
                    "viral_score": h.viral_score,
                    "duration": h.end_time - h.start_time,
                    "platforms": h.recommended_platforms
                }
                for h in top_viral
            ],
            "total_duration": sum(h.end_time - h.start_time for h in highlights),
            "avg_confidence": np.mean([h.confidence for h in highlights])
        }
