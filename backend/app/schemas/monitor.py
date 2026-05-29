from typing import Any

from pydantic import BaseModel


class DiagnosticsBody(BaseModel):
    recent_audit: list[dict[str, Any]]
    error_hints: list[dict[str, Any]]
