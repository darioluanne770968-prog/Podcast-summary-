"""
敏感内容检测器
检测文本中的敏感词和内容
"""
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class SensitiveCategory(Enum):
    POLITICAL = "political"
    VIOLENCE = "violence"
    ADULT = "adult"
    DISCRIMINATION = "discrimination"
    ILLEGAL = "illegal"
    PRIVACY = "privacy"
    HEALTH_MISINFORMATION = "health_misinformation"


@dataclass
class SensitiveMatch:
    text: str
    category: SensitiveCategory
    position: int
    severity: str  # low, medium, high
    context: str
    suggestion: str


@dataclass
class SensitiveCheckResult:
    is_clean: bool
    matches: List[SensitiveMatch]
    risk_level: str
    categories_found: List[SensitiveCategory]
    recommendations: List[str]


class SensitiveDetector:
    """敏感内容检测器"""

    # 敏感词库（示例，实际需要更完整的词库）
    SENSITIVE_WORDS: Dict[SensitiveCategory, Set[str]] = {
        SensitiveCategory.VIOLENCE: {"暴力", "杀", "血腥", "攻击"},
        SensitiveCategory.DISCRIMINATION: {"歧视", "种族"},
        SensitiveCategory.HEALTH_MISINFORMATION: {"包治百病", "神药", "偏方"},
    }

    def __init__(self, custom_words: Optional[Dict[str, Set[str]]] = None):
        self.word_dict = dict(self.SENSITIVE_WORDS)
        if custom_words:
            for cat, words in custom_words.items():
                if cat in self.word_dict:
                    self.word_dict[cat].update(words)

    def check(self, text: str) -> SensitiveCheckResult:
        """检查敏感内容"""
        matches = []
        categories_found = set()

        for category, words in self.word_dict.items():
            for word in words:
                pos = text.find(word)
                while pos != -1:
                    context = text[max(0, pos - 20):pos + len(word) + 20]
                    matches.append(SensitiveMatch(
                        text=word,
                        category=category,
                        position=pos,
                        severity=self._get_severity(category),
                        context=context,
                        suggestion=f"建议修改或删除「{word}」"
                    ))
                    categories_found.add(category)
                    pos = text.find(word, pos + 1)

        risk_level = self._calculate_risk(matches)
        recommendations = self._generate_recommendations(matches, categories_found)

        return SensitiveCheckResult(
            is_clean=len(matches) == 0,
            matches=matches,
            risk_level=risk_level,
            categories_found=list(categories_found),
            recommendations=recommendations
        )

    def _get_severity(self, category: SensitiveCategory) -> str:
        high_severity = {SensitiveCategory.ILLEGAL, SensitiveCategory.VIOLENCE}
        if category in high_severity:
            return "high"
        return "medium"

    def _calculate_risk(self, matches: List[SensitiveMatch]) -> str:
        if not matches:
            return "safe"
        high_count = sum(1 for m in matches if m.severity == "high")
        if high_count > 0:
            return "high"
        if len(matches) > 5:
            return "medium"
        return "low"

    def _generate_recommendations(
        self,
        matches: List[SensitiveMatch],
        categories: Set[SensitiveCategory]
    ) -> List[str]:
        recommendations = []
        if not matches:
            recommendations.append("✅ 未检测到敏感内容")
        else:
            recommendations.append(f"⚠️ 发现{len(matches)}处敏感内容")
            for category in categories:
                recommendations.append(f"• 涉及{category.value}相关内容，请审查")
        return recommendations
