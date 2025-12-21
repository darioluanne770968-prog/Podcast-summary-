"""
趋势预测模块

分析播客讨论预测行业趋势
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class TrendSignal:
    """趋势信号"""
    id: str
    topic: str
    signal_type: str  # emerging, growing, peaking, declining
    strength: float  # 0-1
    first_mention: str
    mention_count: int
    podcasts_mentioning: List[str]
    key_quotes: List[str]
    prediction: str
    confidence: float
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "signal_type": self.signal_type,
            "strength": self.strength,
            "first_mention": self.first_mention,
            "mention_count": self.mention_count,
            "podcasts_mentioning": self.podcasts_mentioning,
            "key_quotes": self.key_quotes[:5],
            "prediction": self.prediction,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


class TrendPredictor:
    """
    趋势预测器

    功能：
    - 识别新兴趋势
    - 追踪话题热度
    - 生成情感指数
    - 预测未来发展
    """

    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        self._topic_history: Dict[str, List[Dict]] = {}
        self._trend_signals: List[TrendSignal] = []

    def record_mention(
        self,
        topic: str,
        podcast_name: str,
        episode_title: str,
        date: str,
        quote: str = "",
        sentiment: float = 0.5,
    ):
        """记录话题提及"""
        if topic not in self._topic_history:
            self._topic_history[topic] = []

        self._topic_history[topic].append({
            "podcast": podcast_name,
            "episode": episode_title,
            "date": date,
            "quote": quote,
            "sentiment": sentiment,
        })

    async def detect_trends(
        self,
        time_window_days: int = 30,
        min_mentions: int = 3,
    ) -> List[TrendSignal]:
        """
        检测趋势

        Args:
            time_window_days: 时间窗口
            min_mentions: 最少提及次数

        Returns:
            趋势信号列表
        """
        import uuid
        cutoff_date = (datetime.now() - timedelta(days=time_window_days)).isoformat()

        trends = []

        for topic, mentions in self._topic_history.items():
            # 过滤时间窗口内的提及
            recent_mentions = [
                m for m in mentions
                if m.get("date", "") >= cutoff_date
            ]

            if len(recent_mentions) < min_mentions:
                continue

            # 分析趋势类型
            signal_type, strength = self._analyze_trend_type(topic, mentions)

            # 收集关键引用
            key_quotes = [m.get("quote", "")[:200] for m in recent_mentions if m.get("quote")]

            # 使用 LLM 生成预测
            prediction = await self._generate_prediction(topic, recent_mentions)

            trend = TrendSignal(
                id=str(uuid.uuid4())[:8],
                topic=topic,
                signal_type=signal_type,
                strength=strength,
                first_mention=min(m.get("date", "") for m in mentions),
                mention_count=len(recent_mentions),
                podcasts_mentioning=list(set(m.get("podcast", "") for m in recent_mentions)),
                key_quotes=key_quotes[:5],
                prediction=prediction,
                confidence=min(0.9, len(recent_mentions) * 0.1),
            )

            trends.append(trend)

        # 按强度排序
        trends.sort(key=lambda t: t.strength, reverse=True)
        self._trend_signals = trends

        return trends

    def _analyze_trend_type(
        self,
        topic: str,
        mentions: List[Dict],
    ) -> tuple:
        """分析趋势类型"""
        if not mentions:
            return "unknown", 0

        # 按日期排序
        sorted_mentions = sorted(mentions, key=lambda m: m.get("date", ""))

        total = len(sorted_mentions)
        if total < 3:
            return "emerging", 0.3

        # 计算时间分布
        third = total // 3
        early = sorted_mentions[:third]
        mid = sorted_mentions[third:2*third]
        late = sorted_mentions[2*third:]

        early_count = len(early)
        mid_count = len(mid)
        late_count = len(late)

        # 判断趋势方向
        if late_count > mid_count > early_count:
            return "growing", 0.8
        elif early_count < mid_count and mid_count >= late_count:
            return "peaking", 0.7
        elif early_count > mid_count > late_count:
            return "declining", 0.5
        elif late_count >= early_count:
            return "emerging", 0.6
        else:
            return "stable", 0.4

    async def _generate_prediction(
        self,
        topic: str,
        recent_mentions: List[Dict],
    ) -> str:
        """生成趋势预测"""
        quotes = [m.get("quote", "") for m in recent_mentions[:5] if m.get("quote")]

        prompt = f"""基于以下播客讨论，预测「{topic}」这个话题的未来发展：

