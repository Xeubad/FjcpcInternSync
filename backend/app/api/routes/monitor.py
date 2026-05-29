from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app.api.deps import AdminUser, AuthUser, get_monitor_service
from app.schemas.common import ApiSuccess
from app.services.monitor_service import MonitorService

router = APIRouter(prefix="/monitor", tags=["monitor"])

ERROR_HINTS = [
    {
        "code": "UPSTREAM_TIMEOUT",
        "hint": "检查上游地址、VPN、aTrust 证书或增大超时时间",
    },
    {
        "code": "UPSTREAM_HTTP_ERROR",
        "hint": "查看上游返回体，核对 Token / Cookie 是否过期",
    },
    {
        "code": "AUTH_TOKEN_INVALID",
        "hint": "重新登录获取令牌",
    },
]


@router.get("/summary")
async def summary(
    session: AuthUser,
    monitor: MonitorService = Depends(get_monitor_service),
    window: int = 100,
):
    data = monitor.task_summary(window=window)
    return ApiSuccess(data=data).model_dump()


@router.get("/diagnostics")
async def diagnostics(request: Request, session: AdminUser):
    log_repo = request.app.state.log_repository
    monitor_service: MonitorService = request.app.state.monitor_service
    audit = log_repo.list_recent("audit", limit=100)
    summary = monitor_service.task_summary(window=200)
    return ApiSuccess(
        data={
            "recent_audit": audit,
            "task_summary": summary,
            "error_hints": ERROR_HINTS,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
    ).model_dump()
