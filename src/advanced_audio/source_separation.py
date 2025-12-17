"""
音源分离模块

分离人声、背景音乐、效果音等
"""

from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
import subprocess

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class SeparationResult:
    """分离结果"""
    vocals_path: Optional[Path] = None  # 人声
    accompaniment_path: Optional[Path] = None  # 伴奏/背景
    drums_path: Optional[Path] = None  # 鼓
    bass_path: Optional[Path] = None  # 贝斯
    other_path: Optional[Path] = None  # 其他

    def to_dict(self) -> dict:
        return {
            "vocals": str(self.vocals_path) if self.vocals_path else None,
            "accompaniment": str(self.accompaniment_path) if self.accompaniment_path else None,
            "drums": str(self.drums_path) if self.drums_path else None,
            "bass": str(self.bass_path) if self.bass_path else None,
            "other": str(self.other_path) if self.other_path else None,
        }


class SourceSeparator:
    """音源分离器"""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        model: str = "htdemucs",  # htdemucs, htdemucs_ft, mdx_extra
    ):
        self.output_dir = output_dir or Path("./output/separated")
        self.model = model
        ensure_dir(self.output_dir)

    def separate(
        self,
        audio_path: Path,
        stems: List[str] = None,  # vocals, drums, bass, other
    ) -> SeparationResult:
        """
        分离音频源

        Args:
            audio_path: 输入音频路径
            stems: 要分离的音轨（默认全部）

        Returns:
            SeparationResult 对象
        """
        stems = stems or ["vocals", "accompaniment"]
        logger.info(f"开始音源分离: {audio_path} -> {stems}")

        try:
            return self._separate_with_demucs(audio_path, stems)
        except Exception as e:
            logger.warning(f"Demucs 分离失败: {e}, 尝试 Spleeter")
            try:
                return self._separate_with_spleeter(audio_path, stems)
            except Exception as e2:
                logger.error(f"音源分离失败: {e2}")
                raise

    def _separate_with_demucs(self, audio_path: Path, stems: List[str]) -> SeparationResult:
        """使用 Demucs 进行分离"""
        try:
            import demucs.separate
            import torch
        except ImportError:
            raise ImportError("请安装 demucs: pip install demucs")

        # 运行分离
        output_subdir = self.output_dir / audio_path.stem
        ensure_dir(output_subdir)

        # 使用命令行方式调用（更稳定）
        cmd = [
            "python", "-m", "demucs.separate",
            "-n", self.model,
            "-o", str(self.output_dir),
            str(audio_path)
        ]

        subprocess.run(cmd, check=True, capture_output=True)

        # 构建结果
        model_output = self.output_dir / self.model / audio_path.stem

        result = SeparationResult()
        if (model_output / "vocals.wav").exists():
            result.vocals_path = model_output / "vocals.wav"
        if (model_output / "no_vocals.wav").exists():
            result.accompaniment_path = model_output / "no_vocals.wav"
        elif (model_output / "other.wav").exists():
            # htdemucs 输出格式
            result.other_path = model_output / "other.wav"
        if (model_output / "drums.wav").exists():
            result.drums_path = model_output / "drums.wav"
        if (model_output / "bass.wav").exists():
            result.bass_path = model_output / "bass.wav"

        logger.info(f"Demucs 分离完成")
        return result

    def _separate_with_spleeter(self, audio_path: Path, stems: List[str]) -> SeparationResult:
        """使用 Spleeter 进行分离"""
        try:
            from spleeter.separator import Separator
        except ImportError:
            raise ImportError("请安装 spleeter: pip install spleeter")

        # 根据需要的音轨选择模型
        if len(stems) <= 2:
            model = "spleeter:2stems"
        elif len(stems) <= 4:
            model = "spleeter:4stems"
        else:
            model = "spleeter:5stems"

        separator = Separator(model)
        output_subdir = self.output_dir / audio_path.stem

        separator.separate_to_file(
            str(audio_path),
            str(self.output_dir),
        )

        result = SeparationResult()
        if (output_subdir / "vocals.wav").exists():
            result.vocals_path = output_subdir / "vocals.wav"
        if (output_subdir / "accompaniment.wav").exists():
            result.accompaniment_path = output_subdir / "accompaniment.wav"

        logger.info(f"Spleeter 分离完成")
        return result

    def extract_vocals_only(self, audio_path: Path) -> Path:
        """仅提取人声"""
        result = self.separate(audio_path, stems=["vocals"])
        if result.vocals_path:
            return result.vocals_path
        raise RuntimeError("人声提取失败")

    def remove_music(self, audio_path: Path) -> Path:
        """
        移除背景音乐，保留人声

        适用于有背景音乐的播客
        """
        return self.extract_vocals_only(audio_path)


class IntelligentSeparator(SourceSeparator):
    """智能音源分离器"""

    def analyze_and_separate(self, audio_path: Path) -> Dict:
        """
        分析音频内容并智能分离

        Returns:
            包含分离结果和分析的字典
        """
        import soundfile as sf
        import numpy as np

        # 读取音频进行分析
        data, rate = sf.read(str(audio_path))

        # 简单的频谱分析判断是否有音乐
        if len(data.shape) > 1:
            data = data.mean(axis=1)

        # FFT 分析
        fft = np.fft.fft(data)
        freqs = np.fft.fftfreq(len(fft), 1/rate)

        # 分析低频能量（音乐通常有更多低频）
        low_freq_mask = (np.abs(freqs) < 300) & (np.abs(freqs) > 20)
        mid_freq_mask = (np.abs(freqs) >= 300) & (np.abs(freqs) < 3000)

        low_energy = np.mean(np.abs(fft[low_freq_mask]))
        mid_energy = np.mean(np.abs(fft[mid_freq_mask]))

        ratio = low_energy / (mid_energy + 1e-10)

        has_music = ratio > 0.5  # 简单阈值判断

        analysis = {
            "has_background_music": has_music,
            "low_freq_ratio": float(ratio),
            "recommendation": "建议进行音源分离" if has_music else "无需音源分离",
        }

        # 如果检测到音乐，进行分离
        if has_music:
            separation_result = self.separate(audio_path)
            analysis["separation_result"] = separation_result.to_dict()
            analysis["processed_audio"] = str(separation_result.vocals_path)
        else:
            analysis["processed_audio"] = str(audio_path)

        return analysis
