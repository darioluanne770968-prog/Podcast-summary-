"""
短视频/片段生成模块

从播客中提取精华片段，生成带字幕的短视频
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Tuple
import subprocess
import json

from ..utils import get_logger, ensure_dir, format_timestamp
from ..analysis import LLMClient

logger = get_logger(__name__)


@dataclass
class VideoClip:
    """视频片段"""
    start_time: float
    end_time: float
    title: str
    description: str
    transcript: str
    tags: List[str] = field(default_factory=list)
    output_path: Optional[Path] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "title": self.title,
            "description": self.description,
            "transcript": self.transcript,
            "tags": self.tags,
            "duration": self.duration,
            "output_path": str(self.output_path) if self.output_path else None,
        }


class VideoClipper:
    """视频片段生成器"""

    SYSTEM_PROMPT = """你是一个视频编辑专家，擅长从长播客中识别和提取精华片段。

选择片段的标准：
1. 内容独立完整，不依赖上下文
2. 观点独到有洞察力
3. 表达精炼有感染力
4. 适合短视频传播（15-90秒）
5. 有话题性和讨论价值"""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.output_dir = output_dir or Path("./output/clips")
        self.llm = llm_client or LLMClient()
        ensure_dir(self.output_dir)

    def identify_clips(
        self,
        transcript_with_timestamps: str,
        max_clips: int = 10,
        min_duration: float = 15.0,
        max_duration: float = 90.0,
    ) -> List[VideoClip]:
        """
        识别值得提取的精华片段

        Args:
            transcript_with_timestamps: 带时间戳的转录文本
            max_clips: 最大片段数
            min_duration: 最短时长（秒）
            max_duration: 最长时长（秒）

        Returns:
            VideoClip 列表
        """
        logger.info("识别精华片段...")

        prompt = f"""分析以下播客转录文本，识别最值得提取为短视频的精华片段。

要求：
- 每个片段时长 {min_duration}-{max_duration} 秒
- 最多 {max_clips} 个片段
- 内容应该独立完整、精彩有价值

文本：
---
{transcript_with_timestamps[:35000]}
---

请按以下 JSON 格式输出：

```json
[
  {{
    "start_time": 123.5,
    "end_time": 178.5,
    "title": "片段标题（适合作为视频标题）",
    "description": "简短描述内容",
    "transcript": "这段的原文内容",
    "tags": ["标签1", "标签2"]
  }}
]
```

