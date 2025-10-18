"""
Blocks Router

This module contains the block management and validation endpoints.
Implements the OpenAPI 3.0 specification for block operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging

from ..schemas.block import (
    BlockDetails, BlockListResponse, BlockValidationRequest, 
    BlockValidationResponse, BlockSummary
)
from ..dependencies import get_current_user, verify_api_key, require_read_permission, require_write_permission
from ..services.block_service import BlockService
from ..errors import BlockNotFoundException, BlockValidationException

router = APIRouter(
    prefix="/blocks",
    tags=["Blocks"],
    responses={404: {"description": "Block not found"}},
)

logger = logging.getLogger(__name__)

@router.get("/", response_model=BlockListResponse)
async def list_blocks(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Number of blocks per page"),
    height_from: Optional[int] = Query(None, ge=0, description="Minimum block height"),
    height_to: Optional[int] = Query(None, ge=0, description="Maximum block height"),
    sort: str = Query("height_desc", regex="^(height|timestamp)_(asc|desc)$", description="Sort order"),
    user = Depends(require_read_permission)
):
    """
    Returns a paginated list of blocks from the lucid_blocks blockchain.
    
    Supports filtering by height range and sorting by height or timestamp.
    Returns block summaries with pagination information.
    """
    try:
        logger.info(f"Listing blocks with page={page}, limit={limit}, height_from={height_from}, height_to={height_to}, sort={sort}")
        blocks_response = await BlockService.list_blocks(page, limit, height_from, height_to, sort)
        return BlockListResponse(**blocks_response)
    except Exception as e:
        logger.error(f"Failed to list blocks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve blocks"
        )

@router.get("/{block_id}", response_model=BlockDetails)
async def get_block_by_id(
    block_id: str,
    user = Depends(require_read_permission)
):
    """
    Returns detailed information about a specific block by its ID or hash.
    
    Provides comprehensive block information including:
    - Block metadata (ID, height, hash, timestamp)
    - Transaction details and count
    - Block size and validation information
    - Validator and signature information
    """
    try:
        logger.info(f"Fetching block by ID: {block_id}")
        block = await BlockService.get_block_by_id(block_id)
        if not block:
            raise BlockNotFoundException(block_id)
        return BlockDetails(**block)
    except BlockNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch block by ID {block_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve block"
        )

@router.get("/height/{height}", response_model=BlockDetails)
async def get_block_by_height(
    height: int,
    user = Depends(require_read_permission)
):
    """
    Returns the block at the specified height.
    
    Retrieves the block at the exact height specified.
    Returns detailed block information including all transactions.
    """
    try:
        logger.info(f"Fetching block by height: {height}")
        block = await BlockService.get_block_by_height(height)
        if not block:
            raise BlockNotFoundException(f"block_height_{height}")
        return BlockDetails(**block)
    except BlockNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch block by height {height}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve block"
        )

@router.get("/latest", response_model=BlockDetails)
async def get_latest_block(
    user = Depends(require_read_permission)
):
    """
    Returns the most recently created block.
    
    Provides the latest block in the blockchain with full details.
    Useful for monitoring blockchain progress and recent activity.
    """
    try:
        logger.info("Fetching latest block")
        latest_block = await BlockService.get_latest_block()
        return BlockDetails(**latest_block)
    except Exception as e:
        logger.error(f"Failed to fetch latest block: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latest block"
        )

@router.post("/validate", response_model=BlockValidationResponse)
async def validate_block_structure(
    block_data: BlockValidationRequest,
    user = Depends(require_write_permission)
):
    """
    Validates the structure and integrity of a block.
    
    Performs comprehensive validation including:
    - Block structure validation
    - Signature verification
    - Merkle root validation
    - Timestamp validation
    - Transaction validation
    
    Returns detailed validation results and any errors found.
    """
    try:
        logger.info("Validating block structure")
        validation_response = await BlockService.validate_block(block_data.block_data)
        return BlockValidationResponse(**validation_response)
    except Exception as e:
        logger.error(f"Failed to validate block structure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate block structure"
        )