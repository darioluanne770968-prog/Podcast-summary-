"""
配置管理模块
"""

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """LLM 提供商"""
    CLAUDE = "claude"
    OPENAI = "openai"


class WhisperDevice(str, Enum):
    """Whisper 运行设备"""
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM API Keys
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    # 默认 LLM 提供商
    default_llm_provider: LLMProvider = Field(
        default=LLMProvider.CLAUDE, alias="DEFAULT_LLM_PROVIDER"
    )

    # Claude 配置
    claude_model: str = Field(default="claude-sonnet-4-20250514", alias="CLAUDE_MODEL")

    # OpenAI 配置
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL")

    # Notion 配置
    notion_api_key: Optional[str] = Field(default=None, alias="NOTION_API_KEY")
    notion_database_id: Optional[str] = Field(default=None, alias="NOTION_DATABASE_ID")

    # Whisper 配置
    whisper_model: str = Field(default="large-v3", alias="WHISPER_MODEL")
    whisper_device: WhisperDevice = Field(default=WhisperDevice.AUTO, alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="float16", alias="WHISPER_COMPUTE_TYPE")

    # HuggingFace Token
    hf_token: Optional[str] = Field(default=None, alias="HF_TOKEN")

    # 输出配置
    output_dir: Path = Field(default=Path("./output"), alias="OUTPUT_DIR")
    default_language: str = Field(default="zh", alias="DEFAULT_LANGUAGE")

    def get_whisper_device(self) -> str:
        """获取 Whisper 设备"""
        if self.whisper_device == WhisperDevice.AUTO:
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return self.whisper_device.value

    def validate_llm_config(self) -> bool:
        """验证 LLM 配置是否有效"""
        if self.default_llm_provider == LLMProvider.CLAUDE:
            return bool(self.anthropic_api_key)
        else:
            return bool(self.openai_api_key)

    def validate_notion_config(self) -> bool:
        """验证 Notion 配置是否有效"""
        return bool(self.notion_api_key and self.notion_database_id)


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def reload_settings() -> Settings:
    """重新加载配置"""
    global settings
    settings = Settings()
    return settings
