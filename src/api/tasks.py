"""
任务队列模块

异步任务处理
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid

from ..utils import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务"""
    id: str
    task_type: str
    params: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "params": self.params,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskQueue:
    """任务队列"""

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self._tasks: Dict[str, Task] = {}
        self._queue: asyncio.Queue = None
        self._workers: List[asyncio.Task] = []
        self._running = False

    async def start(self):
        """启动队列"""
        if self._running:
            return

        self._running = True
        self._queue = asyncio.Queue()

        # 启动工作线程
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        logger.info(f"任务队列已启动，工作线程数: {self.max_workers}")

    async def stop(self):
        """停止队列"""
        self._running = False

        # 等待队列清空
        if self._queue:
            await self._queue.join()

        # 取消工作线程
        for worker in self._workers:
            worker.cancel()

        self._workers.clear()
        logger.info("任务队列已停止")

    async def submit(
        self,
        task_type: str,
        params: Dict[str, Any],
    ) -> str:
        """提交任务"""
        task_id = str(uuid.uuid4())[:12]

        task = Task(
            id=task_id,
            task_type=task_type,
            params=params,
        )

        self._tasks[task_id] = task
        await self._queue.put(task)

        logger.info(f"任务已提交: {task_id} ({task_type})")
        return task_id

    async def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务"""
        task = self._tasks.get(task_id)
        if task:
            return task.to_dict()
        return None

    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in [TaskStatus.PENDING]:
            task.status = TaskStatus.CANCELLED
            task.updated_at = datetime.now().isoformat()
            return True

        return False

    async def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict]:
        """列出任务"""
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status.value == status]

        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in tasks[offset:offset + limit]]

    async def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        total = len(self._tasks)
        by_status = {}
        for task in self._tasks.values():
            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_tasks": total,
            "by_status": by_status,
            "queue_size": self._queue.qsize() if self._queue else 0,
            "workers": self.max_workers,
        }

    async def _worker(self, worker_id: int):
        """工作线程"""
        logger.info(f"工作线程 {worker_id} 已启动")

        while self._running:
            try:
                task = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            if task.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue

            try:
                task.status = TaskStatus.RUNNING
                task.updated_at = datetime.now().isoformat()

                logger.info(f"[Worker {worker_id}] 开始处理任务: {task.id}")

                # 执行任务
                result = await self._execute_task(task)

                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = 100.0

                logger.info(f"[Worker {worker_id}] 任务完成: {task.id}")

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error(f"[Worker {worker_id}] 任务失败 [{task.id}]: {e}")

            finally:
                task.updated_at = datetime.now().isoformat()
                self._queue.task_done()

    async def _execute_task(self, task: Task) -> Dict[str, Any]:
        """执行任务"""
        if task.task_type == "analyze":
            return await self._execute_analyze(task)
        elif task.task_type == "batch":
            return await self._execute_batch(task)
        else:
            raise ValueError(f"未知的任务类型: {task.task_type}")

    async def _execute_analyze(self, task: Task) -> Dict[str, Any]:
        """执行分析任务"""
        params = task.params
        url = params.get("url")
        file_path = params.get("file_path")
        template = params.get("template", "default")

        # 导入分析模块
        try:
            from ..pipeline import PodcastPipeline
        except ImportError:
            # 模拟处理
            await asyncio.sleep(2)
            return {
                "status": "completed",
                "message": "分析完成（模拟）",
                "summary": "这是一个模拟的分析结果。",
            }

        source = url or file_path
        if not source:
            raise ValueError("需要提供 URL 或文件路径")

        # 创建管道并执行
        pipeline = PodcastPipeline()

        # 更新进度的回调
        def progress_callback(progress: float, message: str = ""):
            task.progress = progress
            task.updated_at = datetime.now().isoformat()

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: pipeline.process(source, template=template),
        )

        # 清理临时文件
        if params.get("cleanup") and file_path:
            import os
            try:
                os.remove(file_path)
            except:
                pass

        return result

    async def _execute_batch(self, task: Task) -> Dict[str, Any]:
        """执行批量任务"""
        params = task.params
        urls = params.get("urls", [])
        template = params.get("template", "default")

        results = []
        total = len(urls)

        for i, url in enumerate(urls):
            try:
                # 模拟处理
                await asyncio.sleep(1)
                results.append({
                    "url": url,
                    "status": "completed",
                    "summary": f"分析结果 {i + 1}",
                })
            except Exception as e:
                results.append({
                    "url": url,
                    "status": "failed",
                    "error": str(e),
                })

            task.progress = (i + 1) / total * 100
            task.updated_at = datetime.now().isoformat()

        completed = sum(1 for r in results if r["status"] == "completed")
        failed = sum(1 for r in results if r["status"] == "failed")

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "results": results,
        }


# 全局任务队列实例
task_queue = TaskQueue()
