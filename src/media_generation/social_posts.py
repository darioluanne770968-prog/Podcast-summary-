"""
社交媒体帖子生成模块

为不同平台生成优化的社交媒体帖子
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from ..analysis import LLMClient
from ..utils import get_logger

logger = get_logger(__name__)


class SocialPlatform(str, Enum):
    """社交平台"""
    TWITTER = "twitter"
    WEIBO = "weibo"
    XIAOHONGSHU = "xiaohongshu"
    LINKEDIN = "linkedin"
    THREADS = "threads"
    INSTAGRAM = "instagram"


@dataclass
class SocialPost:
    """社交媒体帖子"""
    platform: SocialPlatform
    content: str
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    emoji_count: int = 0
    character_count: int = 0
    thread: List[str] = field(default_factory=list)  # 用于 Twitter thread

    def __post_init__(self):
        self.character_count = len(self.content)

    def to_dict(self) -> dict:
        return {
            "platform": self.platform.value,
            "content": self.content,
            "hashtags": self.hashtags,
            "mentions": self.mentions,
            "character_count": self.character_count,
            "thread": self.thread,
        }

    def get_full_post(self) -> str:
        """获取完整帖子（包含 hashtag）"""
        hashtag_str = " ".join(f"#{tag}" for tag in self.hashtags)
        return f"{self.content}\n\n{hashtag_str}".strip()


class SocialPostGenerator:
    """社交帖子生成器"""

    PLATFORM_LIMITS = {
        SocialPlatform.TWITTER: 280,
        SocialPlatform.WEIBO: 2000,
        SocialPlatform.XIAOHONGSHU: 1000,
        SocialPlatform.LINKEDIN: 3000,
        SocialPlatform.THREADS: 500,
        SocialPlatform.INSTAGRAM: 2200,
    }

    PLATFORM_STYLES = {
        SocialPlatform.TWITTER: "简洁有力，善用 emoji，适合引发讨论",
        SocialPlatform.WEIBO: "轻松活泼，可以长一些，适当使用 emoji",
        SocialPlatform.XIAOHONGSHU: "种草风格，使用大量 emoji，分段清晰，标题党",
        SocialPlatform.LINKEDIN: "专业正式，突出价值和洞察",
        SocialPlatform.THREADS: "对话式，个人化，引发讨论",
        SocialPlatform.INSTAGRAM: "视觉导向，故事性强，使用 emoji",
    }

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def generate(
        self,
        podcast_title: str,
        summary: str,
        quotes: List[str] = None,
        keywords: List[str] = None,
        platforms: List[SocialPlatform] = None,
    ) -> List[SocialPost]:
        """
        生成多平台社交帖子

        Args:
            podcast_title: 播客标题
            summary: 内容摘要
            quotes: 金句列表
            keywords: 关键词列表
            platforms: 目标平台列表

        Returns:
            SocialPost 列表
        """
        platforms = platforms or list(SocialPlatform)
        posts = []

        for platform in platforms:
            post = self._generate_for_platform(
                platform, podcast_title, summary, quotes, keywords
            )
            if post:
                posts.append(post)

        return posts

    def _generate_for_platform(
        self,
        platform: SocialPlatform,
        title: str,
        summary: str,
        quotes: List[str],
        keywords: List[str],
    ) -> Optional[SocialPost]:
        """为特定平台生成帖子"""
        char_limit = self.PLATFORM_LIMITS.get(platform, 500)
        style = self.PLATFORM_STYLES.get(platform, "")

        prompt = f"""为以下播客内容生成一条 {platform.value} 帖子。

播客标题: {title}
内容摘要: {summary}
金句: {', '.join(quotes[:3]) if quotes else '无'}
关键词: {', '.join(keywords[:5]) if keywords else '无'}

要求:
1. 字数限制: {char_limit} 字以内
2. 风格: {style}
3. 包含相关 hashtag
4. 吸引用户点击/互动

请按以下 JSON 格式输出:

