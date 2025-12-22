"""上下文管理器"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ConversationContext:
    podcast_id: str
    history: List[Dict[str, str]]
    current_topic: str
    mentioned_entities: List[str]


class ContextManager:
    """上下文管理器"""

    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}

    def get_or_create(self, session_id: str, podcast_id: str) -> ConversationContext:
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext(
                podcast_id=podcast_id,
                history=[],
                current_topic="",
                mentioned_entities=[]
            )
        return self.contexts[session_id]

    def add_interaction(self, session_id: str, question: str, answer: str):
        if session_id in self.contexts:
            self.contexts[session_id].history.append({
                "question": question,
                "answer": answer
            })

    def get_history(self, session_id: str, limit: int = 5) -> List[Dict[str, str]]:
        if session_id in self.contexts:
            return self.contexts[session_id].history[-limit:]
        return []
