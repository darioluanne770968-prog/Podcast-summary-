"""
API 路由定义
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from .tasks import task_queue, TaskStatus
from ..utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============ 数据模型 ============

class AnalyzeRequest(BaseModel):
    """分析请求"""
    url: Optional[str] = Field(None, description="播客 URL")
    template: str = Field("default", description="分析模板")
    options: Dict[str, Any] = Field(default_factory=dict, description="分析选项")


class AnalyzeResponse(BaseModel):
    """分析响应"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    top_k: int = Field(10, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None


class BatchRequest(BaseModel):
    """批量处理请求"""
    urls: List[str]
    template: str = "default"
    options: Dict[str, Any] = Field(default_factory=dict)


# ============ 分析接口 ============

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_podcast(request: AnalyzeRequest):
    """
    提交播客分析任务

    - **url**: 播客 URL（支持 YouTube、RSS、直接链接等）
    - **template**: 分析模板（default, quick, deep, study, content_creator）
    - **options**: 额外选项
    """
    if not request.url:
        raise HTTPException(status_code=400, detail="URL 不能为空")

    task_id = await task_queue.submit(
        task_type="analyze",
        params={
            "url": request.url,
            "template": request.template,
            "options": request.options,
        },
    )

    return AnalyzeResponse(
        task_id=task_id,
        status="pending",
        message="任务已提交",
    )


@router.post("/analyze/upload", response_model=AnalyzeResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    template: str = Query("default"),
):
    """
    上传音频文件进行分析

    - **file**: 音频文件
    - **template**: 分析模板
    """
    # 验证文件类型
    allowed_types = ["audio/mpeg", "audio/wav", "audio/mp4", "audio/x-m4a", "audio/ogg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}",
        )

    # 保存文件
    import tempfile
    import os
    from pathlib import Path

    temp_dir = Path(tempfile.gettempdir()) / "podcast_uploads"
    temp_dir.mkdir(exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1] or ".mp3"
    temp_path = temp_dir / f"{uuid.uuid4()}{file_ext}"

    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    task_id = await task_queue.submit(
        task_type="analyze",
        params={
            "file_path": str(temp_path),
            "template": template,
            "cleanup": True,
        },
    )

    return AnalyzeResponse(
        task_id=task_id,
        status="pending",
        message="文件已上传，任务已提交",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态

    - **task_id**: 任务 ID
    """
    task = await task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskStatusResponse(
        task_id=task["id"],
        status=task["status"],
        progress=task["progress"],
        result=task.get("result"),
        error=task.get("error"),
        created_at=task["created_at"],
        updated_at=task["updated_at"],
    )


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    取消任务

    - **task_id**: 任务 ID
    """
    success = await task_queue.cancel(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在或无法取消")

    return {"message": "任务已取消"}


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    列出任务

    - **status**: 过滤状态（pending, running, completed, failed）
    - **limit**: 返回数量
    - **offset**: 偏移量
    """
    tasks = await task_queue.list_tasks(status=status, limit=limit, offset=offset)
    return {
        "tasks": tasks,
        "total": len(tasks),
        "limit": limit,
        "offset": offset,
    }


# ============ 批量处理接口 ============

@router.post("/batch", response_model=AnalyzeResponse)
async def batch_analyze(request: BatchRequest):
    """
    批量分析播客

    - **urls**: URL 列表
    - **template**: 分析模板
    - **options**: 额外选项
    """
    if not request.urls:
        raise HTTPException(status_code=400, detail="URL 列表不能为空")

    if len(request.urls) > 50:
        raise HTTPException(status_code=400, detail="单次最多处理 50 个 URL")

    task_id = await task_queue.submit(
        task_type="batch",
        params={
            "urls": request.urls,
            "template": request.template,
            "options": request.options,
        },
    )

    return AnalyzeResponse(
        task_id=task_id,
        status="pending",
        message=f"批量任务已提交，共 {len(request.urls)} 个",
    )


# ============ 搜索接口 ============

@router.post("/search")
async def search_knowledge(request: SearchRequest):
    """
    搜索知识库

    - **query**: 搜索查询
    - **top_k**: 返回数量
    - **filters**: 过滤条件
    """
    try:
        from ..search import KnowledgeBase
        kb = KnowledgeBase()
        results = kb.search(
            query=request.query,
            top_k=request.top_k,
        )
        return {
            "results": [entry.to_dict() for entry in results],
            "total": len(results),
        }
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 模板接口 ============

@router.get("/templates")
async def list_templates():
    """列出可用模板"""
    try:
        from ..personalization import TemplateManager
        tm = TemplateManager()
        templates = tm.list_templates()
        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "tags": t.tags,
                }
                for t in templates
            ],
        }
    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """获取模板详情"""
    try:
        from ..personalization import TemplateManager
        tm = TemplateManager()
        template = tm.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        return template.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 收藏接口 ============

@router.get("/collections")
async def list_collections():
    """列出收藏夹"""
    try:
        from ..personalization import CollectionManager
        cm = CollectionManager()
        collections = cm.list_collections()
        return {
            "collections": [c.to_dict() for c in collections],
        }
    except Exception as e:
        logger.error(f"获取收藏夹失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections/{collection_id}/items")
async def add_to_collection(collection_id: str, item: Dict[str, Any]):
    """添加到收藏夹"""
    try:
        from ..personalization import CollectionManager, CollectionItem, CollectionItemType
        cm = CollectionManager()

        collection_item = CollectionItem(
            id=item.get("id", str(uuid.uuid4())[:8]),
            type=CollectionItemType(item.get("type", "note")),
            title=item.get("title", ""),
            content=item.get("content", ""),
            source_podcast=item.get("source_podcast"),
            tags=item.get("tags", []),
        )

        success = cm.add_to_collection(collection_id, collection_item)
        if not success:
            raise HTTPException(status_code=404, detail="收藏夹不存在")

        return {"message": "添加成功", "item_id": collection_item.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加收藏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 订阅接口 ============

@router.get("/subscriptions")
async def list_subscriptions():
    """列出 RSS 订阅"""
    try:
        from ..automation import RSSMonitor
        monitor = RSSMonitor()
        subs = monitor.list_subscriptions()
        return {
            "subscriptions": [s.to_dict() for s in subs],
        }
    except Exception as e:
        logger.error(f"获取订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions")
async def add_subscription(
    name: str,
    feed_url: str,
    auto_process: bool = True,
):
    """添加 RSS 订阅"""
    try:
        from ..automation import RSSMonitor
        monitor = RSSMonitor()
        sub = monitor.add_subscription(name, feed_url, auto_process)
        return sub.to_dict()
    except Exception as e:
        logger.error(f"添加订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/subscriptions/{sub_id}")
async def remove_subscription(sub_id: str):
    """移除 RSS 订阅"""
    try:
        from ..automation import RSSMonitor
        monitor = RSSMonitor()
        success = monitor.remove_subscription(sub_id)
        if not success:
            raise HTTPException(status_code=404, detail="订阅不存在")
        return {"message": "订阅已移除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 统计接口 ============

@router.get("/stats")
async def get_stats():
    """获取系统统计"""
    try:
        stats = {
            "queue": await task_queue.get_stats(),
        }

        try:
            from ..search import KnowledgeBase
            kb = KnowledgeBase()
            stats["knowledge_base"] = kb.get_stats()
        except:
            pass

        try:
            from ..automation import BatchProcessor
            bp = BatchProcessor()
            stats["batch_processor"] = bp.get_summary()
        except:
            pass

        return stats
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
