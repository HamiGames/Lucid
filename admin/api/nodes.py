#!/usr/bin/env python3
"""
Lucid Admin Interface - Node Management API
Step 23: Admin Backend APIs Implementation

Node management API endpoints for the Lucid admin interface.
Provides node monitoring, control, and maintenance functionality.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from pydantic import BaseModel, Field
import uuid

# Import admin modules
from admin.config import get_admin_config
from admin.system.admin_controller import AdminController, AdminAccount
from admin.rbac.manager import RBACManager
from admin.audit.logger import AuditLogger

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class NodeInfo(BaseModel):
    """Node information"""
    id: str = Field(..., description="Node ID")
    hostname: str = Field(..., description="Node hostname")
    status: str = Field(..., description="Node status")
    ip_address: str = Field(..., description="Node IP address")
    load_average: float = Field(..., description="Load average")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    active_sessions: int = Field(..., description="Active sessions count")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")
    node_type: str = Field(..., description="Node type")
    location: str = Field(..., description="Node location")
    version: str = Field(..., description="Node version")
    uptime: str = Field(..., description="Node uptime")


class NodeListResponse(BaseModel):
    """Node list response"""
    nodes: List[NodeInfo] = Field(..., description="List of nodes")
    total: int = Field(..., description="Total number of nodes")
    online: int = Field(..., description="Online nodes count")
    offline: int = Field(..., description="Offline nodes count")
    maintenance: int = Field(..., description="Maintenance nodes count")


class NodeMetrics(BaseModel):
    """Node performance metrics"""
    node_id: str = Field(..., description="Node ID")
    timestamp: datetime = Field(..., description="Metrics timestamp")
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    network_in: int = Field(..., description="Network bytes in")
    network_out: int = Field(..., description="Network bytes out")
    load_average: List[float] = Field(..., description="Load average (1m, 5m, 15m)")
    active_sessions: int = Field(..., description="Active sessions")
    response_time: float = Field(..., description="Response time in ms")


class NodeMaintenanceRequest(BaseModel):
    """Node maintenance request"""
    reason: str = Field(..., min_length=10, description="Maintenance reason")
    duration_hours: Optional[int] = Field(None, description="Maintenance duration in hours")
    notify_users: bool = Field(True, description="Whether to notify users")
    drain_sessions: bool = Field(True, description="Whether to drain existing sessions")


class NodeRestartRequest(BaseModel):
    """Node restart request"""
    reason: str = Field(..., min_length=10, description="Restart reason")
    graceful: bool = Field(True, description="Graceful restart")
    notify_users: bool = Field(True, description="Whether to notify users")


class NodeStatusUpdate(BaseModel):
    """Node status update"""
    node_id: str = Field(..., description="Node ID")
    status: str = Field(..., description="New status")
    reason: str = Field(..., description="Status change reason")
    updated_by: str = Field(..., description="Admin who updated status")
    updated_at: datetime = Field(..., description="Update timestamp")


async def get_admin_controller() -> AdminController:
    """Get admin controller dependency"""
    from admin.main import admin_controller
    if not admin_controller:
        raise HTTPException(
            status_code=503,
            detail="Admin controller not available"
        )
    return admin_controller


async def get_rbac_manager() -> RBACManager:
    """Get RBAC manager dependency"""
    from admin.main import rbac_manager
    if not rbac_manager:
        raise HTTPException(
            status_code=503,
            detail="RBAC manager not available"
        )
    return rbac_manager


async def get_audit_logger() -> AuditLogger:
    """Get audit logger dependency"""
    from admin.main import audit_logger
    if not audit_logger:
        raise HTTPException(
            status_code=503,
            detail="Audit logger not available"
        )
    return audit_logger


@router.get("", response_model=NodeListResponse)
async def list_nodes(
    status: Optional[str] = Query(None, description="Filter by node status"),
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    limit: int = Query(50, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Results offset"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    List all nodes with optional filtering
    
    Parameters:
    - status: online, offline, maintenance
    - node_type: Filter by node type
    - location: Filter by location
    - limit: Number of results (1-1000)
    - offset: Results offset
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "nodes:list")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: nodes:list"
            )
        
        # Log access
        await audit.log_access(
            admin.admin_id,
            "nodes_list",
            f"GET /admin/api/v1/nodes?status={status}&node_type={node_type}&location={location}"
        )
        
        # Get nodes from database
        nodes = await _get_nodes_from_database(
            status=status,
            node_type=node_type,
            location=location,
            limit=limit,
            offset=offset
        )
        
        # Get node counts
        total, online, offline, maintenance = await _get_node_counts(
            status=status,
            node_type=node_type,
            location=location
        )
        
        return NodeListResponse(
            nodes=nodes,
            total=total,
            online=online,
            offline=offline,
            maintenance=maintenance
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list nodes: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve nodes"
        )


@router.get("/{node_id}", response_model=NodeInfo)
async def get_node(
    node_id: str = Path(..., description="Node ID"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Get node by ID
    
    Retrieves detailed information about a specific node.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "nodes:view")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: nodes:view"
            )
        
        # Log access
        await audit.log_access(
            admin.admin_id,
            "node_view",
            f"GET /admin/api/v1/nodes/{node_id}"
        )
        
        # Get node
        node = await _get_node_by_id(node_id)
        if not node:
            raise HTTPException(
                status_code=404,
                detail="Node not found"
            )
        
        return node
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve node"
        )


@router.get("/{node_id}/metrics", response_model=List[NodeMetrics])
async def get_node_metrics(
    node_id: str = Path(..., description="Node ID"),
    timeframe: str = Query("1h", description="Time range for metrics"),
    limit: int = Query(100, ge=1, le=1000, description="Number of metrics to return"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Get node performance metrics
    
    Retrieves performance metrics for a specific node.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "nodes:view_metrics")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: nodes:view_metrics"
            )
        
        # Validate timeframe
        valid_timeframes = ["1h", "6h", "24h", "7d", "30d"]
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe. Must be one of: {valid_timeframes}"
            )
        
        # Check if node exists
        existing_node = await _get_node_by_id(node_id)
        if not existing_node:
            raise HTTPException(
                status_code=404,
                detail="Node not found"
            )
        
        # Log access
        await audit.log_access(
            admin.admin_id,
            "node_metrics",
            f"GET /admin/api/v1/nodes/{node_id}/metrics?timeframe={timeframe}"
        )
        
        # Get node metrics
        metrics = await _get_node_metrics_from_service(
            node_id,
            timeframe,
            limit
        )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve node metrics"
        )


@router.post("/{node_id}/restart", response_model=Dict[str, str])
async def restart_node(
    node_id: str = Path(..., description="Node ID"),
    restart_data: NodeRestartRequest = Body(..., description="Restart details"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Restart specific node
    
    Restarts a specific node with optional graceful shutdown.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "nodes:restart")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: nodes:restart"
            )
        
        # Check if node exists
        existing_node = await _get_node_by_id(node_id)
        if not existing_node:
            raise HTTPException(
                status_code=404,
                detail="Node not found"
            )
        
        # Check if node is already restarting
        if existing_node.status == "restarting":
            raise HTTPException(
                status_code=409,
                detail="Node is already restarting"
            )
        
        # Restart node
        await _restart_node_in_service(
            node_id,
            restart_data.reason,
            restart_data.graceful,
            admin.admin_id
        )
        
        # Log restart
        await audit.log_node_action(
            admin.admin_id,
            "node_restart",
            node_id,
            {
                "reason": restart_data.reason,
                "graceful": restart_data.graceful
            }
        )
        
        # Notify users if requested
        if restart_data.notify_users:
            await _notify_users_node_restart(node_id, restart_data.reason)
        
        return {
            "status": "success",
            "message": f"Node {node_id} restart initiated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart node: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to restart node"
        )


@router.post("/{node_id}/maintenance", response_model=Dict[str, str])
async def put_node_in_maintenance(
    node_id: str = Path(..., description="Node ID"),
    maintenance_data: NodeMaintenanceRequest = Body(..., description="Maintenance details"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Put node in maintenance mode
    
    Puts a node in maintenance mode, optionally draining existing sessions.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "nodes:maintenance")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: nodes:maintenance"
            )
        
        # Check if node exists
        existing_node = await _get_node_by_id(node_id)
        if not existing_node:
            raise HTTPException(
                status_code=404,
                detail="Node not found"
            )
        
        # Check if node is already in maintenance
        if existing_node.status == "maintenance":
            raise HTTPException(
                status_code=409,
                detail="Node is already in maintenance mode"
            )
        
        # Put node in maintenance
        await _put_node_in_maintenance_in_service(
            node_id,
            maintenance_data.reason,
            maintenance_data.duration_hours,
            maintenance_data.drain_sessions,
            admin.admin_id
        )
        
        # Log maintenance
        await audit.log_node_action(
            admin.admin_id,
            "node_maintenance",
            node_id,
            {
                "reason": maintenance_data.reason,
                "duration_hours": maintenance_data.duration_hours,
                "drain_sessions": maintenance_data.drain_sessions
            }
        )
        
        # Notify users if requested
        if maintenance_data.notify_users:
            await _notify_users_node_maintenance(node_id, maintenance_data.reason)
        
        return {
            "status": "success",
            "message": f"Node {node_id} put in maintenance mode"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to put node in maintenance: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to put node in maintenance"
        )


@router.post("/{node_id}/activate", response_model=Dict[str, str])
async def activate_node(
    node_id: str = Path(..., description="Node ID"),
    reason: str = Body(..., description="Activation reason"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Activate node
    
    Activates a node from maintenance mode.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "nodes:activate")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: nodes:activate"
            )
        
        # Check if node exists
        existing_node = await _get_node_by_id(node_id)
        if not existing_node:
            raise HTTPException(
                status_code=404,
                detail="Node not found"
            )
        
        # Check if node is not in maintenance
        if existing_node.status != "maintenance":
            raise HTTPException(
                status_code=409,
                detail="Node is not in maintenance mode"
            )
        
        # Activate node
        await _activate_node_in_service(
            node_id,
            reason,
            admin.admin_id
        )
        
        # Log activation
        await audit.log_node_action(
            admin.admin_id,
            "node_activated",
            node_id,
            {
                "reason": reason
            }
        )
        
        return {
            "status": "success",
            "message": f"Node {node_id} activated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate node: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to activate node"
        )


# Helper functions
async def _get_nodes_from_database(
    status: Optional[str] = None,
    node_type: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[NodeInfo]:
    """Get nodes from database with filtering"""
    try:
        # This would query the actual database
        # For now, return sample data
        nodes = []
        
        # Sample node data
        sample_nodes = [
            {
                "id": "node-1",
                "hostname": "node-1.lucid.local",
                "status": "online",
                "ip_address": "192.168.1.10",
                "load_average": 0.75,
                "memory_usage": 67.8,
                "disk_usage": 23.4,
                "active_sessions": 5,
                "last_heartbeat": datetime.now(timezone.utc),
                "node_type": "worker",
                "location": "US-East",
                "version": "1.0.0",
                "uptime": "7 days, 12 hours"
            },
            {
                "id": "node-2",
                "hostname": "node-2.lucid.local",
                "status": "maintenance",
                "ip_address": "192.168.1.11",
                "load_average": 0.0,
                "memory_usage": 45.2,
                "disk_usage": 18.7,
                "active_sessions": 0,
                "last_heartbeat": datetime.now(timezone.utc),
                "node_type": "worker",
                "location": "US-West",
                "version": "1.0.0",
                "uptime": "3 days, 8 hours"
            }
        ]
        
        for node_data in sample_nodes:
            # Apply filters
            if status and node_data["status"] != status:
                continue
            if node_type and node_data["node_type"] != node_type:
                continue
            if location and node_data["location"] != location:
                continue
            
            nodes.append(NodeInfo(**node_data))
        
        return nodes[offset:offset + limit]
        
    except Exception as e:
        logger.error(f"Failed to get nodes from database: {e}")
        return []


async def _get_node_counts(
    status: Optional[str] = None,
    node_type: Optional[str] = None,
    location: Optional[str] = None
) -> tuple[int, int, int, int]:
    """Get node counts by status"""
    try:
        # This would query the actual database
        # For now, return sample counts
        return 2, 1, 0, 1  # total, online, offline, maintenance
        
    except Exception as e:
        logger.error(f"Failed to get node counts: {e}")
        return 0, 0, 0, 0


async def _get_node_by_id(node_id: str) -> Optional[NodeInfo]:
    """Get node by ID"""
    try:
        # This would query the actual database
        # For now, return sample data
        if node_id == "node-1":
            return NodeInfo(
                id="node-1",
                hostname="node-1.lucid.local",
                status="online",
                ip_address="192.168.1.10",
                load_average=0.75,
                memory_usage=67.8,
                disk_usage=23.4,
                active_sessions=5,
                last_heartbeat=datetime.now(timezone.utc),
                node_type="worker",
                location="US-East",
                version="1.0.0",
                uptime="7 days, 12 hours"
            )
        return None
        
    except Exception as e:
        logger.error(f"Failed to get node by ID: {e}")
        return None


async def _get_node_metrics_from_service(
    node_id: str,
    timeframe: str,
    limit: int
) -> List[NodeMetrics]:
    """Get node metrics from service"""
    try:
        # This would query the actual service
        # For now, return sample data
        metrics = []
        
        # Sample metrics
        sample_metrics = [
            {
                "node_id": node_id,
                "timestamp": datetime.now(timezone.utc),
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "disk_usage": 23.4,
                "network_in": 1024000,
                "network_out": 2048000,
                "load_average": [0.75, 0.80, 0.85],
                "active_sessions": 5,
                "response_time": 25.5
            }
        ]
        
        for metric_data in sample_metrics:
            metrics.append(NodeMetrics(**metric_data))
        
        return metrics[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get node metrics: {e}")
        return []


async def _restart_node_in_service(
    node_id: str,
    reason: str,
    graceful: bool,
    admin_id: str
):
    """Restart node in service"""
    try:
        # This would restart the node in the actual service
        logger.info(f"Node restart initiated: {node_id} by admin: {admin_id}, reason: {reason}, graceful: {graceful}")
        
    except Exception as e:
        logger.error(f"Failed to restart node in service: {e}")
        raise


async def _put_node_in_maintenance_in_service(
    node_id: str,
    reason: str,
    duration_hours: Optional[int],
    drain_sessions: bool,
    admin_id: str
):
    """Put node in maintenance in service"""
    try:
        # This would put the node in maintenance in the actual service
        logger.info(f"Node maintenance initiated: {node_id} by admin: {admin_id}, reason: {reason}, duration: {duration_hours}, drain: {drain_sessions}")
        
    except Exception as e:
        logger.error(f"Failed to put node in maintenance: {e}")
        raise


async def _activate_node_in_service(
    node_id: str,
    reason: str,
    admin_id: str
):
    """Activate node in service"""
    try:
        # This would activate the node in the actual service
        logger.info(f"Node activation initiated: {node_id} by admin: {admin_id}, reason: {reason}")
        
    except Exception as e:
        logger.error(f"Failed to activate node: {e}")
        raise


async def _notify_users_node_restart(node_id: str, reason: str):
    """Notify users of node restart"""
    try:
        # This would send notifications to users
        logger.info(f"User notifications sent: node restart for node: {node_id}")
        
    except Exception as e:
        logger.error(f"Failed to notify users node restart: {e}")


async def _notify_users_node_maintenance(node_id: str, reason: str):
    """Notify users of node maintenance"""
    try:
        # This would send notifications to users
        logger.info(f"User notifications sent: node maintenance for node: {node_id}")
        
    except Exception as e:
        logger.error(f"Failed to notify users node maintenance: {e}")
