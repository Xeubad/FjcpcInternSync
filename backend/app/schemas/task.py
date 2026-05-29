from typing import Any

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    report_type: str = Field(pattern="^(day|week|month)$")
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    task: dict[str, Any]


class TaskListResponse(BaseModel):
    tasks: list[dict[str, Any]]
