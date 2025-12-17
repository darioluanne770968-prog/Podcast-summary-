"""
行动建议提取模块

从播客内容中提取可执行的行动建议
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from ..analysis import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


class ActionPriority(str, Enum):
    """行动优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionCategory(str, Enum):
    """行动类别"""
    CAREER = "career"  # 职业发展
    LEARNING = "learning"  # 学习成长
    HEALTH = "health"  # 健康生活
    FINANCE = "finance"  # 理财投资
    RELATIONSHIP = "relationship"  # 人际关系
    PRODUCTIVITY = "productivity"  # 效率提升
    MINDSET = "mindset"  # 思维方式
    TECH = "tech"  # 技术工具
    OTHER = "other"


@dataclass
class ActionItem:
    """行动项"""
    action: str  # 行动内容
    category: ActionCategory
    priority: ActionPriority
    context: str  # 为什么要这样做
    speaker: Optional[str] = None  # 谁提出的
    timestamp: Optional[float] = None
    prerequisites: List[str] = field(default_factory=list)  # 前提条件
    resources: List[str] = field(default_factory=list)  # 相关资源
    estimated_effort: Optional[str] = None  # 预估投入

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "category": self.category.value,
            "priority": self.priority.value,
            "context": self.context,
            "speaker": self.speaker,
            "timestamp": self.timestamp,
            "prerequisites": self.prerequisites,
            "resources": self.resources,
            "estimated_effort": self.estimated_effort,
        }


class ActionExtractor:
    """行动建议提取器"""

    SYSTEM_PROMPT = """你是一个行动规划专家，擅长从内容中提取可执行的行动建议。

提取原则：
1. 行动应该具体、可执行
2. 提供行动的背景和原因
3. 识别行动的优先级
4. 列出所需的前提条件和资源
5. 避免过于笼统的建议

行动类别：
- career: 职业发展相关
- learning: 学习成长相关
- health: 健康生活相关
- finance: 理财投资相关
- relationship: 人际关系相关
- productivity: 效率提升相关
- mindset: 思维方式相关
- tech: 技术工具相关
- other: 其他"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def extract(
        self,
        transcript: str,
        categories: Optional[List[ActionCategory]] = None,
        max_actions: int = 20,
    ) -> List[ActionItem]:
        """
        从转录文本中提取行动建议

        Args:
            transcript: 转录文本
            categories: 要提取的行动类别（None 表示全部）
            max_actions: 最大行动数量

        Returns:
            ActionItem 列表
        """
        logger.info("提取行动建议...")

        cat_str = ""
        if categories:
            cat_str = f"只提取以下类别的行动：{', '.join(c.value for c in categories)}"

        prompt = f"""分析以下播客转录文本，提取所有可执行的行动建议。

{cat_str}

文本：
---
{transcript[:25000]}
---

请提取具体、可执行的行动建议（最多 {max_actions} 条），按以下 JSON 格式输出：

```json
[
  {{
    "action": "具体的行动内容",
    "category": "career/learning/health/finance/relationship/productivity/mindset/tech/other",
    "priority": "high/medium/low",
    "context": "为什么要这样做",
    "speaker": "谁提出的建议",
    "prerequisites": ["前提条件1", "前提条件2"],
    "resources": ["推荐资源1", "推荐资源2"],
    "estimated_effort": "预估所需时间/精力"
  }}
]
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.3)
            data = self.llm.parse_json_response(response)

            actions = []
            for item in data:
                action = ActionItem(
                    action=item.get("action", ""),
                    category=ActionCategory(item.get("category", "other")),
                    priority=ActionPriority(item.get("priority", "medium")),
                    context=item.get("context", ""),
                    speaker=item.get("speaker"),
                    prerequisites=item.get("prerequisites", []),
                    resources=item.get("resources", []),
                    estimated_effort=item.get("estimated_effort"),
                )
                actions.append(action)

            # 按优先级排序
            priority_order = {"high": 0, "medium": 1, "low": 2}
            actions.sort(key=lambda a: priority_order.get(a.priority.value, 1))

            logger.info(f"提取到 {len(actions)} 条行动建议")
            return actions[:max_actions]

        except Exception as e:
            logger.error(f"提取行动建议失败: {e}")
            return []

    def group_by_category(self, actions: List[ActionItem]) -> dict:
        """按类别分组行动"""
        groups = {}
        for action in actions:
            if action.category not in groups:
                groups[action.category] = []
            groups[action.category].append(action)
        return groups

    def generate_action_plan(self, actions: List[ActionItem]) -> str:
        """生成行动计划"""
        lines = ["## ✅ 行动计划\n"]

        # 按优先级分组
        high_priority = [a for a in actions if a.priority == ActionPriority.HIGH]
        medium_priority = [a for a in actions if a.priority == ActionPriority.MEDIUM]
        low_priority = [a for a in actions if a.priority == ActionPriority.LOW]

        if high_priority:
            lines.append("### 🔴 高优先级\n")
            for action in high_priority:
                lines.append(f"- [ ] **{action.action}**")
                lines.append(f"  - 原因: {action.context}")
                if action.estimated_effort:
                    lines.append(f"  - 预估投入: {action.estimated_effort}")
                if action.resources:
                    lines.append(f"  - 资源: {', '.join(action.resources[:3])}")

        if medium_priority:
            lines.append("\n### 🟡 中优先级\n")
            for action in medium_priority:
                lines.append(f"- [ ] **{action.action}**")
                lines.append(f"  - 原因: {action.context}")

        if low_priority:
            lines.append("\n### 🟢 低优先级\n")
            for action in low_priority:
                lines.append(f"- [ ] {action.action}")

        # 按类别统计
        lines.append("\n### 📊 类别统计\n")
        groups = self.group_by_category(actions)
        category_emoji = {
            ActionCategory.CAREER: "💼",
            ActionCategory.LEARNING: "📚",
            ActionCategory.HEALTH: "🏃",
            ActionCategory.FINANCE: "💰",
            ActionCategory.RELATIONSHIP: "👥",
            ActionCategory.PRODUCTIVITY: "⚡",
            ActionCategory.MINDSET: "🧠",
            ActionCategory.TECH: "💻",
        }

        for category, cat_actions in groups.items():
            emoji = category_emoji.get(category, "•")
            lines.append(f"- {emoji} {category.value}: {len(cat_actions)} 条")

        return "\n".join(lines)

    def generate_checklist(self, actions: List[ActionItem]) -> str:
        """生成可打印的检查清单"""
        lines = ["# 📋 行动检查清单\n"]
        lines.append(f"*生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}*\n")

        for i, action in enumerate(actions, 1):
            priority_marker = {"high": "❗", "medium": "➖", "low": "🔸"}.get(action.priority.value, "")
            lines.append(f"- [ ] {priority_marker} {action.action}")

        return "\n".join(lines)
