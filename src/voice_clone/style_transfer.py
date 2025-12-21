"""
风格迁移模块

将播客内容转换为不同风格
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..utils import get_logger

logger = get_logger(__name__)


class PodcastStyle(str, Enum):
    """播客风格"""
    FORMAL = "formal"  # 正式
    CASUAL = "casual"  # 轻松
    HUMOROUS = "humorous"  # 幽默
    STORYTELLING = "storytelling"  # 叙事
    EDUCATIONAL = "educational"  # 教育
    NEWS = "news"  # 新闻
    INTERVIEW = "interview"  # 访谈
    DEBATE = "debate"  # 辩论


@dataclass
class StyleProfile:
    """风格档案"""
    style: PodcastStyle
    tone: str
    vocabulary_level: str
    sentence_structure: str
    emotional_range: str
    pacing: str
    examples: List[str]


class StyleTransfer:
    """
    风格迁移器

    功能：
    - 分析原始风格
    - 转换为目标风格
    - 保持核心内容不变
    """

    STYLE_PROFILES = {
        PodcastStyle.FORMAL: StyleProfile(
            style=PodcastStyle.FORMAL,
            tone="专业、严谨、权威",
            vocabulary_level="高级词汇，专业术语",
            sentence_structure="复杂句式，逻辑严密",
            emotional_range="克制、客观",
            pacing="中速，有节奏",
            examples=["根据研究表明...", "从专业角度来看...", "值得注意的是..."],
        ),
        PodcastStyle.CASUAL: StyleProfile(
            style=PodcastStyle.CASUAL,
            tone="轻松、亲切、随意",
            vocabulary_level="日常用语，口语化",
            sentence_structure="简短句式，自然流畅",
            emotional_range="自然、活泼",
            pacing="快慢结合，自然",
            examples=["你懂的...", "说实话...", "我觉得吧..."],
        ),
        PodcastStyle.HUMOROUS: StyleProfile(
            style=PodcastStyle.HUMOROUS,
            tone="幽默、诙谐、有趣",
            vocabulary_level="生动用语，俏皮话",
            sentence_structure="灵活多变，出人意料",
            emotional_range="欢快、调侃",
            pacing="节奏感强，有包袱",
            examples=["笑死我了...", "这波操作...", "绝绝子..."],
        ),
        PodcastStyle.STORYTELLING: StyleProfile(
            style=PodcastStyle.STORYTELLING,
            tone="生动、引人入胜、情感丰富",
            vocabulary_level="描述性词汇，感官用语",
            sentence_structure="叙事结构，起承转合",
            emotional_range="丰富、感染力强",
            pacing="有张有弛，戏剧性",
            examples=["那是一个...", "想象一下...", "就在那一刻..."],
        ),
        PodcastStyle.EDUCATIONAL: StyleProfile(
            style=PodcastStyle.EDUCATIONAL,
            tone="清晰、有条理、启发性",
            vocabulary_level="适当解释专业术语",
            sentence_structure="层次分明，由浅入深",
            emotional_range="耐心、鼓励",
            pacing="稳定，留有思考时间",
            examples=["首先我们来看...", "简单来说...", "举个例子..."],
        ),
        PodcastStyle.NEWS: StyleProfile(
            style=PodcastStyle.NEWS,
            tone="客观、简洁、及时",
            vocabulary_level="新闻用语，精确",
            sentence_structure="倒金字塔，重点在前",
            emotional_range="中立、克制",
            pacing="快速、紧凑",
            examples=["据报道...", "本台消息...", "最新进展..."],
        ),
    }

    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider

    async def analyze_style(self, content: str) -> Dict[str, Any]:
        """
        分析内容风格

        Args:
            content: 原始内容

        Returns:
            风格分析结果
        """
        prompt = f"""分析以下播客内容的风格特征：

内容：
{content[:3000]}

请分析：
1. 整体语气（正式/轻松/幽默等）
2. 词汇水平（日常/专业/学术等）
3. 句式特点
4. 情感表达方式
5. 节奏感
6. 最接近的风格类型

以 JSON 格式返回。"""

        response = await self._call_llm(prompt)

        try:
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {"raw_analysis": response}

    async def transfer_style(
        self,
        content: str,
        target_style: PodcastStyle,
        preserve_facts: bool = True,
    ) -> str:
        """
        转换内容风格

        Args:
            content: 原始内容
            target_style: 目标风格
            preserve_facts: 是否保持事实不变

        Returns:
            转换后的内容
        """
        style_profile = self.STYLE_PROFILES.get(target_style)
        if not style_profile:
            raise ValueError(f"不支持的风格: {target_style}")

        prompt = f"""将以下播客内容转换为「{target_style.value}」风格：

原始内容：
{content}

目标风格特征：
- 语气：{style_profile.tone}
- 词汇：{style_profile.vocabulary_level}
- 句式：{style_profile.sentence_structure}
- 情感：{style_profile.emotional_range}
- 节奏：{style_profile.pacing}

参考表达：{', '.join(style_profile.examples)}

要求：
1. {"保持所有事实信息准确" if preserve_facts else "可以适当夸张或简化"}
2. 完全使用目标风格的表达方式
3. 保持内容的完整性
4. 使转换自然流畅

请直接输出转换后的内容。"""

        return await self._call_llm(prompt)

    async def make_casual(self, content: str) -> str:
        """转为轻松风格"""
        return await self.transfer_style(content, PodcastStyle.CASUAL)

    async def make_humorous(self, content: str) -> str:
        """转为幽默风格"""
        return await self.transfer_style(content, PodcastStyle.HUMOROUS)

    async def make_formal(self, content: str) -> str:
        """转为正式风格"""
        return await self.transfer_style(content, PodcastStyle.FORMAL)

    async def make_storytelling(self, content: str) -> str:
        """转为叙事风格"""
        return await self.transfer_style(content, PodcastStyle.STORYTELLING)

    async def adapt_for_audience(
        self,
        content: str,
        audience: str,
    ) -> str:
        """
        为特定受众调整内容

        Args:
            content: 原始内容
            audience: 目标受众（如：儿童、专业人士、老年人等）

        Returns:
            调整后的内容
        """
        prompt = f"""将以下内容调整为适合「{audience}」的版本：

原始内容：
{content}

要求：
1. 使用适合该受众的语言水平
2. 调整内容深度和复杂度
3. 选择合适的例子和类比
4. 保持核心信息完整

请直接输出调整后的内容。"""

        return await self._call_llm(prompt)

    async def generate_multiple_versions(
        self,
        content: str,
        styles: List[PodcastStyle] = None,
    ) -> Dict[PodcastStyle, str]:
        """
        生成多个风格版本

        Args:
            content: 原始内容
            styles: 目标风格列表

        Returns:
            {风格: 转换后内容}
        """
        if styles is None:
            styles = [PodcastStyle.CASUAL, PodcastStyle.HUMOROUS, PodcastStyle.STORYTELLING]

        results = {}
        for style in styles:
            try:
                results[style] = await self.transfer_style(content, style)
            except Exception as e:
                logger.error(f"风格转换失败 [{style}]: {e}")
                results[style] = content

        return results

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        try:
            if self.llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "你是一位专业的内容风格转换专家。"},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=2000,
                )
                return response.choices[0].message.content
            else:
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic()
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
