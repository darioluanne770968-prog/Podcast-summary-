"""
话题追踪模块

跨多期播客追踪话题演变
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime

from ..analysis import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class TopicMention:
    """话题提及"""
    episode_id: str
    episode_title: str
    timestamp: Optional[float] = None
    context: str = ""
    sentiment: str = "neutral"  # positive, negative, neutral
    date: Optional[str] = None


@dataclass
class TopicEvolution:
    """话题演变"""
    topic: str
    description: str
    mentions: List[TopicMention] = field(default_factory=list)
    first_mentioned: Optional[str] = None
    last_mentioned: Optional[str] = None
    total_mentions: int = 0
    sentiment_trend: str = "stable"  # improving, declining, stable, fluctuating
    related_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "description": self.description,
            "mentions": [
                {
                    "episode_id": m.episode_id,
                    "episode_title": m.episode_title,
                    "context": m.context,
                    "sentiment": m.sentiment,
                    "date": m.date,
                }
                for m in self.mentions
            ],
            "first_mentioned": self.first_mentioned,
            "last_mentioned": self.last_mentioned,
            "total_mentions": self.total_mentions,
            "sentiment_trend": self.sentiment_trend,
            "related_topics": self.related_topics,
        }


class TopicTracker:
    """话题追踪器"""

    SYSTEM_PROMPT = """你是一个内容分析专家，擅长追踪和分析话题的演变。

