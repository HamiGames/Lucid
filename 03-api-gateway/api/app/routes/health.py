# 03-api-gateway/api/app/routes/health.py
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

from app.db.connection import ping as mongo_ping
from app.utils.config import (
    mongo_conn_str,
    service_name,
    service_version,
    mongo_timeouts_ms,
)

router = APIRouter()
_START_MONO = time.monotonic()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/health")
def health() -> Dict[str, Any]:
    """
    Lightweight health endpoint.
    Reports overall status and Mongo connectivity.
    """
    sst, _ = mongo_timeouts_ms()

    # Attempt a Mongo ping; report 'up'/'down' and fold into overall status.
    db_ok = mongo_ping(timeout_ms=sst)
    db_status = "up" if db_ok else "down"

    status = "ok" if db_ok else "degraded"

    payload: Dict[str, Any] = {
        "service": service_name(),
        "status": status,
        "db": db_status,
        "time": _now_iso(),
        "version": service_version(),
        "uptime_ms": int((time.monotonic() - _START_MONO) * 1000),
        # Useful introspection: which URI the app resolved (redact credentials)
        "mongo": {
            "uri_host": _redact_host_only(mongo_conn_str()),
            "timeout_ms": sst,
        },
    }
    return payload


def _redact_host_only(uri: str) -> str:
    """
    Return only the 'host:port' portion for observability without leaking secrets.
    """
    # naive but robust parsing for typical mongodb:// form
    # mongodb://user:pass@host:port/db?params
    try:
        at = uri.split("@", 1)
        tail = at[1] if len(at) == 2 else at[0]  # after '@' or the whole if no creds
        host_port = tail.split("/", 1)[0]  # cut at first '/' (before db)
        return host_port
    except Exception:
        return "unknown"
