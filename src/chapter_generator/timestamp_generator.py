"""时间戳生成器"""
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class Timestamp:
    time: float
    label: str
    time_str: str


class TimestampGenerator:
    """时间戳生成器"""

    def generate(self, chapters: List[Dict]) -> List[Timestamp]:
        """生成时间戳"""
        timestamps = []
        for chapter in chapters:
            time = chapter.get("start_time", 0)
            timestamps.append(Timestamp(
                time=time,
                label=chapter.get("title", ""),
                time_str=self._format_time(time)
            ))
        return timestamps

    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def export_to_description(self, timestamps: List[Timestamp]) -> str:
        """导出为描述格式"""
        return "\n".join(f"{ts.time_str} {ts.label}" for ts in timestamps)
