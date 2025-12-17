"""
观点对比分析模块

分析播客中不同说话人的观点差异
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict

from ..analysis import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class Opinion:
    """观点"""
    speaker: str
    topic: str
    stance: str  # positive, negative, neutral, mixed
    summary: str
    key_arguments: List[str] = field(default_factory=list)
    confidence: float = 1.0
    timestamps: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "topic": self.topic,
            "stance": self.stance,
            "summary": self.summary,
            "key_arguments": self.key_arguments,
            "confidence": self.confidence,
            "timestamps": self.timestamps,
        }


@dataclass
class OpinionComparison:
    """观点对比"""
    topic: str
    opinions: List[Opinion]
    agreement_level: float  # 0-1，1表示完全一致
    key_differences: List[str]
    key_agreements: List[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "opinions": [o.to_dict() for o in self.opinions],
            "agreement_level": self.agreement_level,
            "key_differences": self.key_differences,
            "key_agreements": self.key_agreements,
            "summary": self.summary,
        }


class OpinionAnalyzer:
    """观点分析器"""

    SYSTEM_PROMPT = """你是一个专业的辩论分析师，擅长分析和对比不同人的观点。

分析原则：
1. 客观中立，不偏向任何一方
2. 准确识别观点的立场（支持/反对/中立/复杂）
3. 提取支持观点的关键论据
4. 识别观点之间的共识和分歧
5. 考虑观点的语境和前提"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def analyze_opinions(
        self,
        transcript_with_speakers: str,
        topics: Optional[List[str]] = None,
    ) -> List[OpinionComparison]:
        """
        分析播客中的观点

        Args:
            transcript_with_speakers: 带说话人标记的转录文本
            topics: 要分析的话题（None 表示自动识别）

        Returns:
            OpinionComparison 列表
        """
        logger.info("开始观点分析...")

        # 1. 识别话题（如果未指定）
        if not topics:
            topics = self._identify_topics(transcript_with_speakers)

        # 2. 分析每个话题的观点
        comparisons = []
        for topic in topics:
            comparison = self._analyze_topic_opinions(transcript_with_speakers, topic)
            if comparison:
                comparisons.append(comparison)

        logger.info(f"分析了 {len(comparisons)} 个话题的观点")
        return comparisons

    def _identify_topics(self, transcript: str) -> List[str]:
        """识别讨论的主要话题"""
        prompt = f"""分析以下播客转录文本，识别讨论的主要话题（特别是有争议或有不同观点的话题）。

文本：
---
{transcript[:20000]}
---

请列出 3-5 个主要话题，按以下 JSON 格式输出：

```json
["话题1", "话题2", "话题3"]
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.3)
            return self.llm.parse_json_response(response)
        except Exception as e:
            logger.error(f"识别话题失败: {e}")
            return []

    def _analyze_topic_opinions(
        self,
        transcript: str,
        topic: str,
    ) -> Optional[OpinionComparison]:
        """分析特定话题的观点"""
        prompt = f"""分析以下播客转录文本中，各位说话人对于"{topic}"这个话题的观点。

文本：
---
{transcript[:25000]}
---

请分析每位说话人的观点，并对比差异。按以下 JSON 格式输出：

```json
{{
  "topic": "{topic}",
  "opinions": [
    {{
      "speaker": "说话人名称",
      "stance": "positive/negative/neutral/mixed",
      "summary": "观点摘要",
      "key_arguments": ["论据1", "论据2"]
    }}
  ],
  "agreement_level": 0.7,
  "key_differences": ["分歧点1", "分歧点2"],
  "key_agreements": ["共识点1", "共识点2"],
  "summary": "总体对比分析"
}}
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.3)
            data = self.llm.parse_json_response(response)

            opinions = [
                Opinion(
                    speaker=o.get("speaker", ""),
                    topic=topic,
                    stance=o.get("stance", "neutral"),
                    summary=o.get("summary", ""),
                    key_arguments=o.get("key_arguments", []),
                )
                for o in data.get("opinions", [])
            ]

            return OpinionComparison(
                topic=data.get("topic", topic),
                opinions=opinions,
                agreement_level=float(data.get("agreement_level", 0.5)),
                key_differences=data.get("key_differences", []),
                key_agreements=data.get("key_agreements", []),
                summary=data.get("summary", ""),
            )

        except Exception as e:
            logger.error(f"分析话题观点失败: {e}")
            return None

    def generate_debate_summary(self, comparisons: List[OpinionComparison]) -> str:
        """生成辩论/讨论摘要"""
        lines = ["## 🗣️ 观点对比分析\n"]

        for comp in comparisons:
            lines.append(f"### 📌 {comp.topic}\n")

            # 一致性指标
            agreement_bar = "█" * int(comp.agreement_level * 10) + "░" * (10 - int(comp.agreement_level * 10))
            lines.append(f"**观点一致性**: {agreement_bar} {comp.agreement_level:.0%}\n")

            # 各方观点
            lines.append("**各方观点**:\n")
            stance_emoji = {
                "positive": "👍",
                "negative": "👎",
                "neutral": "➖",
                "mixed": "🔄",
            }

            for opinion in comp.opinions:
                emoji = stance_emoji.get(opinion.stance, "•")
                lines.append(f"- {emoji} **{opinion.speaker}** ({opinion.stance})")
                lines.append(f"  - {opinion.summary}")
                if opinion.key_arguments:
                    for arg in opinion.key_arguments[:2]:
                        lines.append(f"    - 论据: {arg}")

            # 共识与分歧
            if comp.key_agreements:
                lines.append("\n**✅ 共识**:")
                for a in comp.key_agreements:
                    lines.append(f"- {a}")

            if comp.key_differences:
                lines.append("\n**❌ 分歧**:")
                for d in comp.key_differences:
                    lines.append(f"- {d}")

            lines.append(f"\n**总结**: {comp.summary}\n")
            lines.append("---\n")

        return "\n".join(lines)

    def find_controversial_topics(
        self,
        comparisons: List[OpinionComparison],
        threshold: float = 0.5,
    ) -> List[OpinionComparison]:
        """找出争议性话题（一致性低于阈值的）"""
        return [c for c in comparisons if c.agreement_level < threshold]
