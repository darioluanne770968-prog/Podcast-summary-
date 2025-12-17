"""
语音摘要生成模块（TTS）

将文字摘要转换为语音，方便用户收听
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Literal
import subprocess

from ..utils import get_logger, ensure_dir
from ..analysis import LLMClient

logger = get_logger(__name__)


@dataclass
class TTSConfig:
    """TTS 配置"""
    voice: str = "alloy"  # OpenAI: alloy, echo, fable, onyx, nova, shimmer
    speed: float = 1.0
    language: str = "zh"
    provider: str = "edge"  # openai, edge, gtts


class TTSSummaryGenerator:
    """语音摘要生成器"""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        config: Optional[TTSConfig] = None,
    ):
        self.output_dir = output_dir or Path("./output/audio_summaries")
        self.config = config or TTSConfig()
        ensure_dir(self.output_dir)

    def generate(
        self,
        text: str,
        filename: str = "summary",
        config: Optional[TTSConfig] = None,
    ) -> Path:
        """
        生成语音摘要

        Args:
            text: 要转换的文本
            filename: 输出文件名
            config: TTS 配置

        Returns:
            输出音频路径
        """
        config = config or self.config
        logger.info(f"生成语音摘要 (provider: {config.provider})...")

        if config.provider == "openai":
            return self._generate_openai(text, filename, config)
        elif config.provider == "edge":
            return self._generate_edge_tts(text, filename, config)
        elif config.provider == "gtts":
            return self._generate_gtts(text, filename, config)
        else:
            raise ValueError(f"不支持的 TTS provider: {config.provider}")

    def _generate_openai(
        self,
        text: str,
        filename: str,
        config: TTSConfig,
    ) -> Path:
        """使用 OpenAI TTS"""
        try:
            from openai import OpenAI

            client = OpenAI()
            output_path = self.output_dir / f"{filename}.mp3"

            response = client.audio.speech.create(
                model="tts-1",
                voice=config.voice,
                input=text,
                speed=config.speed,
            )

            response.stream_to_file(str(output_path))
            logger.info(f"OpenAI TTS 完成: {output_path}")
            return output_path

        except ImportError:
            logger.warning("OpenAI 未安装，回退到 edge-tts")
            return self._generate_edge_tts(text, filename, config)
        except Exception as e:
            logger.warning(f"OpenAI TTS 失败: {e}，回退到 edge-tts")
            return self._generate_edge_tts(text, filename, config)

    def _generate_edge_tts(
        self,
        text: str,
        filename: str,
        config: TTSConfig,
    ) -> Path:
        """使用 Edge TTS（免费）"""
        try:
            import asyncio
            import edge_tts

            output_path = self.output_dir / f"{filename}.mp3"

            # 选择语音
            voice = self._get_edge_voice(config.language)

            async def _generate():
                communicate = edge_tts.Communicate(text, voice, rate=f"+{int((config.speed-1)*100)}%")
                await communicate.save(str(output_path))

            asyncio.run(_generate())
            logger.info(f"Edge TTS 完成: {output_path}")
            return output_path

        except ImportError:
            logger.warning("edge-tts 未安装，回退到 gTTS")
            return self._generate_gtts(text, filename, config)

    def _generate_gtts(
        self,
        text: str,
        filename: str,
        config: TTSConfig,
    ) -> Path:
        """使用 Google TTS（免费）"""
        try:
            from gtts import gTTS

            output_path = self.output_dir / f"{filename}.mp3"

            tts = gTTS(text=text, lang=config.language, slow=config.speed < 1)
            tts.save(str(output_path))

            logger.info(f"gTTS 完成: {output_path}")
            return output_path

        except ImportError:
            raise ImportError("请安装 gTTS: pip install gTTS")

    def _get_edge_voice(self, language: str) -> str:
        """获取 Edge TTS 语音"""
        voice_mapping = {
            "zh": "zh-CN-XiaoxiaoNeural",
            "en": "en-US-JennyNeural",
            "ja": "ja-JP-NanamiNeural",
            "ko": "ko-KR-SunHiNeural",
        }
        return voice_mapping.get(language, "zh-CN-XiaoxiaoNeural")

    def generate_podcast_summary_audio(
        self,
        summary_data: dict,
        title: str,
    ) -> Path:
        """
        生成播客摘要音频

        Args:
            summary_data: 摘要数据（包含 brief, key_points 等）
            title: 播客标题

        Returns:
            输出音频路径
        """
        # 构建语音脚本
        script = self._build_summary_script(summary_data, title)

        return self.generate(script, filename=f"summary_{title[:30]}")

    def _build_summary_script(self, summary_data: dict, title: str) -> str:
        """构建摘要语音脚本"""
        lines = []

        # 开场
        lines.append(f"这是《{title}》的内容摘要。")

        # 简要概述
        if summary_data.get("brief"):
            lines.append(f"本期播客主要讲述了：{summary_data['brief']}")

        # 核心要点
        if summary_data.get("key_points"):
            lines.append("核心要点包括：")
            for i, point in enumerate(summary_data["key_points"][:5], 1):
                lines.append(f"第{i}点，{point}")

        # 收获启发
        if summary_data.get("takeaways"):
            lines.append("主要收获和启发：")
            for takeaway in summary_data["takeaways"][:3]:
                lines.append(takeaway)

        # 结尾
        lines.append("以上就是本期播客的内容摘要。")

        return "。".join(lines)

    def generate_quote_audio(
        self,
        quotes: List[dict],
        title: str,
    ) -> Path:
        """
        生成金句合集音频

        Args:
            quotes: 金句列表
            title: 播客标题

        Returns:
            输出音频路径
        """
        lines = [f"《{title}》金句精选："]

        for i, quote in enumerate(quotes[:10], 1):
            text = quote.get("text", "")
            speaker = quote.get("speaker", "")

            if speaker:
                lines.append(f"第{i}句，{speaker}说：{text}")
            else:
                lines.append(f"第{i}句：{text}")

        script = "。".join(lines)
        return self.generate(script, filename=f"quotes_{title[:30]}")


class MultiVoiceTTS(TTSSummaryGenerator):
    """多角色语音生成（适用于对话内容）"""

    def generate_dialogue(
        self,
        segments: List[dict],
        speaker_voices: dict,
    ) -> Path:
        """
        生成多角色对话音频

        Args:
            segments: 片段列表 [{"speaker": "A", "text": "..."}]
            speaker_voices: 说话人语音映射 {"A": "voice1", "B": "voice2"}

        Returns:
            合成后的音频路径
        """
        from pydub import AudioSegment

        combined = AudioSegment.empty()

        for i, segment in enumerate(segments):
            speaker = segment.get("speaker", "default")
            text = segment.get("text", "")

            # 获取语音配置
            voice = speaker_voices.get(speaker, self.config.voice)
            config = TTSConfig(voice=voice, language=self.config.language)

            # 生成片段
            segment_path = self.generate(text, f"segment_{i}", config)

            # 合并
            segment_audio = AudioSegment.from_mp3(str(segment_path))
            combined += segment_audio + AudioSegment.silent(duration=500)  # 500ms 间隔

        # 保存合并后的音频
        output_path = self.output_dir / "dialogue_combined.mp3"
        combined.export(str(output_path), format="mp3")

        logger.info(f"多角色对话音频生成完成: {output_path}")
        return output_path
