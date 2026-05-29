import logging
from typing import Any

from app.repositories.interfaces import TaskRepository

logger = logging.getLogger(__name__)


class MonitorService:
    """任务聚合统计（成功率 / 失败分布）。"""

    def __init__(self, tasks: TaskRepository):
        self._tasks = tasks

    def task_summary(self, window: int = 100) -> dict[str, Any]:
        tasks = self._tasks.list_tasks(limit=window)
        total = len(tasks)
        success = sum(1 for t in tasks if t.get("status") == "success")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        pending = sum(1 for t in tasks if t.get("status") in ("pending", "running"))
        error_buckets: dict[str, int] = {}
        for t in tasks:
            if t.get("status") == "failed" and t.get("error_code"):
                code = str(t["error_code"])
                error_buckets[code] = error_buckets.get(code, 0) + 1
        top_errors = sorted(error_buckets.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            "window_size": window,
            "total": total,
            "success": success,
            "failed": failed,
            "pending": pending,
            "success_rate": (success / total) if total else 0.0,
            "top_errors": [{"code": c, "count": n} for c, n in top_errors],
        }
