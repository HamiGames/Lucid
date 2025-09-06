from fastapi import APIRouter
from datetime import datetime, UTC

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "api-gateway",
        "time": datetime.now(UTC).isoformat(),
        "block_onion": "",
        "block_rpc_url": "",
    }
