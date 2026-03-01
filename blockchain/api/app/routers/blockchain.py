"""
Blockchain Router

This module contains the blockchain information and status endpoints.
Implements the OpenAPI 3.0 specification for blockchain queries.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

from ..schemas.blockchain import BlockchainInfo, BlockchainStatus, BlockHeight, NetworkInfo
from ..dependencies import get_current_user, verify_api_key, require_read_permission
from ..services.blockchain_service import BlockchainService
from ..errors import BlockchainException

router = APIRouter(
    prefix="/chain",
    tags=["Blockchain"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

@router.get("/info", response_model=BlockchainInfo)
async def get_blockchain_info(
    user = Depends(require_read_permission)
):
    """
    Get comprehensive information about the lucid_blocks blockchain network.
    
    Returns detailed information about the blockchain including:
    - Network name and version
    - Consensus algorithm (PoOT)
    - Current block height and statistics
    - Network hash rate and difficulty
    - Validator information
    - Supply information
    """
    try:
        logger.info("Fetching blockchain info")
        info = await BlockchainService.get_info()
        return BlockchainInfo(**info)
    except Exception as e:
        logger.error(f"Failed to fetch blockchain info: {e}")
        raise BlockchainException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch blockchain information",
            error_code="BLOCKCHAIN_001",
            additional_info={"error": str(e)}
        )

@router.get("/status", response_model=BlockchainStatus)
async def get_blockchain_status(
    user = Depends(require_read_permission)
):
    """
    Get the current status and health of the lucid_blocks blockchain.
    
    Returns real-time status information including:
    - Sync status and peer count
    - Block production rate
    - Transaction throughput
    - System resource usage
    - Network latency
    - Consensus health
    """
    try:
        logger.info("Fetching blockchain status")
        status_data = await BlockchainService.get_status()
        return BlockchainStatus(**status_data)
    except Exception as e:
        logger.error(f"Failed to fetch blockchain status: {e}")
        raise BlockchainException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch blockchain status",
            error_code="BLOCKCHAIN_002",
            additional_info={"error": str(e)}
        )

@router.get("/height", response_model=BlockHeight)
async def get_current_block_height(
    user = Depends(require_read_permission)
):
    """
    Get the current height of the lucid_blocks blockchain.
    
    Returns the current block height with additional information:
    - Block height number
    - Block hash
    - Timestamp
    - Transaction count
    - Block size
    - Validator information
    """
    try:
        logger.info("Fetching current block height")
        height_data = await BlockchainService.get_current_height()
        return BlockHeight(**height_data)
    except Exception as e:
        logger.error(f"Failed to fetch current block height: {e}")
        raise BlockchainException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch current block height",
            error_code="BLOCKCHAIN_003",
            additional_info={"error": str(e)}
        )

@router.get("/network", response_model=NetworkInfo)
async def get_network_topology(
    user = Depends(require_read_permission)
):
    """
    Get information about the lucid_blocks network topology and peers.
    
    Returns network information including:
    - Total and active peer count
    - Peer list with status and latency
    - Network topology type
    - Average latency and bandwidth usage
    - Protocol version
    """
    try:
        logger.info("Fetching network topology")
        network_data = await BlockchainService.get_network_info()
        return NetworkInfo(**network_data)
    except Exception as e:
        logger.error(f"Failed to fetch network topology: {e}")
        raise BlockchainException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch network topology",
            error_code="BLOCKCHAIN_004",
            additional_info={"error": str(e)}
        )