"""
深度听众分析模块

功能：
- 注意力热图：分析哪些片段最吸引听众
- 情绪共振：检测内容引发的情绪波动
- 学习曲线：追踪用户对某话题的理解进度
- 遗忘预测：提醒复习即将遗忘的内容
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import math

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class ListeningEvent:
    """收听事件"""
    podcast_id: str
    episode_id: str
    timestamp: float  # 播放位置
    event_type: str  # play, pause, seek, complete, skip
    duration: float = 0  # 持续时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AttentionHeatmap:
    """注意力热图"""
    episode_id: str
    duration: float
    segments: List[Dict]  # [{start, end, attention_score}]
    peak_moments: List[float]  # 高注意力时刻
    drop_points: List[float]  # 流失点

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "duration": self.duration,
            "segments": self.segments,
            "peak_moments": self.peak_moments,
            "drop_points": self.drop_points,
        }


@dataclass
class EmotionalResonance:
    """情绪共振"""
    episode_id: str
    timeline: List[Dict]  # [{timestamp, emotion, intensity}]
    dominant_emotion: str
    emotional_range: float
    peak_emotions: List[Dict]


@dataclass
class ListenerProfile:
    """听众画像"""
    user_id: str
    listening_history: List[Dict] = field(default_factory=list)
    topic_interests: Dict[str, float] = field(default_factory=dict)
    preferred_duration: float = 60
    preferred_time: str = "morning"
    completion_rate: float = 0.0
    learning_progress: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "listening_history": self.listening_history[-20:],
            "topic_interests": self.topic_interests,
            "preferred_duration": self.preferred_duration,
            "preferred_time": self.preferred_time,
            "completion_rate": self.completion_rate,
            "learning_progress": self.learning_progress,
            "created_at": self.created_at,
        }


class AudienceAnalytics:
    """
    听众分析器

    功能：
    - 生成注意力热图
    - 分析情绪共振
    - 追踪学习进度
    - 预测遗忘曲线
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "audience"
        ensure_dir(self.storage_dir)
        self._listeners: Dict[str, ListenerProfile] = {}
        self._events: List[ListeningEvent] = []
        self._load_data()

    def _load_data(self):
        """加载数据"""
        data_file = self.storage_dir / "analytics.json"
        if data_file.exists():
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for listener_data in data.get("listeners", []):
                        listener = ListenerProfile(
                            user_id=listener_data["user_id"],
                            listening_history=listener_data.get("listening_history", []),
                            topic_interests=listener_data.get("topic_interests", {}),
                            preferred_duration=listener_data.get("preferred_duration", 60),
                            preferred_time=listener_data.get("preferred_time", "morning"),
                            completion_rate=listener_data.get("completion_rate", 0),
                            learning_progress=listener_data.get("learning_progress", {}),
                        )
                        self._listeners[listener.user_id] = listener
            except Exception as e:
                logger.error(f"加载听众数据失败: {e}")

    def _save_data(self):
        """保存数据"""
        data_file = self.storage_dir / "analytics.json"
        try:
            data = {
                "listeners": [l.to_dict() for l in self._listeners.values()],
            }
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存听众数据失败: {e}")

    def get_or_create_listener(self, user_id: str) -> ListenerProfile:
        """获取或创建听众档案"""
        if user_id not in self._listeners:
            self._listeners[user_id] = ListenerProfile(user_id=user_id)
            self._save_data()
        return self._listeners[user_id]

    def record_event(
        self,
        user_id: str,
        podcast_id: str,
        episode_id: str,
        timestamp: float,
        event_type: str,
        duration: float = 0,
    ):
        """记录收听事件"""
        event = ListeningEvent(
            podcast_id=podcast_id,
            episode_id=episode_id,
            timestamp=timestamp,
            event_type=event_type,
            duration=duration,
        )
        self._events.append(event)

        # 更新听众档案
        listener = self.get_or_create_listener(user_id)
        listener.listening_history.append({
            "podcast_id": podcast_id,
            "episode_id": episode_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "date": datetime.now().isoformat(),
        })

        self._save_data()

    def generate_attention_heatmap(
        self,
        episode_id: str,
        episode_duration: float,
        segment_length: float = 60,
    ) -> AttentionHeatmap:
        """
        生成注意力热图

        基于收听事件分析哪些片段最吸引听众
        """
        episode_events = [e for e in self._events if e.episode_id == episode_id]

        if not episode_events:
            return AttentionHeatmap(
                episode_id=episode_id,
                duration=episode_duration,
                segments=[],
                peak_moments=[],
                drop_points=[],
            )

        # 计算每个片段的注意力分数
        num_segments = int(episode_duration / segment_length) + 1
        segment_scores = [0.0] * num_segments
        segment_counts = [0] * num_segments

        for event in episode_events:
            segment_idx = int(event.timestamp / segment_length)
            if 0 <= segment_idx < num_segments:
                if event.event_type == "play":
                    segment_scores[segment_idx] += 1
                elif event.event_type == "pause":
                    segment_scores[segment_idx] += 0.5  # 暂停也表示关注
                elif event.event_type == "seek":
                    # 跳转表示跳过
                    segment_scores[segment_idx] -= 0.5
                elif event.event_type == "skip":
                    segment_scores[segment_idx] -= 1

                segment_counts[segment_idx] += 1

        # 归一化
        max_score = max(segment_scores) if segment_scores else 1
        if max_score == 0:
            max_score = 1

        segments = []
        for i in range(num_segments):
            score = segment_scores[i] / max_score if max_score > 0 else 0
            segments.append({
                "start": i * segment_length,
                "end": min((i + 1) * segment_length, episode_duration),
                "attention_score": max(0, min(1, score)),
            })

        # 找出峰值和低谷
        peak_moments = []
        drop_points = []
        threshold_high = 0.7
        threshold_low = 0.3

        for seg in segments:
            if seg["attention_score"] >= threshold_high:
                peak_moments.append((seg["start"] + seg["end"]) / 2)
            elif seg["attention_score"] <= threshold_low:
                drop_points.append((seg["start"] + seg["end"]) / 2)

        return AttentionHeatmap(
            episode_id=episode_id,
            duration=episode_duration,
            segments=segments,
            peak_moments=peak_moments[:10],
            drop_points=drop_points[:10],
        )

    async def analyze_emotional_resonance(
        self,
        transcript: str,
        timestamps: List[Dict],
        llm_provider: str = "openai",
    ) -> EmotionalResonance:
        """
        分析情绪共振

        检测内容在不同时间点引发的情绪
        """
        # 将转录文本分段
        segments = []
        for i, ts in enumerate(timestamps[:20]):  # 限制分析量
            text = ts.get("text", "")
            if len(text) > 50:
                segments.append({
                    "timestamp": ts.get("start", i * 60),
                    "text": text[:200],
                })

        if not segments:
            return EmotionalResonance(
                episode_id="",
                timeline=[],
                dominant_emotion="neutral",
                emotional_range=0,
                peak_emotions=[],
            )

        # 使用 LLM 分析情绪
        prompt = f"""分析以下播客片段的情绪：

{json.dumps(segments, ensure_ascii=False)}

为每个片段标注情绪和强度，返回 JSON：
[
  {{"timestamp": 0, "emotion": "excited/happy/neutral/sad/angry/curious/inspired", "intensity": 0.8}}
]"""

        try:
            if llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是情绪分析专家。"},
                        {"role": "user", "content": prompt},
                    ],
                )
                result = response.choices[0].message.content

                import re
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    timeline = json.loads(json_match.group())

                    # 计算主导情绪
                    emotion_counts = {}
                    intensities = []
                    for item in timeline:
                        emotion = item.get("emotion", "neutral")
                        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                        intensities.append(item.get("intensity", 0.5))

                    dominant = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"
                    emotional_range = max(intensities) - min(intensities) if intensities else 0

                    # 找出情绪高峰
                    peak_emotions = [
                        item for item in timeline
                        if item.get("intensity", 0) >= 0.7
                    ][:5]

                    return EmotionalResonance(
                        episode_id="",
                        timeline=timeline,
                        dominant_emotion=dominant,
                        emotional_range=emotional_range,
                        peak_emotions=peak_emotions,
                    )
        except Exception as e:
            logger.error(f"情绪分析失败: {e}")

        return EmotionalResonance(
            episode_id="",
            timeline=[],
            dominant_emotion="neutral",
            emotional_range=0,
            peak_emotions=[],
        )

    def calculate_learning_curve(
        self,
        user_id: str,
        topic: str,
    ) -> Dict[str, Any]:
        """
        计算学习曲线

        追踪用户对某话题的理解进度
        """
        listener = self.get_or_create_listener(user_id)

        # 获取该话题的学习历史
        topic_history = [
            h for h in listener.listening_history
            if topic.lower() in str(h).lower()
        ]

        if not topic_history:
            return {
                "topic": topic,
                "progress": 0,
                "sessions": 0,
                "curve": [],
            }

        # 模拟学习曲线
        sessions = len(topic_history)
        # 使用对数增长曲线
        progress = min(100, 20 * math.log(sessions + 1))

        curve = []
        for i in range(sessions):
            curve.append({
                "session": i + 1,
                "progress": min(100, 20 * math.log(i + 2)),
                "date": topic_history[i].get("date", ""),
            })

        listener.learning_progress[topic] = progress
        self._save_data()

        return {
            "topic": topic,
            "progress": progress,
            "sessions": sessions,
            "curve": curve,
            "recommendation": self._get_learning_recommendation(progress),
        }

    def _get_learning_recommendation(self, progress: float) -> str:
        """获取学习建议"""
        if progress < 20:
            return "初学阶段，建议多听基础内容"
        elif progress < 50:
            return "入门阶段，可以开始接触进阶内容"
        elif progress < 80:
            return "中级阶段，建议深入学习和实践"
        else:
            return "高级阶段，可以探索前沿话题"

    def predict_forgetting(
        self,
        user_id: str,
        topic: str,
    ) -> Dict[str, Any]:
        """
        预测遗忘曲线

        基于艾宾浩斯遗忘曲线预测复习时间
        """
        listener = self.get_or_create_listener(user_id)

        topic_history = [
            h for h in listener.listening_history
            if topic.lower() in str(h).lower()
        ]

        if not topic_history:
            return {
                "topic": topic,
                "retention": 0,
                "next_review": None,
                "review_schedule": [],
            }

        # 最后学习时间
        last_session = topic_history[-1]
        last_date = datetime.fromisoformat(last_session.get("date", datetime.now().isoformat()))

        # 计算已过去的时间
        days_passed = (datetime.now() - last_date).days

        # 艾宾浩斯遗忘曲线
        # R = e^(-t/S)，S 是记忆强度
        review_count = len(topic_history)
        memory_strength = 1 + review_count * 0.5  # 复习次数增强记忆

        retention = math.exp(-days_passed / memory_strength) * 100

        # 计算复习计划
        review_intervals = [1, 3, 7, 14, 30, 60]
        review_schedule = []
        base_date = last_date

        for interval in review_intervals:
            review_date = base_date + timedelta(days=interval)
            if review_date > datetime.now():
                review_schedule.append({
                    "date": review_date.strftime("%Y-%m-%d"),
                    "days_from_now": (review_date - datetime.now()).days,
                    "estimated_retention": math.exp(-interval / memory_strength) * 100,
                })

        next_review = review_schedule[0] if review_schedule else None

        return {
            "topic": topic,
            "retention": retention,
            "days_since_last_review": days_passed,
            "review_count": review_count,
            "next_review": next_review,
            "review_schedule": review_schedule[:5],
            "recommendation": "建议复习" if retention < 50 else "记忆良好",
        }

    def get_listener_insights(self, user_id: str) -> Dict[str, Any]:
        """获取听众洞察"""
        listener = self.get_or_create_listener(user_id)

        history = listener.listening_history

        # 统计
        total_episodes = len(history)
        podcasts = list(set(h.get("podcast_id", "") for h in history))

        # 收听时间分布
        time_distribution = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
        for h in history:
            try:
                dt = datetime.fromisoformat(h.get("date", ""))
                hour = dt.hour
                if 5 <= hour < 12:
                    time_distribution["morning"] += 1
                elif 12 <= hour < 17:
                    time_distribution["afternoon"] += 1
                elif 17 <= hour < 21:
                    time_distribution["evening"] += 1
                else:
                    time_distribution["night"] += 1
            except:
                pass

        return {
            "user_id": user_id,
            "total_episodes": total_episodes,
            "unique_podcasts": len(podcasts),
            "topic_interests": listener.topic_interests,
            "preferred_time": max(time_distribution, key=time_distribution.get),
            "time_distribution": time_distribution,
            "learning_progress": listener.learning_progress,
            "completion_rate": listener.completion_rate,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_listeners": len(self._listeners),
            "total_events": len(self._events),
        }
