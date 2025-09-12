from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI, Request

from app.config import Settings, get_settings
from app.routes import meta, auth, users

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def _configure_logging() -> None:
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
        response = None  # avoid UnboundLocalError if call_next raises
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
    Application factory.
    - Exposes `app.state.start_time` for health/uptime.
    - Wires routes from app.routes.*
    """
    _configure_logging()

    settings: Settings = get_settings()
    app = FastAPI(title="Lucid API", version=settings.VERSION)

    # Record start time for health/uptime
    app.state.start_time = datetime.now(tz=timezone.utc)

    # Request logging middleware
    _request_logger(app)

    # Routers
    app.include_router(meta.router, tags=["meta"])
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(users.router, prefix="/users", tags=["users"])

    # Root fallback mirroring meta
    @app.get("/", include_in_schema=False)
    def _root():
        return {
            "service": settings.SERVICE_NAME,
            "status": "ok",
            "time": datetime.now(timezone.utc).isoformat(),
            "version": settings.VERSION,
        }

    return app


# ASGI entrypoint used by uvicorn
app = create_app()
