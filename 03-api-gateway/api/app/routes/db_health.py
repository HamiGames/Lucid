# Path: 03-api-gateway/api/app/routes/db_health.py

from __future__ import annotations

from fastapi import APIRouter
from app.services.mongo_service import ping as mongo_ping

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/db", summary="Database health")
async def db_health() -> dict:
    """
    Separate DB health endpoint. Avoids 'await' on non-awaitable and returns a simple shape.
    """
    ok = await mongo_ping()  # <-- mongo_ping() is async and returns bool
    return {"db": "up" if ok else "down", "ok": ok}
