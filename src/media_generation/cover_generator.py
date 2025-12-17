"""
封面/配图生成模块

为播客生成封面图、社交媒体配图等
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple
import json

from ..utils import get_logger, ensure_dir
from ..analysis import LLMClient

logger = get_logger(__name__)


@dataclass
class CoverDesign:
    """封面设计"""
    title: str
    subtitle: Optional[str] = None
    background_color: str = "#1a1a2e"
    accent_color: str = "#6366f1"
    text_color: str = "#ffffff"
    style: str = "modern"  # modern, minimal, bold, artistic
    image_prompt: Optional[str] = None  # AI 图像生成提示词


class CoverGenerator:
    """封面生成器"""

    SYSTEM_PROMPT = """你是一个专业的设计师，擅长为播客和内容创作设计封面。

设计原则：
1. 简洁有力，突出主题
2. 颜色搭配和谐
3. 文字清晰易读
4. 符合平台规范"""

    # 预设颜色方案
    COLOR_SCHEMES = {
        "tech": {"bg": "#0f172a", "accent": "#3b82f6", "text": "#ffffff"},
        "business": {"bg": "#1e293b", "accent": "#f59e0b", "text": "#ffffff"},
        "creative": {"bg": "#831843", "accent": "#f472b6", "text": "#ffffff"},
        "education": {"bg": "#064e3b", "accent": "#34d399", "text": "#ffffff"},
        "lifestyle": {"bg": "#fef3c7", "accent": "#d97706", "text": "#1f2937"},
        "dark": {"bg": "#18181b", "accent": "#a855f7", "text": "#ffffff"},
        "light": {"bg": "#f8fafc", "accent": "#0ea5e9", "text": "#0f172a"},
    }

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.output_dir = output_dir or Path("./output/covers")
        self.llm = llm_client or LLMClient()
        ensure_dir(self.output_dir)

    def generate_design(
        self,
        title: str,
        keywords: List[str] = None,
        style: str = "modern",
    ) -> CoverDesign:
        """
        生成封面设计方案

        Args:
            title: 标题
            keywords: 关键词（用于确定风格）
            style: 设计风格

        Returns:
            CoverDesign 对象
        """
        # 根据关键词选择颜色方案
        color_scheme = self._select_color_scheme(keywords or [])

        # 生成副标题建议
        subtitle = self._generate_subtitle(title, keywords)

        # 生成 AI 图像提示词
        image_prompt = self._generate_image_prompt(title, keywords, style)

        return CoverDesign(
            title=title,
            subtitle=subtitle,
            background_color=color_scheme["bg"],
            accent_color=color_scheme["accent"],
            text_color=color_scheme["text"],
            style=style,
            image_prompt=image_prompt,
        )

    def _select_color_scheme(self, keywords: List[str]) -> dict:
        """根据关键词选择颜色方案"""
        keywords_lower = [k.lower() for k in keywords]

        # 关键词到方案的映射
        keyword_mapping = {
            "tech": ["技术", "编程", "ai", "人工智能", "软件", "开发", "tech", "code"],
            "business": ["商业", "创业", "投资", "金融", "管理", "business", "startup"],
            "creative": ["设计", "艺术", "创意", "音乐", "creative", "design", "art"],
            "education": ["学习", "教育", "知识", "成长", "education", "learning"],
            "lifestyle": ["生活", "健康", "旅行", "美食", "lifestyle", "health"],
        }

        for scheme, kws in keyword_mapping.items():
            for kw in kws:
                if any(kw in k for k in keywords_lower):
                    return self.COLOR_SCHEMES[scheme]

        return self.COLOR_SCHEMES["dark"]

    def _generate_subtitle(self, title: str, keywords: List[str]) -> str:
        """生成副标题"""
        if not keywords:
            return ""

        # 取前3个关键词
        top_keywords = keywords[:3]
        return " · ".join(top_keywords)

    def _generate_image_prompt(
        self,
        title: str,
        keywords: List[str],
        style: str,
    ) -> str:
        """生成 AI 图像提示词"""
        prompt = f"""为以下播客封面生成一个 AI 图像提示词（用于 Midjourney/DALL-E）：

标题: {title}
关键词: {', '.join(keywords or [])}
风格: {style}

要求：
1. 抽象、艺术化，不要包含具体人物
2. 适合作为文字背景
3. 颜色和谐，不要太杂乱

