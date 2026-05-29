from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import ErrorCode, api_error_payload
from app.services.auth_service import AuthService
from app.services.monitor_service import MonitorService
from app.services.text_upload_service import TextUploadService
from app.services.upload_service import UploadService

security = HTTPBearer(auto_error=False)
optional_bearer = HTTPBearer(auto_error=False)


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_upload_service(request: Request) -> UploadService:
    return request.app.state.upload_service


def get_monitor_service(request: Request) -> MonitorService:
    return request.app.state.monitor_service


def get_text_upload_service(request: Request) -> TextUploadService:
    return request.app.state.text_upload_service


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth: AuthService = Depends(get_auth_service),
):
    token = credentials.credentials if credentials else None
    session = auth.validate_token(token)
    if session is None:
        payload = api_error_payload(ErrorCode.AUTH_TOKEN_INVALID, "未登录或令牌无效")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=payload)
    return session


async def require_admin(session: dict = Depends(require_auth)):
    if session.get("role") != "admin":
        payload = api_error_payload(ErrorCode.AUTH_FORBIDDEN, "需要管理员权限")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=payload)
    return session


AuthUser = Annotated[dict, Depends(require_auth)]
AdminUser = Annotated[dict, Depends(require_admin)]
