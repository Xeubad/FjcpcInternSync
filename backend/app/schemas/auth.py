from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class LoginBody(BaseModel):
    """管理台账号密码，或旧版一次性 access token（字段名 token）。"""

    username: str | None = Field(None, max_length=128)
    password: str | None = Field(None, max_length=256)
    token: str | None = Field(None, max_length=4096)

    @model_validator(mode="after")
    def require_one_method(self) -> LoginBody:
        token_ok = bool((self.token or "").strip())
        password_ok = bool((self.username or "").strip() and (self.password or "").strip())
        if not token_ok and not password_ok:
            raise ValueError("请提供 username 与 password，或提供 token（一次性访问令牌）")
        return self


class GenerateTokenBody(BaseModel):
    admin_key: str = Field(..., min_length=1, max_length=256)


class RevokeTokenBody(BaseModel):
    admin_key: str = Field(..., min_length=1, max_length=256)
    token: str = Field(..., min_length=1, max_length=4096)


class SaveCookieBody(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=64)
    cookie_string: str = ""
    token: str = ""


class AnalyzeBody(BaseModel):
    content: str = Field(..., min_length=1)


class TextBatchUploadBody(BaseModel):
    """与旧版 /api/upload/day 等 JSON 字段一致（token 为实习平台 token）。"""

    content: str = Field(..., min_length=1)
    start_date: str = Field(..., min_length=8, max_length=32)
    student_id: str = ""
    token: str = ""


class ExcelCachedSubmitBody(BaseModel):
    """旧版 JSON 提交 Excel（cached_data）。"""

    student_id: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1, description="实习平台 fjcpc_token")
    cached_data: dict = Field(..., description="含 full_data.day/week/month")
