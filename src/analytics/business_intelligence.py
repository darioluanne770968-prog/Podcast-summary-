"""
播客商业智能模块

广告效果分析、赞助商匹配、竞品监控
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import re

from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class SponsorAnalysis:
    """赞助商分析"""
    sponsor_name: str
    podcast_name: str
    episode_title: str
    ad_type: str  # pre-roll, mid-roll, post-roll, host-read, scripted
    duration_seconds: float
    timestamp: float
    naturalness_score: float  # 广告自然度 0-1
    transcript: str = ""
    sentiment: float = 0.5
    cta_detected: bool = False
    promo_code: str = ""


@dataclass
class CompetitorInsight:
    """竞品洞察"""
    competitor_name: str
    topic: str
    mention_type: str  # positive, negative, neutral, comparison
    context: str
    podcast_name: str
    date: str


class BusinessIntelligence:
    """
    商业智能分析

    功能：
    - 广告效果分析
    - 赞助商匹配推荐
    - 竞品监控
    - 变现潜力评估
    """

    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        self._sponsor_history: List[SponsorAnalysis] = []
        self._competitor_mentions: List[CompetitorInsight] = []

    async def detect_advertisements(
        self,
        transcript: str,
        timestamps: List[Dict] = None,
    ) -> List[SponsorAnalysis]:
        """
        检测广告

        Args:
            transcript: 转录文本
            timestamps: 时间戳列表

        Returns:
            广告分析列表
        """
        # 广告关键词
        ad_keywords = [
            "今天的节目由", "感谢赞助", "sponsored by", "brought to you",
            "优惠码", "promo code", "折扣码", "使用链接",
            "这期节目的赞助商", "插播广告",
        ]

        ads = []

        # 使用 LLM 进行更精确的检测
        prompt = f"""分析以下播客转录，找出所有广告/赞助内容：

转录文本：
{transcript[:5000]}

对于每个广告，请提供：
1. 赞助商名称
2. 广告类型 (pre-roll/mid-roll/post-roll/host-read/scripted)
3. 广告文本
4. 自然度评分 (0-1，越自然越高)
5. 是否有优惠码
6. 优惠码内容（如有）

返回 JSON 格式：
[
  {{
    "sponsor": "品牌名",
    "type": "mid-roll",
    "text": "广告文本",
    "naturalness": 0.8,
    "has_promo": true,
    "promo_code": "PODCAST20"
  }}
]

如果没有广告，返回空数组 []"""

        try:
            response = await self._call_llm(prompt)
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                for item in data:
                    ads.append(SponsorAnalysis(
                        sponsor_name=item.get("sponsor", ""),
                        podcast_name="",
                        episode_title="",
                        ad_type=item.get("type", "mid-roll"),
                        duration_seconds=0,
                        timestamp=0,
                        naturalness_score=item.get("naturalness", 0.5),
                        transcript=item.get("text", ""),
                        cta_detected=item.get("has_promo", False),
                        promo_code=item.get("promo_code", ""),
                    ))
        except Exception as e:
            logger.error(f"广告检测失败: {e}")

        return ads

    async def analyze_ad_effectiveness(
        self,
        sponsor_data: List[SponsorAnalysis],
    ) -> Dict[str, Any]:
        """
        分析广告效果

        Args:
            sponsor_data: 赞助商数据

        Returns:
            效果分析
        """
        if not sponsor_data:
            return {"error": "无广告数据"}

        # 按赞助商分组
        by_sponsor: Dict[str, List[SponsorAnalysis]] = {}
        for ad in sponsor_data:
            if ad.sponsor_name not in by_sponsor:
                by_sponsor[ad.sponsor_name] = []
            by_sponsor[ad.sponsor_name].append(ad)

        analysis = {
            "total_ads": len(sponsor_data),
            "unique_sponsors": len(by_sponsor),
            "sponsors": [],
        }

        for sponsor, ads in by_sponsor.items():
            avg_naturalness = sum(a.naturalness_score for a in ads) / len(ads)
            promo_rate = sum(1 for a in ads if a.cta_detected) / len(ads)

            analysis["sponsors"].append({
                "name": sponsor,
                "ad_count": len(ads),
                "avg_naturalness": avg_naturalness,
                "promo_code_rate": promo_rate,
                "ad_types": list(set(a.ad_type for a in ads)),
            })

        return analysis

    async def recommend_sponsors(
        self,
        podcast_profile: Dict,
        budget_range: str = "medium",
    ) -> List[Dict]:
        """
        推荐潜在赞助商

        Args:
            podcast_profile: 播客档案
            budget_range: 预算范围 (low/medium/high)

        Returns:
            推荐列表
        """
        prompt = f"""基于以下播客档案，推荐 5 个合适的潜在赞助商：

