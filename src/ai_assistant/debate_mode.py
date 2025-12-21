"""
辩论模式

AI 扮演不同观点与用户讨论播客内容
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json

from ..utils import get_logger

logger = get_logger(__name__)


class DebateStyle(str, Enum):
    """辩论风格"""
    SOCRATIC = "socratic"  # 苏格拉底式提问
    DEVILS_ADVOCATE = "devils_advocate"  # 魔鬼代言人
    BALANCED = "balanced"  # 平衡讨论
    SUPPORTIVE = "supportive"  # 支持性讨论


@dataclass
class Viewpoint:
    """观点"""
    id: str
    speaker: str
    position: str  # 立场
    arguments: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    counterarguments: List[str] = field(default_factory=list)
    source_quotes: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "speaker": self.speaker,
            "position": self.position,
            "arguments": self.arguments,
            "evidence": self.evidence,
            "counterarguments": self.counterarguments,
            "source_quotes": self.source_quotes,
        }


@dataclass
class DebateRound:
    """辩论回合"""
    round_number: int
    user_argument: str
    ai_response: str
    ai_role: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DebateSession:
    """辩论会话"""
    id: str
    topic: str
    user_position: str
    ai_position: str
    style: DebateStyle
    rounds: List[DebateRound] = field(default_factory=list)
    viewpoints: List[Viewpoint] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "user_position": self.user_position,
            "ai_position": self.ai_position,
            "style": self.style.value,
            "rounds": [
                {
                    "round": r.round_number,
                    "user": r.user_argument,
                    "ai": r.ai_response,
                    "ai_role": r.ai_role,
                }
                for r in self.rounds
            ],
            "viewpoints": [v.to_dict() for v in self.viewpoints],
            "created_at": self.created_at,
        }


class DebateSimulator:
    """
    辩论模拟器

    功能：
    - 提取播客中的观点
    - 模拟不同立场的辩论
    - 苏格拉底式提问
    - 生成辩论总结
    """

    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        self._sessions: Dict[str, DebateSession] = {}

    async def extract_viewpoints(
        self,
        podcast_content: Dict,
    ) -> List[Viewpoint]:
        """
        从播客内容中提取观点

        Args:
            podcast_content: 播客分析结果

        Returns:
            观点列表
        """
        transcript = podcast_content.get("transcript", "")
        speakers = podcast_content.get("speakers", [])

        prompt = f"""分析以下播客对话，提取每个说话人的主要观点：

对话内容：
{transcript[:8000]}

对于每个观点，请提供：
1. 说话人
2. 立场/观点
3. 支持论据
4. 引用的证据
5. 可能的反驳

