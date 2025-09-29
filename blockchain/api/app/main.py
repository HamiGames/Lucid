from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings, Settings
from app.routes.chain import router as chain_router
from app.routes.wallets import router as wallets_router


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _request_logger(app: FastAPI) -> None:
    @app.middleware("http")
    async def _log_requests(request: Request, call_next: Callable):
        logger = logging.getLogger("app.request")
        start = datetime.now(tz=timezone.utc)
        resp = None
        try:
            resp = await call_next(request)
            return resp
        finally:
            dur = (datetime.now(tz=timezone.utc) - start).total_seconds() * 1000.0
            logger.info(
                "%s %s -> %s (%.2fms)",
                request.method,
                request.url.path,
                getattr(resp, "status_code", "?"),
                dur,
            )


def create_app() -> FastAPI:
    settings: Settings = get_settings()
    _configure_logging(settings.LOG_LEVEL)

    app = FastAPI(title="Lucid Blockchain Core", version=settings.VERSION)

    # CORS open for dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    _request_logger(app)

    # Routes
    app.include_router(chain_router)
    app.include_router(wallets_router)

    @app.get("/", tags=["meta"])
    def root():
        return {
            "service": settings.SERVICE_NAME,
            "status": "ok",
            "time": datetime.now(timezone.utc).isoformat(),
            "version": settings.VERSION,
            "endpoints": {
                "health": "/health",
                "chain_info": "/chain/info",
                "wallets": "/wallets",
            },
        }

    @app.get("/health", tags=["meta"])
    def health():
        from app.services.tron_client import TronService

        info = TronService().get_chain_info()
        return {
            "status": "ok",
            "service": settings.SERVICE_NAME,
            "time": datetime.now(timezone.utc).isoformat(),
            "block_onion": settings.BLOCK_ONION or "",
            "block_rpc_url": settings.BLOCK_RPC_URL or info.node,
            "network": info.network,
            "height": info.latest_block,
        }

    return app


app = create_app()
