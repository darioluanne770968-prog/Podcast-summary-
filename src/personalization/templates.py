"""
分析模板管理模块

支持自定义分析模板和提示词
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict
import json
from datetime import datetime

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class AnalysisTemplate:
    """分析模板"""
    id: str
    name: str
    description: str

    # 功能配置
    enable_summary: bool = True
    enable_chapters: bool = True
    enable_keywords: bool = True
    enable_quotes: bool = True
    enable_sentiment: bool = False
    enable_qa: bool = True
    enable_fact_check: bool = False
    enable_entities: bool = False

    # 自定义提示词
    summary_prompt: Optional[str] = None
    chapter_prompt: Optional[str] = None
    custom_prompts: Dict[str, str] = field(default_factory=dict)

    # 输出配置
    output_sections: List[str] = field(default_factory=lambda: [
        "summary", "chapters", "keywords", "quotes", "qa"
    ])
    output_format: str = "markdown"

    # 元数据
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_public: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enable_summary": self.enable_summary,
            "enable_chapters": self.enable_chapters,
            "enable_keywords": self.enable_keywords,
            "enable_quotes": self.enable_quotes,
            "enable_sentiment": self.enable_sentiment,
            "enable_qa": self.enable_qa,
            "enable_fact_check": self.enable_fact_check,
            "enable_entities": self.enable_entities,
            "summary_prompt": self.summary_prompt,
            "chapter_prompt": self.chapter_prompt,
            "custom_prompts": self.custom_prompts,
            "output_sections": self.output_sections,
            "output_format": self.output_format,
            "author": self.author,
            "tags": self.tags,
            "is_public": self.is_public,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisTemplate":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class TemplateManager:
    """模板管理器"""

    # 内置模板
    BUILTIN_TEMPLATES = {
        "default": AnalysisTemplate(
            id="default",
            name="默认模板",
            description="标准播客分析模板",
            tags=["standard"],
        ),
        "quick": AnalysisTemplate(
            id="quick",
            name="快速摘要",
            description="只生成简要摘要和关键词",
            enable_chapters=False,
            enable_quotes=False,
            enable_qa=False,
            output_sections=["summary", "keywords"],
            tags=["quick", "brief"],
        ),
        "deep": AnalysisTemplate(
            id="deep",
            name="深度分析",
            description="全功能深度分析",
            enable_sentiment=True,
            enable_fact_check=True,
            enable_entities=True,
            output_sections=[
                "summary", "chapters", "keywords", "quotes",
                "sentiment", "entities", "qa", "fact_check"
            ],
            tags=["deep", "comprehensive"],
        ),
        "study": AnalysisTemplate(
            id="study",
            name="学习笔记",
            description="适合学习和复习的笔记模板",
            enable_qa=True,
            summary_prompt="请以学习笔记的形式总结内容，突出知识点和可操作的建议",
            output_sections=["summary", "keywords", "quotes", "qa"],
            tags=["study", "learning"],
        ),
        "content_creator": AnalysisTemplate(
            id="content_creator",
            name="内容创作者",
            description="适合内容二次创作的模板",
            enable_quotes=True,
            output_sections=["summary", "chapters", "quotes", "keywords"],
            custom_prompts={
                "hooks": "提取 5 个适合作为视频开头的精彩片段",
                "titles": "生成 10 个吸引人的标题建议",
            },
            tags=["creator", "repurpose"],
        ),
    }

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "templates"
        ensure_dir(self.storage_dir)
        self._custom_templates: Dict[str, AnalysisTemplate] = {}
        self._load_templates()

    def _load_templates(self):
        """加载自定义模板"""
        for template_file in self.storage_dir.glob("*.json"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    template = AnalysisTemplate.from_dict(data)
                    self._custom_templates[template.id] = template
            except Exception as e:
                logger.error(f"加载模板失败 [{template_file}]: {e}")

    def get_template(self, template_id: str) -> Optional[AnalysisTemplate]:
        """获取模板"""
        # 先查自定义模板
        if template_id in self._custom_templates:
            return self._custom_templates[template_id]
        # 再查内置模板
        return self.BUILTIN_TEMPLATES.get(template_id)

    def list_templates(self, include_builtin: bool = True) -> List[AnalysisTemplate]:
        """列出所有模板"""
        templates = list(self._custom_templates.values())
        if include_builtin:
            templates.extend(self.BUILTIN_TEMPLATES.values())
        return templates

    def create_template(self, template: AnalysisTemplate) -> AnalysisTemplate:
        """创建新模板"""
        template.created_at = datetime.now().isoformat()
        template.updated_at = template.created_at

        # 保存到文件
        template_file = self.storage_dir / f"{template.id}.json"
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)

        self._custom_templates[template.id] = template
        logger.info(f"创建模板: {template.name}")
        return template

    def update_template(self, template: AnalysisTemplate):
        """更新模板"""
        template.updated_at = datetime.now().isoformat()

        template_file = self.storage_dir / f"{template.id}.json"
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)

        self._custom_templates[template.id] = template
        logger.info(f"更新模板: {template.name}")

    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        if template_id in self.BUILTIN_TEMPLATES:
            logger.warning("不能删除内置模板")
            return False

        if template_id not in self._custom_templates:
            return False

        template_file = self.storage_dir / f"{template_id}.json"
        if template_file.exists():
            template_file.unlink()

        del self._custom_templates[template_id]
        logger.info(f"删除模板: {template_id}")
        return True

    def duplicate_template(
        self,
        source_id: str,
        new_id: str,
        new_name: str,
    ) -> Optional[AnalysisTemplate]:
        """复制模板"""
        source = self.get_template(source_id)
        if not source:
            return None

        new_template = AnalysisTemplate(
            id=new_id,
            name=new_name,
            description=f"基于 {source.name} 创建",
            enable_summary=source.enable_summary,
            enable_chapters=source.enable_chapters,
            enable_keywords=source.enable_keywords,
            enable_quotes=source.enable_quotes,
            enable_sentiment=source.enable_sentiment,
            enable_qa=source.enable_qa,
            enable_fact_check=source.enable_fact_check,
            enable_entities=source.enable_entities,
            summary_prompt=source.summary_prompt,
            chapter_prompt=source.chapter_prompt,
            custom_prompts=source.custom_prompts.copy(),
            output_sections=source.output_sections.copy(),
            output_format=source.output_format,
            tags=source.tags.copy(),
        )

        return self.create_template(new_template)

    def search_templates(
        self,
        query: str = None,
        tags: List[str] = None,
    ) -> List[AnalysisTemplate]:
        """搜索模板"""
        templates = self.list_templates()
        results = []

        for template in templates:
            # 关键词匹配
            if query:
                query_lower = query.lower()
                if (query_lower not in template.name.lower() and
                    query_lower not in template.description.lower()):
                    continue

            # 标签匹配
            if tags:
                if not any(tag in template.tags for tag in tags):
                    continue

            results.append(template)

        return results
