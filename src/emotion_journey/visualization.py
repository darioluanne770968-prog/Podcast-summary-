"""
情感可视化
生成情感旅程的可视化图表
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json


@dataclass
class ChartConfig:
    """图表配置"""
    width: int = 800
    height: int = 400
    margin_top: int = 20
    margin_right: int = 30
    margin_bottom: int = 40
    margin_left: int = 50
    background_color: str = "#ffffff"
    grid_color: str = "#e0e0e0"
    font_family: str = "Arial, sans-serif"


class EmotionVisualizer:
    """情感可视化器"""

    # 情感颜色映射
    EMOTION_COLORS = {
        "joy": "#FFD700",  # 金色
        "sadness": "#4169E1",  # 皇家蓝
        "anger": "#DC143C",  # 深红色
        "fear": "#800080",  # 紫色
        "surprise": "#FF69B4",  # 粉色
        "disgust": "#556B2F",  # 橄榄绿
        "trust": "#20B2AA",  # 浅海绿
        "anticipation": "#FF8C00",  # 深橙色
        "neutral": "#808080"  # 灰色
    }

    # 效价颜色渐变
    VALENCE_GRADIENT = [
        (-1.0, "#DC143C"),  # 负面 - 红色
        (-0.5, "#FF6347"),  # 较负面 - 番茄色
        (0.0, "#FFFF00"),  # 中性 - 黄色
        (0.5, "#90EE90"),  # 较正面 - 浅绿
        (1.0, "#32CD32")  # 正面 - 绿色
    ]

    def __init__(self, config: Optional[ChartConfig] = None):
        self.config = config or ChartConfig()

    def generate_emotion_timeline(
        self,
        emotion_data: List[Dict[str, Any]],
        duration: float
    ) -> Dict[str, Any]:
        """
        生成情感时间线数据

        Args:
            emotion_data: 情感数据点列表
            duration: 总时长

        Returns:
            可视化数据
        """
        timeline_data = {
            "type": "emotion_timeline",
            "config": {
                "width": self.config.width,
                "height": self.config.height,
                "duration": duration
            },
            "data": {
                "points": [],
                "segments": [],
                "annotations": []
            },
            "legend": self._generate_legend()
        }

        for point in emotion_data:
            timeline_data["data"]["points"].append({
                "x": point.get("timestamp", 0),
                "y_valence": point.get("valence", 0),
                "y_arousal": point.get("arousal", 0.5),
                "y_intensity": point.get("intensity", 0.5),
                "emotion": point.get("primary_emotion", "neutral"),
                "color": self.EMOTION_COLORS.get(point.get("primary_emotion", "neutral"), "#808080"),
                "label": point.get("text_snippet", "")[:50]
            })

        return timeline_data

    def generate_engagement_chart(
        self,
        engagement_data: List[Dict[str, float]],
        retention_data: Optional[List[Dict[str, float]]] = None
    ) -> Dict[str, Any]:
        """
        生成参与度图表数据

        Args:
            engagement_data: 参与度数据
            retention_data: 留存数据

        Returns:
            可视化数据
        """
        chart_data = {
            "type": "engagement_chart",
            "config": {
                "width": self.config.width,
                "height": self.config.height
            },
            "series": []
        }

        # 参与度曲线
        engagement_series = {
            "name": "参与度",
            "type": "area",
            "color": "#4CAF50",
            "data": [
                {"x": d.get("time_percent", 0), "y": d.get("engagement", 0) * 100}
                for d in engagement_data
            ]
        }
        chart_data["series"].append(engagement_series)

        # 留存曲线
        if retention_data:
            retention_series = {
                "name": "留存率",
                "type": "line",
                "color": "#2196F3",
                "data": [
                    {"x": d.get("time_percent", 0), "y": d.get("retention", 0) * 100}
                    for d in retention_data
                ]
            }
            chart_data["series"].append(retention_series)

        return chart_data

    def generate_emotion_heatmap(
        self,
        segments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成情感热力图数据

        Args:
            segments: 情感片段数据

        Returns:
            热力图数据
        """
        heatmap_data = {
            "type": "emotion_heatmap",
            "config": {
                "width": self.config.width,
                "height": 100,
                "cell_width": 20
            },
            "cells": []
        }

        for i, segment in enumerate(segments):
            valence = segment.get("avg_valence", 0)
            intensity = segment.get("avg_intensity", 0.5)

            cell = {
                "index": i,
                "start_time": segment.get("start_time", 0),
                "end_time": segment.get("end_time", 0),
                "valence": valence,
                "intensity": intensity,
                "color": self._get_valence_color(valence),
                "opacity": 0.3 + intensity * 0.7,
                "dominant_emotion": segment.get("dominant_emotion", "neutral")
            }
            heatmap_data["cells"].append(cell)

        return heatmap_data

    def generate_emotion_pie(
        self,
        emotion_summary: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        生成情感分布饼图数据

        Args:
            emotion_summary: 情感汇总

        Returns:
            饼图数据
        """
        pie_data = {
            "type": "emotion_pie",
            "config": {
                "width": 300,
                "height": 300,
                "inner_radius": 50
            },
            "slices": []
        }

        for emotion, percentage in emotion_summary.items():
            if percentage > 0.01:  # 只显示超过1%的
                pie_data["slices"].append({
                    "emotion": emotion,
                    "value": percentage,
                    "percentage": f"{percentage * 100:.1f}%",
                    "color": self.EMOTION_COLORS.get(emotion, "#808080")
                })

        return pie_data

    def generate_journey_visualization(
        self,
        journey_map: Any  # JourneyMap
    ) -> Dict[str, Any]:
        """
        生成完整的旅程可视化数据

        Args:
            journey_map: 旅程图对象

        Returns:
            完整可视化数据
        """
        visualization = {
            "title": journey_map.title,
            "duration": journey_map.duration,
            "overall_rating": journey_map.overall_rating,
            "charts": {}
        }

        # 主时间线
        visualization["charts"]["timeline"] = self._generate_main_timeline(
            journey_map.points,
            journey_map.duration
        )

        # 参与度曲线
        visualization["charts"]["engagement"] = self.generate_engagement_chart(
            journey_map.engagement_curve
        )

        # 阶段标注
        visualization["charts"]["phases"] = self._generate_phase_markers(
            journey_map.phases
        )

        # 高光和低点标记
        visualization["charts"]["markers"] = {
            "highlights": self._format_markers(journey_map.highlights, "highlight"),
            "low_points": self._format_markers(journey_map.low_points, "warning")
        }

        # 评分仪表盘
        visualization["charts"]["gauge"] = self._generate_rating_gauge(
            journey_map.overall_rating
        )

        return visualization

    def _generate_main_timeline(
        self,
        points: List[Any],  # JourneyPoint
        duration: float
    ) -> Dict[str, Any]:
        """生成主时间线"""
        return {
            "type": "main_timeline",
            "config": {
                "width": self.config.width,
                "height": 300,
                "y_axis": {
                    "min": 0,
                    "max": 1,
                    "label": "参与度"
                },
                "x_axis": {
                    "min": 0,
                    "max": duration,
                    "label": "时间 (秒)"
                }
            },
            "data": [
                {
                    "x": p.timestamp,
                    "y": p.engagement_level,
                    "intensity": p.emotional_intensity,
                    "phase": p.phase.value if hasattr(p.phase, 'value') else str(p.phase),
                    "tooltip": p.key_content[:100] if p.key_content else ""
                }
                for p in points
            ],
            "areas": [
                {
                    "name": "engagement",
                    "color": "#4CAF50",
                    "opacity": 0.3
                },
                {
                    "name": "intensity",
                    "color": "#FF9800",
                    "opacity": 0.2
                }
            ]
        }

    def _generate_phase_markers(self, phases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成阶段标记"""
        phase_colors = {
            "hook": "#FF5722",
            "setup": "#9C27B0",
            "rising": "#2196F3",
            "climax": "#F44336",
            "falling": "#FF9800",
            "resolution": "#4CAF50",
            "call_to_action": "#E91E63"
        }

        return {
            "type": "phase_markers",
            "markers": [
                {
                    "phase": p["phase"],
                    "start": p["start_time"],
                    "end": p["end_time"],
                    "color": phase_colors.get(p["phase"], "#9E9E9E"),
                    "label": p["phase"].replace("_", " ").title()
                }
                for p in phases
            ]
        }

    def _format_markers(
        self,
        items: List[Dict[str, Any]],
        marker_type: str
    ) -> List[Dict[str, Any]]:
        """格式化标记"""
        return [
            {
                "type": marker_type,
                "timestamp": item.get("timestamp", item.get("start_time", 0)),
                "value": item.get("engagement", item.get("intensity", 0.5)),
                "label": item.get("reason", item.get("issue", "")),
                "icon": "⭐" if marker_type == "highlight" else "⚠️"
            }
            for item in items
        ]

    def _generate_rating_gauge(self, rating: float) -> Dict[str, Any]:
        """生成评分仪表盘"""
        # 确定颜色
        if rating >= 8:
            color = "#4CAF50"
            label = "优秀"
        elif rating >= 6:
            color = "#8BC34A"
            label = "良好"
        elif rating >= 4:
            color = "#FFC107"
            label = "一般"
        else:
            color = "#F44336"
            label = "需改进"

        return {
            "type": "gauge",
            "config": {
                "width": 200,
                "height": 200,
                "min": 0,
                "max": 10
            },
            "value": rating,
            "color": color,
            "label": label,
            "zones": [
                {"from": 0, "to": 4, "color": "#F44336"},
                {"from": 4, "to": 6, "color": "#FFC107"},
                {"from": 6, "to": 8, "color": "#8BC34A"},
                {"from": 8, "to": 10, "color": "#4CAF50"}
            ]
        }

    def _get_valence_color(self, valence: float) -> str:
        """根据效价获取颜色"""
        for i, (v, color) in enumerate(self.VALENCE_GRADIENT):
            if valence <= v:
                if i == 0:
                    return color
                # 插值
                prev_v, prev_color = self.VALENCE_GRADIENT[i - 1]
                ratio = (valence - prev_v) / (v - prev_v)
                return self._interpolate_color(prev_color, color, ratio)

        return self.VALENCE_GRADIENT[-1][1]

    def _interpolate_color(self, color1: str, color2: str, ratio: float) -> str:
        """颜色插值"""
        # 解析颜色
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

        # 插值
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _generate_legend(self) -> Dict[str, Any]:
        """生成图例"""
        return {
            "emotions": [
                {"name": emotion, "color": color}
                for emotion, color in self.EMOTION_COLORS.items()
            ],
            "valence": [
                {"label": "负面", "color": "#DC143C"},
                {"label": "中性", "color": "#FFFF00"},
                {"label": "正面", "color": "#32CD32"}
            ]
        }

    def export_svg(self, chart_data: Dict[str, Any]) -> str:
        """
        导出为SVG格式

        Args:
            chart_data: 图表数据

        Returns:
            SVG字符串
        """
        chart_type = chart_data.get("type", "")
        config = chart_data.get("config", {})

        width = config.get("width", self.config.width)
        height = config.get("height", self.config.height)

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
            f'<rect width="{width}" height="{height}" fill="{self.config.background_color}"/>',
        ]

        if chart_type == "emotion_heatmap":
            svg_parts.extend(self._render_heatmap_svg(chart_data))
        elif chart_type == "emotion_pie":
            svg_parts.extend(self._render_pie_svg(chart_data))
        elif chart_type == "gauge":
            svg_parts.extend(self._render_gauge_svg(chart_data))

        svg_parts.append('</svg>')

        return '\n'.join(svg_parts)

    def _render_heatmap_svg(self, chart_data: Dict[str, Any]) -> List[str]:
        """渲染热力图SVG"""
        parts = []
        cells = chart_data.get("cells", [])
        cell_width = chart_data.get("config", {}).get("cell_width", 20)
        height = chart_data.get("config", {}).get("height", 100)

        for cell in cells:
            x = cell["index"] * cell_width
            color = cell["color"]
            opacity = cell["opacity"]

            parts.append(
                f'<rect x="{x}" y="0" width="{cell_width}" height="{height}" '
                f'fill="{color}" opacity="{opacity}"/>'
            )

        return parts

    def _render_pie_svg(self, chart_data: Dict[str, Any]) -> List[str]:
        """渲染饼图SVG"""
        parts = []
        config = chart_data.get("config", {})
        width = config.get("width", 300)
        height = config.get("height", 300)
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 10
        inner_radius = config.get("inner_radius", 0)

        slices = chart_data.get("slices", [])
        start_angle = 0

        for slice_data in slices:
            value = slice_data["value"]
            angle = value * 360
            end_angle = start_angle + angle

            # 计算路径
            path = self._create_arc_path(cx, cy, radius, inner_radius, start_angle, end_angle)
            parts.append(f'<path d="{path}" fill="{slice_data["color"]}"/>')

            start_angle = end_angle

        return parts

    def _create_arc_path(
        self,
        cx: float, cy: float,
        outer_r: float, inner_r: float,
        start_angle: float, end_angle: float
    ) -> str:
        """创建扇形路径"""
        import math

        # 转换为弧度
        start_rad = math.radians(start_angle - 90)
        end_rad = math.radians(end_angle - 90)

        # 计算点
        x1 = cx + outer_r * math.cos(start_rad)
        y1 = cy + outer_r * math.sin(start_rad)
        x2 = cx + outer_r * math.cos(end_rad)
        y2 = cy + outer_r * math.sin(end_rad)

        large_arc = 1 if end_angle - start_angle > 180 else 0

        if inner_r > 0:
            x3 = cx + inner_r * math.cos(end_rad)
            y3 = cy + inner_r * math.sin(end_rad)
            x4 = cx + inner_r * math.cos(start_rad)
            y4 = cy + inner_r * math.sin(start_rad)

            return (
                f"M {x1} {y1} "
                f"A {outer_r} {outer_r} 0 {large_arc} 1 {x2} {y2} "
                f"L {x3} {y3} "
                f"A {inner_r} {inner_r} 0 {large_arc} 0 {x4} {y4} "
                f"Z"
            )
        else:
            return (
                f"M {cx} {cy} "
                f"L {x1} {y1} "
                f"A {outer_r} {outer_r} 0 {large_arc} 1 {x2} {y2} "
                f"Z"
            )

    def _render_gauge_svg(self, chart_data: Dict[str, Any]) -> List[str]:
        """渲染仪表盘SVG"""
        parts = []
        config = chart_data.get("config", {})
        width = config.get("width", 200)
        height = config.get("height", 200)
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 20

        value = chart_data.get("value", 0)
        max_val = config.get("max", 10)
        color = chart_data.get("color", "#4CAF50")

        # 背景弧
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" '
            f'fill="none" stroke="#e0e0e0" stroke-width="20"/>'
        )

        # 值弧
        angle = (value / max_val) * 360
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" '
            f'fill="none" stroke="{color}" stroke-width="20" '
            f'stroke-dasharray="{angle * radius * 3.14159 / 180} 1000" '
            f'transform="rotate(-90 {cx} {cy})"/>'
        )

        # 中心文字
        parts.append(
            f'<text x="{cx}" y="{cy}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="24" font-weight="bold">'
            f'{value:.1f}</text>'
        )

        return parts

    def export_to_html(
        self,
        visualization: Dict[str, Any],
        include_interactive: bool = True
    ) -> str:
        """
        导出为HTML页面

        Args:
            visualization: 可视化数据
            include_interactive: 是否包含交互功能

        Returns:
            HTML字符串
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{visualization.get('title', '情感旅程图')}</title>
    <style>
        body {{
            font-family: {self.config.font_family};
            margin: 20px;
            background: #f5f5f5;
        }}
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .title {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
        }}
        .rating {{
            font-size: 36px;
            color: #4CAF50;
        }}
    </style>
</head>
<body>
    <div class="title">{visualization.get('title', '情感旅程图')}</div>
    <div class="rating">评分: {visualization.get('overall_rating', 0):.1f}/10</div>

    <div class="chart-container">
        <h3>参与度时间线</h3>
        <div id="timeline-chart"></div>
    </div>

    <div class="chart-container">
        <h3>阶段分布</h3>
        <div id="phase-chart"></div>
    </div>

    <script>
        const data = {json.dumps(visualization, ensure_ascii=False)};
        console.log('Visualization data:', data);
        // 这里可以添加Chart.js或D3.js来渲染图表
    </script>
</body>
</html>
        """

        return html
