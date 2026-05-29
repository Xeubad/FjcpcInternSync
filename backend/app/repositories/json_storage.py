import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from filelock import FileLock


class JsonAtomicStore:
    """JSON 原子写入（临时文件 + replace）与按路径文件锁。"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._memory_locks: dict[str, threading.Lock] = {}
        self._memory_guard = threading.Lock()

    def _mem_lock(self, key: str) -> threading.Lock:
        with self._memory_guard:
            if key not in self._memory_locks:
                self._memory_locks[key] = threading.Lock()
            return self._memory_locks[key]

    def ensure_dirs(self) -> None:
        for sub in ("tasks", "logs", "config"):
            (self.base_dir / sub).mkdir(parents=True, exist_ok=True)

    def read_json(self, path: Path) -> Any | None:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write_json_atomic(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                json.dump(data, tmp, ensure_ascii=False, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except OSError:
                    pass

    def with_file_lock(self, path: Path):
        lock_path = path.with_suffix(path.suffix + ".lock")
        return FileLock(str(lock_path), timeout=30)
