"""
SEO评分器
综合评估播客内容的SEO效果
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ScoreLevel(Enum):
    """评分等级"""
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 70-89
    FAIR = "fair"  # 50-69
    POOR = "poor"  # 30-49
    CRITICAL = "critical"  # 0-29


@dataclass
class SEOCheckItem:
    """SEO检查项"""
    name: str
    category: str
    passed: bool
    score: float
    max_score: float
    message: str
    recommendation: Optional[str] = None
    priority: str = "medium"  # high, medium, low


@dataclass
class SEOScoreReport:
    """SEO评分报告"""
    overall_score: float
    level: ScoreLevel
    category_scores: Dict[str, float]
    check_items: List[SEOCheckItem]
    top_issues: List[SEOCheckItem]
    improvements: List[Dict[str, Any]]
    comparison_benchmark: Dict[str, Any]
    action_plan: List[Dict[str, Any]]
    generated_at: datetime


class SEOScorer:
    """SEO评分器"""

    # 各类别权重
    CATEGORY_WEIGHTS = {
        "title": 0.25,
        "description": 0.20,
        "keywords": 0.20,
        "content": 0.15,
        "technical": 0.10,
        "engagement": 0.10
    }

    # 检查项配置
    CHECK_ITEMS = {
        "title": [
            ("title_length", "标题长度", 50, 60, 10),
            ("title_keywords", "标题包含关键词", None, None, 15),
            ("title_power_words", "标题包含力量词", None, None, 5),
            ("title_numbers", "标题包含数字", None, None, 5),
            ("title_unique", "标题独特性", None, None, 5)
        ],
        "description": [
            ("desc_length", "描述长度", 1000, 2000, 10),
            ("desc_keywords", "描述包含关键词", None, None, 10),
            ("desc_structure", "描述结构", None, None, 10),
            ("desc_timestamps", "包含时间戳", None, None, 5),
            ("desc_cta", "包含行动号召", None, None, 5)
        ],
        "keywords": [
            ("keyword_count", "关键词数量", 5, 15, 10),
            ("keyword_relevance", "关键词相关性", None, None, 15),
            ("keyword_density", "关键词密度", 0.01, 0.03, 10),
            ("long_tail", "长尾关键词", None, None, 5)
        ],
        "content": [
            ("transcript_length", "内容长度", None, None, 10),
            ("topic_coverage", "主题覆盖", None, None, 10),
            ("readability", "可读性", None, None, 10)
        ],
        "technical": [
            ("audio_quality", "音频质量", None, None, 10),
            ("file_format", "文件格式", None, None, 5),
            ("metadata", "元数据完整性", None, None, 5)
        ],
        "engagement": [
            ("hook_strength", "开头吸引力", None, None, 10),
            ("shareability", "分享潜力", None, None, 10)
        ]
    }

    def __init__(self):
        self.benchmark_data = self._load_benchmark_data()

    def _load_benchmark_data(self) -> Dict[str, Any]:
        """加载基准数据"""
        return {
            "avg_title_length": 45,
            "avg_description_length": 1200,
            "avg_keyword_count": 8,
            "avg_score": 65,
            "top_10_percent_score": 85,
            "industry_averages": {
                "technology": 70,
                "business": 68,
                "education": 72,
                "entertainment": 60
            }
        }

    def score_podcast(
        self,
        title: str,
        description: str,
        keywords: List[str],
        transcript: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SEOScoreReport:
        """
        评估播客SEO效果

        Args:
            title: 标题
            description: 描述
            keywords: 关键词列表
            transcript: 转录文本
            metadata: 元数据

        Returns:
            SEO评分报告
        """
        check_items = []
        category_scores = {}

        # 评估各类别
        for category, items in self.CHECK_ITEMS.items():
            category_checks = []

            for item_config in items:
                item_id, item_name = item_config[0], item_config[1]
                max_score = item_config[4]

                check_result = self._evaluate_item(
                    item_id=item_id,
                    item_name=item_name,
                    category=category,
                    title=title,
                    description=description,
                    keywords=keywords,
                    transcript=transcript,
                    metadata=metadata,
                    max_score=max_score,
                    config=item_config
                )

                category_checks.append(check_result)
                check_items.append(check_result)

            # 计算类别分数
            category_total = sum(c.score for c in category_checks)
            category_max = sum(c.max_score for c in category_checks)
            category_scores[category] = (category_total / category_max * 100) if category_max > 0 else 0

        # 计算总分
        overall_score = sum(
            category_scores[cat] * self.CATEGORY_WEIGHTS[cat]
            for cat in category_scores
        )

        # 确定等级
        level = self._determine_level(overall_score)

        # 找出主要问题
        top_issues = self._identify_top_issues(check_items)

        # 生成改进建议
        improvements = self._generate_improvements(check_items, category_scores)

        # 与基准比较
        comparison = self._compare_with_benchmark(overall_score, category_scores)

        # 生成行动计划
        action_plan = self._generate_action_plan(top_issues, improvements)

        return SEOScoreReport(
            overall_score=round(overall_score, 1),
            level=level,
            category_scores={k: round(v, 1) for k, v in category_scores.items()},
            check_items=check_items,
            top_issues=top_issues,
            improvements=improvements,
            comparison_benchmark=comparison,
            action_plan=action_plan,
            generated_at=datetime.now()
        )

    def _evaluate_item(
        self,
        item_id: str,
        item_name: str,
        category: str,
        title: str,
        description: str,
        keywords: List[str],
        transcript: str,
        metadata: Optional[Dict[str, Any]],
        max_score: float,
        config: tuple
    ) -> SEOCheckItem:
        """评估单个检查项"""
        # 根据不同的检查项执行相应的检查
        evaluators = {
            "title_length": lambda: self._check_title_length(title, config),
            "title_keywords": lambda: self._check_title_keywords(title, keywords),
            "title_power_words": lambda: self._check_title_power_words(title),
            "title_numbers": lambda: self._check_title_numbers(title),
            "title_unique": lambda: self._check_title_unique(title),
            "desc_length": lambda: self._check_desc_length(description, config),
            "desc_keywords": lambda: self._check_desc_keywords(description, keywords),
            "desc_structure": lambda: self._check_desc_structure(description),
            "desc_timestamps": lambda: self._check_desc_timestamps(description),
            "desc_cta": lambda: self._check_desc_cta(description),
            "keyword_count": lambda: self._check_keyword_count(keywords, config),
            "keyword_relevance": lambda: self._check_keyword_relevance(keywords, transcript),
            "keyword_density": lambda: self._check_keyword_density(keywords, description, config),
            "long_tail": lambda: self._check_long_tail(keywords),
            "transcript_length": lambda: self._check_transcript_length(transcript),
            "topic_coverage": lambda: self._check_topic_coverage(transcript, keywords),
            "readability": lambda: self._check_readability(transcript),
            "audio_quality": lambda: self._check_audio_quality(metadata),
            "file_format": lambda: self._check_file_format(metadata),
            "metadata": lambda: self._check_metadata(metadata),
            "hook_strength": lambda: self._check_hook_strength(transcript),
            "shareability": lambda: self._check_shareability(title, description)
        }

        evaluator = evaluators.get(item_id)
        if evaluator:
            passed, score_ratio, message, recommendation = evaluator()
        else:
            passed, score_ratio, message, recommendation = True, 0.5, "无法评估", None

        return SEOCheckItem(
            name=item_name,
            category=category,
            passed=passed,
            score=max_score * score_ratio,
            max_score=max_score,
            message=message,
            recommendation=recommendation,
            priority="high" if not passed and max_score >= 10 else "medium" if not passed else "low"
        )

    # 各检查项的具体实现
    def _check_title_length(self, title: str, config: tuple) -> tuple:
        min_len, max_len = config[2], config[3]
        length = len(title)

        if min_len <= length <= max_len:
            return True, 1.0, f"标题长度({length}字)在理想范围内", None
        elif length < min_len:
            return False, 0.5, f"标题过短({length}字)，建议{min_len}-{max_len}字", "添加更多描述性词汇"
        else:
            return False, 0.7, f"标题过长({length}字)，建议{min_len}-{max_len}字", "精简标题，保留核心信息"

    def _check_title_keywords(self, title: str, keywords: List[str]) -> tuple:
        found = [kw for kw in keywords if kw.lower() in title.lower()]

        if len(found) >= 2:
            return True, 1.0, f"标题包含{len(found)}个关键词", None
        elif len(found) == 1:
            return True, 0.7, f"标题包含1个关键词", "考虑添加更多相关关键词"
        else:
            return False, 0.0, "标题未包含关键词", "在标题开头添加主要关键词"

    def _check_title_power_words(self, title: str) -> tuple:
        power_words = ["独家", "完整", "深度", "必看", "揭秘", "震撼", "精华"]
        found = [pw for pw in power_words if pw in title]

        if found:
            return True, 1.0, f"标题包含力量词汇：{', '.join(found)}", None
        else:
            return False, 0.0, "标题缺少力量词汇", "添加如「独家」「深度」等吸引眼球的词汇"

    def _check_title_numbers(self, title: str) -> tuple:
        import re
        numbers = re.findall(r'\d+', title)

        if numbers:
            return True, 1.0, f"标题包含数字", None
        else:
            return False, 0.0, "标题不包含数字", "考虑使用「5个技巧」「10分钟」等数字形式"

    def _check_title_unique(self, title: str) -> tuple:
        # 简单检查是否包含独特元素
        unique_indicators = ["首次", "独家", "仅此", "原创", "深度"]

        if any(ind in title for ind in unique_indicators):
            return True, 1.0, "标题体现独特性", None
        else:
            return True, 0.6, "标题可以更独特", "添加独特的角度或视点"

    def _check_desc_length(self, description: str, config: tuple) -> tuple:
        min_len, max_len = config[2], config[3]
        length = len(description)

        if min_len <= length <= max_len:
            return True, 1.0, f"描述长度({length}字)适中", None
        elif length < min_len:
            return False, 0.4, f"描述过短({length}字)", "扩展描述内容，添加更多细节"
        else:
            return True, 0.8, f"描述较长({length}字)", "可考虑精简"

    def _check_desc_keywords(self, description: str, keywords: List[str]) -> tuple:
        found = [kw for kw in keywords if kw.lower() in description.lower()]
        ratio = len(found) / len(keywords) if keywords else 0

        if ratio >= 0.8:
            return True, 1.0, f"描述包含{len(found)}/{len(keywords)}个关键词", None
        elif ratio >= 0.5:
            return True, 0.7, f"描述包含{len(found)}/{len(keywords)}个关键词", "添加更多关键词"
        else:
            return False, 0.3, f"描述仅包含{len(found)}个关键词", "确保主要关键词出现在描述中"

    def _check_desc_structure(self, description: str) -> tuple:
        structure_elements = {
            "分段": "\n\n" in description,
            "列表": "•" in description or "-" in description,
            "emoji": any(ord(c) > 127 and c not in "。，、；：""''（）【】" for c in description),
            "标题": "📌" in description or "🎙️" in description
        }

        found = [k for k, v in structure_elements.items() if v]

        if len(found) >= 3:
            return True, 1.0, f"描述结构良好：{', '.join(found)}", None
        elif len(found) >= 2:
            return True, 0.7, f"描述结构一般：{', '.join(found)}", "添加更多结构元素"
        else:
            return False, 0.3, "描述缺乏结构", "使用分段、列表、emoji改善可读性"

    def _check_desc_timestamps(self, description: str) -> tuple:
        import re
        timestamps = re.findall(r'\d{1,2}:\d{2}', description)

        if len(timestamps) >= 3:
            return True, 1.0, f"描述包含{len(timestamps)}个时间戳", None
        elif timestamps:
            return True, 0.6, f"描述包含{len(timestamps)}个时间戳", "添加更多时间戳"
        else:
            return False, 0.0, "描述不包含时间戳", "添加章节时间戳提升用户体验"

    def _check_desc_cta(self, description: str) -> tuple:
        cta_indicators = ["订阅", "关注", "点赞", "分享", "评论", "👉", "🔔"]

        if any(ind in description for ind in cta_indicators):
            return True, 1.0, "描述包含行动号召", None
        else:
            return False, 0.0, "描述缺少行动号召", "添加订阅、点赞、评论等引导"

    def _check_keyword_count(self, keywords: List[str], config: tuple) -> tuple:
        min_count, max_count = config[2], config[3]
        count = len(keywords)

        if min_count <= count <= max_count:
            return True, 1.0, f"关键词数量({count})适中", None
        elif count < min_count:
            return False, 0.5, f"关键词太少({count})", f"建议添加到{min_count}个以上"
        else:
            return True, 0.8, f"关键词较多({count})", "可以精选最重要的关键词"

    def _check_keyword_relevance(self, keywords: List[str], transcript: str) -> tuple:
        if not keywords:
            return False, 0.0, "没有关键词", "添加相关关键词"

        relevant = [kw for kw in keywords if kw.lower() in transcript.lower()]
        ratio = len(relevant) / len(keywords)

        if ratio >= 0.8:
            return True, 1.0, f"{len(relevant)}/{len(keywords)}个关键词与内容相关", None
        elif ratio >= 0.5:
            return True, 0.6, f"部分关键词与内容相关", "移除不相关关键词"
        else:
            return False, 0.2, "关键词与内容相关性低", "选择与内容更相关的关键词"

    def _check_keyword_density(self, keywords: List[str], description: str, config: tuple) -> tuple:
        if not description or not keywords:
            return False, 0.0, "无法计算关键词密度", None

        min_density, max_density = config[2], config[3]

        total_keywords = sum(description.lower().count(kw.lower()) for kw in keywords)
        density = total_keywords / len(description)

        if min_density <= density <= max_density:
            return True, 1.0, f"关键词密度({density:.2%})适中", None
        elif density < min_density:
            return False, 0.5, f"关键词密度过低({density:.2%})", "增加关键词使用频率"
        else:
            return False, 0.4, f"关键词密度过高({density:.2%})", "减少关键词使用，避免堆砌"

    def _check_long_tail(self, keywords: List[str]) -> tuple:
        long_tail = [kw for kw in keywords if len(kw) > 8]

        if len(long_tail) >= 3:
            return True, 1.0, f"包含{len(long_tail)}个长尾关键词", None
        elif long_tail:
            return True, 0.6, f"包含{len(long_tail)}个长尾关键词", "添加更多长尾关键词"
        else:
            return False, 0.0, "缺少长尾关键词", "添加如「如何...」「...教程」等长尾词"

    def _check_transcript_length(self, transcript: str) -> tuple:
        length = len(transcript)

        if length >= 10000:
            return True, 1.0, f"内容充实({length}字)", None
        elif length >= 5000:
            return True, 0.7, f"内容适中({length}字)", None
        else:
            return False, 0.4, f"内容较短({length}字)", "考虑增加内容深度"

    def _check_topic_coverage(self, transcript: str, keywords: List[str]) -> tuple:
        covered = [kw for kw in keywords if kw.lower() in transcript.lower()]
        ratio = len(covered) / len(keywords) if keywords else 0

        if ratio >= 0.8:
            return True, 1.0, "内容覆盖所有主题", None
        elif ratio >= 0.5:
            return True, 0.6, "内容覆盖部分主题", "增加遗漏主题的讨论"
        else:
            return False, 0.3, "主题覆盖不足", "确保内容涵盖所有关键主题"

    def _check_readability(self, transcript: str) -> tuple:
        if not transcript:
            return False, 0.0, "无内容", None

        sentences = transcript.split("。")
        avg_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0

        if 20 <= avg_length <= 50:
            return True, 1.0, "可读性良好", None
        else:
            return True, 0.6, "可读性一般", "优化句子长度"

    def _check_audio_quality(self, metadata: Optional[Dict[str, Any]]) -> tuple:
        if not metadata:
            return True, 0.5, "无音频信息", None

        bitrate = metadata.get("bitrate", 0)
        if bitrate >= 128:
            return True, 1.0, f"音频质量良好({bitrate}kbps)", None
        else:
            return False, 0.5, "音频质量一般", "提高音频比特率"

    def _check_file_format(self, metadata: Optional[Dict[str, Any]]) -> tuple:
        if not metadata:
            return True, 0.5, "无文件信息", None

        format = metadata.get("format", "").lower()
        if format in ["mp3", "m4a", "aac"]:
            return True, 1.0, f"文件格式({format})兼容性好", None
        else:
            return True, 0.7, f"文件格式：{format}", "考虑使用MP3格式"

    def _check_metadata(self, metadata: Optional[Dict[str, Any]]) -> tuple:
        if not metadata:
            return False, 0.0, "缺少元数据", "添加完整的音频元数据"

        required = ["title", "artist", "album", "genre"]
        found = [k for k in required if k in metadata]

        ratio = len(found) / len(required)
        if ratio >= 0.75:
            return True, 1.0, "元数据完整", None
        else:
            return False, ratio, f"元数据不完整({len(found)}/{len(required)})", "补充缺失的元数据"

    def _check_hook_strength(self, transcript: str) -> tuple:
        if not transcript:
            return False, 0.0, "无内容", None

        first_100 = transcript[:100]
        hook_indicators = ["你知道", "想象", "如果", "有没有想过", "今天"]

        if any(ind in first_100 for ind in hook_indicators):
            return True, 1.0, "开头有吸引力", None
        else:
            return True, 0.5, "开头一般", "使用问题或故事作为开头"

    def _check_shareability(self, title: str, description: str) -> tuple:
        share_elements = {
            "emotional": any(w in title for w in ["震撼", "感动", "爆笑"]),
            "valuable": any(w in title for w in ["技巧", "方法", "指南"]),
            "unique": any(w in title for w in ["独家", "首次", "揭秘"])
        }

        score = sum(1 for v in share_elements.values() if v) / 3

        if score >= 0.66:
            return True, 1.0, "具有较高分享潜力", None
        elif score >= 0.33:
            return True, 0.6, "分享潜力一般", "添加情感或价值元素"
        else:
            return False, 0.3, "分享潜力较低", "增加独特性和价值主张"

    def _determine_level(self, score: float) -> ScoreLevel:
        """确定评分等级"""
        if score >= 90:
            return ScoreLevel.EXCELLENT
        elif score >= 70:
            return ScoreLevel.GOOD
        elif score >= 50:
            return ScoreLevel.FAIR
        elif score >= 30:
            return ScoreLevel.POOR
        else:
            return ScoreLevel.CRITICAL

    def _identify_top_issues(self, check_items: List[SEOCheckItem]) -> List[SEOCheckItem]:
        """识别主要问题"""
        failed_items = [item for item in check_items if not item.passed]
        # 按优先级和潜在分数排序
        failed_items.sort(key=lambda x: (x.priority == "high", x.max_score - x.score), reverse=True)
        return failed_items[:5]

    def _generate_improvements(
        self,
        check_items: List[SEOCheckItem],
        category_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """生成改进建议"""
        improvements = []

        # 按类别分数排序，最低的优先
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1])

        for category, score in sorted_categories[:3]:
            if score < 70:
                category_items = [item for item in check_items if item.category == category and not item.passed]

                improvements.append({
                    "category": category,
                    "current_score": score,
                    "target_score": min(90, score + 20),
                    "actions": [
                        item.recommendation for item in category_items[:3] if item.recommendation
                    ],
                    "priority": "high" if score < 50 else "medium"
                })

        return improvements

    def _compare_with_benchmark(
        self,
        score: float,
        category_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """与基准比较"""
        return {
            "your_score": score,
            "industry_average": self.benchmark_data["avg_score"],
            "top_10_percent": self.benchmark_data["top_10_percent_score"],
            "percentile": self._calculate_percentile(score),
            "gap_to_top": self.benchmark_data["top_10_percent_score"] - score,
            "category_comparison": {
                cat: {
                    "your_score": category_scores.get(cat, 0),
                    "benchmark": 65  # 假设的基准
                }
                for cat in category_scores
            }
        }

    def _calculate_percentile(self, score: float) -> int:
        """计算百分位"""
        if score >= 90:
            return 95
        elif score >= 80:
            return 85
        elif score >= 70:
            return 70
        elif score >= 60:
            return 50
        elif score >= 50:
            return 35
        else:
            return 20

    def _generate_action_plan(
        self,
        top_issues: List[SEOCheckItem],
        improvements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成行动计划"""
        plan = []

        # 立即行动
        high_priority = [issue for issue in top_issues if issue.priority == "high"]
        if high_priority:
            plan.append({
                "phase": "立即",
                "actions": [
                    {
                        "task": issue.name,
                        "action": issue.recommendation,
                        "impact": "高"
                    }
                    for issue in high_priority[:3]
                ]
            })

        # 短期行动
        medium_priority = [issue for issue in top_issues if issue.priority == "medium"]
        if medium_priority:
            plan.append({
                "phase": "本周",
                "actions": [
                    {
                        "task": issue.name,
                        "action": issue.recommendation,
                        "impact": "中"
                    }
                    for issue in medium_priority[:3]
                ]
            })

        # 持续优化
        if improvements:
            plan.append({
                "phase": "持续",
                "actions": [
                    {
                        "task": f"优化{imp['category']}",
                        "action": ", ".join(imp["actions"][:2]),
                        "impact": imp["priority"]
                    }
                    for imp in improvements[:2]
                ]
            })

        return plan
