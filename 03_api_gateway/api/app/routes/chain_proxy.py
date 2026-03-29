# app/routes/chain_proxy.py
"""
File: /app/03_api_gateway/api/app/routes/chain_proxy.py
x-lucid-file-path: /app/03_api_gateway/api/app/routes/chain_proxy.py
x-lucid-file-type: python
"""

from __future__ import annotations

import os
import httpx
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse

# Base URL for the Blockchain Core service (Cluster B)
# Defaults to local dev port 8084; override via env if needed.
BLOCKCHAIN_CORE_URL = os.getenv(env="BLOCKCHAIN_CORE_URL")

router = APIRouter(prefix="/chain", tags=["chain"])


async def _passthrough_get(path: str) -> JSONResponse:
    url = f"{BLOCKCHAIN_CORE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"chain upstream error: {e}") from e


@router.get("/info", summary="Chain info (proxied)")
async def chain_info() -> JSONResponse:
    return await _passthrough_get("/chain/info")


@router.get("/height", summary="Latest block height (proxied)")
async def chain_height() -> JSONResponse:
    return await _passthrough_get("/chain/height")


@router.get(
    "/balance/{address_base58}",
    summary="Account balance in sun (proxied)",
)
async def chain_balance(
    address_base58: str = Path(..., description="TRON base58 address, e.g., T..."),
) -> JSONResponse:
    return await _passthrough_get(f"/chain/balance/{address_base58}")
