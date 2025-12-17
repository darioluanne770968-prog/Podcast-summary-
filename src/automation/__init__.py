"""
自动化工作流模块

功能：
- RSS 订阅监控
- 批量处理
- 通知系统
- 定时任务
"""

from .rss_monitor import RSSMonitor, FeedSubscription
from .batch_processor import BatchProcessor, BatchJob
from .notifications import NotificationManager, NotificationType
from .scheduler import TaskScheduler, ScheduledTask

__all__ = [
    "RSSMonitor",
    "FeedSubscription",
    "BatchProcessor",
    "BatchJob",
    "NotificationManager",
    "NotificationType",
    "TaskScheduler",
    "ScheduledTask",
]
