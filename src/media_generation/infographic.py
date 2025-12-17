"""
信息图表生成模块

生成数据可视化和信息图
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


class InfographicGenerator:
    """信息图表生成器"""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("./output/infographics")
        ensure_dir(self.output_dir)

    def generate_stats_card(
        self,
        title: str,
        stats: Dict[str, any],
    ) -> str:
        """
        生成统计卡片（SVG）

        Args:
            title: 标题
            stats: 统计数据

        Returns:
            SVG 字符串
        """
        height = 120 + len(stats) * 60

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#1a1a2e"/>
            <stop offset="100%" style="stop-color:#16213e"/>
        </linearGradient>
    </defs>

    <rect width="100%" height="100%" rx="16" fill="url(#cardBg)"/>

    <text x="20" y="40" font-family="Arial" font-size="20" font-weight="bold" fill="#ffffff">
        {title}
    </text>
    <line x1="20" y1="55" x2="380" y2="55" stroke="#6366f1" stroke-width="2"/>
'''

        y = 90
        for key, value in stats.items():
            svg += f'''
    <text x="20" y="{y}" font-family="Arial" font-size="14" fill="#a0a0a0">{key}</text>
    <text x="380" y="{y}" font-family="Arial" font-size="18" font-weight="bold" fill="#6366f1" text-anchor="end">{value}</text>
'''
            y += 50

        svg += '</svg>'
        return svg

    def generate_timeline(
        self,
        title: str,
        events: List[Dict],
    ) -> str:
        """
        生成时间线图（SVG）

        Args:
            title: 标题
            events: 事件列表 [{"time": "00:00", "title": "...", "desc": "..."}]

        Returns:
            SVG 字符串
        """
        height = 100 + len(events) * 100

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="600" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#0f172a"/>

    <text x="300" y="40" font-family="Arial" font-size="24" font-weight="bold" fill="#ffffff" text-anchor="middle">
        {title}
    </text>

    <!-- 时间线 -->
    <line x1="100" y1="70" x2="100" y2="{height - 30}" stroke="#6366f1" stroke-width="3"/>
'''

        y = 100
        for i, event in enumerate(events):
            svg += f'''
    <!-- 事件 {i+1} -->
    <circle cx="100" cy="{y}" r="10" fill="#6366f1"/>
    <text x="120" y="{y - 10}" font-family="Arial" font-size="12" fill="#6366f1">{event.get('time', '')}</text>
    <text x="120" y="{y + 5}" font-family="Arial" font-size="16" font-weight="bold" fill="#ffffff">{event.get('title', '')[:40]}</text>
    <text x="120" y="{y + 25}" font-family="Arial" font-size="12" fill="#a0a0a0">{event.get('desc', '')[:60]}</text>
'''
            y += 100

        svg += '</svg>'
        return svg

    def generate_pie_chart(
        self,
        title: str,
        data: Dict[str, float],
    ) -> str:
        """
        生成饼图（SVG）

        Args:
            title: 标题
            data: 数据 {"label": percentage}

        Returns:
            SVG 字符串
        """
        colors = ["#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899", "#f43f5e"]

        svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="400" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#0f172a"/>
'''
        svg += f'<text x="250" y="30" font-family="Arial" font-size="20" font-weight="bold" fill="#ffffff" text-anchor="middle">{title}</text>'

        # 计算饼图
        cx, cy, r = 180, 200, 120
        total = sum(data.values())
        start_angle = 0

        for i, (label, value) in enumerate(data.items()):
            percentage = value / total if total > 0 else 0
            angle = percentage * 360
            end_angle = start_angle + angle

            # 计算路径
            large_arc = 1 if angle > 180 else 0
            start_x = cx + r * __import__('math').cos(__import__('math').radians(start_angle - 90))
            start_y = cy + r * __import__('math').sin(__import__('math').radians(start_angle - 90))
            end_x = cx + r * __import__('math').cos(__import__('math').radians(end_angle - 90))
            end_y = cy + r * __import__('math').sin(__import__('math').radians(end_angle - 90))

            color = colors[i % len(colors)]

            svg += f'''
    <path d="M {cx} {cy} L {start_x} {start_y} A {r} {r} 0 {large_arc} 1 {end_x} {end_y} Z" fill="{color}"/>
'''
            start_angle = end_angle

        # 图例
        legend_y = 80
        for i, (label, value) in enumerate(data.items()):
            color = colors[i % len(colors)]
            percentage = value / total * 100 if total > 0 else 0
            svg += f'''
    <rect x="350" y="{legend_y}" width="16" height="16" fill="{color}"/>
    <text x="375" y="{legend_y + 13}" font-family="Arial" font-size="12" fill="#ffffff">{label} ({percentage:.1f}%)</text>
'''
            legend_y += 25

        svg += '</svg>'
        return svg

    def generate_bar_chart(
        self,
        title: str,
        data: Dict[str, float],
        max_value: float = None,
    ) -> str:
        """
        生成条形图（SVG）

        Args:
            title: 标题
            data: 数据
            max_value: 最大值（用于缩放）

        Returns:
            SVG 字符串
        """
        if max_value is None:
            max_value = max(data.values()) if data else 100

        height = 100 + len(data) * 50

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="500" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#0f172a"/>
    <text x="250" y="35" font-family="Arial" font-size="20" font-weight="bold" fill="#ffffff" text-anchor="middle">{title}</text>
'''

        y = 70
        bar_max_width = 300

        for label, value in data.items():
            bar_width = (value / max_value) * bar_max_width if max_value > 0 else 0
            percentage = (value / max_value) * 100 if max_value > 0 else 0

            svg += f'''
    <text x="10" y="{y + 15}" font-family="Arial" font-size="12" fill="#ffffff">{label[:20]}</text>
    <rect x="150" y="{y}" width="{bar_width}" height="25" rx="4" fill="#6366f1"/>
    <text x="{160 + bar_width}" y="{y + 17}" font-family="Arial" font-size="12" fill="#a0a0a0">{value} ({percentage:.0f}%)</text>
'''
            y += 45

        svg += '</svg>'
        return svg

    def save_svg(self, svg_content: str, filename: str) -> Path:
        """保存 SVG 文件"""
        output_path = self.output_dir / f"{filename}.svg"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        logger.info(f"图表保存完成: {output_path}")
        return output_path

    def generate_summary_infographic(
        self,
        title: str,
        duration: str,
        key_points: List[str],
        stats: Dict[str, any],
    ) -> str:
        """
        生成摘要信息图

        Args:
            title: 标题
            duration: 时长
            key_points: 核心要点
            stats: 统计数据

        Returns:
            SVG 字符串
        """
        height = 500 + len(key_points) * 40

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#6366f1"/>
            <stop offset="100%" style="stop-color:#8b5cf6"/>
        </linearGradient>
    </defs>

    <!-- 背景 -->
    <rect width="100%" height="100%" fill="#0f172a"/>

    <!-- 头部 -->
    <rect width="100%" height="120" fill="url(#headerGrad)"/>
    <text x="400" y="50" font-family="Arial" font-size="28" font-weight="bold" fill="#ffffff" text-anchor="middle">🎙️ 播客摘要</text>
    <text x="400" y="85" font-family="Arial" font-size="18" fill="#ffffff" text-anchor="middle" opacity="0.9">{title[:50]}</text>
    <text x="400" y="110" font-family="Arial" font-size="14" fill="#ffffff" text-anchor="middle" opacity="0.7">时长: {duration}</text>

    <!-- 核心要点 -->
    <text x="40" y="160" font-family="Arial" font-size="18" font-weight="bold" fill="#ffffff">📌 核心要点</text>
'''

        y = 190
        for i, point in enumerate(key_points[:8], 1):
            svg += f'''
    <circle cx="50" cy="{y}" r="12" fill="#6366f1"/>
    <text x="50" y="{y + 5}" font-family="Arial" font-size="12" fill="#ffffff" text-anchor="middle">{i}</text>
    <text x="75" y="{y + 5}" font-family="Arial" font-size="14" fill="#e2e8f0">{point[:70]}</text>
'''
            y += 40

        # 统计数据
        svg += f'''
    <text x="40" y="{y + 30}" font-family="Arial" font-size="18" font-weight="bold" fill="#ffffff">📊 统计数据</text>
'''
        stat_x = 60
        for key, value in list(stats.items())[:4]:
            svg += f'''
    <rect x="{stat_x}" y="{y + 50}" width="160" height="80" rx="8" fill="#1e293b"/>
    <text x="{stat_x + 80}" y="{y + 85}" font-family="Arial" font-size="24" font-weight="bold" fill="#6366f1" text-anchor="middle">{value}</text>
    <text x="{stat_x + 80}" y="{y + 110}" font-family="Arial" font-size="12" fill="#a0a0a0" text-anchor="middle">{key}</text>
'''
            stat_x += 180

        svg += '''
    <!-- 页脚 -->
    <text x="400" y="''' + str(height - 20) + '''" font-family="Arial" font-size="10" fill="#64748b" text-anchor="middle">Generated by Podcast Summary Tool</text>
</svg>'''

        return svg
