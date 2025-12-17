"""
批量处理模块

支持批量处理多个播客文件
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import json
import uuid

from ..utils import get_logger, ensure_dir

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchItem:
    """批量处理项"""
    id: str
    source: str  # URL 或文件路径
    title: str = ""
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    error: Optional[str] = None
    result: Optional[Dict] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class BatchJob:
    """批量处理任务"""
    id: str
    name: str
    items: List[BatchItem] = field(default_factory=list)
    status: JobStatus = JobStatus.PENDING
    template: str = "default"
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @property
    def progress(self) -> float:
        """计算总体进度"""
        if not self.items:
            return 0.0
        completed = sum(1 for item in self.items if item.status == JobStatus.COMPLETED)
        return completed / len(self.items) * 100

    @property
    def completed_count(self) -> int:
        return sum(1 for item in self.items if item.status == JobStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status == JobStatus.FAILED)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "items": [
                {
                    "id": item.id,
                    "source": item.source,
                    "title": item.title,
                    "status": item.status.value,
                    "progress": item.progress,
                    "error": item.error,
                    "started_at": item.started_at,
                    "completed_at": item.completed_at,
                }
                for item in self.items
            ],
            "status": self.status.value,
            "template": self.template,
            "config": self.config,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
        }


class BatchProcessor:
    """批量处理器"""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        max_concurrent: int = 3,
    ):
        self.storage_dir = storage_dir or Path.home() / ".podcast_summary" / "batch"
        ensure_dir(self.storage_dir)
        self.max_concurrent = max_concurrent
        self._jobs: Dict[str, BatchJob] = {}
        self._process_func: Optional[Callable] = None
        self._progress_callback: Optional[Callable] = None
        self._load_jobs()

    def _load_jobs(self):
        """加载任务历史"""
        jobs_file = self.storage_dir / "jobs.json"
        if jobs_file.exists():
            try:
                with open(jobs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for job_data in data:
                        job = self._job_from_dict(job_data)
                        self._jobs[job.id] = job
            except Exception as e:
                logger.error(f"加载任务历史失败: {e}")

    def _save_jobs(self):
        """保存任务历史"""
        jobs_file = self.storage_dir / "jobs.json"
        try:
            # 只保留最近 100 个任务
            jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True
            )[:100]
            data = [job.to_dict() for job in jobs]
            with open(jobs_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务历史失败: {e}")

    def _job_from_dict(self, data: dict) -> BatchJob:
        """从字典创建任务"""
        items = [
            BatchItem(
                id=item["id"],
                source=item["source"],
                title=item.get("title", ""),
                status=JobStatus(item.get("status", "pending")),
                progress=item.get("progress", 0),
                error=item.get("error"),
                started_at=item.get("started_at"),
                completed_at=item.get("completed_at"),
            )
            for item in data.get("items", [])
        ]
        return BatchJob(
            id=data["id"],
            name=data["name"],
            items=items,
            status=JobStatus(data.get("status", "pending")),
            template=data.get("template", "default"),
            config=data.get("config", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )

    def set_processor(self, func: Callable):
        """设置处理函数"""
        self._process_func = func

    def on_progress(self, callback: Callable):
        """设置进度回调"""
        self._progress_callback = callback

    def create_job(
        self,
        name: str,
        sources: List[str],
        template: str = "default",
        config: Optional[Dict] = None,
    ) -> BatchJob:
        """创建批量任务"""
        job_id = str(uuid.uuid4())[:8]

        items = [
            BatchItem(
                id=str(uuid.uuid4())[:8],
                source=source,
                title=Path(source).stem if Path(source).exists() else source,
            )
            for source in sources
        ]

        job = BatchJob(
            id=job_id,
            name=name,
            items=items,
            template=template,
            config=config or {},
        )

        self._jobs[job_id] = job
        self._save_jobs()
        logger.info(f"创建批量任务: {name} ({len(items)} 项)")
        return job

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """获取任务"""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 20,
    ) -> List[BatchJob]:
        """列出任务"""
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """取消任务"""
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
            return False

        job.status = JobStatus.CANCELLED
        for item in job.items:
            if item.status == JobStatus.PENDING:
                item.status = JobStatus.CANCELLED

        self._save_jobs()
        logger.info(f"取消任务: {job_id}")
        return True

    async def _process_item(
        self,
        job: BatchJob,
        item: BatchItem,
    ):
        """处理单个项目"""
        if not self._process_func:
            logger.error("未设置处理函数")
            item.status = JobStatus.FAILED
            item.error = "未设置处理函数"
            return

        item.status = JobStatus.RUNNING
        item.started_at = datetime.now().isoformat()

        try:
            # 调用处理函数
            result = self._process_func(
                source=item.source,
                template=job.template,
                config=job.config,
            )
            if asyncio.iscoroutine(result):
                result = await result

            item.status = JobStatus.COMPLETED
            item.result = result
            item.progress = 100.0
            logger.info(f"处理完成: {item.title}")

        except Exception as e:
            item.status = JobStatus.FAILED
            item.error = str(e)
            logger.error(f"处理失败 [{item.title}]: {e}")

        finally:
            item.completed_at = datetime.now().isoformat()

            # 触发进度回调
            if self._progress_callback:
                try:
                    self._progress_callback(job, item)
                except:
                    pass

    async def run_job(self, job_id: str) -> BatchJob:
        """执行批量任务"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"任务不存在: {job_id}")

        if job.status == JobStatus.RUNNING:
            raise ValueError("任务正在执行中")

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now().isoformat()
        self._save_jobs()

        logger.info(f"开始执行批量任务: {job.name}")

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def process_with_semaphore(item: BatchItem):
            async with semaphore:
                if job.status == JobStatus.CANCELLED:
                    return
                await self._process_item(job, item)
                self._save_jobs()

        # 并发处理所有项目
        pending_items = [item for item in job.items if item.status == JobStatus.PENDING]
        await asyncio.gather(*[process_with_semaphore(item) for item in pending_items])

        # 更新任务状态
        if job.status != JobStatus.CANCELLED:
            if job.failed_count > 0:
                job.status = JobStatus.FAILED if job.completed_count == 0 else JobStatus.COMPLETED
            else:
                job.status = JobStatus.COMPLETED

        job.completed_at = datetime.now().isoformat()
        self._save_jobs()

        logger.info(
            f"批量任务完成: {job.name} "
            f"(成功: {job.completed_count}, 失败: {job.failed_count})"
        )

        return job

    def create_job_from_folder(
        self,
        folder_path: Path,
        name: Optional[str] = None,
        extensions: List[str] = None,
        **kwargs,
    ) -> BatchJob:
        """从文件夹创建批量任务"""
        if extensions is None:
            extensions = [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus"]

        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"文件夹不存在: {folder_path}")

        sources = []
        for ext in extensions:
            sources.extend(str(f) for f in folder.glob(f"*{ext}"))

        if not sources:
            raise ValueError(f"文件夹中没有找到音频文件: {folder_path}")

        return self.create_job(
            name=name or folder.name,
            sources=sorted(sources),
            **kwargs,
        )

    def retry_failed(self, job_id: str) -> Optional[BatchJob]:
        """重试失败的项目"""
        job = self.get_job(job_id)
        if not job:
            return None

        # 重置失败的项目
        for item in job.items:
            if item.status == JobStatus.FAILED:
                item.status = JobStatus.PENDING
                item.error = None
                item.progress = 0
                item.started_at = None
                item.completed_at = None

        job.status = JobStatus.PENDING
        self._save_jobs()
        return job

    def get_summary(self) -> Dict[str, Any]:
        """获取处理统计摘要"""
        total_jobs = len(self._jobs)
        completed_jobs = sum(1 for j in self._jobs.values() if j.status == JobStatus.COMPLETED)
        failed_jobs = sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED)

        total_items = sum(len(j.items) for j in self._jobs.values())
        completed_items = sum(j.completed_count for j in self._jobs.values())
        failed_items = sum(j.failed_count for j in self._jobs.values())

        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "pending_jobs": total_jobs - completed_jobs - failed_jobs,
            "total_items": total_items,
            "completed_items": completed_items,
            "failed_items": failed_items,
            "success_rate": completed_items / total_items * 100 if total_items > 0 else 0,
        }
