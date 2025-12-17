"""
定时任务调度模块

支持定时执行任务
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Callable, Any
from enum import Enum
import json
import uuid

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


class ScheduleType(str, Enum):
    """调度类型"""
    ONCE = "once"
    INTERVAL = "interval"
    DAILY = "daily"
    WEEKLY = "weekly"
    CRON = "cron"


class TaskStatus(str, Enum):
    """任务状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScheduledTask:
    """定时任务"""
    id: str
    name: str
    schedule_type: ScheduleType
    action: str
    action_params: Dict[str, Any] = field(default_factory=dict)

    # 调度配置
    interval_seconds: int = 3600
    run_at_time: str = "08:00"
    weekday: int = 0  # 0=周一
    cron_expression: str = ""

    # 状态
    status: TaskStatus = TaskStatus.ACTIVE
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    fail_count: int = 0
    last_error: Optional[str] = None

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "schedule_type": self.schedule_type.value,
            "action": self.action,
            "action_params": self.action_params,
            "interval_seconds": self.interval_seconds,
            "run_at_time": self.run_at_time,
            "weekday": self.weekday,
            "cron_expression": self.cron_expression,
            "status": self.status.value,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "fail_count": self.fail_count,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledTask":
        return cls(
            id=data["id"],
            name=data["name"],
            schedule_type=ScheduleType(data.get("schedule_type", "once")),
            action=data.get("action", ""),
            action_params=data.get("action_params", {}),
            interval_seconds=data.get("interval_seconds", 3600),
            run_at_time=data.get("run_at_time", "08:00"),
            weekday=data.get("weekday", 0),
            cron_expression=data.get("cron_expression", ""),
            status=TaskStatus(data.get("status", "active")),
            last_run=data.get("last_run"),
            next_run=data.get("next_run"),
            run_count=data.get("run_count", 0),
            fail_count=data.get("fail_count", 0),
            last_error=data.get("last_error"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )

    def calculate_next_run(self) -> datetime:
        """计算下次执行时间"""
        now = datetime.now()

        if self.schedule_type == ScheduleType.ONCE:
            # 一次性任务
            if self.next_run:
                return datetime.fromisoformat(self.next_run)
            return now

        elif self.schedule_type == ScheduleType.INTERVAL:
            # 固定间隔
            if self.last_run:
                last = datetime.fromisoformat(self.last_run)
                return last + timedelta(seconds=self.interval_seconds)
            return now

        elif self.schedule_type == ScheduleType.DAILY:
            # 每日定时
            hour, minute = map(int, self.run_at_time.split(":"))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run

        elif self.schedule_type == ScheduleType.WEEKLY:
            # 每周定时
            hour, minute = map(int, self.run_at_time.split(":"))
            days_ahead = self.weekday - now.weekday()
            if days_ahead < 0:
                days_ahead += 7
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            next_run += timedelta(days=days_ahead)
            if next_run <= now:
                next_run += timedelta(weeks=1)
            return next_run

        elif self.schedule_type == ScheduleType.CRON:
            # Cron 表达式
            try:
                from croniter import croniter
                cron = croniter(self.cron_expression, now)
                return cron.get_next(datetime)
            except ImportError:
                logger.warning("Cron 调度需要安装 croniter: pip install croniter")
                return now + timedelta(hours=1)
            except Exception as e:
                logger.error(f"解析 cron 表达式失败: {e}")
                return now + timedelta(hours=1)

        return now


class TaskScheduler:
    """任务调度器"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "scheduler"
        ensure_dir(self.storage_dir)
        self._tasks: Dict[str, ScheduledTask] = {}
        self._actions: Dict[str, Callable] = {}
        self._running = False
        self._load_tasks()

    def _load_tasks(self):
        """加载任务配置"""
        tasks_file = self.storage_dir / "tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_data in data:
                        task = ScheduledTask.from_dict(task_data)
                        self._tasks[task.id] = task
            except Exception as e:
                logger.error(f"加载调度任务失败: {e}")

    def _save_tasks(self):
        """保存任务配置"""
        tasks_file = self.storage_dir / "tasks.json"
        try:
            data = [task.to_dict() for task in self._tasks.values()]
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存调度任务失败: {e}")

    def register_action(self, name: str, func: Callable):
        """注册任务动作"""
        self._actions[name] = func
        logger.info(f"注册调度动作: {name}")

    def create_task(
        self,
        name: str,
        action: str,
        schedule_type: ScheduleType,
        action_params: Optional[Dict] = None,
        **schedule_config,
    ) -> ScheduledTask:
        """创建定时任务"""
        task_id = str(uuid.uuid4())[:8]

        task = ScheduledTask(
            id=task_id,
            name=name,
            action=action,
            schedule_type=schedule_type,
            action_params=action_params or {},
            **schedule_config,
        )

        # 计算首次执行时间
        task.next_run = task.calculate_next_run().isoformat()

        self._tasks[task_id] = task
        self._save_tasks()
        logger.info(f"创建定时任务: {name} ({schedule_type.value})")
        return task

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
    ) -> List[ScheduledTask]:
        """列出任务"""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.next_run or "")

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.PAUSED
            task.updated_at = datetime.now().isoformat()
            self._save_tasks()
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.ACTIVE
            task.next_run = task.calculate_next_run().isoformat()
            task.updated_at = datetime.now().isoformat()
            self._save_tasks()
            return True
        return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save_tasks()
            return True
        return False

    async def _execute_task(self, task: ScheduledTask):
        """执行任务"""
        if task.action not in self._actions:
            logger.error(f"未知的任务动作: {task.action}")
            task.last_error = f"未知动作: {task.action}"
            task.fail_count += 1
            return

        logger.info(f"执行定时任务: {task.name}")
        task.last_run = datetime.now().isoformat()

        try:
            action_func = self._actions[task.action]
            result = action_func(**task.action_params)
            if asyncio.iscoroutine(result):
                await result

            task.run_count += 1
            task.last_error = None
            logger.info(f"任务执行成功: {task.name}")

        except Exception as e:
            task.fail_count += 1
            task.last_error = str(e)
            logger.error(f"任务执行失败 [{task.name}]: {e}")

        finally:
            # 更新下次执行时间
            if task.schedule_type == ScheduleType.ONCE:
                task.status = TaskStatus.COMPLETED
            else:
                task.next_run = task.calculate_next_run().isoformat()

            task.updated_at = datetime.now().isoformat()
            self._save_tasks()

    async def run_once(self, task_id: str):
        """立即执行一次任务"""
        task = self.get_task(task_id)
        if task:
            await self._execute_task(task)

    async def start(self):
        """启动调度器"""
        self._running = True
        logger.info("任务调度器已启动")

        while self._running:
            now = datetime.now()

            for task in self._tasks.values():
                if task.status != TaskStatus.ACTIVE:
                    continue

                if not task.next_run:
                    continue

                next_run = datetime.fromisoformat(task.next_run)
                if next_run <= now:
                    asyncio.create_task(self._execute_task(task))

            await asyncio.sleep(10)  # 每 10 秒检查一次

    def stop(self):
        """停止调度器"""
        self._running = False
        logger.info("任务调度器已停止")

    # 便捷方法
    def schedule_rss_check(
        self,
        name: str,
        feed_url: str,
        interval_hours: int = 1,
    ) -> ScheduledTask:
        """调度 RSS 检查"""
        return self.create_task(
            name=name,
            action="check_rss",
            schedule_type=ScheduleType.INTERVAL,
            action_params={"feed_url": feed_url},
            interval_seconds=interval_hours * 3600,
        )

    def schedule_daily_summary(
        self,
        name: str,
        run_at: str = "08:00",
    ) -> ScheduledTask:
        """调度每日摘要"""
        return self.create_task(
            name=name,
            action="daily_summary",
            schedule_type=ScheduleType.DAILY,
            run_at_time=run_at,
        )

    def schedule_batch_job(
        self,
        name: str,
        job_id: str,
        run_at: datetime,
    ) -> ScheduledTask:
        """调度批量任务"""
        task = self.create_task(
            name=name,
            action="run_batch",
            schedule_type=ScheduleType.ONCE,
            action_params={"job_id": job_id},
        )
        task.next_run = run_at.isoformat()
        self._save_tasks()
        return task

    def get_upcoming_tasks(self, hours: int = 24) -> List[ScheduledTask]:
        """获取即将执行的任务"""
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)

        upcoming = []
        for task in self._tasks.values():
            if task.status != TaskStatus.ACTIVE:
                continue
            if not task.next_run:
                continue

            next_run = datetime.fromisoformat(task.next_run)
            if next_run <= cutoff:
                upcoming.append(task)

        return sorted(upcoming, key=lambda t: t.next_run or "")

    def get_stats(self) -> Dict[str, Any]:
        """获取调度统计"""
        total = len(self._tasks)
        active = sum(1 for t in self._tasks.values() if t.status == TaskStatus.ACTIVE)
        paused = sum(1 for t in self._tasks.values() if t.status == TaskStatus.PAUSED)
        completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)

        total_runs = sum(t.run_count for t in self._tasks.values())
        total_fails = sum(t.fail_count for t in self._tasks.values())

        return {
            "total_tasks": total,
            "active_tasks": active,
            "paused_tasks": paused,
            "completed_tasks": completed,
            "total_runs": total_runs,
            "total_failures": total_fails,
            "success_rate": total_runs / (total_runs + total_fails) * 100 if (total_runs + total_fails) > 0 else 100,
        }
