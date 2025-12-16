"""
音频格式转换模块
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from pydub import AudioSegment

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


class AudioConverter:
    """音频格式转换器"""

    SUPPORTED_FORMATS = ["mp3", "wav", "m4a", "flac", "ogg", "aac"]

    def __init__(self, output_dir: Optional[Path] = None):
        """
        初始化转换器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "podcast_summary"
        ensure_dir(self.output_dir)

    def convert(
        self,
        input_path: Path,
        output_format: str = "wav",
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> Path:
        """
        转换音频格式

        Args:
            input_path: 输入文件路径
            output_format: 输出格式
            sample_rate: 采样率（Hz）
            channels: 声道数

        Returns:
            输出文件路径
        """
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的格式: {output_format}")

        output_path = self.output_dir / f"{input_path.stem}.{output_format}"

        logger.info(f"转换音频: {input_path} -> {output_path}")

        # 加载音频
        audio = AudioSegment.from_file(str(input_path))

        # 转换参数
        audio = audio.set_frame_rate(sample_rate)
        audio = audio.set_channels(channels)

        # 导出
        audio.export(str(output_path), format=output_format)

        logger.info(f"转换完成: {output_path}")
        return output_path

    def get_audio_info(self, audio_path: Path) -> dict:
        """
        获取音频信息

        Args:
            audio_path: 音频文件路径

        Returns:
            音频信息字典
        """
        audio = AudioSegment.from_file(str(audio_path))

        return {
            "duration_seconds": len(audio) / 1000,
            "duration_formatted": self._format_duration(len(audio) / 1000),
            "channels": audio.channels,
            "sample_rate": audio.frame_rate,
            "sample_width": audio.sample_width,
            "frame_count": audio.frame_count(),
            "file_size_mb": audio_path.stat().st_size / (1024 * 1024),
        }

    def split_audio(
        self,
        audio_path: Path,
        segments: list[Tuple[float, float]],
        output_prefix: str = "segment",
    ) -> list[Path]:
        """
        分割音频

        Args:
            audio_path: 音频文件路径
            segments: 分割点列表 [(start_sec, end_sec), ...]
            output_prefix: 输出文件前缀

        Returns:
            分割后的文件路径列表
        """
        audio = AudioSegment.from_file(str(audio_path))
        output_paths = []

        for i, (start, end) in enumerate(segments):
            start_ms = int(start * 1000)
            end_ms = int(end * 1000)

            segment = audio[start_ms:end_ms]
            output_path = self.output_dir / f"{output_prefix}_{i:03d}.wav"
            segment.export(str(output_path), format="wav")
            output_paths.append(output_path)

            logger.info(f"分割片段 {i}: {start:.2f}s - {end:.2f}s -> {output_path}")

        return output_paths

    def normalize_audio(
        self,
        audio_path: Path,
        target_dbfs: float = -20.0,
    ) -> Path:
        """
        音频标准化（调整音量）

        Args:
            audio_path: 音频文件路径
            target_dbfs: 目标分贝值

        Returns:
            处理后的文件路径
        """
        audio = AudioSegment.from_file(str(audio_path))

        # 计算需要调整的分贝数
        change_in_dbfs = target_dbfs - audio.dBFS

        # 调整音量
        normalized = audio.apply_gain(change_in_dbfs)

        output_path = self.output_dir / f"{audio_path.stem}_normalized{audio_path.suffix}"
        normalized.export(str(output_path), format=audio_path.suffix.lstrip("."))

        logger.info(f"音频标准化完成: {output_path}")
        return output_path

    def extract_audio_from_video(
        self,
        video_path: Path,
        output_format: str = "wav",
    ) -> Path:
        """
        从视频中提取音频

        Args:
            video_path: 视频文件路径
            output_format: 输出音频格式

        Returns:
            音频文件路径
        """
        output_path = self.output_dir / f"{video_path.stem}.{output_format}"

        logger.info(f"从视频提取音频: {video_path}")

        # 使用 ffmpeg 提取音频
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # 不包含视频
            "-acodec", "pcm_s16le" if output_format == "wav" else "libmp3lame",
            "-ar", "16000",  # 采样率
            "-ac", "1",  # 单声道
            "-y",  # 覆盖输出文件
            str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg 提取音频失败: {e.stderr.decode()}")
        except FileNotFoundError:
            raise RuntimeError("未找到 ffmpeg，请确保已安装 ffmpeg")

        logger.info(f"音频提取完成: {output_path}")
        return output_path

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """格式化时长"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
