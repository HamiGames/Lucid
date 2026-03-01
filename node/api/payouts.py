# Path: node/api/payouts.py
# Lucid Node Management API - Payout Endpoints
# Based on LUCID-STRICT requirements per Spec-1c

"""
Payout management API endpoints for Lucid system.

This module provides REST API endpoints for:
- Node payout history and tracking
- Batch payout processing
- Payout status monitoring
- TRON payment integration
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import logging
import uuid

from ..models.payout import (
    Payout, PayoutRequest, BatchPayoutRequest, 
    PayoutStatus, PayoutPriority, Currency
)
from ..repositories.node_repository import NodeRepository

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Dependency for node repository
def get_node_repository() -> NodeRepository:
    """Get node repository instance"""
    return NodeRepository()

@router.get("/{node_id}/payouts", response_model=Dict[str, Any])
async def get_node_payouts(
    node_id: str = Path(..., description="Node ID", pattern="^node_[a-zA-Z0-9_-]+$"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[PayoutStatus] = Query(None, description="Filter by payout status"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get payout history for a specific node.
    
    Returns a paginated list of payouts with optional filtering by:
    - Payout status (pending, processing, completed, failed, cancelled)
    - Date range
    - Currency type
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Build filter criteria
        filters = {}
        if status:
            filters["status"] = status.value
        
        # Get payouts
        payouts, total_count = await repository.get_node_payouts(
            node_id=node_id,
            page=page,
            limit=limit,
            filters=filters
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "node_id": node_id,
            "payouts": [payout.dict() for payout in payouts],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get payouts for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve node payouts"
        )

@router.post("/payouts/batch", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def process_batch_payouts(
    batch_request: BatchPayoutRequest,
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Process batch payouts for multiple nodes.
    
    Initiates batch payout processing for multiple nodes in a single transaction.
    Returns batch ID and estimated completion time.
    """
    try:
        # Validate batch request
        if not batch_request.payout_requests or len(batch_request.payout_requests) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch request must contain at least one payout"
            )
        
        if len(batch_request.payout_requests) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size cannot exceed 1000 payouts"
            )
        
        # Validate all nodes exist
        for payout_req in batch_request.payout_requests:
            node = await repository.get_node(payout_req.node_id)
            if not node:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Node not found: {payout_req.node_id}"
                )
        
        # Process batch
        batch_id = await repository.process_batch_payouts(batch_request)
        
        # Calculate estimated completion time (rough estimate)
        estimated_completion = datetime.now(timezone.utc)
        estimated_completion = estimated_completion.replace(
            minute=estimated_completion.minute + 5  # 5 minutes estimate
        )
        
        logger.info(f"Initiated batch payout: {batch_id} with {len(batch_request.payout_requests)} payouts")
        
        return {
            "batch_id": batch_id,
            "status": "processing",
            "payout_count": len(batch_request.payout_requests),
            "estimated_completion": estimated_completion.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process batch payouts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process batch payouts"
        )

@router.get("/payouts/batch/{batch_id}", response_model=Dict[str, Any])
async def get_batch_status(
    batch_id: str = Path(..., description="Batch ID", pattern="^batch_[a-zA-Z0-9_-]+$"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get batch payout status and progress.
    
    Returns current status of a batch payout operation including:
    - Processing progress
    - Individual payout statuses
    - Error information
    - Completion statistics
    """
    try:
        # Get batch status
        batch_status = await repository.get_batch_status(batch_id)
        if not batch_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Batch not found"
            )
        
        return batch_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch status {batch_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve batch status"
        )

@router.get("/payouts/{payout_id}", response_model=Payout)
async def get_payout(
    payout_id: str = Path(..., description="Payout ID", pattern="^payout_[a-zA-Z0-9_-]+$"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get payout details by ID.
    
    Returns detailed information about a specific payout including:
    - Payout amount and currency
    - Transaction details
    - Status and timestamps
    - Error information (if failed)
    """
    try:
        # Get payout
        payout = await repository.get_payout(payout_id)
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payout not found"
            )
        
        return payout
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get payout {payout_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payout"
        )

@router.post("/{node_id}/payouts", response_model=Payout, status_code=status.HTTP_201_CREATED)
async def create_payout(
    node_id: str = Path(..., description="Node ID", pattern="^node_[a-zA-Z0-9_-]+$"),
    payout_request: PayoutRequest = ...,
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Create a new payout for a node.
    
    Creates a single payout request for a specific node.
    The payout will be processed according to the specified priority.
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Validate payout request
        if payout_request.node_id != node_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Node ID in request does not match path parameter"
            )
        
        if payout_request.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payout amount must be greater than 0"
            )
        
        # Validate wallet address format based on currency
        if payout_request.currency == Currency.USDT:
            if not payout_request.wallet_address or len(payout_request.wallet_address) != 34:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid TRON wallet address format"
                )
        elif payout_request.currency == Currency.LUCID:
            if not payout_request.wallet_address or len(payout_request.wallet_address) != 42:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid LUCID wallet address format"
                )
        
        # Create payout
        payout = await repository.create_payout(payout_request)
        
        logger.info(f"Created payout: {payout.payout_id} for node {node_id}")
        return payout
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create payout for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payout"
        )

@router.post("/payouts/{payout_id}/cancel", response_model=Dict[str, Any])
async def cancel_payout(
    payout_id: str = Path(..., description="Payout ID", pattern="^payout_[a-zA-Z0-9_-]+$"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Cancel a pending payout.
    
    Cancels a payout that is still in pending status.
    Completed or processing payouts cannot be cancelled.
    """
    try:
        # Get payout
        payout = await repository.get_payout(payout_id)
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payout not found"
            )
        
        # Check if payout can be cancelled
        if payout.status in [PayoutStatus.COMPLETED, PayoutStatus.PROCESSING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel payout in current status"
            )
        
        if payout.status == PayoutStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payout is already cancelled"
            )
        
        # Cancel payout
        await repository.cancel_payout(payout_id)
        
        logger.info(f"Cancelled payout: {payout_id}")
        return {
            "payout_id": payout_id,
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel payout {payout_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel payout"
        )

@router.get("/payouts/stats", response_model=Dict[str, Any])
async def get_payout_statistics(
    time_range: Optional[str] = Query("24h", description="Time range for statistics"),
    currency: Optional[Currency] = Query(None, description="Filter by currency"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get payout statistics and analytics.
    
    Returns aggregated payout statistics including:
    - Total payout amounts
    - Success/failure rates
    - Processing times
    - Currency breakdowns
    """
    try:
        # Get statistics
        stats = await repository.get_payout_statistics(
            time_range=time_range,
            currency=currency.value if currency else None
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get payout statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payout statistics"
        )

@router.get("/payouts/queue", response_model=Dict[str, Any])
async def get_payout_queue(
    priority: Optional[PayoutPriority] = Query(None, description="Filter by priority"),
    limit: int = Query(50, ge=1, le=200, description="Maximum items to return"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get current payout queue status.
    
    Returns information about pending payouts in the processing queue including:
    - Queue length and estimated wait times
    - Priority distribution
    - Processing capacity
    """
    try:
        # Get queue status
        queue_status = await repository.get_payout_queue(
            priority=priority.value if priority else None,
            limit=limit
        )
        
        return queue_status
        
    except Exception as e:
        logger.error(f"Failed to get payout queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payout queue"
        )
