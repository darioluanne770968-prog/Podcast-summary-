"""
参与度追踪器
追踪和分析听众参与度
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np


class EngagementMetric(Enum):
    """参与度指标"""
    LISTEN_THROUGH = "listen_through"  # 完播率
    REPLAY = "replay"  # 重播
    SKIP = "skip"  # 跳过
    PAUSE = "pause"  # 暂停
    SHARE = "share"  # 分享
    COMMENT = "comment"  # 评论
    LIKE = "like"  # 点赞
    SAVE = "save"  # 收藏


@dataclass
class EngagementEvent:
    """参与度事件"""
    user_id: str
    timestamp: float  # 播客时间点
    event_time: datetime  # 事件发生时间
    metric: EngagementMetric
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSlotStats:
    """时间段统计"""
    start_time: float
    end_time: float
    total_listeners: int
    avg_engagement: float
    drop_off_rate: float
    replay_rate: float
    skip_rate: float
    top_actions: List[Dict[str, Any]]


@dataclass
class EngagementReport:
    """参与度报告"""
    podcast_id: str
    total_plays: int
    unique_listeners: int
    avg_listen_duration: float
    completion_rate: float
    engagement_score: float
    time_slot_stats: List[TimeSlotStats]
    hotspots: List[Dict[str, Any]]
    coldspots: List[Dict[str, Any]]
    user_segments: Dict[str, Dict[str, Any]]
    trends: Dict[str, Any]
    recommendations: List[str]


class EngagementTracker:
    """参与度追踪器"""

    def __init__(self, podcast_id: str, duration: float):
        self.podcast_id = podcast_id
        self.duration = duration
        self.events: List[EngagementEvent] = []
        self.user_sessions: Dict[str, List[EngagementEvent]] = {}
        self.slot_duration = 30  # 30秒一个时间段

    def track_event(
        self,
        user_id: str,
        timestamp: float,
        metric: EngagementMetric,
        value: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录参与度事件

        Args:
            user_id: 用户ID
            timestamp: 播客时间点
            metric: 指标类型
            value: 值
            metadata: 元数据
        """
        event = EngagementEvent(
            user_id=user_id,
            timestamp=timestamp,
            event_time=datetime.now(),
            metric=metric,
            value=value,
            metadata=metadata or {}
        )

        self.events.append(event)

        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(event)

    def generate_report(self) -> EngagementReport:
        """生成参与度报告"""
        # 基础统计
        total_plays = len(self.user_sessions)
        unique_listeners = len(set(e.user_id for e in self.events))

        # 计算平均收听时长
        avg_listen_duration = self._calculate_avg_listen_duration()

        # 计算完播率
        completion_rate = self._calculate_completion_rate()

        # 计算整体参与度分数
        engagement_score = self._calculate_engagement_score()

        # 时间段统计
        time_slot_stats = self._generate_time_slot_stats()

        # 热点和冷点
        hotspots = self._identify_hotspots(time_slot_stats)
        coldspots = self._identify_coldspots(time_slot_stats)

        # 用户分群
        user_segments = self._segment_users()

        # 趋势分析
        trends = self._analyze_trends()

        # 生成建议
        recommendations = self._generate_recommendations(
            time_slot_stats, hotspots, coldspots, completion_rate
        )

        return EngagementReport(
            podcast_id=self.podcast_id,
            total_plays=total_plays,
            unique_listeners=unique_listeners,
            avg_listen_duration=avg_listen_duration,
            completion_rate=completion_rate,
            engagement_score=engagement_score,
            time_slot_stats=time_slot_stats,
            hotspots=hotspots,
            coldspots=coldspots,
            user_segments=user_segments,
            trends=trends,
            recommendations=recommendations
        )

    def _calculate_avg_listen_duration(self) -> float:
        """计算平均收听时长"""
        if not self.user_sessions:
            return 0

        durations = []
        for user_id, events in self.user_sessions.items():
            # 找到最大时间戳作为收听时长
            max_timestamp = max(e.timestamp for e in events) if events else 0
            durations.append(max_timestamp)

        return np.mean(durations) if durations else 0

    def _calculate_completion_rate(self) -> float:
        """计算完播率"""
        if not self.user_sessions:
            return 0

        completed = 0
        for user_id, events in self.user_sessions.items():
            max_timestamp = max(e.timestamp for e in events) if events else 0
            if max_timestamp >= self.duration * 0.9:  # 90%以上视为完播
                completed += 1

        return completed / len(self.user_sessions)

    def _calculate_engagement_score(self) -> float:
        """计算整体参与度分数"""
        if not self.events:
            return 0

        # 各指标权重
        weights = {
            EngagementMetric.LISTEN_THROUGH: 1.0,
            EngagementMetric.REPLAY: 0.8,
            EngagementMetric.SHARE: 1.2,
            EngagementMetric.COMMENT: 1.0,
            EngagementMetric.LIKE: 0.6,
            EngagementMetric.SAVE: 0.8,
            EngagementMetric.SKIP: -0.5,
            EngagementMetric.PAUSE: 0.2
        }

        total_score = 0
        for event in self.events:
            total_score += event.value * weights.get(event.metric, 0.5)

        # 归一化到0-100
        max_possible = len(self.events) * max(weights.values())
        return min(100, (total_score / max_possible * 100)) if max_possible > 0 else 0

    def _generate_time_slot_stats(self) -> List[TimeSlotStats]:
        """生成时间段统计"""
        stats = []
        num_slots = int(np.ceil(self.duration / self.slot_duration))

        for i in range(num_slots):
            start_time = i * self.slot_duration
            end_time = min((i + 1) * self.slot_duration, self.duration)

            # 获取该时间段的事件
            slot_events = [
                e for e in self.events
                if start_time <= e.timestamp < end_time
            ]

            # 计算统计数据
            total_listeners = len(set(e.user_id for e in slot_events))

            # 计算参与度
            engagement_values = [e.value for e in slot_events if e.metric != EngagementMetric.SKIP]
            avg_engagement = np.mean(engagement_values) if engagement_values else 0.5

            # 计算跳过率
            skip_events = [e for e in slot_events if e.metric == EngagementMetric.SKIP]
            skip_rate = len(skip_events) / total_listeners if total_listeners > 0 else 0

            # 计算重播率
            replay_events = [e for e in slot_events if e.metric == EngagementMetric.REPLAY]
            replay_rate = len(replay_events) / total_listeners if total_listeners > 0 else 0

            # 计算流失率
            if i > 0 and stats:
                prev_listeners = stats[-1].total_listeners
                drop_off_rate = 1 - (total_listeners / prev_listeners) if prev_listeners > 0 else 0
            else:
                drop_off_rate = 0

            # 统计主要行为
            action_counts = {}
            for e in slot_events:
                action_counts[e.metric.value] = action_counts.get(e.metric.value, 0) + 1

            top_actions = [
                {"action": k, "count": v}
                for k, v in sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            ]

            slot_stat = TimeSlotStats(
                start_time=start_time,
                end_time=end_time,
                total_listeners=total_listeners,
                avg_engagement=avg_engagement,
                drop_off_rate=drop_off_rate,
                replay_rate=replay_rate,
                skip_rate=skip_rate,
                top_actions=top_actions
            )

            stats.append(slot_stat)

        return stats

    def _identify_hotspots(self, stats: List[TimeSlotStats]) -> List[Dict[str, Any]]:
        """识别热点"""
        hotspots = []

        for stat in stats:
            if stat.avg_engagement > 0.7 or stat.replay_rate > 0.1:
                hotspots.append({
                    "start_time": stat.start_time,
                    "end_time": stat.end_time,
                    "engagement": stat.avg_engagement,
                    "replay_rate": stat.replay_rate,
                    "reason": "高参与度" if stat.avg_engagement > 0.7 else "高重播率"
                })

        return sorted(hotspots, key=lambda x: x["engagement"], reverse=True)[:5]

    def _identify_coldspots(self, stats: List[TimeSlotStats]) -> List[Dict[str, Any]]:
        """识别冷点"""
        coldspots = []

        for stat in stats:
            if stat.skip_rate > 0.2 or stat.drop_off_rate > 0.15:
                coldspots.append({
                    "start_time": stat.start_time,
                    "end_time": stat.end_time,
                    "skip_rate": stat.skip_rate,
                    "drop_off_rate": stat.drop_off_rate,
                    "issue": "高跳过率" if stat.skip_rate > 0.2 else "高流失率"
                })

        return sorted(coldspots, key=lambda x: x["skip_rate"] + x["drop_off_rate"], reverse=True)[:5]

    def _segment_users(self) -> Dict[str, Dict[str, Any]]:
        """用户分群"""
        segments = {
            "power_listeners": {"count": 0, "users": []},
            "casual_listeners": {"count": 0, "users": []},
            "skippers": {"count": 0, "users": []},
            "engagers": {"count": 0, "users": []}
        }

        for user_id, events in self.user_sessions.items():
            # 计算用户指标
            max_timestamp = max(e.timestamp for e in events) if events else 0
            completion = max_timestamp / self.duration if self.duration > 0 else 0

            skip_count = len([e for e in events if e.metric == EngagementMetric.SKIP])
            engage_count = len([
                e for e in events
                if e.metric in [EngagementMetric.SHARE, EngagementMetric.COMMENT, EngagementMetric.LIKE]
            ])

            # 分类
            if completion > 0.9 and engage_count > 0:
                segments["power_listeners"]["count"] += 1
                segments["power_listeners"]["users"].append(user_id)
            elif skip_count > 3:
                segments["skippers"]["count"] += 1
                segments["skippers"]["users"].append(user_id)
            elif engage_count > 0:
                segments["engagers"]["count"] += 1
                segments["engagers"]["users"].append(user_id)
            else:
                segments["casual_listeners"]["count"] += 1
                segments["casual_listeners"]["users"].append(user_id)

        return segments

    def _analyze_trends(self) -> Dict[str, Any]:
        """分析趋势"""
        # 按时间分组事件
        hourly_events = {}
        for event in self.events:
            hour = event.event_time.hour
            if hour not in hourly_events:
                hourly_events[hour] = []
            hourly_events[hour].append(event)

        # 找出最活跃的时间
        peak_hours = sorted(
            hourly_events.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:3]

        return {
            "peak_listening_hours": [h[0] for h in peak_hours],
            "total_events": len(self.events),
            "events_per_user": len(self.events) / len(self.user_sessions) if self.user_sessions else 0,
            "engagement_trend": self._calculate_engagement_trend()
        }

    def _calculate_engagement_trend(self) -> str:
        """计算参与度趋势"""
        if len(self.events) < 10:
            return "数据不足"

        # 将事件按时间分成前后两半
        sorted_events = sorted(self.events, key=lambda x: x.event_time)
        mid = len(sorted_events) // 2

        first_half = sorted_events[:mid]
        second_half = sorted_events[mid:]

        first_engagement = np.mean([e.value for e in first_half])
        second_engagement = np.mean([e.value for e in second_half])

        if second_engagement > first_engagement * 1.1:
            return "上升"
        elif second_engagement < first_engagement * 0.9:
            return "下降"
        else:
            return "稳定"

    def _generate_recommendations(
        self,
        stats: List[TimeSlotStats],
        hotspots: List[Dict[str, Any]],
        coldspots: List[Dict[str, Any]],
        completion_rate: float
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 完播率建议
        if completion_rate < 0.5:
            recommendations.append("⚠️ 完播率较低，建议优化内容结构，减少冗余")
        elif completion_rate > 0.8:
            recommendations.append("✅ 完播率优秀，继续保持当前风格")

        # 冷点建议
        if coldspots:
            first_coldspot = coldspots[0]
            recommendations.append(
                f"🔴 在 {first_coldspot['start_time']:.0f}-{first_coldspot['end_time']:.0f}秒 "
                f"存在问题：{first_coldspot['issue']}"
            )

        # 热点建议
        if hotspots:
            first_hotspot = hotspots[0]
            recommendations.append(
                f"🟢 {first_hotspot['start_time']:.0f}-{first_hotspot['end_time']:.0f}秒 "
                f"是最受欢迎的片段，可作为精彩片段分享"
            )

        # 开头建议
        if stats and stats[0].drop_off_rate > 0.2:
            recommendations.append("⚡ 开头流失率高，建议使用更吸引人的开场")

        # 结尾建议
        if stats and stats[-1].avg_engagement < 0.4:
            recommendations.append("📢 结尾参与度低，建议添加行动号召或预告")

        return recommendations

    def get_retention_curve(self) -> List[Dict[str, float]]:
        """获取留存曲线"""
        curve = []
        num_points = 20

        for i in range(num_points):
            time_point = (i / num_points) * self.duration

            # 计算该时间点的留存用户
            retained_users = 0
            for user_id, events in self.user_sessions.items():
                max_timestamp = max(e.timestamp for e in events) if events else 0
                if max_timestamp >= time_point:
                    retained_users += 1

            retention_rate = retained_users / len(self.user_sessions) if self.user_sessions else 0

            curve.append({
                "time": time_point,
                "time_percent": (i / num_points) * 100,
                "retention": retention_rate
            })

        return curve

    def simulate_data(self, num_users: int = 100):
        """模拟测试数据"""
        import random

        for i in range(num_users):
            user_id = f"user_{i}"

            # 模拟收听时长（正态分布，偏向完整收听）
            listen_duration = min(self.duration, max(0, random.gauss(self.duration * 0.7, self.duration * 0.3)))

            # 记录收听事件
            current_time = 0
            while current_time < listen_duration:
                # 随机事件
                event_type = random.choices(
                    [EngagementMetric.LISTEN_THROUGH, EngagementMetric.PAUSE,
                     EngagementMetric.SKIP, EngagementMetric.REPLAY],
                    weights=[0.7, 0.15, 0.1, 0.05]
                )[0]

                self.track_event(user_id, current_time, event_type)
                current_time += random.uniform(10, 60)

            # 随机互动事件
            if random.random() > 0.7:
                self.track_event(user_id, listen_duration, EngagementMetric.LIKE)
            if random.random() > 0.9:
                self.track_event(user_id, listen_duration, EngagementMetric.SHARE)
            if random.random() > 0.95:
                self.track_event(user_id, listen_duration, EngagementMetric.COMMENT)
