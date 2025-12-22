"""平台政策检查"""
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class PolicyViolation:
    platform: str
    policy: str
    description: str
    severity: str
    fix_suggestion: str


@dataclass
class PlatformComplianceResult:
    platform: str
    is_compliant: bool
    violations: List[PolicyViolation]
    warnings: List[str]


class PlatformPolicyChecker:
    """平台政策检查器"""

    PLATFORM_RULES = {
        "youtube": {
            "max_title_length": 100,
            "forbidden_content": ["spam", "misleading"],
            "requires_original": True
        },
        "spotify": {
            "max_title_length": 200,
            "explicit_label_required": True,
            "music_license_required": True
        },
        "apple_podcasts": {
            "max_description_length": 4000,
            "category_required": True,
            "artwork_required": True
        },
        "xiaoyuzhou": {
            "max_title_length": 50,
            "sensitive_check_required": True
        }
    }

    def check_platform(
        self,
        platform: str,
        content: Dict[str, Any]
    ) -> PlatformComplianceResult:
        """检查特定平台合规"""
        rules = self.PLATFORM_RULES.get(platform, {})
        violations = []
        warnings = []

        # 检查标题长度
        if "title" in content:
            max_len = rules.get("max_title_length", 100)
            if len(content["title"]) > max_len:
                violations.append(PolicyViolation(
                    platform=platform,
                    policy="title_length",
                    description=f"标题超过{max_len}字符限制",
                    severity="medium",
                    fix_suggestion=f"将标题缩短至{max_len}字符以内"
                ))

        # 检查描述长度
        if "description" in content:
            max_desc = rules.get("max_description_length", 5000)
            if len(content["description"]) > max_desc:
                warnings.append(f"描述可能超过{platform}的限制")

        return PlatformComplianceResult(
            platform=platform,
            is_compliant=len(violations) == 0,
            violations=violations,
            warnings=warnings
        )

    def check_all_platforms(
        self,
        content: Dict[str, Any]
    ) -> Dict[str, PlatformComplianceResult]:
        """检查所有平台"""
        results = {}
        for platform in self.PLATFORM_RULES.keys():
            results[platform] = self.check_platform(platform, content)
        return results
