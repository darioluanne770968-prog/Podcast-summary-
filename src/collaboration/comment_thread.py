"""
评论线程系统
支持层级评论和讨论
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class Comment:
    """评论"""
    id: str
    thread_id: str
    parent_id: Optional[str]  # 父评论ID，None表示顶级评论
    content: str
    author_id: str
    author_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_edited: bool = False
    is_deleted: bool = False
    mentions: List[str] = field(default_factory=list)
    reactions: Dict[str, List[str]] = field(default_factory=dict)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommentThreadData:
    """评论线程数据"""
    id: str
    podcast_id: str
    timestamp: float  # 关联的播客时间点
    title: Optional[str]
    comments: List[Comment]
    created_at: datetime
    created_by: str
    is_locked: bool
    is_pinned: bool
    participant_count: int
    comment_count: int


class CommentThread:
    """评论线程管理器"""

    def __init__(self, podcast_id: str):
        self.podcast_id = podcast_id
        self.threads: Dict[str, Dict[str, Any]] = {}  # thread_id -> thread_data
        self.comments: Dict[str, Comment] = {}  # comment_id -> comment
        self.thread_comments: Dict[str, List[str]] = {}  # thread_id -> [comment_ids]
        self.user_comments: Dict[str, List[str]] = {}  # user_id -> [comment_ids]

    def create_thread(
        self,
        timestamp: float,
        user_id: str,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None
    ) -> str:
        """
        创建评论线程

        Args:
            timestamp: 播客时间点
            user_id: 创建者ID
            title: 线程标题
            initial_comment: 初始评论内容

        Returns:
            线程ID
        """
        thread_id = str(uuid.uuid4())

        self.threads[thread_id] = {
            "id": thread_id,
            "podcast_id": self.podcast_id,
            "timestamp": timestamp,
            "title": title,
            "created_at": datetime.now(),
            "created_by": user_id,
            "is_locked": False,
            "is_pinned": False,
            "participants": {user_id}
        }

        self.thread_comments[thread_id] = []

        # 如果有初始评论，添加它
        if initial_comment:
            self.add_comment(thread_id, initial_comment, user_id, user_id)

        return thread_id

    def add_comment(
        self,
        thread_id: str,
        content: str,
        author_id: str,
        author_name: str,
        parent_id: Optional[str] = None,
        mentions: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Comment]:
        """
        添加评论

        Args:
            thread_id: 线程ID
            content: 评论内容
            author_id: 作者ID
            author_name: 作者名
            parent_id: 父评论ID
            mentions: 提及的用户
            attachments: 附件

        Returns:
            创建的评论
        """
        if thread_id not in self.threads:
            return None

        thread = self.threads[thread_id]

        # 检查线程是否锁定
        if thread["is_locked"]:
            raise PermissionError("线程已锁定，无法添加评论")

        # 验证父评论
        if parent_id and parent_id not in self.comments:
            raise ValueError("父评论不存在")

        comment_id = str(uuid.uuid4())

        comment = Comment(
            id=comment_id,
            thread_id=thread_id,
            parent_id=parent_id,
            content=content,
            author_id=author_id,
            author_name=author_name,
            created_at=datetime.now(),
            mentions=mentions or [],
            attachments=attachments or []
        )

        # 存储评论
        self.comments[comment_id] = comment
        self.thread_comments[thread_id].append(comment_id)

        # 更新用户评论索引
        if author_id not in self.user_comments:
            self.user_comments[author_id] = []
        self.user_comments[author_id].append(comment_id)

        # 更新参与者
        thread["participants"].add(author_id)

        return comment

    def edit_comment(
        self,
        comment_id: str,
        new_content: str,
        editor_id: str
    ) -> Optional[Comment]:
        """编辑评论"""
        comment = self.comments.get(comment_id)
        if not comment:
            return None

        # 检查权限
        if comment.author_id != editor_id:
            raise PermissionError("无权编辑此评论")

        if comment.is_deleted:
            raise ValueError("无法编辑已删除的评论")

        comment.content = new_content
        comment.updated_at = datetime.now()
        comment.is_edited = True

        return comment

    def delete_comment(self, comment_id: str, user_id: str) -> bool:
        """删除评论（软删除）"""
        comment = self.comments.get(comment_id)
        if not comment:
            return False

        # 检查权限
        if comment.author_id != user_id:
            raise PermissionError("无权删除此评论")

        comment.is_deleted = True
        comment.content = "[评论已删除]"

        return True

    def add_reaction(
        self,
        comment_id: str,
        emoji: str,
        user_id: str
    ) -> bool:
        """添加表情反应"""
        comment = self.comments.get(comment_id)
        if not comment:
            return False

        if emoji not in comment.reactions:
            comment.reactions[emoji] = []

        if user_id not in comment.reactions[emoji]:
            comment.reactions[emoji].append(user_id)

        return True

    def remove_reaction(
        self,
        comment_id: str,
        emoji: str,
        user_id: str
    ) -> bool:
        """移除表情反应"""
        comment = self.comments.get(comment_id)
        if not comment:
            return False

        if emoji in comment.reactions:
            comment.reactions[emoji] = [
                uid for uid in comment.reactions[emoji] if uid != user_id
            ]

        return True

    def get_thread(self, thread_id: str) -> Optional[CommentThreadData]:
        """获取线程数据"""
        if thread_id not in self.threads:
            return None

        thread = self.threads[thread_id]
        comment_ids = self.thread_comments.get(thread_id, [])
        comments = [self.comments[cid] for cid in comment_ids if cid in self.comments]

        return CommentThreadData(
            id=thread_id,
            podcast_id=self.podcast_id,
            timestamp=thread["timestamp"],
            title=thread.get("title"),
            comments=comments,
            created_at=thread["created_at"],
            created_by=thread["created_by"],
            is_locked=thread["is_locked"],
            is_pinned=thread["is_pinned"],
            participant_count=len(thread["participants"]),
            comment_count=len(comments)
        )

    def get_thread_comments(
        self,
        thread_id: str,
        include_deleted: bool = False
    ) -> List[Comment]:
        """获取线程的所有评论"""
        comment_ids = self.thread_comments.get(thread_id, [])
        comments = [self.comments[cid] for cid in comment_ids if cid in self.comments]

        if not include_deleted:
            comments = [c for c in comments if not c.is_deleted]

        return comments

    def get_nested_comments(self, thread_id: str) -> List[Dict[str, Any]]:
        """获取嵌套结构的评论"""
        comments = self.get_thread_comments(thread_id)

        # 构建评论树
        comment_dict = {c.id: c for c in comments}
        root_comments = []
        children_map: Dict[str, List[Comment]] = {}

        for comment in comments:
            if comment.parent_id is None:
                root_comments.append(comment)
            else:
                if comment.parent_id not in children_map:
                    children_map[comment.parent_id] = []
                children_map[comment.parent_id].append(comment)

        def build_tree(comment: Comment) -> Dict[str, Any]:
            children = children_map.get(comment.id, [])
            return {
                "comment": {
                    "id": comment.id,
                    "content": comment.content,
                    "author_id": comment.author_id,
                    "author_name": comment.author_name,
                    "created_at": comment.created_at.isoformat(),
                    "is_edited": comment.is_edited,
                    "is_deleted": comment.is_deleted,
                    "reactions": {k: len(v) for k, v in comment.reactions.items()},
                    "mentions": comment.mentions
                },
                "replies": [build_tree(child) for child in children]
            }

        return [build_tree(rc) for rc in root_comments]

    def get_threads_at_timestamp(
        self,
        timestamp: float,
        tolerance: float = 5.0
    ) -> List[CommentThreadData]:
        """获取特定时间点附近的线程"""
        results = []

        for thread_id, thread in self.threads.items():
            if abs(thread["timestamp"] - timestamp) <= tolerance:
                thread_data = self.get_thread(thread_id)
                if thread_data:
                    results.append(thread_data)

        # 按时间点排序
        results.sort(key=lambda x: x.timestamp)

        return results

    def get_threads_in_range(
        self,
        start_time: float,
        end_time: float
    ) -> List[CommentThreadData]:
        """获取时间范围内的线程"""
        results = []

        for thread_id, thread in self.threads.items():
            if start_time <= thread["timestamp"] <= end_time:
                thread_data = self.get_thread(thread_id)
                if thread_data:
                    results.append(thread_data)

        results.sort(key=lambda x: x.timestamp)

        return results

    def lock_thread(self, thread_id: str, admin_id: str) -> bool:
        """锁定线程"""
        if thread_id not in self.threads:
            return False

        self.threads[thread_id]["is_locked"] = True
        return True

    def unlock_thread(self, thread_id: str, admin_id: str) -> bool:
        """解锁线程"""
        if thread_id not in self.threads:
            return False

        self.threads[thread_id]["is_locked"] = False
        return True

    def pin_thread(self, thread_id: str, admin_id: str) -> bool:
        """置顶线程"""
        if thread_id not in self.threads:
            return False

        self.threads[thread_id]["is_pinned"] = True
        return True

    def unpin_thread(self, thread_id: str, admin_id: str) -> bool:
        """取消置顶"""
        if thread_id not in self.threads:
            return False

        self.threads[thread_id]["is_pinned"] = False
        return True

    def get_user_comments(self, user_id: str) -> List[Comment]:
        """获取用户的所有评论"""
        comment_ids = self.user_comments.get(user_id, [])
        return [self.comments[cid] for cid in comment_ids if cid in self.comments]

    def search_comments(
        self,
        query: str,
        limit: int = 50
    ) -> List[Comment]:
        """搜索评论"""
        query_lower = query.lower()
        results = []

        for comment in self.comments.values():
            if comment.is_deleted:
                continue

            if query_lower in comment.content.lower():
                results.append(comment)

        return results[:limit]

    def get_mentions_for_user(self, user_id: str) -> List[Comment]:
        """获取提及用户的评论"""
        return [
            c for c in self.comments.values()
            if user_id in c.mentions and not c.is_deleted
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_comments = len([c for c in self.comments.values() if not c.is_deleted])
        total_threads = len(self.threads)

        # 活跃线程（有评论的线程）
        active_threads = len([
            tid for tid, cids in self.thread_comments.items()
            if len(cids) > 0
        ])

        # 计算平均每线程评论数
        avg_comments = total_comments / total_threads if total_threads > 0 else 0

        # 计算总反应数
        total_reactions = sum(
            sum(len(users) for users in c.reactions.values())
            for c in self.comments.values()
        )

        return {
            "total_threads": total_threads,
            "active_threads": active_threads,
            "total_comments": total_comments,
            "avg_comments_per_thread": round(avg_comments, 2),
            "total_reactions": total_reactions,
            "unique_participants": len(set(
                c.author_id for c in self.comments.values()
            )),
            "pinned_threads": len([t for t in self.threads.values() if t["is_pinned"]]),
            "locked_threads": len([t for t in self.threads.values() if t["is_locked"]])
        }

    def export_thread(self, thread_id: str) -> Dict[str, Any]:
        """导出线程数据"""
        thread_data = self.get_thread(thread_id)
        if not thread_data:
            return {}

        return {
            "thread_id": thread_id,
            "podcast_id": self.podcast_id,
            "timestamp": thread_data.timestamp,
            "title": thread_data.title,
            "created_at": thread_data.created_at.isoformat(),
            "created_by": thread_data.created_by,
            "is_locked": thread_data.is_locked,
            "is_pinned": thread_data.is_pinned,
            "participant_count": thread_data.participant_count,
            "comments": self.get_nested_comments(thread_id),
            "exported_at": datetime.now().isoformat()
        }
