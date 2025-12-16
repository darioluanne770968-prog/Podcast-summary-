"""
内容摘要生成模块
"""

from dataclasses import dataclass, field
from typing import Optional, List

from .llm_client import LLMClient
from ..utils import get_logger, truncate_text

logger = get_logger(__name__)


@dataclass
class Summary:
    """摘要结果"""
    brief: str  # 简短摘要（1-2句）
    detailed: str  # 详细摘要（1-2段）
    key_points: List[str]  # 核心要点
    topics: List[str]  # 主要话题
    takeaways: List[str]  # 收获/启发
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "brief": self.brief,
            "detailed": self.detailed,
            "key_points": self.key_points,
            "topics": self.topics,
            "takeaways": self.takeaways,
            "metadata": self.metadata,
        }


class PodcastSummarizer:
    """播客内容摘要生成器"""

    SYSTEM_PROMPT = """你是一个专业的播客内容分析师。你的任务是分析播客转录文本，生成高质量的内容摘要。

请确保：
1. 准确捕捉播客的核心内容和主题
2. 提取最有价值的观点和信息
3. 使用清晰、简洁的语言
4. 保持客观中立的立场
5. 如果内容是中文，请用中文回复；如果是英文，请用英文回复"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化摘要生成器

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client or LLMClient()

    def summarize(
        self,
        transcript: str,
        title: Optional[str] = None,
        max_length: int = 50000,
    ) -> Summary:
        """
        生成内容摘要

        Args:
            transcript: 转录文本
            title: 播客标题（可选）
            max_length: 最大处理文本长度

        Returns:
            Summary 对象
        """
        logger.info("生成内容摘要...")

        # 截断过长的文本
        transcript = truncate_text(transcript, max_length, suffix="\n\n[文本已截断...]")

        prompt = self._build_prompt(transcript, title)

        response = self.llm.complete(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.5,
            max_tokens=2000,
        )

        return self._parse_response(response)

    def _build_prompt(self, transcript: str, title: Optional[str]) -> str:
        """构建提示"""
        title_part = f"播客标题：{title}\n\n" if title else ""

        return f"""{title_part}以下是播客的转录文本：

---
{transcript}
---

请分析以上内容，按以下格式输出：

## 简短摘要
（用1-2句话概括播客的核心内容）

## 详细摘要
（用1-2段详细描述播客讨论的内容）

## 核心要点
（列出3-5个最重要的要点，每个要点一行）
- 要点1
- 要点2
- ...

## 主要话题
（列出播客涵盖的主要话题）
- 话题1
- 话题2
- ...

## 收获与启发
（从内容中可以获得的收获或启发）
- 启发1
- 启发2
- ..."""

    def _parse_response(self, response: str) -> Summary:
        """解析响应"""
        sections = {
            "brief": "",
            "detailed": "",
            "key_points": [],
            "topics": [],
            "takeaways": [],
        }

        current_section = None
        current_content = []

        for line in response.split("\n"):
            line = line.strip()

            # 检测章节标题
            if "简短摘要" in line or "Brief" in line.lower():
                current_section = "brief"
                current_content = []
            elif "详细摘要" in line or "Detailed" in line.lower():
                if current_section and current_content:
                    self._save_section(sections, current_section, current_content)
                current_section = "detailed"
                current_content = []
            elif "核心要点" in line or "Key Points" in line.lower():
                if current_section and current_content:
                    self._save_section(sections, current_section, current_content)
                current_section = "key_points"
                current_content = []
            elif "主要话题" in line or "Topics" in line.lower():
                if current_section and current_content:
                    self._save_section(sections, current_section, current_content)
                current_section = "topics"
                current_content = []
            elif "收获" in line or "启发" in line or "Takeaways" in line.lower():
                if current_section and current_content:
                    self._save_section(sections, current_section, current_content)
                current_section = "takeaways"
                current_content = []
            elif line and not line.startswith("#"):
                current_content.append(line)

        # 保存最后一个章节
        if current_section and current_content:
            self._save_section(sections, current_section, current_content)

        return Summary(**sections)

    def _save_section(
        self,
        sections: dict,
        section_name: str,
        content: List[str],
    ):
        """保存章节内容"""
        if section_name in ["brief", "detailed"]:
            sections[section_name] = "\n".join(content)
        else:
            # 列表类型：提取列表项
            items = []
            for line in content:
                # 移除列表标记
                line = line.lstrip("- •·*123456789.）)")
                if line:
                    items.append(line.strip())
            sections[section_name] = items

    def summarize_by_speaker(
        self,
        transcript_with_speakers: str,
    ) -> dict:
        """
        按说话人生成摘要

        Args:
            transcript_with_speakers: 带说话人标签的转录文本

        Returns:
            按说话人组织的摘要
        """
        prompt = f"""以下是带有说话人标签的播客转录文本：

---
{transcript_with_speakers}
---

请为每位说话人总结其主要观点和贡献。按以下格式输出：

对于每位说话人：
## [说话人名称]
- 主要观点1
- 主要观点2
- ...
"""

        response = self.llm.complete(
            prompt,
            system=self.SYSTEM_PROMPT,
            temperature=0.5,
        )

        return {"raw_response": response}
