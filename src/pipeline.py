"""
播客分析管道

整合所有模块，提供统一的分析流程
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any

from .config import get_settings, LLMProvider
from .utils import get_logger, setup_logging

from .audio import AudioDownloader, AudioConverter, PodcastSource
from .transcription import WhisperTranscriber, SpeakerDiarizer, TranscriptionResult
from .analysis import (
    LLMClient,
    PodcastSummarizer,
    KeywordExtractor,
    ChapterGenerator,
    QuoteExtractor,
    SentimentAnalyzer,
    QAGenerator,
)
from .export import MarkdownExporter, JSONExporter, NotionExporter, MindmapGenerator
from .export.markdown import PodcastAnalysisResult

logger = get_logger(__name__)


@dataclass
class PipelineConfig:
    """管道配置"""
    # 功能开关
    enable_transcription: bool = True
    enable_diarization: bool = False  # 说话人识别（需要 HF Token）
    enable_summary: bool = True
    enable_keywords: bool = True
    enable_chapters: bool = True
    enable_quotes: bool = True
    enable_sentiment: bool = True
    enable_qa: bool = True

    # 导出选项
    export_markdown: bool = True
    export_json: bool = False
    export_notion: bool = False
    export_mindmap: bool = False

    # LLM 配置
    llm_provider: Optional[LLMProvider] = None

    # Whisper 配置
    whisper_model: str = "large-v3"
    language: Optional[str] = None  # 自动检测

    # 输出配置
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    include_transcript: bool = False

    # 高级选项
    max_keywords: int = 20
    max_quotes: int = 10
    max_qa: int = 10
    speaker_names: Optional[Dict[str, str]] = None


class PodcastAnalyzer:
    """播客分析器"""

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        初始化分析器

        Args:
            config: 管道配置
        """
        self.config = config or PipelineConfig()
        self._init_components()

    def _init_components(self):
        """初始化组件"""
        settings = get_settings()

        # 音频处理
        self.downloader = AudioDownloader(self.config.output_dir)
        self.converter = AudioConverter(self.config.output_dir)

        # 转录
        self.transcriber = WhisperTranscriber(
            model_name=self.config.whisper_model,
        )

        # 说话人识别
        self.diarizer = SpeakerDiarizer() if self.config.enable_diarization else None

        # LLM 客户端
        llm_provider = self.config.llm_provider or settings.default_llm_provider
        self.llm = LLMClient(provider=llm_provider)

        # 分析器
        self.summarizer = PodcastSummarizer(self.llm)
        self.keyword_extractor = KeywordExtractor(self.llm)
        self.chapter_generator = ChapterGenerator(self.llm)
        self.quote_extractor = QuoteExtractor(self.llm)
        self.sentiment_analyzer = SentimentAnalyzer(self.llm)
        self.qa_generator = QAGenerator(self.llm)

        # 导出器
        self.markdown_exporter = MarkdownExporter(self.config.output_dir)
        self.json_exporter = JSONExporter(self.config.output_dir)
        self.notion_exporter = NotionExporter() if self.config.export_notion else None
        self.mindmap_generator = MindmapGenerator(self.config.output_dir)

    async def analyze(
        self,
        source: str,
        title: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> PodcastAnalysisResult:
        """
        分析播客

        Args:
            source: 音频来源（文件路径或 URL）
            title: 播客标题（可选）
            progress_callback: 进度回调 (stage, progress, message)

        Returns:
            PodcastAnalysisResult 对象
        """
        def report_progress(stage: str, progress: float, message: str):
            logger.info(f"[{stage}] {message}")
            if progress_callback:
                progress_callback(stage, progress, message)

        # 1. 获取音频
        report_progress("download", 0.0, "获取音频...")
        podcast_source = await self.downloader.download(source)
        report_progress("download", 1.0, f"音频获取完成: {podcast_source.local_path}")

        # 获取音频信息
        audio_info = self.converter.get_audio_info(podcast_source.local_path)

        # 2. 转录
        report_progress("transcription", 0.0, "开始转录...")
        transcription = self.transcriber.transcribe(
            podcast_source.local_path,
            language=self.config.language,
        )
        report_progress("transcription", 1.0, f"转录完成: {len(transcription.segments)} 段")

        # 3. 说话人识别（可选）
        speaker_stats = None
        if self.config.enable_diarization and self.diarizer:
            report_progress("diarization", 0.0, "识别说话人...")
            try:
                diarization = self.diarizer.diarize(podcast_source.local_path)
                transcription = self.diarizer.assign_speakers_to_transcription(
                    transcription, diarization, self.config.speaker_names
                )
                speaker_stats = self.diarizer.get_speaker_stats(diarization)
                report_progress("diarization", 1.0, f"说话人识别完成: {len(speaker_stats)} 位")
            except Exception as e:
                logger.warning(f"说话人识别失败: {e}")

        # 准备文本
        transcript = transcription.full_text
        transcript_with_timestamps = transcription.full_text_with_timestamps

        # 4. LLM 分析
        summary = None
        keywords = None
        chapters = None
        quotes = None
        sentiment = None
        qa_pairs = None

        if self.config.enable_summary:
            report_progress("analysis", 0.2, "生成摘要...")
            summary = self.summarizer.summarize(transcript, title=title or podcast_source.title)

        if self.config.enable_keywords:
            report_progress("analysis", 0.35, "提取关键词...")
            keywords = self.keyword_extractor.extract(transcript, self.config.max_keywords)

        if self.config.enable_chapters:
            report_progress("analysis", 0.5, "生成章节...")
            chapters = self.chapter_generator.generate(transcript_with_timestamps)

        if self.config.enable_quotes:
            report_progress("analysis", 0.65, "提取金句...")
            quotes = self.quote_extractor.extract(
                transcript_with_timestamps,
                self.config.max_quotes,
            )

        if self.config.enable_sentiment:
            report_progress("analysis", 0.8, "分析情感...")
            sentiment = self.sentiment_analyzer.analyze(transcript)

        if self.config.enable_qa:
            report_progress("analysis", 0.95, "生成问答...")
            qa_pairs = self.qa_generator.generate(transcript, self.config.max_qa)

        report_progress("analysis", 1.0, "分析完成")

        # 5. 构建结果
        result = PodcastAnalysisResult(
            title=title or podcast_source.title or "Untitled Podcast",
            source_url=podcast_source.url,
            duration=audio_info["duration_seconds"],
            publish_date=podcast_source.publish_date,
            author=podcast_source.author,
            transcript=transcript,
            transcript_with_timestamps=transcript_with_timestamps,
            summary=summary,
            chapters=chapters,
            keywords=keywords,
            quotes=quotes,
            sentiment=sentiment,
            qa_pairs=qa_pairs,
            speaker_stats=speaker_stats,
            metadata={
                "language": transcription.language,
                "processing_time": transcription.processing_time,
                "model": transcription.model_name,
                **podcast_source.metadata,
            },
        )

        # 6. 导出
        report_progress("export", 0.0, "导出结果...")
        await self._export_results(result)
        report_progress("export", 1.0, "导出完成")

        return result

    async def _export_results(self, result: PodcastAnalysisResult):
        """导出结果"""
        if self.config.export_markdown:
            self.markdown_exporter.export(
                result,
                include_transcript=self.config.include_transcript,
            )

        if self.config.export_json:
            self.json_exporter.export(result)

        if self.config.export_mindmap:
            self.mindmap_generator.generate_mermaid(result)
            self.mindmap_generator.generate_markmap(result)

        if self.config.export_notion and self.notion_exporter:
            try:
                self.notion_exporter.export(result)
            except Exception as e:
                logger.error(f"Notion 导出失败: {e}")

    def analyze_sync(
        self,
        source: str,
        title: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> PodcastAnalysisResult:
        """同步版本的分析方法"""
        return asyncio.run(self.analyze(source, title, progress_callback))


def quick_analyze(
    source: str,
    output_dir: str = "./output",
    full: bool = False,
) -> PodcastAnalysisResult:
    """
    快速分析播客

    Args:
        source: 音频来源
        output_dir: 输出目录
        full: 是否启用全部功能

    Returns:
        分析结果
    """
    config = PipelineConfig(
        output_dir=Path(output_dir),
        enable_diarization=full,
        export_markdown=True,
        export_json=full,
        export_mindmap=full,
    )

    analyzer = PodcastAnalyzer(config)
    return analyzer.analyze_sync(source)
