from enum import Enum


class ErrorCode(str, Enum):
    """统一错误码（鉴权 / 参数 / 上游 / 系统）。"""

    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"

    PARAM_INVALID = "PARAM_INVALID"
    PARAM_MISSING = "PARAM_MISSING"

    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    UPSTREAM_HTTP_ERROR = "UPSTREAM_HTTP_ERROR"
    UPSTREAM_NETWORK = "UPSTREAM_NETWORK"

    SYSTEM_INTERNAL = "SYSTEM_INTERNAL"
    SYSTEM_IO = "SYSTEM_IO"


def api_error_payload(code: ErrorCode, message: str, detail: object | None = None) -> dict:
    body: dict = {"success": False, "message": message, "error": {"code": code.value}}
    if detail is not None:
        body["error"]["detail"] = detail
    return body
