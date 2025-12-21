"""
AI 对话式播客助手模块

功能：
- 实时问答：边听边问，AI 回答关于播客内容的问题
- 上下文记忆：记住你听过的所有播客，跨节目关联回答
- 个人播客教练：根据你的学习目标推荐内容片段
- 辩论模式：AI 扮演不同观点与你讨论播客内容
"""

from .chat_assistant import ChatAssistant, ConversationMemory
from .podcast_coach import PodcastCoach, LearningGoal
from .debate_mode import DebateSimulator, Viewpoint

__all__ = [
    "ChatAssistant",
    "ConversationMemory",
    "PodcastCoach",
    "LearningGoal",
    "DebateSimulator",
    "Viewpoint",
]
