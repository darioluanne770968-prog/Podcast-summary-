"""
Notion 导出模块
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from ..config import get_settings
from ..utils import get_logger
from .markdown import PodcastAnalysisResult

logger = get_logger(__name__)


class NotionExporter:
    """Notion 导出器"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        database_id: Optional[str] = None,
    ):
        """
        初始化 Notion 导出器

        Args:
            api_key: Notion API Key
            database_id: 目标数据库 ID
        """
        settings = get_settings()

        self.api_key = api_key or settings.notion_api_key
        self.database_id = database_id or settings.notion_database_id

        if not self.api_key:
            logger.warning("Notion API Key 未配置")

        self._client = None

    def _init_client(self):
        """初始化 Notion 客户端"""
        if self._client is not None:
            return

        if not self.api_key:
            raise ValueError("需要 NOTION_API_KEY")

        try:
            from notion_client import Client
            self._client = Client(auth=self.api_key)
        except ImportError:
            raise ImportError("请安装 notion-client: pip install notion-client")

    def export(
        self,
        result: PodcastAnalysisResult,
        database_id: Optional[str] = None,
    ) -> str:
        """
        导出到 Notion

        Args:
            result: 分析结果
            database_id: 目标数据库 ID（覆盖默认值）

        Returns:
            创建的页面 URL
        """
        self._init_client()

        db_id = database_id or self.database_id
        if not db_id:
            raise ValueError("需要 Notion Database ID")

        logger.info("导出到 Notion...")

        # 构建页面属性
        properties = self._build_properties(result)

        # 构建页面内容
        children = self._build_content_blocks(result)

        # 创建页面
        response = self._client.pages.create(
            parent={"database_id": db_id},
            properties=properties,
            children=children,
        )

        page_url = response.get("url", "")
        logger.info(f"Notion 页面创建成功: {page_url}")

        return page_url

    def _build_properties(self, result: PodcastAnalysisResult) -> dict:
        """构建页面属性"""
        properties = {
            "Name": {
                "title": [{"text": {"content": result.title or "Untitled"}}]
            },
        }

        # 添加常用属性（如果数据库支持）
        if result.publish_date:
            properties["Date"] = {
                "date": {"start": result.publish_date}
            }

        if result.author:
            properties["Author"] = {
                "rich_text": [{"text": {"content": result.author}}]
            }

        if result.source_url:
            properties["URL"] = {
                "url": result.source_url
            }

        if result.duration:
            properties["Duration"] = {
                "number": int(result.duration / 60)  # 转换为分钟
            }

        # 添加标签（如果有关键词）
        if result.keywords:
            tags = []
            for kw in result.keywords[:10]:  # 最多10个标签
                if hasattr(kw, "word"):
                    tags.append({"name": kw.word})
                elif isinstance(kw, str):
                    tags.append({"name": kw})
            if tags:
                properties["Tags"] = {"multi_select": tags}

        return properties

    def _build_content_blocks(self, result: PodcastAnalysisResult) -> List[dict]:
        """构建页面内容块"""
        blocks = []

        # 摘要部分
        if result.summary:
            blocks.extend(self._build_summary_blocks(result.summary))

        # 章节目录
        if result.chapters:
            blocks.extend(self._build_chapters_blocks(result.chapters))

        # 金句
        if result.quotes:
            blocks.extend(self._build_quotes_blocks(result.quotes))

        # 问答
        if result.qa_pairs:
            blocks.extend(self._build_qa_blocks(result.qa_pairs))

        return blocks

    def _build_summary_blocks(self, summary) -> List[dict]:
        """构建摘要块"""
        blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📝 内容摘要"}}]
                },
            },
        ]

        # 简短摘要
        if hasattr(summary, "brief") and summary.brief:
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"emoji": "💡"},
                    "rich_text": [{"type": "text", "text": {"content": summary.brief}}],
                },
            })

        # 详细摘要
        if hasattr(summary, "detailed") and summary.detailed:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary.detailed}}]
                },
            })

        # 核心要点
        if hasattr(summary, "key_points") and summary.key_points:
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "核心要点"}}]
                },
            })

            for point in summary.key_points:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": point}}]
                    },
                })

        return blocks

    def _build_chapters_blocks(self, chapters: List) -> List[dict]:
        """构建章节块"""
        blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📑 章节目录"}}]
                },
            },
        ]

        for chapter in chapters:
            if hasattr(chapter, "start_formatted"):
                time_str = chapter.start_formatted
                title = chapter.title
            else:
                time_str = chapter.get("start_formatted", "")
                title = chapter.get("title", "")

            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": f"[{time_str}] "},
                            "annotations": {"bold": True},
                        },
                        {"type": "text", "text": {"content": title}},
                    ]
                },
            })

        return blocks

    def _build_quotes_blocks(self, quotes: List) -> List[dict]:
        """构建金句块"""
        blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "💬 金句摘录"}}]
                },
            },
        ]

        for quote in quotes:
            if hasattr(quote, "text"):
                text = quote.text
                speaker = getattr(quote, "speaker", None)
            else:
                text = quote.get("text", "")
                speaker = quote.get("speaker")

            content = f'"{text}"'
            if speaker:
                content += f" — {speaker}"

            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                },
            })

        return blocks

    def _build_qa_blocks(self, qa_pairs: List) -> List[dict]:
        """构建问答块"""
        blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "❓ 问答复习"}}]
                },
            },
        ]

        for qa in qa_pairs:
            if hasattr(qa, "question"):
                question = qa.question
                answer = qa.answer
            else:
                question = qa.get("question", "")
                answer = qa.get("answer", "")

            # 问题
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": f"Q: {question}"},
                            "annotations": {"bold": True},
                        }
                    ],
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": f"A: {answer}"}}
                                ]
                            },
                        }
                    ],
                },
            })

        return blocks

    def check_connection(self) -> bool:
        """检查 Notion 连接"""
        try:
            self._init_client()
            # 尝试获取用户信息
            self._client.users.me()
            return True
        except Exception as e:
            logger.error(f"Notion 连接失败: {e}")
            return False
