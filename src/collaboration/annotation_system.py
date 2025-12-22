"""
标注系统
支持多人协作标注播客内容
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class AnnotationType(Enum):
    """标注类型"""
    HIGHLIGHT = "highlight"  # 高亮
    NOTE = "note"  # 笔记
    QUESTION = "question"  # 问题
    BOOKMARK = "bookmark"  # 书签
    TAG = "tag"  # 标签
    CORRECTION = "correction"  # 纠错
    SUMMARY = "summary"  # 摘要
    ACTION_ITEM = "action_item"  # 待办事项
    REFERENCE = "reference"  # 引用
    EMOJI_REACTION = "emoji"  # 表情反应


class AnnotationVisibility(Enum):
    """标注可见性"""
    PRIVATE = "private"  # 仅自己可见
    TEAM = "team"  # 团队可见
    PUBLIC = "public"  # 公开


@dataclass
class TimeRange:
    """时间范围"""
    start: float  # 开始时间（秒）
    end: float  # 结束时间（秒）

    def overlaps(self, other: 'TimeRange') -> bool:
        """检查是否重叠"""
        return self.start < other.end and other.start < self.end

    def contains(self, time: float) -> bool:
        """检查时间点是否在范围内"""
        return self.start <= time <= self.end


@dataclass
class Annotation:
    """标注"""
    id: str
    type: AnnotationType
    time_range: TimeRange
    content: str
    created_by: str
    created_at: datetime
    visibility: AnnotationVisibility
    color: str
    tags: List[str] = field(default_factory=list)
    replies: List['AnnotationReply'] = field(default_factory=list)
    reactions: Dict[str, List[str]] = field(default_factory=dict)  # emoji -> [user_ids]
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnnotationReply:
    """标注回复"""
    id: str
    annotation_id: str
    content: str
    created_by: str
    created_at: datetime
    mentions: List[str] = field(default_factory=list)


class AnnotationSystem:
    """标注系统"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.annotations: Dict[str, Annotation] = {}
        self.annotation_index: Dict[float, List[str]] = {}  # time -> annotation_ids
        self.user_annotations: Dict[str, List[str]] = {}  # user_id -> annotation_ids
        self.tag_index: Dict[str, List[str]] = {}  # tag -> annotation_ids

    def create_annotation(
        self,
        annotation_type: AnnotationType,
        start_time: float,
        end_time: float,
        content: str,
        user_id: str,
        visibility: AnnotationVisibility = AnnotationVisibility.TEAM,
        color: str = "#f39c12",
        tags: Optional[List[str]] = None
    ) -> Annotation:
        """
        创建标注

        Args:
            annotation_type: 标注类型
            start_time: 开始时间
            end_time: 结束时间
            content: 标注内容
            user_id: 创建者ID
            visibility: 可见性
            color: 颜色
            tags: 标签列表

        Returns:
            创建的标注
        """
        annotation_id = str(uuid.uuid4())

        annotation = Annotation(
            id=annotation_id,
            type=annotation_type,
            time_range=TimeRange(start_time, end_time),
            content=content,
            created_by=user_id,
            created_at=datetime.now(),
            visibility=visibility,
            color=color,
            tags=tags or []
        )

        # 存储标注
        self.annotations[annotation_id] = annotation

        # 更新索引
        self._update_indices(annotation)

        return annotation

    def _update_indices(self, annotation: Annotation):
        """更新索引"""
        # 时间索引
        time_key = int(annotation.time_range.start)
        if time_key not in self.annotation_index:
            self.annotation_index[time_key] = []
        self.annotation_index[time_key].append(annotation.id)

        # 用户索引
        if annotation.created_by not in self.user_annotations:
            self.user_annotations[annotation.created_by] = []
        self.user_annotations[annotation.created_by].append(annotation.id)

        # 标签索引
        for tag in annotation.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(annotation.id)

    def get_annotation(self, annotation_id: str) -> Optional[Annotation]:
        """获取标注"""
        return self.annotations.get(annotation_id)

    def update_annotation(
        self,
        annotation_id: str,
        user_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        visibility: Optional[AnnotationVisibility] = None
    ) -> Optional[Annotation]:
        """更新标注"""
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            return None

        # 检查权限
        if annotation.created_by != user_id:
            raise PermissionError("无权修改此标注")

        if content is not None:
            annotation.content = content

        if tags is not None:
            # 更新标签索引
            for old_tag in annotation.tags:
                if old_tag in self.tag_index:
                    self.tag_index[old_tag] = [
                        aid for aid in self.tag_index[old_tag] if aid != annotation_id
                    ]

            annotation.tags = tags

            for new_tag in tags:
                if new_tag not in self.tag_index:
                    self.tag_index[new_tag] = []
                self.tag_index[new_tag].append(annotation_id)

        if visibility is not None:
            annotation.visibility = visibility

        return annotation

    def delete_annotation(self, annotation_id: str, user_id: str) -> bool:
        """删除标注"""
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            return False

        # 检查权限
        if annotation.created_by != user_id:
            raise PermissionError("无权删除此标注")

        # 移除索引
        time_key = int(annotation.time_range.start)
        if time_key in self.annotation_index:
            self.annotation_index[time_key] = [
                aid for aid in self.annotation_index[time_key] if aid != annotation_id
            ]

        if annotation.created_by in self.user_annotations:
            self.user_annotations[annotation.created_by] = [
                aid for aid in self.user_annotations[annotation.created_by] if aid != annotation_id
            ]

        for tag in annotation.tags:
            if tag in self.tag_index:
                self.tag_index[tag] = [
                    aid for aid in self.tag_index[tag] if aid != annotation_id
                ]

        del self.annotations[annotation_id]
        return True

    def add_reply(
        self,
        annotation_id: str,
        content: str,
        user_id: str,
        mentions: Optional[List[str]] = None
    ) -> Optional[AnnotationReply]:
        """添加回复"""
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            return None

        reply = AnnotationReply(
            id=str(uuid.uuid4()),
            annotation_id=annotation_id,
            content=content,
            created_by=user_id,
            created_at=datetime.now(),
            mentions=mentions or []
        )

        annotation.replies.append(reply)
        return reply

    def add_reaction(
        self,
        annotation_id: str,
        emoji: str,
        user_id: str
    ) -> bool:
        """添加表情反应"""
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            return False

        if emoji not in annotation.reactions:
            annotation.reactions[emoji] = []

        if user_id not in annotation.reactions[emoji]:
            annotation.reactions[emoji].append(user_id)

        return True

    def remove_reaction(
        self,
        annotation_id: str,
        emoji: str,
        user_id: str
    ) -> bool:
        """移除表情反应"""
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            return False

        if emoji in annotation.reactions:
            annotation.reactions[emoji] = [
                uid for uid in annotation.reactions[emoji] if uid != user_id
            ]

        return True

    def resolve_annotation(self, annotation_id: str, user_id: str) -> bool:
        """标记标注为已解决"""
        annotation = self.annotations.get(annotation_id)
        if not annotation:
            return False

        annotation.is_resolved = True
        annotation.resolved_by = user_id
        annotation.resolved_at = datetime.now()

        return True

    def get_annotations_at_time(
        self,
        time: float,
        user_id: str,
        include_types: Optional[List[AnnotationType]] = None
    ) -> List[Annotation]:
        """获取特定时间点的标注"""
        results = []

        for annotation in self.annotations.values():
            # 检查时间范围
            if not annotation.time_range.contains(time):
                continue

            # 检查可见性
            if not self._can_view(annotation, user_id):
                continue

            # 检查类型过滤
            if include_types and annotation.type not in include_types:
                continue

            results.append(annotation)

        return results

    def get_annotations_in_range(
        self,
        start_time: float,
        end_time: float,
        user_id: str,
        include_types: Optional[List[AnnotationType]] = None
    ) -> List[Annotation]:
        """获取时间范围内的标注"""
        query_range = TimeRange(start_time, end_time)
        results = []

        for annotation in self.annotations.values():
            # 检查时间范围重叠
            if not annotation.time_range.overlaps(query_range):
                continue

            # 检查可见性
            if not self._can_view(annotation, user_id):
                continue

            # 检查类型过滤
            if include_types and annotation.type not in include_types:
                continue

            results.append(annotation)

        # 按开始时间排序
        results.sort(key=lambda x: x.time_range.start)

        return results

    def _can_view(self, annotation: Annotation, user_id: str) -> bool:
        """检查用户是否可以查看标注"""
        if annotation.visibility == AnnotationVisibility.PUBLIC:
            return True

        if annotation.visibility == AnnotationVisibility.PRIVATE:
            return annotation.created_by == user_id

        # TEAM visibility - 所有会话参与者可见
        return True

    def get_user_annotations(self, user_id: str) -> List[Annotation]:
        """获取用户的所有标注"""
        annotation_ids = self.user_annotations.get(user_id, [])
        return [self.annotations[aid] for aid in annotation_ids if aid in self.annotations]

    def get_annotations_by_tag(self, tag: str) -> List[Annotation]:
        """按标签获取标注"""
        annotation_ids = self.tag_index.get(tag, [])
        return [self.annotations[aid] for aid in annotation_ids if aid in self.annotations]

    def get_annotations_by_type(
        self,
        annotation_type: AnnotationType,
        user_id: str
    ) -> List[Annotation]:
        """按类型获取标注"""
        results = []

        for annotation in self.annotations.values():
            if annotation.type != annotation_type:
                continue

            if not self._can_view(annotation, user_id):
                continue

            results.append(annotation)

        return results

    def get_unresolved_questions(self, user_id: str) -> List[Annotation]:
        """获取未解决的问题"""
        return [
            ann for ann in self.annotations.values()
            if ann.type == AnnotationType.QUESTION
            and not ann.is_resolved
            and self._can_view(ann, user_id)
        ]

    def get_action_items(self, user_id: str) -> List[Annotation]:
        """获取待办事项"""
        return [
            ann for ann in self.annotations.values()
            if ann.type == AnnotationType.ACTION_ITEM
            and not ann.is_resolved
            and self._can_view(ann, user_id)
        ]

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """获取所有标签及其使用次数"""
        return [
            {"tag": tag, "count": len(ids)}
            for tag, ids in self.tag_index.items()
            if ids  # 只返回有标注的标签
        ]

    def search_annotations(
        self,
        query: str,
        user_id: str,
        limit: int = 50
    ) -> List[Annotation]:
        """搜索标注"""
        query_lower = query.lower()
        results = []

        for annotation in self.annotations.values():
            if not self._can_view(annotation, user_id):
                continue

            # 搜索内容
            if query_lower in annotation.content.lower():
                results.append(annotation)
                continue

            # 搜索标签
            if any(query_lower in tag.lower() for tag in annotation.tags):
                results.append(annotation)
                continue

        # 按相关性排序（简单实现：按匹配度）
        results.sort(
            key=lambda x: x.content.lower().count(query_lower),
            reverse=True
        )

        return results[:limit]

    def export_annotations(
        self,
        user_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """导出标注"""
        visible_annotations = [
            ann for ann in self.annotations.values()
            if self._can_view(ann, user_id)
        ]

        if format == "json":
            return {
                "session_id": self.session_id,
                "exported_at": datetime.now().isoformat(),
                "total_annotations": len(visible_annotations),
                "annotations": [
                    {
                        "id": ann.id,
                        "type": ann.type.value,
                        "start_time": ann.time_range.start,
                        "end_time": ann.time_range.end,
                        "content": ann.content,
                        "created_by": ann.created_by,
                        "created_at": ann.created_at.isoformat(),
                        "tags": ann.tags,
                        "is_resolved": ann.is_resolved,
                        "replies_count": len(ann.replies),
                        "reactions": {k: len(v) for k, v in ann.reactions.items()}
                    }
                    for ann in visible_annotations
                ]
            }

        return {}

    def get_annotation_statistics(self, user_id: str) -> Dict[str, Any]:
        """获取标注统计"""
        visible = [ann for ann in self.annotations.values() if self._can_view(ann, user_id)]

        by_type = {}
        for ann in visible:
            type_name = ann.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        by_user = {}
        for ann in visible:
            by_user[ann.created_by] = by_user.get(ann.created_by, 0) + 1

        return {
            "total": len(visible),
            "by_type": by_type,
            "by_user": by_user,
            "resolved": len([ann for ann in visible if ann.is_resolved]),
            "unresolved": len([ann for ann in visible if not ann.is_resolved]),
            "total_replies": sum(len(ann.replies) for ann in visible),
            "total_reactions": sum(
                sum(len(users) for users in ann.reactions.values())
                for ann in visible
            ),
            "unique_tags": len(self.tag_index)
        }
