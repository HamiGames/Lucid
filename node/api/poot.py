# Path: node/api/poot.py
# Lucid Node Management API - PoOT Endpoints
# Based on LUCID-STRICT requirements per Spec-1c

"""
PoOT (Proof of Output) validation API endpoints for Lucid system.

This module provides REST API endpoints for:
- PoOT score calculation and validation
- Batch PoOT validation
- PoOT history and analytics
- Output data verification
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
import uuid
import hashlib
import base64

from ..models.node import PoOTScore, PoOTValidation, PoOTValidationRequest
from ..repositories.node_repository import NodeRepository

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Dependency for node repository
def get_node_repository() -> NodeRepository:
    """Get node repository instance"""
    return NodeRepository()

@router.get("/{node_id}/poot/score", response_model=PoOTScore)
async def get_poot_score(
    node_id: str = Path(..., description="Node ID", pattern="^node_[a-zA-Z0-9_-]+$"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get current PoOT score for a node.
    
    Returns the current PoOT score including:
    - Score value (0-100)
    - Calculation timestamp
    - Output hash
    - Validation status
    - Confidence level
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get PoOT score
        poot_score = await repository.get_poot_score(node_id)
        if not poot_score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PoOT score not found for node"
            )
        
        return poot_score
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PoOT score for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve PoOT score"
        )

@router.post("/{node_id}/poot/validate", response_model=PoOTValidation)
async def validate_poot(
    node_id: str = Path(..., description="Node ID", pattern="^node_[a-zA-Z0-9_-]+$"),
    validation_request: PoOTValidationRequest = ...,
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Validate PoOT for a specific node.
    
    Validates the PoOT output data for a node including:
    - Output data verification
    - Hash validation
    - Score calculation
    - Confidence assessment
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Validate request data
        if not validation_request.output_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Output data is required"
            )
        
        # Decode and validate base64 data
        try:
            decoded_data = base64.b64decode(validation_request.output_data)
            if len(decoded_data) > 1024 * 1024:  # 1MB limit
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Output data too large (max 1MB)"
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 encoded output data"
            )
        
        # Calculate hash of output data
        output_hash = hashlib.sha256(decoded_data).hexdigest()
        
        # Validate PoOT
        validation_result = await repository.validate_poot(
            node_id=node_id,
            output_data=validation_request.output_data,
            output_hash=output_hash,
            timestamp=validation_request.timestamp,
            nonce=validation_request.nonce
        )
        
        logger.info(f"Validated PoOT for node {node_id}: {validation_result.is_valid}")
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate PoOT for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate PoOT"
        )

@router.post("/poot/batch-validate", response_model=Dict[str, Any])
async def batch_validate_poot(
    validations: List[PoOTValidationRequest],
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Batch validate PoOT for multiple nodes.
    
    Validates PoOT for multiple nodes in a single request.
    Returns validation results for all nodes.
    """
    try:
        # Validate batch size
        if not validations or len(validations) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch must contain at least one validation"
            )
        
        if len(validations) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size cannot exceed 100 validations"
            )
        
        # Process batch validations
        results = []
        valid_count = 0
        invalid_count = 0
        error_count = 0
        
        for validation_req in validations:
            try:
                # Check if node exists
                node = await repository.get_node(validation_req.node_id)
                if not node:
                    results.append({
                        "node_id": validation_req.node_id,
                        "is_valid": False,
                        "error": "Node not found"
                    })
                    error_count += 1
                    continue
                
                # Validate PoOT
                validation_result = await repository.validate_poot(
                    node_id=validation_req.node_id,
                    output_data=validation_req.output_data,
                    output_hash=hashlib.sha256(base64.b64decode(validation_req.output_data)).hexdigest(),
                    timestamp=validation_req.timestamp,
                    nonce=validation_req.nonce
                )
                
                results.append(validation_result.dict())
                
                if validation_result.is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to validate PoOT for node {validation_req.node_id}: {e}")
                results.append({
                    "node_id": validation_req.node_id,
                    "is_valid": False,
                    "error": str(e)
                })
                error_count += 1
        
        logger.info(f"Batch PoOT validation completed: {valid_count} valid, {invalid_count} invalid, {error_count} errors")
        
        return {
            "results": results,
            "summary": {
                "total": len(validations),
                "valid": valid_count,
                "invalid": invalid_count,
                "errors": error_count
            },
            "batch_id": str(uuid.uuid4()),
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch validate PoOT: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to batch validate PoOT"
        )

@router.get("/{node_id}/poot/history", response_model=Dict[str, Any])
async def get_poot_history(
    node_id: str = Path(..., description="Node ID", pattern="^node_[a-zA-Z0-9_-]+$"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get PoOT validation history for a node.
    
    Returns a paginated list of PoOT validations including:
    - Historical scores
    - Validation timestamps
    - Success/failure rates
    - Performance metrics
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get PoOT history
        history, total_count = await repository.get_poot_history(
            node_id=node_id,
            page=page,
            limit=limit
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "node_id": node_id,
            "history": [validation.dict() for validation in history],
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
        logger.error(f"Failed to get PoOT history for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve PoOT history"
        )

@router.get("/poot/statistics", response_model=Dict[str, Any])
async def get_poot_statistics(
    time_range: Optional[str] = Query("24h", description="Time range for statistics"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get PoOT validation statistics.
    
    Returns aggregated PoOT statistics including:
    - Average scores
    - Validation success rates
    - Performance metrics
    - Node rankings
    """
    try:
        # Get statistics
        stats = await repository.get_poot_statistics(time_range=time_range)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get PoOT statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve PoOT statistics"
        )

@router.get("/poot/leaderboard", response_model=Dict[str, Any])
async def get_poot_leaderboard(
    limit: int = Query(50, ge=1, le=200, description="Number of top nodes to return"),
    time_range: Optional[str] = Query("24h", description="Time range for leaderboard"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get PoOT score leaderboard.
    
    Returns the top performing nodes by PoOT score including:
    - Node rankings
    - Score comparisons
    - Performance trends
    - Achievement badges
    """
    try:
        # Get leaderboard
        leaderboard = await repository.get_poot_leaderboard(
            limit=limit,
            time_range=time_range
        )
        
        return leaderboard
        
    except Exception as e:
        logger.error(f"Failed to get PoOT leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve PoOT leaderboard"
        )

@router.post("/{node_id}/poot/calculate", response_model=PoOTScore)
async def calculate_poot_score(
    node_id: str = Path(..., description="Node ID", pattern="^node_[a-zA-Z0-9_-]+$"),
    output_data: str = Query(..., description="Base64 encoded output data"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Calculate PoOT score for a node.
    
    Calculates and stores a new PoOT score based on provided output data.
    This endpoint triggers score calculation and updates the node's current score.
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Validate output data
        try:
            decoded_data = base64.b64decode(output_data)
            if len(decoded_data) > 1024 * 1024:  # 1MB limit
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Output data too large (max 1MB)"
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 encoded output data"
            )
        
        # Calculate PoOT score
        poot_score = await repository.calculate_poot_score(
            node_id=node_id,
            output_data=output_data
        )
        
        logger.info(f"Calculated PoOT score for node {node_id}: {poot_score.score}")
        return poot_score
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate PoOT score for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate PoOT score"
        )
