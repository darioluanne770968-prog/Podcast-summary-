"""
关键词分析器
分析和优化播客关键词策略
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter
import re


class KeywordType(Enum):
    """关键词类型"""
    PRIMARY = "primary"  # 主关键词
    SECONDARY = "secondary"  # 次要关键词
    LONG_TAIL = "long_tail"  # 长尾关键词
    BRANDED = "branded"  # 品牌关键词
    COMPETITOR = "competitor"  # 竞品关键词
    QUESTION = "question"  # 问题关键词
    TRENDING = "trending"  # 趋势关键词


class KeywordIntent(Enum):
    """关键词意图"""
    INFORMATIONAL = "informational"  # 信息获取
    NAVIGATIONAL = "navigational"  # 导航
    TRANSACTIONAL = "transactional"  # 交易
    COMMERCIAL = "commercial"  # 商业调研


@dataclass
class Keyword:
    """关键词"""
    word: str
    type: KeywordType
    intent: KeywordIntent
    search_volume: int  # 搜索量估计
    competition: float  # 竞争度 0-1
    relevance: float  # 相关性 0-1
    current_ranking: Optional[int] = None
    trend: str = "stable"  # rising, stable, declining
    related_keywords: List[str] = field(default_factory=list)


@dataclass
class KeywordAnalysisResult:
    """关键词分析结果"""
    primary_keywords: List[Keyword]
    secondary_keywords: List[Keyword]
    long_tail_keywords: List[Keyword]
    question_keywords: List[Keyword]
    keyword_gaps: List[str]
    optimization_opportunities: List[Dict[str, Any]]
    competitor_keywords: List[Keyword]
    trending_keywords: List[Keyword]
    overall_strategy: Dict[str, Any]


class KeywordAnalyzer:
    """关键词分析器"""

    # 停用词
    STOP_WORDS = {
        "zh": ["的", "是", "在", "了", "和", "与", "或", "这", "那", "有", "就",
               "也", "都", "还", "要", "会", "能", "可以", "但是", "而且", "所以",
               "因为", "如果", "虽然", "不过", "然后", "我们", "他们", "你们"],
        "en": ["the", "a", "an", "is", "are", "was", "were", "be", "been",
               "being", "have", "has", "had", "do", "does", "did", "will",
               "would", "could", "should", "may", "might", "must", "shall"]
    }

    # 问题词
    QUESTION_WORDS = {
        "zh": ["什么", "为什么", "怎么", "如何", "哪个", "哪些", "何时", "何地", "是否"],
        "en": ["what", "why", "how", "which", "when", "where", "who", "whose"]
    }

    def __init__(self, language: str = "zh"):
        self.language = language
        self.stop_words = set(self.STOP_WORDS.get(language, []))
        self.question_words = self.QUESTION_WORDS.get(language, [])
        self.keyword_cache: Dict[str, Keyword] = {}

    def analyze_transcript(
        self,
        transcript: str,
        title: str,
        existing_keywords: Optional[List[str]] = None
    ) -> KeywordAnalysisResult:
        """
        分析转录文本提取关键词

        Args:
            transcript: 转录文本
            title: 标题
            existing_keywords: 现有关键词

        Returns:
            关键词分析结果
        """
        # 提取所有关键词
        all_keywords = self._extract_keywords(transcript + " " + title)

        # 分类关键词
        primary = self._identify_primary_keywords(all_keywords, title)
        secondary = self._identify_secondary_keywords(all_keywords, primary)
        long_tail = self._generate_long_tail_keywords(primary, transcript)
        questions = self._extract_question_keywords(transcript)

        # 分析关键词差距
        keyword_gaps = self._identify_keyword_gaps(
            primary + secondary,
            existing_keywords or []
        )

        # 发现优化机会
        opportunities = self._find_optimization_opportunities(
            primary, secondary, long_tail
        )

        # 获取趋势关键词
        trending = self._get_trending_keywords(primary)

        # 生成整体策略
        strategy = self._generate_strategy(
            primary, secondary, long_tail, questions
        )

        return KeywordAnalysisResult(
            primary_keywords=primary,
            secondary_keywords=secondary,
            long_tail_keywords=long_tail,
            question_keywords=questions,
            keyword_gaps=keyword_gaps,
            optimization_opportunities=opportunities,
            competitor_keywords=[],  # 需要外部数据
            trending_keywords=trending,
            overall_strategy=strategy
        )

    def _extract_keywords(self, text: str) -> List[Tuple[str, int]]:
        """提取关键词及其频率"""
        # 分词（简单实现）
        if self.language == "zh":
            # 中文：使用简单的切分
            words = self._chinese_tokenize(text)
        else:
            # 英文：空格分词
            words = text.lower().split()

        # 过滤停用词
        words = [w for w in words if w not in self.stop_words and len(w) > 1]

        # 统计词频
        word_counts = Counter(words)

        return word_counts.most_common(100)

    def _chinese_tokenize(self, text: str) -> List[str]:
        """中文分词（简单实现）"""
        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)

        # 提取连续的中文字符
        words = []

        # 提取2-4字的词组
        for length in [4, 3, 2]:
            for i in range(len(text) - length + 1):
                word = text[i:i + length]
                if all('\u4e00' <= c <= '\u9fff' for c in word):
                    words.append(word)

        return words

    def _identify_primary_keywords(
        self,
        all_keywords: List[Tuple[str, int]],
        title: str
    ) -> List[Keyword]:
        """识别主关键词"""
        primary = []

        # 标题中的词优先
        title_words = set(self._chinese_tokenize(title) if self.language == "zh" else title.lower().split())

        for word, count in all_keywords[:20]:
            if word in title_words or count >= 5:
                keyword = Keyword(
                    word=word,
                    type=KeywordType.PRIMARY,
                    intent=self._determine_intent(word),
                    search_volume=self._estimate_search_volume(word),
                    competition=self._estimate_competition(word),
                    relevance=min(1.0, count / 10),
                    trend=self._get_trend(word)
                )
                primary.append(keyword)

                if len(primary) >= 5:
                    break

        return primary

    def _identify_secondary_keywords(
        self,
        all_keywords: List[Tuple[str, int]],
        primary: List[Keyword]
    ) -> List[Keyword]:
        """识别次要关键词"""
        primary_words = {kw.word for kw in primary}
        secondary = []

        for word, count in all_keywords:
            if word in primary_words:
                continue

            if count >= 2:
                keyword = Keyword(
                    word=word,
                    type=KeywordType.SECONDARY,
                    intent=self._determine_intent(word),
                    search_volume=self._estimate_search_volume(word),
                    competition=self._estimate_competition(word),
                    relevance=min(1.0, count / 5)
                )
                secondary.append(keyword)

                if len(secondary) >= 10:
                    break

        return secondary

    def _generate_long_tail_keywords(
        self,
        primary: List[Keyword],
        transcript: str
    ) -> List[Keyword]:
        """生成长尾关键词"""
        long_tail = []

        # 长尾关键词模板
        templates = {
            "zh": [
                "{kw}是什么",
                "如何{kw}",
                "{kw}的方法",
                "{kw}技巧",
                "{kw}入门指南",
                "最好的{kw}",
                "{kw}推荐",
                "{kw}教程"
            ],
            "en": [
                "what is {kw}",
                "how to {kw}",
                "{kw} guide",
                "{kw} tips",
                "best {kw}",
                "{kw} tutorial",
                "{kw} for beginners"
            ]
        }

        templates_list = templates.get(self.language, templates["zh"])

        for kw in primary[:3]:
            for template in templates_list[:3]:
                long_tail_word = template.format(kw=kw.word)

                keyword = Keyword(
                    word=long_tail_word,
                    type=KeywordType.LONG_TAIL,
                    intent=KeywordIntent.INFORMATIONAL,
                    search_volume=self._estimate_search_volume(long_tail_word) // 10,
                    competition=max(0.1, kw.competition - 0.3),
                    relevance=kw.relevance * 0.8
                )
                long_tail.append(keyword)

        return long_tail

    def _extract_question_keywords(self, transcript: str) -> List[Keyword]:
        """提取问题关键词"""
        questions = []

        # 查找问句
        question_patterns = [
            r'(什么[^？。]*[？?])',
            r'(为什么[^？。]*[？?])',
            r'(怎么[^？。]*[？?])',
            r'(如何[^？。]*[？?])',
            r'(哪[个些][^？。]*[？?])'
        ]

        for pattern in question_patterns:
            matches = re.findall(pattern, transcript)
            for match in matches[:2]:
                keyword = Keyword(
                    word=match.strip(),
                    type=KeywordType.QUESTION,
                    intent=KeywordIntent.INFORMATIONAL,
                    search_volume=self._estimate_search_volume(match) // 5,
                    competition=0.3,
                    relevance=0.7
                )
                questions.append(keyword)

        return questions[:10]

    def _determine_intent(self, word: str) -> KeywordIntent:
        """确定关键词意图"""
        informational_indicators = ["什么", "如何", "为什么", "教程", "指南", "入门"]
        transactional_indicators = ["购买", "下载", "注册", "订阅", "价格"]
        commercial_indicators = ["最好", "推荐", "对比", "评测", "哪个"]

        for indicator in informational_indicators:
            if indicator in word:
                return KeywordIntent.INFORMATIONAL

        for indicator in transactional_indicators:
            if indicator in word:
                return KeywordIntent.TRANSACTIONAL

        for indicator in commercial_indicators:
            if indicator in word:
                return KeywordIntent.COMMERCIAL

        return KeywordIntent.INFORMATIONAL

    def _estimate_search_volume(self, word: str) -> int:
        """估算搜索量"""
        # 简单的启发式估算
        base_volume = 1000

        # 短词通常搜索量更大
        if len(word) <= 4:
            base_volume *= 2

        # 热门词汇加成
        hot_words = ["AI", "人工智能", "创业", "投资", "教程", "指南"]
        if any(hw in word for hw in hot_words):
            base_volume *= 3

        return base_volume

    def _estimate_competition(self, word: str) -> float:
        """估算竞争度"""
        # 简单的启发式估算
        competition = 0.5

        # 短词竞争更激烈
        if len(word) <= 2:
            competition += 0.3
        elif len(word) >= 6:
            competition -= 0.2

        # 长尾词竞争较低
        if len(word) > 10:
            competition -= 0.3

        return max(0.1, min(0.9, competition))

    def _get_trend(self, word: str) -> str:
        """获取趋势"""
        # 模拟趋势数据
        rising_topics = ["AI", "GPT", "人工智能", "大模型", "自动化"]
        declining_topics = ["区块链", "NFT", "元宇宙"]

        if any(topic in word for topic in rising_topics):
            return "rising"
        elif any(topic in word for topic in declining_topics):
            return "declining"

        return "stable"

    def _identify_keyword_gaps(
        self,
        current_keywords: List[Keyword],
        existing_keywords: List[str]
    ) -> List[str]:
        """识别关键词差距"""
        current_words = {kw.word for kw in current_keywords}
        existing_set = set(existing_keywords)

        # 找出现有但未使用的关键词
        gaps = list(existing_set - current_words)

        # 建议添加的关键词
        suggested_additions = [
            "播客", "podcast", "音频", "节目",
            "干货", "分享", "深度", "解读"
        ]

        for suggestion in suggested_additions:
            if suggestion not in current_words and suggestion not in gaps:
                gaps.append(suggestion)

        return gaps[:10]

    def _find_optimization_opportunities(
        self,
        primary: List[Keyword],
        secondary: List[Keyword],
        long_tail: List[Keyword]
    ) -> List[Dict[str, Any]]:
        """发现优化机会"""
        opportunities = []

        # 低竞争高相关性机会
        for kw in secondary + long_tail:
            if kw.competition < 0.4 and kw.relevance > 0.6:
                opportunities.append({
                    "keyword": kw.word,
                    "type": "low_competition",
                    "description": f"低竞争关键词机会：{kw.word}",
                    "priority": "high",
                    "action": f"在标题和描述中使用「{kw.word}」"
                })

        # 上升趋势机会
        for kw in primary + secondary:
            if kw.trend == "rising":
                opportunities.append({
                    "keyword": kw.word,
                    "type": "trending",
                    "description": f"热门上升关键词：{kw.word}",
                    "priority": "high",
                    "action": f"围绕「{kw.word}」创作更多内容"
                })

        # 问题关键词机会
        for kw in long_tail:
            if kw.type == KeywordType.QUESTION or any(
                qw in kw.word for qw in self.question_words
            ):
                opportunities.append({
                    "keyword": kw.word,
                    "type": "question",
                    "description": f"问答类关键词：{kw.word}",
                    "priority": "medium",
                    "action": "创建FAQ或问答类内容"
                })

        return opportunities[:10]

    def _get_trending_keywords(self, primary: List[Keyword]) -> List[Keyword]:
        """获取趋势关键词"""
        trending = []

        # 模拟热门话题
        trending_topics = [
            ("AI播客", 0.9),
            ("GPT应用", 0.85),
            ("效率提升", 0.75),
            ("远程工作", 0.7),
            ("自媒体", 0.65)
        ]

        for topic, relevance in trending_topics:
            keyword = Keyword(
                word=topic,
                type=KeywordType.TRENDING,
                intent=KeywordIntent.INFORMATIONAL,
                search_volume=5000,
                competition=0.6,
                relevance=relevance,
                trend="rising"
            )
            trending.append(keyword)

        return trending

    def _generate_strategy(
        self,
        primary: List[Keyword],
        secondary: List[Keyword],
        long_tail: List[Keyword],
        questions: List[Keyword]
    ) -> Dict[str, Any]:
        """生成关键词策略"""
        return {
            "focus_keywords": [kw.word for kw in primary[:3]],
            "supporting_keywords": [kw.word for kw in secondary[:5]],
            "content_opportunities": [kw.word for kw in long_tail[:5]],
            "faq_topics": [kw.word for kw in questions[:5]],
            "recommendations": [
                "确保主关键词出现在标题开头",
                "在描述的前100字内使用主要关键词",
                "创建针对长尾关键词的专题内容",
                "在每期节目中自然使用2-3个次要关键词",
                "定期创建回答问题类关键词的内容"
            ],
            "keyword_density_target": {
                "title": "1-2个主关键词",
                "description": "主关键词2-3次，次要关键词各1-2次",
                "tags": "包含所有主要和次要关键词"
            }
        }

    def get_keyword_suggestions(
        self,
        seed_keyword: str,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取关键词建议

        Args:
            seed_keyword: 种子关键词
            count: 建议数量

        Returns:
            关键词建议列表
        """
        suggestions = []

        # 基于种子词生成变体
        prefixes = ["最新", "2024", "完整", "深度", "专业"]
        suffixes = ["教程", "指南", "技巧", "方法", "推荐"]

        for prefix in prefixes:
            suggestions.append({
                "keyword": f"{prefix}{seed_keyword}",
                "type": "prefix_variation",
                "estimated_volume": 500
            })

        for suffix in suffixes:
            suggestions.append({
                "keyword": f"{seed_keyword}{suffix}",
                "type": "suffix_variation",
                "estimated_volume": 800
            })

        # 问题变体
        questions = [
            f"什么是{seed_keyword}",
            f"如何学习{seed_keyword}",
            f"{seed_keyword}有什么用",
            f"为什么要学{seed_keyword}"
        ]

        for q in questions:
            suggestions.append({
                "keyword": q,
                "type": "question",
                "estimated_volume": 300
            })

        return suggestions[:count]
