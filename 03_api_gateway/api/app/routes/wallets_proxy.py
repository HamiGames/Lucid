# app/routes/wallets_proxy.py
from __future__ import annotations

import os
import httpx
from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from fastapi.responses import JSONResponse

BLOCKCHAIN_CORE_URL = os.getenv("BLOCKCHAIN_CORE_URL", "http://blockchain-core-distroless:8084")

router = APIRouter(prefix="/wallets", tags=["wallets"])


async def _passthrough_get(path: str, params: dict | None = None) -> JSONResponse:
    url = f"{BLOCKCHAIN_CORE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params or {})
        # Return JSON exactly, with upstream status
        return JSONResponse(status_code=r.status_code, content=r.json())
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502, detail=f"wallets upstream error: {e}"
        ) from e


async def _passthrough_post(path: str, json: dict | None = None) -> JSONResponse:
    url = f"{BLOCKCHAIN_CORE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=json or {})
        # Some routes return 201 etc.; preserve status code.
        # If upstream returns no json body, make it an empty dict.
        content = {}
        try:
            content = r.json()
        except Exception:
            content = {}
        return JSONResponse(status_code=r.status_code, content=content)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502, detail=f"wallets upstream error: {e}"
        ) from e


@router.get("", summary="List wallets (proxied)")
async def list_wallets(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> JSONResponse:
    return await _passthrough_get(
        "/wallets", params={"page": page, "page_size": page_size}
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create wallet (proxied)")
async def create_wallet(payload: dict) -> JSONResponse:
    # payload: { "label": "..." }
    return await _passthrough_post("/wallets", json=payload)


@router.get("/{wallet_id}", summary="Get wallet by id (proxied)")
async def get_wallet(
    wallet_id: str = Path(..., description="Wallet record id"),
) -> JSONResponse:
    return await _passthrough_get(f"/wallets/{wallet_id}")


@router.post("/{wallet_id}/transfer", summary="Transfer from wallet (proxied)")
async def transfer(
    wallet_id: str = Path(..., description="Wallet record id"),
    payload: dict = ...,
) -> JSONResponse:
    # payload: { "to_address": "T...", "amount_sun": 1000000 }
    return await _passthrough_post(f"/wallets/{wallet_id}/transfer", json=payload)
