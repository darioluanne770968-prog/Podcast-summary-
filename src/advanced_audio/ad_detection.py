"""
广告检测模块

自动检测播客中的广告片段
"""

from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass
import json

from ..utils import get_logger, ensure_dir, format_timestamp
from ..analysis import LLMClient

logger = get_logger(__name__)


@dataclass
class AdSegment:
    """广告片段"""
    start_time: float
    end_time: float
    confidence: float
    ad_type: str  # sponsor, self-promo, intro, outro
    description: Optional[str] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def start_formatted(self) -> str:
        return format_timestamp(self.start_time)

    @property
    def end_formatted(self) -> str:
        return format_timestamp(self.end_time)

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "start_formatted": self.start_formatted,
            "end_formatted": self.end_formatted,
            "duration": self.duration,
            "confidence": self.confidence,
            "ad_type": self.ad_type,
            "description": self.description,
        }


class AdDetector:
    """广告检测器"""

    AD_INDICATORS = [
        # 中文广告标志词
        "本期节目由", "感谢", "赞助", "广告", "推广", "优惠码",
        "折扣", "链接在", "描述栏", "使用我的", "专属",
        # 英文广告标志词
        "sponsored by", "brought to you by", "promo code",
        "discount", "check out", "use my link", "affiliate",
        "this episode is", "today's sponsor",
    ]

    SYSTEM_PROMPT = """你是一个播客广告检测专家。分析播客转录文本，识别其中的广告片段。

广告类型包括：
1. sponsor - 赞助商广告
2. self-promo - 自我推广（其他节目、社交媒体等）
3. intro - 片头广告
4. outro - 片尾广告
5. mid-roll - 中插广告

请仔细分析文本，识别广告的起止位置。"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def detect(
        self,
        transcript_with_timestamps: str,
        audio_fingerprint: bool = False,
    ) -> List[AdSegment]:
        """
        检测广告片段

        Args:
            transcript_with_timestamps: 带时间戳的转录文本
            audio_fingerprint: 是否使用音频指纹匹配

        Returns:
            AdSegment 列表
        """
        logger.info("开始广告检测...")

        # 1. 基于关键词的快速检测
        keyword_segments = self._detect_by_keywords(transcript_with_timestamps)

        # 2. 使用 LLM 进行精确检测
        llm_segments = self._detect_by_llm(transcript_with_timestamps)

        # 3. 合并结果
        all_segments = self._merge_detections(keyword_segments, llm_segments)

        logger.info(f"检测到 {len(all_segments)} 个广告片段")
        return all_segments

    def _detect_by_keywords(self, transcript: str) -> List[AdSegment]:
        """基于关键词检测"""
        segments = []
        lines = transcript.split("\n")

        for i, line in enumerate(lines):
            # 检查是否包含广告标志词
            line_lower = line.lower()
            for indicator in self.AD_INDICATORS:
                if indicator.lower() in line_lower:
                    # 解析时间戳
                    timestamp = self._parse_timestamp_from_line(line)
                    if timestamp is not None:
                        # 估计广告时长（通常30-90秒）
                        segments.append(AdSegment(
                            start_time=timestamp,
                            end_time=timestamp + 60,  # 假设60秒
                            confidence=0.6,
                            ad_type="sponsor",
                            description=f"关键词检测: {indicator}",
                        ))
                    break

        return segments

    def _detect_by_llm(self, transcript: str) -> List[AdSegment]:
        """使用 LLM 检测"""
        prompt = f"""分析以下播客转录文本，识别所有广告片段。

文本：
---
{transcript[:30000]}
---

请按以下 JSON 格式输出检测到的广告片段：

```json
[
  {{
    "start_time": 123.5,
    "end_time": 183.5,
    "ad_type": "sponsor",
    "confidence": 0.9,
    "description": "简短描述广告内容"
  }}
]
```