只输出英文提示词，不要其他内容。"""

        try:
            response = self.llm.complete(prompt, system=self.SYSTEM_PROMPT, temperature=0.7)
            return response.strip()
        except Exception:
            return f"Abstract {style} background, {', '.join(keywords[:3]) if keywords else 'podcast'}, minimalist, clean"

    def create_cover_svg(
        self,
        design: CoverDesign,
        width: int = 1400,
        height: int = 1400,
    ) -> str:
        """
        生成 SVG 格式封面

        Args:
            design: 封面设计
            width: 宽度
            height: 高度

        Returns:
            SVG 字符串
        """
        # 计算文字大小
        title_size = min(width // 10, 120)
        subtitle_size = title_size // 2

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:{design.background_color}"/>
            <stop offset="100%" style="stop-color:{self._darken_color(design.background_color)}"/>
        </linearGradient>
        <filter id="shadow">
            <feDropShadow dx="2" dy="4" stdDeviation="3" flood-opacity="0.3"/>
        </filter>
    </defs>

    <!-- 背景 -->
    <rect width="100%" height="100%" fill="url(#bgGradient)"/>

    <!-- 装饰元素 -->
    <circle cx="{width * 0.85}" cy="{height * 0.15}" r="{width * 0.2}"
            fill="{design.accent_color}" opacity="0.1"/>
    <circle cx="{width * 0.1}" cy="{height * 0.9}" r="{width * 0.15}"
            fill="{design.accent_color}" opacity="0.1"/>

    <!-- 播客图标 -->
    <g transform="translate({width/2 - 40}, {height * 0.25})">
        <circle cx="40" cy="40" r="35" fill="{design.accent_color}"/>
        <rect x="30" y="25" width="8" height="30" rx="4" fill="{design.text_color}"/>
        <rect x="42" y="15" width="8" height="50" rx="4" fill="{design.text_color}"/>
        <rect x="54" y="30" width="8" height="20" rx="4" fill="{design.text_color}"/>
    </g>

    <!-- 标题 -->
    <text x="50%" y="{height * 0.55}"
          font-family="Arial, sans-serif" font-size="{title_size}" font-weight="bold"
          fill="{design.text_color}" text-anchor="middle" filter="url(#shadow)">
        {self._wrap_text(design.title, 15)}
    </text>

    <!-- 副标题 -->
    {f'''<text x="50%" y="{height * 0.68}"
          font-family="Arial, sans-serif" font-size="{subtitle_size}"
          fill="{design.accent_color}" text-anchor="middle">
        {design.subtitle}
    </text>''' if design.subtitle else ''}

    <!-- 底部装饰线 -->
    <rect x="{width * 0.3}" y="{height * 0.85}" width="{width * 0.4}" height="4"
          rx="2" fill="{design.accent_color}"/>
</svg>'''

        return svg

    def create_cover_image(
        self,
        design: CoverDesign,
        width: int = 1400,
        height: int = 1400,
        output_format: str = "png",
    ) -> Path:
        """
        生成封面图片

        Args:
            design: 封面设计
            width: 宽度
            height: 高度
            output_format: 输出格式

        Returns:
            输出文件路径
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.warning("Pillow 未安装，使用 SVG 格式")
            return self.save_cover_svg(design, width, height)

        # 创建图像
        img = Image.new('RGB', (width, height), design.background_color)
        draw = ImageDraw.Draw(img)

        # 绘制装饰圆形
        accent_rgb = self._hex_to_rgb(design.accent_color)
        for i in range(3):
            x = int(width * (0.2 + i * 0.3))
            y = int(height * 0.2)
            r = int(width * 0.1)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(*accent_rgb, 30))

        # 尝试加载字体
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", width // 12)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", width // 24)
        except Exception:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

        # 绘制标题
        title_bbox = draw.textbbox((0, 0), design.title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = int(height * 0.45)
        draw.text((title_x, title_y), design.title, fill=design.text_color, font=title_font)

        # 绘制副标题
        if design.subtitle:
            subtitle_bbox = draw.textbbox((0, 0), design.subtitle, font=subtitle_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (width - subtitle_width) // 2
            subtitle_y = int(height * 0.58)
            draw.text((subtitle_x, subtitle_y), design.subtitle, fill=design.accent_color, font=subtitle_font)

        # 保存
        filename = f"cover_{design.title[:20].replace(' ', '_')}.{output_format}"
        output_path = self.output_dir / filename
        img.save(output_path)

        logger.info(f"封面生成完成: {output_path}")
        return output_path

    def save_cover_svg(
        self,
        design: CoverDesign,
        width: int = 1400,
        height: int = 1400,
    ) -> Path:
        """保存 SVG 封面"""
        svg_content = self.create_cover_svg(design, width, height)
        filename = f"cover_{design.title[:20].replace(' ', '_')}.svg"
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        logger.info(f"SVG 封面生成完成: {output_path}")
        return output_path

    def _darken_color(self, hex_color: str) -> str:
        """加深颜色"""
        r, g, b = self._hex_to_rgb(hex_color)
        factor = 0.7
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """十六进制转 RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _wrap_text(self, text: str, max_chars: int) -> str:
        """文字换行"""
        if len(text) <= max_chars:
            return text
        # 简单换行
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) > max_chars:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length += len(word) + 1

        if current_line:
            lines.append(' '.join(current_line))

        return lines[0] if lines else text  # SVG 中只显示第一行
