"""
情感分析器
分析播客内容的情感变化
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from datetime import timedelta


class EmotionType(Enum):
    """情感类型"""
    JOY = "joy"  # 喜悦
    SADNESS = "sadness"  # 悲伤
    ANGER = "anger"  # 愤怒
    FEAR = "fear"  # 恐惧
    SURPRISE = "surprise"  # 惊讶
    DISGUST = "disgust"  # 厌恶
    TRUST = "trust"  # 信任
    ANTICIPATION = "anticipation"  # 期待
    NEUTRAL = "neutral"  # 中性


class EmotionIntensity(Enum):
    """情感强度"""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5


@dataclass
class EmotionPoint:
    """情感数据点"""
    timestamp: float  # 时间戳（秒）
    primary_emotion: EmotionType
    secondary_emotion: Optional[EmotionType]
    intensity: float  # 0-1
    valence: float  # -1到1，负面到正面
    arousal: float  # 0-1，平静到激动
    confidence: float
    text_snippet: str
    audio_features: Dict[str, float] = field(default_factory=dict)


@dataclass
class EmotionSegment:
    """情感片段"""
    start_time: float
    end_time: float
    dominant_emotion: EmotionType
    avg_intensity: float
    avg_valence: float
    avg_arousal: float
    emotion_distribution: Dict[EmotionType, float]
    key_moments: List[EmotionPoint]
    narrative_phase: str  # 叙事阶段


@dataclass
class EmotionAnalysisResult:
    """情感分析结果"""
    duration: float
    points: List[EmotionPoint]
    segments: List[EmotionSegment]
    overall_sentiment: float  # -1到1
    emotion_summary: Dict[EmotionType, float]
    emotional_arc: List[Dict[str, Any]]
    peak_moments: List[EmotionPoint]
    valley_moments: List[EmotionPoint]
    transitions: List[Dict[str, Any]]
    narrative_structure: Dict[str, Any]


class EmotionAnalyzer:
    """情感分析器"""

    # 情感关键词
    EMOTION_KEYWORDS = {
        EmotionType.JOY: ["开心", "高兴", "快乐", "兴奋", "喜悦", "幸福", "棒", "太好了", "哈哈"],
        EmotionType.SADNESS: ["难过", "悲伤", "伤心", "遗憾", "失望", "沮丧", "唉", "可惜"],
        EmotionType.ANGER: ["生气", "愤怒", "恼火", "气愤", "烦", "讨厌", "可恶"],
        EmotionType.FEAR: ["害怕", "恐惧", "担心", "紧张", "焦虑", "不安", "可怕"],
        EmotionType.SURPRISE: ["惊讶", "震惊", "意外", "没想到", "居然", "竟然", "天哪"],
        EmotionType.DISGUST: ["恶心", "厌恶", "反感", "讨厌", "糟糕"],
        EmotionType.TRUST: ["相信", "信任", "可靠", "放心", "安心", "肯定"],
        EmotionType.ANTICIPATION: ["期待", "希望", "盼望", "等待", "憧憬", "向往"]
    }

    # 强度修饰词
    INTENSITY_MODIFIERS = {
        "very_high": ["非常", "特别", "极其", "超级", "太"],
        "high": ["很", "真的", "相当"],
        "low": ["有点", "稍微", "略微"],
        "very_low": ["不太", "不怎么"]
    }

    def __init__(self):
        self.segment_duration = 30  # 默认30秒一个片段
        self.min_confidence = 0.5

    def analyze(
        self,
        transcript: str,
        audio_features: Optional[Dict[str, Any]] = None,
        timestamps: Optional[List[Dict[str, Any]]] = None
    ) -> EmotionAnalysisResult:
        """
        分析播客情感

        Args:
            transcript: 转录文本
            audio_features: 音频特征
            timestamps: 时间戳信息

        Returns:
            情感分析结果
        """
        # 估算总时长
        duration = self._estimate_duration(transcript, timestamps)

        # 分析文本情感点
        points = self._analyze_text_emotions(transcript, duration)

        # 如果有音频特征，合并分析
        if audio_features:
            points = self._merge_audio_emotions(points, audio_features)

        # 生成情感片段
        segments = self._create_segments(points, duration)

        # 计算整体情感
        overall_sentiment = self._calculate_overall_sentiment(points)

        # 情感分布汇总
        emotion_summary = self._summarize_emotions(points)

        # 提取情感弧线
        emotional_arc = self._extract_emotional_arc(segments)

        # 找出峰值和低谷
        peak_moments = self._find_peak_moments(points)
        valley_moments = self._find_valley_moments(points)

        # 分析情感转换
        transitions = self._analyze_transitions(segments)

        # 叙事结构分析
        narrative_structure = self._analyze_narrative_structure(segments)

        return EmotionAnalysisResult(
            duration=duration,
            points=points,
            segments=segments,
            overall_sentiment=overall_sentiment,
            emotion_summary=emotion_summary,
            emotional_arc=emotional_arc,
            peak_moments=peak_moments,
            valley_moments=valley_moments,
            transitions=transitions,
            narrative_structure=narrative_structure
        )

    def _estimate_duration(
        self,
        transcript: str,
        timestamps: Optional[List[Dict[str, Any]]]
    ) -> float:
        """估算时长"""
        if timestamps and len(timestamps) > 0:
            return max(ts.get("end", 0) for ts in timestamps)

        # 基于文字数量估算（假设每分钟150-200字）
        char_count = len(transcript)
        return char_count / 175 * 60  # 秒

    def _analyze_text_emotions(
        self,
        transcript: str,
        duration: float
    ) -> List[EmotionPoint]:
        """分析文本情感"""
        points = []

        # 将文本分成句子
        sentences = self._split_sentences(transcript)
        time_per_sentence = duration / len(sentences) if sentences else 1

        for i, sentence in enumerate(sentences):
            timestamp = i * time_per_sentence

            # 分析句子情感
            emotion_scores = self._score_emotions(sentence)
            primary_emotion, secondary_emotion = self._get_top_emotions(emotion_scores)
            intensity = self._calculate_intensity(sentence, emotion_scores)
            valence = self._calculate_valence(emotion_scores)
            arousal = self._calculate_arousal(sentence, emotion_scores)

            point = EmotionPoint(
                timestamp=timestamp,
                primary_emotion=primary_emotion,
                secondary_emotion=secondary_emotion,
                intensity=intensity,
                valence=valence,
                arousal=arousal,
                confidence=self._calculate_confidence(emotion_scores),
                text_snippet=sentence[:100]
            )

            points.append(point)

        return points

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        import re
        # 按中文和英文标点分割
        sentences = re.split(r'[。！？.!?]', text)
        return [s.strip() for s in sentences if s.strip()]

    def _score_emotions(self, text: str) -> Dict[EmotionType, float]:
        """计算各情感得分"""
        scores = {emotion: 0.0 for emotion in EmotionType}

        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[emotion] += 1.0

                    # 检查强度修饰
                    for modifier_level, modifiers in self.INTENSITY_MODIFIERS.items():
                        for modifier in modifiers:
                            if modifier + keyword in text:
                                if modifier_level == "very_high":
                                    scores[emotion] += 0.5
                                elif modifier_level == "high":
                                    scores[emotion] += 0.3
                                elif modifier_level == "low":
                                    scores[emotion] -= 0.2
                                elif modifier_level == "very_low":
                                    scores[emotion] -= 0.4

        # 归一化
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        else:
            scores[EmotionType.NEUTRAL] = 1.0

        return scores

    def _get_top_emotions(
        self,
        scores: Dict[EmotionType, float]
    ) -> Tuple[EmotionType, Optional[EmotionType]]:
        """获取主要和次要情感"""
        sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        primary = sorted_emotions[0][0] if sorted_emotions[0][1] > 0 else EmotionType.NEUTRAL
        secondary = sorted_emotions[1][0] if len(sorted_emotions) > 1 and sorted_emotions[1][1] > 0.1 else None

        return primary, secondary

    def _calculate_intensity(
        self,
        text: str,
        scores: Dict[EmotionType, float]
    ) -> float:
        """计算情感强度"""
        base_intensity = max(scores.values()) if scores else 0

        # 检查感叹号和重复标点
        exclamation_count = text.count("！") + text.count("!")
        base_intensity += min(0.2, exclamation_count * 0.1)

        # 检查强度词
        for modifier_level, modifiers in self.INTENSITY_MODIFIERS.items():
            for modifier in modifiers:
                if modifier in text:
                    if modifier_level == "very_high":
                        base_intensity += 0.2
                    elif modifier_level == "high":
                        base_intensity += 0.1

        return min(1.0, base_intensity)

    def _calculate_valence(self, scores: Dict[EmotionType, float]) -> float:
        """计算情感效价（正负）"""
        positive_emotions = [EmotionType.JOY, EmotionType.TRUST, EmotionType.ANTICIPATION]
        negative_emotions = [EmotionType.SADNESS, EmotionType.ANGER, EmotionType.FEAR, EmotionType.DISGUST]

        positive_score = sum(scores.get(e, 0) for e in positive_emotions)
        negative_score = sum(scores.get(e, 0) for e in negative_emotions)

        if positive_score + negative_score == 0:
            return 0

        return (positive_score - negative_score) / (positive_score + negative_score)

    def _calculate_arousal(
        self,
        text: str,
        scores: Dict[EmotionType, float]
    ) -> float:
        """计算唤醒度（激动程度）"""
        high_arousal = [EmotionType.ANGER, EmotionType.FEAR, EmotionType.JOY, EmotionType.SURPRISE]
        low_arousal = [EmotionType.SADNESS, EmotionType.DISGUST]

        high_score = sum(scores.get(e, 0) for e in high_arousal)
        low_score = sum(scores.get(e, 0) for e in low_arousal)

        arousal = 0.5 + (high_score - low_score) * 0.5

        # 感叹号增加唤醒度
        exclamation_count = text.count("！") + text.count("!")
        arousal += min(0.2, exclamation_count * 0.1)

        return min(1.0, max(0.0, arousal))

    def _calculate_confidence(self, scores: Dict[EmotionType, float]) -> float:
        """计算置信度"""
        max_score = max(scores.values()) if scores else 0

        if max_score > 0.5:
            return 0.9
        elif max_score > 0.3:
            return 0.7
        elif max_score > 0.1:
            return 0.5
        else:
            return 0.3

    def _merge_audio_emotions(
        self,
        text_points: List[EmotionPoint],
        audio_features: Dict[str, Any]
    ) -> List[EmotionPoint]:
        """合并音频情感特征"""
        # 获取音频情感指标
        energy_curve = audio_features.get("energy_curve", [])
        pitch_curve = audio_features.get("pitch_curve", [])

        for point in text_points:
            # 找到对应时间的音频特征
            audio_energy = self._get_audio_value_at_time(energy_curve, point.timestamp)
            audio_pitch = self._get_audio_value_at_time(pitch_curve, point.timestamp)

            # 更新音频特征
            point.audio_features = {
                "energy": audio_energy,
                "pitch": audio_pitch
            }

            # 调整唤醒度
            if audio_energy > 0.7:
                point.arousal = min(1.0, point.arousal + 0.2)
            elif audio_energy < 0.3:
                point.arousal = max(0.0, point.arousal - 0.1)

        return text_points

    def _get_audio_value_at_time(
        self,
        curve: List[Dict[str, float]],
        timestamp: float
    ) -> float:
        """获取特定时间的音频值"""
        if not curve:
            return 0.5

        # 找到最近的点
        closest = min(curve, key=lambda x: abs(x.get("time", 0) - timestamp))
        return closest.get("energy", closest.get("pitch", 0.5))

    def _create_segments(
        self,
        points: List[EmotionPoint],
        duration: float
    ) -> List[EmotionSegment]:
        """创建情感片段"""
        segments = []
        segment_count = max(1, int(duration / self.segment_duration))

        for i in range(segment_count):
            start_time = i * self.segment_duration
            end_time = min((i + 1) * self.segment_duration, duration)

            # 获取该片段内的点
            segment_points = [
                p for p in points
                if start_time <= p.timestamp < end_time
            ]

            if not segment_points:
                continue

            # 计算统计
            emotion_counts = {}
            for p in segment_points:
                emotion_counts[p.primary_emotion] = emotion_counts.get(p.primary_emotion, 0) + 1

            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]

            # 计算平均值
            avg_intensity = np.mean([p.intensity for p in segment_points])
            avg_valence = np.mean([p.valence for p in segment_points])
            avg_arousal = np.mean([p.arousal for p in segment_points])

            # 情感分布
            total = len(segment_points)
            emotion_distribution = {
                emotion: count / total
                for emotion, count in emotion_counts.items()
            }

            # 关键时刻（强度最高的点）
            key_moments = sorted(segment_points, key=lambda x: x.intensity, reverse=True)[:3]

            # 叙事阶段
            narrative_phase = self._determine_narrative_phase(i, segment_count)

            segment = EmotionSegment(
                start_time=start_time,
                end_time=end_time,
                dominant_emotion=dominant_emotion,
                avg_intensity=avg_intensity,
                avg_valence=avg_valence,
                avg_arousal=avg_arousal,
                emotion_distribution=emotion_distribution,
                key_moments=key_moments,
                narrative_phase=narrative_phase
            )

            segments.append(segment)

        return segments

    def _determine_narrative_phase(self, index: int, total: int) -> str:
        """确定叙事阶段"""
        position = index / total

        if position < 0.15:
            return "开场"
        elif position < 0.30:
            return "铺垫"
        elif position < 0.50:
            return "发展"
        elif position < 0.75:
            return "高潮"
        elif position < 0.90:
            return "收尾"
        else:
            return "结束"

    def _calculate_overall_sentiment(self, points: List[EmotionPoint]) -> float:
        """计算整体情感"""
        if not points:
            return 0

        return np.mean([p.valence for p in points])

    def _summarize_emotions(self, points: List[EmotionPoint]) -> Dict[EmotionType, float]:
        """汇总情感分布"""
        counts = {}
        for point in points:
            counts[point.primary_emotion] = counts.get(point.primary_emotion, 0) + 1

        total = len(points)
        return {emotion: count / total for emotion, count in counts.items()}

    def _extract_emotional_arc(self, segments: List[EmotionSegment]) -> List[Dict[str, Any]]:
        """提取情感弧线"""
        arc = []

        for segment in segments:
            arc.append({
                "time": segment.start_time,
                "end_time": segment.end_time,
                "valence": segment.avg_valence,
                "arousal": segment.avg_arousal,
                "intensity": segment.avg_intensity,
                "dominant_emotion": segment.dominant_emotion.value,
                "phase": segment.narrative_phase
            })

        return arc

    def _find_peak_moments(self, points: List[EmotionPoint]) -> List[EmotionPoint]:
        """找出情感峰值"""
        if not points:
            return []

        # 按强度排序，取前5
        sorted_points = sorted(points, key=lambda x: x.intensity, reverse=True)
        return sorted_points[:5]

    def _find_valley_moments(self, points: List[EmotionPoint]) -> List[EmotionPoint]:
        """找出情感低谷"""
        if not points:
            return []

        # 按效价排序，取最负面的5个
        sorted_points = sorted(points, key=lambda x: x.valence)
        return sorted_points[:5]

    def _analyze_transitions(self, segments: List[EmotionSegment]) -> List[Dict[str, Any]]:
        """分析情感转换"""
        transitions = []

        for i in range(1, len(segments)):
            prev_segment = segments[i - 1]
            curr_segment = segments[i]

            if prev_segment.dominant_emotion != curr_segment.dominant_emotion:
                valence_change = curr_segment.avg_valence - prev_segment.avg_valence
                arousal_change = curr_segment.avg_arousal - prev_segment.avg_arousal

                transitions.append({
                    "time": curr_segment.start_time,
                    "from_emotion": prev_segment.dominant_emotion.value,
                    "to_emotion": curr_segment.dominant_emotion.value,
                    "valence_change": valence_change,
                    "arousal_change": arousal_change,
                    "transition_type": self._classify_transition(valence_change, arousal_change)
                })

        return transitions

    def _classify_transition(self, valence_change: float, arousal_change: float) -> str:
        """分类转换类型"""
        if valence_change > 0.3 and arousal_change > 0.2:
            return "突然振奋"
        elif valence_change < -0.3 and arousal_change > 0.2:
            return "情绪爆发"
        elif valence_change > 0.3 and arousal_change < -0.2:
            return "平静喜悦"
        elif valence_change < -0.3 and arousal_change < -0.2:
            return "逐渐低落"
        elif abs(valence_change) < 0.1 and abs(arousal_change) < 0.1:
            return "平稳过渡"
        else:
            return "自然转换"

    def _analyze_narrative_structure(self, segments: List[EmotionSegment]) -> Dict[str, Any]:
        """分析叙事结构"""
        if not segments:
            return {}

        # 找出各阶段
        phases = {}
        for segment in segments:
            phase = segment.narrative_phase
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(segment)

        # 分析结构
        return {
            "phases": list(phases.keys()),
            "phase_details": {
                phase: {
                    "duration": sum(s.end_time - s.start_time for s in segs),
                    "avg_intensity": np.mean([s.avg_intensity for s in segs]),
                    "dominant_emotion": max(
                        set(s.dominant_emotion for s in segs),
                        key=lambda e: sum(1 for s in segs if s.dominant_emotion == e)
                    ).value
                }
                for phase, segs in phases.items()
            },
            "arc_type": self._determine_arc_type(segments),
            "emotional_range": max(s.avg_valence for s in segments) - min(s.avg_valence for s in segments)
        }

    def _determine_arc_type(self, segments: List[EmotionSegment]) -> str:
        """确定情感弧类型"""
        if len(segments) < 3:
            return "简短"

        valences = [s.avg_valence for s in segments]

        # 检测模式
        mid_point = len(valences) // 2

        start_avg = np.mean(valences[:mid_point])
        end_avg = np.mean(valences[mid_point:])
        middle_max = max(valences[mid_point - 2:mid_point + 2]) if mid_point >= 2 else max(valences)

        if middle_max > start_avg and middle_max > end_avg:
            return "山峰型"
        elif start_avg > end_avg:
            return "下降型"
        elif start_avg < end_avg:
            return "上升型"
        else:
            return "平稳型"
