"""
版权风险评估器
综合评估播客的版权风险
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class RiskLevel(Enum):
    """风险级别"""
    SAFE = "safe"  # 安全
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中等风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 严重风险


class RiskCategory(Enum):
    """风险类别"""
    MUSIC = "music"  # 音乐
    TEXT = "text"  # 文本引用
    TRADEMARK = "trademark"  # 商标
    IMAGE = "image"  # 图像（如封面）
    CLIP = "clip"  # 音视频片段
    NAME_LIKENESS = "name_likeness"  # 肖像权


@dataclass
class RiskItem:
    """风险项"""
    category: RiskCategory
    level: RiskLevel
    description: str
    location: str  # 时间戳或位置
    details: Dict[str, Any]
    mitigation: str
    legal_reference: Optional[str] = None


@dataclass
class CopyrightRiskReport:
    """版权风险报告"""
    podcast_id: str
    generated_at: datetime
    overall_risk: RiskLevel
    risk_score: float  # 0-100
    risk_items: List[RiskItem]
    by_category: Dict[RiskCategory, List[RiskItem]]
    summary: str
    action_items: List[Dict[str, Any]]
    legal_disclaimer: str
    monetization_impact: Dict[str, Any]
    platform_compliance: Dict[str, Any]


class CopyrightRiskAssessor:
    """版权风险评估器"""

    # 风险权重
    RISK_WEIGHTS = {
        RiskCategory.MUSIC: 1.5,  # 音乐版权最敏感
        RiskCategory.TEXT: 0.8,
        RiskCategory.TRADEMARK: 1.2,
        RiskCategory.IMAGE: 0.6,
        RiskCategory.CLIP: 1.3,
        RiskCategory.NAME_LIKENESS: 1.0
    }

    # 级别分数
    LEVEL_SCORES = {
        RiskLevel.SAFE: 0,
        RiskLevel.LOW: 20,
        RiskLevel.MEDIUM: 50,
        RiskLevel.HIGH: 80,
        RiskLevel.CRITICAL: 100
    }

    # 平台政策
    PLATFORM_POLICIES = {
        "youtube": {
            "music_tolerance": "low",
            "content_id": True,
            "fair_use_consideration": True
        },
        "spotify": {
            "music_tolerance": "very_low",
            "content_id": True,
            "fair_use_consideration": False
        },
        "apple_podcasts": {
            "music_tolerance": "low",
            "content_id": False,
            "fair_use_consideration": True
        },
        "xiaoyuzhou": {
            "music_tolerance": "medium",
            "content_id": False,
            "fair_use_consideration": True
        }
    }

    def __init__(self):
        self.legal_disclaimer = (
            "本报告仅供参考，不构成法律建议。"
            "如有疑问，请咨询专业版权律师。"
        )

    def assess_risk(
        self,
        music_detection_result: Optional[Any] = None,
        quote_check_result: Optional[Any] = None,
        audio_fingerprint_result: Optional[Dict[str, Any]] = None,
        additional_content: Optional[Dict[str, Any]] = None,
        podcast_id: str = "unknown"
    ) -> CopyrightRiskReport:
        """
        综合评估版权风险

        Args:
            music_detection_result: 音乐检测结果
            quote_check_result: 引用检查结果
            audio_fingerprint_result: 音频指纹结果
            additional_content: 附加内容（封面、标题等）
            podcast_id: 播客ID

        Returns:
            版权风险报告
        """
        risk_items = []

        # 评估音乐风险
        if music_detection_result:
            music_risks = self._assess_music_risk(music_detection_result)
            risk_items.extend(music_risks)

        # 评估引用风险
        if quote_check_result:
            quote_risks = self._assess_quote_risk(quote_check_result)
            risk_items.extend(quote_risks)

        # 评估音频指纹匹配风险
        if audio_fingerprint_result:
            fingerprint_risks = self._assess_fingerprint_risk(audio_fingerprint_result)
            risk_items.extend(fingerprint_risks)

        # 评估附加内容风险
        if additional_content:
            additional_risks = self._assess_additional_content(additional_content)
            risk_items.extend(additional_risks)

        # 按类别分组
        by_category = self._group_by_category(risk_items)

        # 计算整体风险分数
        risk_score = self._calculate_risk_score(risk_items)

        # 确定整体风险级别
        overall_risk = self._determine_overall_risk(risk_score)

        # 生成摘要
        summary = self._generate_summary(risk_items, overall_risk)

        # 生成行动项
        action_items = self._generate_action_items(risk_items)

        # 评估变现影响
        monetization_impact = self._assess_monetization_impact(risk_items)

        # 评估平台合规性
        platform_compliance = self._assess_platform_compliance(risk_items)

        return CopyrightRiskReport(
            podcast_id=podcast_id,
            generated_at=datetime.now(),
            overall_risk=overall_risk,
            risk_score=risk_score,
            risk_items=risk_items,
            by_category=by_category,
            summary=summary,
            action_items=action_items,
            legal_disclaimer=self.legal_disclaimer,
            monetization_impact=monetization_impact,
            platform_compliance=platform_compliance
        )

    def _assess_music_risk(self, music_result: Any) -> List[RiskItem]:
        """评估音乐风险"""
        risks = []

        if hasattr(music_result, 'segments'):
            for segment in music_result.segments:
                # 检查版权状态
                if hasattr(segment, 'license_status'):
                    license_status = segment.license_status.value if hasattr(segment.license_status, 'value') else str(segment.license_status)

                    if license_status == "copyrighted":
                        risk = RiskItem(
                            category=RiskCategory.MUSIC,
                            level=RiskLevel.HIGH,
                            description=f"检测到版权音乐",
                            location=f"{segment.start_time:.0f}-{segment.end_time:.0f}秒",
                            details={
                                "duration": segment.end_time - segment.start_time,
                                "type": segment.music_type.value if hasattr(segment.music_type, 'value') else str(segment.music_type),
                                "identified_track": getattr(segment, 'identified_track', None)
                            },
                            mitigation="移除该音乐片段或获取授权许可",
                            legal_reference="《著作权法》第四十八条"
                        )
                        risks.append(risk)

                    elif license_status == "unknown":
                        risk = RiskItem(
                            category=RiskCategory.MUSIC,
                            level=RiskLevel.MEDIUM,
                            description="检测到未识别的音乐",
                            location=f"{segment.start_time:.0f}-{segment.end_time:.0f}秒",
                            details={
                                "duration": segment.end_time - segment.start_time,
                                "type": segment.music_type.value if hasattr(segment.music_type, 'value') else str(segment.music_type)
                            },
                            mitigation="确认音乐版权状态，或替换为免版税音乐"
                        )
                        risks.append(risk)

        # 检查整体音乐使用时长
        if hasattr(music_result, 'music_percentage') and music_result.music_percentage > 30:
            risks.append(RiskItem(
                category=RiskCategory.MUSIC,
                level=RiskLevel.MEDIUM,
                description=f"音乐内容占比过高 ({music_result.music_percentage:.1f}%)",
                location="整体",
                details={"percentage": music_result.music_percentage},
                mitigation="减少音乐使用，确保播客以语音内容为主"
            ))

        return risks

    def _assess_quote_risk(self, quote_result: Any) -> List[RiskItem]:
        """评估引用风险"""
        risks = []

        if hasattr(quote_result, 'quotes'):
            for quote in quote_result.quotes:
                if quote.risk_level == "high":
                    risk = RiskItem(
                        category=RiskCategory.TEXT,
                        level=RiskLevel.HIGH,
                        description=f"高风险引用：{quote.text[:50]}...",
                        location=f"位置 {quote.start_position}",
                        details={
                            "quote_type": quote.quote_type.value if hasattr(quote.quote_type, 'value') else str(quote.quote_type),
                            "word_count": quote.word_count,
                            "is_attributed": quote.is_attributed
                        },
                        mitigation="获取授权或移除该引用"
                    )
                    risks.append(risk)

                elif quote.risk_level == "medium":
                    risks.append(RiskItem(
                        category=RiskCategory.TEXT,
                        level=RiskLevel.MEDIUM,
                        description=f"中等风险引用：{quote.text[:30]}...",
                        location=f"位置 {quote.start_position}",
                        details={
                            "quote_type": quote.quote_type.value if hasattr(quote.quote_type, 'value') else str(quote.quote_type),
                            "word_count": quote.word_count
                        },
                        mitigation="添加来源归属或缩短引用长度"
                    ))

        return risks

    def _assess_fingerprint_risk(self, fingerprint_result: Dict[str, Any]) -> List[RiskItem]:
        """评估音频指纹风险"""
        risks = []

        if fingerprint_result.get("requires_attention"):
            matched_percentage = fingerprint_result.get("match_percentage", 0)

            risks.append(RiskItem(
                category=RiskCategory.CLIP,
                level=RiskLevel.HIGH if matched_percentage > 20 else RiskLevel.MEDIUM,
                description=f"音频指纹匹配到版权内容 ({matched_percentage:.1f}%)",
                location="多个片段",
                details={
                    "matched_duration": fingerprint_result.get("matched_duration", 0),
                    "match_percentage": matched_percentage
                },
                mitigation="检查并移除匹配的音频片段"
            ))

        return risks

    def _assess_additional_content(self, content: Dict[str, Any]) -> List[RiskItem]:
        """评估附加内容风险"""
        risks = []

        # 检查封面
        if "cover_image" in content:
            cover = content["cover_image"]
            if cover.get("source") == "unknown":
                risks.append(RiskItem(
                    category=RiskCategory.IMAGE,
                    level=RiskLevel.MEDIUM,
                    description="封面图片来源不明",
                    location="封面",
                    details={"filename": cover.get("filename")},
                    mitigation="使用原创图片或确认图片版权"
                ))

        # 检查标题中的商标
        if "title" in content:
            title = content["title"]
            # 简单检查常见商标（实际需要完整的商标数据库）
            trademarks = ["Apple", "Google", "Microsoft", "Tesla"]
            for trademark in trademarks:
                if trademark in title:
                    risks.append(RiskItem(
                        category=RiskCategory.TRADEMARK,
                        level=RiskLevel.LOW,
                        description=f"标题包含商标「{trademark}」",
                        location="标题",
                        details={"trademark": trademark},
                        mitigation="确保使用合规，避免暗示品牌背书"
                    ))

        return risks

    def _group_by_category(
        self,
        risk_items: List[RiskItem]
    ) -> Dict[RiskCategory, List[RiskItem]]:
        """按类别分组"""
        grouped = {}
        for item in risk_items:
            if item.category not in grouped:
                grouped[item.category] = []
            grouped[item.category].append(item)
        return grouped

    def _calculate_risk_score(self, risk_items: List[RiskItem]) -> float:
        """计算风险分数"""
        if not risk_items:
            return 0

        total_score = 0
        total_weight = 0

        for item in risk_items:
            weight = self.RISK_WEIGHTS.get(item.category, 1.0)
            score = self.LEVEL_SCORES.get(item.level, 50)

            total_score += score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0

    def _determine_overall_risk(self, score: float) -> RiskLevel:
        """确定整体风险级别"""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        elif score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.SAFE

    def _generate_summary(
        self,
        risk_items: List[RiskItem],
        overall_risk: RiskLevel
    ) -> str:
        """生成摘要"""
        if overall_risk == RiskLevel.SAFE:
            return "✅ 未检测到明显的版权风险，可以安全发布。"

        elif overall_risk == RiskLevel.LOW:
            return f"🟢 发现{len(risk_items)}个低风险项，建议处理后发布。"

        elif overall_risk == RiskLevel.MEDIUM:
            return f"🟡 发现{len(risk_items)}个风险项，需要在发布前处理。"

        elif overall_risk == RiskLevel.HIGH:
            return f"🟠 发现{len(risk_items)}个高风险项，强烈建议处理后再发布。"

        else:
            return f"🔴 发现{len(risk_items)}个严重风险项，请立即处理！"

    def _generate_action_items(self, risk_items: List[RiskItem]) -> List[Dict[str, Any]]:
        """生成行动项"""
        action_items = []

        # 按优先级排序
        sorted_items = sorted(
            risk_items,
            key=lambda x: self.LEVEL_SCORES.get(x.level, 0),
            reverse=True
        )

        for i, item in enumerate(sorted_items[:5]):  # 最多5个行动项
            action_items.append({
                "priority": i + 1,
                "category": item.category.value,
                "risk_level": item.level.value,
                "action": item.mitigation,
                "location": item.location,
                "deadline": "发布前" if item.level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else "建议处理"
            })

        return action_items

    def _assess_monetization_impact(
        self,
        risk_items: List[RiskItem]
    ) -> Dict[str, Any]:
        """评估变现影响"""
        music_risks = [r for r in risk_items if r.category == RiskCategory.MUSIC]
        high_risks = [r for r in risk_items if r.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]

        if high_risks:
            return {
                "can_monetize": False,
                "reason": "存在高风险版权内容，可能导致下架或收益分成",
                "potential_issues": [
                    "广告收益可能被版权方索取",
                    "可能收到版权声明",
                    "严重情况可能面临诉讼"
                ],
                "recommendation": "解决所有高风险问题后再开启变现"
            }

        elif music_risks:
            return {
                "can_monetize": "limited",
                "reason": "包含音乐内容，需要确认版权状态",
                "potential_issues": [
                    "部分平台可能自动检测到音乐",
                    "可能需要与版权方分享收益"
                ],
                "recommendation": "使用免版税音乐以避免版权纠纷"
            }

        return {
            "can_monetize": True,
            "reason": "未检测到明显的版权风险",
            "potential_issues": [],
            "recommendation": "可以正常开启变现功能"
        }

    def _assess_platform_compliance(
        self,
        risk_items: List[RiskItem]
    ) -> Dict[str, Any]:
        """评估平台合规性"""
        compliance = {}

        music_risks = [r for r in risk_items if r.category == RiskCategory.MUSIC]
        has_copyrighted_music = any(r.level == RiskLevel.HIGH for r in music_risks)

        for platform, policy in self.PLATFORM_POLICIES.items():
            if has_copyrighted_music:
                if policy["music_tolerance"] == "very_low":
                    compliance[platform] = {
                        "status": "blocked",
                        "reason": "平台对版权音乐零容忍",
                        "action": "移除所有版权音乐"
                    }
                elif policy["music_tolerance"] == "low":
                    compliance[platform] = {
                        "status": "risk",
                        "reason": "可能触发Content ID系统",
                        "action": "可能导致视频静音或收益分成"
                    }
                else:
                    compliance[platform] = {
                        "status": "warning",
                        "reason": "建议谨慎使用版权音乐",
                        "action": "可能收到版权警告"
                    }
            else:
                compliance[platform] = {
                    "status": "ok",
                    "reason": "符合平台政策",
                    "action": "无需特别处理"
                }

        return compliance

    def export_report(
        self,
        report: CopyrightRiskReport,
        format: str = "json"
    ) -> str:
        """导出报告"""
        import json

        if format == "json":
            return json.dumps({
                "podcast_id": report.podcast_id,
                "generated_at": report.generated_at.isoformat(),
                "overall_risk": report.overall_risk.value,
                "risk_score": report.risk_score,
                "summary": report.summary,
                "risk_items": [
                    {
                        "category": item.category.value,
                        "level": item.level.value,
                        "description": item.description,
                        "location": item.location,
                        "mitigation": item.mitigation
                    }
                    for item in report.risk_items
                ],
                "action_items": report.action_items,
                "monetization_impact": report.monetization_impact,
                "platform_compliance": report.platform_compliance,
                "legal_disclaimer": report.legal_disclaimer
            }, ensure_ascii=False, indent=2)

        return ""
