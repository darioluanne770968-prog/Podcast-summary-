"""
用户画像与偏好管理模块
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict
import json
from datetime import datetime

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


@dataclass
class UserPreferences:
    """用户偏好设置"""
    # 内容偏好
    preferred_topics: List[str] = field(default_factory=list)
    preferred_length: str = "medium"  # short, medium, long
    preferred_language: str = "zh"

    # 摘要风格偏好
    summary_style: str = "detailed"  # brief, detailed, bullet_points
    include_quotes: bool = True
    include_timestamps: bool = True
    include_qa: bool = True

    # 导出偏好
    default_export_format: str = "markdown"
    auto_export_notion: bool = False
    auto_generate_audio: bool = False

    # LLM 偏好
    preferred_llm: str = "claude"
    temperature: float = 0.7

    def to_dict(self) -> dict:
        return {
            "preferred_topics": self.preferred_topics,
            "preferred_length": self.preferred_length,
            "preferred_language": self.preferred_language,
            "summary_style": self.summary_style,
            "include_quotes": self.include_quotes,
            "include_timestamps": self.include_timestamps,
            "include_qa": self.include_qa,
            "default_export_format": self.default_export_format,
            "auto_export_notion": self.auto_export_notion,
            "auto_generate_audio": self.auto_generate_audio,
            "preferred_llm": self.preferred_llm,
            "temperature": self.temperature,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    name: str
    email: Optional[str] = None
    preferences: UserPreferences = field(default_factory=UserPreferences)

    # 使用统计
    total_podcasts_analyzed: int = 0
    total_minutes_analyzed: float = 0
    favorite_topics: Dict[str, int] = field(default_factory=dict)
    analysis_history: List[dict] = field(default_factory=list)

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def update_stats(
        self,
        podcast_title: str,
        duration_minutes: float,
        topics: List[str],
    ):
        """更新使用统计"""
        self.total_podcasts_analyzed += 1
        self.total_minutes_analyzed += duration_minutes

        # 更新话题统计
        for topic in topics:
            self.favorite_topics[topic] = self.favorite_topics.get(topic, 0) + 1

        # 添加到历史记录
        self.analysis_history.append({
            "title": podcast_title,
            "duration": duration_minutes,
            "topics": topics,
            "timestamp": datetime.now().isoformat(),
        })

        # 只保留最近100条记录
        if len(self.analysis_history) > 100:
            self.analysis_history = self.analysis_history[-100:]

        self.updated_at = datetime.now().isoformat()

    def get_top_topics(self, n: int = 10) -> List[tuple]:
        """获取最常分析的话题"""
        sorted_topics = sorted(
            self.favorite_topics.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_topics[:n]

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "preferences": self.preferences.to_dict(),
            "total_podcasts_analyzed": self.total_podcasts_analyzed,
            "total_minutes_analyzed": self.total_minutes_analyzed,
            "favorite_topics": self.favorite_topics,
            "analysis_history": self.analysis_history[-20:],  # 只保存最近20条
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        prefs = UserPreferences.from_dict(data.get("preferences", {}))
        return cls(
            user_id=data.get("user_id", ""),
            name=data.get("name", ""),
            email=data.get("email"),
            preferences=prefs,
            total_podcasts_analyzed=data.get("total_podcasts_analyzed", 0),
            total_minutes_analyzed=data.get("total_minutes_analyzed", 0),
            favorite_topics=data.get("favorite_topics", {}),
            analysis_history=data.get("analysis_history", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class PreferenceManager:
    """偏好管理器"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary"
        ensure_dir(self.storage_dir)
        self.profiles_file = self.storage_dir / "profiles.json"
        self._profiles: Dict[str, UserProfile] = {}
        self._load_profiles()

    def _load_profiles(self):
        """加载用户配置"""
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, profile_data in data.items():
                        self._profiles[user_id] = UserProfile.from_dict(profile_data)
            except Exception as e:
                logger.error(f"加载用户配置失败: {e}")

    def _save_profiles(self):
        """保存用户配置"""
        try:
            data = {uid: profile.to_dict() for uid, profile in self._profiles.items()}
            with open(self.profiles_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户配置失败: {e}")

    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户配置"""
        return self._profiles.get(user_id)

    def create_profile(
        self,
        user_id: str,
        name: str,
        email: Optional[str] = None,
    ) -> UserProfile:
        """创建用户配置"""
        profile = UserProfile(user_id=user_id, name=name, email=email)
        self._profiles[user_id] = profile
        self._save_profiles()
        logger.info(f"创建用户配置: {user_id}")
        return profile

    def update_profile(self, profile: UserProfile):
        """更新用户配置"""
        profile.updated_at = datetime.now().isoformat()
        self._profiles[profile.user_id] = profile
        self._save_profiles()

    def delete_profile(self, user_id: str):
        """删除用户配置"""
        if user_id in self._profiles:
            del self._profiles[user_id]
            self._save_profiles()
            logger.info(f"删除用户配置: {user_id}")

    def get_or_create_default(self) -> UserProfile:
        """获取或创建默认用户"""
        default_id = "default"
        if default_id not in self._profiles:
            return self.create_profile(default_id, "Default User")
        return self._profiles[default_id]

    def learn_preferences(
        self,
        user_id: str,
        feedback: dict,
    ):
        """
        从用户反馈中学习偏好

        Args:
            user_id: 用户 ID
            feedback: 反馈数据
        """
        profile = self.get_profile(user_id)
        if not profile:
            return

        # 根据反馈更新偏好
        if "liked_summary_style" in feedback:
            profile.preferences.summary_style = feedback["liked_summary_style"]

        if "useful_sections" in feedback:
            sections = feedback["useful_sections"]
            profile.preferences.include_quotes = "quotes" in sections
            profile.preferences.include_qa = "qa" in sections

        if "preferred_length" in feedback:
            profile.preferences.preferred_length = feedback["preferred_length"]

        self.update_profile(profile)
        logger.info(f"更新用户偏好: {user_id}")
