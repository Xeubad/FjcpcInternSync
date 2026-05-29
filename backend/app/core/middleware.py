import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import request_id_var

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """注入 request_id，并记录耗时。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            response.headers["X-Request-Id"] = request_id
            logger.info(
                "%s %s -> %s %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
                extra={"request_id": request_id},
            )
            return response
        finally:
            request_id_var.reset(token)
