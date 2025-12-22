"""合规报告生成"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class ComplianceReport:
    podcast_id: str
    generated_at: datetime
    overall_status: str  # compliant, warnings, violations
    sensitive_check: Dict[str, Any]
    ad_check: Dict[str, Any]
    platform_checks: Dict[str, Dict[str, Any]]
    action_items: List[Dict[str, Any]]
    summary: str


class ComplianceReporter:
    """合规报告生成器"""

    def generate_report(
        self,
        podcast_id: str,
        sensitive_result: Optional[Dict] = None,
        ad_result: Optional[Dict] = None,
        platform_results: Optional[Dict] = None
    ) -> ComplianceReport:
        """生成合规报告"""
        action_items = []
        has_violations = False
        has_warnings = False

        # 处理敏感内容检查
        if sensitive_result:
            if not sensitive_result.get("is_clean", True):
                has_violations = True
                for match in sensitive_result.get("matches", []):
                    action_items.append({
                        "type": "sensitive",
                        "priority": "high" if match.get("severity") == "high" else "medium",
                        "action": match.get("suggestion", "审查敏感内容")
                    })

        # 处理广告合规检查
        if ad_result:
            if not ad_result.get("is_compliant", True):
                has_warnings = True
                for violation in ad_result.get("violations", []):
                    action_items.append({
                        "type": "ad_compliance",
                        "priority": "medium",
                        "action": violation.get("fix_suggestion", "审查广告披露")
                    })

        # 处理平台合规检查
        if platform_results:
            for platform, result in platform_results.items():
                if not result.get("is_compliant", True):
                    has_warnings = True
                    for violation in result.get("violations", []):
                        action_items.append({
                            "type": f"platform_{platform}",
                            "priority": "medium",
                            "action": violation.get("fix_suggestion", f"调整以符合{platform}要求")
                        })

        # 确定整体状态
        if has_violations:
            overall_status = "violations"
        elif has_warnings:
            overall_status = "warnings"
        else:
            overall_status = "compliant"

        summary = self._generate_summary(overall_status, action_items)

        return ComplianceReport(
            podcast_id=podcast_id,
            generated_at=datetime.now(),
            overall_status=overall_status,
            sensitive_check=sensitive_result or {},
            ad_check=ad_result or {},
            platform_checks=platform_results or {},
            action_items=action_items,
            summary=summary
        )

    def _generate_summary(self, status: str, actions: List[Dict]) -> str:
        if status == "compliant":
            return "✅ 内容审查通过，未发现合规问题"
        elif status == "warnings":
            return f"⚠️ 发现{len(actions)}个需要注意的问题"
        else:
            return f"🔴 发现{len(actions)}个合规问题，请在发布前处理"

    def export_json(self, report: ComplianceReport) -> str:
        """导出JSON报告"""
        return json.dumps({
            "podcast_id": report.podcast_id,
            "generated_at": report.generated_at.isoformat(),
            "overall_status": report.overall_status,
            "action_items": report.action_items,
            "summary": report.summary
        }, ensure_ascii=False, indent=2)