讨论摘录：
{json.dumps(quotes, ensure_ascii=False)}

提及次数：{len(recent_mentions)}
涉及播客：{len(set(m.get('podcast', '') for m in recent_mentions))}

请提供一段简短的趋势预测（50-100字）。"""

        try:
            return await self._call_llm(prompt)
        except:
            return "趋势预测暂时不可用"

    def calculate_sentiment_index(
        self,
        topic: str,
        time_window_days: int = 30,
    ) -> Dict[str, Any]:
        """
        计算情感指数

        Args:
            topic: 话题
            time_window_days: 时间窗口

        Returns:
            情感指数
        """
        mentions = self._topic_history.get(topic, [])
        if not mentions:
            return {"topic": topic, "index": 0.5, "data_points": 0}

        cutoff = (datetime.now() - timedelta(days=time_window_days)).isoformat()
        recent = [m for m in mentions if m.get("date", "") >= cutoff]

        if not recent:
            return {"topic": topic, "index": 0.5, "data_points": 0}

        # 计算平均情感
        sentiments = [m.get("sentiment", 0.5) for m in recent]
        avg_sentiment = sum(sentiments) / len(sentiments)

        # 计算情感波动
        variance = sum((s - avg_sentiment) ** 2 for s in sentiments) / len(sentiments)

        # 生成时间线
        timeline = []
        for m in sorted(recent, key=lambda x: x.get("date", "")):
            timeline.append({
                "date": m.get("date", ""),
                "sentiment": m.get("sentiment", 0.5),
                "podcast": m.get("podcast", ""),
            })

        return {
            "topic": topic,
            "index": avg_sentiment,
            "variance": variance,
            "data_points": len(recent),
            "timeline": timeline[-20:],  # 最近 20 个数据点
            "interpretation": self._interpret_sentiment(avg_sentiment),
        }

    def _interpret_sentiment(self, sentiment: float) -> str:
        """解释情感分数"""
        if sentiment >= 0.8:
            return "非常乐观"
        elif sentiment >= 0.6:
            return "偏向乐观"
        elif sentiment >= 0.4:
            return "中性"
        elif sentiment >= 0.2:
            return "偏向悲观"
        else:
            return "非常悲观"

    async def compare_podcast_sentiment(
        self,
        topic: str,
    ) -> Dict[str, Any]:
        """
        比较不同播客对同一话题的情感

        Args:
            topic: 话题

        Returns:
            情感对比
        """
        mentions = self._topic_history.get(topic, [])
        if not mentions:
            return {"topic": topic, "comparison": {}}

        # 按播客分组
        by_podcast: Dict[str, List[float]] = {}
        for m in mentions:
            podcast = m.get("podcast", "unknown")
            if podcast not in by_podcast:
                by_podcast[podcast] = []
            by_podcast[podcast].append(m.get("sentiment", 0.5))

        # 计算每个播客的平均情感
        comparison = {}
        for podcast, sentiments in by_podcast.items():
            comparison[podcast] = {
                "avg_sentiment": sum(sentiments) / len(sentiments),
                "mention_count": len(sentiments),
            }

        # 找出最乐观和最悲观的播客
        sorted_podcasts = sorted(
            comparison.items(),
            key=lambda x: x[1]["avg_sentiment"],
            reverse=True
        )

        return {
            "topic": topic,
            "comparison": comparison,
            "most_optimistic": sorted_podcasts[0][0] if sorted_podcasts else None,
            "most_pessimistic": sorted_podcasts[-1][0] if sorted_podcasts else None,
        }

    def get_hot_topics(self, limit: int = 10) -> List[Dict]:
        """获取热门话题"""
        topics = []
        for topic, mentions in self._topic_history.items():
            # 只看最近 7 天
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            recent = [m for m in mentions if m.get("date", "") >= cutoff]

            if recent:
                topics.append({
                    "topic": topic,
                    "recent_mentions": len(recent),
                    "total_mentions": len(mentions),
                    "podcasts": len(set(m.get("podcast", "") for m in recent)),
                })

        topics.sort(key=lambda x: x["recent_mentions"], reverse=True)
        return topics[:limit]

    def get_trend_by_topic(self, topic: str) -> Optional[TrendSignal]:
        """获取话题趋势"""
        for trend in self._trend_signals:
            if trend.topic.lower() == topic.lower():
                return trend
        return None

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if self.llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "你是趋势分析专家。"},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=200,
                )
                return response.choices[0].message.content
            else:
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic()
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return "预测暂不可用"
