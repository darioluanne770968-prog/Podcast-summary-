"""
内容预测模块

预测下一期可能讨论的内容
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class PredictedTopic:
    """预测话题"""
    topic: str
    probability: float
    reasoning: str
    related_past_topics: List[str] = field(default_factory=list)
    suggested_questions: List[str] = field(default_factory=list)


@dataclass
class EpisodePrediction:
    """节目预测"""
    podcast_name: str
    predicted_topics: List[PredictedTopic]
    predicted_guests: List[str]
    predicted_format: str
    predicted_duration: str
    content_outline: str
    confidence: float
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ContentPredictor:
    """
    内容预测器

    功能：
    - 分析历史节目模式
    - 预测下一期主题
    - 生成内容提纲
    - 推荐潜在嘉宾
    """

    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        self._podcast_history: Dict[str, List[Dict]] = {}

    def add_episode(
        self,
        podcast_name: str,
        episode_data: Dict,
    ):
        """添加节目历史"""
        if podcast_name not in self._podcast_history:
            self._podcast_history[podcast_name] = []
        self._podcast_history[podcast_name].append(episode_data)

    def load_history(self, podcast_name: str, episodes: List[Dict]):
        """加载节目历史"""
        self._podcast_history[podcast_name] = episodes
        logger.info(f"加载 {podcast_name} 历史: {len(episodes)} 期")

    async def predict_next_episode(
        self,
        podcast_name: str,
        recent_events: List[str] = None,
    ) -> EpisodePrediction:
        """
        预测下一期内容

        Args:
            podcast_name: 播客名称
            recent_events: 近期相关事件

        Returns:
            节目预测
        """
        history = self._podcast_history.get(podcast_name, [])

        if not history:
            return await self._predict_without_history(podcast_name, recent_events)

        # 分析历史模式
        pattern_analysis = await self._analyze_patterns(history)

        # 生成预测
        prediction = await self._generate_prediction(
            podcast_name,
            history,
            pattern_analysis,
            recent_events,
        )

        return prediction

    async def _analyze_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """分析节目模式"""
        # 提取历史话题
        all_topics = []
        all_keywords = []
        all_guests = []
        durations = []

        for ep in history:
            all_topics.extend(ep.get("topics", []))
            all_keywords.extend(ep.get("keywords", []))
            all_guests.extend(ep.get("guests", []))
            if ep.get("duration"):
                durations.append(ep["duration"])

        # 统计频率
        topic_freq = {}
        for t in all_topics:
            topic_freq[t] = topic_freq.get(t, 0) + 1

        keyword_freq = {}
        for k in all_keywords:
            keyword_freq[k] = keyword_freq.get(k, 0) + 1

        return {
            "common_topics": sorted(topic_freq.items(), key=lambda x: x[1], reverse=True)[:10],
            "common_keywords": sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20],
            "past_guests": list(set(all_guests)),
            "avg_duration": sum(durations) / len(durations) if durations else 60,
            "episode_count": len(history),
        }

    async def _generate_prediction(
        self,
        podcast_name: str,
        history: List[Dict],
        pattern_analysis: Dict,
        recent_events: List[str] = None,
    ) -> EpisodePrediction:
        """生成预测"""
        # 获取最近几期的摘要
        recent_summaries = []
        for ep in history[-5:]:
            recent_summaries.append({
                "title": ep.get("title", ""),
                "summary": ep.get("summary", "")[:200],
                "topics": ep.get("topics", []),
            })

        prompt = f"""作为播客内容分析专家，基于以下信息预测「{podcast_name}」下一期可能讨论的内容：

最近几期内容：
{json.dumps(recent_summaries, ensure_ascii=False, indent=2)}

常见话题：{[t[0] for t in pattern_analysis['common_topics'][:5]]}
常见关键词：{[k[0] for k in pattern_analysis['common_keywords'][:10]]}
历史嘉宾：{pattern_analysis['past_guests'][:5]}
平均时长：{pattern_analysis['avg_duration']:.0f} 分钟

{f"近期相关事件：{recent_events}" if recent_events else ""}