如果没有检测到广告，返回空数组 []。
只输出 JSON，不要其他内容。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.2)
            data = self.llm.parse_json_response(response)

            segments = []
            for item in data:
                segments.append(AdSegment(
                    start_time=float(item.get("start_time", 0)),
                    end_time=float(item.get("end_time", 0)),
                    confidence=float(item.get("confidence", 0.8)),
                    ad_type=item.get("ad_type", "sponsor"),
                    description=item.get("description"),
                ))
            return segments

        except Exception as e:
            logger.error(f"LLM 广告检测失败: {e}")
            return []

    def _merge_detections(
        self,
        keyword_segments: List[AdSegment],
        llm_segments: List[AdSegment],
    ) -> List[AdSegment]:
        """合并检测结果"""
        all_segments = []

        # 优先使用 LLM 检测结果
        for llm_seg in llm_segments:
            # 检查是否与关键词检测重叠
            overlapping = False
            for kw_seg in keyword_segments:
                if self._segments_overlap(llm_seg, kw_seg):
                    # 提高置信度
                    llm_seg.confidence = min(1.0, llm_seg.confidence + 0.2)
                    overlapping = True
                    break

            all_segments.append(llm_seg)

        # 添加独立的关键词检测结果
        for kw_seg in keyword_segments:
            if not any(self._segments_overlap(kw_seg, s) for s in all_segments):
                all_segments.append(kw_seg)

        # 按时间排序
        all_segments.sort(key=lambda x: x.start_time)

        return all_segments

    def _segments_overlap(self, seg1: AdSegment, seg2: AdSegment) -> bool:
        """检查两个片段是否重叠"""
        return not (seg1.end_time < seg2.start_time or seg2.end_time < seg1.start_time)

    def _parse_timestamp_from_line(self, line: str) -> Optional[float]:
        """从行中解析时间戳"""
        import re
        match = re.search(r"\[(\d+):(\d+):?(\d+)?\]", line)
        if match:
            parts = match.groups()
            if parts[2]:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
        return None

    def remove_ads_from_audio(
        self,
        audio_path: Path,
        ad_segments: List[AdSegment],
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        从音频中移除广告片段

        Args:
            audio_path: 输入音频路径
            ad_segments: 广告片段列表
            output_path: 输出路径

        Returns:
            处理后的音频路径
        """
        from pydub import AudioSegment

        logger.info(f"移除 {len(ad_segments)} 个广告片段...")

        audio = AudioSegment.from_file(str(audio_path))
        output_path = output_path or audio_path.with_stem(f"{audio_path.stem}_no_ads")

        # 构建非广告片段列表
        keep_segments = []
        current_time = 0

        for ad in sorted(ad_segments, key=lambda x: x.start_time):
            if current_time < ad.start_time * 1000:
                keep_segments.append((current_time, ad.start_time * 1000))
            current_time = ad.end_time * 1000

        # 添加最后一段
        if current_time < len(audio):
            keep_segments.append((current_time, len(audio)))

        # 拼接保留的片段
        result = AudioSegment.empty()
        for start, end in keep_segments:
            result += audio[int(start):int(end)]

        # 导出
        result.export(str(output_path), format=output_path.suffix.lstrip(".") or "mp3")

        logger.info(f"广告移除完成: {output_path}")
        return output_path

    def generate_skip_chapters(self, ad_segments: List[AdSegment]) -> str:
        """
        生成跳过广告的章节标记（YouTube 格式）

        可用于视频播放器自动跳过
        """
        lines = ["# 非广告内容章节\n"]
        current_time = 0

        for i, ad in enumerate(sorted(ad_segments, key=lambda x: x.start_time)):
            if current_time < ad.start_time:
                lines.append(f"{format_timestamp(current_time)} 正片内容")
            lines.append(f"{ad.start_formatted} [广告] {ad.description or ad.ad_type}")
            current_time = ad.end_time

        return "\n".join(lines)
