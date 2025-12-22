"""
社交媒体格式化器
为不同平台优化内容格式和文案
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re


class Platform(Enum):
    """社交媒体平台"""
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    WECHAT = "wechat"
    WEIBO = "weibo"
    DOUYIN = "douyin"
    XIAOHONGSHU = "xiaohongshu"
    BILIBILI = "bilibili"
    ZHIHU = "zhihu"


@dataclass
class PlatformConfig:
    """平台配置"""
    max_title_length: int
    max_description_length: int
    max_hashtags: int
    supports_links: bool
    supports_mentions: bool
    video_formats: List[str]
    optimal_posting_times: List[int]  # 小时
    engagement_features: List[str]


@dataclass
class FormattedContent:
    """格式化后的内容"""
    platform: Platform
    title: str
    description: str
    hashtags: List[str]
    mentions: List[str]
    call_to_action: str
    link: Optional[str]
    thumbnail_text: str
    scheduling_suggestion: Dict[str, Any]
    engagement_tips: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SocialMediaFormatter:
    """社交媒体格式化器"""

    # 各平台配置
    PLATFORM_CONFIGS = {
        Platform.TIKTOK: PlatformConfig(
            max_title_length=150,
            max_description_length=2200,
            max_hashtags=5,
            supports_links=False,
            supports_mentions=True,
            video_formats=["vertical_9_16"],
            optimal_posting_times=[7, 12, 19, 22],
            engagement_features=["duet", "stitch", "sounds"]
        ),
        Platform.INSTAGRAM: PlatformConfig(
            max_title_length=125,
            max_description_length=2200,
            max_hashtags=30,
            supports_links=False,
            supports_mentions=True,
            video_formats=["vertical_9_16", "square_1_1", "horizontal_16_9"],
            optimal_posting_times=[8, 11, 14, 19],
            engagement_features=["stories", "reels", "collab"]
        ),
        Platform.YOUTUBE: PlatformConfig(
            max_title_length=100,
            max_description_length=5000,
            max_hashtags=15,
            supports_links=True,
            supports_mentions=True,
            video_formats=["horizontal_16_9", "vertical_9_16"],
            optimal_posting_times=[14, 15, 16, 17],
            engagement_features=["cards", "end_screens", "chapters"]
        ),
        Platform.TWITTER: PlatformConfig(
            max_title_length=280,
            max_description_length=280,
            max_hashtags=3,
            supports_links=True,
            supports_mentions=True,
            video_formats=["horizontal_16_9", "square_1_1"],
            optimal_posting_times=[8, 12, 17, 21],
            engagement_features=["threads", "polls", "spaces"]
        ),
        Platform.LINKEDIN: PlatformConfig(
            max_title_length=150,
            max_description_length=3000,
            max_hashtags=5,
            supports_links=True,
            supports_mentions=True,
            video_formats=["horizontal_16_9", "square_1_1"],
            optimal_posting_times=[7, 8, 12, 17],
            engagement_features=["articles", "documents", "polls"]
        ),
        Platform.WECHAT: PlatformConfig(
            max_title_length=64,
            max_description_length=500,
            max_hashtags=3,
            supports_links=True,
            supports_mentions=False,
            video_formats=["vertical_9_16"],
            optimal_posting_times=[7, 12, 18, 21],
            engagement_features=["moments", "channels", "mini_programs"]
        ),
        Platform.DOUYIN: PlatformConfig(
            max_title_length=55,
            max_description_length=1000,
            max_hashtags=5,
            supports_links=False,
            supports_mentions=True,
            video_formats=["vertical_9_16"],
            optimal_posting_times=[12, 18, 21, 22],
            engagement_features=["duet", "challenges", "live"]
        ),
        Platform.XIAOHONGSHU: PlatformConfig(
            max_title_length=20,
            max_description_length=1000,
            max_hashtags=10,
            supports_links=False,
            supports_mentions=True,
            video_formats=["vertical_3_4", "square_1_1"],
            optimal_posting_times=[7, 12, 18, 22],
            engagement_features=["notes", "collections", "topics"]
        ),
        Platform.BILIBILI: PlatformConfig(
            max_title_length=80,
            max_description_length=2000,
            max_hashtags=5,
            supports_links=True,
            supports_mentions=True,
            video_formats=["horizontal_16_9"],
            optimal_posting_times=[17, 18, 19, 20],
            engagement_features=["danmaku", "collections", "dynamics"]
        ),
        Platform.ZHIHU: PlatformConfig(
            max_title_length=50,
            max_description_length=10000,
            max_hashtags=5,
            supports_links=True,
            supports_mentions=True,
            video_formats=["horizontal_16_9"],
            optimal_posting_times=[9, 12, 21, 22],
            engagement_features=["answers", "columns", "ideas"]
        )
    }

    def __init__(self):
        self.hashtag_database = self._load_hashtag_database()
        self.cta_templates = self._load_cta_templates()

    def _load_hashtag_database(self) -> Dict[str, List[str]]:
        """加载标签数据库"""
        return {
            "podcast": ["#播客", "#Podcast", "#播客推荐", "#音频", "#听播客"],
            "tech": ["#科技", "#AI", "#人工智能", "#技术", "#数字化"],
            "business": ["#商业", "#创业", "#职场", "#管理", "#营销"],
            "lifestyle": ["#生活", "#成长", "#自我提升", "#生活方式", "#日常"],
            "education": ["#学习", "#知识", "#教育", "#干货", "#涨知识"],
            "entertainment": ["#娱乐", "#有趣", "#搞笑", "#趣味", "#段子"],
            "motivation": ["#励志", "#正能量", "#鸡汤", "#加油", "#努力"],
            "health": ["#健康", "#养生", "#健身", "#心理", "#身心健康"]
        }

    def _load_cta_templates(self) -> Dict[Platform, List[str]]:
        """加载行动号召模板"""
        return {
            Platform.TIKTOK: [
                "关注我获取更多精彩内容！",
                "点赞+收藏，下次更容易找到！",
                "你怎么看？评论区聊聊～",
                "分享给需要的朋友！"
            ],
            Platform.INSTAGRAM: [
                "保存这条帖子，以后会用到！",
                "双击❤️如果你同意！",
                "在评论区分享你的想法～",
                "标记一个需要看这个的朋友！"
            ],
            Platform.YOUTUBE: [
                "觉得有帮助就点个赞👍订阅支持一下！",
                "点击订阅，打开小铃铛🔔不错过更新！",
                "有问题欢迎在评论区留言！",
                "喜欢就分享给朋友吧！"
            ],
            Platform.TWITTER: [
                "转发让更多人看到！",
                "有同感请点赞❤️",
                "你的看法是什么？",
                "关注获取更多内容"
            ],
            Platform.LINKEDIN: [
                "如果这对你有启发，请点赞分享给你的network",
                "欢迎在评论区分享你的观点",
                "关注我获取更多行业洞察",
                "转发给可能需要的同事"
            ],
            Platform.WECHAT: [
                "觉得有用就点个在看吧～",
                "分享给需要的朋友",
                "关注公众号获取更多内容",
                "欢迎留言交流"
            ],
            Platform.DOUYIN: [
                "关注我，带你了解更多！",
                "双击❤️不迷路！",
                "评论区见～",
                "转发给你的朋友！"
            ],
            Platform.XIAOHONGSHU: [
                "记得点赞收藏哦～",
                "有问题评论区问我！",
                "关注我，持续分享干货！",
                "分享给需要的姐妹～"
            ],
            Platform.BILIBILI: [
                "一键三连支持一下UP主！",
                "关注不迷路，更新不错过！",
                "有什么想法弹幕告诉我～",
                "觉得有用就收藏转发吧！"
            ],
            Platform.ZHIHU: [
                "觉得有帮助就点个赞同吧",
                "关注我获取更多优质回答",
                "欢迎在评论区讨论",
                "收藏这个回答以后用得上"
            ]
        }

    def format_for_platform(
        self,
        content: Dict[str, Any],
        platform: Platform,
        podcast_info: Optional[Dict[str, Any]] = None
    ) -> FormattedContent:
        """
        为特定平台格式化内容

        Args:
            content: 原始内容
            platform: 目标平台
            podcast_info: 播客信息

        Returns:
            格式化后的内容
        """
        config = self.PLATFORM_CONFIGS.get(platform)
        if not config:
            raise ValueError(f"Unsupported platform: {platform}")

        # 生成标题
        title = self._generate_title(content, platform, config)

        # 生成描述
        description = self._generate_description(content, platform, config)

        # 生成标签
        hashtags = self._generate_hashtags(content, platform, config)

        # 生成提及
        mentions = self._generate_mentions(content, platform, config)

        # 选择行动号召
        cta = self._select_cta(platform, content)

        # 生成缩略图文字
        thumbnail_text = self._generate_thumbnail_text(content, platform)

        # 生成发布建议
        scheduling = self._generate_scheduling_suggestion(platform, config)

        # 生成互动技巧
        engagement_tips = self._generate_engagement_tips(platform, config)

        # 处理链接
        link = content.get("link") if config.supports_links else None

        return FormattedContent(
            platform=platform,
            title=title,
            description=description,
            hashtags=hashtags,
            mentions=mentions,
            call_to_action=cta,
            link=link,
            thumbnail_text=thumbnail_text,
            scheduling_suggestion=scheduling,
            engagement_tips=engagement_tips,
            metadata={
                "content_type": content.get("type", "clip"),
                "podcast_name": podcast_info.get("name") if podcast_info else None,
                "generated_at": datetime.now().isoformat()
            }
        )

    def _generate_title(
        self,
        content: Dict[str, Any],
        platform: Platform,
        config: PlatformConfig
    ) -> str:
        """生成标题"""
        original_title = content.get("title", "精彩片段")

        # 根据平台特点调整标题风格
        if platform in [Platform.TIKTOK, Platform.DOUYIN]:
            # 短视频平台：使用钩子开头
            hooks = ["震惊！", "原来", "这个", "必看！", "绝了！"]
            title = f"{hooks[hash(original_title) % len(hooks)]} {original_title}"
        elif platform == Platform.XIAOHONGSHU:
            # 小红书：使用emoji和感叹
            title = f"📌 {original_title}！"
        elif platform == Platform.LINKEDIN:
            # LinkedIn：专业语调
            title = original_title.replace("！", "").replace("~", "")
        else:
            title = original_title

        # 截断到最大长度
        if len(title) > config.max_title_length:
            title = title[:config.max_title_length - 3] + "..."

        return title

    def _generate_description(
        self,
        content: Dict[str, Any],
        platform: Platform,
        config: PlatformConfig
    ) -> str:
        """生成描述"""
        original_desc = content.get("description", "")
        transcript = content.get("transcript", "")

        # 构建描述
        parts = []

        # 添加引导语
        if platform == Platform.YOUTUBE:
            parts.append("📺 视频简介：")
        elif platform == Platform.XIAOHONGSHU:
            parts.append("💡 ")

        # 添加主要内容
        if original_desc:
            parts.append(original_desc)
        elif transcript:
            # 使用转录文本的前几句
            sentences = transcript.split("。")[:3]
            parts.append("。".join(sentences) + "。")

        # 添加分隔线和标签区域
        if platform == Platform.INSTAGRAM:
            parts.append("\n.\n.\n.\n")  # Instagram风格的分隔

        description = "\n".join(parts)

        # 截断到最大长度
        if len(description) > config.max_description_length:
            description = description[:config.max_description_length - 3] + "..."

        return description

    def _generate_hashtags(
        self,
        content: Dict[str, Any],
        platform: Platform,
        config: PlatformConfig
    ) -> List[str]:
        """生成标签"""
        tags = set()

        # 添加播客相关标签
        tags.update(self.hashtag_database.get("podcast", [])[:2])

        # 根据内容主题添加标签
        topics = content.get("topics", [])
        for topic in topics:
            if topic.lower() in self.hashtag_database:
                tags.update(self.hashtag_database[topic.lower()][:2])

        # 添加平台特定标签
        if platform == Platform.TIKTOK:
            tags.add("#fyp")
            tags.add("#foryou")
        elif platform == Platform.INSTAGRAM:
            tags.add("#instagood")
            tags.add("#explore")
        elif platform == Platform.YOUTUBE:
            tags.add("#Shorts")
        elif platform == Platform.BILIBILI:
            tags.add("#B站")

        # 限制标签数量
        return list(tags)[:config.max_hashtags]

    def _generate_mentions(
        self,
        content: Dict[str, Any],
        platform: Platform,
        config: PlatformConfig
    ) -> List[str]:
        """生成提及"""
        if not config.supports_mentions:
            return []

        mentions = []

        # 添加嘉宾提及
        guests = content.get("guests", [])
        for guest in guests:
            if guest.get("handle"):
                mentions.append(f"@{guest['handle']}")

        return mentions[:5]  # 最多5个提及

    def _select_cta(self, platform: Platform, content: Dict[str, Any]) -> str:
        """选择行动号召"""
        ctas = self.cta_templates.get(platform, ["感谢观看！"])

        # 根据内容类型选择合适的CTA
        content_type = content.get("type", "general")

        if content_type == "educational":
            # 教育类内容：强调收藏
            ctas = [c for c in ctas if "收藏" in c or "保存" in c or "save" in c.lower()] or ctas
        elif content_type == "controversial":
            # 争议类内容：鼓励讨论
            ctas = [c for c in ctas if "评论" in c or "看法" in c or "comment" in c.lower()] or ctas

        return ctas[hash(str(content)) % len(ctas)]

    def _generate_thumbnail_text(self, content: Dict[str, Any], platform: Platform) -> str:
        """生成缩略图文字"""
        title = content.get("title", "")

        # 缩略图文字要短而有冲击力
        if len(title) > 20:
            # 提取关键词
            words = title.split()[:4]
            return " ".join(words)

        return title

    def _generate_scheduling_suggestion(
        self,
        platform: Platform,
        config: PlatformConfig
    ) -> Dict[str, Any]:
        """生成发布时间建议"""
        optimal_hours = config.optimal_posting_times

        # 获取当前时间
        now = datetime.now()

        # 找到下一个最佳发布时间
        suggested_times = []
        for hour in optimal_hours:
            suggested_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if suggested_time <= now:
                # 如果今天的这个时间已过，推到明天
                suggested_time = suggested_time.replace(day=now.day + 1)
            suggested_times.append(suggested_time)

        suggested_times.sort()

        return {
            "optimal_hours": optimal_hours,
            "suggested_time": suggested_times[0].isoformat() if suggested_times else None,
            "timezone": "Asia/Shanghai",
            "best_days": ["周二", "周三", "周四"],  # 通常工作日表现更好
            "avoid": ["周末早上", "深夜"],
            "notes": f"建议在 {optimal_hours[0]}:00-{optimal_hours[-1]}:00 之间发布"
        }

    def _generate_engagement_tips(
        self,
        platform: Platform,
        config: PlatformConfig
    ) -> List[str]:
        """生成互动技巧"""
        tips = []

        # 通用技巧
        tips.append("发布后1小时内积极回复评论")
        tips.append("在描述中提出问题以鼓励互动")

        # 平台特定技巧
        features = config.engagement_features

        if "duet" in features:
            tips.append("开启合拍功能，鼓励用户创作")
        if "stories" in features:
            tips.append("同步发布Story增加曝光")
        if "chapters" in features:
            tips.append("添加视频章节提升用户体验")
        if "danmaku" in features:
            tips.append("鼓励用户发送弹幕互动")
        if "polls" in features:
            tips.append("使用投票功能增加互动")

        return tips[:5]

    def format_for_all_platforms(
        self,
        content: Dict[str, Any],
        platforms: Optional[List[Platform]] = None
    ) -> Dict[Platform, FormattedContent]:
        """为所有平台格式化内容"""
        if platforms is None:
            platforms = list(Platform)

        results = {}
        for platform in platforms:
            try:
                results[platform] = self.format_for_platform(content, platform)
            except Exception as e:
                print(f"Failed to format for {platform}: {e}")

        return results

    def generate_cross_post_strategy(
        self,
        content: Dict[str, Any],
        primary_platform: Platform,
        secondary_platforms: List[Platform]
    ) -> Dict[str, Any]:
        """
        生成跨平台发布策略

        Args:
            content: 内容
            primary_platform: 主要平台
            secondary_platforms: 次要平台

        Returns:
            发布策略
        """
        primary_content = self.format_for_platform(content, primary_platform)

        strategy = {
            "primary": {
                "platform": primary_platform.value,
                "content": primary_content,
                "timing": "首发",
                "priority": "high"
            },
            "secondary": [],
            "timeline": [],
            "notes": []
        }

        # 为次要平台生成发布计划
        for i, platform in enumerate(secondary_platforms):
            formatted = self.format_for_platform(content, platform)

            # 错开发布时间
            delay_hours = (i + 1) * 2

            strategy["secondary"].append({
                "platform": platform.value,
                "content": formatted,
                "delay_hours": delay_hours,
                "priority": "medium"
            })

            strategy["timeline"].append({
                "time": f"+{delay_hours}小时",
                "action": f"发布到 {platform.value}"
            })

        # 添加策略建议
        strategy["notes"] = [
            "首发平台发布后等待互动数据再发布其他平台",
            "根据各平台反馈调整后续内容",
            "注意各平台的最佳发布时间可能不同"
        ]

        return strategy
