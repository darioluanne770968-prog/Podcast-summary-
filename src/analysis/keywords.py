"""
关键词提取模块
"""

from dataclasses import dataclass
from typing import Optional, List

from .llm_client import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class Keyword:
    """关键词"""
    word: str
    category: str  # 分类（人物、概念、技术、组织等）
    relevance: float  # 相关度 0-1
    context: Optional[str] = None  # 上下文

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "category": self.category,
            "relevance": self.relevance,
            "context": self.context,
        }


class KeywordExtractor:
    """关键词提取器"""

    SYSTEM_PROMPT = """你是一个专业的内容分析师，擅长从文本中提取关键词和核心概念。

提取关键词时请：
1. 识别最重要和最具代表性的词汇
2. 对关键词进行分类（人物、概念、技术、组织、地点等）
3. 评估每个关键词的相关度
4. 避免提取过于通用的词汇"""

    CATEGORIES = [
        "人物",      # 人名、角色
        "概念",      # 抽象概念、理论
        "技术",      # 技术术语、工具
        "组织",      # 公司、机构
        "产品",      # 产品名称
        "事件",      # 事件名称
        "地点",      # 地名
        "其他",      # 其他
    ]

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """初始化关键词提取器"""
        self.llm = llm_client or LLMClient()

    def extract(
        self,
        transcript: str,
        max_keywords: int = 20,
        min_relevance: float = 0.5,
    ) -> List[Keyword]:
        """
        提取关键词

        Args:
            transcript: 转录文本
            max_keywords: 最大关键词数量
            min_relevance: 最小相关度阈值

        Returns:
            Keyword 列表
        """
        logger.info("提取关键词...")

        prompt = f"""分析以下播客转录文本，提取最重要的关键词。

文本：
---
{transcript[:30000]}
---

请提取最多 {max_keywords} 个关键词，按以下 JSON 格式输出：

```json
[
  {{"word": "关键词", "category": "分类", "relevance": 0.9, "context": "该词出现的典型上下文"}},
  ...
]
```

分类可选：{', '.join(self.CATEGORIES)}
relevance 范围：0.0-1.0，表示该词与播客主题的相关程度

只输出 JSON，不要其他内容。"""

        response = self.llm.complete(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.3,
        )

        keywords = self._parse_response(response)

        # 过滤低相关度的关键词
        keywords = [k for k in keywords if k.relevance >= min_relevance]

        # 按相关度排序
        keywords.sort(key=lambda x: x.relevance, reverse=True)

        logger.info(f"提取到 {len(keywords)} 个关键词")
        return keywords[:max_keywords]

    def _parse_response(self, response: str) -> List[Keyword]:
        """解析响应"""
        try:
            data = self.llm.parse_json_response(response)

            keywords = []
            for item in data:
                keywords.append(
                    Keyword(
                        word=item.get("word", ""),
                        category=item.get("category", "其他"),
                        relevance=float(item.get("relevance", 0.5)),
                        context=item.get("context"),
                    )
                )
            return keywords

        except Exception as e:
            logger.error(f"解析关键词响应失败: {e}")
            return []

    def extract_tags(
        self,
        transcript: str,
        max_tags: int = 10,
    ) -> List[str]:
        """
        提取标签（简化版关键词）

        Args:
            transcript: 转录文本
            max_tags: 最大标签数量

        Returns:
            标签列表
        """
        prompt = f"""分析以下播客内容，提取 {max_tags} 个最能代表内容主题的标签。

文本：
---
{transcript[:20000]}
---

要求：
1. 标签应简短（1-4个字）
2. 标签应具有代表性
3. 避免过于通用的标签

请直接输出标签，用逗号分隔，例如：人工智能, 创业, 投资"""

        response = self.llm.complete(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.3,
        )

        # 解析标签
        tags = [tag.strip() for tag in response.split(",")]
        tags = [tag for tag in tags if tag and len(tag) <= 20]

        return tags[:max_tags]

    def group_keywords_by_category(
        self,
        keywords: List[Keyword],
    ) -> dict:
        """
        按分类分组关键词

        Args:
            keywords: 关键词列表

        Returns:
            按分类分组的字典
        """
        groups = {}
        for keyword in keywords:
            if keyword.category not in groups:
                groups[keyword.category] = []
            groups[keyword.category].append(keyword)
        return groups
