"""
Whisper 语音转文字引擎

支持 faster-whisper 和 openai-whisper
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Literal, Iterator
import time

from ..config import get_settings
from ..utils import get_logger, format_timestamp

logger = get_logger(__name__)


@dataclass
class Segment:
    """转录片段"""
    id: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    confidence: Optional[float] = None

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def start_formatted(self) -> str:
        return format_timestamp(self.start)

    @property
    def end_formatted(self) -> str:
        return format_timestamp(self.end)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "start_formatted": self.start_formatted,
            "end_formatted": self.end_formatted,
            "text": self.text,
            "speaker": self.speaker,
            "confidence": self.confidence,
        }


@dataclass
class TranscriptionResult:
    """转录结果"""
    segments: List[Segment]
    language: str
    language_probability: float
    duration: float
    processing_time: float
    model_name: str
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """获取完整文本"""
        return " ".join(seg.text.strip() for seg in self.segments)

    @property
    def full_text_with_timestamps(self) -> str:
        """获取带时间戳的完整文本"""
        lines = []
        for seg in self.segments:
            speaker = f"[{seg.speaker}] " if seg.speaker else ""
            lines.append(f"[{seg.start_formatted}] {speaker}{seg.text.strip()}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "segments": [seg.to_dict() for seg in self.segments],
            "full_text": self.full_text,
            "language": self.language,
            "language_probability": self.language_probability,
            "duration": self.duration,
            "processing_time": self.processing_time,
            "model_name": self.model_name,
            "metadata": self.metadata,
        }

    def to_srt(self) -> str:
        """导出为 SRT 字幕格式"""
        lines = []
        for seg in self.segments:
            start_srt = self._seconds_to_srt_time(seg.start)
            end_srt = self._seconds_to_srt_time(seg.end)
            lines.append(str(seg.id + 1))
            lines.append(f"{start_srt} --> {end_srt}")
            lines.append(seg.text.strip())
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """转换为 SRT 时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


class WhisperTranscriber:
    """Whisper 转录器"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        use_faster_whisper: bool = True,
    ):
        """
        初始化转录器

        Args:
            model_name: 模型名称 (tiny, base, small, medium, large-v2, large-v3)
            device: 运行设备 (cpu, cuda, auto)
            compute_type: 计算类型 (float16, int8, float32)
            use_faster_whisper: 是否使用 faster-whisper（推荐）
        """
        settings = get_settings()

        self.model_name = model_name or settings.whisper_model
        self.device = device or settings.get_whisper_device()
        self.compute_type = compute_type or settings.whisper_compute_type
        self.use_faster_whisper = use_faster_whisper

        self._model = None

    def _load_model(self):
        """懒加载模型"""
        if self._model is not None:
            return

        logger.info(f"加载 Whisper 模型: {self.model_name} (设备: {self.device})")

        if self.use_faster_whisper:
            try:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                logger.info("使用 faster-whisper 引擎")
            except ImportError:
                logger.warning("faster-whisper 未安装，回退到 openai-whisper")
                self.use_faster_whisper = False

        if not self.use_faster_whisper:
            import whisper

            self._model = whisper.load_model(self.model_name, device=self.device)
            logger.info("使用 openai-whisper 引擎")

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        task: Literal["transcribe", "translate"] = "transcribe",
        initial_prompt: Optional[str] = None,
        word_timestamps: bool = False,
        vad_filter: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> TranscriptionResult:
        """
        转录音频

        Args:
            audio_path: 音频文件路径
            language: 语言代码（如 zh, en），None 为自动检测
            task: 任务类型（transcribe 或 translate）
            initial_prompt: 初始提示（帮助模型理解上下文）
            word_timestamps: 是否获取词级别时间戳
            vad_filter: 是否使用语音活动检测过滤
            progress_callback: 进度回调函数

        Returns:
            TranscriptionResult 对象
        """
        self._load_model()

        logger.info(f"开始转录: {audio_path}")
        start_time = time.time()

        if self.use_faster_whisper:
            result = self._transcribe_faster_whisper(
                audio_path,
                language=language,
                task=task,
                initial_prompt=initial_prompt,
                word_timestamps=word_timestamps,
                vad_filter=vad_filter,
                progress_callback=progress_callback,
            )
        else:
            result = self._transcribe_openai_whisper(
                audio_path,
                language=language,
                task=task,
                initial_prompt=initial_prompt,
                word_timestamps=word_timestamps,
            )

        result.processing_time = time.time() - start_time
        logger.info(
            f"转录完成: {len(result.segments)} 段, "
            f"语言: {result.language}, "
            f"耗时: {result.processing_time:.2f}s"
        )

        return result

    def _transcribe_faster_whisper(
        self,
        audio_path: Path,
        language: Optional[str],
        task: str,
        initial_prompt: Optional[str],
        word_timestamps: bool,
        vad_filter: bool,
        progress_callback: Optional[callable],
    ) -> TranscriptionResult:
        """使用 faster-whisper 转录"""
        segments_gen, info = self._model.transcribe(
            str(audio_path),
            language=language,
            task=task,
            initial_prompt=initial_prompt,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        segments = []
        for i, seg in enumerate(segments_gen):
            segments.append(
                Segment(
                    id=i,
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    confidence=seg.avg_logprob if hasattr(seg, "avg_logprob") else None,
                )
            )

            if progress_callback:
                progress_callback(seg.end / info.duration if info.duration else 0)

        return TranscriptionResult(
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
            processing_time=0,  # 将在调用处更新
            model_name=self.model_name,
        )

    def _transcribe_openai_whisper(
        self,
        audio_path: Path,
        language: Optional[str],
        task: str,
        initial_prompt: Optional[str],
        word_timestamps: bool,
    ) -> TranscriptionResult:
        """使用 openai-whisper 转录"""
        import whisper

        result = self._model.transcribe(
            str(audio_path),
            language=language,
            task=task,
            initial_prompt=initial_prompt,
            word_timestamps=word_timestamps,
            verbose=False,
        )

        segments = []
        for i, seg in enumerate(result["segments"]):
            segments.append(
                Segment(
                    id=i,
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"],
                )
            )

        # 获取音频时长
        import whisper.audio
        audio = whisper.audio.load_audio(str(audio_path))
        duration = len(audio) / whisper.audio.SAMPLE_RATE

        return TranscriptionResult(
            segments=segments,
            language=result.get("language", "unknown"),
            language_probability=1.0,
            duration=duration,
            processing_time=0,
            model_name=self.model_name,
        )

    def transcribe_stream(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        **kwargs,
    ) -> Iterator[Segment]:
        """
        流式转录（逐段返回结果）

        Args:
            audio_path: 音频文件路径
            language: 语言代码

        Yields:
            Segment 对象
        """
        self._load_model()

        if not self.use_faster_whisper:
            raise NotImplementedError("流式转录仅支持 faster-whisper")

        segments_gen, info = self._model.transcribe(
            str(audio_path),
            language=language,
            **kwargs,
        )

        for i, seg in enumerate(segments_gen):
            yield Segment(
                id=i,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                confidence=seg.avg_logprob if hasattr(seg, "avg_logprob") else None,
            )
