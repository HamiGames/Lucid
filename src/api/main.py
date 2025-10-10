from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import FastAPI, Request

from src.api.utils.config import service_name, service_version

# Routers (each defines its own prefix/tags)
from src.api.routes.meta import router as meta_router
from src.api.routes.auth import router as auth_router
from src.api.routes.users import router as users_router
from src.api.routes.health import router as health_router

# NEW: proxied Cluster B routers
from src.api.routes.blockchain import router as blockchain_router
from src.api.routes.wallets import router as wallets_router

# Optional: Mongo health probe (kept non-fatal)
try:
    from src.api.db.connection import ping as mongo_ping  # type: ignore
except Exception:
    mongo_ping = None  # type: ignore[assignment]

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def _configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, _LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _request_logger(app: FastAPI) -> None:
    @app.middleware("http")
    async def _log_requests(request: Request, call_next: Callable):
        logger = logging.getLogger("src.api.request")
        start = request.state.start = datetime.now(tz=timezone.utc)

        response = await call_next(request)

        duration_ms = int(
            (datetime.now(tz=timezone.utc) - start).total_seconds() * 1000
        )

        logger.info(
            "%s %s -> %d (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response


def create_app() -> FastAPI:
    _configure_logging()
    service_name_val = service_name()
    service_version_val = service_version()

    app = FastAPI(
        title="Lucid API",
        version=service_version_val,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.state.start_time = datetime.now(tz=timezone.utc)
    _request_logger(app)

    # Routers (Cluster A scope)
    # meta_router should expose /meta/* internally (prefix defined in router)
    app.include_router(meta_router)
    app.include_router(auth_router, prefix="/auth")
    app.include_router(users_router, prefix="/users")
    app.include_router(health_router)

    # Proxied Cluster B endpoints (Blockchain Core)
    # These appear in the gateway OpenAPI as /chain/* and /wallets/*
    app.include_router(blockchain_router)
    app.include_router(wallets_router)

    @app.get("/", include_in_schema=False)
    def _root():
        return {
            "service": service_name_val,
            "status": "ok",
            "time": datetime.now(timezone.utc).isoformat(),
            "version": service_version_val,
        }

    @app.get("/health", tags=["meta"], summary="Service health")
    def _health() -> dict:
        mongo_ok: Optional[bool] = None
        mongo_error: Optional[str] = None
        if mongo_ping:
            try:
                mongo_ping()
                mongo_ok = True
            except Exception as e:
                mongo_ok = False
                mongo_error = str(e)

        return {
            "ok": True,
            "service": service_name_val,
            "started_at": app.state.start_time.isoformat(),
            "version": service_version_val,
            "dependencies": {"mongo": {"ok": mongo_ok, "error": mongo_error}},
        }

    return app


app = create_app()
