import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import auth, compat, health, monitor, tasks, uploads
from app.core.config import settings
from app.core.errors import ErrorCode, api_error_payload
from app.core.limiter import limiter
from app.core.logging_config import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.startup_maintenance import backup_access_tokens_file, cleanup_data_logs_and_backups
from app.repositories.access_token_repository import AccessTokenRepository
from app.repositories.json_log_repository import JsonLogRepository
from app.repositories.json_storage import JsonAtomicStore
from app.repositories.json_task_repository import JsonTaskRepository
from app.services.auth_service import AuthService
from app.services.monitor_service import MonitorService
from app.services.text_upload_service import TextUploadService
from app.services.upload_service import UploadService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.app_env)
    if settings.db_enabled:
        logger.warning("DB_ENABLED=true：SqlRepository 仍为骨架，第一阶段继续使用 JsonRepository")
    if settings.queue_enabled:
        logger.warning("QUEUE_ENABLED=true：队列尚未接入，任务仍在进程内执行")

    store = JsonAtomicStore(settings.data_path)
    store.ensure_dirs()

    (settings.data_path / "logs").mkdir(parents=True, exist_ok=True)
    backup_access_tokens_file(settings.access_tokens_path, settings.data_path)
    cleanup_data_logs_and_backups(settings.data_path)

    task_repository = JsonTaskRepository(store)
    log_repository = JsonLogRepository(store)

    access_token_repository = AccessTokenRepository(
        settings.access_tokens_path,
        dev_access_token=settings.dev_access_token,
    )
    auth_service = AuthService(settings, access_token_repository)
    upload_service = UploadService(settings, task_repository, log_repository)
    monitor_service = MonitorService(task_repository)
    text_upload_service = TextUploadService(settings)

    app.state.settings = settings
    app.state.store = store
    app.state.task_repository = task_repository
    app.state.log_repository = log_repository
    app.state.access_token_repository = access_token_repository
    app.state.auth_service = auth_service
    app.state.upload_service = upload_service
    app.state.monitor_service = monitor_service
    app.state.text_upload_service = text_upload_service

    spa = settings.spa_dist_path
    if spa:
        logger.info("检测到 React 构建目录，将作为 SPA 托管: %s", spa)
    else:
        logger.warning(
            "未找到 frontend/dist，请先在前端执行 npm run build，或设置 SPA_STATIC_DIR"
        )

    logger.info("FjcpcInternSync 后端已启动 env=%s data=%s", settings.app_env, settings.data_path)
    yield


app = FastAPI(title="FjcpcInternSync API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    payload = api_error_payload(
        ErrorCode.PARAM_INVALID,
        "请求参数不合法",
        detail=exc.errors(),
    )
    return JSONResponse(status_code=422, content=payload)


@app.exception_handler(HTTPException)
async def http_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    payload = api_error_payload(ErrorCode.SYSTEM_INTERNAL, str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=payload)


api_router_prefix = "/api"
app.include_router(health.router)
app.include_router(health.legacy_health_router)
app.include_router(auth.router, prefix=api_router_prefix)
app.include_router(tasks.router, prefix=api_router_prefix)
app.include_router(uploads.router, prefix=api_router_prefix)
app.include_router(monitor.router, prefix=api_router_prefix)
app.include_router(compat.router, prefix=api_router_prefix)


@app.get("/login.html")
async def redirect_login_html():
    return RedirectResponse(url="/login", status_code=302)


@app.get("/select.html")
async def redirect_select_html():
    return RedirectResponse(url="/app/dashboard", status_code=302)


@app.get("/txt_upload.html")
async def redirect_txt_upload_html():
    return RedirectResponse(url="/app/text-upload", status_code=302)


@app.get("/excel_upload.html")
async def redirect_excel_upload_html():
    return RedirectResponse(url="/app/tasks", status_code=302)


@app.get("/admin_panel.html")
async def redirect_admin_panel_html():
    return RedirectResponse(url="/app/admin/tokens", status_code=302)


@app.get("/api/meta")
async def meta():
    return {
        "success": True,
        "data": {
            "db_enabled": settings.db_enabled,
            "queue_enabled": settings.queue_enabled,
            "fjcpc_api_url": settings.fjcpc_api_url[:64] + ("…" if len(settings.fjcpc_api_url) > 64 else ""),
            "fjcpc_dry_run": settings.fjcpc_dry_run,
            "upstream_legacy_set": bool((settings.upstream_base_url or "").strip()),
            "access_tokens_path": str(settings.access_tokens_path),
        },
    }


_spa_dist = settings.spa_dist_path
if _spa_dist is not None:
    app.mount("/", StaticFiles(directory=str(_spa_dist), html=True), name="spa")
