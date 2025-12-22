"""
用户画像管理
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    favorite_topics: List[str] = field(default_factory=list)
    preferred_duration_min: float = 15.0
    preferred_duration_max: float = 60.0
    preferred_languages: List[str] = field(default_factory=lambda: ["zh"])
    listening_history: List[Dict[str, Any]] = field(default_factory=list)
    liked_podcasts: List[str] = field(default_factory=list)
    disliked_podcasts: List[str] = field(default_factory=list)
    total_listening_time: float = 0.0
    avg_completion_rate: float = 0.0


class UserProfileManager:
    """用户画像管理器"""

    def __init__(self):
        self.profiles: Dict[str, UserProfile] = {}

    def get_or_create(self, user_id: str) -> UserProfile:
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(user_id=user_id)
        return self.profiles[user_id]

    def update_listening_history(self, user_id: str, podcast_id: str, duration: float, completion: float):
        profile = self.get_or_create(user_id)
        profile.listening_history.append({
            "podcast_id": podcast_id,
            "duration": duration,
            "completion": completion,
            "timestamp": datetime.now().isoformat()
        })
        profile.total_listening_time += duration * completion

    def like_podcast(self, user_id: str, podcast_id: str):
        profile = self.get_or_create(user_id)
        if podcast_id not in profile.liked_podcasts:
            profile.liked_podcasts.append(podcast_id)
        if podcast_id in profile.disliked_podcasts:
            profile.disliked_podcasts.remove(podcast_id)

    def dislike_podcast(self, user_id: str, podcast_id: str):
        profile = self.get_or_create(user_id)
        if podcast_id not in profile.disliked_podcasts:
            profile.disliked_podcasts.append(podcast_id)
        if podcast_id in profile.liked_podcasts:
            profile.liked_podcasts.remove(podcast_id)

    def add_favorite_topic(self, user_id: str, topic: str):
        profile = self.get_or_create(user_id)
        if topic not in profile.favorite_topics:
            profile.favorite_topics.append(topic)
