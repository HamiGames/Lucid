# Path: node/api/pools.py
# Lucid Node Management API - Pool Endpoints
# Based on LUCID-STRICT requirements per Spec-1c

"""
Pool management API endpoints for Lucid system.

This module provides REST API endpoints for:
- Pool lifecycle management (CRUD operations)
- Node assignment to pools
- Pool resource management
- Auto-scaling configuration
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
import uuid

from ..models.pool import (
    NodePool, NodePoolCreateRequest, NodePoolUpdateRequest,
    ResourceLimits, ScalingPolicy
)
from ..repositories.pool_repository import PoolRepository

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Dependency for pool repository
def get_pool_repository() -> PoolRepository:
    """Get pool repository instance"""
    return PoolRepository()

@router.get("/", response_model=Dict[str, Any])
async def list_pools(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    auto_scaling: Optional[bool] = Query(None, description="Filter by auto-scaling enabled"),
    repository: PoolRepository = Depends(get_pool_repository)
):
    """
    List all node pools with pagination and filtering.
    
    Returns a paginated list of pools with optional filtering by:
    - Auto-scaling enabled/disabled
    - Pool capacity
    - Resource limits
    """
    try:
        # Build filter criteria
        filters = {}
        if auto_scaling is not None:
            filters["auto_scaling"] = auto_scaling
        
        # Get pools from repository
        pools, total_count = await repository.list_pools(
            page=page,
            limit=limit,
            filters=filters
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "pools": [pool.dict() for pool in pools],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list pools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pools"
        )

@router.post("/", response_model=NodePool, status_code=status.HTTP_201_CREATED)
async def create_pool(
    pool_data: NodePoolCreateRequest,
    repository: PoolRepository = Depends(get_pool_repository)
):
    """
    Create a new node pool.
    
    Creates a new pool with the specified configuration.
    The pool will be assigned a unique ID and initial settings.
    """
    try:
        # Validate pool data
        if not pool_data.name or len(pool_data.name) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pool name must be at least 3 characters"
            )
        
        if pool_data.max_nodes < 1 or pool_data.max_nodes > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Max nodes must be between 1 and 1000"
            )
        
        # Check if pool name already exists
        existing_pool = await repository.get_pool_by_name(pool_data.name)
        if existing_pool:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pool with this name already exists"
            )
        
        # Create pool
        pool = await repository.create_pool(pool_data)
        
        logger.info(f"Created pool: {pool.pool_id} ({pool.name})")
        return pool
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create pool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create pool"
        )

@router.get("/{pool_id}", response_model=NodePool)
async def get_pool(
    pool_id: str = Path(..., description="Pool ID", regex="^pool_[a-zA-Z0-9_-]+$"),
    repository: PoolRepository = Depends(get_pool_repository)
):
    """
    Get pool details by ID.
    
    Retrieves detailed information about a specific pool including:
    - Pool configuration
    - Node assignments
    - Resource limits
    - Auto-scaling settings
    """
    try:
        pool = await repository.get_pool(pool_id)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pool not found"
            )
        
        return pool
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pool {pool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pool"
        )

@router.put("/{pool_id}", response_model=NodePool)
async def update_pool(
    pool_id: str = Path(..., description="Pool ID", regex="^pool_[a-zA-Z0-9_-]+$"),
    pool_data: NodePoolUpdateRequest = ...,
    repository: PoolRepository = Depends(get_pool_repository)
):
    """
    Update pool configuration.
    
    Updates pool configuration including:
    - Pool name and description
    - Resource limits
    - Auto-scaling settings
    - Node capacity
    """
    try:
        # Check if pool exists
        existing_pool = await repository.get_pool(pool_id)
        if not existing_pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pool not found"
            )
        
        # Validate name uniqueness if name is being changed
        if pool_data.name and pool_data.name != existing_pool.name:
            name_exists = await repository.get_pool_by_name(pool_data.name)
            if name_exists and name_exists.pool_id != pool_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Pool name already exists"
                )
        
        # Update pool
        updated_pool = await repository.update_pool(pool_id, pool_data)
        
        logger.info(f"Updated pool: {pool_id}")
        return updated_pool
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update pool {pool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update pool"
        )

@router.delete("/{pool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pool(
    pool_id: str = Path(..., description="Pool ID", regex="^pool_[a-zA-Z0-9_-]+$"),
    repository: PoolRepository = Depends(get_pool_repository)
):
    """
    Delete a pool.
    
    Permanently removes a pool from the system.
    All nodes in the pool must be reassigned or removed first.
    """
    try:
        # Check if pool exists
        existing_pool = await repository.get_pool(pool_id)
        if not existing_pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pool not found"
            )
        
        # Check if pool has nodes
        if existing_pool.node_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete pool with assigned nodes. Remove all nodes first."
            )
        
        # Delete pool
        await repository.delete_pool(pool_id)
        
        logger.info(f"Deleted pool: {pool_id}")
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pool {pool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete pool"
        )

@router.post("/{pool_id}/nodes", response_model=Dict[str, Any])
async def add_node_to_pool(
    pool_id: str = Path(..., description="Pool ID", regex="^pool_[a-zA-Z0-9_-]+$"),
    node_id: str = Query(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    priority: int = Query(50, ge=1, le=100, description="Node priority in pool"),
    repository: PoolRepository = Depends(get_pool_repository)
):
    """
    Add a node to a pool.
    
    Assigns a node to a specific pool with the given priority.
    The node must be inactive or in maintenance mode.
    """
    try:
        # Check if pool exists
        pool = await repository.get_pool(pool_id)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pool not found"
            )
        
        # Check pool capacity
        if pool.node_count >= pool.max_nodes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pool is at maximum capacity"
            )
        
        # Add node to pool
        await repository.add_node_to_pool(pool_id, node_id, priority)
        
        logger.info(f"Added node {node_id} to pool {pool_id}")
        return {
            "pool_id": pool_id,
            "node_id": node_id,
            "priority": priority,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add node {node_id} to pool {pool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add node to pool"
        )

@router.delete("/{pool_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_node_from_pool(
    pool_id: str = Path(..., description="Pool ID", regex="^pool_[a-zA-Z0-9_-]+$"),
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    repository: PoolRepository = Depends(get_pool_repository)
):
    """
    Remove a node from a pool.
    
    Removes a node from the specified pool.
    The node will be unassigned and can be assigned to another pool.
    """
    try:
        # Check if pool exists
        pool = await repository.get_pool(pool_id)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pool not found"
            )
        
        # Remove node from pool
        success = await repository.remove_node_from_pool(pool_id, node_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found in pool"
            )
        
        logger.info(f"Removed node {node_id} from pool {pool_id}")
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove node {node_id} from pool {pool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove node from pool"
        )

@router.get("/{pool_id}/nodes", response_model=Dict[str, Any])
async def list_pool_nodes(
    pool_id: str = Path(..., description="Pool ID", regex="^pool_[a-zA-Z0-9_-]+$"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    repository: PoolRepository = Depends(get_pool_repository)
):
    """
    List nodes in a pool.
    
    Returns a paginated list of nodes assigned to the specified pool.
    """
    try:
        # Check if pool exists
        pool = await repository.get_pool(pool_id)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pool not found"
            )
        
        # Get nodes in pool
        nodes, total_count = await repository.list_pool_nodes(
            pool_id=pool_id,
            page=page,
            limit=limit
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "pool_id": pool_id,
            "nodes": [node.dict() for node in nodes],
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
        logger.error(f"Failed to list nodes in pool {pool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pool nodes"
        )

@router.post("/{pool_id}/scale", response_model=Dict[str, Any])
async def scale_pool(
    pool_id: str = Path(..., description="Pool ID", regex="^pool_[a-zA-Z0-9_-]+$"),
    target_nodes: int = Query(..., ge=0, description="Target number of nodes"),
    repository: PoolRepository = Depends(get_pool_repository)
):
    """
    Scale a pool to target number of nodes.
    
    Manually scales a pool to the specified number of nodes.
    This overrides auto-scaling settings temporarily.
    """
    try:
        # Check if pool exists
        pool = await repository.get_pool(pool_id)
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pool not found"
            )
        
        # Validate target nodes
        if target_nodes > pool.max_nodes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target nodes exceeds pool maximum capacity"
            )
        
        # Scale pool
        await repository.scale_pool(pool_id, target_nodes)
        
        logger.info(f"Scaled pool {pool_id} to {target_nodes} nodes")
        return {
            "pool_id": pool_id,
            "target_nodes": target_nodes,
            "scaled_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to scale pool {pool_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scale pool"
        )
