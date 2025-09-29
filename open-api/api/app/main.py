from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import FastAPI, Request

from app.config import Settings, get_settings

# Routers (each defines its own prefix/tags)
from app.routes.meta import router as meta_router
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router

# NEW: proxied Cluster B routers
from app.routes.chain_proxy import router as chain_proxy_router
from app.routes.wallets_proxy import router as wallets_proxy_router

# NEW: Core API blueprint routers
from app.routes.sessions import router as sessions_router
from app.routes.blockchain import router as blockchain_router
from app.routes.policies import router as policies_router
from app.routes.payouts import router as payouts_router
from app.routes.nodes import router as nodes_router  
from app.routes.trust_policy import router as trust_policy_router
from app.routes.admin import router as admin_router
from app.routes.analytics import router as analytics_router

# Optional: Mongo health probe (kept non-fatal)
try:
    from app.db.connection import ping as mongo_ping  # type: ignore
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
        logger = logging.getLogger("app.request")
        path = request.url.path
        method = request.method
        start = datetime.now(tz=timezone.utc)
        response = None
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
    _configure_logging()
    settings: Settings = get_settings()

    app = FastAPI(
        title="Lucid API",
        version=settings.VERSION,
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

    # Proxied Cluster B endpoints (Blockchain Core)
    # These appear in the gateway OpenAPI as /chain/* and /wallets/*
    app.include_router(chain_proxy_router)
    app.include_router(wallets_proxy_router)
    
    # Core API blueprint endpoints
    app.include_router(sessions_router)
    app.include_router(blockchain_router)
    app.include_router(policies_router)
    app.include_router(payouts_router)
    app.include_router(nodes_router)
    app.include_router(trust_policy_router)
    app.include_router(admin_router)
    app.include_router(analytics_router)

    @app.get("/", include_in_schema=False)
    def _root():
        return {
            "service": settings.SERVICE_NAME,
            "status": "ok",
            "time": datetime.now(timezone.utc).isoformat(),
            "version": settings.VERSION,
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
            "service": settings.SERVICE_NAME,
            "started_at": app.state.start_time.isoformat(),
            "version": settings.VERSION,
            "dependencies": {"mongo": {"ok": mongo_ok, "error": mongo_error}},
        }

    return app


app = create_app()
