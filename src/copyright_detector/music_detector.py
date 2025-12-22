"""
音乐检测器
检测播客中的背景音乐和音乐片段
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class MusicType(Enum):
    """音乐类型"""
    BACKGROUND = "background"  # 背景音乐
    INTRO_OUTRO = "intro_outro"  # 片头片尾
    TRANSITION = "transition"  # 转场音乐
    FULL_SONG = "full_song"  # 完整歌曲
    SNIPPET = "snippet"  # 音乐片段
    JINGLE = "jingle"  # 广告/品牌音乐


class MusicLicense(Enum):
    """音乐许可类型"""
    PUBLIC_DOMAIN = "public_domain"  # 公共领域
    CREATIVE_COMMONS = "creative_commons"  # CC许可
    ROYALTY_FREE = "royalty_free"  # 免版税
    LICENSED = "licensed"  # 已授权
    COPYRIGHTED = "copyrighted"  # 版权保护
    UNKNOWN = "unknown"  # 未知


@dataclass
class MusicSegment:
    """音乐片段"""
    start_time: float
    end_time: float
    music_type: MusicType
    confidence: float
    volume_level: float  # 相对于语音的音量
    is_vocal: bool
    genre: Optional[str] = None
    tempo: Optional[float] = None
    key: Optional[str] = None
    identified_track: Optional[Dict[str, str]] = None
    license_status: MusicLicense = MusicLicense.UNKNOWN


@dataclass
class MusicDetectionResult:
    """音乐检测结果"""
    total_duration: float
    music_duration: float
    music_percentage: float
    segments: List[MusicSegment]
    copyright_risk: str  # low, medium, high
    identified_tracks: List[Dict[str, Any]]
    recommendations: List[str]


class MusicDetector:
    """音乐检测器"""

    # 音乐特征阈值
    MUSIC_THRESHOLDS = {
        "spectral_flatness_min": 0.1,
        "spectral_flatness_max": 0.8,
        "onset_density_min": 0.5,
        "harmonic_ratio_min": 0.3,
        "rhythm_regularity_min": 0.4
    }

    def __init__(self):
        self.known_tracks: Dict[str, Dict[str, Any]] = {}
        self._load_known_tracks()

    def _load_known_tracks(self):
        """加载已知音乐库"""
        # 模拟音乐库
        self.known_tracks = {
            "track_001": {
                "title": "Inspiring Corporate",
                "artist": "Stock Music",
                "license": MusicLicense.ROYALTY_FREE,
                "genre": "corporate",
                "duration": 120
            },
            "track_002": {
                "title": "Popular Hit Song",
                "artist": "Famous Artist",
                "license": MusicLicense.COPYRIGHTED,
                "genre": "pop",
                "duration": 210
            }
        }

    def detect_music(
        self,
        audio_path: str,
        sensitivity: float = 0.5
    ) -> MusicDetectionResult:
        """
        检测音频中的音乐

        Args:
            audio_path: 音频文件路径
            sensitivity: 检测灵敏度 (0-1)

        Returns:
            音乐检测结果
        """
        # 获取音频时长
        total_duration = self._get_audio_duration(audio_path)

        # 检测音乐片段
        segments = self._detect_music_segments(audio_path, sensitivity)

        # 计算音乐总时长
        music_duration = sum(seg.end_time - seg.start_time for seg in segments)
        music_percentage = music_duration / total_duration * 100 if total_duration > 0 else 0

        # 识别已知曲目
        identified_tracks = self._identify_tracks(segments)

        # 评估版权风险
        copyright_risk = self._assess_risk(segments, identified_tracks)

        # 生成建议
        recommendations = self._generate_recommendations(
            segments, identified_tracks, copyright_risk
        )

        return MusicDetectionResult(
            total_duration=total_duration,
            music_duration=music_duration,
            music_percentage=music_percentage,
            segments=segments,
            copyright_risk=copyright_risk,
            identified_tracks=identified_tracks,
            recommendations=recommendations
        )

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        return 3600.0  # 模拟1小时

    def _detect_music_segments(
        self,
        audio_path: str,
        sensitivity: float
    ) -> List[MusicSegment]:
        """检测音乐片段"""
        segments = []

        # 模拟音乐检测
        # 实际实现需要使用音频分析库

        # 模拟检测结果
        simulated_segments = [
            # 片头音乐
            {
                "start": 0, "end": 15,
                "type": MusicType.INTRO_OUTRO,
                "confidence": 0.95,
                "volume": 0.8,
                "vocal": False
            },
            # 转场音乐
            {
                "start": 900, "end": 908,
                "type": MusicType.TRANSITION,
                "confidence": 0.85,
                "volume": 0.5,
                "vocal": False
            },
            # 背景音乐
            {
                "start": 1200, "end": 1320,
                "type": MusicType.BACKGROUND,
                "confidence": 0.7,
                "volume": 0.2,
                "vocal": False
            },
            # 片尾音乐
            {
                "start": 3540, "end": 3600,
                "type": MusicType.INTRO_OUTRO,
                "confidence": 0.95,
                "volume": 0.8,
                "vocal": False
            }
        ]

        for seg_data in simulated_segments:
            if seg_data["confidence"] >= (1 - sensitivity):
                segment = MusicSegment(
                    start_time=seg_data["start"],
                    end_time=seg_data["end"],
                    music_type=seg_data["type"],
                    confidence=seg_data["confidence"],
                    volume_level=seg_data["volume"],
                    is_vocal=seg_data["vocal"],
                    genre=self._detect_genre(seg_data),
                    tempo=self._detect_tempo(seg_data),
                    key=self._detect_key(seg_data)
                )
                segments.append(segment)

        return segments

    def _detect_genre(self, segment_data: Dict[str, Any]) -> str:
        """检测音乐流派"""
        genres = ["pop", "rock", "electronic", "ambient", "corporate", "classical"]
        return np.random.choice(genres)

    def _detect_tempo(self, segment_data: Dict[str, Any]) -> float:
        """检测BPM"""
        return np.random.uniform(80, 140)

    def _detect_key(self, segment_data: Dict[str, Any]) -> str:
        """检测调式"""
        keys = ["C major", "G major", "D major", "A minor", "E minor"]
        return np.random.choice(keys)

    def _identify_tracks(
        self,
        segments: List[MusicSegment]
    ) -> List[Dict[str, Any]]:
        """识别已知曲目"""
        identified = []

        for segment in segments:
            # 模拟曲目识别
            # 实际实现需要使用音频指纹匹配

            if segment.music_type in [MusicType.FULL_SONG, MusicType.INTRO_OUTRO]:
                # 随机匹配一个已知曲目
                if np.random.random() > 0.5:
                    track_id = np.random.choice(list(self.known_tracks.keys()))
                    track = self.known_tracks[track_id]

                    identified.append({
                        "segment_start": segment.start_time,
                        "segment_end": segment.end_time,
                        "track_id": track_id,
                        "title": track["title"],
                        "artist": track["artist"],
                        "license": track["license"].value,
                        "confidence": segment.confidence * 0.9
                    })

                    # 更新片段的识别信息
                    segment.identified_track = {
                        "title": track["title"],
                        "artist": track["artist"]
                    }
                    segment.license_status = track["license"]

        return identified

    def _assess_risk(
        self,
        segments: List[MusicSegment],
        identified_tracks: List[Dict[str, Any]]
    ) -> str:
        """评估版权风险"""
        # 检查是否有版权保护的音乐
        copyrighted_count = sum(
            1 for seg in segments
            if seg.license_status == MusicLicense.COPYRIGHTED
        )

        # 检查音乐总时长
        total_music_duration = sum(seg.end_time - seg.start_time for seg in segments)

        if copyrighted_count > 0:
            return "high"
        elif total_music_duration > 300 or len(segments) > 5:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        segments: List[MusicSegment],
        identified_tracks: List[Dict[str, Any]],
        risk_level: str
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        if risk_level == "high":
            recommendations.append("⚠️ 检测到版权保护的音乐，建议移除或获取授权")

        # 检查每个片段
        for segment in segments:
            if segment.license_status == MusicLicense.COPYRIGHTED:
                recommendations.append(
                    f"🔴 {segment.start_time:.0f}-{segment.end_time:.0f}秒: "
                    f"版权音乐「{segment.identified_track.get('title', '未知')}」"
                )
            elif segment.license_status == MusicLicense.UNKNOWN:
                recommendations.append(
                    f"🟡 {segment.start_time:.0f}-{segment.end_time:.0f}秒: "
                    f"未识别的音乐，建议确认版权状态"
                )

        if not recommendations:
            recommendations.append("✅ 未检测到明显的版权风险")

        # 通用建议
        recommendations.append("💡 建议使用免版税音乐库（如Epidemic Sound, Artlist）")

        return recommendations

    def analyze_music_usage(
        self,
        segments: List[MusicSegment]
    ) -> Dict[str, Any]:
        """分析音乐使用情况"""
        # 按类型统计
        by_type = {}
        for seg in segments:
            type_name = seg.music_type.value
            if type_name not in by_type:
                by_type[type_name] = {"count": 0, "duration": 0}
            by_type[type_name]["count"] += 1
            by_type[type_name]["duration"] += seg.end_time - seg.start_time

        # 按许可统计
        by_license = {}
        for seg in segments:
            license_name = seg.license_status.value
            if license_name not in by_license:
                by_license[license_name] = {"count": 0, "duration": 0}
            by_license[license_name]["count"] += 1
            by_license[license_name]["duration"] += seg.end_time - seg.start_time

        return {
            "total_segments": len(segments),
            "by_type": by_type,
            "by_license": by_license,
            "avg_volume": np.mean([seg.volume_level for seg in segments]) if segments else 0,
            "vocal_segments": sum(1 for seg in segments if seg.is_vocal),
            "genres_detected": list(set(seg.genre for seg in segments if seg.genre))
        }
