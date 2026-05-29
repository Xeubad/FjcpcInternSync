import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.repositories.access_token_repository import AccessTokenRepository

logger = logging.getLogger(__name__)


def mask_token_preview(token: str | None) -> str:
    """日志脱敏：仅保留前后片段。"""
    if not token:
        return ""
    if len(token) <= 12:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


class AuthService:
    """管理台账号 + 内存 Bearer；一次性访问令牌（JSON 文件）登录。"""

    def __init__(self, settings: Settings, access_tokens: AccessTokenRepository):
        self._settings = settings
        self._access_tokens = access_tokens
        self._sessions: dict[str, dict[str, Any]] = {}

    def login(self, username: str, password: str) -> dict[str, Any] | None:
        role: str | None = None
        if (
            username == self._settings.admin_username
            and password == self._settings.admin_password
        ):
            role = "admin"
        elif (
            username == self._settings.user_username
            and password == self._settings.user_password
        ):
            role = "user"
        if role is None:
            logger.info("登录失败 user=%s", username)
            return None
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {"username": username, "role": role, "auth_source": "password"}
        logger.info(
            "登录成功 user=%s role=%s token=%s",
            username,
            role,
            mask_token_preview(token),
        )
        return {"token": token, "role": role, "username": username}

    def login_with_file_access_token(self, raw_token: str) -> tuple[dict[str, Any] | None, str | None]:
        """旧版一次性 Token 登录：校验文件、标记已用、签发 Bearer。"""
        raw = raw_token.strip()
        if not raw:
            return None, "请输入访问Token"

        ok, result = self._access_tokens.validate_access(raw, check_used=True)
        if not ok:
            logger.warning("access token 登录失败: %s", result)
            return None, str(result)

        if raw != self._settings.dev_access_token:
            self._access_tokens.mark_used(raw)

        bearer = secrets.token_urlsafe(32)
        self._sessions[bearer] = {
            "username": "用户",
            "role": "user",
            "auth_source": "access_file_token",
        }
        logger.info("一次性 Token 登录成功，签发 Bearer token=%s", mask_token_preview(bearer))
        return (
            {
                "token": bearer,
                "role": "user",
                "username": "用户",
                "user_info": {
                    "username": "用户",
                    "login_time": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                },
            },
            None,
        )

    def logout(self, bearer: str | None) -> None:
        if bearer and bearer in self._sessions:
            del self._sessions[bearer]

    def validate_token(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        return self._sessions.get(token)
