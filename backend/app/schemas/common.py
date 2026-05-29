from typing import Any

from pydantic import BaseModel


class ApiSuccess(BaseModel):
    success: bool = True
    data: Any | None = None
    message: str | None = None


class ApiErrorBody(BaseModel):
    code: str
    detail: Any | None = None


class ApiFailure(BaseModel):
    success: bool = False
    message: str
    error: ApiErrorBody
