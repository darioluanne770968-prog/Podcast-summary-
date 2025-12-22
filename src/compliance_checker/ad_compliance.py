"""广告合规检查"""
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class AdViolationType(Enum):
    UNDISCLOSED = "undisclosed"  # 未披露广告
    MISLEADING = "misleading"  # 虚假宣传
    PROHIBITED_PRODUCT = "prohibited_product"  # 禁止产品
    MISSING_DISCLAIMER = "missing_disclaimer"  # 缺少免责声明


@dataclass
class AdViolation:
    violation_type: AdViolationType
    description: str
    position: int
    severity: str
    fix_suggestion: str


@dataclass
class AdComplianceResult:
    is_compliant: bool
    violations: List[AdViolation]
    ad_segments: List[Dict[str, Any]]
    recommendations: List[str]


class AdComplianceChecker:
    """广告合规检查器"""

    AD_INDICATORS = ["推荐", "赞助", "广告", "合作", "优惠码", "链接"]
    DISCLOSURE_PHRASES = ["广告", "推广", "赞助", "合作"]

    def check(self, transcript: str, metadata: Dict[str, Any] = None) -> AdComplianceResult:
        """检查广告合规"""
        violations = []
        ad_segments = self._detect_ad_segments(transcript)

        for segment in ad_segments:
            # 检查是否有披露
            if not self._has_disclosure(segment["text"]):
                violations.append(AdViolation(
                    violation_type=AdViolationType.UNDISCLOSED,
                    description="广告内容未明确披露",
                    position=segment["position"],
                    severity="medium",
                    fix_suggestion="在广告开始前添加「以下内容为广告」等披露语"
                ))

        recommendations = self._generate_recommendations(violations, ad_segments)

        return AdComplianceResult(
            is_compliant=len(violations) == 0,
            violations=violations,
            ad_segments=ad_segments,
            recommendations=recommendations
        )

    def _detect_ad_segments(self, text: str) -> List[Dict[str, Any]]:
        """检测广告片段"""
        segments = []
        for indicator in self.AD_INDICATORS:
            pos = text.find(indicator)
            if pos != -1:
                segments.append({
                    "indicator": indicator,
                    "position": pos,
                    "text": text[max(0, pos - 50):pos + 100]
                })
        return segments

    def _has_disclosure(self, text: str) -> bool:
        """检查是否有披露"""
        return any(phrase in text for phrase in self.DISCLOSURE_PHRASES)

    def _generate_recommendations(
        self,
        violations: List[AdViolation],
        ad_segments: List[Dict[str, Any]]
    ) -> List[str]:
        recommendations = []
        if not violations:
            recommendations.append("✅ 广告内容符合披露要求")
        else:
            recommendations.append("⚠️ 请确保所有广告内容都有明确披露")
            recommendations.append("💡 建议在广告前后使用清晰的分隔语")
        return recommendations
