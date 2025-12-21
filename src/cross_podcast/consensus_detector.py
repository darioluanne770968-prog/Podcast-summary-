"""
共识与矛盾检测模块

发现多个播客间的共识和冲突
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class Consensus:
    """共识"""
    id: str
    topic: str
    consensus_statement: str
    supporting_viewpoints: List[Dict]  # 支持的观点列表
    confidence: float
    podcasts_involved: List[str]
    speakers_involved: List[str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "consensus_statement": self.consensus_statement,
            "supporting_viewpoints": self.supporting_viewpoints,
            "confidence": self.confidence,
            "podcasts_involved": self.podcasts_involved,
            "speakers_involved": self.speakers_involved,
            "agreement_count": len(self.supporting_viewpoints),
            "created_at": self.created_at,
        }


@dataclass
class Contradiction:
    """矛盾"""
    id: str
    topic: str
    position_a: Dict  # 立场 A
    position_b: Dict  # 立场 B
    nature: str  # direct（直接矛盾）, partial（部分矛盾）, nuanced（细微差异）
    analysis: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "position_a": self.position_a,
            "position_b": self.position_b,
            "nature": self.nature,
            "analysis": self.analysis,
            "created_at": self.created_at,
        }


class ConsensusDetector:
    """
    共识与矛盾检测器

    功能：
    - 检测跨播客共识
    - 发现观点矛盾
    - 分析分歧原因
    """

    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        self._consensus_cache: List[Consensus] = []
        self._contradiction_cache: List[Contradiction] = []

    async def detect_consensus(
        self,
        viewpoints: List[Dict],
        min_agreement: int = 3,
    ) -> List[Consensus]:
        """
        检测共识

        Args:
            viewpoints: 观点列表 [{speaker, podcast, viewpoint, topic}]
            min_agreement: 最少需要几人同意

        Returns:
            共识列表
        """
        if len(viewpoints) < min_agreement:
            return []

        # 按话题分组
        by_topic: Dict[str, List[Dict]] = {}
        for vp in viewpoints:
            topic = vp.get("topic", "general")
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(vp)

        consensus_list = []

        for topic, topic_viewpoints in by_topic.items():
            if len(topic_viewpoints) < min_agreement:
                continue

            # 使用 LLM 分析共识
            detected = await self._analyze_consensus(topic, topic_viewpoints)
            consensus_list.extend(detected)

        self._consensus_cache.extend(consensus_list)
        return consensus_list

    async def _analyze_consensus(
        self,
        topic: str,
        viewpoints: List[Dict],
    ) -> List[Consensus]:
        """分析话题共识"""
        vp_text = "\n".join([
            f"- {vp.get('speaker', '未知')}（{vp.get('podcast', '')}）：{vp.get('viewpoint', '')}"
            for vp in viewpoints
        ])

        prompt = f"""分析以下关于「{topic}」的多个观点，找出共识：

观点列表：
{vp_text}

请找出至少 3 人以上达成共识的观点。
以 JSON 格式返回：
[
  {{
    "consensus": "共识内容",
    "supporters": ["说话人1", "说话人2"],
    "confidence": 0.8
  }}
]

如果没有明显共识，返回空数组 []"""

        response = await self._call_llm(prompt)

        try:
            import re
            import uuid
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                results = []
                for item in data:
                    supporters = item.get("supporters", [])
                    if len(supporters) >= 3:
                        results.append(Consensus(
                            id=str(uuid.uuid4())[:8],
                            topic=topic,
                            consensus_statement=item.get("consensus", ""),
                            supporting_viewpoints=[
                                vp for vp in viewpoints
                                if vp.get("speaker", "") in supporters
                            ],
                            confidence=item.get("confidence", 0.5),
                            podcasts_involved=list(set(
                                vp.get("podcast", "") for vp in viewpoints
                                if vp.get("speaker", "") in supporters
                            )),
                            speakers_involved=supporters,
                        ))
                return results
        except Exception as e:
            logger.error(f"解析共识结果失败: {e}")

        return []

    async def detect_contradictions(
        self,
        viewpoints: List[Dict],
    ) -> List[Contradiction]:
        """
        检测矛盾

        Args:
            viewpoints: 观点列表

        Returns:
            矛盾列表
        """
        if len(viewpoints) < 2:
            return []

        # 按话题分组
        by_topic: Dict[str, List[Dict]] = {}
        for vp in viewpoints:
            topic = vp.get("topic", "general")
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(vp)

        contradictions = []

        for topic, topic_viewpoints in by_topic.items():
            if len(topic_viewpoints) < 2:
                continue

            detected = await self._analyze_contradictions(topic, topic_viewpoints)
            contradictions.extend(detected)

        self._contradiction_cache.extend(contradictions)
        return contradictions

    async def _analyze_contradictions(
        self,
        topic: str,
        viewpoints: List[Dict],
    ) -> List[Contradiction]:
        """分析话题矛盾"""
        vp_text = "\n".join([
            f"{i + 1}. {vp.get('speaker', '未知')}（{vp.get('podcast', '')}）：{vp.get('viewpoint', '')}"
            for i, vp in enumerate(viewpoints)
        ])

        prompt = f"""分析以下关于「{topic}」的观点，找出矛盾或冲突：

