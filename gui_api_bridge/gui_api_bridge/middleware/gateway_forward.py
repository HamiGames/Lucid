"""
Forward API traffic to api-gateway with client headers preserved (no local JWT validation).
Anonymous login and Bearer flows both pass through to B1.
"""

from __future__ import annotations

import logging
from typing import Callable

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..config import GuiAPIBridgeSettings

logger = logging.getLogger(__name__)

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class GatewayForwardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: GuiAPIBridgeSettings):
        super().__init__(app)
        self._settings = settings

    def _local_path(self, path: str) -> bool:
        if path in ("/health", "/",):
            return True
        if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
            return True
        if path.startswith("/ws"):
            return True
        return False

    async def dispatch(self, request: Request, call_next: Callable):
        if self._local_path(request.url.path) or not (self._settings.API_GATEWAY_URL or "").strip():
            return await call_next(request)

        base = self._settings.API_GATEWAY_URL.rstrip("/")
        url = base + request.url.path
        q = request.url.query
        if q:
            url = f"{url}?{q}"

        body = await request.body()
        fwd = {}
        for k, v in request.headers.items():
            kl = k.lower()
            if kl in ("host",) or kl in HOP_BY_HOP:
                continue
            fwd[k] = v
        if not any(k.lower() == "x-lucid-calling-service" for k in fwd):
            fwd["X-Lucid-Calling-Service"] = self._settings.SERVICE_NAME

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
                upstream = await client.request(
                    request.method,
                    url,
                    content=body or None,
                    headers=fwd,
                )
        except httpx.RequestError as e:
            logger.warning("gateway forward transport error: %s", e)
            return Response(
                content=b'{"detail":"upstream api-gateway unreachable"}',
                status_code=502,
                media_type="application/json",
            )

        out_h = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP}
        return Response(content=upstream.content, status_code=upstream.status_code, headers=out_h)
