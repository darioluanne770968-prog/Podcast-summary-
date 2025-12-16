"""
情感分析模块
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict

from .llm_client import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class SentimentResult:
    """情感分析结果"""
    overall_sentiment: str  # positive, negative, neutral, mixed
    overall_score: float  # -1.0 到 1.0
    confidence: float  # 置信度 0-1
    emotions: Dict[str, float]  # 情感分布
    tone: str  # 整体基调描述
    highlights: List[dict] = field(default_factory=list)  # 情感高点/低点

    def to_dict(self) -> dict:
        return {
            "overall_sentiment": self.overall_sentiment,
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "emotions": self.emotions,
            "tone": self.tone,
            "highlights": self.highlights,
        }


class SentimentAnalyzer:
    """情感分析器"""

    SYSTEM_PROMPT = """你是一个专业的情感分析师，擅长分析播客对话中的情感和语气。

分析时请：
1. 识别整体情感倾向
2. 分析各种情感的分布
3. 找出情感的高点和低点
4. 考虑上下文和文化背景"""

    EMOTIONS = [
        "喜悦",      # joy
        "兴奋",      # excitement
        "好奇",      # curiosity
        "担忧",      # concern
        "悲伤",      # sadness
        "愤怒",      # anger
        "惊讶",      # surprise
        "平静",      # calm
    ]

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """初始化情感分析器"""
        self.llm = llm_client or LLMClient()

    def analyze(
        self,
        transcript: str,
        include_highlights: bool = True,
    ) -> SentimentResult:
        """
        分析情感

        Args:
            transcript: 转录文本
            include_highlights: 是否包含情感高点/低点

        Returns:
            SentimentResult 对象
        """
        logger.info("进行情感分析...")

        highlight_instruction = ""
        if include_highlights:
            highlight_instruction = """
5. highlights: 情感高点和低点（最多5个）
   - type: "high" 或 "low"
   - text: 相关文本片段
   - emotion: 主要情感
   - description: 简短描述"""

        prompt = f"""分析以下播客转录文本的情感和语气。

文本：
---
{transcript[:25000]}
---

请按以下 JSON 格式输出分析结果：

```json
{{
  "overall_sentiment": "positive/negative/neutral/mixed",
  "overall_score": 0.5,
  "confidence": 0.8,
  "emotions": {{
    "喜悦": 0.3,
    "兴奋": 0.2,
    "好奇": 0.2,
    "担忧": 0.1,
    "悲伤": 0.0,
    "愤怒": 0.0,
    "惊讶": 0.1,
    "平静": 0.1
  }},
  "tone": "整体基调的描述（一句话）",
  "highlights": [
    {{"type": "high", "text": "...", "emotion": "喜悦", "description": "..."}}
  ]
}}
```

说明：
1. overall_score: -1.0（非常消极）到 1.0（非常积极）
2. confidence: 分析的置信度 0-1
3. emotions: 各种情感的占比（总和为1）
4. tone: 用一句话描述整体语气{highlight_instruction}

只输出 JSON，不要其他内容。"""

        response = self.llm.complete(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.3,
        )

        result = self._parse_response(response)
        logger.info(
            f"情感分析完成: {result.overall_sentiment} "
            f"(得分: {result.overall_score:.2f})"
        )
        return result

    def _parse_response(self, response: str) -> SentimentResult:
        """解析响应"""
        try:
            data = self.llm.parse_json_response(response)

            return SentimentResult(
                overall_sentiment=data.get("overall_sentiment", "neutral"),
                overall_score=float(data.get("overall_score", 0)),
                confidence=float(data.get("confidence", 0.5)),
                emotions=data.get("emotions", {}),
                tone=data.get("tone", ""),
                highlights=data.get("highlights", []),
            )

        except Exception as e:
            logger.error(f"解析情感分析响应失败: {e}")
            return SentimentResult(
                overall_sentiment="unknown",
                overall_score=0,
                confidence=0,
                emotions={},
                tone="无法分析",
            )

    def format_result(self, result: SentimentResult) -> str:
        """
        格式化情感分析结果

        Args:
            result: 情感分析结果

        Returns:
            Markdown 格式的输出
        """
        # 情感图标映射
        sentiment_icons = {
            "positive": "😊",
            "negative": "😔",
            "neutral": "😐",
            "mixed": "🤔",
        }

        icon = sentiment_icons.get(result.overall_sentiment, "❓")

        lines = [
            "## 😊 情感分析\n",
            f"**整体基调**: {icon} {result.tone}",
            f"**情感倾向**: {result.overall_sentiment} (得分: {result.overall_score:.2f})",
            f"**置信度**: {result.confidence * 100:.0f}%",
            "",
            "### 情感分布",
        ]

        # 情感分布条形图
        for emotion, score in sorted(
            result.emotions.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            bar_length = int(score * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            lines.append(f"- {emotion}: {bar} {score * 100:.0f}%")

        # 情感高点/低点
        if result.highlights:
            lines.extend(["", "### 情感亮点"])
            for h in result.highlights:
                emoji = "📈" if h.get("type") == "high" else "📉"
                lines.append(
                    f"- {emoji} **{h.get('emotion', '')}**: "
                    f"\"{h.get('text', '')[:50]}...\" - {h.get('description', '')}"
                )

        return "\n".join(lines)
