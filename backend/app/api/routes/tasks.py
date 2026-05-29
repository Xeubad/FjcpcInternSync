import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.api.deps import AuthUser, get_upload_service
from app.core.errors import ErrorCode, api_error_payload
from app.schemas.common import ApiSuccess
from app.schemas.task import TaskCreateRequest
from app.services.upload_service import UploadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _filter_tasks_for_user(tasks: list[dict], session: dict) -> list[dict]:
    if session.get("role") == "admin":
        return tasks
    username = session.get("username")
    return [t for t in tasks if t.get("created_by") == username]


@router.get("")
async def list_tasks(request: Request, session: AuthUser, limit: int = 100):
    repo = request.app.state.task_repository
    tasks = repo.list_tasks(limit=limit)
    return ApiSuccess(data={"tasks": _filter_tasks_for_user(tasks, session)}).model_dump()


@router.post("")
async def create_task(
    body: TaskCreateRequest,
    session: AuthUser,
    upload: UploadService = Depends(get_upload_service),
):
    task = upload.create_task(
        body.report_type,
        body.payload,
        created_by=session.get("username", "unknown"),
    )
    return ApiSuccess(data={"task": task}).model_dump()


@router.get("/{task_id}")
async def get_task(task_id: str, request: Request, session: AuthUser):
    repo = request.app.state.task_repository
    task = repo.get(task_id)
    if task is None:
        payload = api_error_payload(ErrorCode.PARAM_INVALID, "任务不存在")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=payload)
    if session.get("role") != "admin" and task.get("created_by") != session.get("username"):
        payload = api_error_payload(ErrorCode.AUTH_FORBIDDEN, "无权查看该任务")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=payload)
    return ApiSuccess(data={"task": task}).model_dump()


@router.post("/{task_id}/run")
async def run_task(
    task_id: str,
    request: Request,
    session: AuthUser,
    background_tasks: BackgroundTasks,
    upload: UploadService = Depends(get_upload_service),
):
    repo = request.app.state.task_repository
    task = repo.get(task_id)
    if task is None:
        payload = api_error_payload(ErrorCode.PARAM_INVALID, "任务不存在")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=payload)
    if session.get("role") != "admin" and task.get("created_by") != session.get("username"):
        payload = api_error_payload(ErrorCode.AUTH_FORBIDDEN, "无权执行该任务")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=payload)

    background_tasks.add_task(upload.execute_task, task_id)
    logger.info("已排队执行任务 task_id=%s user=%s", task_id, session.get("username"))
    return ApiSuccess(message="任务已排队执行").model_dump()


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    request: Request,
    session: AuthUser,
    background_tasks: BackgroundTasks,
    upload: UploadService = Depends(get_upload_service),
):
    repo = request.app.state.task_repository
    task = repo.get(task_id)
    if task is None:
        payload = api_error_payload(ErrorCode.PARAM_INVALID, "任务不存在")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=payload)
    if session.get("role") != "admin" and task.get("created_by") != session.get("username"):
        payload = api_error_payload(ErrorCode.AUTH_FORBIDDEN, "无权重试该任务")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=payload)
    repo.update(task_id, {"status": "pending", "error_code": None})

    background_tasks.add_task(upload.execute_task, task_id)
    return ApiSuccess(message="任务已重置并排队重试").model_dump()
