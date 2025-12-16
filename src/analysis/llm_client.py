"""
LLM 客户端模块

支持 Claude (Anthropic) 和 GPT (OpenAI)
"""

import json
from enum import Enum
from typing import Optional, List, Dict, Any, Union

from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings, LLMProvider
from ..utils import get_logger

logger = get_logger(__name__)


class LLMClient:
    """统一的 LLM 客户端"""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化 LLM 客户端

        Args:
            provider: LLM 提供商 (claude 或 openai)
            api_key: API 密钥
            model: 模型名称
        """
        settings = get_settings()

        self.provider = provider or settings.default_llm_provider

        if self.provider == LLMProvider.CLAUDE:
            self.api_key = api_key or settings.anthropic_api_key
            self.model = model or settings.claude_model
            self._client = self._init_claude_client()
        else:
            self.api_key = api_key or settings.openai_api_key
            self.model = model or settings.openai_model
            self._client = self._init_openai_client()

        logger.info(f"LLM 客户端初始化: {self.provider.value} / {self.model}")

    def _init_claude_client(self):
        """初始化 Claude 客户端"""
        if not self.api_key:
            raise ValueError("需要 ANTHROPIC_API_KEY")

        try:
            from anthropic import Anthropic
            return Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("请安装 anthropic: pip install anthropic")

    def _init_openai_client(self):
        """初始化 OpenAI 客户端"""
        if not self.api_key:
            raise ValueError("需要 OPENAI_API_KEY")

        try:
            from openai import OpenAI
            return OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            system: 系统提示
            temperature: 温度参数
            max_tokens: 最大输出 token 数
            json_mode: 是否返回 JSON

        Returns:
            模型响应文本
        """
        if self.provider == LLMProvider.CLAUDE:
            return self._chat_claude(
                messages, system, temperature, max_tokens, json_mode
            )
        else:
            return self._chat_openai(
                messages, system, temperature, max_tokens, json_mode
            )

    def _chat_claude(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """Claude API 调用"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        return response.content[0].text

    def _chat_openai(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """OpenAI API 调用"""
        full_messages = []

        if system:
            full_messages.append({"role": "system", "content": system})

        full_messages.extend(messages)

        kwargs = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        简单的补全请求

        Args:
            prompt: 提示文本
            system: 系统提示
            **kwargs: 其他参数

        Returns:
            模型响应
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, system=system, **kwargs)

    def parse_json_response(self, response: str) -> Union[dict, list]:
        """
        解析 JSON 响应

        Args:
            response: 模型响应文本

        Returns:
            解析后的 JSON 对象
        """
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 块
        import re
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找到 JSON 数组或对象
        json_match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法解析 JSON 响应: {response[:200]}...")