观点列表：
{vp_text}

请找出互相矛盾的观点对。
以 JSON 格式返回：
[
  {{
    "viewpoint_a_index": 1,
    "viewpoint_b_index": 2,
    "nature": "direct/partial/nuanced",
    "analysis": "矛盾分析"
  }}
]

nature 说明：
- direct: 直接矛盾，完全对立
- partial: 部分矛盾，有些方面冲突
- nuanced: 细微差异，视角不同

如果没有矛盾，返回空数组 []"""

        response = await self._call_llm(prompt)

        try:
            import re
            import uuid
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                results = []
                for item in data:
                    idx_a = item.get("viewpoint_a_index", 1) - 1
                    idx_b = item.get("viewpoint_b_index", 2) - 1

                    if 0 <= idx_a < len(viewpoints) and 0 <= idx_b < len(viewpoints):
                        results.append(Contradiction(
                            id=str(uuid.uuid4())[:8],
                            topic=topic,
                            position_a=viewpoints[idx_a],
                            position_b=viewpoints[idx_b],
                            nature=item.get("nature", "partial"),
                            analysis=item.get("analysis", ""),
                        ))
                return results
        except Exception as e:
            logger.error(f"解析矛盾结果失败: {e}")

        return []

    async def analyze_disagreement(
        self,
        position_a: str,
        position_b: str,
    ) -> Dict[str, Any]:
        """
        深入分析分歧

        Args:
            position_a: 立场 A
            position_b: 立场 B

        Returns:
            分歧分析
        """
        prompt = f"""深入分析以下两个对立观点：

观点 A：{position_a}
观点 B：{position_b}

请分析：
1. 核心分歧点
2. 各自的合理之处
3. 各自的局限性
4. 可能的共识基础
5. 如何调和或取舍

以结构化方式回答。"""

        response = await self._call_llm(prompt)

        return {
            "position_a": position_a,
            "position_b": position_b,
            "analysis": response,
        }

    async def find_emerging_consensus(
        self,
        topic: str,
        time_range: str = "recent",
    ) -> Dict[str, Any]:
        """
        发现正在形成的共识

        Args:
            topic: 话题
            time_range: 时间范围

        Returns:
            新兴共识分析
        """
        recent_consensus = [
            c for c in self._consensus_cache
            if c.topic.lower() == topic.lower()
        ]

        if not recent_consensus:
            return {
                "topic": topic,
                "emerging_consensus": None,
                "message": "暂无足够数据分析新兴共识",
            }

        # 分析趋势
        return {
            "topic": topic,
            "recent_consensus_count": len(recent_consensus),
            "consensus_examples": [c.to_dict() for c in recent_consensus[:3]],
            "trend": "forming" if len(recent_consensus) > 2 else "uncertain",
        }

    async def generate_debate_summary(
        self,
        topic: str,
    ) -> str:
        """
        生成辩论摘要

        Args:
            topic: 话题

        Returns:
            辩论摘要
        """
        consensus = [c for c in self._consensus_cache if c.topic.lower() == topic.lower()]
        contradictions = [c for c in self._contradiction_cache if c.topic.lower() == topic.lower()]

        prompt = f"""基于以下信息，生成关于「{topic}」的播客圈辩论摘要：

已达成的共识：
{json.dumps([c.to_dict() for c in consensus], ensure_ascii=False)}

存在的矛盾：
{json.dumps([c.to_dict() for c in contradictions], ensure_ascii=False)}

请生成一份简洁的辩论摘要，包括：
1. 主要共识点
2. 主要分歧点
3. 各方立场概述
4. 未来可能的发展方向"""

        return await self._call_llm(prompt)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_consensus": len(self._consensus_cache),
            "total_contradictions": len(self._contradiction_cache),
            "topics_with_consensus": len(set(c.topic for c in self._consensus_cache)),
            "topics_with_contradictions": len(set(c.topic for c in self._contradiction_cache)),
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
                        {"role": "system", "content": "你是一位擅长分析观点关系的专家。"},
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
            return f"分析出错: {str(e)}"
