"""
LUCID Payment Systems - TRON Network API
TRON network connectivity and blockchain operations
Distroless container: lucid-tron-payment-service:latest
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import httpx

from ..services.tron_client import TronClientService, NetworkInfo, AccountInfo, TransactionInfo
from ..models.wallet import WalletResponse, WalletCreateRequest
from ..models.transaction import TransactionResponse, TransactionCreateRequest
from ..models.payout import PayoutResponse, PayoutCreateRequest

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/tron", tags=["TRON Network"])

# Initialize TRON client service
tron_client = TronClientService()

class NetworkStatusResponse(BaseModel):
    """Network status response"""
    network_name: str
    network_id: str
    chain_id: str
    latest_block: int
    block_timestamp: int
    node_url: str
    status: str
    last_updated: str
    sync_progress: float
    node_count: int
    total_supply: int
    total_transactions: int

class AccountBalanceResponse(BaseModel):
    """Account balance response"""
    address: str
    balance_trx: float
    balance_sun: int
    energy_available: int
    bandwidth_available: int
    frozen_balance: float
    delegated_energy: int
    delegated_bandwidth: int
    last_updated: str
    transaction_count: int

class TransactionStatusResponse(BaseModel):
    """Transaction status response"""
    txid: str
    block_number: int
    timestamp: int
    from_address: str
    to_address: str
    amount: int
    token_type: str
    fee: int
    energy_used: int
    bandwidth_used: int
    status: str
    confirmed: bool

@router.get("/network/status", response_model=NetworkStatusResponse)
async def get_network_status():
    """Get TRON network status and information"""
    try:
        network_info = await tron_client.get_network_info()
        
        return NetworkStatusResponse(
            network_name=network_info.network_name,
            network_id=network_info.network_id,
            chain_id=network_info.chain_id,
            latest_block=network_info.latest_block,
            block_timestamp=network_info.block_timestamp,
            node_url=network_info.node_url,
            status=network_info.status.value,
            last_updated=network_info.last_updated.isoformat(),
            sync_progress=network_info.sync_progress,
            node_count=network_info.node_count,
            total_supply=network_info.total_supply,
            total_transactions=network_info.total_transactions
        )
    except Exception as e:
        logger.error(f"Error getting network status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get network status: {str(e)}")

@router.get("/network/health")
async def get_network_health():
    """Get network health status"""
    try:
        network_info = await tron_client.get_network_info()
        
        health_status = {
            "status": "healthy" if network_info.status.value == "connected" else "unhealthy",
            "network": network_info.network_name,
            "latest_block": network_info.latest_block,
            "sync_progress": network_info.sync_progress,
            "node_count": network_info.node_count,
            "last_updated": network_info.last_updated.isoformat(),
            "timestamp": datetime.now().isoformat()
        }
        
        return health_status
    except Exception as e:
        logger.error(f"Error getting network health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/account/{address}/balance", response_model=AccountBalanceResponse)
async def get_account_balance(address: str):
    """Get account balance and resources"""
    try:
        # Validate address format
        if not address.startswith('T') or len(address) != 34:
            raise HTTPException(status_code=400, detail="Invalid TRON address format")
        
        account_info = await tron_client.get_account_info(address)
        
        return AccountBalanceResponse(
            address=account_info.address,
            balance_trx=account_info.balance_trx,
            balance_sun=account_info.balance_sun,
            energy_available=account_info.energy_available,
            bandwidth_available=account_info.bandwidth_available,
            frozen_balance=account_info.frozen_balance,
            delegated_energy=account_info.delegated_energy,
            delegated_bandwidth=account_info.delegated_bandwidth,
            last_updated=account_info.last_updated.isoformat(),
            transaction_count=account_info.transaction_count
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account balance for {address}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account balance: {str(e)}")

@router.get("/account/{address}/balance/trx")
async def get_trx_balance(address: str):
    """Get TRX balance for address"""
    try:
        # Validate address format
        if not address.startswith('T') or len(address) != 34:
            raise HTTPException(status_code=400, detail="Invalid TRON address format")
        
        balance = await tron_client.get_balance(address)
        
        return {
            "address": address,
            "balance_trx": balance,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting TRX balance for {address}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get TRX balance: {str(e)}")

@router.get("/transaction/{txid}", response_model=TransactionStatusResponse)
async def get_transaction_status(txid: str):
    """Get transaction status and details"""
    try:
        # Validate transaction ID format
        if not txid or len(txid) != 64:
            raise HTTPException(status_code=400, detail="Invalid transaction ID format")
        
        transaction_info = await tron_client.get_transaction(txid)
        
        if not transaction_info:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return TransactionStatusResponse(
            txid=transaction_info.txid,
            block_number=transaction_info.block_number,
            timestamp=transaction_info.timestamp,
            from_address=transaction_info.from_address,
            to_address=transaction_info.to_address,
            amount=transaction_info.amount,
            token_type=transaction_info.token_type,
            fee=transaction_info.fee,
            energy_used=transaction_info.energy_used,
            bandwidth_used=transaction_info.bandwidth_used,
            status=transaction_info.status,
            confirmed=transaction_info.status == "SUCCESS"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transaction {txid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get transaction: {str(e)}")

@router.post("/transaction/broadcast")
async def broadcast_transaction(transaction_data: TransactionCreateRequest):
    """Broadcast transaction to TRON network"""
    try:
        # Validate transaction data
        if not transaction_data.from_address or not transaction_data.to_address:
            raise HTTPException(status_code=400, detail="Missing required transaction fields")
        
        if transaction_data.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid transaction amount")
        
        # Convert to dict for tron_client
        tx_data = {
            "from_address": transaction_data.from_address,
            "to_address": transaction_data.to_address,
            "amount": transaction_data.amount,
            "token_type": transaction_data.token_type or "TRX",
            "fee": transaction_data.fee or 0,
            "private_key": transaction_data.private_key
        }
        
        txid = await tron_client.broadcast_transaction(tx_data)
        
        return {
            "txid": txid,
            "status": "broadcasted",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error broadcasting transaction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to broadcast transaction: {str(e)}")

@router.post("/transaction/{txid}/wait")
async def wait_for_transaction_confirmation(txid: str, timeout_seconds: Optional[int] = None):
    """Wait for transaction confirmation"""
    try:
        # Get timeout from environment variable or use default
        if timeout_seconds is None:
            timeout_seconds = int(os.getenv("TRON_TRANSACTION_CONFIRMATION_TIMEOUT", os.getenv("TRON_TIMEOUT", "300")))
        
        # Validate transaction ID format
        if not txid or len(txid) != 64:
            raise HTTPException(status_code=400, detail="Invalid transaction ID format")
        
        # Validate timeout - get max timeout from environment
        max_timeout = int(os.getenv("TRON_MAX_CONFIRMATION_TIMEOUT", "3600"))
        if timeout_seconds <= 0 or timeout_seconds > max_timeout:
            raise HTTPException(status_code=400, detail=f"Invalid timeout value (1-{max_timeout} seconds)")
        
        confirmed = await tron_client.wait_for_confirmation(txid, timeout_seconds)
        
        return {
            "txid": txid,
            "confirmed": confirmed,
            "timeout_seconds": timeout_seconds,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error waiting for transaction confirmation {txid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to wait for confirmation: {str(e)}")

@router.get("/network/stats")
async def get_network_statistics():
    """Get network statistics and metrics"""
    try:
        stats = await tron_client.get_service_stats()
        
        return {
            "service_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting network statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get network statistics: {str(e)}")

@router.get("/network/peers")
async def get_network_peers():
    """Get connected network peers"""
    try:
        network_info = await tron_client.get_network_info()
        
        return {
            "node_count": network_info.node_count,
            "network": network_info.network_name,
            "status": network_info.status.value,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting network peers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get network peers: {str(e)}")

@router.get("/network/block/{block_number}")
async def get_block_info(block_number: int):
    """Get block information"""
    try:
        if block_number < 0:
            raise HTTPException(status_code=400, detail="Invalid block number")
        
        # Get block information from network info
        # Note: Full block details would require extending tron_client service
        return {
            "block_number": block_number,
            "status": "not_implemented",
            "message": "Block query functionality not yet implemented",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting block {block_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get block info: {str(e)}")

@router.get("/network/latest-block")
async def get_latest_block():
    """Get latest block information"""
    try:
        network_info = await tron_client.get_network_info()
        
        return {
            "block_number": network_info.latest_block,
            "block_timestamp": network_info.block_timestamp,
            "network": network_info.network_name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting latest block: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get latest block: {str(e)}")
