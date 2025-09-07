# Path: 03-api-gateway/api/app/routes/db_health.py
from fastapi import APIRouter
from ..db.connection import ping
from ..utils.logger import get_logger

router = APIRouter(prefix="/db", tags=["db"])
log = get_logger(__name__)


@router.get("/health")
async def db_health():
    ok, latency_ms = await ping()
    status = "ok" if ok else "degraded"
    log.info("db_health", extra={"ok": ok, "latency_ms": latency_ms})
    return {"status": status, "latency_ms": latency_ms}