只输出 JSON。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.4)
            data = self.llm.parse_json_response(response)

            clips = []
            for item in data:
                clip = VideoClip(
                    start_time=float(item.get("start_time", 0)),
                    end_time=float(item.get("end_time", 0)),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    transcript=item.get("transcript", ""),
                    tags=item.get("tags", []),
                )
                clips.append(clip)

            logger.info(f"识别到 {len(clips)} 个精华片段")
            return clips

        except Exception as e:
            logger.error(f"识别片段失败: {e}")
            return []

    def extract_clip(
        self,
        video_path: Path,
        clip: VideoClip,
        add_subtitles: bool = True,
        subtitle_style: str = "modern",
    ) -> Path:
        """
        从视频中提取片段

        Args:
            video_path: 源视频路径
            clip: 片段信息
            add_subtitles: 是否添加字幕
            subtitle_style: 字幕样式

        Returns:
            输出视频路径
        """
        logger.info(f"提取片段: {clip.title}")

        output_path = self.output_dir / f"{self._sanitize_filename(clip.title)}.mp4"

        # 基础 ffmpeg 命令
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", str(clip.start_time),
            "-t", str(clip.duration),
            "-c:v", "libx264",
            "-c:a", "aac",
        ]

        # 添加字幕
        if add_subtitles and clip.transcript:
            srt_path = self._create_srt_file(clip)
            subtitle_filter = self._get_subtitle_filter(srt_path, subtitle_style)
            cmd.extend(["-vf", subtitle_filter])

        cmd.extend(["-y", str(output_path)])

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            clip.output_path = output_path
            logger.info(f"片段提取完成: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"片段提取失败: {e.stderr.decode()}")
            raise

    def extract_audio_clip(
        self,
        audio_path: Path,
        clip: VideoClip,
    ) -> Path:
        """
        从音频中提取片段

        Args:
            audio_path: 源音频路径
            clip: 片段信息

        Returns:
            输出音频路径
        """
        output_path = self.output_dir / f"{self._sanitize_filename(clip.title)}.mp3"

        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-ss", str(clip.start_time),
            "-t", str(clip.duration),
            "-c:a", "libmp3lame",
            "-q:a", "2",
            "-y", str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            clip.output_path = output_path
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"音频片段提取失败: {e.stderr.decode()}")
            raise

    def create_video_from_audio(
        self,
        audio_path: Path,
        clip: VideoClip,
        background_image: Optional[Path] = None,
        add_waveform: bool = True,
        add_subtitles: bool = True,
    ) -> Path:
        """
        从音频创建视频（带波形动画和字幕）

        Args:
            audio_path: 音频路径
            clip: 片段信息
            background_image: 背景图片
            add_waveform: 是否添加波形动画
            add_subtitles: 是否添加字幕

        Returns:
            输出视频路径
        """
        logger.info(f"从音频创建视频: {clip.title}")

        output_path = self.output_dir / f"{self._sanitize_filename(clip.title)}.mp4"

        # 构建滤镜
        filters = []

        # 背景
        if background_image and background_image.exists():
            # 使用背景图片
            input_bg = f"-loop 1 -i {background_image}"
        else:
            # 纯色背景
            filters.append("color=c=0x1a1a2e:s=1080x1920:d={duration}")

        # 波形动画
        if add_waveform:
            filters.append("showwaves=s=1080x200:mode=cline:colors=0x6366f1")

        # 这是一个简化的实现，完整实现需要更复杂的 ffmpeg 滤镜
        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-ss", str(clip.start_time),
            "-t", str(clip.duration),
            "-filter_complex",
            f"color=c=0x1a1a2e:s=1080x1920:d={clip.duration}[bg];"
            f"[0:a]showwaves=s=1080x200:mode=cline:colors=0x6366f1[wave];"
            f"[bg][wave]overlay=(W-w)/2:(H-h)/2[v]",
            "-map", "[v]",
            "-map", "0:a",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            "-y", str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            clip.output_path = output_path
            logger.info(f"视频创建完成: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"视频创建失败: {e.stderr.decode()}")
            # 回退到简单模式
            return self.extract_audio_clip(audio_path, clip)

    def _create_srt_file(self, clip: VideoClip) -> Path:
        """创建字幕文件"""
        srt_path = self.output_dir / f"{self._sanitize_filename(clip.title)}.srt"

        # 简单分句
        sentences = self._split_sentences(clip.transcript)

        lines = []
        duration_per_sentence = clip.duration / max(len(sentences), 1)

        for i, sentence in enumerate(sentences):
            start = i * duration_per_sentence
            end = (i + 1) * duration_per_sentence

            lines.append(str(i + 1))
            lines.append(f"{self._seconds_to_srt_time(start)} --> {self._seconds_to_srt_time(end)}")
            lines.append(sentence)
            lines.append("")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return srt_path

    def _split_sentences(self, text: str) -> List[str]:
        """分句"""
        import re
        # 按标点分句
        sentences = re.split(r'[。！？.!?]', text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_subtitle_filter(self, srt_path: Path, style: str) -> str:
        """获取字幕滤镜"""
        styles = {
            "modern": "Fontsize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2",
            "minimal": "Fontsize=20,PrimaryColour=&HFFFFFF,Outline=0",
            "bold": "Fontsize=28,PrimaryColour=&HFFFF00,OutlineColour=&H000000,Outline=3,Bold=1",
        }
        style_str = styles.get(style, styles["modern"])
        return f"subtitles={srt_path}:force_style='{style_str}'"

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """转换为 SRT 时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名"""
        import re
        clean = re.sub(r'[<>:"/\\|?*]', '', name)
        return clean[:50].strip()

    def batch_extract(
        self,
        media_path: Path,
        clips: List[VideoClip],
        **kwargs,
    ) -> List[Path]:
        """批量提取片段"""
        results = []
        is_video = media_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.webm']

        for clip in clips:
            try:
                if is_video:
                    path = self.extract_clip(media_path, clip, **kwargs)
                else:
                    path = self.create_video_from_audio(media_path, clip, **kwargs)
                results.append(path)
            except Exception as e:
                logger.error(f"提取片段失败 [{clip.title}]: {e}")

        return results
