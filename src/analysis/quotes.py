"""
金句提取模块
"""

from dataclasses import dataclass
from typing import Optional, List

from .llm_client import LLMClient
from ..utils import get_logger, format_timestamp

logger = get_logger(__name__)


@dataclass
class Quote:
    """金句"""
    text: str
    speaker: Optional[str] = None
    timestamp: Optional[float] = None
    context: Optional[str] = None
    category: Optional[str] = None  # 励志、洞见、幽默等

    @property
    def timestamp_formatted(self) -> str:
        return format_timestamp(self.timestamp) if self.timestamp else ""

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "speaker": self.speaker,
            "timestamp": self.timestamp,
            "timestamp_formatted": self.timestamp_formatted,
            "context": self.context,
            "category": self.category,
        }


class QuoteExtractor:
    """金句提取器"""

    SYSTEM_PROMPT = """你是一个专业的内容编辑，擅长从播客对话中提取精彩的金句和观点。

提取金句时请：
1. 选择有洞察力、有深度的观点
2. 选择表达精炼、令人印象深刻的语句
3. 选择能够独立理解、具有传播价值的内容
4. 保持原话的精确性，不要改写"""

    CATEGORIES = [
        "洞见",      # 深刻的见解
        "励志",      # 激励人心的话
        "幽默",      # 有趣的表达
        "警句",      # 警示性的话
        "金句",      # 精彩的表达
        "观点",      # 独特的观点
    ]

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """初始化金句提取器"""
        self.llm = llm_client or LLMClient()

    def extract(
        self,
        transcript_with_timestamps: str,
        max_quotes: int = 10,
        speaker_names: Optional[dict] = None,
    ) -> List[Quote]:
        """
        提取金句

        Args:
            transcript_with_timestamps: 带时间戳的转录文本
            max_quotes: 最大金句数量
            speaker_names: 说话人名称映射

        Returns:
            Quote 列表
        """
        logger.info("提取金句...")

        prompt = f"""分析以下播客转录文本，提取最精彩的金句和观点。

文本：
---
{transcript_with_timestamps[:30000]}
---

要求：
1. 提取 {max_quotes} 条最精彩的金句
2. 保持原话，不要改写
3. 优先选择有洞察力、令人印象深刻的内容

请按以下 JSON 格式输出：

```json
[
  {{
    "text": "金句原文",
    "speaker": "说话人（如果能识别）",
    "timestamp": 123.5,
    "context": "简短说明这句话的背景",
    "category": "分类"
  }},
  ...
]
```

分类可选：{', '.join(self.CATEGORIES)}
timestamp 使用秒数（从时间戳中提取）

只输出 JSON，不要其他内容。"""

        response = self.llm.complete(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.4,
        )

        quotes = self._parse_response(response)

        # 应用说话人名称映射
        if speaker_names:
            for quote in quotes:
                if quote.speaker and quote.speaker in speaker_names:
                    quote.speaker = speaker_names[quote.speaker]

        logger.info(f"提取到 {len(quotes)} 条金句")
        return quotes[:max_quotes]

    def _parse_response(self, response: str) -> List[Quote]:
        """解析响应"""
        try:
            data = self.llm.parse_json_response(response)

            quotes = []
            for item in data:
                quotes.append(
                    Quote(
                        text=item.get("text", ""),
                        speaker=item.get("speaker"),
                        timestamp=float(item.get("timestamp", 0)) if item.get("timestamp") else None,
                        context=item.get("context"),
                        category=item.get("category", "金句"),
                    )
                )
            return quotes

        except Exception as e:
            logger.error(f"解析金句响应失败: {e}")
            return []

    def format_quotes(
        self,
        quotes: List[Quote],
        style: str = "markdown",
    ) -> str:
        """
        格式化金句输出

        Args:
            quotes: 金句列表
            style: 输出样式 (markdown, plain)

        Returns:
            格式化的文本
        """
        if style == "markdown":
            lines = ["## 💬 金句摘录\n"]
            for quote in quotes:
                speaker_part = f" — {quote.speaker}" if quote.speaker else ""
                time_part = f" [{quote.timestamp_formatted}]" if quote.timestamp else ""
                lines.append(f"> \"{quote.text}\"{speaker_part}{time_part}")
                if quote.context:
                    lines.append(f"> *{quote.context}*")
                lines.append("")
            return "\n".join(lines)
        else:
            lines = []
            for quote in quotes:
                speaker_part = f" — {quote.speaker}" if quote.speaker else ""
                lines.append(f"\"{quote.text}\"{speaker_part}")
            return "\n".join(lines)
