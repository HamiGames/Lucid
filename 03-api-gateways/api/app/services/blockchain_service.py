# Path: 03-api-gateway/api/app/services/blockchain_service.py
# Minimal stub to interact with a blockchain node (HTTP/RPC URL from env).
# Extend later with actual RPC calls (e.g., JSON-RPC).
import os
import httpx
from ..utils.logger import get_logger

log = get_logger(__name__)
BLOCK_RPC_URL = os.getenv("BLOCK_RPC_URL", "").strip()


async def node_health(timeout_s: float = 2.0) -> dict:
    if not BLOCK_RPC_URL:
        return {"status": "disabled", "reason": "BLOCK_RPC_URL not set"}
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            # HEAD or simple GET as a liveness probe
            resp = await client.get(BLOCK_RPC_URL)
            return {"status": "ok", "code": resp.status_code}
    except Exception as e:
        log.warning("blockchain_node_unreachable", extra={"error": str(e)})
        return {"status": "degraded", "error": str(e)}
