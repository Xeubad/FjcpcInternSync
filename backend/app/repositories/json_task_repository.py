import uuid
from datetime import datetime, timezone
from typing import Any

from app.models.constants import SCHEMA_VERSION
from app.repositories.json_storage import JsonAtomicStore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class JsonTaskRepository:
    def __init__(self, store: JsonAtomicStore):
        self._store = store
        self._tasks_dir = store.base_dir / "tasks"
        self._lock = store._mem_lock("tasks")

    def create(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("id") or str(uuid.uuid4())
        now = _utc_now_iso()
        record = {
            "schema_version": SCHEMA_VERSION,
            "id": task_id,
            "type": task["type"],
            "status": task.get("status", "pending"),
            "created_at": now,
            "updated_at": now,
            "created_by": task.get("created_by", "unknown"),
            "payload": task.get("payload") or {},
            "error_code": task.get("error_code"),
            "retry_count": int(task.get("retry_count", 0)),
        }
        path = self._tasks_dir / f"{task_id}.json"
        with self._lock:
            with self._store.with_file_lock(path):
                self._store.write_json_atomic(path, record)
        return record

    def get(self, task_id: str) -> dict[str, Any] | None:
        path = self._tasks_dir / f"{task_id}.json"
        with self._lock:
            with self._store.with_file_lock(path):
                data = self._store.read_json(path)
        return data if isinstance(data, dict) else None

    def list_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        self._tasks_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(
            self._tasks_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        out: list[dict[str, Any]] = []
        with self._lock:
            for path in files[:limit]:
                with self._store.with_file_lock(path):
                    data = self._store.read_json(path)
                if isinstance(data, dict):
                    out.append(data)
        return out

    def update(self, task_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        path = self._tasks_dir / f"{task_id}.json"
        with self._lock:
            with self._store.with_file_lock(path):
                current = self._store.read_json(path)
                if not isinstance(current, dict):
                    return None
                merged = {**current, **patch, "updated_at": _utc_now_iso()}
                self._store.write_json_atomic(path, merged)
                return merged

    def claim_for_run(self, task_id: str) -> tuple[str, dict[str, Any] | None]:
        """原子抢占任务执行权：在同一把锁内读状态并改为 running。

        返回 (outcome, task):
        - outcome="claimed"：抢占成功，task 为已置 running 的记录
        - outcome="not_found"：任务不存在
        - outcome="running"：已在执行中（其它触发已抢占）
        - outcome="success"：已完成（拒绝重复执行以免重复上传）
        """
        path = self._tasks_dir / f"{task_id}.json"
        with self._lock:
            with self._store.with_file_lock(path):
                current = self._store.read_json(path)
                if not isinstance(current, dict):
                    return "not_found", None
                status = str(current.get("status") or "")
                if status == "running":
                    return "running", current
                if status == "success":
                    return "success", current
                merged = {**current, "status": "running", "updated_at": _utc_now_iso()}
                self._store.write_json_atomic(path, merged)
                return "claimed", merged
