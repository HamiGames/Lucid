# Path: node/api/nodes.py
# Lucid Node Management API - Node Endpoints
# Based on LUCID-STRICT requirements per Spec-1c

"""
Node management API endpoints for Lucid system.

This module provides REST API endpoints for:
- Node lifecycle management (CRUD operations)
- Node status monitoring
- Node configuration updates
- Node pool assignment
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
import uuid

from ..models.node import (
    Node, NodeCreateRequest, NodeUpdateRequest, 
    NodeStatus, NodeType, HardwareInfo, NodeLocation
)
from ..repositories.node_repository import NodeRepository

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Dependency for node repository
def get_node_repository() -> NodeRepository:
    """Get node repository instance"""
    return NodeRepository()

@router.get("/", response_model=Dict[str, Any])
async def list_nodes(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[NodeStatus] = Query(None, description="Filter by node status"),
    pool_id: Optional[str] = Query(None, description="Filter by pool ID"),
    node_type: Optional[NodeType] = Query(None, description="Filter by node type"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    List all nodes with pagination and filtering.
    
    Returns a paginated list of nodes with optional filtering by:
    - Status (active, inactive, maintenance, error)
    - Pool ID
    - Node type (worker, validator, storage, compute)
    """
    try:
        # Build filter criteria
        filters = {}
        if status:
            filters["status"] = status.value
        if pool_id:
            filters["pool_id"] = pool_id
        if node_type:
            filters["node_type"] = node_type.value
        
        # Get nodes from repository
        nodes, total_count = await repository.list_nodes(
            page=page,
            limit=limit,
            filters=filters
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
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
        
    except Exception as e:
        logger.error(f"Failed to list nodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve nodes"
        )

@router.post("/", response_model=Node, status_code=status.HTTP_201_CREATED)
async def create_node(
    node_data: NodeCreateRequest,
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Create a new node.
    
    Creates a new worker node with the specified configuration.
    The node will be assigned a unique ID and initial status.
    """
    try:
        # Validate node data
        if not node_data.name or len(node_data.name) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Node name must be at least 3 characters"
            )
        
        # Check if node name already exists
        existing_node = await repository.get_node_by_name(node_data.name)
        if existing_node:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Node with this name already exists"
            )
        
        # Create node
        node = await repository.create_node(node_data)
        
        logger.info(f"Created node: {node.node_id} ({node.name})")
        return node
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create node"
        )

@router.get("/{node_id}", response_model=Node)
async def get_node(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get node details by ID.
    
    Retrieves detailed information about a specific node including:
    - Node configuration
    - Hardware information
    - Current status
    - Resource metrics
    """
    try:
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        return node
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve node"
        )

@router.put("/{node_id}", response_model=Node)
async def update_node(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    node_data: NodeUpdateRequest = ...,
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Update node configuration.
    
    Updates node configuration including:
    - Node name and type
    - Pool assignment
    - Resource limits
    - Status changes
    """
    try:
        # Check if node exists
        existing_node = await repository.get_node(node_id)
        if not existing_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Validate name uniqueness if name is being changed
        if node_data.name and node_data.name != existing_node.name:
            name_exists = await repository.get_node_by_name(node_data.name)
            if name_exists and name_exists.node_id != node_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Node name already exists"
                )
        
        # Update node
        updated_node = await repository.update_node(node_id, node_data)
        
        logger.info(f"Updated node: {node_id}")
        return updated_node
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update node"
        )

@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Delete a node.
    
    Permanently removes a node from the system.
    This operation cannot be undone.
    """
    try:
        # Check if node exists
        existing_node = await repository.get_node(node_id)
        if not existing_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Check if node is active (prevent deletion of active nodes)
        if existing_node.status == NodeStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete active node. Stop the node first."
            )
        
        # Delete node
        await repository.delete_node(node_id)
        
        logger.info(f"Deleted node: {node_id}")
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete node"
        )

@router.post("/{node_id}/start", response_model=Dict[str, Any])
async def start_node(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Start a node.
    
    Starts a stopped or inactive node and changes its status to active.
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Check if node can be started
        if node.status == NodeStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Node is already active"
            )
        
        # Start node
        await repository.start_node(node_id)
        
        logger.info(f"Started node: {node_id}")
        return {
            "node_id": node_id,
            "status": "starting",
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start node"
        )

@router.post("/{node_id}/stop", response_model=Dict[str, Any])
async def stop_node(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Stop a node.
    
    Stops an active node and changes its status to inactive.
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Check if node can be stopped
        if node.status != NodeStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Node is not active"
            )
        
        # Stop node
        await repository.stop_node(node_id)
        
        logger.info(f"Stopped node: {node_id}")
        return {
            "node_id": node_id,
            "status": "stopping",
            "stopped_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop node"
        )

@router.get("/{node_id}/status", response_model=Dict[str, Any])
async def get_node_status(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get node status and health information.
    
    Returns current node status including:
    - Operational status
    - Resource utilization
    - Last heartbeat
    - Error information (if any)
    """
    try:
        # Get node
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get additional status information
        status_info = await repository.get_node_status(node_id)
        
        return {
            "node_id": node_id,
            "status": node.status.value,
            "node_type": node.node_type.value,
            "pool_id": node.pool_id,
            "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
            "created_at": node.created_at.isoformat(),
            "updated_at": node.updated_at.isoformat(),
            **status_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node status {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve node status"
        )
