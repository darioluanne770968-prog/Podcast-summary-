"""
实体识别模块

识别播客中的人名、组织、产品、地点等实体
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum

from ..analysis import LLMClient
from ..utils import get_logger, format_timestamp

logger = get_logger(__name__)


class EntityType(str, Enum):
    """实体类型"""
    PERSON = "person"
    ORGANIZATION = "organization"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    LOCATION = "location"
    EVENT = "event"
    DATE = "date"
    MONEY = "money"
    BOOK = "book"
    PAPER = "paper"
    OTHER = "other"


@dataclass
class Entity:
    """实体"""
    name: str
    type: EntityType
    normalized_name: Optional[str] = None  # 标准化名称
    description: Optional[str] = None
    mentions: List[Dict] = field(default_factory=list)  # 出现位置列表
    metadata: Dict = field(default_factory=dict)
    confidence: float = 1.0

    @property
    def mention_count(self) -> int:
        return len(self.mentions)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type.value,
            "normalized_name": self.normalized_name,
            "description": self.description,
            "mention_count": self.mention_count,
            "mentions": self.mentions,
            "metadata": self.metadata,
            "confidence": self.confidence,
        }


class EntityRecognizer:
    """实体识别器"""

    SYSTEM_PROMPT = """你是一个专业的命名实体识别专家。从文本中识别和提取各类实体。

实体类型包括：
- person: 人名（包括昵称、代称）
- organization: 组织、公司、机构
- product: 产品名称、品牌
- technology: 技术、编程语言、框架
- location: 地点、国家、城市
- event: 事件名称
- date: 日期、时间
- money: 金额、数字
- book: 书籍、出版物
- paper: 论文、研究

识别原则：
1. 尽可能标准化实体名称
2. 合并同一实体的不同称呼
3. 提供实体的简短描述
4. 记录实体在文本中的位置"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def recognize(
        self,
        transcript_with_timestamps: str,
        entity_types: Optional[List[EntityType]] = None,
    ) -> List[Entity]:
        """
        识别文本中的实体

        Args:
            transcript_with_timestamps: 带时间戳的转录文本
            entity_types: 要识别的实体类型（None 表示全部）

        Returns:
            Entity 列表
        """
        logger.info("开始实体识别...")

        types_str = ""
        if entity_types:
            types_str = f"只识别以下类型的实体：{', '.join(t.value for t in entity_types)}"

        prompt = f"""分析以下播客转录文本，识别其中的命名实体。

{types_str}

文本：
---
{transcript_with_timestamps[:30000]}
---

请按以下 JSON 格式输出：

```json
[
  {{
    "name": "实体名称",
    "type": "person/organization/product/technology/location/event/date/money/book/paper/other",
    "normalized_name": "标准化名称",
    "description": "简短描述（一句话）",
    "mentions": [
      {{"text": "原文片段", "timestamp": 123.5}}
    ],
    "confidence": 0.95
  }}
]
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.2)
            data = self.llm.parse_json_response(response)

            entities = []
            for item in data:
                entity = Entity(
                    name=item.get("name", ""),
                    type=EntityType(item.get("type", "other")),
                    normalized_name=item.get("normalized_name"),
                    description=item.get("description"),
                    mentions=item.get("mentions", []),
                    confidence=float(item.get("confidence", 1.0)),
                )
                entities.append(entity)

            # 按出现次数排序
            entities.sort(key=lambda x: x.mention_count, reverse=True)

            logger.info(f"识别到 {len(entities)} 个实体")
            return entities

        except Exception as e:
            logger.error(f"实体识别失败: {e}")
            return []

    def group_by_type(self, entities: List[Entity]) -> Dict[EntityType, List[Entity]]:
        """按类型分组实体"""
        groups = {}
        for entity in entities:
            if entity.type not in groups:
                groups[entity.type] = []
            groups[entity.type].append(entity)
        return groups

    def find_related_entities(
        self,
        entities: List[Entity],
        entity_name: str,
        window_seconds: float = 60.0,
    ) -> List[Entity]:
        """
        找出与指定实体相关的其他实体（基于时间窗口共现）

        Args:
            entities: 所有实体
            entity_name: 目标实体名称
            window_seconds: 时间窗口（秒）

        Returns:
            相关实体列表
        """
        # 找到目标实体
        target = None
        for e in entities:
            if e.name == entity_name or e.normalized_name == entity_name:
                target = e
                break

        if not target:
            return []

        # 获取目标实体的所有出现时间
        target_times = [m.get("timestamp", 0) for m in target.mentions if m.get("timestamp")]

        # 找出在时间窗口内共现的实体
        related = []
        for entity in entities:
            if entity.name == entity_name:
                continue

            for mention in entity.mentions:
                mention_time = mention.get("timestamp", 0)
                for target_time in target_times:
                    if abs(mention_time - target_time) <= window_seconds:
                        related.append(entity)
                        break

        # 去重
        seen = set()
        unique_related = []
        for e in related:
            if e.name not in seen:
                seen.add(e.name)
                unique_related.append(e)

        return unique_related

    def generate_entity_report(self, entities: List[Entity]) -> str:
        """生成实体报告"""
        lines = ["## 🏷️ 实体识别报告\n"]

        groups = self.group_by_type(entities)

        type_emoji = {
            EntityType.PERSON: "👤",
            EntityType.ORGANIZATION: "🏢",
            EntityType.PRODUCT: "📦",
            EntityType.TECHNOLOGY: "💻",
            EntityType.LOCATION: "📍",
            EntityType.EVENT: "📅",
            EntityType.BOOK: "📚",
            EntityType.PAPER: "📄",
        }

        for entity_type, type_entities in groups.items():
            emoji = type_emoji.get(entity_type, "•")
            lines.append(f"### {emoji} {entity_type.value.title()} ({len(type_entities)})\n")

            for entity in type_entities[:10]:  # 每类最多显示10个
                desc = f" - {entity.description}" if entity.description else ""
                lines.append(f"- **{entity.name}** (x{entity.mention_count}){desc}")

            if len(type_entities) > 10:
                lines.append(f"- ... 还有 {len(type_entities) - 10} 个")

            lines.append("")

        return "\n".join(lines)
