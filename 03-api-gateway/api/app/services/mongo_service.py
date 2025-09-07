# Path: 03-api-gateway/api/app/services/mongo_service.py
# Async Mongo helpers using Motor (FastAPI + Motor is a common, recommended combo). :contentReference[oaicite:2]{index=2}
from typing import Tuple
from ..db.connection import get_client


async def ping() -> Tuple[bool, float]:
    """
    Returns (ok, latency_ms) using MongoDB 'ping' command.
    """
    client = get_client()
    import time

    start = time.perf_counter()
    try:
        await client.admin.command("ping")
        elapsed = (time.perf_counter() - start) * 1000.0
        return True, round(elapsed, 2)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000.0
        return False, round(elapsed, 2)
