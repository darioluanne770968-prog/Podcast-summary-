"""
文章/博客生成模块

将播客内容转换为结构化的文章
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Literal

from ..analysis import LLMClient
from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class ArticleConfig:
    """文章配置"""
    style: str = "informative"  # informative, narrative, listicle, tutorial
    length: str = "medium"  # short (~500字), medium (~1500字), long (~3000字)
    tone: str = "professional"  # professional, casual, academic
    include_quotes: bool = True
    include_takeaways: bool = True
    seo_optimized: bool = False


class ArticleGenerator:
    """文章生成器"""

    LENGTH_TARGETS = {
        "short": 500,
        "medium": 1500,
        "long": 3000,
    }

    STYLE_DESCRIPTIONS = {
        "informative": "信息型文章，重点传递知识和信息",
        "narrative": "叙事型文章，以故事形式呈现",
        "listicle": "列表型文章，以要点清单为主",
        "tutorial": "教程型文章，步骤清晰可操作",
    }

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.output_dir = output_dir or Path("./output/articles")
        self.llm = llm_client or LLMClient()
        ensure_dir(self.output_dir)

    def generate(
        self,
        podcast_title: str,
        transcript: str,
        summary: dict = None,
        quotes: List[str] = None,
        config: ArticleConfig = None,
    ) -> str:
        """
        生成文章

        Args:
            podcast_title: 播客标题
            transcript: 转录文本
            summary: 摘要数据
            quotes: 金句列表
            config: 文章配置

        Returns:
            文章内容（Markdown 格式）
        """
        config = config or ArticleConfig()
        target_length = self.LENGTH_TARGETS.get(config.length, 1500)
        style_desc = self.STYLE_DESCRIPTIONS.get(config.style, "")

        logger.info(f"生成文章 (风格: {config.style}, 长度: {config.length})...")

        prompt = self._build_prompt(
            podcast_title, transcript, summary, quotes, config, target_length, style_desc
        )

        article = self.llm.complete(prompt, temperature=0.7, max_tokens=4000)

        # 后处理
        article = self._post_process(article, config)

        return article

    def _build_prompt(
        self,
        title: str,
        transcript: str,
        summary: dict,
        quotes: List[str],
        config: ArticleConfig,
        target_length: int,
        style_desc: str,
    ) -> str:
        """构建提示词"""
        summary_str = ""
        if summary:
            if isinstance(summary, dict):
                summary_str = f"摘要: {summary.get('brief', '')}\n要点: {summary.get('key_points', [])}"
            else:
                summary_str = f"摘要: {summary}"

        quotes_str = ""
        if quotes and config.include_quotes:
            quotes_str = f"金句:\n" + "\n".join(f"- {q}" for q in quotes[:5])

        return f"""将以下播客内容转换为一篇高质量的文章。

播客标题: {title}
{summary_str}
{quotes_str}

转录文本（节选）:
---
{transcript[:15000]}
---

文章要求:
1. 风格: {config.style} - {style_desc}
2. 目标长度: 约 {target_length} 字
3. 语调: {config.tone}
4. 格式: Markdown
5. 包含: 引言、正文（分段）、结论
{'6. SEO 优化: 包含关键词、优化标题和小标题' if config.seo_optimized else ''}

请直接输出文章内容，使用 Markdown 格式。"""

    def _post_process(self, article: str, config: ArticleConfig) -> str:
        """文章后处理"""
        # 确保有标题
        if not article.startswith("#"):
            lines = article.split("\n")
            article = f"# {lines[0]}\n\n" + "\n".join(lines[1:])

        # 添加收获（如果需要）
        if config.include_takeaways and "收获" not in article and "Takeaway" not in article:
            article += "\n\n## 💡 关键收获\n\n*待补充*"

        return article

    def generate_blog_post(
        self,
        podcast_title: str,
        transcript: str,
        summary: dict = None,
        keywords: List[str] = None,
    ) -> str:
        """
        生成 SEO 优化的博客文章

        Args:
            podcast_title: 播客标题
            transcript: 转录文本
            summary: 摘要数据
            keywords: SEO 关键词

        Returns:
            博客文章（带 frontmatter）
        """
        config = ArticleConfig(
            style="informative",
            length="long",
            seo_optimized=True,
        )

        article = self.generate(podcast_title, transcript, summary, config=config)

        # 添加 frontmatter
        frontmatter = f"""---
title: "{podcast_title}"
date: "{__import__('datetime').datetime.now().strftime('%Y-%m-%d')}"
tags: {keywords or []}
description: "{summary.get('brief', '')[:150] if summary else ''}"
---

"""
        return frontmatter + article

    def generate_newsletter(
        self,
        podcast_title: str,
        summary: dict,
        quotes: List[str] = None,
        action_items: List[str] = None,
    ) -> str:
        """
        生成 Newsletter 内容

        Args:
            podcast_title: 播客标题
            summary: 摘要数据
            quotes: 金句列表
            action_items: 行动建议

        Returns:
            Newsletter 内容
        """
        logger.info("生成 Newsletter...")

        prompt = f"""为以下播客内容生成一期 Newsletter。

播客标题: {podcast_title}
摘要: {summary}
金句: {quotes[:3] if quotes else []}
行动建议: {action_items[:5] if action_items else []}

Newsletter 要求:
1. 开头要有引人入胜的 hook
2. 简洁有力，易于快速阅读
3. 包含 1-2 个金句引用
4. 以行动建议或思考问题结尾
5. 格式友好，适合邮件阅读
6. 长度约 500-800 字

请直接输出 Newsletter 内容，使用 Markdown 格式。"""

        return self.llm.complete(prompt, temperature=0.7)

    def save_article(
        self,
        article: str,
        filename: str,
        format: str = "md",
    ) -> Path:
        """
        保存文章

        Args:
            article: 文章内容
            filename: 文件名
            format: 格式 (md, html)

        Returns:
            输出文件路径
        """
        if format == "html":
            try:
                import markdown
                content = markdown.markdown(article)
                content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #1a1a2e; }}
        blockquote {{ border-left: 4px solid #6366f1; padding-left: 16px; color: #666; }}
        code {{ background: #f4f4f5; padding: 2px 6px; border-radius: 4px; }}
    </style>
</head>
<body>
{content}
</body>
</html>"""
            except ImportError:
                format = "md"
                content = article
        else:
            content = article

        output_path = self.output_dir / f"{filename}.{format}"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"文章保存完成: {output_path}")
        return output_path
