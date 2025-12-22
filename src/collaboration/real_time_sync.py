"""
实时同步系统
处理多用户实时协作的数据同步
"""

from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import uuid
import json


class SyncEventType(Enum):
    """同步事件类型"""
    CURSOR_MOVE = "cursor_move"  # 光标移动
    PLAYBACK_SYNC = "playback_sync"  # 播放同步
    ANNOTATION_CREATE = "annotation_create"  # 创建标注
    ANNOTATION_UPDATE = "annotation_update"  # 更新标注
    ANNOTATION_DELETE = "annotation_delete"  # 删除标注
    COMMENT_ADD = "comment_add"  # 添加评论
    COMMENT_EDIT = "comment_edit"  # 编辑评论
    REACTION_ADD = "reaction_add"  # 添加反应
    REACTION_REMOVE = "reaction_remove"  # 移除反应
    USER_JOIN = "user_join"  # 用户加入
    USER_LEAVE = "user_leave"  # 用户离开
    PRESENCE_UPDATE = "presence_update"  # 在线状态更新
    SELECTION_CHANGE = "selection_change"  # 选择变化


class ConflictResolution(Enum):
    """冲突解决策略"""
    LAST_WRITE_WINS = "last_write_wins"  # 最后写入优先
    FIRST_WRITE_WINS = "first_write_wins"  # 首次写入优先
    MERGE = "merge"  # 合并
    MANUAL = "manual"  # 手动解决


@dataclass
class SyncEvent:
    """同步事件"""
    id: str
    type: SyncEventType
    user_id: str
    timestamp: datetime
    data: Dict[str, Any]
    version: int
    acknowledged: bool = False


@dataclass
class UserPresence:
    """用户在线状态"""
    user_id: str
    name: str
    is_online: bool
    cursor_position: float
    current_selection: Optional[Dict[str, float]] = None
    last_active: datetime = field(default_factory=datetime.now)
    color: str = "#3498db"
    status: str = "active"  # active, idle, away


@dataclass
class SyncState:
    """同步状态"""
    session_id: str
    version: int
    last_sync: datetime
    pending_events: List[SyncEvent]
    confirmed_events: List[SyncEvent]
    conflicts: List[Dict[str, Any]]


