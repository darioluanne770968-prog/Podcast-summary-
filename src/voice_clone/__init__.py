"""
虚拟克隆与内容再创作模块

功能：
- 声音克隆：用主播的声音生成新内容
- 风格迁移：把严肃播客转成轻松脱口秀风格
- 多语言配音：保留原声特征的实时翻译配音
- AI 续写：预测下一期可能讨论什么
"""

from .voice_cloner import VoiceCloner, VoiceProfile
from .style_transfer import StyleTransfer, PodcastStyle
from .multilingual import MultilingualDubbing
from .content_predictor import ContentPredictor

__all__ = [
    "VoiceCloner",
    "VoiceProfile",
    "StyleTransfer",
    "PodcastStyle",
    "MultilingualDubbing",
    "ContentPredictor",
]
