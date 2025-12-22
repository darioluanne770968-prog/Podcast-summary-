"""
问答引擎
处理用户问题并生成答案
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Question:
    id: str
    text: str
    timestamp: Optional[float]  # 播客时间点
    user_id: str
    asked_at: datetime


@dataclass
class Answer:
    question_id: str
    text: str
    confidence: float
    source_segments: List[Dict[str, Any]]
    related_timestamps: List[float]
    generated_at: datetime


@dataclass
class QASession:
    session_id: str
    podcast_id: str
    questions: List[Question]
    answers: List[Answer]


class QAEngine:
    """问答引擎"""

    def __init__(self):
        self.sessions: Dict[str, QASession] = {}
        self.podcast_contexts: Dict[str, Dict[str, Any]] = {}

    def load_podcast_context(self, podcast_id: str, transcript: str, metadata: Dict[str, Any]):
        """加载播客上下文"""
        self.podcast_contexts[podcast_id] = {
            "transcript": transcript,
            "metadata": metadata,
            "segments": self._segment_transcript(transcript),
            "key_topics": self._extract_topics(transcript)
        }

    def _segment_transcript(self, transcript: str) -> List[Dict[str, Any]]:
        """分割转录文本"""
        sentences = transcript.split("。")
        segments = []
        current_time = 0
        time_per_char = 0.1  # 假设每字符0.1秒

        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            segments.append({
                "index": i,
                "text": sentence + "。",
                "start_time": current_time,
                "end_time": current_time + len(sentence) * time_per_char
            })
            current_time += len(sentence) * time_per_char

        return segments

    def _extract_topics(self, transcript: str) -> List[str]:
        """提取关键话题"""
        # 简化实现
        return ["话题1", "话题2", "话题3"]

    def ask(
        self,
        podcast_id: str,
        question_text: str,
        user_id: str,
        timestamp: Optional[float] = None
    ) -> Answer:
        """提问"""
        context = self.podcast_contexts.get(podcast_id)
        if not context:
            return Answer(
                question_id="error",
                text="未找到播客内容",
                confidence=0,
                source_segments=[],
                related_timestamps=[],
                generated_at=datetime.now()
            )

        # 找到相关段落
        relevant_segments = self._find_relevant_segments(
            question_text, context["segments"], timestamp
        )

        # 生成答案
        answer_text = self._generate_answer(question_text, relevant_segments)

        return Answer(
            question_id=f"q_{datetime.now().timestamp()}",
            text=answer_text,
            confidence=0.8,
            source_segments=relevant_segments,
            related_timestamps=[seg["start_time"] for seg in relevant_segments],
            generated_at=datetime.now()
        )

    def _find_relevant_segments(
        self,
        question: str,
        segments: List[Dict[str, Any]],
        timestamp: Optional[float]
    ) -> List[Dict[str, Any]]:
        """找到相关段落"""
        relevant = []

        # 如果指定了时间戳，优先查找附近的段落
        if timestamp:
            for seg in segments:
                if abs(seg["start_time"] - timestamp) < 60:
                    relevant.append(seg)

        # 基于关键词匹配
        question_words = set(question)
        for seg in segments:
            overlap = len(question_words & set(seg["text"])) / len(question_words)
            if overlap > 0.2:
                relevant.append(seg)

        return relevant[:5]

    def _generate_answer(
        self,
        question: str,
        segments: List[Dict[str, Any]]
    ) -> str:
        """生成答案"""
        if not segments:
            return "抱歉，在播客内容中没有找到与您问题相关的信息。"

        # 合并相关内容
        context = " ".join(seg["text"] for seg in segments)

        return f"根据播客内容，{context[:200]}..."

    def get_suggested_questions(self, podcast_id: str) -> List[str]:
        """获取建议问题"""
        context = self.podcast_contexts.get(podcast_id)
        if not context:
            return []

        topics = context.get("key_topics", [])
        return [
            f"这期节目主要讲了什么？",
            f"能总结一下关于{topics[0]}的讨论吗？" if topics else "能总结一下吗？",
            "嘉宾的主要观点是什么？",
            "有哪些实用的建议？"
        ]
