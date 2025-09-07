# Path: 03-api-gateway/api/app/middleware/logging.py
# Request logging middleware with timing; aligns with FastAPI middleware pattern. :contentReference[oaicite:4]{index=4}

import time
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.logger import get_logger

log = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        path = request.url.path
        method = request.method
        client = request.client.host if request.client else "unknown"

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
        log.info(
            "http_request",
            extra={
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "client": client,
                "elapsed_ms": elapsed_ms,
            },
        )
        return response
