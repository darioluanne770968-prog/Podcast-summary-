"""
说话人识别（Speaker Diarization）模块

使用 pyannote.audio 进行说话人分离
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict
import time

from ..config import get_settings
from ..utils import get_logger, format_timestamp
from .whisper_engine import Segment, TranscriptionResult

logger = get_logger(__name__)


@dataclass
class DiarizedSegment:
    """带说话人标签的片段"""
    start: float
    end: float
    speaker: str
    text: Optional[str] = None

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
            "start": self.start,
            "end": self.end,
            "start_formatted": self.start_formatted,
            "end_formatted": self.end_formatted,
            "speaker": self.speaker,
            "text": self.text,
        }


class SpeakerDiarizer:
    """说话人识别器"""

    def __init__(
        self,
        hf_token: Optional[str] = None,
        device: Optional[str] = None,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ):
        """
        初始化说话人识别器

        Args:
            hf_token: HuggingFace API Token（需要同意模型使用条款）
            device: 运行设备
            num_speakers: 精确说话人数量（如果已知）
            min_speakers: 最少说话人数量
            max_speakers: 最多说话人数量
        """
        settings = get_settings()

        self.hf_token = hf_token or settings.hf_token
        self.device = device or settings.get_whisper_device()
        self.num_speakers = num_speakers
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers

        self._pipeline = None

    def _load_pipeline(self):
        """懒加载 pipeline"""
        if self._pipeline is not None:
            return

        if not self.hf_token:
            raise ValueError(
                "需要 HuggingFace Token 才能使用说话人识别。"
                "请在 .env 中设置 HF_TOKEN 或传入 hf_token 参数。"
                "获取方式：https://huggingface.co/settings/tokens"
            )

        logger.info("加载说话人识别模型...")

        try:
            from pyannote.audio import Pipeline
            import torch

            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token,
            )

            # 移动到指定设备
            if self.device == "cuda" and torch.cuda.is_available():
                self._pipeline.to(torch.device("cuda"))

            logger.info("说话人识别模型加载完成")

        except ImportError:
            raise ImportError(
                "请安装 pyannote.audio: pip install pyannote.audio"
            )
        except Exception as e:
            raise RuntimeError(f"加载说话人识别模型失败: {e}")

    def diarize(
        self,
        audio_path: Path,
        num_speakers: Optional[int] = None,
    ) -> List[DiarizedSegment]:
        """
        对音频进行说话人分离

        Args:
            audio_path: 音频文件路径
            num_speakers: 说话人数量（可选）

        Returns:
            DiarizedSegment 列表
        """
        self._load_pipeline()

        logger.info(f"开始说话人识别: {audio_path}")
        start_time = time.time()

        # 准备参数
        params = {}
        if num_speakers or self.num_speakers:
            params["num_speakers"] = num_speakers or self.num_speakers
        if self.min_speakers:
            params["min_speakers"] = self.min_speakers
        if self.max_speakers:
            params["max_speakers"] = self.max_speakers

        # 执行说话人分离
        diarization = self._pipeline(str(audio_path), **params)

        # 转换结果
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                DiarizedSegment(
                    start=turn.start,
                    end=turn.end,
                    speaker=speaker,
                )
            )

        processing_time = time.time() - start_time
        logger.info(
            f"说话人识别完成: {len(segments)} 段, "
            f"{len(set(s.speaker for s in segments))} 位说话人, "
            f"耗时: {processing_time:.2f}s"
        )

        return segments

    def assign_speakers_to_transcription(
        self,
        transcription: TranscriptionResult,
        diarization: List[DiarizedSegment],
        speaker_names: Optional[Dict[str, str]] = None,
    ) -> TranscriptionResult:
        """
        将说话人标签分配给转录结果

        Args:
            transcription: 转录结果
            diarization: 说话人分离结果
            speaker_names: 说话人名称映射 (如 {"SPEAKER_00": "主持人"})

        Returns:
            更新后的转录结果
        """
        speaker_names = speaker_names or {}

        for segment in transcription.segments:
            # 找到与当前片段重叠最多的说话人
            best_speaker = None
            best_overlap = 0

            for diar_seg in diarization:
                # 计算重叠
                overlap_start = max(segment.start, diar_seg.start)
                overlap_end = min(segment.end, diar_seg.end)
                overlap = max(0, overlap_end - overlap_start)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = diar_seg.speaker

            if best_speaker:
                # 使用自定义名称或原始标签
                segment.speaker = speaker_names.get(best_speaker, best_speaker)

        return transcription

    def get_speaker_stats(
        self,
        diarization: List[DiarizedSegment],
    ) -> Dict[str, dict]:
        """
        获取说话人统计信息

        Args:
            diarization: 说话人分离结果

        Returns:
            说话人统计字典
        """
        stats = {}

        for seg in diarization:
            if seg.speaker not in stats:
                stats[seg.speaker] = {
                    "total_duration": 0,
                    "segment_count": 0,
                    "segments": [],
                }

            stats[seg.speaker]["total_duration"] += seg.duration
            stats[seg.speaker]["segment_count"] += 1
            stats[seg.speaker]["segments"].append({
                "start": seg.start,
                "end": seg.end,
            })

        # 计算百分比
        total_duration = sum(s["total_duration"] for s in stats.values())
        for speaker in stats:
            stats[speaker]["percentage"] = (
                stats[speaker]["total_duration"] / total_duration * 100
                if total_duration > 0
                else 0
            )
            stats[speaker]["total_duration_formatted"] = format_timestamp(
                stats[speaker]["total_duration"]
            )

        return stats


def merge_transcription_with_diarization(
    transcription: TranscriptionResult,
    diarization: List[DiarizedSegment],
    speaker_names: Optional[Dict[str, str]] = None,
) -> List[DiarizedSegment]:
    """
    合并转录结果和说话人分离结果

    Args:
        transcription: 转录结果
        diarization: 说话人分离结果
        speaker_names: 说话人名称映射

    Returns:
        合并后的 DiarizedSegment 列表
    """
    speaker_names = speaker_names or {}
    merged = []

    for diar_seg in diarization:
        # 找到在当前说话人时间段内的所有转录文本
        texts = []
        for trans_seg in transcription.segments:
            # 检查重叠
            if trans_seg.start < diar_seg.end and trans_seg.end > diar_seg.start:
                texts.append(trans_seg.text.strip())

        merged.append(
            DiarizedSegment(
                start=diar_seg.start,
                end=diar_seg.end,
                speaker=speaker_names.get(diar_seg.speaker, diar_seg.speaker),
                text=" ".join(texts) if texts else None,
            )
        )

    return merged
