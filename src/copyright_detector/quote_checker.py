"""
引用检查器
检测文本中的引用和潜在的版权问题
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import re


class QuoteType(Enum):
    """引用类型"""
    BOOK = "book"  # 书籍引用
    ARTICLE = "article"  # 文章引用
    SPEECH = "speech"  # 演讲引用
    SONG_LYRICS = "song_lyrics"  # 歌词引用
    MOVIE_SCRIPT = "movie_script"  # 电影台词
    TRADEMARK = "trademark"  # 商标
    SLOGAN = "slogan"  # 广告语
    PROVERB = "proverb"  # 谚语/格言
    UNKNOWN = "unknown"


class FairUseCategory(Enum):
    """合理使用类别"""
    CRITICISM = "criticism"  # 批评
    COMMENT = "comment"  # 评论
    NEWS_REPORTING = "news_reporting"  # 新闻报道
    TEACHING = "teaching"  # 教学
    SCHOLARSHIP = "scholarship"  # 学术研究
    PARODY = "parody"  # 戏仿
    UNCLEAR = "unclear"  # 不明确


@dataclass
class Quote:
    """引用"""
    text: str
    start_position: int
    end_position: int
    quote_type: QuoteType
    source: Optional[str] = None
    author: Optional[str] = None
    is_attributed: bool = False
    word_count: int = 0
    fair_use_likely: bool = True
    fair_use_category: Optional[FairUseCategory] = None
    risk_level: str = "low"  # low, medium, high
    recommendations: List[str] = field(default_factory=list)


@dataclass
class QuoteCheckResult:
    """引用检查结果"""
    total_quotes: int
    high_risk_quotes: int
    quotes: List[Quote]
    overall_risk: str
    total_quoted_words: int
    quoted_percentage: float
    recommendations: List[str]


class QuoteChecker:
    """引用检查器"""

    # 引用标记模式
    QUOTE_PATTERNS = [
        (r'"([^"]{10,})"', "double_quote"),
        (r'"([^"]{10,})"', "smart_quote"),
        (r'「([^」]{10,})」', "chinese_quote"),
        (r'『([^』]{10,})』', "chinese_double_quote"),
        (r"'([^']{10,})'", "single_quote"),
    ]

    # 归属标记
    ATTRIBUTION_PATTERNS = [
        r'——\s*([^\n]+)',  # 中文破折号
        r'—\s*([^\n]+)',  # 英文破折号
        r'-\s*([^\n]+)$',  # 短横线
        r'[\(（]\s*([^)）]+)\s*[\)）]',  # 括号
        r'(?:说|says?|said|according to)\s+([^\n,，。]+)',  # 动词引导
    ]

    # 已知的公共领域引用
    PUBLIC_DOMAIN_QUOTES = [
        "一千个读者就有一千个哈姆雷特",
        "知识就是力量",
        "时间就是金钱",
        "天下没有免费的午餐",
    ]

    # 已知的商标/版权短语
    TRADEMARKED_PHRASES = [
        "Just Do It",
        "Think Different",
        "I'm Lovin' It",
    ]

    def __init__(self):
        self.known_sources: Dict[str, Dict[str, Any]] = {}
        self._load_known_sources()

    def _load_known_sources(self):
        """加载已知来源数据库"""
        self.known_sources = {
            "steve_jobs": {
                "author": "史蒂夫·乔布斯",
                "type": QuoteType.SPEECH,
                "protected": False,
                "famous_quotes": [
                    "Stay hungry, stay foolish",
                    "Innovation distinguishes between a leader and a follower"
                ]
            },
            "confucius": {
                "author": "孔子",
                "type": QuoteType.PROVERB,
                "protected": False,  # 公共领域
                "famous_quotes": [
                    "学而不思则罔，思而不学则殆",
                    "三人行，必有我师焉"
                ]
            }
        }

    def check_quotes(
        self,
        text: str,
        context: Optional[str] = None
    ) -> QuoteCheckResult:
        """
        检查文本中的引用

        Args:
            text: 要检查的文本
            context: 上下文（用于判断合理使用）

        Returns:
            引用检查结果
        """
        # 提取所有引用
        quotes = self._extract_quotes(text)

        # 分析每个引用
        analyzed_quotes = []
        for quote in quotes:
            analyzed = self._analyze_quote(quote, text, context)
            analyzed_quotes.append(analyzed)

        # 计算统计
        total_quoted_words = sum(q.word_count for q in analyzed_quotes)
        total_words = len(text.split())
        quoted_percentage = total_quoted_words / total_words * 100 if total_words > 0 else 0

        high_risk_quotes = sum(1 for q in analyzed_quotes if q.risk_level == "high")

        # 确定整体风险
        if high_risk_quotes > 0:
            overall_risk = "high"
        elif quoted_percentage > 20 or any(q.risk_level == "medium" for q in analyzed_quotes):
            overall_risk = "medium"
        else:
            overall_risk = "low"

        # 生成整体建议
        recommendations = self._generate_overall_recommendations(
            analyzed_quotes, quoted_percentage, overall_risk
        )

        return QuoteCheckResult(
            total_quotes=len(analyzed_quotes),
            high_risk_quotes=high_risk_quotes,
            quotes=analyzed_quotes,
            overall_risk=overall_risk,
            total_quoted_words=total_quoted_words,
            quoted_percentage=quoted_percentage,
            recommendations=recommendations
        )

    def _extract_quotes(self, text: str) -> List[Dict[str, Any]]:
        """提取引用"""
        quotes = []

        for pattern, pattern_type in self.QUOTE_PATTERNS:
            for match in re.finditer(pattern, text):
                quote_text = match.group(1)
                quotes.append({
                    "text": quote_text,
                    "start": match.start(),
                    "end": match.end(),
                    "pattern_type": pattern_type
                })

        # 去重（基于位置重叠）
        quotes = self._deduplicate_quotes(quotes)

        return quotes

    def _deduplicate_quotes(self, quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复引用"""
        if not quotes:
            return []

        # 按开始位置排序
        quotes.sort(key=lambda x: x["start"])

        deduplicated = [quotes[0]]
        for quote in quotes[1:]:
            last = deduplicated[-1]
            # 检查重叠
            if quote["start"] >= last["end"]:
                deduplicated.append(quote)

        return deduplicated

    def _analyze_quote(
        self,
        quote_data: Dict[str, Any],
        full_text: str,
        context: Optional[str]
    ) -> Quote:
        """分析单个引用"""
        text = quote_data["text"]
        word_count = len(text.split())

        # 检测引用类型
        quote_type = self._detect_quote_type(text)

        # 查找归属
        source, author = self._find_attribution(
            full_text, quote_data["end"]
        )

        # 检查是否是已知来源
        known_info = self._check_known_source(text)
        if known_info:
            author = known_info.get("author", author)
            source = known_info.get("source", source)

        # 判断合理使用
        fair_use_likely, fair_use_category = self._assess_fair_use(
            text, quote_type, context, word_count
        )

        # 评估风险
        risk_level = self._assess_risk(
            quote_type, word_count, source is not None, fair_use_likely
        )

        # 生成建议
        recommendations = self._generate_quote_recommendations(
            quote_type, source, author, word_count, risk_level
        )

        return Quote(
            text=text,
            start_position=quote_data["start"],
            end_position=quote_data["end"],
            quote_type=quote_type,
            source=source,
            author=author,
            is_attributed=source is not None or author is not None,
            word_count=word_count,
            fair_use_likely=fair_use_likely,
            fair_use_category=fair_use_category,
            risk_level=risk_level,
            recommendations=recommendations
        )

    def _detect_quote_type(self, text: str) -> QuoteType:
        """检测引用类型"""
        # 检查歌词特征
        if self._looks_like_lyrics(text):
            return QuoteType.SONG_LYRICS

        # 检查商标
        for trademark in self.TRADEMARKED_PHRASES:
            if trademark.lower() in text.lower():
                return QuoteType.TRADEMARK

        # 检查谚语
        for proverb in self.PUBLIC_DOMAIN_QUOTES:
            if proverb in text:
                return QuoteType.PROVERB

        # 默认为未知
        return QuoteType.UNKNOWN

    def _looks_like_lyrics(self, text: str) -> bool:
        """检查是否像歌词"""
        # 歌词特征：短行、重复、押韵
        lines = text.split('\n')
        if len(lines) > 2:
            avg_line_length = sum(len(l) for l in lines) / len(lines)
            if avg_line_length < 30:
                return True
        return False

    def _find_attribution(
        self,
        full_text: str,
        quote_end: int
    ) -> tuple[Optional[str], Optional[str]]:
        """查找引用归属"""
        # 查看引用后的文本
        after_quote = full_text[quote_end:quote_end + 100]

        for pattern in self.ATTRIBUTION_PATTERNS:
            match = re.search(pattern, after_quote)
            if match:
                attribution = match.group(1).strip()
                # 尝试分离来源和作者
                if "《" in attribution and "》" in attribution:
                    source_match = re.search(r'《([^》]+)》', attribution)
                    source = source_match.group(1) if source_match else None
                    author = attribution.replace(f"《{source}》", "").strip() if source else None
                    return source, author
                return None, attribution

        return None, None

    def _check_known_source(self, text: str) -> Optional[Dict[str, Any]]:
        """检查是否是已知来源"""
        for source_id, source_info in self.known_sources.items():
            for famous_quote in source_info.get("famous_quotes", []):
                if famous_quote in text or text in famous_quote:
                    return {
                        "author": source_info["author"],
                        "type": source_info["type"],
                        "protected": source_info["protected"]
                    }
        return None

    def _assess_fair_use(
        self,
        text: str,
        quote_type: QuoteType,
        context: Optional[str],
        word_count: int
    ) -> tuple[bool, Optional[FairUseCategory]]:
        """评估合理使用"""
        # 歌词和商标通常不适用合理使用
        if quote_type in [QuoteType.SONG_LYRICS, QuoteType.TRADEMARK]:
            return False, None

        # 短引用通常是合理使用
        if word_count < 50:
            category = FairUseCategory.COMMENT
            if context:
                if "评论" in context or "分析" in context:
                    category = FairUseCategory.CRITICISM
                elif "新闻" in context or "报道" in context:
                    category = FairUseCategory.NEWS_REPORTING
                elif "教学" in context or "学习" in context:
                    category = FairUseCategory.TEACHING

            return True, category

        # 长引用需要更谨慎
        return word_count < 100, FairUseCategory.UNCLEAR

    def _assess_risk(
        self,
        quote_type: QuoteType,
        word_count: int,
        is_attributed: bool,
        fair_use_likely: bool
    ) -> str:
        """评估风险级别"""
        # 高风险情况
        if quote_type == QuoteType.SONG_LYRICS and word_count > 20:
            return "high"
        if quote_type == QuoteType.TRADEMARK:
            return "high"
        if word_count > 200 and not fair_use_likely:
            return "high"

        # 中等风险
        if word_count > 100 and not is_attributed:
            return "medium"
        if quote_type == QuoteType.SONG_LYRICS:
            return "medium"
        if not fair_use_likely:
            return "medium"

        return "low"

    def _generate_quote_recommendations(
        self,
        quote_type: QuoteType,
        source: Optional[str],
        author: Optional[str],
        word_count: int,
        risk_level: str
    ) -> List[str]:
        """生成单个引用的建议"""
        recommendations = []

        if risk_level == "high":
            if quote_type == QuoteType.SONG_LYRICS:
                recommendations.append("🔴 歌词引用需要获得版权许可")
            elif quote_type == QuoteType.TRADEMARK:
                recommendations.append("🔴 商标使用需要谨慎，避免暗示品牌背书")
            else:
                recommendations.append("🔴 引用较长，建议缩短或获取授权")

        if not source and not author:
            recommendations.append("🟡 建议添加引用来源和作者")

        if word_count > 50:
            recommendations.append("💡 考虑使用间接引语或总结替代直接引用")

        return recommendations

    def _generate_overall_recommendations(
        self,
        quotes: List[Quote],
        quoted_percentage: float,
        overall_risk: str
    ) -> List[str]:
        """生成整体建议"""
        recommendations = []

        if overall_risk == "high":
            recommendations.append("⚠️ 存在高风险引用，请在发布前处理")

        if quoted_percentage > 20:
            recommendations.append(f"📊 引用内容占比{quoted_percentage:.1f}%，建议降低")

        # 检查未归属的引用
        unattributed = [q for q in quotes if not q.is_attributed]
        if unattributed:
            recommendations.append(f"📝 {len(unattributed)}处引用未注明来源")

        # 通用建议
        recommendations.append("✅ 确保所有引用都符合合理使用原则")
        recommendations.append("💡 在节目简介中列出主要引用来源")

        return recommendations