分析要点：
1. 识别话题在不同时间点的讨论内容
2. 分析讨论的情感倾向变化
3. 识别相关联的话题
4. 总结话题的整体演变趋势"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()
        self._topic_database: Dict[str, TopicEvolution] = {}

    def add_episode(
        self,
        episode_id: str,
        episode_title: str,
        transcript: str,
        date: Optional[str] = None,
    ):
        """
        添加一期播客到追踪数据库

        Args:
            episode_id: 节目 ID
            episode_title: 节目标题
            transcript: 转录文本
            date: 发布日期
        """
        logger.info(f"添加节目到话题追踪: {episode_title}")

        # 提取话题
        topics = self._extract_topics_from_episode(
            transcript, episode_id, episode_title, date
        )

        # 更新数据库
        for topic_name, mentions in topics.items():
            if topic_name not in self._topic_database:
                self._topic_database[topic_name] = TopicEvolution(
                    topic=topic_name,
                    description="",
                )

            evolution = self._topic_database[topic_name]
            evolution.mentions.extend(mentions)
            evolution.total_mentions = len(evolution.mentions)

            # 更新时间范围
            dates = [m.date for m in evolution.mentions if m.date]
            if dates:
                evolution.first_mentioned = min(dates)
                evolution.last_mentioned = max(dates)

    def _extract_topics_from_episode(
        self,
        transcript: str,
        episode_id: str,
        episode_title: str,
        date: Optional[str],
    ) -> Dict[str, List[TopicMention]]:
        """从单期节目提取话题"""
        prompt = f"""分析以下播客转录文本，提取讨论的主要话题。

文本：
---
{transcript[:20000]}
---

请提取所有重要话题，按以下 JSON 格式输出：

```json
[
  {{
    "topic": "话题名称",
    "context": "讨论了什么内容",
    "sentiment": "positive/negative/neutral"
  }}
]
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.3)
            data = self.llm.parse_json_response(response)

            topics = {}
            for item in data:
                topic_name = item.get("topic", "")
                if topic_name:
                    if topic_name not in topics:
                        topics[topic_name] = []
                    topics[topic_name].append(TopicMention(
                        episode_id=episode_id,
                        episode_title=episode_title,
                        context=item.get("context", ""),
                        sentiment=item.get("sentiment", "neutral"),
                        date=date,
                    ))

            return topics

        except Exception as e:
            logger.error(f"提取话题失败: {e}")
            return {}

    def track_topic(self, topic_name: str) -> Optional[TopicEvolution]:
        """
        追踪特定话题的演变

        Args:
            topic_name: 话题名称

        Returns:
            TopicEvolution 对象
        """
        if topic_name not in self._topic_database:
            return None

        evolution = self._topic_database[topic_name]

        # 分析情感趋势
        evolution.sentiment_trend = self._analyze_sentiment_trend(evolution.mentions)

        # 找相关话题
        evolution.related_topics = self._find_related_topics(topic_name)

        return evolution

    def _analyze_sentiment_trend(self, mentions: List[TopicMention]) -> str:
        """分析情感趋势"""
        if len(mentions) < 2:
            return "stable"

        # 按日期排序
        sorted_mentions = sorted(mentions, key=lambda m: m.date or "")

        # 计算情感分数
        sentiment_scores = []
        for m in sorted_mentions:
            if m.sentiment == "positive":
                sentiment_scores.append(1)
            elif m.sentiment == "negative":
                sentiment_scores.append(-1)
            else:
                sentiment_scores.append(0)

        if len(sentiment_scores) < 2:
            return "stable"

        # 比较前半和后半
        mid = len(sentiment_scores) // 2
        first_half = sum(sentiment_scores[:mid]) / max(mid, 1)
        second_half = sum(sentiment_scores[mid:]) / max(len(sentiment_scores) - mid, 1)

        diff = second_half - first_half
        if diff > 0.3:
            return "improving"
        elif diff < -0.3:
            return "declining"
        elif abs(diff) < 0.1:
            return "stable"
        else:
            return "fluctuating"

    def _find_related_topics(self, topic_name: str) -> List[str]:
        """找出与给定话题相关的其他话题"""
        if topic_name not in self._topic_database:
            return []

        target = self._topic_database[topic_name]
        target_episodes = {m.episode_id for m in target.mentions}

        # 找在相同节目中出现的其他话题
        related = []
        for other_topic, evolution in self._topic_database.items():
            if other_topic == topic_name:
                continue
            other_episodes = {m.episode_id for m in evolution.mentions}
            overlap = len(target_episodes & other_episodes)
            if overlap > 0:
                related.append((other_topic, overlap))

        # 按重叠度排序
        related.sort(key=lambda x: x[1], reverse=True)
        return [t[0] for t in related[:5]]

    def get_all_topics(self) -> List[TopicEvolution]:
        """获取所有追踪的话题"""
        return list(self._topic_database.values())

    def get_trending_topics(self, limit: int = 10) -> List[TopicEvolution]:
        """获取热门话题（按提及次数排序）"""
        topics = list(self._topic_database.values())
        topics.sort(key=lambda t: t.total_mentions, reverse=True)
        return topics[:limit]

    def generate_topic_report(self, topic_name: str) -> str:
        """生成话题追踪报告"""
        evolution = self.track_topic(topic_name)

        if not evolution:
            return f"未找到话题: {topic_name}"

        lines = [f"## 📈 话题追踪: {topic_name}\n"]

        # 基本信息
        lines.append(f"**首次提及**: {evolution.first_mentioned or '未知'}")
        lines.append(f"**最近提及**: {evolution.last_mentioned or '未知'}")
        lines.append(f"**总提及次数**: {evolution.total_mentions}")

        trend_emoji = {
            "improving": "📈",
            "declining": "📉",
            "stable": "➡️",
            "fluctuating": "📊",
        }
        lines.append(f"**情感趋势**: {trend_emoji.get(evolution.sentiment_trend, '')} {evolution.sentiment_trend}")

        # 相关话题
        if evolution.related_topics:
            lines.append(f"\n**相关话题**: {', '.join(evolution.related_topics)}")

        # 演变历程
        lines.append("\n### 📅 演变历程\n")
        for mention in evolution.mentions:
            sentiment_emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(mention.sentiment, "")
            lines.append(f"- **{mention.episode_title}** ({mention.date or '未知日期'}) {sentiment_emoji}")
            lines.append(f"  - {mention.context[:100]}...")

        return "\n".join(lines)
