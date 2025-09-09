from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI, Request
from .routes.health import router as health_router

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def _configure_logging() -> None:
    # Simple, consistent logging format usable in containers
    logging.basicConfig(
        level=getattr(logging, _LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _request_logger(app: FastAPI) -> None:
    @app.middleware("http")
    async def _log_requests(request: Request, call_next: Callable):
        logger = logging.getLogger("app.request")
        path = request.url.path
        method = request.method
        start = datetime.now(tz=timezone.utc)
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (
                datetime.now(tz=timezone.utc) - start
            ).total_seconds() * 1000.0
            logger.info(
                "%s %s -> %s (%.2fms)",
                method,
                path,
                getattr(response, "status_code", "?"),
                duration_ms,
            )


def create_app() -> FastAPI:
    """
    Application factory (kept for tests and parity with project scripts).
    - Exposes `app.state.start_time` for health/uptime.
    - Wires routes from app.routes.*
    """
    _configure_logging()

    app = FastAPI(title="Lucid API", version="0.1.0")

    # Record monotonic-ish start time for health endpoint
    app.state.start_time = datetime.now(tz=timezone.utc)

    # Lightweight request logging middleware (compatible with test suite expectations)
    _request_logger(app)

    # Routers
    app.include_router(health_router)

    return app


# ASGI entrypoint used by uvicorn
app = create_app()
