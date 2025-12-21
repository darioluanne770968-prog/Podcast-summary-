"""
多语言配音模块

支持多语言翻译和配音
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


class Language(str, Enum):
    """支持的语言"""
    CHINESE = "zh"
    ENGLISH = "en"
    JAPANESE = "ja"
    KOREAN = "ko"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"


@dataclass
class TranslatedSegment:
    """翻译片段"""
    original_text: str
    translated_text: str
    source_lang: Language
    target_lang: Language
    start_time: float
    end_time: float
    confidence: float = 1.0


@dataclass
class DubbedAudio:
    """配音结果"""
    source_lang: Language
    target_lang: Language
    original_path: str
    dubbed_path: str
    subtitle_path: Optional[str] = None
    segments: List[TranslatedSegment] = field(default_factory=list)


class MultilingualDubbing:
    """
    多语言配音系统

    功能：
    - 自动翻译
    - 保持说话人特征的配音
    - 生成多语言字幕
    - 时间轴对齐
    """

    # 语言对应的 Edge TTS 声音
    VOICE_MAP = {
        Language.CHINESE: "zh-CN-XiaoxiaoNeural",
        Language.ENGLISH: "en-US-JennyNeural",
        Language.JAPANESE: "ja-JP-NanamiNeural",
        Language.KOREAN: "ko-KR-SunHiNeural",
        Language.SPANISH: "es-ES-ElviraNeural",
        Language.FRENCH: "fr-FR-DeniseNeural",
        Language.GERMAN: "de-DE-KatjaNeural",
        Language.PORTUGUESE: "pt-BR-FranciscaNeural",
        Language.RUSSIAN: "ru-RU-SvetlanaNeural",
        Language.ARABIC: "ar-SA-ZariyahNeural",
    }

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path.home() / ".podcast_summary" / "dubbing"
        ensure_dir(self.output_dir)
        ensure_dir(self.output_dir / "translations")
        ensure_dir(self.output_dir / "audio")
        ensure_dir(self.output_dir / "subtitles")

    async def translate_segments(
        self,
        segments: List[Dict],
        source_lang: Language,
        target_lang: Language,
    ) -> List[TranslatedSegment]:
        """
        翻译分段

        Args:
            segments: 带时间戳的文本段落
            source_lang: 源语言
            target_lang: 目标语言

        Returns:
            翻译后的分段列表
        """
        translated_segments = []

        for segment in segments:
            text = segment.get("text", "")
            start = segment.get("start", 0)
            end = segment.get("end", 0)

            try:
                translated_text = await self._translate_text(
                    text, source_lang, target_lang
                )
                translated_segments.append(TranslatedSegment(
                    original_text=text,
                    translated_text=translated_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    start_time=start,
                    end_time=end,
                ))
            except Exception as e:
                logger.error(f"翻译失败: {e}")
                translated_segments.append(TranslatedSegment(
                    original_text=text,
                    translated_text=text,  # 保留原文
                    source_lang=source_lang,
                    target_lang=target_lang,
                    start_time=start,
                    end_time=end,
                    confidence=0,
                ))

        return translated_segments

    async def _translate_text(
        self,
        text: str,
        source_lang: Language,
        target_lang: Language,
    ) -> str:
        """翻译文本"""
        # 使用 OpenAI 翻译
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI()

            lang_names = {
                Language.CHINESE: "中文",
                Language.ENGLISH: "英文",
                Language.JAPANESE: "日文",
                Language.KOREAN: "韩文",
                Language.SPANISH: "西班牙文",
                Language.FRENCH: "法文",
                Language.GERMAN: "德文",
            }

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个专业翻译。将{lang_names.get(source_lang, '源语言')}翻译成{lang_names.get(target_lang, '目标语言')}。保持原意和语气。只输出翻译结果。",
                    },
                    {"role": "user", "content": text},
                ],
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"翻译 API 调用失败: {e}")
            # 备选：使用免费翻译 API
            return await self._translate_with_libre(text, source_lang, target_lang)

    async def _translate_with_libre(
        self,
        text: str,
        source_lang: Language,
        target_lang: Language,
    ) -> str:
        """使用 LibreTranslate 翻译（备选）"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://libretranslate.com/translate",
                    json={
                        "q": text,
                        "source": source_lang.value,
                        "target": target_lang.value,
                    },
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("translatedText", text)
        except Exception as e:
            logger.warning(f"LibreTranslate 失败: {e}")
        return text

    async def dub_audio(
        self,
        segments: List[TranslatedSegment],
        target_lang: Language,
        output_name: str,
        voice: Optional[str] = None,
    ) -> Path:
        """
        生成配音音频

        Args:
            segments: 翻译后的分段
            target_lang: 目标语言
            output_name: 输出文件名
            voice: 指定声音

        Returns:
            配音文件路径
        """
        voice = voice or self.VOICE_MAP.get(target_lang, "en-US-JennyNeural")
        output_path = self.output_dir / "audio" / f"{output_name}_{target_lang.value}.mp3"

        try:
            import edge_tts
            from pydub import AudioSegment

            # 生成每个片段的音频
            segment_audios = []
            temp_files = []

            for i, segment in enumerate(segments):
                temp_path = self.output_dir / "audio" / f"temp_{i}.mp3"
                temp_files.append(temp_path)

                communicate = edge_tts.Communicate(
                    segment.translated_text,
                    voice,
                )
                await communicate.save(str(temp_path))

                audio = AudioSegment.from_mp3(str(temp_path))
                segment_audios.append({
                    "audio": audio,
                    "start": segment.start_time,
                    "end": segment.end_time,
                })

            # 合并音频，考虑时间对齐
            if segment_audios:
                total_duration = max(s["end"] for s in segment_audios) * 1000  # 毫秒
                final_audio = AudioSegment.silent(duration=int(total_duration))

                for seg in segment_audios:
                    start_ms = int(seg["start"] * 1000)
                    final_audio = final_audio.overlay(seg["audio"], position=start_ms)

                final_audio.export(str(output_path), format="mp3")

            # 清理临时文件
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                except:
                    pass

            logger.info(f"配音生成完成: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"配音生成失败: {e}")
            raise

    async def generate_subtitles(
        self,
        segments: List[TranslatedSegment],
        output_name: str,
        format: str = "srt",
    ) -> Path:
        """
        生成字幕文件

        Args:
            segments: 翻译后的分段
            output_name: 输出文件名
            format: 字幕格式 (srt, vtt, ass)

        Returns:
            字幕文件路径
        """
        output_path = self.output_dir / "subtitles" / f"{output_name}.{format}"

        if format == "srt":
            content = self._generate_srt(segments)
        elif format == "vtt":
            content = self._generate_vtt(segments)
        elif format == "ass":
            content = self._generate_ass(segments)
        else:
            raise ValueError(f"不支持的字幕格式: {format}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"字幕生成完成: {output_path}")
        return output_path

    def _generate_srt(self, segments: List[TranslatedSegment]) -> str:
        """生成 SRT 格式字幕"""
        lines = []
        for i, seg in enumerate(segments, 1):
            start = self._format_time_srt(seg.start_time)
            end = self._format_time_srt(seg.end_time)
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(seg.translated_text)
            lines.append("")
        return "\n".join(lines)

    def _generate_vtt(self, segments: List[TranslatedSegment]) -> str:
        """生成 VTT 格式字幕"""
        lines = ["WEBVTT", ""]
        for seg in segments:
            start = self._format_time_vtt(seg.start_time)
            end = self._format_time_vtt(seg.end_time)
            lines.append(f"{start} --> {end}")
            lines.append(seg.translated_text)
            lines.append("")
        return "\n".join(lines)

    def _generate_ass(self, segments: List[TranslatedSegment]) -> str:
        """生成 ASS 格式字幕"""
        header = """[Script Info]
Title: Podcast Translation
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        lines = [header]
        for seg in segments:
            start = self._format_time_ass(seg.start_time)
            end = self._format_time_ass(seg.end_time)
            text = seg.translated_text.replace("\n", "\\N")
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        return "\n".join(lines)

    def _format_time_srt(self, seconds: float) -> str:
        """格式化 SRT 时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_time_vtt(self, seconds: float) -> str:
        """格式化 VTT 时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _format_time_ass(self, seconds: float) -> str:
        """格式化 ASS 时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    async def full_dubbing_pipeline(
        self,
        audio_path: Path,
        transcript_segments: List[Dict],
        source_lang: Language,
        target_langs: List[Language],
        output_name: str,
    ) -> List[DubbedAudio]:
        """
        完整配音流程

        Args:
            audio_path: 原始音频路径
            transcript_segments: 转录分段
            source_lang: 源语言
            target_langs: 目标语言列表
            output_name: 输出名称

        Returns:
            配音结果列表
        """
        results = []

        for target_lang in target_langs:
            try:
                # 翻译
                translated = await self.translate_segments(
                    transcript_segments,
                    source_lang,
                    target_lang,
                )

                # 配音
                dubbed_path = await self.dub_audio(
                    translated,
                    target_lang,
                    output_name,
                )

                # 字幕
                subtitle_path = await self.generate_subtitles(
                    translated,
                    f"{output_name}_{target_lang.value}",
                )

                results.append(DubbedAudio(
                    source_lang=source_lang,
                    target_lang=target_lang,
                    original_path=str(audio_path),
                    dubbed_path=str(dubbed_path),
                    subtitle_path=str(subtitle_path),
                    segments=translated,
                ))

                logger.info(f"完成 {target_lang.value} 配音")

            except Exception as e:
                logger.error(f"{target_lang.value} 配音失败: {e}")

        return results
