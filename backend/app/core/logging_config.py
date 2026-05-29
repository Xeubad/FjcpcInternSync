import json
import logging
import sys
from typing import Any

from app.core.context import request_id_var


class RequestIdFilter(logging.Filter):
    """为日志记录注入 request_id（contextvars + LogRecord）。"""

    def filter(self, record: logging.LogRecord) -> bool:
        rid = getattr(record, "request_id", None) or request_id_var.get()
        record.request_id = rid or "-"
        return True


class JsonLineFormatter(logging.Formatter):
    """生产环境每行一条 JSON，便于采集。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(app_env: str) -> None:
    """结构化日志：开发人类可读，生产 JSON 行。"""
    root = logging.getLogger()
    root.handlers.clear()
    level = logging.DEBUG if app_env == "development" else logging.INFO
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    if app_env == "development":
        fmt = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
    else:
        handler.setFormatter(JsonLineFormatter())

    root.addHandler(handler)


def log_extra(request_id: str | None = None) -> dict[str, Any]:
    return {"request_id": request_id or "-"}
