import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import get_auth_service, optional_bearer
from app.core.errors import ErrorCode, api_error_payload
from app.core.limiter import limiter
from app.schemas.auth import GenerateTokenBody, LoginBody, RevokeTokenBody
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _login_success_payload(result: dict) -> dict:
    """兼容旧版前端：顶层带 user_info。"""
    user_info = result.get("user_info") or {
        "username": result.get("username", "用户"),
        "login_time": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    return {
        "success": True,
        "message": "登录成功",
        "data": result,
        "user_info": user_info,
    }


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginBody,
    auth: AuthService = Depends(get_auth_service),
):
    if (body.token or "").strip():
        result, err = auth.login_with_file_access_token(body.token or "")
        if err:
            payload = api_error_payload(ErrorCode.AUTH_INVALID_CREDENTIALS, err)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=payload)
        request.app.state.log_repository.append(
            "audit",
            {
                "event": "login_access_token",
                "username": result["username"],
                "role": result["role"],
                "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            },
        )
        return _login_success_payload(result)

    result = auth.login(body.username or "", body.password or "")
    if result is None:
        payload = api_error_payload(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=payload)
    request.app.state.log_repository.append(
        "audit",
        {
            "event": "login",
            "username": result["username"],
            "role": result["role"],
            "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return _login_success_payload(result)


@router.post("/logout")
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    auth: AuthService = Depends(get_auth_service),
):
    token = credentials.credentials if credentials else None
    auth.logout(token)
    return {"success": True, "message": "已登出"}


@router.get("/check")
@limiter.limit("300/minute")
async def auth_check(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    auth: AuthService = Depends(get_auth_service),
):
    token = credentials.credentials if credentials else None
    session = auth.validate_token(token)
    if session is None:
        return {"success": True, "logged_in": False}
    return {
        "success": True,
        "logged_in": True,
        "user_info": {"username": session.get("username", "用户")},
    }


@router.post("/generate_token")
@limiter.limit("10/minute")
async def generate_token(request: Request, body: GenerateTokenBody):
    settings = request.app.state.settings
    repo = request.app.state.access_token_repository
    raw, err = repo.generate(body.admin_key, settings.admin_key, settings.token_expire_days)
    if err:
        payload = api_error_payload(ErrorCode.AUTH_INVALID_CREDENTIALS, err)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=payload)
    return {
        "success": True,
        "message": "认证Token生成成功",
        "token": raw,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


@router.get("/tokens")
@limiter.limit("30/minute")
async def list_tokens(request: Request, admin_key: str = Query("")):
    settings = request.app.state.settings
    if not admin_key or admin_key != settings.admin_key:
        payload = api_error_payload(ErrorCode.AUTH_INVALID_CREDENTIALS, "管理员密钥错误")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=payload)
    repo = request.app.state.access_token_repository
    items = repo.list_tokens_for_admin()
    return {"success": True, "tokens": items, "total": len(items)}


@router.post("/revoke_token")
@limiter.limit("30/minute")
async def revoke_token(request: Request, body: RevokeTokenBody):
    settings = request.app.state.settings
    if not body.admin_key or body.admin_key != settings.admin_key:
        payload = api_error_payload(ErrorCode.AUTH_INVALID_CREDENTIALS, "管理员密钥错误")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=payload)
    repo = request.app.state.access_token_repository
    if not repo.revoke(body.token.strip()):
        payload = api_error_payload(ErrorCode.PARAM_INVALID, "Token不存在")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=payload)
    return {"success": True, "message": "Token已禁用"}


@router.get("/health")
@limiter.limit("300/minute")
async def auth_health(request: Request):
    return {
        "success": True,
        "service": "auth",
        "message": "认证服务运行正常",
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
