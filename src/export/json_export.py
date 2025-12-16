"""
JSON 导出模块
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .markdown import PodcastAnalysisResult
from ..utils import get_logger, ensure_dir, sanitize_filename

logger = get_logger(__name__)


class JSONExporter:
    """JSON 导出器"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        初始化导出器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or Path("./output")
        ensure_dir(self.output_dir)

    def export(
        self,
        result: PodcastAnalysisResult,
        filename: Optional[str] = None,
        include_transcript: bool = True,
        pretty: bool = True,
    ) -> Path:
        """
        导出为 JSON 文件

        Args:
            result: 分析结果
            filename: 文件名（不含扩展名）
            include_transcript: 是否包含完整转录文本
            pretty: 是否格式化输出

        Returns:
            导出文件路径
        """
        logger.info("导出 JSON...")

        # 生成文件名
        if not filename:
            filename = sanitize_filename(result.title or "podcast_data")

        output_path = self.output_dir / f"{filename}.json"

        # 构建数据
        data = self._build_data(result, include_transcript)

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False)

        logger.info(f"JSON 导出完成: {output_path}")
        return output_path

    def _build_data(
        self,
        result: PodcastAnalysisResult,
        include_transcript: bool,
    ) -> dict:
        """构建导出数据"""
        data = {
            "meta": {
                "title": result.title,
                "source_url": result.source_url,
                "duration": result.duration,
                "publish_date": result.publish_date,
                "author": result.author,
                "generated_at": datetime.now().isoformat(),
                "tool": "Podcast Summary Tool",
            },
        }

        # 摘要
        if result.summary:
            if hasattr(result.summary, "to_dict"):
                data["summary"] = result.summary.to_dict()
            else:
                data["summary"] = result.summary

        # 章节
        if result.chapters:
            data["chapters"] = [
                c.to_dict() if hasattr(c, "to_dict") else c
                for c in result.chapters
            ]

        # 关键词
        if result.keywords:
            data["keywords"] = [
                k.to_dict() if hasattr(k, "to_dict") else k
                for k in result.keywords
            ]

        # 金句
        if result.quotes:
            data["quotes"] = [
                q.to_dict() if hasattr(q, "to_dict") else q
                for q in result.quotes
            ]

        # 情感分析
        if result.sentiment:
            if hasattr(result.sentiment, "to_dict"):
                data["sentiment"] = result.sentiment.to_dict()
            else:
                data["sentiment"] = result.sentiment

        # 问答
        if result.qa_pairs:
            data["qa_pairs"] = [
                qa.to_dict() if hasattr(qa, "to_dict") else qa
                for qa in result.qa_pairs
            ]

        # 说话人统计
        if result.speaker_stats:
            data["speaker_stats"] = result.speaker_stats

        # 转录文本
        if include_transcript:
            data["transcript"] = {
                "plain": result.transcript,
                "with_timestamps": result.transcript_with_timestamps,
            }

        # 其他元数据
        if result.metadata:
            data["metadata"] = result.metadata

        return data

    def export_transcript_only(
        self,
        result: PodcastAnalysisResult,
        filename: Optional[str] = None,
    ) -> Path:
        """
        仅导出转录文本

        Args:
            result: 分析结果
            filename: 文件名

        Returns:
            导出文件路径
        """
        if not filename:
            filename = sanitize_filename(result.title or "transcript")

        output_path = self.output_dir / f"{filename}_transcript.json"

        data = {
            "title": result.title,
            "transcript": result.transcript,
            "transcript_with_timestamps": result.transcript_with_timestamps,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path
