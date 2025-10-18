# Path: node/api/resources.py
# Lucid Node Management API - Resource Monitoring Endpoints
# Based on LUCID-STRICT requirements per Spec-1c

"""
Resource monitoring API endpoints for Lucid system.

This module provides REST API endpoints for:
- Node resource utilization monitoring
- Resource metrics collection and retrieval
- Performance analytics
- Resource alerts and thresholds
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
import uuid

from ..models.node import NodeResources, ResourceMetrics, CPUMetrics, MemoryMetrics, DiskMetrics, NetworkMetrics
from ..repositories.node_repository import NodeRepository

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Time range options
class TimeRange(str, Enum):
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"

class MetricType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"

class Granularity(str, Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"

# Dependency for node repository
def get_node_repository() -> NodeRepository:
    """Get node repository instance"""
    return NodeRepository()

@router.get("/{node_id}/resources", response_model=NodeResources)
async def get_node_resources(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    time_range: TimeRange = Query(TimeRange.ONE_HOUR, description="Time range for resource data"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get current resource utilization for a node.
    
    Returns real-time resource metrics including:
    - CPU usage and load averages
    - Memory utilization and swap usage
    - Disk I/O and storage usage
    - Network interface statistics
    - GPU utilization (if available)
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get resource data
        resources = await repository.get_node_resources(node_id, time_range.value)
        
        return resources
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resources for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve node resources"
        )

@router.get("/{node_id}/resources/metrics", response_model=ResourceMetrics)
async def get_resource_metrics(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    metric_type: Optional[MetricType] = Query(None, description="Type of metrics to retrieve"),
    granularity: Granularity = Query(Granularity.FIVE_MINUTES, description="Data granularity"),
    start_time: Optional[datetime] = Query(None, description="Start time for metrics"),
    end_time: Optional[datetime] = Query(None, description="End time for metrics"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get detailed resource metrics for a node.
    
    Returns historical resource metrics with configurable:
    - Time range (start_time to end_time)
    - Metric type (CPU, memory, disk, network, GPU)
    - Data granularity (1m, 5m, 15m, 1h)
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(hours=1)
        
        # Validate time range
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be before end time"
            )
        
        # Get metrics
        metrics = await repository.get_resource_metrics(
            node_id=node_id,
            metric_type=metric_type.value if metric_type else None,
            granularity=granularity.value,
            start_time=start_time,
            end_time=end_time
        )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource metrics"
        )

@router.get("/{node_id}/resources/cpu", response_model=CPUMetrics)
async def get_cpu_metrics(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    time_range: TimeRange = Query(TimeRange.ONE_HOUR, description="Time range for CPU data"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get CPU-specific metrics for a node.
    
    Returns detailed CPU metrics including:
    - CPU usage percentage
    - Core count and frequency
    - Load averages (1min, 5min, 15min)
    - Temperature readings
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get CPU metrics
        cpu_metrics = await repository.get_cpu_metrics(node_id, time_range.value)
        
        return cpu_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get CPU metrics for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve CPU metrics"
        )

@router.get("/{node_id}/resources/memory", response_model=MemoryMetrics)
async def get_memory_metrics(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    time_range: TimeRange = Query(TimeRange.ONE_HOUR, description="Time range for memory data"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get memory-specific metrics for a node.
    
    Returns detailed memory metrics including:
    - Total, used, and free memory
    - Cached and buffer memory
    - Swap usage
    - Memory utilization trends
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get memory metrics
        memory_metrics = await repository.get_memory_metrics(node_id, time_range.value)
        
        return memory_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory metrics for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory metrics"
        )

@router.get("/{node_id}/resources/disk", response_model=DiskMetrics)
async def get_disk_metrics(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    time_range: TimeRange = Query(TimeRange.ONE_HOUR, description="Time range for disk data"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get disk-specific metrics for a node.
    
    Returns detailed disk metrics including:
    - Disk usage and free space
    - Read/write IOPS
    - Throughput (MB/s)
    - Disk health indicators
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get disk metrics
        disk_metrics = await repository.get_disk_metrics(node_id, time_range.value)
        
        return disk_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get disk metrics for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve disk metrics"
        )

@router.get("/{node_id}/resources/network", response_model=NetworkMetrics)
async def get_network_metrics(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    time_range: TimeRange = Query(TimeRange.ONE_HOUR, description="Time range for network data"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get network-specific metrics for a node.
    
    Returns detailed network metrics including:
    - Interface statistics
    - Bytes in/out
    - Packet counts
    - Error rates
    - Bandwidth utilization
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get network metrics
        network_metrics = await repository.get_network_metrics(node_id, time_range.value)
        
        return network_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get network metrics for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve network metrics"
        )

@router.get("/{node_id}/resources/alerts", response_model=List[Dict[str, Any]])
async def get_resource_alerts(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    severity: Optional[str] = Query(None, description="Filter by alert severity"),
    active_only: bool = Query(True, description="Return only active alerts"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get resource alerts for a node.
    
    Returns alerts triggered by resource thresholds including:
    - High CPU usage
    - Low memory availability
    - Disk space warnings
    - Network connectivity issues
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get alerts
        alerts = await repository.get_resource_alerts(
            node_id=node_id,
            severity=severity,
            active_only=active_only
        )
        
        return alerts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alerts for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource alerts"
        )

@router.post("/{node_id}/resources/thresholds", response_model=Dict[str, Any])
async def set_resource_thresholds(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    thresholds: Dict[str, Any] = ...,
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Set resource monitoring thresholds for a node.
    
    Configures alert thresholds for:
    - CPU usage percentage
    - Memory usage percentage
    - Disk usage percentage
    - Network error rates
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Validate thresholds
        required_fields = ["cpu_percent", "memory_percent", "disk_percent"]
        for field in required_fields:
            if field not in thresholds:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required threshold: {field}"
                )
            
            value = thresholds[field]
            if not isinstance(value, (int, float)) or value < 0 or value > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid threshold value for {field}: must be between 0 and 100"
                )
        
        # Set thresholds
        await repository.set_resource_thresholds(node_id, thresholds)
        
        logger.info(f"Set resource thresholds for node {node_id}")
        return {
            "node_id": node_id,
            "thresholds": thresholds,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set thresholds for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set resource thresholds"
        )

@router.get("/{node_id}/resources/summary", response_model=Dict[str, Any])
async def get_resource_summary(
    node_id: str = Path(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$"),
    time_range: TimeRange = Query(TimeRange.TWENTY_FOUR_HOURS, description="Time range for summary"),
    repository: NodeRepository = Depends(get_node_repository)
):
    """
    Get resource utilization summary for a node.
    
    Returns aggregated resource statistics including:
    - Average and peak utilization
    - Resource trends
    - Performance insights
    - Capacity planning data
    """
    try:
        # Check if node exists
        node = await repository.get_node(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
            )
        
        # Get summary
        summary = await repository.get_resource_summary(node_id, time_range.value)
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resource summary for node {node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resource summary"
        )
