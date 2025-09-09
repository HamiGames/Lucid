from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["meta"])

# Environment-driven knobs (match compose + project docs)
MONGO_URL = os.getenv("MONGO_URL")  # example: mongodb://lucid:lucid@lucid_mongo:27017/?authSource=admin
TOR_CONTROL_HOST = os.getenv("TOR_CONTROL_HOST", "lucid_tor")
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9051"))
TOR_CONNECT_TIMEOUT_S = float(os.getenv("TOR_CONNECT_TIMEOUT_S", "0.25"))
MONGO_PING_TIMEOUT_MS = int(os.getenv("MONGO_PING_TIMEOUT_MS", "200"))


async def _check_tor() -> Dict[str, Any]:
    """Fast, non-blocking connectivity probe to Tor ControlPort (9051)."""
    try:
        fut = asyncio.open_connection(TOR_CONTROL_HOST, TOR_CONTROL_PORT)
        reader, writer = await asyncio.wait_for(fut, timeout=TOR_CONNECT_TIMEOUT_S)
        try:
            # Minimal PROTOCOLINFO then quit to avoid leaving sockets open
            writer.write(b"PROTOCOLINFO\r\nQUIT\r\n")
            await writer.drain()
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
        return {"name": "tor", "available": True, "host": TOR_CONTROL_HOST, "port": TOR_CONTROL_PORT}
    except Exception as exc:  # noqa: BLE001 - health check must not raise
        return {
            "name": "tor",
            "available": False,
            "host": TOR_CONTROL_HOST,
            "port": TOR_CONTROL_PORT,
            "error": type(exc).__name__,
        }


def _check_mongo_sync() -> Dict[str, Any]:
    """
    Ping MongoDB if pymongo is available; otherwise report 'skipped' gracefully.
    This avoids hard-coupling tests to driver availability while remaining informative.
    """
    try:
        from pymongo import MongoClient  # type: ignore
    except Exception:
        return {"name": "mongodb", "available": None, "reason": "pymongo-not-installed"}

    if not MONGO_URL:
        return {"name": "mongodb", "available": None, "reason": "no-url"}

    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=MONGO_PING_TIMEOUT_MS)
        ok = bool(client.admin.command("ping").get("ok") == 1)
        return {"name": "mongodb", "available": ok}
    except Exception as exc:  # noqa: BLE001
        return {"name": "mongodb", "available": False, "error": type(exc).__name__}


@router.get("/health", summary="Liveness/readiness with dependency probes")
async def health(request: Request) -> JSONResponse:
    """
    Returns overall status plus dependency checks.
    - TOR check: TCP connect + PROTOCOLINFO against lucid_tor:9051 (fast).
    - Mongo check: admin.ping if pymongo is installed; otherwise marked 'skipped'.
    """
    # Uptime
    started: Optional[datetime] = getattr(request.app.state, "start_time", None)
    now = datetime.now(tz=timezone.utc)
    uptime_s = (now - started).total_seconds() if started else None

    # Run checks (tor async, mongo sync quickly)
    tor = await _check_tor()
    mongo = await asyncio.to_thread(_check_mongo_sync)

    # Determine overall status
    checks = [c for c in (tor, mongo) if c.get("available") is not None]
    any_fail = any(c.get("available") is False for c in checks)
    status = "ok" if not any_fail else "degraded"

    payload = {
        "status": status,
        "service": "lucid-api",
        "environment": os.getenv("LUCID_ENV", "dev"),
        "uptime_seconds": uptime_s,
        "dependencies": {"tor": tor, "mongodb": mongo},
    }
    return JSONResponse(payload)


# --- internals ---
import contextlib  # placed at bottom to keep top section focused on app bits
