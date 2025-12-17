"""
PPT 演示文稿生成模块

根据播客分析结果生成演示文稿
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from ...utils import get_logger, ensure_dir

logger = get_logger(__name__)


class PPTGenerator:
    """PPT 生成器"""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("./output/presentations")
        ensure_dir(self.output_dir)

    def generate(
        self,
        analysis_result: Dict[str, Any],
        title: str,
        template: str = "default",
    ) -> Path:
        """
        生成 PPT

        Args:
            analysis_result: 分析结果
            title: 演示文稿标题
            template: 模板名称

        Returns:
            输出文件路径
        """
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RgbColor
            from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
        except ImportError:
            logger.error("请安装 python-pptx: pip install python-pptx")
            raise

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        # 标题页
        self._add_title_slide(prs, title, analysis_result)

        # 摘要页
        if analysis_result.get("summary"):
            self._add_summary_slide(prs, analysis_result["summary"])

        # 关键词页
        if analysis_result.get("keywords"):
            self._add_keywords_slide(prs, analysis_result["keywords"])

        # 章节页
        if analysis_result.get("chapters"):
            self._add_chapters_slides(prs, analysis_result["chapters"])

        # 金句页
        if analysis_result.get("quotes"):
            self._add_quotes_slides(prs, analysis_result["quotes"])

        # Q&A 页
        if analysis_result.get("qa_pairs"):
            self._add_qa_slides(prs, analysis_result["qa_pairs"])

        # 结尾页
        self._add_ending_slide(prs, title)

        # 保存
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:50]
        output_path = self.output_dir / f"{safe_title}.pptx"
        prs.save(output_path)

        logger.info(f"PPT 生成完成: {output_path}")
        return output_path

    def _add_title_slide(
        self,
        prs,
        title: str,
        result: Dict[str, Any],
    ):
        """添加标题页"""
        from pptx.util import Inches, Pt

        slide_layout = prs.slide_layouts[6]  # 空白布局
        slide = prs.slides.add_slide(slide_layout)

        # 背景色
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb("#1a1a2e")

        # 标题
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"🎙️ {title}"
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = self._hex_to_rgb("#ffffff")
        p.alignment = 1  # CENTER

        # 副标题
        subtitle_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(12.333), Inches(0.8))
        tf = subtitle_box.text_frame
        p = tf.paragraphs[0]
        p.text = "播客内容分析报告"
        p.font.size = Pt(24)
        p.font.color.rgb = self._hex_to_rgb("#a0a0a0")
        p.alignment = 1

        # 日期
        date_box = slide.shapes.add_textbox(Inches(0.5), Inches(5.5), Inches(12.333), Inches(0.5))
        tf = date_box.text_frame
        p = tf.paragraphs[0]
        p.text = datetime.now().strftime("%Y年%m月%d日")
        p.font.size = Pt(16)
        p.font.color.rgb = self._hex_to_rgb("#6366f1")
        p.alignment = 1

    def _add_summary_slide(self, prs, summary: str):
        """添加摘要页"""
        from pptx.util import Inches, Pt

        slide = prs.slides.add_slide(prs.slide_layouts[6])
        self._set_slide_background(slide, "#0f172a")

        # 标题
        self._add_slide_title(slide, "📝 内容摘要")

        # 摘要文本
        content_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.733), Inches(5))
        tf = content_box.text_frame
        tf.word_wrap = True

        # 分段显示
        paragraphs = summary.split("\n\n")
        for i, para in enumerate(paragraphs[:4]):  # 最多4段
            if i > 0:
                p = tf.add_paragraph()
            else:
                p = tf.paragraphs[0]
            p.text = para[:300]  # 限制长度
            p.font.size = Pt(18)
            p.font.color.rgb = self._hex_to_rgb("#e2e8f0")
            p.space_after = Pt(12)

    def _add_keywords_slide(self, prs, keywords: List[str]):
        """添加关键词页"""
        from pptx.util import Inches, Pt

        slide = prs.slides.add_slide(prs.slide_layouts[6])
        self._set_slide_background(slide, "#0f172a")

        self._add_slide_title(slide, "🏷️ 关键词")

        # 关键词标签
        x_start = 0.8
        y_start = 2.0
        x = x_start
        y = y_start
        max_x = 12.5

        for kw in keywords[:15]:  # 最多15个
            # 估算宽度
            width = len(kw) * 0.25 + 0.5
            if x + width > max_x:
                x = x_start
                y += 0.8

            # 添加标签背景
            shape = slide.shapes.add_shape(
                5,  # 圆角矩形
                Inches(x), Inches(y),
                Inches(width), Inches(0.6)
            )
            shape.fill.solid()
            shape.fill.fore_color.rgb = self._hex_to_rgb("#6366f1")
            shape.line.fill.background()

            # 添加文字
            text_box = slide.shapes.add_textbox(
                Inches(x), Inches(y + 0.1),
                Inches(width), Inches(0.4)
            )
            tf = text_box.text_frame
            p = tf.paragraphs[0]
            p.text = kw
            p.font.size = Pt(16)
            p.font.color.rgb = self._hex_to_rgb("#ffffff")
            p.alignment = 1

            x += width + 0.3

    def _add_chapters_slides(self, prs, chapters: List[Dict]):
        """添加章节页"""
        from pptx.util import Inches, Pt

        # 目录页
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        self._set_slide_background(slide, "#0f172a")
        self._add_slide_title(slide, "📑 章节目录")

        y = 1.8
        for i, chapter in enumerate(chapters[:8], 1):
            title = chapter.get("title", "")[:40]
            timestamp = self._format_timestamp(chapter.get("start_time", 0))

            text_box = slide.shapes.add_textbox(Inches(0.8), Inches(y), Inches(11), Inches(0.5))
            tf = text_box.text_frame
            p = tf.paragraphs[0]
            p.text = f"{i}. {title}"
            p.font.size = Pt(20)
            p.font.color.rgb = self._hex_to_rgb("#e2e8f0")

            time_box = slide.shapes.add_textbox(Inches(11), Inches(y), Inches(1.5), Inches(0.5))
            tf = time_box.text_frame
            p = tf.paragraphs[0]
            p.text = timestamp
            p.font.size = Pt(16)
            p.font.color.rgb = self._hex_to_rgb("#6366f1")

            y += 0.65

        # 各章节详情页
        for chapter in chapters[:5]:  # 最多5个章节详情
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            self._set_slide_background(slide, "#0f172a")

            title = chapter.get("title", "")
            self._add_slide_title(slide, f"📖 {title}")

            if chapter.get("summary"):
                content_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.733), Inches(5))
                tf = content_box.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.text = chapter["summary"][:500]
                p.font.size = Pt(18)
                p.font.color.rgb = self._hex_to_rgb("#e2e8f0")

    def _add_quotes_slides(self, prs, quotes: List[Dict]):
        """添加金句页"""
        from pptx.util import Inches, Pt

        for quote in quotes[:5]:  # 最多5条金句
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            self._set_slide_background(slide, "#1e1b4b")

            # 引号装饰
            quote_mark = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(1), Inches(1))
            tf = quote_mark.text_frame
            p = tf.paragraphs[0]
            p.text = """
            p.font.size = Pt(120)
            p.font.color.rgb = self._hex_to_rgb("#6366f1")

            # 金句内容
            text = quote.get("text", "")
            content_box = slide.shapes.add_textbox(Inches(1.5), Inches(2.5), Inches(10.333), Inches(3))
            tf = content_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = text[:200]
            p.font.size = Pt(28)
            p.font.italic = True
            p.font.color.rgb = self._hex_to_rgb("#ffffff")

            # 说话人
            speaker = quote.get("speaker", "")
            if speaker:
                speaker_box = slide.shapes.add_textbox(Inches(1.5), Inches(5.5), Inches(10.333), Inches(0.5))
                tf = speaker_box.text_frame
                p = tf.paragraphs[0]
                p.text = f"— {speaker}"
                p.font.size = Pt(18)
                p.font.color.rgb = self._hex_to_rgb("#a0a0a0")
                p.alignment = 2  # RIGHT

    def _add_qa_slides(self, prs, qa_pairs: List[Dict]):
        """添加 Q&A 页"""
        from pptx.util import Inches, Pt

        slide = prs.slides.add_slide(prs.slide_layouts[6])
        self._set_slide_background(slide, "#0f172a")
        self._add_slide_title(slide, "❓ 问答精选")

        y = 1.8
        for qa in qa_pairs[:4]:  # 最多4个问答
            # 问题
            q_box = slide.shapes.add_textbox(Inches(0.8), Inches(y), Inches(11.733), Inches(0.6))
            tf = q_box.text_frame
            p = tf.paragraphs[0]
            p.text = f"Q: {qa.get('question', '')[:80]}"
            p.font.size = Pt(18)
            p.font.bold = True
            p.font.color.rgb = self._hex_to_rgb("#6366f1")

            # 答案
            a_box = slide.shapes.add_textbox(Inches(0.8), Inches(y + 0.5), Inches(11.733), Inches(0.8))
            tf = a_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = f"A: {qa.get('answer', '')[:150]}"
            p.font.size = Pt(16)
            p.font.color.rgb = self._hex_to_rgb("#e2e8f0")

            y += 1.4

    def _add_ending_slide(self, prs, title: str):
        """添加结尾页"""
        from pptx.util import Inches, Pt

        slide = prs.slides.add_slide(prs.slide_layouts[6])
        self._set_slide_background(slide, "#1a1a2e")

        # 感谢文字
        thanks_box = slide.shapes.add_textbox(Inches(0.5), Inches(3), Inches(12.333), Inches(1))
        tf = thanks_box.text_frame
        p = tf.paragraphs[0]
        p.text = "Thanks for Watching!"
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = self._hex_to_rgb("#ffffff")
        p.alignment = 1

        # 来源
        source_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(12.333), Inches(0.5))
        tf = source_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"内容来源: {title}"
        p.font.size = Pt(18)
        p.font.color.rgb = self._hex_to_rgb("#a0a0a0")
        p.alignment = 1

        # 工具标注
        tool_box = slide.shapes.add_textbox(Inches(0.5), Inches(6.5), Inches(12.333), Inches(0.3))
        tf = tool_box.text_frame
        p = tf.paragraphs[0]
        p.text = "Generated by Podcast Summary Tool"
        p.font.size = Pt(12)
        p.font.color.rgb = self._hex_to_rgb("#64748b")
        p.alignment = 1

    def _set_slide_background(self, slide, color: str):
        """设置幻灯片背景色"""
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(color)

    def _add_slide_title(self, slide, title: str):
        """添加幻灯片标题"""
        from pptx.util import Inches, Pt

        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12.333), Inches(1))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = self._hex_to_rgb("#ffffff")

    def _hex_to_rgb(self, hex_color: str):
        """十六进制颜色转 RGB"""
        from pptx.dml.color import RgbColor
        hex_color = hex_color.lstrip("#")
        return RgbColor(
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
