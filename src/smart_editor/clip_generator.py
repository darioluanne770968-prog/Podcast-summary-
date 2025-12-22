"""
片段生成器
自动生成社交媒体分享的短片段
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json


class OutputFormat(Enum):
    """输出格式"""
    VERTICAL_9_16 = "9:16"  # TikTok, Reels, Shorts
    SQUARE_1_1 = "1:1"  # Instagram Feed
    HORIZONTAL_16_9 = "16:9"  # YouTube, 横屏
    HORIZONTAL_4_3 = "4:3"  # 传统视频
    STORY_9_16 = "9:16_story"  # Instagram/Facebook Story


class CaptionStyle(Enum):
    """字幕样式"""
    MINIMAL = "minimal"  # 简约
    BOLD = "bold"  # 粗体突出
    ANIMATED = "animated"  # 动画效果
    KARAOKE = "karaoke"  # 卡拉OK式
    HIGHLIGHT = "highlight"  # 高亮关键词
    GRADIENT = "gradient"  # 渐变色
    OUTLINE = "outline"  # 描边


@dataclass
class ClipConfig:
    """片段配置"""
    output_format: OutputFormat = OutputFormat.VERTICAL_9_16
    caption_style: CaptionStyle = CaptionStyle.BOLD
    add_captions: bool = True
    add_progress_bar: bool = True
    add_watermark: bool = True
    watermark_text: str = ""
    background_music: Optional[str] = None
    music_volume: float = 0.2
    fade_in_duration: float = 0.5
    fade_out_duration: float = 0.5
    output_quality: str = "high"  # low, medium, high, ultra
    output_fps: int = 30
    max_file_size_mb: Optional[float] = None


@dataclass
class GeneratedClip:
    """生成的片段"""
    id: str
    source_highlight_id: str
    output_path: str
    format: OutputFormat
    duration: float
    file_size_bytes: int
    resolution: Tuple[int, int]
    has_captions: bool
    caption_text: str
    thumbnail_path: Optional[str] = None
    preview_gif_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClipGenerator:
    """片段生成器"""

    # 各平台推荐配置
    PLATFORM_PRESETS = {
        "tiktok": {
            "format": OutputFormat.VERTICAL_9_16,
            "resolution": (1080, 1920),
            "max_duration": 60,
            "caption_style": CaptionStyle.ANIMATED,
            "fps": 30
        },
        "instagram_reels": {
            "format": OutputFormat.VERTICAL_9_16,
            "resolution": (1080, 1920),
            "max_duration": 90,
            "caption_style": CaptionStyle.BOLD,
            "fps": 30
        },
        "youtube_shorts": {
            "format": OutputFormat.VERTICAL_9_16,
            "resolution": (1080, 1920),
            "max_duration": 60,
            "caption_style": CaptionStyle.HIGHLIGHT,
            "fps": 30
        },
        "twitter": {
            "format": OutputFormat.HORIZONTAL_16_9,
            "resolution": (1280, 720),
            "max_duration": 140,
            "caption_style": CaptionStyle.MINIMAL,
            "fps": 30
        },
        "linkedin": {
            "format": OutputFormat.HORIZONTAL_16_9,
            "resolution": (1920, 1080),
            "max_duration": 600,
            "caption_style": CaptionStyle.MINIMAL,
            "fps": 24
        },
        "wechat": {
            "format": OutputFormat.VERTICAL_9_16,
            "resolution": (1080, 1920),
            "max_duration": 300,
            "caption_style": CaptionStyle.BOLD,
            "fps": 30
        },
        "douyin": {
            "format": OutputFormat.VERTICAL_9_16,
            "resolution": (1080, 1920),
            "max_duration": 60,
            "caption_style": CaptionStyle.KARAOKE,
            "fps": 30
        },
        "xiaohongshu": {
            "format": OutputFormat.VERTICAL_9_16,
            "resolution": (1080, 1440),
            "max_duration": 300,
            "caption_style": CaptionStyle.GRADIENT,
            "fps": 30
        }
    }

    def __init__(self, config: Optional[ClipConfig] = None):
        self.config = config or ClipConfig()
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        """加载视频模板"""
        return {
            "podcast_clip": {
                "background": "gradient",
                "audio_visualizer": True,
                "speaker_image": True,
                "caption_position": "center"
            },
            "quote_card": {
                "background": "solid_color",
                "text_animation": "typewriter",
                "speaker_name": True,
                "caption_position": "center"
            },
            "audiogram": {
                "background": "waveform",
                "audio_visualizer": True,
                "podcast_cover": True,
                "caption_position": "bottom"
            },
            "highlight_reel": {
                "background": "dynamic",
                "transitions": "smooth",
                "music_sync": True,
                "caption_position": "bottom"
            }
        }

    def generate_clip(
        self,
        audio_path: str,
        start_time: float,
        end_time: float,
        transcript: str,
        output_dir: str,
        template: str = "podcast_clip",
        platform: Optional[str] = None
    ) -> GeneratedClip:
        """
        生成视频片段

        Args:
            audio_path: 音频文件路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            transcript: 转录文本
            output_dir: 输出目录
            template: 使用的模板
            platform: 目标平台（使用预设配置）

        Returns:
            生成的片段信息
        """
        # 如果指定了平台，使用预设配置
        if platform and platform in self.PLATFORM_PRESETS:
            preset = self.PLATFORM_PRESETS[platform]
            self.config.output_format = preset["format"]
            resolution = preset["resolution"]
            self.config.caption_style = preset["caption_style"]
            self.config.output_fps = preset["fps"]
        else:
            resolution = self._get_resolution(self.config.output_format)

        duration = end_time - start_time

        # 创建视频处理管道
        pipeline = self._create_pipeline(template)

        # 提取音频片段
        audio_segment = self._extract_audio_segment(audio_path, start_time, end_time)

        # 生成字幕
        captions = self._generate_captions(transcript, duration) if self.config.add_captions else None

        # 创建视觉内容
        visual_content = self._create_visual_content(
            template=template,
            duration=duration,
            resolution=resolution,
            audio_segment=audio_segment
        )

        # 合成视频
        output_path = Path(output_dir) / f"clip_{start_time}_{end_time}.mp4"

        video_data = self._render_video(
            visual_content=visual_content,
            audio_segment=audio_segment,
            captions=captions,
            output_path=str(output_path),
            resolution=resolution
        )

        # 生成缩略图
        thumbnail_path = self._generate_thumbnail(str(output_path), output_dir)

        # 生成预览GIF
        preview_gif_path = self._generate_preview_gif(str(output_path), output_dir)

        return GeneratedClip(
            id=f"clip_{start_time}_{end_time}",
            source_highlight_id=f"highlight_{start_time}",
            output_path=str(output_path),
            format=self.config.output_format,
            duration=duration,
            file_size_bytes=video_data.get("file_size", 0),
            resolution=resolution,
            has_captions=self.config.add_captions,
            caption_text=transcript,
            thumbnail_path=thumbnail_path,
            preview_gif_path=preview_gif_path,
            metadata={
                "template": template,
                "platform": platform,
                "quality": self.config.output_quality,
                "fps": self.config.output_fps
            }
        )

    def _get_resolution(self, format: OutputFormat) -> Tuple[int, int]:
        """获取分辨率"""
        resolutions = {
            OutputFormat.VERTICAL_9_16: (1080, 1920),
            OutputFormat.SQUARE_1_1: (1080, 1080),
            OutputFormat.HORIZONTAL_16_9: (1920, 1080),
            OutputFormat.HORIZONTAL_4_3: (1440, 1080),
            OutputFormat.STORY_9_16: (1080, 1920)
        }
        return resolutions.get(format, (1080, 1920))

    def _create_pipeline(self, template: str) -> Dict[str, Any]:
        """创建视频处理管道"""
        template_config = self.templates.get(template, self.templates["podcast_clip"])

        return {
            "stages": [
                {"name": "audio_extraction", "enabled": True},
                {"name": "visual_generation", "enabled": True, "config": template_config},
                {"name": "caption_overlay", "enabled": self.config.add_captions},
                {"name": "watermark", "enabled": self.config.add_watermark},
                {"name": "audio_mixing", "enabled": True},
                {"name": "encoding", "enabled": True}
            ]
        }

    def _extract_audio_segment(
        self,
        audio_path: str,
        start_time: float,
        end_time: float
    ) -> Dict[str, Any]:
        """提取音频片段"""
        return {
            "source": audio_path,
            "start": start_time,
            "end": end_time,
            "duration": end_time - start_time,
            "format": "wav",
            "sample_rate": 44100,
            "channels": 2
        }

    def _generate_captions(self, transcript: str, duration: float) -> List[Dict[str, Any]]:
        """生成字幕"""
        words = transcript.split()
        if not words:
            return []

        # 计算每个词的显示时间
        time_per_word = duration / len(words)

        captions = []
        current_time = 0
        chunk_size = 5  # 每次显示5个词

        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            text = " ".join(chunk)

            captions.append({
                "text": text,
                "start_time": current_time,
                "end_time": current_time + time_per_word * len(chunk),
                "style": self.config.caption_style.value,
                "position": "center",
                "animation": self._get_caption_animation()
            })

            current_time += time_per_word * len(chunk)

        return captions

    def _get_caption_animation(self) -> Dict[str, Any]:
        """获取字幕动画配置"""
        animations = {
            CaptionStyle.MINIMAL: {"type": "fade", "duration": 0.2},
            CaptionStyle.BOLD: {"type": "pop", "duration": 0.15},
            CaptionStyle.ANIMATED: {"type": "bounce", "duration": 0.3},
            CaptionStyle.KARAOKE: {"type": "highlight_word", "duration": 0.1},
            CaptionStyle.HIGHLIGHT: {"type": "glow", "duration": 0.2},
            CaptionStyle.GRADIENT: {"type": "color_shift", "duration": 0.5},
            CaptionStyle.OUTLINE: {"type": "stroke", "duration": 0.15}
        }
        return animations.get(self.config.caption_style, {"type": "fade", "duration": 0.2})

    def _create_visual_content(
        self,
        template: str,
        duration: float,
        resolution: Tuple[int, int],
        audio_segment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建视觉内容"""
        template_config = self.templates.get(template, {})

        return {
            "template": template,
            "duration": duration,
            "resolution": resolution,
            "layers": [
                {
                    "type": "background",
                    "style": template_config.get("background", "gradient"),
                    "colors": ["#1a1a2e", "#16213e", "#0f3460"]
                },
                {
                    "type": "audio_visualizer",
                    "enabled": template_config.get("audio_visualizer", True),
                    "style": "waveform",
                    "color": "#00d4ff",
                    "position": "center"
                },
                {
                    "type": "speaker_image",
                    "enabled": template_config.get("speaker_image", False),
                    "position": "top_center",
                    "size": 0.3
                },
                {
                    "type": "progress_bar",
                    "enabled": self.config.add_progress_bar,
                    "position": "bottom",
                    "color": "#00d4ff"
                }
            ],
            "transitions": {
                "fade_in": self.config.fade_in_duration,
                "fade_out": self.config.fade_out_duration
            }
        }

    def _render_video(
        self,
        visual_content: Dict[str, Any],
        audio_segment: Dict[str, Any],
        captions: Optional[List[Dict[str, Any]]],
        output_path: str,
        resolution: Tuple[int, int]
    ) -> Dict[str, Any]:
        """渲染视频"""
        # 模拟视频渲染过程
        return {
            "output_path": output_path,
            "file_size": int(audio_segment["duration"] * 500000),  # 估算文件大小
            "resolution": resolution,
            "fps": self.config.output_fps,
            "bitrate": "5000k" if self.config.output_quality == "high" else "2500k",
            "codec": "h264",
            "render_time": audio_segment["duration"] * 0.5
        }

    def _generate_thumbnail(self, video_path: str, output_dir: str) -> str:
        """生成缩略图"""
        thumbnail_path = Path(output_dir) / f"{Path(video_path).stem}_thumb.jpg"
        return str(thumbnail_path)

    def _generate_preview_gif(self, video_path: str, output_dir: str) -> str:
        """生成预览GIF"""
        gif_path = Path(output_dir) / f"{Path(video_path).stem}_preview.gif"
        return str(gif_path)

    def batch_generate(
        self,
        audio_path: str,
        highlights: List[Dict[str, Any]],
        output_dir: str,
        platforms: List[str]
    ) -> List[GeneratedClip]:
        """
        批量生成多平台片段

        Args:
            audio_path: 音频文件路径
            highlights: 精彩片段列表
            output_dir: 输出目录
            platforms: 目标平台列表

        Returns:
            生成的片段列表
        """
        clips = []

        for highlight in highlights:
            for platform in platforms:
                # 为每个平台创建子目录
                platform_dir = Path(output_dir) / platform
                platform_dir.mkdir(parents=True, exist_ok=True)

                clip = self.generate_clip(
                    audio_path=audio_path,
                    start_time=highlight["start_time"],
                    end_time=highlight["end_time"],
                    transcript=highlight.get("transcript", ""),
                    output_dir=str(platform_dir),
                    platform=platform
                )
                clips.append(clip)

        return clips

    def create_compilation(
        self,
        clips: List[GeneratedClip],
        output_path: str,
        transition_style: str = "smooth",
        add_intro: bool = True,
        add_outro: bool = True
    ) -> Dict[str, Any]:
        """
        创建精彩合集

        Args:
            clips: 片段列表
            output_path: 输出路径
            transition_style: 转场风格
            add_intro: 是否添加片头
            add_outro: 是否添加片尾

        Returns:
            合集信息
        """
        total_duration = sum(clip.duration for clip in clips)

        # 添加转场时间
        transition_duration = 0.5
        total_duration += (len(clips) - 1) * transition_duration

        # 添加片头片尾
        if add_intro:
            total_duration += 3.0
        if add_outro:
            total_duration += 3.0

        return {
            "output_path": output_path,
            "total_duration": total_duration,
            "clip_count": len(clips),
            "transition_style": transition_style,
            "has_intro": add_intro,
            "has_outro": add_outro,
            "file_size_estimate": int(total_duration * 500000)
        }

    def export_metadata(self, clips: List[GeneratedClip], output_path: str):
        """导出片段元数据"""
        metadata = {
            "clips": [
                {
                    "id": clip.id,
                    "output_path": clip.output_path,
                    "format": clip.format.value,
                    "duration": clip.duration,
                    "resolution": clip.resolution,
                    "caption_text": clip.caption_text,
                    "thumbnail": clip.thumbnail_path,
                    "preview_gif": clip.preview_gif_path,
                    "metadata": clip.metadata
                }
                for clip in clips
            ],
            "total_clips": len(clips),
            "platforms": list(set(clip.metadata.get("platform", "unknown") for clip in clips))
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
