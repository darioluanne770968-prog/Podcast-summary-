"""答案生成器"""
from typing import List, Dict, Any


class AnswerGenerator:
    """答案生成器"""

    def __init__(self):
        self.templates = {
            "summary": "根据播客内容，{content}",
            "explain": "关于这个问题，播客中提到：{content}",
            "list": "主要包括以下几点：\n{content}",
            "not_found": "抱歉，在播客内容中没有找到相关信息。"
        }

    def generate(
        self,
        question_type: str,
        context_segments: List[Dict[str, Any]],
        question: str
    ) -> str:
        """生成答案"""
        if not context_segments:
            return self.templates["not_found"]

        content = self._extract_relevant_content(context_segments, question)
        template = self.templates.get(question_type, self.templates["explain"])

        return template.format(content=content)

    def _extract_relevant_content(
        self,
        segments: List[Dict[str, Any]],
        question: str
    ) -> str:
        """提取相关内容"""
        texts = [seg.get("text", "") for seg in segments]
        return " ".join(texts)[:500]

    def format_with_timestamps(
        self,
        answer: str,
        timestamps: List[float]
    ) -> str:
        """添加时间戳引用"""
        if timestamps:
            ts_str = ", ".join(f"{int(t//60)}:{int(t%60):02d}" for t in timestamps[:3])
            return f"{answer}\n\n📍 相关时间点：{ts_str}"
        return answer
