from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/chain", tags=["chain"])


@router.get("/info")
def chain_info():
    """
    Get blockchain information for the On-System Data Chain.
    Returns basic chain information for the primary blockchain.
    """
    return {
        "network": "lucid_blocks",
        "chain_type": "on_system_data_chain",
        "height": 0,
        "status": "operational"
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
