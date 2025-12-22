"""
描述优化器
优化播客描述以提升SEO效果
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DescriptionAnalysis:
    """描述分析结果"""
    original_length: int
    optimized_length: int
    keyword_density: float
    keywords_found: List[str]
    keywords_missing: List[str]
    readability_score: float
    seo_score: float
    structure_score: float
    suggestions: List[str]


@dataclass
class OptimizedDescription:
    """优化后的描述"""
    short_description: str  # 简短描述（160字符）
    medium_description: str  # 中等描述（500字符）
    full_description: str  # 完整描述
    meta_description: str  # 元描述
    timestamps: List[Dict[str, Any]]
    hashtags: List[str]
    keywords_used: List[str]
    analysis: DescriptionAnalysis


class DescriptionOptimizer:
    """描述优化器"""

    # 描述模板
    TEMPLATES = {
        "podcast_episode": """
🎙️ {title}

{hook}

📌 本期要点：
{key_points}

⏱️ 时间戳：
{timestamps}

🔑 关键词：{keywords}

{call_to_action}

{hashtags}
""",
        "interview": """
🎙️ {title}

{hook}

👤 本期嘉宾：{guest_name}
{guest_intro}

📌 讨论话题：
{topics}

⏱️ 时间戳：
{timestamps}

{call_to_action}

{hashtags}
""",
        "educational": """
🎙️ {title}

{hook}

📚 你将学到：
{learning_points}

📌 核心内容：
{key_points}

⏱️ 章节导航：
{timestamps}

💡 适合人群：{target_audience}

{call_to_action}

