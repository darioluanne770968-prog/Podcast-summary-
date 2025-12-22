"""
协作会话管理
管理多人协作的实时会话
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
import asyncio


class SessionRole(Enum):
    """会话角色"""
    OWNER = "owner"  # 所有者
    EDITOR = "editor"  # 编辑者
    COMMENTER = "commenter"  # 评论者
    VIEWER = "viewer"  # 观看者


class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ARCHIVED = "archived"


@dataclass
class Participant:
    """参与者"""
    id: str
    name: str
    email: str
    role: SessionRole
    joined_at: datetime
    cursor_position: float = 0.0  # 当前播放位置
    is_online: bool = True
    color: str = "#3498db"  # 用于标注的颜色
    last_activity: datetime = field(default_factory=datetime.now)


@dataclass
class SessionEvent:
    """会话事件"""
    id: str
    event_type: str
    participant_id: str
    timestamp: datetime
    data: Dict[str, Any]


@dataclass
class CollaborationSessionData:
    """协作会话数据"""
    id: str
    podcast_id: str
    title: str
    created_at: datetime
    created_by: str
    status: SessionStatus
    participants: List[Participant]
    events: List[SessionEvent]
    settings: Dict[str, Any]


class CollaborationSession:
    """协作会话管理器"""

    def __init__(self, podcast_id: str, title: str, creator_id: str):
        self.session_id = str(uuid.uuid4())
        self.podcast_id = podcast_id
        self.title = title
        self.created_at = datetime.now()
        self.created_by = creator_id
        self.status = SessionStatus.ACTIVE

        self.participants: Dict[str, Participant] = {}
        self.events: List[SessionEvent] = []
        self.event_listeners: Dict[str, List[callable]] = {}

        self.settings = {
            "allow_anonymous": False,
            "auto_pause_on_annotation": True,
            "sync_playback": True,
            "max_participants": 50,
            "enable_chat": True,
            "enable_video_call": False,
            "annotation_permissions": ["editor", "owner"],
            "comment_permissions": ["editor", "owner", "commenter"]
        }

        # 用于标注的颜色池
        self.color_pool = [
            "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
            "#1abc9c", "#e67e22", "#34495e", "#16a085", "#d35400"
        ]
        self.used_colors: Set[str] = set()

    def join(
        self,
        user_id: str,
        name: str,
        email: str,
        role: SessionRole = SessionRole.VIEWER
    ) -> Participant:
        """
        加入协作会话

        Args:
            user_id: 用户ID
            name: 用户名
            email: 邮箱
            role: 角色

        Returns:
            参与者信息
        """
        if len(self.participants) >= self.settings["max_participants"]:
            raise ValueError("会话已达到最大参与人数")

        # 分配颜色
        color = self._assign_color()

        participant = Participant(
            id=user_id,
            name=name,
            email=email,
            role=role,
            joined_at=datetime.now(),
            color=color
        )

        self.participants[user_id] = participant

        # 记录事件
        self._add_event("join", user_id, {"name": name, "role": role.value})

        # 广播加入事件
        self._broadcast("participant_joined", participant)

        return participant

    def leave(self, user_id: str):
        """离开协作会话"""
        if user_id not in self.participants:
            return

        participant = self.participants[user_id]
        participant.is_online = False

        # 回收颜色
        self.used_colors.discard(participant.color)

        # 记录事件
        self._add_event("leave", user_id, {})

        # 广播离开事件
        self._broadcast("participant_left", {"user_id": user_id})

    def _assign_color(self) -> str:
        """分配颜色"""
        available = [c for c in self.color_pool if c not in self.used_colors]

        if available:
            color = available[0]
        else:
            # 如果颜色用完，生成随机颜色
            import random
            color = f"#{random.randint(0, 0xFFFFFF):06x}"

        self.used_colors.add(color)
        return color

    def update_cursor(self, user_id: str, position: float):
        """更新用户光标位置（当前播放位置）"""
        if user_id not in self.participants:
            return

        self.participants[user_id].cursor_position = position
        self.participants[user_id].last_activity = datetime.now()

        # 广播光标更新
        self._broadcast("cursor_update", {
            "user_id": user_id,
            "position": position
        })

    def sync_playback(self, initiator_id: str, position: float, action: str = "seek"):
        """
        同步播放位置

        Args:
            initiator_id: 发起者ID
            position: 播放位置
            action: 动作类型 (play, pause, seek)
        """
        if not self.settings["sync_playback"]:
            return

        # 检查权限
        if initiator_id not in self.participants:
            return

        participant = self.participants[initiator_id]
        if participant.role not in [SessionRole.OWNER, SessionRole.EDITOR]:
            return

        # 记录事件
        self._add_event("playback_sync", initiator_id, {
            "position": position,
            "action": action
        })

        # 广播同步事件
        self._broadcast("playback_sync", {
            "initiator": initiator_id,
            "position": position,
            "action": action
        })

    def change_role(self, admin_id: str, target_user_id: str, new_role: SessionRole):
        """更改用户角色"""
        # 验证权限
        if admin_id not in self.participants:
            raise PermissionError("无权操作")

        admin = self.participants[admin_id]
        if admin.role != SessionRole.OWNER:
            raise PermissionError("只有所有者可以更改角色")

        if target_user_id not in self.participants:
            raise ValueError("用户不存在")

        old_role = self.participants[target_user_id].role
        self.participants[target_user_id].role = new_role

        # 记录事件
        self._add_event("role_change", admin_id, {
            "target_user": target_user_id,
            "old_role": old_role.value,
            "new_role": new_role.value
        })

        # 广播角色变更
        self._broadcast("role_changed", {
            "user_id": target_user_id,
            "new_role": new_role.value
        })

    def update_settings(self, admin_id: str, settings: Dict[str, Any]):
        """更新会话设置"""
        if admin_id not in self.participants:
            raise PermissionError("无权操作")

        admin = self.participants[admin_id]
        if admin.role != SessionRole.OWNER:
            raise PermissionError("只有所有者可以更改设置")

        self.settings.update(settings)

        # 记录事件
        self._add_event("settings_update", admin_id, {"settings": settings})

        # 广播设置变更
        self._broadcast("settings_updated", settings)

    def pause_session(self, admin_id: str):
        """暂停会话"""
        if admin_id not in self.participants:
            return

        if self.participants[admin_id].role != SessionRole.OWNER:
            return

        self.status = SessionStatus.PAUSED
        self._add_event("session_paused", admin_id, {})
        self._broadcast("session_paused", {})

    def resume_session(self, admin_id: str):
        """恢复会话"""
        if admin_id not in self.participants:
            return

        if self.participants[admin_id].role != SessionRole.OWNER:
            return

        self.status = SessionStatus.ACTIVE
        self._add_event("session_resumed", admin_id, {})
        self._broadcast("session_resumed", {})

    def end_session(self, admin_id: str):
        """结束会话"""
        if admin_id not in self.participants:
            return

        if self.participants[admin_id].role != SessionRole.OWNER:
            return

        self.status = SessionStatus.ENDED
        self._add_event("session_ended", admin_id, {})
        self._broadcast("session_ended", {})

    def _add_event(self, event_type: str, participant_id: str, data: Dict[str, Any]):
        """添加事件"""
        event = SessionEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            participant_id=participant_id,
            timestamp=datetime.now(),
            data=data
        )
        self.events.append(event)

    def _broadcast(self, event_type: str, data: Any):
        """广播事件"""
        listeners = self.event_listeners.get(event_type, [])
        for listener in listeners:
            try:
                listener(data)
            except Exception as e:
                print(f"Event listener error: {e}")

    def on(self, event_type: str, callback: callable):
        """注册事件监听器"""
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(callback)

    def off(self, event_type: str, callback: callable):
        """移除事件监听器"""
        if event_type in self.event_listeners:
            self.event_listeners[event_type] = [
                cb for cb in self.event_listeners[event_type] if cb != callback
            ]

    def get_online_participants(self) -> List[Participant]:
        """获取在线参与者"""
        return [p for p in self.participants.values() if p.is_online]

    def get_participant_count(self) -> Dict[str, int]:
        """获取参与者统计"""
        return {
            "total": len(self.participants),
            "online": len([p for p in self.participants.values() if p.is_online]),
            "by_role": {
                role.value: len([p for p in self.participants.values() if p.role == role])
                for role in SessionRole
            }
        }

    def get_activity_log(
        self,
        limit: int = 50,
        event_types: Optional[List[str]] = None
    ) -> List[SessionEvent]:
        """获取活动日志"""
        events = self.events

        if event_types:
            events = [e for e in events if e.event_type in event_types]

        return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]

    def export_session_data(self) -> CollaborationSessionData:
        """导出会话数据"""
        return CollaborationSessionData(
            id=self.session_id,
            podcast_id=self.podcast_id,
            title=self.title,
            created_at=self.created_at,
            created_by=self.created_by,
            status=self.status,
            participants=list(self.participants.values()),
            events=self.events,
            settings=self.settings
        )

    def generate_share_link(self, role: SessionRole = SessionRole.VIEWER) -> str:
        """生成分享链接"""
        import hashlib

        # 生成唯一token
        token_data = f"{self.session_id}:{role.value}:{datetime.now().isoformat()}"
        token = hashlib.sha256(token_data.encode()).hexdigest()[:16]

        return f"https://podcast-collab.app/join/{self.session_id}?token={token}&role={role.value}"

    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        return {
            "session_id": self.session_id,
            "title": self.title,
            "podcast_id": self.podcast_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "duration": (datetime.now() - self.created_at).total_seconds(),
            "participants": self.get_participant_count(),
            "total_events": len(self.events),
            "settings": self.settings
        }
