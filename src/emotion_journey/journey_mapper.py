"""
旅程映射器
将情感分析结果映射为可视化的旅程图
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class JourneyPhase(Enum):
    """旅程阶段"""
    HOOK = "hook"  # 钩子
    SETUP = "setup"  # 设定
    RISING = "rising"  # 上升
    CLIMAX = "climax"  # 高潮
    FALLING = "falling"  # 下降
    RESOLUTION = "resolution"  # 解决
    CALL_TO_ACTION = "call_to_action"  # 号召


@dataclass
class JourneyPoint:
    """旅程点"""
    timestamp: float
    phase: JourneyPhase
    emotional_intensity: float
    engagement_level: float
    key_content: str
    annotations: List[str] = field(default_factory=list)


@dataclass
class JourneyMap:
    """旅程图"""
    title: str
    duration: float
    points: List[JourneyPoint]
    phases: List[Dict[str, Any]]
    highlights: List[Dict[str, Any]]
    low_points: List[Dict[str, Any]]
    overall_rating: float
    engagement_curve: List[Dict[str, float]]
    recommendations: List[str]


class JourneyMapper:
    """旅程映射器"""

    # 理想的情感曲线（叙事弧）
    IDEAL_CURVES = {
        "standard": [0.3, 0.4, 0.5, 0.6, 0.8, 0.9, 0.7, 0.5],
        "thriller": [0.5, 0.6, 0.7, 0.5, 0.8, 1.0, 0.9, 0.6],
        "documentary": [0.4, 0.5, 0.6, 0.7, 0.7, 0.8, 0.7, 0.5],
        "interview": [0.4, 0.5, 0.6, 0.7, 0.8, 0.7, 0.6, 0.5],
        "educational": [0.4, 0.5, 0.6, 0.7, 0.6, 0.7, 0.8, 0.6]
    }

    def __init__(self):
        self.phase_thresholds = {
            "intensity_high": 0.7,
            "intensity_low": 0.3,
            "engagement_critical": 0.4
        }

    def create_journey_map(
        self,
        emotion_analysis: Any,  # EmotionAnalysisResult
        title: str,
        content_type: str = "standard"
    ) -> JourneyMap:
        """
        创建旅程图

        Args:
            emotion_analysis: 情感分析结果
            title: 标题
            content_type: 内容类型

        Returns:
            旅程图
        """
        duration = emotion_analysis.duration

        # 创建旅程点
        points = self._create_journey_points(emotion_analysis)

        # 识别阶段
        phases = self._identify_phases(points, duration)

        # 找出高光和低点
        highlights = self._find_highlights(points)
        low_points = self._find_low_points(points)

        # 生成参与度曲线
        engagement_curve = self._generate_engagement_curve(points, duration)

        # 计算整体评分
        overall_rating = self._calculate_overall_rating(
            points, engagement_curve, content_type
        )

        # 生成建议
        recommendations = self._generate_recommendations(
            points, phases, highlights, low_points, content_type
        )

        return JourneyMap(
            title=title,
            duration=duration,
            points=points,
            phases=phases,
            highlights=highlights,
            low_points=low_points,
            overall_rating=overall_rating,
            engagement_curve=engagement_curve,
            recommendations=recommendations
        )

    def _create_journey_points(self, emotion_analysis: Any) -> List[JourneyPoint]:
        """创建旅程点"""
        points = []

        for segment in emotion_analysis.segments:
            # 确定阶段
            phase = self._determine_phase(
                segment.start_time,
                emotion_analysis.duration,
                segment.avg_intensity
            )

            # 计算参与度
            engagement = self._calculate_engagement(
                segment.avg_intensity,
                segment.avg_arousal,
                segment.avg_valence
            )

            # 获取关键内容
            key_content = segment.key_moments[0].text_snippet if segment.key_moments else ""

            point = JourneyPoint(
                timestamp=segment.start_time,
                phase=phase,
                emotional_intensity=segment.avg_intensity,
                engagement_level=engagement,
                key_content=key_content,
                annotations=[
                    f"主导情感: {segment.dominant_emotion.value}",
                    f"叙事阶段: {segment.narrative_phase}"
                ]
            )

            points.append(point)

        return points

    def _determine_phase(
        self,
        timestamp: float,
        total_duration: float,
        intensity: float
    ) -> JourneyPhase:
        """确定旅程阶段"""
        position = timestamp / total_duration if total_duration > 0 else 0

        if position < 0.05:
            return JourneyPhase.HOOK
        elif position < 0.15:
            return JourneyPhase.SETUP
        elif position < 0.40:
            return JourneyPhase.RISING
        elif position < 0.65:
            if intensity > self.phase_thresholds["intensity_high"]:
                return JourneyPhase.CLIMAX
            return JourneyPhase.RISING
        elif position < 0.85:
            return JourneyPhase.FALLING
        elif position < 0.95:
            return JourneyPhase.RESOLUTION
        else:
            return JourneyPhase.CALL_TO_ACTION

    def _calculate_engagement(
        self,
        intensity: float,
        arousal: float,
        valence: float
    ) -> float:
        """计算参与度"""
        # 参与度 = 强度权重 + 唤醒度权重 + 情感极端度
        emotional_extremity = abs(valence)

        engagement = (
            intensity * 0.4 +
            arousal * 0.35 +
            emotional_extremity * 0.25
        )

        return min(1.0, engagement)

    def _identify_phases(
        self,
        points: List[JourneyPoint],
        duration: float
    ) -> List[Dict[str, Any]]:
        """识别并汇总阶段"""
        phases = []
        current_phase = None
        phase_start = 0

        for point in points:
            if point.phase != current_phase:
                if current_phase is not None:
                    phases.append({
                        "phase": current_phase.value,
                        "start_time": phase_start,
                        "end_time": point.timestamp,
                        "duration": point.timestamp - phase_start
                    })

                current_phase = point.phase
                phase_start = point.timestamp

        # 添加最后一个阶段
        if current_phase is not None:
            phases.append({
                "phase": current_phase.value,
                "start_time": phase_start,
                "end_time": duration,
                "duration": duration - phase_start
            })

        return phases

    def _find_highlights(self, points: List[JourneyPoint]) -> List[Dict[str, Any]]:
        """找出高光时刻"""
        # 按参与度排序
        sorted_points = sorted(points, key=lambda x: x.engagement_level, reverse=True)

        highlights = []
        for point in sorted_points[:5]:
            if point.engagement_level > self.phase_thresholds["intensity_high"]:
                highlights.append({
                    "timestamp": point.timestamp,
                    "intensity": point.emotional_intensity,
                    "engagement": point.engagement_level,
                    "phase": point.phase.value,
                    "content": point.key_content,
                    "reason": "高参与度时刻"
                })

        return highlights

    def _find_low_points(self, points: List[JourneyPoint]) -> List[Dict[str, Any]]:
        """找出低点"""
        low_points = []

        for point in points:
            if point.engagement_level < self.phase_thresholds["engagement_critical"]:
                low_points.append({
                    "timestamp": point.timestamp,
                    "intensity": point.emotional_intensity,
                    "engagement": point.engagement_level,
                    "phase": point.phase.value,
                    "content": point.key_content,
                    "issue": "参与度较低"
                })

        return low_points

    def _generate_engagement_curve(
        self,
        points: List[JourneyPoint],
        duration: float
    ) -> List[Dict[str, float]]:
        """生成参与度曲线"""
        curve = []

        for point in points:
            curve.append({
                "time": point.timestamp,
                "time_percent": point.timestamp / duration * 100 if duration > 0 else 0,
                "engagement": point.engagement_level,
                "intensity": point.emotional_intensity
            })

        return curve

    def _calculate_overall_rating(
        self,
        points: List[JourneyPoint],
        engagement_curve: List[Dict[str, float]],
        content_type: str
    ) -> float:
        """计算整体评分"""
        if not points:
            return 0.0

        # 计算平均参与度
        avg_engagement = sum(p.engagement_level for p in points) / len(points)

        # 计算与理想曲线的匹配度
        ideal_curve = self.IDEAL_CURVES.get(content_type, self.IDEAL_CURVES["standard"])
        curve_match = self._calculate_curve_match(engagement_curve, ideal_curve)

        # 检查是否有高潮
        has_climax = any(p.phase == JourneyPhase.CLIMAX for p in points)
        climax_bonus = 0.1 if has_climax else 0

        # 检查开头和结尾
        hook_strength = points[0].engagement_level if points else 0
        ending_strength = points[-1].engagement_level if points else 0

        # 综合评分
        rating = (
            avg_engagement * 0.4 +
            curve_match * 0.3 +
            climax_bonus +
            hook_strength * 0.1 +
            ending_strength * 0.1
        )

        return min(10.0, rating * 10)

    def _calculate_curve_match(
        self,
        actual_curve: List[Dict[str, float]],
        ideal_curve: List[float]
    ) -> float:
        """计算曲线匹配度"""
        if not actual_curve or not ideal_curve:
            return 0.5

        # 将实际曲线重采样到与理想曲线相同的点数
        n_points = len(ideal_curve)
        actual_values = [c["engagement"] for c in actual_curve]

        if len(actual_values) < n_points:
            # 插值
            step = len(actual_values) / n_points
            resampled = [actual_values[int(i * step)] for i in range(n_points)]
        else:
            # 降采样
            step = len(actual_values) / n_points
            resampled = [actual_values[int(i * step)] for i in range(n_points)]

        # 计算相关性
        diff_sum = sum(abs(a - i) for a, i in zip(resampled, ideal_curve))
        match_score = 1 - (diff_sum / n_points)

        return max(0, match_score)

    def _generate_recommendations(
        self,
        points: List[JourneyPoint],
        phases: List[Dict[str, Any]],
        highlights: List[Dict[str, Any]],
        low_points: List[Dict[str, Any]],
        content_type: str
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 检查开头
        if points and points[0].engagement_level < 0.5:
            recommendations.append("⚡ 开头参与度较低，建议使用更强的钩子")

        # 检查高潮
        has_climax = any(p.phase == JourneyPhase.CLIMAX for p in points)
        if not has_climax:
            recommendations.append("📈 缺少明显的高潮点，考虑在中后段增加情感冲击")

        # 检查低点
        if len(low_points) > 3:
            recommendations.append(f"⚠️ 有{len(low_points)}个低参与度区域，需要优化内容节奏")

        # 检查结尾
        if points and points[-1].engagement_level < 0.4:
            recommendations.append("🔚 结尾参与度较低，建议添加更有力的行动号召")

        # 检查阶段平衡
        phase_durations = {p["phase"]: p["duration"] for p in phases}

        if phase_durations.get("setup", 0) > phase_durations.get("climax", 0) * 2:
            recommendations.append("⏱️ 铺垫时间过长，建议更快进入核心内容")

        # 内容类型特定建议
        if content_type == "interview":
            if len(highlights) < 3:
                recommendations.append("💡 访谈类内容建议增加更多引人深思的观点")

        elif content_type == "educational":
            recommendations.append("📚 教育类内容建议在每个知识点后添加小结")

        # 默认建议
        if not recommendations:
            recommendations.append("✅ 整体结构良好，继续保持！")

        return recommendations

    def export_to_json(self, journey_map: JourneyMap) -> str:
        """导出为JSON"""
        data = {
            "title": journey_map.title,
            "duration": journey_map.duration,
            "overall_rating": journey_map.overall_rating,
            "points": [
                {
                    "timestamp": p.timestamp,
                    "phase": p.phase.value,
                    "emotional_intensity": p.emotional_intensity,
                    "engagement_level": p.engagement_level,
                    "key_content": p.key_content,
                    "annotations": p.annotations
                }
                for p in journey_map.points
            ],
            "phases": journey_map.phases,
            "highlights": journey_map.highlights,
            "low_points": journey_map.low_points,
            "engagement_curve": journey_map.engagement_curve,
            "recommendations": journey_map.recommendations
        }

        return json.dumps(data, ensure_ascii=False, indent=2)

    def compare_journeys(
        self,
        journey1: JourneyMap,
        journey2: JourneyMap
    ) -> Dict[str, Any]:
        """比较两个旅程图"""
        return {
            "rating_diff": journey1.overall_rating - journey2.overall_rating,
            "journey1_highlights": len(journey1.highlights),
            "journey2_highlights": len(journey2.highlights),
            "journey1_low_points": len(journey1.low_points),
            "journey2_low_points": len(journey2.low_points),
            "avg_engagement_diff": (
                sum(p.engagement_level for p in journey1.points) / len(journey1.points)
                if journey1.points else 0
            ) - (
                sum(p.engagement_level for p in journey2.points) / len(journey2.points)
                if journey2.points else 0
            ),
            "winner": "journey1" if journey1.overall_rating > journey2.overall_rating else "journey2"
        }
