"""
个性化与协作模块

功能：
- 用户画像/偏好学习
- 自定义分析模板
- 收藏管理
- 团队协作
"""

from .user_profile import UserProfile, PreferenceManager
from .templates import TemplateManager, AnalysisTemplate
from .collections import CollectionManager, Collection

__all__ = [
    "UserProfile",
    "PreferenceManager",
    "TemplateManager",
    "AnalysisTemplate",
    "CollectionManager",
    "Collection",
]