播客信息：
- 名称：{podcast_profile.get('name', '')}
- 话题：{podcast_profile.get('topics', [])}
- 听众画像：{podcast_profile.get('audience', '')}
- 预算范围：{budget_range}

请推荐与播客调性匹配的品牌/产品，返回 JSON：
[
  {{
    "brand": "品牌名",
    "category": "类别",
    "reason": "推荐理由",
    "ad_format": "建议的广告形式",
    "match_score": 0.85
  }}
]"""

        try:
            response = await self._call_llm(prompt)
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"赞助商推荐失败: {e}")

        return []

    def track_competitor(
        self,
        competitor_name: str,
        mention_context: str,
        mention_type: str,
        podcast_name: str,
    ):
        """追踪竞品提及"""
        insight = CompetitorInsight(
            competitor_name=competitor_name,
            topic="",
            mention_type=mention_type,
            context=mention_context,
            podcast_name=podcast_name,
            date=datetime.now().isoformat(),
        )
        self._competitor_mentions.append(insight)

    async def detect_competitor_mentions(
        self,
        transcript: str,
        competitors: List[str],
        podcast_name: str,
    ) -> List[CompetitorInsight]:
        """
        检测竞品提及

        Args:
            transcript: 转录文本
            competitors: 竞品列表
            podcast_name: 播客名称

        Returns:
            竞品洞察列表
        """
        if not competitors:
            return []

        prompt = f"""在以下播客转录中，找出对这些品牌/产品的提及：
竞品列表：{competitors}

转录文本：
{transcript[:4000]}

对于每个提及，分析：
1. 品牌名称
2. 提及类型 (positive/negative/neutral/comparison)
3. 上下文

返回 JSON：
[
  {{"brand": "品牌", "type": "positive", "context": "具体内容"}}
]"""

        insights = []
        try:
            response = await self._call_llm(prompt)
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                for item in data:
                    insight = CompetitorInsight(
                        competitor_name=item.get("brand", ""),
                        topic="",
                        mention_type=item.get("type", "neutral"),
                        context=item.get("context", ""),
                        podcast_name=podcast_name,
                        date=datetime.now().isoformat(),
                    )
                    insights.append(insight)
                    self._competitor_mentions.append(insight)
        except Exception as e:
            logger.error(f"竞品检测失败: {e}")

        return insights

    def get_competitor_report(
        self,
        competitor_name: str,
    ) -> Dict[str, Any]:
        """
        获取竞品报告

        Args:
            competitor_name: 竞品名称

        Returns:
            报告
        """
        mentions = [
            m for m in self._competitor_mentions
            if m.competitor_name.lower() == competitor_name.lower()
        ]

        if not mentions:
            return {"competitor": competitor_name, "mentions": 0}

        type_counts = {}
        for m in mentions:
            type_counts[m.mention_type] = type_counts.get(m.mention_type, 0) + 1

        return {
            "competitor": competitor_name,
            "total_mentions": len(mentions),
            "mention_types": type_counts,
            "podcasts_mentioning": list(set(m.podcast_name for m in mentions)),
            "recent_mentions": [
                {
                    "podcast": m.podcast_name,
                    "type": m.mention_type,
                    "context": m.context[:100],
                    "date": m.date,
                }
                for m in sorted(mentions, key=lambda x: x.date, reverse=True)[:5]
            ],
            "sentiment_distribution": {
                "positive": type_counts.get("positive", 0),
                "negative": type_counts.get("negative", 0),
                "neutral": type_counts.get("neutral", 0),
            },
        }

    async def evaluate_monetization_potential(
        self,
        podcast_data: Dict,
    ) -> Dict[str, Any]:
        """
        评估变现潜力

        Args:
            podcast_data: 播客数据

        Returns:
            变现评估
        """
        prompt = f"""评估以下播客的商业变现潜力：

播客信息：
{json.dumps(podcast_data, ensure_ascii=False, indent=2)}

请评估：
1. 整体商业价值 (1-10)
2. 适合的变现方式
3. 预估 CPM 范围
4. 最匹配的行业/品类
5. 增长建议

返回 JSON 格式。"""

        try:
            response = await self._call_llm(prompt)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"变现评估失败: {e}")

        return {
            "commercial_value": 5,
            "monetization_methods": ["广告", "付费订阅"],
            "analysis": "评估失败",
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_ads_tracked": len(self._sponsor_history),
            "total_competitor_mentions": len(self._competitor_mentions),
            "unique_sponsors": len(set(a.sponsor_name for a in self._sponsor_history)),
            "unique_competitors": len(set(m.competitor_name for m in self._competitor_mentions)),
        }

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if self.llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "你是播客商业分析专家。"},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1500,
                )
                return response.choices[0].message.content
            else:
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic()
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
