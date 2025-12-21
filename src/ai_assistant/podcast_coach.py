"""
个人播客教练

根据用户学习目标推荐内容和制定学习计划
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import uuid

from ..utils import get_logger

logger = get_logger(__name__)


class GoalStatus(str, Enum):
    """目标状态"""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"


class DifficultyLevel(str, Enum):
    """难度级别"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class LearningGoal:
    """学习目标"""
    id: str
    title: str
    description: str
    topics: List[str] = field(default_factory=list)
    target_hours: float = 10.0
    completed_hours: float = 0.0
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    status: GoalStatus = GoalStatus.ACTIVE
    deadline: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def progress(self) -> float:
        if self.target_hours == 0:
            return 100.0
        return min(self.completed_hours / self.target_hours * 100, 100.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "topics": self.topics,
            "target_hours": self.target_hours,
            "completed_hours": self.completed_hours,
            "difficulty": self.difficulty.value,
            "status": self.status.value,
            "deadline": self.deadline,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class LearningSession:
    """学习记录"""
    id: str
    goal_id: str
    podcast_id: str
    podcast_title: str
    duration_minutes: float
    segments_listened: List[Dict] = field(default_factory=list)
    notes: str = ""
    rating: int = 0  # 1-5
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ContentRecommendation:
    """内容推荐"""
    podcast_id: str
    podcast_title: str
    segment_start: float
    segment_end: float
    relevance_score: float
    reason: str
    topics: List[str] = field(default_factory=list)


class PodcastCoach:
    """
    播客学习教练

    功能：
    - 设定学习目标
    - 推荐相关内容
    - 追踪学习进度
    - 间隔重复复习
    - 生成学习报告
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "coach"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._goals: Dict[str, LearningGoal] = {}
        self._sessions: List[LearningSession] = []
        self._podcast_index: Dict[str, Dict] = {}
        self._load_data()

    def _load_data(self):
        """加载数据"""
        goals_file = self.storage_dir / "goals.json"
        if goals_file.exists():
            try:
                with open(goals_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for goal_data in data.get("goals", []):
                        goal = LearningGoal(
                            id=goal_data["id"],
                            title=goal_data["title"],
                            description=goal_data.get("description", ""),
                            topics=goal_data.get("topics", []),
                            target_hours=goal_data.get("target_hours", 10),
                            completed_hours=goal_data.get("completed_hours", 0),
                            difficulty=DifficultyLevel(goal_data.get("difficulty", "intermediate")),
                            status=GoalStatus(goal_data.get("status", "active")),
                            deadline=goal_data.get("deadline"),
                            created_at=goal_data.get("created_at", ""),
                            updated_at=goal_data.get("updated_at", ""),
                        )
                        self._goals[goal.id] = goal
            except Exception as e:
                logger.error(f"加载目标数据失败: {e}")

    def _save_data(self):
        """保存数据"""
        goals_file = self.storage_dir / "goals.json"
        try:
            data = {
                "goals": [goal.to_dict() for goal in self._goals.values()],
            }
            with open(goals_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存目标数据失败: {e}")

    def create_goal(
        self,
        title: str,
        description: str = "",
        topics: List[str] = None,
        target_hours: float = 10.0,
        difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
        deadline: Optional[str] = None,
    ) -> LearningGoal:
        """创建学习目标"""
        goal_id = str(uuid.uuid4())[:8]
        goal = LearningGoal(
            id=goal_id,
            title=title,
            description=description,
            topics=topics or [],
            target_hours=target_hours,
            difficulty=difficulty,
            deadline=deadline,
        )
        self._goals[goal_id] = goal
        self._save_data()
        logger.info(f"创建学习目标: {title}")
        return goal

    def get_goal(self, goal_id: str) -> Optional[LearningGoal]:
        """获取目标"""
        return self._goals.get(goal_id)

    def list_goals(self, status: Optional[GoalStatus] = None) -> List[LearningGoal]:
        """列出目标"""
        goals = list(self._goals.values())
        if status:
            goals = [g for g in goals if g.status == status]
        return sorted(goals, key=lambda g: g.created_at, reverse=True)

    def update_goal_progress(
        self,
        goal_id: str,
        hours_completed: float,
    ):
        """更新目标进度"""
        goal = self.get_goal(goal_id)
        if goal:
            goal.completed_hours += hours_completed
            goal.updated_at = datetime.now().isoformat()
            if goal.completed_hours >= goal.target_hours:
                goal.status = GoalStatus.COMPLETED
            self._save_data()

    def index_podcast(self, podcast_id: str, content: Dict):
        """索引播客内容"""
        self._podcast_index[podcast_id] = {
            "id": podcast_id,
            "title": content.get("title", ""),
            "summary": content.get("summary", ""),
            "keywords": content.get("keywords", []),
            "chapters": content.get("chapters", []),
            "duration": content.get("duration", 0),
            "topics": content.get("topics", content.get("keywords", [])),
        }

    def recommend_for_goal(
        self,
        goal_id: str,
        count: int = 5,
    ) -> List[ContentRecommendation]:
        """
        为目标推荐内容

        Args:
            goal_id: 目标 ID
            count: 推荐数量

        Returns:
            推荐列表
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return []

        recommendations = []
        goal_topics = set(t.lower() for t in goal.topics)

        for podcast_id, podcast in self._podcast_index.items():
            podcast_topics = set(t.lower() for t in podcast.get("topics", []))

            # 计算话题重合度
            overlap = goal_topics & podcast_topics
            if not overlap:
                continue

            relevance = len(overlap) / len(goal_topics) if goal_topics else 0

            # 检查章节
            for chapter in podcast.get("chapters", []):
                chapter_keywords = set(k.lower() for k in chapter.get("keywords", []))
                chapter_overlap = goal_topics & chapter_keywords

                if chapter_overlap:
                    recommendations.append(ContentRecommendation(
                        podcast_id=podcast_id,
                        podcast_title=podcast.get("title", ""),
                        segment_start=chapter.get("start_time", 0),
                        segment_end=chapter.get("end_time", 0),
                        relevance_score=len(chapter_overlap) / len(goal_topics),
                        reason=f"涵盖话题: {', '.join(chapter_overlap)}",
                        topics=list(chapter_overlap),
                    ))

            # 如果没有匹配的章节，推荐整个播客
            if not any(r.podcast_id == podcast_id for r in recommendations):
                recommendations.append(ContentRecommendation(
                    podcast_id=podcast_id,
                    podcast_title=podcast.get("title", ""),
                    segment_start=0,
                    segment_end=podcast.get("duration", 0),
                    relevance_score=relevance,
                    reason=f"涵盖话题: {', '.join(overlap)}",
                    topics=list(overlap),
                ))

        # 按相关性排序
        recommendations.sort(key=lambda r: r.relevance_score, reverse=True)
        return recommendations[:count]

    def record_session(
        self,
        goal_id: str,
        podcast_id: str,
        podcast_title: str,
        duration_minutes: float,
        segments: List[Dict] = None,
        notes: str = "",
        rating: int = 0,
    ) -> LearningSession:
        """记录学习"""
        session = LearningSession(
            id=str(uuid.uuid4())[:8],
            goal_id=goal_id,
            podcast_id=podcast_id,
            podcast_title=podcast_title,
            duration_minutes=duration_minutes,
            segments_listened=segments or [],
            notes=notes,
            rating=rating,
        )
        self._sessions.append(session)

        # 更新目标进度
        self.update_goal_progress(goal_id, duration_minutes / 60)

        return session

    def get_review_schedule(
        self,
        goal_id: str,
    ) -> List[Dict]:
        """
        获取复习计划（间隔重复）

        基于遗忘曲线推荐复习时间
        """
        goal_sessions = [s for s in self._sessions if s.goal_id == goal_id]
        if not goal_sessions:
            return []

        schedule = []
        now = datetime.now()

        # 间隔重复间隔（天）
        intervals = [1, 3, 7, 14, 30]

        for session in goal_sessions:
            session_time = datetime.fromisoformat(session.timestamp)

            for i, interval in enumerate(intervals):
                review_time = session_time + timedelta(days=interval)
                if review_time > now:
                    schedule.append({
                        "podcast_id": session.podcast_id,
                        "podcast_title": session.podcast_title,
                        "review_date": review_time.strftime("%Y-%m-%d"),
                        "review_number": i + 1,
                        "original_session": session.timestamp,
                    })
                    break

        schedule.sort(key=lambda x: x["review_date"])
        return schedule

    def generate_study_plan(
        self,
        goal_id: str,
        hours_per_day: float = 1.0,
    ) -> Dict[str, Any]:
        """
        生成学习计划

        Args:
            goal_id: 目标 ID
            hours_per_day: 每天学习时长

        Returns:
            学习计划
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return {}

        remaining_hours = goal.target_hours - goal.completed_hours
        days_needed = int(remaining_hours / hours_per_day) + 1

        recommendations = self.recommend_for_goal(goal_id, count=days_needed * 2)

        plan = {
            "goal": goal.to_dict(),
            "remaining_hours": remaining_hours,
            "days_needed": days_needed,
            "hours_per_day": hours_per_day,
            "daily_schedule": [],
        }

        current_date = datetime.now()
        rec_index = 0

        for day in range(days_needed):
            date = current_date + timedelta(days=day)
            day_content = []
            day_hours = 0

            while day_hours < hours_per_day and rec_index < len(recommendations):
                rec = recommendations[rec_index]
                segment_duration = (rec.segment_end - rec.segment_start) / 3600  # 转换为小时

                if segment_duration == 0:
                    segment_duration = 0.5  # 默认 30 分钟

                day_content.append({
                    "podcast": rec.podcast_title,
                    "segment": f"{rec.segment_start/60:.0f}-{rec.segment_end/60:.0f}分钟",
                    "duration_hours": segment_duration,
                    "topics": rec.topics,
                })
                day_hours += segment_duration
                rec_index += 1

            plan["daily_schedule"].append({
                "date": date.strftime("%Y-%m-%d"),
                "day": day + 1,
                "content": day_content,
                "total_hours": day_hours,
            })

        return plan

    def get_progress_report(self, goal_id: str) -> Dict[str, Any]:
        """获取学习报告"""
        goal = self.get_goal(goal_id)
        if not goal:
            return {}

        goal_sessions = [s for s in self._sessions if s.goal_id == goal_id]

        total_minutes = sum(s.duration_minutes for s in goal_sessions)
        podcasts_listened = len(set(s.podcast_id for s in goal_sessions))
        avg_rating = sum(s.rating for s in goal_sessions) / len(goal_sessions) if goal_sessions else 0

        return {
            "goal": goal.to_dict(),
            "statistics": {
                "total_sessions": len(goal_sessions),
                "total_hours": total_minutes / 60,
                "podcasts_listened": podcasts_listened,
                "average_rating": avg_rating,
                "completion_rate": goal.progress,
            },
            "recent_sessions": [
                {
                    "podcast": s.podcast_title,
                    "duration": s.duration_minutes,
                    "date": s.timestamp,
                }
                for s in goal_sessions[-5:]
            ],
            "upcoming_reviews": self.get_review_schedule(goal_id)[:5],
        }
