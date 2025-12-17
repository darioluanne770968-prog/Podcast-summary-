"""
音频增强模块

综合音频处理：降噪、均衡、标准化
"""

from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class EnhancementConfig:
    """增强配置"""
    normalize: bool = True
    target_loudness: float = -16.0  # LUFS
    remove_silence: bool = False
    silence_threshold: float = -50.0  # dB
    min_silence_duration: float = 0.5  # seconds
    equalize: bool = False
    high_pass_freq: float = 80.0  # Hz
    low_pass_freq: float = 15000.0  # Hz
    compress: bool = False
    compression_ratio: float = 4.0


class AudioEnhancer:
    """音频增强器"""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("./output/enhanced")
        ensure_dir(self.output_dir)

    def enhance(
        self,
        audio_path: Path,
        config: Optional[EnhancementConfig] = None,
    ) -> Path:
        """
        综合增强音频

        Args:
            audio_path: 输入音频路径
            config: 增强配置

        Returns:
            处理后的音频路径
        """
        config = config or EnhancementConfig()
        logger.info(f"开始音频增强: {audio_path}")

        from pydub import AudioSegment

        audio = AudioSegment.from_file(str(audio_path))
        output_path = self.output_dir / f"{audio_path.stem}_enhanced.wav"

        # 1. 高通滤波（去除低频噪音）
        if config.equalize and config.high_pass_freq > 0:
            audio = audio.high_pass_filter(config.high_pass_freq)

        # 2. 低通滤波
        if config.equalize and config.low_pass_freq < 20000:
            audio = audio.low_pass_filter(config.low_pass_freq)

        # 3. 响度标准化
        if config.normalize:
            audio = self._normalize_loudness(audio, config.target_loudness)

        # 4. 移除静音
        if config.remove_silence:
            audio = self._remove_silence(
                audio,
                config.silence_threshold,
                config.min_silence_duration,
            )

        # 5. 动态压缩
        if config.compress:
            audio = self._compress(audio, config.compression_ratio)

        # 导出
        audio.export(str(output_path), format="wav")
        logger.info(f"音频增强完成: {output_path}")

        return output_path

    def _normalize_loudness(
        self,
        audio,
        target_lufs: float = -16.0,
    ):
        """响度标准化（LUFS）"""
        try:
            import pyloudnorm as pyln
            import numpy as np
            import soundfile as sf
            import tempfile

            # 导出为临时文件以便读取
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                audio.export(tmp.name, format="wav")
                data, rate = sf.read(tmp.name)

            # 测量当前响度
            meter = pyln.Meter(rate)
            loudness = meter.integrated_loudness(data)

            # 标准化
            normalized = pyln.normalize.loudness(data, loudness, target_lufs)

            # 转回 AudioSegment
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, normalized, rate)
                return type(audio).from_file(tmp.name)

        except ImportError:
            logger.warning("pyloudnorm 未安装，使用简单标准化")
            # 简单的 dBFS 标准化
            change_in_dbfs = target_lufs - audio.dBFS
            return audio.apply_gain(change_in_dbfs)

    def _remove_silence(
        self,
        audio,
        threshold_db: float = -50.0,
        min_duration: float = 0.5,
    ):
        """移除静音片段"""
        from pydub.silence import split_on_silence

        chunks = split_on_silence(
            audio,
            min_silence_len=int(min_duration * 1000),
            silence_thresh=threshold_db,
            keep_silence=200,  # 保留200ms静音作为过渡
        )

        if not chunks:
            return audio

        # 拼接非静音片段
        result = chunks[0]
        for chunk in chunks[1:]:
            result += chunk

        return result

    def _compress(self, audio, ratio: float = 4.0):
        """动态压缩"""
        # pydub 没有内置压缩，使用 ffmpeg
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_in:
            audio.export(tmp_in.name, format="wav")

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_out:
                cmd = [
                    "ffmpeg", "-i", tmp_in.name,
                    "-af", f"acompressor=threshold=-20dB:ratio={ratio}:attack=5:release=50",
                    "-y", tmp_out.name
                ]
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    return type(audio).from_file(tmp_out.name)
                except Exception as e:
                    logger.warning(f"压缩失败: {e}")
                    return audio

    def analyze_audio_quality(self, audio_path: Path) -> dict:
        """
        分析音频质量

        Returns:
            质量分析报告
        """
        from pydub import AudioSegment
        import numpy as np

        audio = AudioSegment.from_file(str(audio_path))
        samples = np.array(audio.get_array_of_samples())

        # 基本信息
        info = {
            "duration_seconds": len(audio) / 1000,
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "bit_depth": audio.sample_width * 8,
        }

        # 响度分析
        rms = np.sqrt(np.mean(samples.astype(float) ** 2))
        peak = np.max(np.abs(samples))
        dbfs = 20 * np.log10(rms / (2 ** (audio.sample_width * 8 - 1)))

        info["loudness"] = {
            "rms_dbfs": float(dbfs),
            "peak_dbfs": float(20 * np.log10(peak / (2 ** (audio.sample_width * 8 - 1)) + 1e-10)),
            "dynamic_range": float(20 * np.log10(peak / (rms + 1e-10))),
        }

        # 静音检测
        from pydub.silence import detect_silence
        silences = detect_silence(audio, min_silence_len=1000, silence_thresh=-50)
        total_silence = sum(end - start for start, end in silences) / 1000

        info["silence"] = {
            "total_seconds": float(total_silence),
            "percentage": float(total_silence / (len(audio) / 1000) * 100),
            "segments_count": len(silences),
        }

        # 质量评分
        score = 100
        if info["loudness"]["rms_dbfs"] < -30:
            score -= 20  # 太安静
        if info["loudness"]["rms_dbfs"] > -10:
            score -= 15  # 太响
        if info["silence"]["percentage"] > 20:
            score -= 10  # 太多静音
        if audio.frame_rate < 44100:
            score -= 10  # 采样率低

        info["quality_score"] = max(0, score)
        info["recommendations"] = self._get_recommendations(info)

        return info

    def _get_recommendations(self, analysis: dict) -> List[str]:
        """根据分析结果给出建议"""
        recommendations = []

        if analysis["loudness"]["rms_dbfs"] < -30:
            recommendations.append("音频过于安静，建议进行响度标准化")
        if analysis["loudness"]["rms_dbfs"] > -10:
            recommendations.append("音频过于响亮，可能存在削波")
        if analysis["silence"]["percentage"] > 20:
            recommendations.append("静音片段较多，建议移除多余静音")
        if analysis.get("sample_rate", 44100) < 44100:
            recommendations.append("采样率较低，音质可能受影响")

        if not recommendations:
            recommendations.append("音频质量良好，无需特殊处理")

        return recommendations


class BatchAudioEnhancer(AudioEnhancer):
    """批量音频增强器"""

    def enhance_batch(
        self,
        audio_paths: List[Path],
        config: Optional[EnhancementConfig] = None,
    ) -> List[Path]:
        """批量增强音频"""
        results = []
        for path in audio_paths:
            try:
                result = self.enhance(path, config)
                results.append(result)
            except Exception as e:
                logger.error(f"处理 {path} 失败: {e}")
        return results
