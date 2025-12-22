"""
标题生成器
生成优化的播客标题
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import re


class TitleStyle(Enum):
    """标题风格"""
    INFORMATIVE = "informative"  # 信息型
    CURIOSITY = "curiosity"  # 好奇型
    LISTICLE = "listicle"  # 列表型
    HOW_TO = "how_to"  # 教程型
    QUESTION = "question"  # 问题型
    CONTROVERSIAL = "controversial"  # 争议型
    STORY = "story"  # 故事型
    URGENT = "urgent"  # 紧迫型
    EXCLUSIVE = "exclusive"  # 独家型
    COMPARISON = "comparison"  # 对比型


@dataclass
class TitleSuggestion:
    """标题建议"""
    title: str
    style: TitleStyle
    seo_score: float
    click_potential: float
    keywords_included: List[str]
    character_count: int
    word_count: int
    power_words: List[str]
    emotional_triggers: List[str]
    improvements: List[str]


class TitleGenerator:
    """标题生成器"""

    # 标题模板
    TEMPLATES = {
        TitleStyle.INFORMATIVE: [
            "{topic}：完整指南",
            "{topic}的{number}个关键要点",
            "深度解析：{topic}",
            "{expert}详解{topic}",
            "一文读懂{topic}"
        ],
        TitleStyle.CURIOSITY: [
            "{topic}背后的真相",
            "为什么{topic}如此重要？",
            "{topic}的秘密，你知道几个？",
            "揭秘：{topic}的真实内幕",
            "你不知道的{topic}"
        ],
        TitleStyle.LISTICLE: [
            "{topic}的{number}个必知技巧",
            "{number}个关于{topic}的惊人事实",
            "顶级{expert}分享的{number}条{topic}建议",
            "{topic}：{number}步快速上手",
            "{number}个改变{topic}的方法"
        ],
        TitleStyle.HOW_TO: [
            "如何{action}：完整教程",
            "{action}的正确方法",
            "从零开始{action}",
            "专家教你{action}",
            "{action}：初学者指南"
        ],
        TitleStyle.QUESTION: [
            "{topic}真的有效吗？",
            "为什么你应该关注{topic}？",
            "{topic}：值得投入吗？",
            "什么是{topic}？为什么重要？",
            "{topic}适合你吗？"
        ],
        TitleStyle.CONTROVERSIAL: [
            "{topic}：被误解的真相",
            "关于{topic}，大多数人都错了",
            "{topic}：打破常规认知",
            "为什么{topic}的传统方法已过时",
            "{topic}：你被骗了多久？"
        ],
        TitleStyle.STORY: [
            "{expert}的{topic}之旅",
            "从{start}到{end}：{topic}故事",
            "{expert}如何通过{topic}改变人生",
            "我与{topic}的故事",
            "{topic}：一个真实的成功案例"
        ],
        TitleStyle.URGENT: [
            "{topic}：现在就要知道",
            "紧急！{topic}的最新动态",
            "{topic}：你不能再等了",
            "立即行动：{topic}指南",
            "{year}年{topic}必备知识"
        ],
        TitleStyle.EXCLUSIVE: [
            "独家：{expert}首次公开{topic}",
            "{topic}内部消息",
            "首发：{topic}深度报告",
            "仅此一次：{topic}独家分享",
            "{expert}独家揭秘{topic}"
        ],
        TitleStyle.COMPARISON: [
            "{topic_a} vs {topic_b}：哪个更好？",
            "{topic}：{option_a}还是{option_b}？",
            "对比分析：{topic}的两种方法",
            "{topic}：传统vs现代方法",
            "深度对比：{topic}主流方案"
        ]
    }

    # 力量词汇
    POWER_WORDS = {
        "zh": [
            "惊人", "独家", "秘密", "免费", "立即", "限时",
            "必备", "终极", "完整", "深度", "权威", "专业",
            "突破", "革命", "颠覆", "震撼", "独特", "稀缺",
            "揭秘", "内幕", "真相", "实战", "干货", "精华"
        ],
        "en": [
            "amazing", "exclusive", "secret", "free", "instant", "limited",
            "essential", "ultimate", "complete", "deep", "authority", "professional",
            "breakthrough", "revolutionary", "game-changing", "shocking", "unique", "rare",
            "revealed", "insider", "truth", "practical", "valuable", "premium"
        ]
    }

    # 情感触发词
    EMOTIONAL_TRIGGERS = {
        "curiosity": ["秘密", "揭秘", "真相", "内幕", "背后"],
        "urgency": ["立即", "现在", "紧急", "限时", "最后"],
        "fear": ["警告", "危险", "错误", "避免", "别再"],
        "greed": ["免费", "赚钱", "省钱", "增长", "翻倍"],
        "trust": ["专家", "权威", "研究", "证实", "官方"],
        "social": ["流行", "热门", "大家", "所有人", "趋势"]
    }

    def __init__(self, language: str = "zh"):
        self.language = language
        self.power_words = self.POWER_WORDS.get(language, self.POWER_WORDS["zh"])

    def generate_titles(
        self,
        transcript: str,
        topics: List[str],
        keywords: List[str],
        guest_name: Optional[str] = None,
        style_preferences: Optional[List[TitleStyle]] = None,
        count: int = 10
    ) -> List[TitleSuggestion]:
        """
        生成标题建议

        Args:
            transcript: 转录文本
            topics: 主题列表
            keywords: 关键词列表
            guest_name: 嘉宾名
            style_preferences: 偏好风格
            count: 生成数量

        Returns:
            标题建议列表
        """
        suggestions = []

        # 确定要使用的风格
        styles = style_preferences or list(TitleStyle)

        # 提取关键信息
        main_topic = topics[0] if topics else "播客话题"
        numbers = self._extract_numbers(transcript)
        actions = self._extract_actions(transcript)

        for style in styles:
            templates = self.TEMPLATES.get(style, [])

            for template in templates[:2]:  # 每种风格最多2个模板
                title = self._fill_template(
                    template=template,
                    topic=main_topic,
                    topics=topics,
                    keywords=keywords,
                    expert=guest_name or "专家",
                    numbers=numbers,
                    actions=actions
                )

                if title:
                    suggestion = self._analyze_title(title, style, keywords)
                    suggestions.append(suggestion)

        # 按SEO分数排序
        suggestions.sort(key=lambda x: x.seo_score, reverse=True)

        return suggestions[:count]

    def _fill_template(
        self,
        template: str,
        topic: str,
        topics: List[str],
        keywords: List[str],
        expert: str,
        numbers: List[int],
        actions: List[str]
    ) -> Optional[str]:
        """填充模板"""
        try:
            # 准备变量
            variables = {
                "topic": topic,
                "expert": expert,
                "number": numbers[0] if numbers else 5,
                "action": actions[0] if actions else f"掌握{topic}",
                "year": "2024",
                "start": "新手",
                "end": "专家"
            }

            # 处理对比类型
            if len(topics) >= 2:
                variables["topic_a"] = topics[0]
                variables["topic_b"] = topics[1]
                variables["option_a"] = topics[0]
                variables["option_b"] = topics[1]

            # 填充模板
            title = template
            for key, value in variables.items():
                title = title.replace(f"{{{key}}}", str(value))

            # 检查是否还有未填充的占位符
            if "{" in title:
                return None

            return title

        except Exception:
            return None

    def _extract_numbers(self, transcript: str) -> List[int]:
        """从转录中提取数字"""
        numbers = re.findall(r'\b(\d+)\b', transcript)
        numbers = [int(n) for n in numbers if 3 <= int(n) <= 15]
        return numbers or [5, 7, 10]

    def _extract_actions(self, transcript: str) -> List[str]:
        """从转录中提取动作"""
        action_patterns = [
            r"如何(.{2,10})",
            r"怎样(.{2,10})",
            r"学会(.{2,10})",
            r"掌握(.{2,10})"
        ]

        actions = []
        for pattern in action_patterns:
            matches = re.findall(pattern, transcript)
            actions.extend(matches)

        return actions[:5] if actions else ["提升效率", "实现目标"]

    def _analyze_title(
        self,
        title: str,
        style: TitleStyle,
        target_keywords: List[str]
    ) -> TitleSuggestion:
        """分析标题"""
        # 基础统计
        char_count = len(title)
        word_count = len(title.split())

        # 查找包含的关键词
        keywords_included = [kw for kw in target_keywords if kw.lower() in title.lower()]

        # 查找力量词汇
        power_words_found = [pw for pw in self.power_words if pw in title]

        # 查找情感触发词
        emotional_triggers = []
        for trigger_type, words in self.EMOTIONAL_TRIGGERS.items():
            for word in words:
                if word in title:
                    emotional_triggers.append(trigger_type)
                    break

        # 计算SEO分数
        seo_score = self._calculate_seo_score(
            title=title,
            keywords_included=keywords_included,
            target_keywords=target_keywords,
            power_words=power_words_found
        )

        # 计算点击潜力
        click_potential = self._calculate_click_potential(
            title=title,
            style=style,
            power_words=power_words_found,
            emotional_triggers=emotional_triggers
        )

        # 生成改进建议
        improvements = self._generate_improvements(
            title=title,
            char_count=char_count,
            keywords_included=keywords_included,
            target_keywords=target_keywords,
            power_words=power_words_found
        )

        return TitleSuggestion(
            title=title,
            style=style,
            seo_score=seo_score,
            click_potential=click_potential,
            keywords_included=keywords_included,
            character_count=char_count,
            word_count=word_count,
            power_words=power_words_found,
            emotional_triggers=list(set(emotional_triggers)),
            improvements=improvements
        )

    def _calculate_seo_score(
        self,
        title: str,
        keywords_included: List[str],
        target_keywords: List[str],
        power_words: List[str]
    ) -> float:
        """计算SEO分数"""
        score = 0.0

        # 长度分数（理想长度：50-60字符）
        length = len(title)
        if 50 <= length <= 60:
            score += 25
        elif 40 <= length <= 70:
            score += 15
        elif 30 <= length <= 80:
            score += 10
        else:
            score += 5

        # 关键词分数
        if target_keywords:
            keyword_ratio = len(keywords_included) / len(target_keywords)
            score += keyword_ratio * 35

            # 关键词位置加分（出现在开头更好）
            for kw in keywords_included:
                if title.lower().startswith(kw.lower()):
                    score += 10
                    break
                elif kw.lower() in title[:len(title)//2].lower():
                    score += 5
                    break

        # 力量词汇分数
        score += min(len(power_words) * 5, 15)

        # 标点符号检查（有冒号或问号通常更好）
        if "：" in title or ":" in title:
            score += 5
        if "？" in title or "?" in title:
            score += 5

        # 数字加分
        if any(c.isdigit() for c in title):
            score += 5

        return min(100, score)

    def _calculate_click_potential(
        self,
        title: str,
        style: TitleStyle,
        power_words: List[str],
        emotional_triggers: List[str]
    ) -> float:
        """计算点击潜力"""
        score = 50.0  # 基础分

        # 风格加分
        high_click_styles = [TitleStyle.CURIOSITY, TitleStyle.LISTICLE, TitleStyle.CONTROVERSIAL]
        if style in high_click_styles:
            score += 15

        # 力量词汇加分
        score += min(len(power_words) * 8, 20)

        # 情感触发加分
        score += min(len(emotional_triggers) * 5, 15)

        # 简洁性（太长会降低）
        if len(title) > 70:
            score -= 10
        elif len(title) < 40:
            score += 5

        return min(100, max(0, score))

    def _generate_improvements(
        self,
        title: str,
        char_count: int,
        keywords_included: List[str],
        target_keywords: List[str],
        power_words: List[str]
    ) -> List[str]:
        """生成改进建议"""
        improvements = []

        # 长度建议
        if char_count > 70:
            improvements.append("标题过长，建议缩短至60字符以内")
        elif char_count < 30:
            improvements.append("标题较短，可以添加更多描述性词汇")

        # 关键词建议
        missing_keywords = [kw for kw in target_keywords if kw not in keywords_included]
        if missing_keywords:
            improvements.append(f"考虑加入关键词：{', '.join(missing_keywords[:3])}")

        # 力量词汇建议
        if len(power_words) < 2:
            improvements.append("添加更多力量词汇以提高吸引力")

        # 数字建议
        if not any(c.isdigit() for c in title):
            improvements.append("考虑在标题中加入数字（如「5个技巧」）")

        # 标点建议
        if "：" not in title and ":" not in title and "？" not in title:
            improvements.append("使用冒号或问号可以提高标题的吸引力")

        return improvements

    def optimize_title(
        self,
        original_title: str,
        keywords: List[str],
        max_length: int = 60
    ) -> Dict[str, Any]:
        """
        优化现有标题

        Args:
            original_title: 原始标题
            keywords: 目标关键词
            max_length: 最大长度

        Returns:
            优化建议
        """
        analysis = self._analyze_title(original_title, TitleStyle.INFORMATIVE, keywords)

        optimized_versions = []

        # 生成优化版本
        if analysis.seo_score < 70:
            # 添加力量词
            for pw in self.power_words[:3]:
                if pw not in original_title:
                    new_title = f"{pw}：{original_title}"
                    if len(new_title) <= max_length:
                        optimized_versions.append(new_title)
                    break

            # 添加关键词
            for kw in keywords[:2]:
                if kw not in original_title:
                    new_title = f"{original_title} | {kw}"
                    if len(new_title) <= max_length:
                        optimized_versions.append(new_title)
                    break

        return {
            "original": original_title,
            "original_score": analysis.seo_score,
            "optimized_versions": optimized_versions,
            "analysis": analysis,
            "recommendations": analysis.improvements
        }

    def generate_ab_test_variants(
        self,
        base_title: str,
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        生成A/B测试变体

        Args:
            base_title: 基础标题
            count: 变体数量

        Returns:
            变体列表
        """
        variants = [{"title": base_title, "variant": "A (Original)"}]

        # 变体B：添加数字
        variant_b = re.sub(r'^', '5个关于', base_title) + "的技巧"
        if len(variant_b) <= 70:
            variants.append({"title": variant_b, "variant": "B (Numbered)"})

        # 变体C：问题形式
        variant_c = f"为什么{base_title}如此重要？"
        if len(variant_c) <= 70:
            variants.append({"title": variant_c, "variant": "C (Question)"})

        # 变体D：紧迫感
        variant_d = f"必看：{base_title}"
        if len(variant_d) <= 70:
            variants.append({"title": variant_d, "variant": "D (Urgent)"})

        return variants[:count + 1]
