"""
LUCID TRON Relay - Cache API Endpoints
Cached TRON blockchain data endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from config import config
from services.relay_service import relay_service
from services.cache_manager import cache_manager

router = APIRouter()


class BlockResponse(BaseModel):
    """Block response"""
    block_number: int
    block_hash: Optional[str]
    timestamp: Optional[int]
    transactions_count: int
    cached: bool
    data: Dict[str, Any]


class TransactionResponse(BaseModel):
    """Transaction response"""
    txid: str
    block_number: Optional[int]
    timestamp: Optional[int]
    cached: bool
    data: Dict[str, Any]


class AccountResponse(BaseModel):
    """Account response"""
    address: str
    balance_trx: float
    balance_sun: int
    cached: bool
    data: Dict[str, Any]


class BalanceResponse(BaseModel):
    """Balance response"""
    address: str
    balance_trx: float
    balance_sun: int
    trc20_balances: Dict[str, int]
    bandwidth: int
    energy: int
    cached: bool


# ==========================================================================
# BLOCK ENDPOINTS
# ==========================================================================

@router.get("/block/latest")
async def get_latest_block():
    """Get the latest block (always fresh, not cached)"""
    block = await relay_service.get_latest_block()
    
    if not block:
        raise HTTPException(status_code=503, detail="Could not fetch latest block")
    
    # Update last sync time
    from main import service_state
    from datetime import datetime
    service_state["last_tron_sync"] = datetime.utcnow().isoformat()
    
    block_header = block.get("block_header", {}).get("raw_data", {})
    
    return {
        "block_number": block_header.get("number", 0),
        "block_hash": block.get("blockID"),
        "timestamp": block_header.get("timestamp"),
        "transactions_count": len(block.get("transactions", [])),
        "cached": False,
        "data": block
    }


@router.get("/block/{block_number}", response_model=BlockResponse)
async def get_block_by_number(block_number: int):
    """Get block by number (cached)"""
    # Check cache first
    cached = await cache_manager.get_block(str(block_number))
    
    if cached:
        from main import service_state
        service_state["cache_stats"]["hits"] += 1
        
        block_header = cached.get("block_header", {}).get("raw_data", {})
        return BlockResponse(
            block_number=block_number,
            block_hash=cached.get("blockID"),
            timestamp=block_header.get("timestamp"),
            transactions_count=len(cached.get("transactions", [])),
            cached=True,
            data=cached
        )
    
    # Fetch from network
    from main import service_state
    service_state["cache_stats"]["misses"] += 1
    
    block = await relay_service.get_block_by_number(block_number)
    
    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_number} not found")
    
    # Cache the result
    await cache_manager.set_block(str(block_number), block)
    
    block_header = block.get("block_header", {}).get("raw_data", {})
    
    return BlockResponse(
        block_number=block_number,
        block_hash=block.get("blockID"),
        timestamp=block_header.get("timestamp"),
        transactions_count=len(block.get("transactions", [])),
        cached=False,
        data=block
    )


# ==========================================================================
# TRANSACTION ENDPOINTS
# ==========================================================================

@router.get("/transaction/{txid}", response_model=TransactionResponse)
async def get_transaction(txid: str):
    """Get transaction by ID (cached)"""
    # Check cache first
    cached = await cache_manager.get_transaction(txid)
    
    if cached:
        from main import service_state
        service_state["cache_stats"]["hits"] += 1
        
        return TransactionResponse(
            txid=txid,
            block_number=cached.get("blockNumber"),
            timestamp=cached.get("blockTimeStamp"),
            cached=True,
            data=cached
        )
    
    # Fetch from network
    from main import service_state
    service_state["cache_stats"]["misses"] += 1
    
    tx = await relay_service.get_transaction_by_id(txid)
    
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")
    
    # Also get transaction info
    tx_info = await relay_service.get_transaction_info(txid)
    
    # Merge data
    tx_data = {**tx, **(tx_info or {})}
    
    # Cache the result
    await cache_manager.set_transaction(txid, tx_data)
    
    return TransactionResponse(
        txid=txid,
        block_number=tx_data.get("blockNumber"),
        timestamp=tx_data.get("blockTimeStamp"),
        cached=False,
        data=tx_data
    )


@router.get("/transaction/{txid}/info")
async def get_transaction_info(txid: str):
    """Get transaction info/receipt (cached)"""
    # Check cache first
    cached = await cache_manager.get_transaction_info(txid)
    
    if cached:
        from main import service_state
        service_state["cache_stats"]["hits"] += 1
        return {"txid": txid, "cached": True, "data": cached}
    
    # Fetch from network
    from main import service_state
    service_state["cache_stats"]["misses"] += 1
    
    tx_info = await relay_service.get_transaction_info(txid)
    
    if not tx_info:
        raise HTTPException(status_code=404, detail=f"Transaction info for {txid} not found")
    
    # Cache the result
    await cache_manager.set_transaction_info(txid, tx_info)
    
    return {"txid": txid, "cached": False, "data": tx_info}


@router.get("/transaction/{txid}/confirmations")
async def get_transaction_confirmations(txid: str):
    """Get confirmation count for a transaction"""
    confirmations = await relay_service.get_transaction_confirmations(txid)
    
    return {
        "txid": txid,
        "confirmations": confirmations,
        "confirmed": confirmations >= config.confirmation_threshold,
        "threshold": config.confirmation_threshold
    }


# ==========================================================================
# ACCOUNT ENDPOINTS
# ==========================================================================

@router.get("/account/{address}", response_model=AccountResponse)
async def get_account(address: str):
    """Get account information (cached)"""
    # Validate address format
    if not address.startswith("T") or len(address) != 34:
        raise HTTPException(status_code=400, detail="Invalid TRON address format")
    
    # Check cache first
    cached = await cache_manager.get_account(address)
    
    if cached:
        from main import service_state
        service_state["cache_stats"]["hits"] += 1
        
        return AccountResponse(
            address=address,
            balance_trx=cached.get("balance", 0) / 1_000_000,
            balance_sun=cached.get("balance", 0),
            cached=True,
            data=cached
        )
    
    # Fetch from network
    from main import service_state
    service_state["cache_stats"]["misses"] += 1
    
    account = await relay_service.get_account(address)
    
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {address} not found")
    
    # Cache the result
    await cache_manager.set_account(address, account)
    
    return AccountResponse(
        address=address,
        balance_trx=account.get("balance", 0) / 1_000_000,
        balance_sun=account.get("balance", 0),
        cached=False,
        data=account
    )


@router.get("/balance/{address}", response_model=BalanceResponse)
async def get_balance(address: str):
    """Get account balance (cached)"""
    # Validate address format
    if not address.startswith("T") or len(address) != 34:
        raise HTTPException(status_code=400, detail="Invalid TRON address format")
    
    # Check cache first
    cached = await cache_manager.get_balance(address)
    
    if cached:
        from main import service_state
        service_state["cache_stats"]["hits"] += 1
        
        return BalanceResponse(
            address=address,
            balance_trx=cached.get("balance_trx", 0),
            balance_sun=cached.get("balance_sun", 0),
            trc20_balances=cached.get("trc20_balances", {}),
            bandwidth=cached.get("bandwidth", 0),
            energy=cached.get("energy", 0),
            cached=True
        )
    
    # Fetch from network
    from main import service_state
    service_state["cache_stats"]["misses"] += 1
    
    balance = await relay_service.get_account_balance(address)
    
    if not balance:
        raise HTTPException(status_code=404, detail=f"Balance for {address} not found")
    
    # Cache the result
    await cache_manager.set_balance(address, balance)
    
    return BalanceResponse(
        address=address,
        balance_trx=balance.get("balance_trx", 0),
        balance_sun=balance.get("balance_sun", 0),
        trc20_balances=balance.get("trc20_balances", {}),
        bandwidth=balance.get("bandwidth", 0),
        energy=balance.get("energy", 0),
        cached=False
    )


@router.get("/resources/{address}")
async def get_account_resources(address: str):
    """Get account resources (bandwidth, energy)"""
    # Validate address format
    if not address.startswith("T") or len(address) != 34:
        raise HTTPException(status_code=400, detail="Invalid TRON address format")
    
    resources = await relay_service.get_account_resource(address)
    
    if not resources:
        raise HTTPException(status_code=404, detail=f"Resources for {address} not found")
    
    return {
        "address": address,
        "resources": resources
    }


# ==========================================================================
# TRC20 ENDPOINTS
# ==========================================================================

@router.get("/trc20/balance/{address}")
async def get_trc20_balance(
    address: str,
    contract: str = Query(..., description="TRC20 contract address")
):
    """Get TRC20 token balance for an address"""
    # Validate addresses
    if not address.startswith("T") or len(address) != 34:
        raise HTTPException(status_code=400, detail="Invalid TRON address format")
    
    if not contract.startswith("T") or len(contract) != 34:
        raise HTTPException(status_code=400, detail="Invalid contract address format")
    
    balance = await relay_service.get_trc20_balance(address, contract)
    
    if balance is None:
        raise HTTPException(status_code=404, detail="Could not fetch TRC20 balance")
    
    return {
        "address": address,
        "contract": contract,
        "balance": balance,
        "balance_formatted": balance / 1_000_000  # Assuming 6 decimals (USDT)
    }


# ==========================================================================
# NETWORK INFO ENDPOINTS
# ==========================================================================

@router.get("/chain/parameters")
async def get_chain_parameters():
    """Get blockchain parameters"""
    params = await relay_service.get_chain_parameters()
    
    if not params:
        raise HTTPException(status_code=503, detail="Could not fetch chain parameters")
    
    return params


@router.get("/node/info")
async def get_node_info():
    """Get connected node information"""
    info = await relay_service.get_node_info()
    
    if not info:
        raise HTTPException(status_code=503, detail="Could not fetch node info")
    
    return info


# ==========================================================================
# CACHE MANAGEMENT
# ==========================================================================

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    return cache_manager.get_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear all caches"""
    await cache_manager.clear_all()
    return {"success": True, "message": "All caches cleared"}


@router.post("/cache/cleanup")
async def cleanup_cache():
    """Clean up expired cache entries"""
    cleaned = await cache_manager.cleanup_expired()
    return {"success": True, "cleaned_entries": cleaned}

