"""
音频降噪模块

使用多种降噪技术提升音频质量
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class NoiseProfile:
    """噪音配置"""
    noise_floor: float = -60.0  # dB
    reduction_amount: float = 0.75  # 0-1
    frequency_smoothing: float = 0.5


class NoiseReducer:
    """音频降噪器"""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("./output/enhanced")
        ensure_dir(self.output_dir)

    def reduce_noise(
        self,
        audio_path: Path,
        profile: Optional[NoiseProfile] = None,
        method: str = "spectral",  # spectral, rnnoise, deepfilter
    ) -> Path:
        """
        对音频进行降噪处理

        Args:
            audio_path: 输入音频路径
            profile: 降噪配置
            method: 降噪方法

        Returns:
            处理后的音频路径
        """
        logger.info(f"开始降噪处理: {audio_path} (方法: {method})")
        profile = profile or NoiseProfile()

        if method == "spectral":
            return self._spectral_denoise(audio_path, profile)
        elif method == "rnnoise":
            return self._rnnoise_denoise(audio_path)
        elif method == "deepfilter":
            return self._deepfilter_denoise(audio_path)
        else:
            raise ValueError(f"不支持的降噪方法: {method}")

    def _spectral_denoise(self, audio_path: Path, profile: NoiseProfile) -> Path:
        """频谱降噪（使用 noisereduce 库）"""
        try:
            import noisereduce as nr
            import soundfile as sf
        except ImportError:
            raise ImportError("请安装 noisereduce 和 soundfile: pip install noisereduce soundfile")

        # 读取音频
        data, rate = sf.read(str(audio_path))

        # 降噪处理
        reduced = nr.reduce_noise(
            y=data,
            sr=rate,
            prop_decrease=profile.reduction_amount,
            freq_mask_smooth_hz=int(profile.frequency_smoothing * 500),
        )

        # 保存结果
        output_path = self.output_dir / f"{audio_path.stem}_denoised.wav"
        sf.write(str(output_path), reduced, rate)

        logger.info(f"降噪完成: {output_path}")
        return output_path

    def _rnnoise_denoise(self, audio_path: Path) -> Path:
        """使用 RNNoise 降噪"""
        try:
            import subprocess
            output_path = self.output_dir / f"{audio_path.stem}_rnnoise.wav"

            # 使用 ffmpeg + rnnoise 滤镜
            cmd = [
                "ffmpeg", "-i", str(audio_path),
                "-af", "arnndn=m=rnnoise-models/cb.rnnn",
                "-y", str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except Exception as e:
            logger.warning(f"RNNoise 降噪失败，回退到频谱降噪: {e}")
            return self._spectral_denoise(audio_path, NoiseProfile())

    def _deepfilter_denoise(self, audio_path: Path) -> Path:
        """使用 DeepFilterNet 降噪"""
        try:
            from df.enhance import enhance, init_df, load_audio, save_audio

            model, df_state, _ = init_df()
            audio, _ = load_audio(str(audio_path), sr=df_state.sr())
            enhanced = enhance(model, df_state, audio)

            output_path = self.output_dir / f"{audio_path.stem}_deepfilter.wav"
            save_audio(str(output_path), enhanced, df_state.sr())

            logger.info(f"DeepFilter 降噪完成: {output_path}")
            return output_path

        except ImportError:
            logger.warning("DeepFilterNet 未安装，回退到频谱降噪")
            return self._spectral_denoise(audio_path, NoiseProfile())

    def analyze_noise(self, audio_path: Path) -> dict:
        """
        分析音频中的噪音情况

        Returns:
            噪音分析报告
        """
        try:
            import soundfile as sf
            import numpy as np

            data, rate = sf.read(str(audio_path))

            # 计算 RMS
            rms = np.sqrt(np.mean(data ** 2))
            db = 20 * np.log10(rms + 1e-10)

            # 计算静音段的噪音水平
            frame_length = int(rate * 0.025)  # 25ms 帧
            frames = np.array_split(data, len(data) // frame_length)
            frame_energies = [np.sqrt(np.mean(f ** 2)) for f in frames]

            # 找到最安静的 10% 帧作为噪音基准
            sorted_energies = sorted(frame_energies)
            noise_floor = np.mean(sorted_energies[:len(sorted_energies) // 10])
            noise_db = 20 * np.log10(noise_floor + 1e-10)

            # SNR 估计
            signal_db = 20 * np.log10(np.mean(sorted_energies[-len(sorted_energies) // 10:]) + 1e-10)
            snr = signal_db - noise_db

            return {
                "overall_level_db": float(db),
                "noise_floor_db": float(noise_db),
                "signal_level_db": float(signal_db),
                "estimated_snr": float(snr),
                "recommendation": self._get_recommendation(snr),
            }

        except Exception as e:
            logger.error(f"噪音分析失败: {e}")
            return {"error": str(e)}

    def _get_recommendation(self, snr: float) -> str:
        """根据 SNR 给出建议"""
        if snr > 30:
            return "音频质量优秀，无需降噪"
        elif snr > 20:
            return "音频质量良好，可选择轻度降噪"
        elif snr > 10:
            return "存在明显噪音，建议使用中度降噪"
        else:
            return "噪音严重，建议使用强力降噪"


class AdaptiveNoiseReducer(NoiseReducer):
    """自适应降噪器"""

    def reduce_noise_adaptive(self, audio_path: Path) -> Path:
        """根据噪音分析自动选择降噪参数"""
        analysis = self.analyze_noise(audio_path)

        snr = analysis.get("estimated_snr", 20)

        # 根据 SNR 自动调整参数
        if snr > 30:
            profile = NoiseProfile(reduction_amount=0.3)
        elif snr > 20:
            profile = NoiseProfile(reduction_amount=0.5)
        elif snr > 10:
            profile = NoiseProfile(reduction_amount=0.75)
        else:
            profile = NoiseProfile(reduction_amount=0.9)

        return self.reduce_noise(audio_path, profile, method="spectral")