class RealTimeSync:
    """实时同步管理器"""

    def __init__(
        self,
        session_id: str,
        conflict_resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS
    ):
        self.session_id = session_id
        self.conflict_resolution = conflict_resolution

        # 版本控制
        self.current_version = 0
        self.event_history: List[SyncEvent] = []
        self.pending_events: List[SyncEvent] = []

        # 用户状态
        self.user_presence: Dict[str, UserPresence] = {}
        self.connected_users: Set[str] = set()

        # 事件处理器
        self.event_handlers: Dict[SyncEventType, List[Callable]] = {}
        self.broadcast_handlers: List[Callable] = []

        # 冲突跟踪
        self.conflicts: List[Dict[str, Any]] = []

        # 心跳设置
        self.heartbeat_interval = 30  # 秒
        self.idle_timeout = 60  # 秒
        self.away_timeout = 300  # 秒

    async def connect(self, user_id: str, name: str, color: str = "#3498db"):
        """
        用户连接

        Args:
            user_id: 用户ID
            name: 用户名
            color: 用户颜色
        """
        self.connected_users.add(user_id)

        presence = UserPresence(
            user_id=user_id,
            name=name,
            is_online=True,
            cursor_position=0.0,
            color=color,
            status="active"
        )

        self.user_presence[user_id] = presence

        # 广播用户加入事件
        await self._broadcast_event(SyncEvent(
            id=str(uuid.uuid4()),
            type=SyncEventType.USER_JOIN,
            user_id=user_id,
            timestamp=datetime.now(),
            data={"name": name, "color": color},
            version=self.current_version
        ))

        # 发送当前状态给新用户
        return self._get_initial_state()

    async def disconnect(self, user_id: str):
        """用户断开连接"""
        self.connected_users.discard(user_id)

        if user_id in self.user_presence:
            self.user_presence[user_id].is_online = False
            self.user_presence[user_id].status = "offline"

        # 广播用户离开事件
        await self._broadcast_event(SyncEvent(
            id=str(uuid.uuid4()),
            type=SyncEventType.USER_LEAVE,
            user_id=user_id,
            timestamp=datetime.now(),
            data={},
            version=self.current_version
        ))

    def _get_initial_state(self) -> Dict[str, Any]:
        """获取初始状态"""
        return {
            "session_id": self.session_id,
            "version": self.current_version,
            "users": [
                {
                    "user_id": p.user_id,
                    "name": p.name,
                    "is_online": p.is_online,
                    "cursor_position": p.cursor_position,
                    "color": p.color,
                    "status": p.status
                }
                for p in self.user_presence.values()
            ],
            "recent_events": [
                self._serialize_event(e) for e in self.event_history[-50:]
            ]
        }

    async def send_event(self, event_type: SyncEventType, user_id: str, data: Dict[str, Any]) -> SyncEvent:
        """
        发送同步事件

        Args:
            event_type: 事件类型
            user_id: 用户ID
            data: 事件数据

        Returns:
            创建的事件
        """
        # 创建事件
        self.current_version += 1

        event = SyncEvent(
            id=str(uuid.uuid4()),
            type=event_type,
            user_id=user_id,
            timestamp=datetime.now(),
            data=data,
            version=self.current_version
        )

        # 检查冲突
        conflict = self._check_conflict(event)
        if conflict:
            resolved_event = await self._resolve_conflict(event, conflict)
            if resolved_event:
                event = resolved_event

        # 添加到历史
        self.event_history.append(event)

        # 更新用户活动时间
        if user_id in self.user_presence:
            self.user_presence[user_id].last_active = datetime.now()
            self.user_presence[user_id].status = "active"

        # 广播事件
        await self._broadcast_event(event)

        # 触发事件处理器
        await self._trigger_handlers(event)

        return event

    async def update_cursor(self, user_id: str, position: float):
        """更新用户光标位置"""
        if user_id in self.user_presence:
            self.user_presence[user_id].cursor_position = position
            self.user_presence[user_id].last_active = datetime.now()

        await self.send_event(
            SyncEventType.CURSOR_MOVE,
            user_id,
            {"position": position}
        )

    async def update_selection(
        self,
        user_id: str,
        start: float,
        end: float
    ):
        """更新用户选择范围"""
        if user_id in self.user_presence:
            self.user_presence[user_id].current_selection = {
                "start": start,
                "end": end
            }

        await self.send_event(
            SyncEventType.SELECTION_CHANGE,
            user_id,
            {"start": start, "end": end}
        )

    async def sync_playback(
        self,
        user_id: str,
        position: float,
        action: str = "seek"
    ):
        """
        同步播放状态

        Args:
            user_id: 用户ID
            position: 播放位置
            action: 动作 (play, pause, seek)
        """
        await self.send_event(
            SyncEventType.PLAYBACK_SYNC,
            user_id,
            {"position": position, "action": action}
        )

    def _check_conflict(self, event: SyncEvent) -> Optional[SyncEvent]:
        """检查事件冲突"""
        # 查找同一时间范围内的相关事件
        conflict_window = 1.0  # 1秒内的事件视为可能冲突

        for historical_event in reversed(self.event_history[-20:]):
            # 跳过自己的事件
            if historical_event.user_id == event.user_id:
                continue

            # 检查时间窗口
            time_diff = (event.timestamp - historical_event.timestamp).total_seconds()
            if time_diff > conflict_window:
                break

            # 检查事件类型冲突
            if self._events_conflict(event, historical_event):
                return historical_event

        return None

    def _events_conflict(self, event1: SyncEvent, event2: SyncEvent) -> bool:
        """检查两个事件是否冲突"""
        # 标注冲突：同一位置的创建/更新
        if event1.type in [SyncEventType.ANNOTATION_CREATE, SyncEventType.ANNOTATION_UPDATE]:
            if event2.type in [SyncEventType.ANNOTATION_CREATE, SyncEventType.ANNOTATION_UPDATE]:
                # 检查位置重叠
                pos1 = event1.data.get("position", 0)
                pos2 = event2.data.get("position", 0)
                if abs(pos1 - pos2) < 5:  # 5秒内视为重叠
                    return True

        # 评论冲突：编辑同一评论
        if event1.type == SyncEventType.COMMENT_EDIT and event2.type == SyncEventType.COMMENT_EDIT:
            if event1.data.get("comment_id") == event2.data.get("comment_id"):
                return True

        return False

    async def _resolve_conflict(
        self,
        event: SyncEvent,
        conflicting_event: SyncEvent
    ) -> Optional[SyncEvent]:
        """解决冲突"""
        conflict_record = {
            "id": str(uuid.uuid4()),
            "event": self._serialize_event(event),
            "conflicting_event": self._serialize_event(conflicting_event),
            "resolution": None,
            "timestamp": datetime.now().isoformat()
        }

        if self.conflict_resolution == ConflictResolution.LAST_WRITE_WINS:
            # 最后写入优先 - 当前事件获胜
            conflict_record["resolution"] = "last_write_wins"
            self.conflicts.append(conflict_record)
            return event

        elif self.conflict_resolution == ConflictResolution.FIRST_WRITE_WINS:
            # 首次写入优先 - 拒绝当前事件
            conflict_record["resolution"] = "first_write_wins_rejected"
            self.conflicts.append(conflict_record)
            return None

        elif self.conflict_resolution == ConflictResolution.MERGE:
            # 尝试合并
            merged_event = self._merge_events(event, conflicting_event)
            conflict_record["resolution"] = "merged"
            conflict_record["merged_result"] = self._serialize_event(merged_event)
            self.conflicts.append(conflict_record)
            return merged_event

        else:
            # 手动解决 - 标记为待解决
            conflict_record["resolution"] = "pending_manual"
            self.conflicts.append(conflict_record)
            return event

    def _merge_events(self, event1: SyncEvent, event2: SyncEvent) -> SyncEvent:
        """合并两个事件"""
        # 简单合并：合并数据
        merged_data = {**event2.data, **event1.data}

        return SyncEvent(
            id=str(uuid.uuid4()),
            type=event1.type,
            user_id=event1.user_id,
            timestamp=event1.timestamp,
            data=merged_data,
            version=self.current_version
        )

    async def _broadcast_event(self, event: SyncEvent):
        """广播事件给所有连接的用户"""
        serialized = self._serialize_event(event)

        for handler in self.broadcast_handlers:
            try:
                await handler(serialized)
            except Exception as e:
                print(f"Broadcast error: {e}")

    async def _trigger_handlers(self, event: SyncEvent):
        """触发事件处理器"""
        handlers = self.event_handlers.get(event.type, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Handler error: {e}")

    def _serialize_event(self, event: SyncEvent) -> Dict[str, Any]:
        """序列化事件"""
        return {
            "id": event.id,
            "type": event.type.value,
            "user_id": event.user_id,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data,
            "version": event.version
        }

    def on(self, event_type: SyncEventType, handler: Callable):
        """注册事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def on_broadcast(self, handler: Callable):
        """注册广播处理器"""
        self.broadcast_handlers.append(handler)

    async def heartbeat(self, user_id: str):
        """处理心跳"""
        if user_id in self.user_presence:
            presence = self.user_presence[user_id]
            presence.last_active = datetime.now()
            presence.is_online = True

    async def check_user_status(self):
        """检查用户状态（定期调用）"""
        now = datetime.now()

        for user_id, presence in self.user_presence.items():
            if not presence.is_online:
                continue

            idle_seconds = (now - presence.last_active).total_seconds()

            if idle_seconds > self.away_timeout:
                presence.status = "away"
            elif idle_seconds > self.idle_timeout:
                presence.status = "idle"
            else:
                presence.status = "active"

            # 广播状态变化
            await self.send_event(
                SyncEventType.PRESENCE_UPDATE,
                user_id,
                {"status": presence.status}
            )

    def get_online_users(self) -> List[UserPresence]:
        """获取在线用户"""
        return [p for p in self.user_presence.values() if p.is_online]

    def get_user_cursors(self) -> Dict[str, float]:
        """获取所有用户光标位置"""
        return {
            p.user_id: p.cursor_position
            for p in self.user_presence.values()
            if p.is_online
        }

    def get_sync_state(self) -> SyncState:
        """获取同步状态"""
        return SyncState(
            session_id=self.session_id,
            version=self.current_version,
            last_sync=datetime.now(),
            pending_events=self.pending_events,
            confirmed_events=self.event_history[-100:],
            conflicts=self.conflicts
        )

    def get_events_since(self, version: int) -> List[SyncEvent]:
        """获取指定版本之后的事件"""
        return [e for e in self.event_history if e.version > version]

    def acknowledge_event(self, event_id: str, user_id: str):
        """确认事件已接收"""
        for event in self.event_history:
            if event.id == event_id:
                event.acknowledged = True
                break

    def get_conflict_history(self) -> List[Dict[str, Any]]:
        """获取冲突历史"""
        return self.conflicts

    def resolve_manual_conflict(
        self,
        conflict_id: str,
        resolution: str,
        resolved_data: Optional[Dict[str, Any]] = None
    ):
        """手动解决冲突"""
        for conflict in self.conflicts:
            if conflict["id"] == conflict_id:
                conflict["resolution"] = resolution
                if resolved_data:
                    conflict["resolved_data"] = resolved_data
                conflict["resolved_at"] = datetime.now().isoformat()
                break

    def get_statistics(self) -> Dict[str, Any]:
        """获取同步统计"""
        return {
            "session_id": self.session_id,
            "current_version": self.current_version,
            "total_events": len(self.event_history),
            "online_users": len(self.connected_users),
            "total_conflicts": len(self.conflicts),
            "unresolved_conflicts": len([
                c for c in self.conflicts if c["resolution"] == "pending_manual"
            ]),
            "events_by_type": {
                event_type.value: len([
                    e for e in self.event_history if e.type == event_type
                ])
                for event_type in SyncEventType
            }
        }
