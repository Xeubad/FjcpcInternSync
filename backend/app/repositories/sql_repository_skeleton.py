"""第二阶段 SqlRepository 空骨架（DB_ENABLED=true 时可替换实现）。"""

from typing import Any


class SqlTaskRepositoryStub:
    def create(self, task: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("SqlTaskRepository 尚未实现，请保持 DB_ENABLED=false")

    def get(self, task_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("SqlTaskRepository 尚未实现，请保持 DB_ENABLED=false")

    def list_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        raise NotImplementedError("SqlTaskRepository 尚未实现，请保持 DB_ENABLED=false")

    def update(self, task_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError("SqlTaskRepository 尚未实现，请保持 DB_ENABLED=false")

    def claim_for_run(self, task_id: str) -> tuple[str, dict[str, Any] | None]:
        raise NotImplementedError("SqlTaskRepository 尚未实现，请保持 DB_ENABLED=false")


class SqlLogRepositoryStub:
    def append(self, channel: str, entry: dict[str, Any]) -> None:
        raise NotImplementedError("SqlLogRepository 尚未实现")

    def list_recent(self, channel: str, limit: int = 200) -> list[dict[str, Any]]:
        raise NotImplementedError("SqlLogRepository 尚未实现")
