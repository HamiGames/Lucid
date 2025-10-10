"""
Meta routes for Lucid API
Service metadata and dependency checking endpoints
"""

from __future__ import annotations

from fastapi import APIRouter
from datetime import datetime, timezone

# Optional: check Mongo dependency if available
try:
    from src.api.db.connection import ping as mongo_ping
except Exception:  # keep route resilient even if DB layer imports fail
    mongo_ping = None  # type: ignore[assignment]

router = APIRouter(prefix="/meta", tags=["meta"])
_started = datetime.now(timezone.utc)


@router.get("/ping", summary="Liveness & dependency check")
def ping() -> dict:
    db_ok = None
    db_error = None
    if mongo_ping:
        try:
            mongo_ping()
            db_ok = True
        except Exception as e:  # surface as string, no stack
            db_ok = False
            db_error = str(e)

    return {
        "ok": True,
        "service": "lucid-api",
        "started_at": _started.isoformat(),
        "dependencies": {"mongo": {"ok": db_ok, "error": db_error}},
    }
