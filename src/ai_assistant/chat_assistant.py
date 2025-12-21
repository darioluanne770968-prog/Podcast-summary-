"""
对话式播客助手

支持实时问答和上下文记忆
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import uuid

from ..utils import get_logger

logger = get_logger(__name__)


@dataclass
class Message:
    """对话消息"""
    id: str
    role: str  # user, assistant, system
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationMemory:
    """对话记忆"""
    id: str
    podcast_id: Optional[str] = None
    podcast_title: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_message(self, role: str, content: str, metadata: Dict = None) -> Message:
        msg = Message(
            id=str(uuid.uuid4())[:8],
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        return msg

    def get_history(self, limit: int = 20) -> List[Dict]:
        """获取对话历史"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages[-limit:]
        ]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "podcast_id": self.podcast_id,
            "podcast_title": self.podcast_title,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                }
                for msg in self.messages
            ],
            "context": self.context,
            "created_at": self.created_at,
        }


class ChatAssistant:
    """
    对话式播客助手

    支持：
    - 基于播客内容的问答
    - 跨播客知识关联
    - 上下文记忆
    - 多轮对话
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        llm_provider: str = "openai",
    ):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "assistant"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.llm_provider = llm_provider
        self._conversations: Dict[str, ConversationMemory] = {}
        self._podcast_contexts: Dict[str, Dict] = {}
        self._load_data()

    def _load_data(self):
        """加载历史数据"""
        conv_file = self.storage_dir / "conversations.json"
        if conv_file.exists():
            try:
                with open(conv_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for conv_data in data:
                        conv = ConversationMemory(
                            id=conv_data["id"],
                            podcast_id=conv_data.get("podcast_id"),
                            podcast_title=conv_data.get("podcast_title"),
                            context=conv_data.get("context", {}),
                            created_at=conv_data.get("created_at"),
                        )
                        for msg_data in conv_data.get("messages", []):
                            conv.messages.append(Message(
                                id=msg_data["id"],
                                role=msg_data["role"],
                                content=msg_data["content"],
                                timestamp=msg_data.get("timestamp", ""),
                            ))
                        self._conversations[conv.id] = conv
            except Exception as e:
                logger.error(f"加载对话历史失败: {e}")

    def _save_data(self):
        """保存数据"""
        conv_file = self.storage_dir / "conversations.json"
        try:
            data = [conv.to_dict() for conv in self._conversations.values()]
            with open(conv_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存对话历史失败: {e}")

    def create_conversation(
        self,
        podcast_id: Optional[str] = None,
        podcast_title: Optional[str] = None,
        podcast_content: Optional[Dict] = None,
    ) -> ConversationMemory:
        """创建新对话"""
        conv_id = str(uuid.uuid4())[:8]
        conv = ConversationMemory(
            id=conv_id,
            podcast_id=podcast_id,
            podcast_title=podcast_title,
        )

        if podcast_content:
            conv.context = {
                "transcript": podcast_content.get("transcript", "")[:10000],
                "summary": podcast_content.get("summary", ""),
                "chapters": podcast_content.get("chapters", []),
                "keywords": podcast_content.get("keywords", []),
                "quotes": podcast_content.get("quotes", []),
            }

        self._conversations[conv_id] = conv
        self._save_data()
        logger.info(f"创建新对话: {conv_id}")
        return conv

    def get_conversation(self, conv_id: str) -> Optional[ConversationMemory]:
        """获取对话"""
        return self._conversations.get(conv_id)

    def list_conversations(self, limit: int = 20) -> List[ConversationMemory]:
        """列出对话"""
        convs = list(self._conversations.values())
        convs.sort(key=lambda c: c.created_at, reverse=True)
        return convs[:limit]

    async def chat(
        self,
        conv_id: str,
        user_message: str,
        stream: bool = False,
    ) -> str:
        """
        对话

        Args:
            conv_id: 对话 ID
            user_message: 用户消息
            stream: 是否流式返回

        Returns:
            助手回复
        """
        conv = self.get_conversation(conv_id)
        if not conv:
            raise ValueError(f"对话不存在: {conv_id}")

        # 添加用户消息
        conv.add_message("user", user_message)

        # 构建系统提示
        system_prompt = self._build_system_prompt(conv)

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conv.get_history(limit=10))

        # 调用 LLM
        response = await self._call_llm(messages, stream)

        # 添加助手回复
        conv.add_message("assistant", response)
        self._save_data()

        return response

    def _build_system_prompt(self, conv: ConversationMemory) -> str:
        """构建系统提示"""
        base_prompt = """你是一个专业的播客内容助手。你的任务是帮助用户理解和学习播客内容。

