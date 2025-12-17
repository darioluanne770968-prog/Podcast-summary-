"""
事实核查模块

验证播客中提到的事实、数据、引用
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from ..analysis import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


class VerificationStatus(str, Enum):
    """验证状态"""
    VERIFIED = "verified"  # 已验证为真
    FALSE = "false"  # 已验证为假
    PARTIALLY_TRUE = "partially_true"  # 部分真实
    UNVERIFIABLE = "unverifiable"  # 无法验证
    NEEDS_CONTEXT = "needs_context"  # 需要更多上下文
    OUTDATED = "outdated"  # 信息过时


@dataclass
class FactCheckResult:
    """事实核查结果"""
    claim: str  # 原始声明
    status: VerificationStatus
    confidence: float  # 置信度 0-1
    explanation: str  # 解释
    sources: List[str] = field(default_factory=list)  # 参考来源
    corrected_info: Optional[str] = None  # 更正后的信息
    timestamp: Optional[float] = None  # 声明出现的时间

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "status": self.status.value,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "sources": self.sources,
            "corrected_info": self.corrected_info,
            "timestamp": self.timestamp,
        }


class FactChecker:
    """事实核查器"""

    SYSTEM_PROMPT = """你是一个专业的事实核查员。你的任务是验证播客内容中的事实性声明。

核查原则：
1. 区分事实性声明和观点/意见
2. 只核查可验证的事实（数据、日期、事件、引用等）
3. 提供明确的验证状态和解释
4. 如果信息可能过时，说明最新情况
5. 保持客观中立

验证状态说明：
- verified: 声明完全准确
- false: 声明不准确
- partially_true: 部分准确，部分不准确
- unverifiable: 无法确定真假
- needs_context: 需要更多上下文才能判断
- outdated: 信息曾经准确但已过时"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enable_web_search: bool = True,
    ):
        self.llm = llm_client or LLMClient()
        self.enable_web_search = enable_web_search

    def check(
        self,
        transcript: str,
        focus_topics: Optional[List[str]] = None,
    ) -> List[FactCheckResult]:
        """
        对转录文本进行事实核查

        Args:
            transcript: 转录文本
            focus_topics: 重点关注的主题

        Returns:
            FactCheckResult 列表
        """
        logger.info("开始事实核查...")

        # 1. 提取事实性声明
        claims = self._extract_claims(transcript, focus_topics)
        logger.info(f"提取到 {len(claims)} 个事实性声明")

        # 2. 核查每个声明
        results = []
        for claim in claims:
            result = self._verify_claim(claim)
            results.append(result)

        # 按置信度排序，可疑的排前面
        results.sort(key=lambda x: (
            0 if x.status in [VerificationStatus.FALSE, VerificationStatus.PARTIALLY_TRUE] else 1,
            -x.confidence
        ))

        logger.info(f"事实核查完成，{sum(1 for r in results if r.status == VerificationStatus.FALSE)} 个声明存疑")
        return results

    def _extract_claims(
        self,
        transcript: str,
        focus_topics: Optional[List[str]] = None,
    ) -> List[dict]:
        """提取事实性声明"""
        focus_str = f"重点关注以下主题相关的声明：{', '.join(focus_topics)}" if focus_topics else ""

        prompt = f"""分析以下播客转录文本，提取所有需要事实核查的声明。

{focus_str}

只提取事实性声明，包括：
- 统计数据和数字
- 历史事件和日期
- 科学事实和研究结论
- 人物引用和言论
- 公司/产品信息

不要提取：
- 个人观点和意见
- 预测和推测
- 通用常识

文本：
---
{transcript[:25000]}
---

请按以下 JSON 格式输出：

```json
[
  {{
    "claim": "需要核查的声明",
    "type": "statistic/date/quote/fact/research",
    "context": "声明的上下文",
    "timestamp": 123.5
  }}
]
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.2)
            return self.llm.parse_json_response(response)
        except Exception as e:
            logger.error(f"提取声明失败: {e}")
            return []

    def _verify_claim(self, claim_data: dict) -> FactCheckResult:
        """验证单个声明"""
        claim = claim_data.get("claim", "")
        claim_type = claim_data.get("type", "fact")
        context = claim_data.get("context", "")

        prompt = f"""核查以下声明的准确性：

声明："{claim}"
类型：{claim_type}
上下文：{context}

请基于你的知识进行核查，并按以下 JSON 格式回复：

```json
{{
  "status": "verified/false/partially_true/unverifiable/needs_context/outdated",
  "confidence": 0.8,
  "explanation": "详细解释为什么给出这个判断",
  "corrected_info": "如果声明不准确，提供正确信息（可选）",
  "sources": ["可能的参考来源"]
}}
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.1)
            data = self.llm.parse_json_response(response)

            return FactCheckResult(
                claim=claim,
                status=VerificationStatus(data.get("status", "unverifiable")),
                confidence=float(data.get("confidence", 0.5)),
                explanation=data.get("explanation", ""),
                sources=data.get("sources", []),
                corrected_info=data.get("corrected_info"),
                timestamp=claim_data.get("timestamp"),
            )
        except Exception as e:
            logger.error(f"核查声明失败: {e}")
            return FactCheckResult(
                claim=claim,
                status=VerificationStatus.UNVERIFIABLE,
                confidence=0.0,
                explanation=f"核查过程出错: {e}",
            )

    def generate_report(self, results: List[FactCheckResult]) -> str:
        """生成事实核查报告"""
        lines = ["## 📋 事实核查报告\n"]

        # 统计
        status_counts = {}
        for r in results:
            status_counts[r.status] = status_counts.get(r.status, 0) + 1

        lines.append("### 核查统计\n")
        status_emoji = {
            VerificationStatus.VERIFIED: "✅",
            VerificationStatus.FALSE: "❌",
            VerificationStatus.PARTIALLY_TRUE: "⚠️",
            VerificationStatus.UNVERIFIABLE: "❓",
            VerificationStatus.NEEDS_CONTEXT: "📝",
            VerificationStatus.OUTDATED: "📅",
        }

        for status, count in status_counts.items():
            emoji = status_emoji.get(status, "•")
            lines.append(f"- {emoji} {status.value}: {count}")

        lines.append("\n### 详细结果\n")

        # 先显示有问题的
        for r in results:
            emoji = status_emoji.get(r.status, "•")
            lines.append(f"#### {emoji} {r.claim[:80]}...")
            lines.append(f"**状态**: {r.status.value} (置信度: {r.confidence:.0%})")
            lines.append(f"**解释**: {r.explanation}")

            if r.corrected_info:
                lines.append(f"**更正**: {r.corrected_info}")

            if r.sources:
                lines.append(f"**参考**: {', '.join(r.sources)}")

            lines.append("")

        return "\n".join(lines)
