"""
问答生成模块
"""

from dataclasses import dataclass
from typing import Optional, List

from .llm_client import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class QAPair:
    """问答对"""
    question: str
    answer: str
    difficulty: str = "medium"  # easy, medium, hard
    category: Optional[str] = None
    source_timestamp: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "difficulty": self.difficulty,
            "category": self.category,
            "source_timestamp": self.source_timestamp,
        }


class QAGenerator:
    """问答生成器"""

    SYSTEM_PROMPT = """你是一个专业的教育内容设计师，擅长从播客内容中设计有价值的问答题目。

设计问答时请：
1. 问题应该有教育价值，帮助听众回顾和理解内容
2. 答案应该准确、完整但简洁
3. 覆盖播客的主要内容和关键知识点
4. 难度应该有层次，从简单到复杂"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """初始化问答生成器"""
        self.llm = llm_client or LLMClient()

    def generate(
        self,
        transcript: str,
        num_questions: int = 10,
        difficulty_distribution: Optional[dict] = None,
    ) -> List[QAPair]:
        """
        生成问答

        Args:
            transcript: 转录文本
            num_questions: 生成问题数量
            difficulty_distribution: 难度分布 {"easy": 3, "medium": 4, "hard": 3}

        Returns:
            QAPair 列表
        """
        logger.info("生成问答...")

        if difficulty_distribution:
            diff_str = f"难度分布: 简单 {difficulty_distribution.get('easy', 0)} 题, " \
                      f"中等 {difficulty_distribution.get('medium', 0)} 题, " \
                      f"困难 {difficulty_distribution.get('hard', 0)} 题"
        else:
            diff_str = "难度分布均匀"

        prompt = f"""分析以下播客转录文本，生成 {num_questions} 个有价值的问答题目。

文本：
---
{transcript[:30000]}
---

要求：
1. 问题应覆盖播客的主要内容
2. 答案应准确、完整但简洁
3. {diff_str}
4. 问题类型多样：事实型、理解型、应用型

请按以下 JSON 格式输出：

```json
[
  {{
    "question": "问题内容",
    "answer": "答案内容",
    "difficulty": "easy/medium/hard",
    "category": "问题分类（如：概念理解、事实记忆、应用分析）"
  }},
  ...
]
```

只输出 JSON，不要其他内容。"""

        response = self.llm.complete(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.5,
        )

        qa_pairs = self._parse_response(response)
        logger.info(f"生成了 {len(qa_pairs)} 个问答")
        return qa_pairs[:num_questions]

    def _parse_response(self, response: str) -> List[QAPair]:
        """解析响应"""
        try:
            data = self.llm.parse_json_response(response)

            qa_pairs = []
            for item in data:
                qa_pairs.append(
                    QAPair(
                        question=item.get("question", ""),
                        answer=item.get("answer", ""),
                        difficulty=item.get("difficulty", "medium"),
                        category=item.get("category"),
                    )
                )
            return qa_pairs

        except Exception as e:
            logger.error(f"解析问答响应失败: {e}")
            return []

    def generate_flashcards(
        self,
        transcript: str,
        num_cards: int = 20,
    ) -> List[QAPair]:
        """
        生成闪卡（用于记忆复习）

        Args:
            transcript: 转录文本
            num_cards: 闪卡数量

        Returns:
            QAPair 列表（简化版）
        """
        prompt = f"""分析以下播客转录文本，生成 {num_cards} 张闪卡用于复习。

文本：
---
{transcript[:25000]}
---

要求：
1. 正面是简短的提示或问题
2. 背面是关键信息或答案
3. 每张卡片聚焦一个知识点
4. 适合快速复习和记忆

请按以下 JSON 格式输出：

```json
[
  {{"question": "卡片正面（提示/问题）", "answer": "卡片背面（答案/解释）"}},
  ...
]
```

只输出 JSON，不要其他内容。"""

        response = self.llm.complete(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.4,
        )

        return self._parse_response(response)[:num_cards]

    def format_qa(
        self,
        qa_pairs: List[QAPair],
        style: str = "markdown",
        show_answers: bool = True,
    ) -> str:
        """
        格式化问答输出

        Args:
            qa_pairs: 问答列表
            style: 输出样式
            show_answers: 是否显示答案

        Returns:
            格式化的文本
        """
        lines = ["## ❓ 问答复习\n"]

        for i, qa in enumerate(qa_pairs, 1):
            difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(
                qa.difficulty, "⚪"
            )

            lines.append(f"### Q{i}. {qa.question} {difficulty_emoji}")

            if show_answers:
                lines.append(f"\n**A:** {qa.answer}")

            if qa.category:
                lines.append(f"\n*分类: {qa.category}*")

            lines.append("")

        return "\n".join(lines)
