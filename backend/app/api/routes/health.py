import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# 旧版监控脚本使用 GET /api/health
legacy_health_router = APIRouter(prefix="/api", tags=["health-legacy"])


@router.get("/health")
async def health(request: Request):
    settings = request.app.state.settings
    store = request.app.state.store
    checks: dict = {"filesystem": False, "token_storage": False, "upstream": None}

    try:
        probe = store.base_dir / ".write_probe.json"
        store.write_json_atomic(probe, {"ok": True})
        probe.unlink(missing_ok=True)
        checks["filesystem"] = True
    except OSError as exc:
        logger.warning("文件系统探测失败: %s", exc)

    try:
        token_dir = settings.access_tokens_path.parent
        token_dir.mkdir(parents=True, exist_ok=True)
        probe = token_dir / ".probe_access_tokens.json"
        store.write_json_atomic(probe, {"ok": True})
        probe.unlink(missing_ok=True)
        checks["token_storage"] = True
    except OSError as exc:
        logger.warning("访问令牌存储目录不可写: %s", exc)

    base = (settings.upstream_base_url or settings.fjcpc_api_url or "").strip()
    if base:
        try:
            async with httpx.AsyncClient(
                timeout=5.0,
                verify=settings.fjcpc_verify_tls,
            ) as client:
                response = await client.head(base.rstrip("/"))
            checks["upstream"] = {
                "reachable": True,
                "status_code": response.status_code,
                "url": base[:80],
            }
        except Exception as exc:
            checks["upstream"] = {"reachable": False, "error": str(exc), "url": base[:80]}
    else:
        checks["upstream"] = {"skipped": True}

    healthy = bool(checks["filesystem"]) and bool(checks["token_storage"])
    body = {"success": healthy, "data": {"checks": checks}}
    return JSONResponse(status_code=200 if healthy else 503, content=body)


@legacy_health_router.get("/health")
async def health_flask_compatible(request: Request):
    """与旧版 Flask /api/health 相近的 JSON 结构（status + checks 字符串）。"""
    settings = request.app.state.settings
    store = request.app.state.store
    repo = request.app.state.access_token_repository

    health_body: dict = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": {},
    }

    try:
        probe = store.base_dir / ".write_probe_legacy.json"
        store.write_json_atomic(probe, {"ok": True})
        probe.unlink(missing_ok=True)
        health_body["checks"]["filesystem"] = "ok"
    except Exception as exc:
        health_body["checks"]["filesystem"] = f"failed: {exc}"
        health_body["status"] = "unhealthy"

    try:
        repo.load_all()
        health_body["checks"]["token_storage"] = "ok"
    except Exception as exc:
        health_body["checks"]["token_storage"] = f"failed: {exc}"
        health_body["status"] = "unhealthy"

    base = (settings.upstream_base_url or settings.fjcpc_api_url or "").strip()
    if base:
        try:
            async with httpx.AsyncClient(
                timeout=5.0,
                verify=settings.fjcpc_verify_tls,
            ) as client:
                await client.head(base.rstrip("/"))
            health_body["checks"]["api_connection"] = "ok"
        except Exception as exc:
            health_body["checks"]["api_connection"] = f"warning: {exc}"
    else:
        health_body["checks"]["api_connection"] = "skipped"

    code = 200 if health_body["status"] == "healthy" else 503
    return JSONResponse(content=health_body, status_code=code)
