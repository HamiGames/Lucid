#!/usr/bin/env python3
"""
Lucid Admin Interface - Dashboard API
Step 23: Admin Backend APIs Implementation

Dashboard API endpoints for the Lucid admin interface.
Provides system overview, metrics, and real-time monitoring data.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import json

# Import admin modules
from admin.config import get_admin_config
from admin.system.admin_controller import AdminController, AdminAccount
from admin.rbac.manager import RBACManager
from admin.audit.logger import AuditLogger

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Dashboard"])

# Security
security = HTTPBearer()

# Pydantic models
class SystemStatus(BaseModel):
    """System status information"""
    status: str = Field(..., description="Overall system status")
    uptime: str = Field(..., description="System uptime")
    version: str = Field(..., description="System version")
    last_updated: datetime = Field(..., description="Last update timestamp")


class ActiveSessions(BaseModel):
    """Active sessions information"""
    total: int = Field(..., description="Total sessions")
    active: int = Field(..., description="Active sessions")
    idle: int = Field(..., description="Idle sessions")
    by_type: Dict[str, int] = Field(..., description="Sessions by type")


class NodeStatus(BaseModel):
    """Node status information"""
    total_nodes: int = Field(..., description="Total nodes")
    online_nodes: int = Field(..., description="Online nodes")
    offline_nodes: int = Field(..., description="Offline nodes")
    load_average: float = Field(..., description="Average load")


class BlockchainStatus(BaseModel):
    """Blockchain status information"""
    network_height: int = Field(..., description="Network block height")
    sync_status: str = Field(..., description="Sync status")
    pending_transactions: int = Field(..., description="Pending transactions")


class ResourceUsage(BaseModel):
    """Resource usage information"""
    cpu_percentage: float = Field(..., description="CPU usage percentage")
    memory_percentage: float = Field(..., description="Memory usage percentage")
    disk_percentage: float = Field(..., description="Disk usage percentage")
    network_io: Dict[str, int] = Field(..., description="Network I/O statistics")


class DashboardOverview(BaseModel):
    """Dashboard overview data"""
    system_status: SystemStatus
    active_sessions: ActiveSessions
    node_status: NodeStatus
    blockchain_status: BlockchainStatus
    resource_usage: ResourceUsage


class MetricDataPoint(BaseModel):
    """Metric data point"""
    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Metric value")
    label: Optional[str] = Field(None, description="Data point label")


class MetricResponse(BaseModel):
    """Metric response"""
    metric_name: str = Field(..., description="Metric name")
    data_points: List[MetricDataPoint] = Field(..., description="Metric data points")
    time_range: str = Field(..., description="Time range")
    aggregation: str = Field(..., description="Aggregation method")


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(..., description="Message timestamp")


# Global WebSocket connections
websocket_connections: List[WebSocket] = []


async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AdminAccount:
    """Get current authenticated admin user"""
    from admin.main import admin_controller
    if not admin_controller:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin controller not available"
        )
    
    try:
        admin = await admin_controller.validate_admin_session(credentials.credentials)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token"
            )
        return admin
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_rbac_manager() -> RBACManager:
    """Get RBAC manager dependency"""
    from admin.main import rbac_manager
    if not rbac_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RBAC manager not available"
        )
    return rbac_manager


async def get_audit_logger() -> AuditLogger:
    """Get audit logger dependency"""
    from admin.main import audit_logger
    if not audit_logger:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit logger not available"
        )
    return audit_logger


@router.get(
    "/overview",
    response_model=DashboardOverview,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard overview",
    description="Get comprehensive system overview dashboard data including system health, active sessions, node status, blockchain sync status, and resource usage metrics",
    operation_id="get_dashboard_overview",
    responses={
        200: {"description": "Dashboard overview retrieved successfully"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
)
async def get_dashboard_overview(
    admin: AdminAccount = Depends(get_current_admin),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Get system overview dashboard data
    
    Returns comprehensive system status including:
    - System health and uptime
    - Active session statistics
    - Node status and load
    - Blockchain synchronization status
    - Resource usage metrics
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "dashboard:view")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: dashboard:view"
            )
        
        # Log access
        await audit.log_access(
            admin.admin_id,
            "dashboard_overview",
            "GET /admin/api/v1/dashboard/overview"
        )
        
        # Get system status
        system_status = await _get_system_status()
        
        # Get active sessions
        active_sessions = await _get_active_sessions()
        
        # Get node status
        node_status = await _get_node_status()
        
        # Get blockchain status
        blockchain_status = await _get_blockchain_status()
        
        # Get resource usage
        resource_usage = await _get_resource_usage()
        
        return DashboardOverview(
            system_status=system_status,
            active_sessions=active_sessions,
            node_status=node_status,
            blockchain_status=blockchain_status,
            resource_usage=resource_usage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard data"
        )


@router.get(
    "/metrics",
    response_model=List[MetricResponse],
    status_code=status.HTTP_200_OK,
    summary="Get system metrics",
    description="Get real-time system metrics for specified timeframe and metric type",
    operation_id="get_dashboard_metrics",
    responses={
        200: {"description": "Metrics retrieved successfully"},
        400: {"description": "Invalid timeframe or metric parameter"},
        403: {"description": "Permission denied"},
        500: {"description": "Internal server error"}
    }
)
async def get_dashboard_metrics(
    timeframe: str = Query("1h", description="Time range for metrics (1h, 6h, 24h, 7d, 30d)", example="1h"),
    metric: str = Query("cpu", description="Metric type to retrieve (cpu, memory, disk, network, sessions)", example="cpu"),
    admin: AdminAccount = Depends(get_current_admin),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Get real-time system metrics
    
    Parameters:
    - timeframe: 1h, 6h, 24h, 7d, 30d
    - metric: cpu, memory, disk, network, sessions
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "metrics:view")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: metrics:view"
            )
        
        # Validate parameters
        valid_timeframes = ["1h", "6h", "24h", "7d", "30d"]
        valid_metrics = ["cpu", "memory", "disk", "network", "sessions"]
        
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timeframe. Must be one of: {valid_timeframes}"
            )
        
        if metric not in valid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metric. Must be one of: {valid_metrics}"
            )
        
        # Log access
        await audit.log_access(
            admin.admin_id,
            "dashboard_metrics",
            f"GET /admin/api/v1/dashboard/metrics?timeframe={timeframe}&metric={metric}"
        )
        
        # Get metrics data
        metrics_data = await _get_metrics_data(timeframe, metric)
        
        return metrics_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics data"
        )


@router.websocket(
    "/stream",
    summary="Dashboard WebSocket stream",
    description="Real-time dashboard updates via WebSocket. Provides live updates for system metrics, session changes, node status updates, blockchain updates, and system alerts"
)
async def dashboard_stream(websocket: WebSocket):
    """
    Real-time dashboard updates via WebSocket
    
    Provides live updates for:
    - System metrics
    - Session changes
    - Node status updates
    - Blockchain updates
    - System alerts
    """
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "data": {"status": "connected"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))
        
        # Start real-time updates
        while True:
            try:
                # Get current metrics
                system_metrics = await _get_realtime_metrics()
                
                # Send metrics update
                message = WebSocketMessage(
                    type="metric_update",
                    data=system_metrics,
                    timestamp=datetime.now(timezone.utc)
                )
                
                await websocket.send_text(message.json())
                
                # Check for alerts
                alerts = await _check_system_alerts()
                if alerts:
                    for alert in alerts:
                        alert_message = WebSocketMessage(
                            type="system_alert",
                            data=alert,
                            timestamp=datetime.now(timezone.utc)
                        )
                        await websocket.send_text(alert_message.json())
                
                # Wait before next update
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Remove connection from list
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


# Helper functions
async def _get_system_status() -> SystemStatus:
    """Get system status information"""
    try:
        # This would integrate with actual system monitoring
        return SystemStatus(
            status="healthy",
            uptime="7 days, 12 hours, 34 minutes",
            version="1.0.0",
            last_updated=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return SystemStatus(
            status="unknown",
            uptime="unknown",
            version="1.0.0",
            last_updated=datetime.now(timezone.utc)
        )


async def _get_active_sessions() -> ActiveSessions:
    """Get active sessions information"""
    try:
        # This would query the session management service
        return ActiveSessions(
            total=150,
            active=120,
            idle=30,
            by_type={
                "rdp": 100,
                "vnc": 20,
                "ssh": 30
            }
        )
    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        return ActiveSessions(
            total=0,
            active=0,
            idle=0,
            by_type={}
        )


async def _get_node_status() -> NodeStatus:
    """Get node status information"""
    try:
        # This would query the node management service
        return NodeStatus(
            total_nodes=25,
            online_nodes=23,
            offline_nodes=2,
            load_average=0.75
        )
    except Exception as e:
        logger.error(f"Failed to get node status: {e}")
        return NodeStatus(
            total_nodes=0,
            online_nodes=0,
            offline_nodes=0,
            load_average=0.0
        )


async def _get_blockchain_status() -> BlockchainStatus:
    """Get blockchain status information"""
    try:
        # This would query the blockchain service
        return BlockchainStatus(
            network_height=1234567,
            sync_status="synced",
            pending_transactions=15
        )
    except Exception as e:
        logger.error(f"Failed to get blockchain status: {e}")
        return BlockchainStatus(
            network_height=0,
            sync_status="unknown",
            pending_transactions=0
        )


async def _get_resource_usage() -> ResourceUsage:
    """Get resource usage information"""
    try:
        # This would query system metrics
        return ResourceUsage(
            cpu_percentage=45.2,
            memory_percentage=67.8,
            disk_percentage=23.4,
            network_io={
                "bytes_in": 1024000,
                "bytes_out": 2048000
            }
        )
    except Exception as e:
        logger.error(f"Failed to get resource usage: {e}")
        return ResourceUsage(
            cpu_percentage=0.0,
            memory_percentage=0.0,
            disk_percentage=0.0,
            network_io={
                "bytes_in": 0,
                "bytes_out": 0
            }
        )


async def _get_metrics_data(timeframe: str, metric: str) -> List[MetricResponse]:
    """Get metrics data for specified timeframe and metric"""
    try:
        # Calculate time range
        now = datetime.now(timezone.utc)
        time_ranges = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        
        start_time = now - time_ranges[timeframe]
        
        # Generate sample data points
        data_points = []
        interval_minutes = 1 if timeframe == "1h" else 5
        
        current_time = start_time
        while current_time <= now:
            # Generate sample metric value
            import random
            value = random.uniform(0, 100)
            
            data_points.append(MetricDataPoint(
                timestamp=current_time,
                value=value,
                label=f"{metric}_{current_time.strftime('%H:%M')}"
            ))
            
            current_time += timedelta(minutes=interval_minutes)
        
        return [MetricResponse(
            metric_name=metric,
            data_points=data_points,
            time_range=timeframe,
            aggregation="average"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get metrics data: {e}")
        return []


async def _get_realtime_metrics() -> Dict[str, Any]:
    """Get real-time metrics for WebSocket updates"""
    try:
        return {
            "cpu": 45.2,
            "memory": 67.8,
            "disk": 23.4,
            "network_in": 1024000,
            "network_out": 2048000,
            "active_sessions": 120,
            "online_nodes": 23
        }
    except Exception as e:
        logger.error(f"Failed to get real-time metrics: {e}")
        return {}


async def _check_system_alerts() -> List[Dict[str, Any]]:
    """Check for system alerts"""
    try:
        alerts = []
        
        # Check for high CPU usage
        cpu_usage = 45.2  # This would be actual CPU usage
        if cpu_usage > 80:
            alerts.append({
                "type": "high_cpu_usage",
                "severity": "warning",
                "message": f"CPU usage is {cpu_usage}%",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Check for high memory usage
        memory_usage = 67.8  # This would be actual memory usage
        if memory_usage > 90:
            alerts.append({
                "type": "high_memory_usage",
                "severity": "critical",
                "message": f"Memory usage is {memory_usage}%",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to check system alerts: {e}")
        return []


async def broadcast_to_websockets(message: Dict[str, Any]):
    """Broadcast message to all connected WebSocket clients"""
    if not websocket_connections:
        return
    
    message_json = json.dumps(message)
    disconnected = []
    
    for websocket in websocket_connections:
        try:
            await websocket.send_text(message_json)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            disconnected.append(websocket)
    
    # Remove disconnected clients
    for websocket in disconnected:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