请预测：
1. 最可能的 3 个话题（附概率和理由）
2. 可能邀请的嘉宾
3. 节目形式
4. 预计时长
5. 内容大纲

以 JSON 格式返回：
{{
  "topics": [
    {{"topic": "话题", "probability": 0.8, "reasoning": "理由", "related_past": ["相关历史话题"]}},
    ...
  ],
  "predicted_guests": ["嘉宾1", "嘉宾2"],
  "format": "访谈/独白/圆桌",
  "duration": "60分钟",
  "outline": "内容大纲...",
  "confidence": 0.75
}}"""

        response = await self._call_llm(prompt)

        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                predicted_topics = []
                for t in data.get("topics", []):
                    predicted_topics.append(PredictedTopic(
                        topic=t.get("topic", ""),
                        probability=t.get("probability", 0.5),
                        reasoning=t.get("reasoning", ""),
                        related_past_topics=t.get("related_past", []),
                    ))

                return EpisodePrediction(
                    podcast_name=podcast_name,
                    predicted_topics=predicted_topics,
                    predicted_guests=data.get("predicted_guests", []),
                    predicted_format=data.get("format", ""),
                    predicted_duration=data.get("duration", ""),
                    content_outline=data.get("outline", ""),
                    confidence=data.get("confidence", 0.5),
                )
        except Exception as e:
            logger.error(f"解析预测结果失败: {e}")

        return EpisodePrediction(
            podcast_name=podcast_name,
            predicted_topics=[],
            predicted_guests=[],
            predicted_format="未知",
            predicted_duration="未知",
            content_outline=response,
            confidence=0.3,
        )

    async def _predict_without_history(
        self,
        podcast_name: str,
        recent_events: List[str] = None,
    ) -> EpisodePrediction:
        """无历史数据时的预测"""
        prompt = f"""为播客「{podcast_name}」生成一期内容建议：

{f"可参考的近期事件：{recent_events}" if recent_events else ""}

请提供：
1. 3 个推荐话题
2. 内容大纲
3. 节目形式建议"""

        response = await self._call_llm(prompt)

        return EpisodePrediction(
            podcast_name=podcast_name,
            predicted_topics=[],
            predicted_guests=[],
            predicted_format="建议",
            predicted_duration="60分钟",
            content_outline=response,
            confidence=0.3,
        )

    async def generate_episode_script(
        self,
        podcast_name: str,
        topic: str,
        style: str = "conversational",
        duration_minutes: int = 60,
    ) -> str:
        """
        生成节目脚本

        Args:
            podcast_name: 播客名称
            topic: 主题
            style: 风格
            duration_minutes: 时长

        Returns:
            节目脚本
        """
        prompt = f"""为播客「{podcast_name}」生成一期关于「{topic}」的脚本：

风格：{style}
时长：约 {duration_minutes} 分钟

脚本应包含：
1. 开场白
2. 主题介绍
3. 主要讨论点（3-5个）
4. 听众互动环节建议
5. 总结与结尾

请生成完整脚本，包含时间标记。"""

        return await self._call_llm(prompt)

    async def suggest_follow_up_topics(
        self,
        episode_data: Dict,
        count: int = 5,
    ) -> List[str]:
        """
        建议后续话题

        Args:
            episode_data: 当前节目数据
            count: 建议数量

        Returns:
            话题列表
        """
        prompt = f"""基于以下播客节目内容，建议 {count} 个可以作为后续节目的话题：

标题：{episode_data.get('title', '')}
摘要：{episode_data.get('summary', '')}
关键词：{episode_data.get('keywords', [])}

要求：
1. 话题应与当前内容有关联
2. 但要提供新的角度或深入
3. 考虑听众可能感兴趣的方向

直接列出话题，每行一个。"""

        response = await self._call_llm(prompt)
        topics = [t.strip().lstrip("0123456789.-) ") for t in response.split("\n") if t.strip()]
        return topics[:count]

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if self.llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "你是一位资深播客内容策划专家。"},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=2000,
                )
                return response.choices[0].message.content
            else:
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic()
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