{hashtags}
"""
    }

    # CTA模板
    CTA_TEMPLATES = [
        "👉 订阅频道，不错过每一期精彩内容！",
        "💬 在评论区分享你的想法，我们下期见！",
        "🔔 点击订阅并打开通知，第一时间获取更新！",
        "❤️ 如果觉得有帮助，请点赞分享给需要的朋友！",
        "📧 有问题？在评论区留言，我们会一一回复！"
    ]

    def __init__(self):
        self.max_meta_length = 160
        self.max_short_length = 200
        self.max_medium_length = 500
        self.ideal_keyword_density = 0.02  # 2%

    def optimize_description(
        self,
        transcript: str,
        title: str,
        keywords: List[str],
        topics: List[str],
        template_type: str = "podcast_episode",
        guest_info: Optional[Dict[str, str]] = None,
        existing_description: Optional[str] = None
    ) -> OptimizedDescription:
        """
        优化播客描述

        Args:
            transcript: 转录文本
            title: 标题
            keywords: 关键词列表
            topics: 话题列表
            template_type: 模板类型
            guest_info: 嘉宾信息
            existing_description: 现有描述

        Returns:
            优化后的描述
        """
        # 生成hook
        hook = self._generate_hook(transcript, topics)

        # 提取关键点
        key_points = self._extract_key_points(transcript, topics)

        # 生成时间戳
        timestamps = self._generate_timestamps(transcript)

        # 选择CTA
        cta = self._select_cta()

        # 生成标签
        hashtags = self._generate_hashtags(keywords, topics)

        # 构建完整描述
        full_description = self._build_description(
            template_type=template_type,
            title=title,
            hook=hook,
            key_points=key_points,
            timestamps=timestamps,
            keywords=keywords,
            cta=cta,
            hashtags=hashtags,
            guest_info=guest_info,
            topics=topics
        )

        # 生成不同长度版本
        short_description = self._create_short_version(full_description, hook)
        medium_description = self._create_medium_version(full_description, hook, key_points)
        meta_description = self._create_meta_description(hook, keywords)

        # 分析描述
        analysis = self._analyze_description(
            full_description,
            existing_description,
            keywords
        )

        return OptimizedDescription(
            short_description=short_description,
            medium_description=medium_description,
            full_description=full_description,
            meta_description=meta_description,
            timestamps=timestamps,
            hashtags=hashtags,
            keywords_used=keywords,
            analysis=analysis
        )

    def _generate_hook(self, transcript: str, topics: List[str]) -> str:
        """生成开头钩子"""
        # 从转录中提取引人入胜的开头
        sentences = transcript.split("。")[:5]

        # 寻找有冲击力的句子
        hook_indicators = ["你知道", "其实", "很多人", "真相是", "今天"]

        for sentence in sentences:
            for indicator in hook_indicators:
                if indicator in sentence:
                    return sentence.strip() + "。"

        # 默认使用主题生成
        if topics:
            return f"本期节目，我们深入探讨{topics[0]}，带你了解不为人知的内幕。"

        return "本期节目精彩不容错过！"

    def _extract_key_points(
        self,
        transcript: str,
        topics: List[str]
    ) -> List[str]:
        """提取关键点"""
        key_points = []

        # 从话题生成关键点
        for i, topic in enumerate(topics[:5]):
            key_points.append(f"• {topic}")

        # 如果关键点不足，从转录中提取
        if len(key_points) < 3:
            sentences = transcript.split("。")
            for sentence in sentences:
                if len(sentence) > 20 and len(sentence) < 50:
                    if any(kw in sentence for kw in ["重要", "关键", "核心", "主要"]):
                        key_points.append(f"• {sentence.strip()}")
                        if len(key_points) >= 5:
                            break

        return key_points[:5]

    def _generate_timestamps(self, transcript: str) -> List[Dict[str, Any]]:
        """生成时间戳"""
        # 模拟时间戳生成
        # 实际实现需要结合音频分析
        timestamps = [
            {"time": "00:00", "label": "开场介绍", "seconds": 0},
            {"time": "02:30", "label": "话题引入", "seconds": 150},
            {"time": "10:00", "label": "核心内容", "seconds": 600},
            {"time": "25:00", "label": "深入讨论", "seconds": 1500},
            {"time": "40:00", "label": "总结与建议", "seconds": 2400},
            {"time": "45:00", "label": "Q&A / 结尾", "seconds": 2700}
        ]

        return timestamps

    def _select_cta(self) -> str:
        """选择行动号召"""
        import random
        return random.choice(self.CTA_TEMPLATES)

    def _generate_hashtags(
        self,
        keywords: List[str],
        topics: List[str]
    ) -> List[str]:
        """生成标签"""
        hashtags = ["#播客", "#Podcast"]

        # 从关键词生成
        for kw in keywords[:3]:
            hashtags.append(f"#{kw.replace(' ', '')}")

        # 从话题生成
        for topic in topics[:2]:
            tag = topic.replace(" ", "").replace("的", "")
            if len(tag) <= 10:
                hashtags.append(f"#{tag}")

        return list(set(hashtags))[:10]

    def _build_description(
        self,
        template_type: str,
        title: str,
        hook: str,
        key_points: List[str],
        timestamps: List[Dict[str, Any]],
        keywords: List[str],
        cta: str,
        hashtags: List[str],
        guest_info: Optional[Dict[str, str]] = None,
        topics: Optional[List[str]] = None
    ) -> str:
        """构建完整描述"""
        template = self.TEMPLATES.get(template_type, self.TEMPLATES["podcast_episode"])

        # 格式化时间戳
        timestamps_str = "\n".join([
            f"{ts['time']} - {ts['label']}" for ts in timestamps
        ])

        # 格式化关键点
        key_points_str = "\n".join(key_points)

        # 格式化标签
        hashtags_str = " ".join(hashtags)

        # 格式化关键词
        keywords_str = "、".join(keywords[:5])

        # 替换模板变量
        description = template.format(
            title=title,
            hook=hook,
            key_points=key_points_str,
            timestamps=timestamps_str,
            keywords=keywords_str,
            call_to_action=cta,
            hashtags=hashtags_str,
            guest_name=guest_info.get("name", "") if guest_info else "",
            guest_intro=guest_info.get("intro", "") if guest_info else "",
            topics="\n".join([f"• {t}" for t in (topics or [])[:5]]),
            learning_points=key_points_str,
            target_audience="对该领域感兴趣的听众"
        )

        return description.strip()

    def _create_short_version(self, full_description: str, hook: str) -> str:
        """创建简短版本"""
        # 使用hook作为基础
        short = hook

        # 确保不超过限制
        if len(short) > self.max_short_length:
            short = short[:self.max_short_length - 3] + "..."

        return short

    def _create_medium_version(
        self,
        full_description: str,
        hook: str,
        key_points: List[str]
    ) -> str:
        """创建中等版本"""
        medium = hook + "\n\n📌 要点：\n" + "\n".join(key_points[:3])

        if len(medium) > self.max_medium_length:
            medium = medium[:self.max_medium_length - 3] + "..."

        return medium

    def _create_meta_description(self, hook: str, keywords: List[str]) -> str:
        """创建元描述"""
        meta = hook

        # 尝试加入关键词
        if keywords and keywords[0] not in meta:
            meta = f"{keywords[0]}：{meta}"

        # 确保不超过限制
        if len(meta) > self.max_meta_length:
            meta = meta[:self.max_meta_length - 3] + "..."

        return meta

    def _analyze_description(
        self,
        description: str,
        original: Optional[str],
        keywords: List[str]
    ) -> DescriptionAnalysis:
        """分析描述"""
        # 计算关键词密度
        word_count = len(description)
        keyword_count = sum(description.lower().count(kw.lower()) for kw in keywords)
        keyword_density = keyword_count / word_count if word_count > 0 else 0

        # 查找关键词
        keywords_found = [kw for kw in keywords if kw.lower() in description.lower()]
        keywords_missing = [kw for kw in keywords if kw.lower() not in description.lower()]

        # 计算可读性分数
        readability_score = self._calculate_readability(description)

        # 计算SEO分数
        seo_score = self._calculate_seo_score(
            description, keywords_found, keywords, keyword_density
        )

        # 计算结构分数
        structure_score = self._calculate_structure_score(description)

        # 生成建议
        suggestions = self._generate_suggestions(
            description, keywords_missing, keyword_density, structure_score
        )

        return DescriptionAnalysis(
            original_length=len(original) if original else 0,
            optimized_length=len(description),
            keyword_density=keyword_density,
            keywords_found=keywords_found,
            keywords_missing=keywords_missing,
            readability_score=readability_score,
            seo_score=seo_score,
            structure_score=structure_score,
            suggestions=suggestions
        )

    def _calculate_readability(self, text: str) -> float:
        """计算可读性分数"""
        # 简单的可读性计算
        sentences = text.split("。")
        if not sentences:
            return 50.0

        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)

        # 理想句子长度：20-40字
        if 20 <= avg_sentence_length <= 40:
            score = 90.0
        elif 15 <= avg_sentence_length <= 50:
            score = 70.0
        else:
            score = 50.0

        # emoji加分
        if any(c in text for c in ["🎙️", "📌", "⏱️", "💡", "👉"]):
            score += 5

        return min(100, score)

    def _calculate_seo_score(
        self,
        description: str,
        keywords_found: List[str],
        all_keywords: List[str],
        keyword_density: float
    ) -> float:
        """计算SEO分数"""
        score = 0.0

        # 关键词覆盖率
        if all_keywords:
            coverage = len(keywords_found) / len(all_keywords)
            score += coverage * 40

        # 关键词密度
        if 0.01 <= keyword_density <= 0.03:
            score += 20
        elif 0.005 <= keyword_density <= 0.05:
            score += 10

        # 长度分数
        length = len(description)
        if 1000 <= length <= 2000:
            score += 20
        elif 500 <= length <= 3000:
            score += 10

        # 结构元素
        if "时间戳" in description or "⏱️" in description:
            score += 10
        if "#" in description:
            score += 10

        return min(100, score)

    def _calculate_structure_score(self, description: str) -> float:
        """计算结构分数"""
        score = 0.0

        # 检查结构元素
        structure_elements = [
            ("标题/Hook", "🎙️" in description or description.startswith("本期")),
            ("要点列表", "•" in description or "📌" in description),
            ("时间戳", "⏱️" in description or ":" in description),
            ("行动号召", "👉" in description or "订阅" in description),
            ("标签", "#" in description),
            ("分段", "\n\n" in description)
        ]

        for name, present in structure_elements:
            if present:
                score += 100 / len(structure_elements)

        return score

    def _generate_suggestions(
        self,
        description: str,
        keywords_missing: List[str],
        keyword_density: float,
        structure_score: float
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 关键词建议
        if keywords_missing:
            suggestions.append(f"考虑加入关键词：{', '.join(keywords_missing[:3])}")

        # 关键词密度建议
        if keyword_density < 0.01:
            suggestions.append("关键词密度较低，可以适当增加关键词使用")
        elif keyword_density > 0.05:
            suggestions.append("关键词密度过高，可能被视为关键词堆砌")

        # 结构建议
        if structure_score < 60:
            suggestions.append("建议添加更多结构元素（时间戳、要点列表等）")

        # 长度建议
        if len(description) < 500:
            suggestions.append("描述较短，建议扩展到1000字以上以提升SEO效果")
        elif len(description) > 3000:
            suggestions.append("描述较长，可以考虑精简非关键内容")

        # Emoji建议
        if not any(c in description for c in ["🎙️", "📌", "⏱️", "💡"]):
            suggestions.append("添加emoji可以提高视觉吸引力和可读性")

        return suggestions

    def format_for_platform(
        self,
        description: OptimizedDescription,
        platform: str
    ) -> str:
        """
        为特定平台格式化描述

        Args:
            description: 优化后的描述
            platform: 平台名称

        Returns:
            格式化后的描述
        """
        if platform == "youtube":
            return description.full_description

        elif platform == "apple_podcasts":
            # Apple Podcasts有4000字符限制
            return description.full_description[:4000]

        elif platform == "spotify":
            # Spotify显示较短描述
            return description.medium_description

        elif platform == "xiaoyuzhou":
            # 小宇宙
            return description.full_description

        elif platform == "social_media":
            # 社交媒体分享
            return description.short_description + "\n" + " ".join(description.hashtags)

        else:
            return description.full_description
