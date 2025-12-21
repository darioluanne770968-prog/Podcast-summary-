"""
声音克隆模块

用主播的声音生成新内容
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import hashlib

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class VoiceProfile:
    """声音档案"""
    id: str
    name: str
    description: str = ""
    sample_paths: List[str] = field(default_factory=list)
    characteristics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sample_paths": self.sample_paths,
            "characteristics": self.characteristics,
            "created_at": self.created_at,
        }


class VoiceCloner:
    """
    声音克隆器

    功能：
    - 从音频样本提取声音特征
    - 使用克隆声音合成新内容
    - 声音风格混合
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "voice_clone"
        ensure_dir(self.storage_dir)
        ensure_dir(self.storage_dir / "profiles")
        ensure_dir(self.storage_dir / "samples")
        ensure_dir(self.storage_dir / "output")
        self._profiles: Dict[str, VoiceProfile] = {}
        self._load_profiles()

    def _load_profiles(self):
        """加载声音档案"""
        profiles_file = self.storage_dir / "profiles.json"
        if profiles_file.exists():
            try:
                with open(profiles_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for profile_data in data:
                        profile = VoiceProfile(**profile_data)
                        self._profiles[profile.id] = profile
            except Exception as e:
                logger.error(f"加载声音档案失败: {e}")

    def _save_profiles(self):
        """保存声音档案"""
        profiles_file = self.storage_dir / "profiles.json"
        try:
            data = [p.to_dict() for p in self._profiles.values()]
            with open(profiles_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存声音档案失败: {e}")

    async def create_profile(
        self,
        name: str,
        audio_samples: List[Path],
        description: str = "",
    ) -> VoiceProfile:
        """
        创建声音档案

        Args:
            name: 档案名称
            audio_samples: 音频样本路径列表
            description: 描述

        Returns:
            VoiceProfile
        """
        profile_id = hashlib.md5(name.encode()).hexdigest()[:8]

        # 复制样本文件
        sample_paths = []
        for i, sample_path in enumerate(audio_samples):
            if Path(sample_path).exists():
                dest_path = self.storage_dir / "samples" / f"{profile_id}_{i}.wav"
                # 转换为 WAV 格式
                await self._convert_to_wav(sample_path, dest_path)
                sample_paths.append(str(dest_path))

        # 提取声音特征
        characteristics = await self._extract_characteristics(sample_paths)

        profile = VoiceProfile(
            id=profile_id,
            name=name,
            description=description,
            sample_paths=sample_paths,
            characteristics=characteristics,
        )

        self._profiles[profile_id] = profile
        self._save_profiles()
        logger.info(f"创建声音档案: {name}")
        return profile

    async def _convert_to_wav(self, input_path: Path, output_path: Path):
        """转换为 WAV 格式"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(str(input_path))
            audio = audio.set_frame_rate(22050).set_channels(1)
            audio.export(str(output_path), format="wav")
        except Exception as e:
            logger.error(f"音频转换失败: {e}")
            raise

    async def _extract_characteristics(
        self,
        sample_paths: List[str],
    ) -> Dict[str, Any]:
        """提取声音特征"""
        characteristics = {
            "pitch_mean": 0,
            "pitch_std": 0,
            "energy_mean": 0,
            "speaking_rate": 0,
            "voice_quality": "normal",
        }

        try:
            import librosa
            import numpy as np

            all_pitches = []
            all_energies = []
            total_duration = 0
            total_words = 0

            for sample_path in sample_paths:
                y, sr = librosa.load(sample_path, sr=22050)

                # 提取基频
                pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
                pitch_values = pitches[magnitudes > np.median(magnitudes)]
                pitch_values = pitch_values[pitch_values > 0]
                if len(pitch_values) > 0:
                    all_pitches.extend(pitch_values)

                # 提取能量
                rms = librosa.feature.rms(y=y)[0]
                all_energies.extend(rms)

                # 时长
                total_duration += librosa.get_duration(y=y, sr=sr)

            if all_pitches:
                characteristics["pitch_mean"] = float(np.mean(all_pitches))
                characteristics["pitch_std"] = float(np.std(all_pitches))

            if all_energies:
                characteristics["energy_mean"] = float(np.mean(all_energies))

            # 估算语速（假设每秒 3 个词）
            characteristics["speaking_rate"] = 3.0

        except ImportError:
            logger.warning("librosa 未安装，跳过特征提取")
        except Exception as e:
            logger.error(f"特征提取失败: {e}")

        return characteristics

    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """获取声音档案"""
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[VoiceProfile]:
        """列出所有声音档案"""
        return list(self._profiles.values())

    async def synthesize(
        self,
        profile_id: str,
        text: str,
        output_path: Optional[Path] = None,
        method: str = "xtts",
    ) -> Path:
        """
        使用克隆声音合成语音

        Args:
            profile_id: 声音档案 ID
            text: 要合成的文本
            output_path: 输出路径
            method: 合成方法 (xtts, openai, elevenlabs)

        Returns:
            输出文件路径
        """
        profile = self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"声音档案不存在: {profile_id}")

        if not output_path:
            output_path = self.storage_dir / "output" / f"synth_{profile_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"

        if method == "xtts":
            await self._synthesize_xtts(profile, text, output_path)
        elif method == "openai":
            await self._synthesize_openai(text, output_path)
        elif method == "elevenlabs":
            await self._synthesize_elevenlabs(profile, text, output_path)
        else:
            raise ValueError(f"不支持的合成方法: {method}")

        logger.info(f"语音合成完成: {output_path}")
        return output_path

    async def _synthesize_xtts(
        self,
        profile: VoiceProfile,
        text: str,
        output_path: Path,
    ):
        """使用 XTTS 合成"""
        try:
            from TTS.api import TTS
            tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

            # 使用第一个样本作为参考
            reference_audio = profile.sample_paths[0] if profile.sample_paths else None

            if reference_audio:
                tts.tts_to_file(
                    text=text,
                    file_path=str(output_path),
                    speaker_wav=reference_audio,
                    language="zh-cn",
                )
            else:
                tts.tts_to_file(
                    text=text,
                    file_path=str(output_path),
                    language="zh-cn",
                )
        except ImportError:
            logger.warning("TTS 库未安装，使用 Edge TTS 替代")
            await self._synthesize_edge_tts(text, output_path)
        except Exception as e:
            logger.error(f"XTTS 合成失败: {e}")
            await self._synthesize_edge_tts(text, output_path)

    async def _synthesize_edge_tts(self, text: str, output_path: Path):
        """使用 Edge TTS 合成（备选）"""
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            await communicate.save(str(output_path))
        except Exception as e:
            logger.error(f"Edge TTS 合成失败: {e}")

    async def _synthesize_openai(self, text: str, output_path: Path):
        """使用 OpenAI TTS 合成"""
        try:
            from openai import OpenAI
            client = OpenAI()
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice="nova",
                input=text,
            )
            response.stream_to_file(str(output_path))
        except Exception as e:
            logger.error(f"OpenAI TTS 合成失败: {e}")

    async def _synthesize_elevenlabs(
        self,
        profile: VoiceProfile,
        text: str,
        output_path: Path,
    ):
        """使用 ElevenLabs 合成"""
        try:
            from elevenlabs import clone, generate, save

            # 克隆声音
            voice = clone(
                name=profile.name,
                files=profile.sample_paths,
            )

            # 生成语音
            audio = generate(
                text=text,
                voice=voice,
            )

            save(audio, str(output_path))
        except ImportError:
            logger.error("elevenlabs 库未安装")
            raise
        except Exception as e:
            logger.error(f"ElevenLabs 合成失败: {e}")
            raise

    async def generate_summary_audio(
        self,
        profile_id: str,
        summary: str,
    ) -> Path:
        """
        用克隆声音生成摘要音频

        Args:
            profile_id: 声音档案 ID
            summary: 摘要文本

        Returns:
            音频文件路径
        """
        return await self.synthesize(profile_id, summary)

    async def blend_voices(
        self,
        profile_ids: List[str],
        weights: List[float] = None,
    ) -> VoiceProfile:
        """
        混合多个声音

        Args:
            profile_ids: 声音档案 ID 列表
            weights: 权重列表

        Returns:
            混合后的声音档案
        """
        if not weights:
            weights = [1.0 / len(profile_ids)] * len(profile_ids)

        profiles = [self.get_profile(pid) for pid in profile_ids]
        profiles = [p for p in profiles if p]

        if not profiles:
            raise ValueError("没有有效的声音档案")

        # 混合特征
        blended_characteristics = {}
        for key in profiles[0].characteristics:
            if isinstance(profiles[0].characteristics[key], (int, float)):
                blended_characteristics[key] = sum(
                    p.characteristics.get(key, 0) * w
                    for p, w in zip(profiles, weights)
                )
            else:
                blended_characteristics[key] = profiles[0].characteristics[key]

        # 收集所有样本
        all_samples = []
        for p in profiles:
            all_samples.extend(p.sample_paths)

        blended_profile = VoiceProfile(
            id=f"blend_{'_'.join(profile_ids)}",
            name=f"混合: {', '.join(p.name for p in profiles)}",
            description="混合声音档案",
            sample_paths=all_samples,
            characteristics=blended_characteristics,
        )

        self._profiles[blended_profile.id] = blended_profile
        self._save_profiles()

        return blended_profile
