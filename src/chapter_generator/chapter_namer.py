"""章节命名器"""
from typing import List, Optional


class ChapterNamer:
    """章节命名器"""

    def __init__(self):
        self.default_names = {
            "intro": "开场介绍",
            "main": "主要内容",
            "qa": "问答环节",
            "sponsor": "赞助商信息",
            "outro": "结尾总结"
        }

    def generate_name(
        self,
        transcript_segment: str,
        chapter_type: str,
        index: int
    ) -> str:
        """生成章节名称"""
        if chapter_type in self.default_names:
            return self.default_names[chapter_type]

        # 尝试从文本提取关键主题
        keywords = self._extract_keywords(transcript_segment)
        if keywords:
            return f"讨论：{keywords[0]}"

        return f"第{index + 1}部分"

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简化实现
        important_words = []
        indicators = ["关于", "讨论", "分享", "介绍"]
        for indicator in indicators:
            if indicator in text[:100]:
                # 找到指示词后的内容
                idx = text.find(indicator)
                snippet = text[idx:idx + 30]
                important_words.append(snippet.split()[0] if snippet.split() else "")
        return [w for w in important_words if w]