你的能力：
1. 回答关于播客内容的问题
2. 解释复杂概念
3. 提取关键信息
4. 关联不同话题
5. 提供深入分析

回答要求：
- 基于播客内容回答，不要编造信息
- 如果信息不在播客中，明确说明
- 使用简洁清晰的语言
- 适当引用原文
"""

        if conv.context:
            context_parts = []

            if conv.context.get("summary"):
                context_parts.append(f"【播客摘要】\n{conv.context['summary']}")

            if conv.context.get("keywords"):
                keywords = ", ".join(conv.context["keywords"][:10])
                context_parts.append(f"【关键词】{keywords}")

            if conv.context.get("chapters"):
                chapters = "\n".join([
                    f"- {ch.get('title', '')}: {ch.get('summary', '')[:100]}"
                    for ch in conv.context["chapters"][:5]
                ])
                context_parts.append(f"【章节】\n{chapters}")

            if conv.context.get("transcript"):
                # 只取部分转录文本
                transcript = conv.context["transcript"][:5000]
                context_parts.append(f"【部分转录】\n{transcript}...")

            if context_parts:
                base_prompt += "\n\n" + "\n\n".join(context_parts)

        return base_prompt

    async def _call_llm(self, messages: List[Dict], stream: bool = False) -> str:
        """调用 LLM"""
        try:
            if self.llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=2000,
                )
                return response.choices[0].message.content

            elif self.llm_provider == "anthropic":
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic()
                # 提取 system 消息
                system = ""
                chat_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system = msg["content"]
                    else:
                        chat_messages.append(msg)

                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    system=system,
                    messages=chat_messages,
                )
                return response.content[0].text

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"抱歉，处理您的问题时出现错误: {str(e)}"

    async def ask_about_timestamp(
        self,
        conv_id: str,
        timestamp: float,
        question: str,
    ) -> str:
        """
        询问特定时间点的内容

        Args:
            conv_id: 对话 ID
            timestamp: 时间戳（秒）
            question: 问题
        """
        enhanced_question = f"关于播客 {self._format_time(timestamp)} 时间点附近的内容，{question}"
        return await self.chat(conv_id, enhanced_question)

    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    async def summarize_conversation(self, conv_id: str) -> str:
        """总结对话"""
        conv = self.get_conversation(conv_id)
        if not conv:
            return ""

        messages = [
            {"role": "system", "content": "请总结以下对话的要点，提取用户关心的问题和得到的答案。"},
            {"role": "user", "content": json.dumps(conv.get_history(), ensure_ascii=False)},
        ]

        return await self._call_llm(messages)

    async def suggest_questions(self, conv_id: str, count: int = 5) -> List[str]:
        """建议问题"""
        conv = self.get_conversation(conv_id)
        if not conv or not conv.context:
            return []

        prompt = f"""基于以下播客内容，生成 {count} 个有深度的问题供用户思考：

摘要：{conv.context.get('summary', '')}
关键词：{', '.join(conv.context.get('keywords', []))}

请直接返回问题列表，每行一个问题。"""

        response = await self._call_llm([
            {"role": "system", "content": "你是一个善于提问的播客分析师。"},
            {"role": "user", "content": prompt},
        ])

        questions = [q.strip().lstrip("0123456789.-) ") for q in response.split("\n") if q.strip()]
        return questions[:count]

    def load_podcast_context(self, podcast_id: str, content: Dict):
        """加载播客上下文"""
        self._podcast_contexts[podcast_id] = content
        logger.info(f"加载播客上下文: {podcast_id}")

    async def cross_podcast_query(self, query: str, podcast_ids: List[str] = None) -> str:
        """
        跨播客查询

        在多个播客中搜索相关信息
        """
        if podcast_ids:
            contexts = {pid: self._podcast_contexts.get(pid, {}) for pid in podcast_ids}
        else:
            contexts = self._podcast_contexts

        if not contexts:
            return "没有可用的播客上下文"

        # 构建查询上下文
        context_text = ""
        for pid, ctx in contexts.items():
            if ctx:
                context_text += f"\n\n【{ctx.get('title', pid)}】\n"
                context_text += f"摘要：{ctx.get('summary', '')[:500]}\n"
                context_text += f"关键词：{', '.join(ctx.get('keywords', [])[:10])}"

        prompt = f"""基于以下多个播客的内容，回答用户的问题：

{context_text}

用户问题：{query}

请综合多个播客的信息进行回答，并标注信息来源。"""

        return await self._call_llm([
            {"role": "system", "content": "你是一个博学的播客知识助手，擅长跨内容关联分析。"},
            {"role": "user", "content": prompt},
        ])
