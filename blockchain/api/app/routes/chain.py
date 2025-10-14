from __future__ import annotations

from fastapi import APIRouter

# from app.services.tron_client import TronService

router = APIRouter(prefix="/chain", tags=["chain"])


@router.get("/info")
def chain_info():
    # svc = TronService()
    # info = svc.get_chain_info()
    return {
        # "network": info.network,
        # "node": info.node,
        # "height": info.latest_block,
        # "block_id": info.block_id,
        # "block_time": info.block_time,
        # "block_onion": info.block_onion,
        # "block_rpc_url": info.block_rpc_url,
    }


@router.get("/height")
def chain_height():
    return {"height": 0}


@router.get("/balance/{address_base58}")
def balance(address_base58: str):
    return {
        "address": address_base58,
        "balance_sun": 0,
    }