```json
{{
  "content": "帖子正文",
  "hashtags": ["标签1", "标签2"],
  "hook": "开头吸引人的第一句话"
}}
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, temperature=0.7)
            data = self.llm.parse_json_response(response)

            return SocialPost(
                platform=platform,
                content=data.get("content", "")[:char_limit],
                hashtags=data.get("hashtags", []),
            )

        except Exception as e:
            logger.error(f"生成 {platform.value} 帖子失败: {e}")
            return None

    def generate_twitter_thread(
        self,
        podcast_title: str,
        summary: str,
        key_points: List[str],
        max_tweets: int = 10,
    ) -> SocialPost:
        """
        生成 Twitter 话题串

        Args:
            podcast_title: 播客标题
            summary: 内容摘要
            key_points: 核心要点
            max_tweets: 最大推文数

        Returns:
            包含 thread 的 SocialPost
        """
        prompt = f"""将以下播客内容转换为 Twitter 话题串（thread）。

标题: {podcast_title}
摘要: {summary}
要点: {chr(10).join(f'- {p}' for p in key_points)}

要求:
1. 每条推文不超过 280 字符
2. 最多 {max_tweets} 条推文
3. 第一条要有吸引力，引发好奇
4. 最后一条要有 call to action
5. 使用数字标注（1/, 2/, ...）

请按以下 JSON 格式输出:

```json
{{
  "thread": ["推文1", "推文2", "..."],
  "hashtags": ["标签1", "标签2"]
}}
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, temperature=0.6)
            data = self.llm.parse_json_response(response)

            return SocialPost(
                platform=SocialPlatform.TWITTER,
                content=data.get("thread", [""])[0],
                hashtags=data.get("hashtags", []),
                thread=data.get("thread", []),
            )

        except Exception as e:
            logger.error(f"生成 Twitter thread 失败: {e}")
            return SocialPost(
                platform=SocialPlatform.TWITTER,
                content=f"🎙️ {podcast_title}\n\n{summary[:200]}...",
            )

    def generate_xiaohongshu_post(
        self,
        podcast_title: str,
        summary: str,
        quotes: List[str] = None,
    ) -> SocialPost:
        """
        生成小红书风格帖子

        Args:
            podcast_title: 播客标题
            summary: 内容摘要
            quotes: 金句列表

        Returns:
            小红书风格的 SocialPost
        """
        prompt = f"""将以下播客内容转换为小红书风格的帖子。

标题: {podcast_title}
摘要: {summary}
金句: {chr(10).join(quotes[:3]) if quotes else '无'}

要求:
1. 标题要吸引人（可以用夸张表达）
2. 开头要有 emoji 和吸引人的话
3. 正文分成多个小段落
4. 每段开头用 emoji
5. 结尾要有互动引导
6. 整体风格：活泼、实用、有干货感

请按以下 JSON 格式输出:

```json
{{
  "title": "帖子标题（20字以内）",
  "content": "完整帖子内容",
  "hashtags": ["标签1", "标签2"]
}}
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, temperature=0.8)
            data = self.llm.parse_json_response(response)

            title = data.get("title", podcast_title)
            content = data.get("content", summary)

            # 小红书格式：标题 + 正文
            full_content = f"{title}\n\n{content}"

            return SocialPost(
                platform=SocialPlatform.XIAOHONGSHU,
                content=full_content,
                hashtags=data.get("hashtags", []),
            )

        except Exception as e:
            logger.error(f"生成小红书帖子失败: {e}")
            return SocialPost(
                platform=SocialPlatform.XIAOHONGSHU,
                content=f"📻 {podcast_title}\n\n{summary}",
            )

    def format_posts_for_export(self, posts: List[SocialPost]) -> str:
        """格式化帖子用于导出"""
        lines = ["# 📱 社交媒体帖子\n"]

        for post in posts:
            platform_emoji = {
                SocialPlatform.TWITTER: "🐦",
                SocialPlatform.WEIBO: "🔴",
                SocialPlatform.XIAOHONGSHU: "📕",
                SocialPlatform.LINKEDIN: "💼",
                SocialPlatform.THREADS: "🧵",
                SocialPlatform.INSTAGRAM: "📸",
            }

            emoji = platform_emoji.get(post.platform, "📱")
            lines.append(f"## {emoji} {post.platform.value.title()}\n")
            lines.append(f"```\n{post.get_full_post()}\n```\n")

            if post.thread:
                lines.append("### Thread:\n")
                for i, tweet in enumerate(post.thread, 1):
                    lines.append(f"{i}. {tweet}\n")

            lines.append(f"*字数: {post.character_count}*\n")
            lines.append("---\n")

        return "\n".join(lines)
