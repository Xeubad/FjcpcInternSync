from datetime import datetime, timezone
from typing import Any

from app.models.constants import SCHEMA_VERSION
from app.repositories.json_storage import JsonAtomicStore


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class JsonLogRepository:
    """按日聚合的日志文件：audit / request / business。"""

    def __init__(self, store: JsonAtomicStore):
        self._store = store
        self._logs_dir = store.base_dir / "logs"
        self._lock = store._mem_lock("logs")

    def _channel_path(self, channel: str) -> Any:
        day = _today_str()
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in channel)
        return self._logs_dir / f"{safe}_{day}.json"

    def append(self, channel: str, entry: dict[str, Any]) -> None:
        path = self._channel_path(channel)
        with self._lock:
            with self._store.with_file_lock(path):
                raw = self._store.read_json(path)
                if raw is None:
                    doc = {"schema_version": SCHEMA_VERSION, "entries": []}
                else:
                    doc = raw if isinstance(raw, dict) else {"schema_version": SCHEMA_VERSION, "entries": []}
                entries = doc.get("entries")
                if not isinstance(entries, list):
                    entries = []
                entries.append(entry)
                doc["entries"] = entries[-5000:]
                self._store.write_json_atomic(path, doc)

    def list_recent(self, channel: str, limit: int = 200) -> list[dict[str, Any]]:
        path = self._channel_path(channel)
        with self._lock:
            with self._store.with_file_lock(path):
                raw = self._store.read_json(path)
        if not isinstance(raw, dict):
            return []
        entries = raw.get("entries")
        if not isinstance(entries, list):
            return []
        return entries[-limit:]