请以 JSON 格式返回，示例：
[
  {{
    "speaker": "主持人",
    "position": "AI将取代大部分工作",
    "arguments": ["自动化效率更高", "成本更低"],
    "evidence": ["某研究显示...", "某公司案例..."],
    "counterarguments": ["创造新工作", "人类创造力不可替代"]
  }}
]"""

        response = await self._call_llm([
            {"role": "system", "content": "你是一个擅长分析辩论的专家。"},
            {"role": "user", "content": prompt},
        ])

        try:
            # 尝试解析 JSON
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                viewpoints_data = json.loads(json_match.group())
                viewpoints = []
                for i, vp in enumerate(viewpoints_data):
                    viewpoints.append(Viewpoint(
                        id=f"vp_{i}",
                        speaker=vp.get("speaker", ""),
                        position=vp.get("position", ""),
                        arguments=vp.get("arguments", []),
                        evidence=vp.get("evidence", []),
                        counterarguments=vp.get("counterarguments", []),
                    ))
                return viewpoints
        except:
            pass

        return []

    async def start_debate(
        self,
        topic: str,
        user_position: str,
        podcast_content: Optional[Dict] = None,
        style: DebateStyle = DebateStyle.DEVILS_ADVOCATE,
    ) -> DebateSession:
        """
        开始辩论

        Args:
            topic: 辩论主题
            user_position: 用户立场
            podcast_content: 播客内容（可选）
            style: 辩论风格

        Returns:
            辩论会话
        """
        import uuid
        session_id = str(uuid.uuid4())[:8]

        # 确定 AI 立场
        if style == DebateStyle.DEVILS_ADVOCATE:
            ai_position = f"反对 '{user_position}'"
        elif style == DebateStyle.SUPPORTIVE:
            ai_position = f"支持 '{user_position}'"
        else:
            ai_position = "中立分析"

        session = DebateSession(
            id=session_id,
            topic=topic,
            user_position=user_position,
            ai_position=ai_position,
            style=style,
        )

        if podcast_content:
            session.context = {
                "summary": podcast_content.get("summary", ""),
                "keywords": podcast_content.get("keywords", []),
            }
            session.viewpoints = await self.extract_viewpoints(podcast_content)

        self._sessions[session_id] = session
        logger.info(f"开始辩论: {topic}")
        return session

    async def debate_round(
        self,
        session_id: str,
        user_argument: str,
    ) -> str:
        """
        进行一轮辩论

        Args:
            session_id: 会话 ID
            user_argument: 用户论点

        Returns:
            AI 回应
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")

        round_number = len(session.rounds) + 1

        # 构建提示
        system_prompt = self._build_debate_prompt(session)

        # 构建对话历史
        messages = [{"role": "system", "content": system_prompt}]
        for r in session.rounds[-5:]:  # 最近 5 轮
            messages.append({"role": "user", "content": r.user_argument})
            messages.append({"role": "assistant", "content": r.ai_response})
        messages.append({"role": "user", "content": user_argument})

        # 获取 AI 回应
        ai_response = await self._call_llm(messages)

        # 记录回合
        debate_round = DebateRound(
            round_number=round_number,
            user_argument=user_argument,
            ai_response=ai_response,
            ai_role=session.ai_position,
        )
        session.rounds.append(debate_round)

        return ai_response

    def _build_debate_prompt(self, session: DebateSession) -> str:
        """构建辩论提示"""
        style_instructions = {
            DebateStyle.SOCRATIC: """你采用苏格拉底式提问法：
- 不直接反驳，而是通过提问引导思考
- 揭示论证中的假设和漏洞
- 帮助对方深化和完善观点""",

            DebateStyle.DEVILS_ADVOCATE: """你扮演魔鬼代言人：
- 积极寻找并指出论证的弱点
- 提出强有力的反驳
- 挑战所有假设
- 但保持理性和尊重""",

            DebateStyle.BALANCED: """你进行平衡讨论：
- 公正地分析双方观点
- 指出各自的优缺点
- 提供多角度思考
- 寻找共同点""",

            DebateStyle.SUPPORTIVE: """你进行支持性讨论：
- 帮助完善和强化用户的论点
- 补充更多支持证据
- 预判可能的反驳并准备回应
- 深化论证逻辑""",
        }

        prompt = f"""你正在参与一场关于「{session.topic}」的辩论。

你的立场：{session.ai_position}
用户立场：{session.user_position}

{style_instructions.get(session.style, "")}

辩论规则：
1. 保持逻辑清晰
2. 引用具体例子和证据
3. 承认对方的合理之处
4. 每次回应控制在 200 字以内
"""

        if session.context.get("summary"):
            prompt += f"\n\n背景资料（来自播客）：\n{session.context['summary'][:500]}"

        if session.viewpoints:
            prompt += "\n\n播客中的相关观点：\n"
            for vp in session.viewpoints[:3]:
                prompt += f"- {vp.speaker}: {vp.position}\n"

        return prompt

    async def socratic_questioning(
        self,
        statement: str,
        depth: int = 3,
    ) -> List[str]:
        """
        苏格拉底式追问

        对一个陈述进行连续追问

        Args:
            statement: 初始陈述
            depth: 追问深度

        Returns:
            问题列表
        """
        prompt = f"""对以下陈述进行苏格拉底式追问，生成 {depth} 个由浅入深的问题：

陈述：「{statement}」

要求：
1. 第一个问题澄清定义和假设
2. 中间问题探索逻辑和证据
3. 最后一个问题挑战根本假设

直接返回问题列表，每行一个。"""

        response = await self._call_llm([
            {"role": "system", "content": "你是一位善于苏格拉底式提问的哲学家。"},
            {"role": "user", "content": prompt},
        ])

        questions = [q.strip().lstrip("0123456789.-) ") for q in response.split("\n") if q.strip()]
        return questions[:depth]

    async def generate_debate_summary(self, session_id: str) -> Dict[str, Any]:
        """
        生成辩论总结

        Args:
            session_id: 会话 ID

        Returns:
            辩论总结
        """
        session = self._sessions.get(session_id)
        if not session:
            return {}

        # 收集所有论点
        user_arguments = [r.user_argument for r in session.rounds]
        ai_arguments = [r.ai_response for r in session.rounds]

        debate_text = ""
        for r in session.rounds:
            debate_text += f"用户: {r.user_argument}\nAI: {r.ai_response}\n\n"

        prompt = f"""总结以下辩论：

主题：{session.topic}
用户立场：{session.user_position}
AI立场：{session.ai_position}

辩论内容：
{debate_text}

请提供：
1. 核心分歧点
2. 用户的主要论点
3. AI的主要论点
4. 达成的共识（如有）
5. 未解决的问题
6. 进一步思考的方向"""

        summary = await self._call_llm([
            {"role": "system", "content": "你是一位擅长辩论分析的专家。"},
            {"role": "user", "content": prompt},
        ])

        return {
            "session": session.to_dict(),
            "rounds_count": len(session.rounds),
            "summary": summary,
        }

    async def generate_perspective_shift(
        self,
        topic: str,
        current_view: str,
    ) -> Dict[str, Any]:
        """
        生成视角转换

        帮助用户从不同角度看问题

        Args:
            topic: 主题
            current_view: 当前观点

        Returns:
            多角度分析
        """
        prompt = f"""关于「{topic}」，用户当前的观点是：「{current_view}」

请从以下角度提供不同的视角：
1. 反对者视角
2. 历史视角
3. 未来视角
4. 局外人视角
5. 受影响者视角

每个视角提供：
- 核心观点
- 主要理由
- 可能被忽视的因素"""

        response = await self._call_llm([
            {"role": "system", "content": "你是一位善于多角度思考的分析师。"},
            {"role": "user", "content": prompt},
        ])

        return {
            "topic": topic,
            "current_view": current_view,
            "alternative_perspectives": response,
        }

    async def _call_llm(self, messages: List[Dict]) -> str:
        """调用 LLM"""
        try:
            if self.llm_provider == "openai":
                from openai import AsyncOpenAI
                client = AsyncOpenAI()
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=1500,
                )
                return response.choices[0].message.content

            elif self.llm_provider == "anthropic":
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic()
                system = ""
                chat_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system = msg["content"]
                    else:
                        chat_messages.append(msg)

                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    system=system,
                    messages=chat_messages,
                )
                return response.content[0].text

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"处理出错: {str(e)}"
