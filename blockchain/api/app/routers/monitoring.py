"""
Monitoring Router

This module contains monitoring and metrics endpoints.
Provides health checks, metrics, and system monitoring capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import logging

from ..dependencies import get_current_user, verify_api_key, require_read_permission
from ..health_check import health_check_service
from ..metrics import metrics_service
from ..monitoring import metrics_collector, performance_monitor

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
    responses={404: {"description": "Monitoring data not found"}},
)

logger = logging.getLogger(__name__)

@router.get("/health", response_model=Dict[str, Any])
async def get_health_status(
    user = Depends(require_read_permission)
):
    """
    Get comprehensive health status of the system.
    
    Returns detailed health information including:
    - Overall system health status
    - Individual component health checks
    - System uptime and performance metrics
    - Health check results and timestamps
    
    Health status values:
    - healthy: All systems operating normally
    - warning: Some issues detected, system functional
    - error: Critical issues detected, system may be degraded
    """
    try:
        logger.info("Fetching comprehensive health status")
        health_status = await health_check_service.get_health_status()
        return health_status
    except Exception as e:
        logger.error(f"Failed to fetch health status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve health status"
        )

@router.get("/health/quick", response_model=Dict[str, Any])
async def get_quick_health_status(
    user = Depends(require_read_permission)
):
    """
    Get quick health status using cached results.
    
    Returns a lightweight health status for:
    - Load balancer health checks
    - Quick system status monitoring
    - High-frequency health monitoring
    
    Provides basic health information without detailed checks.
    """
    try:
        logger.info("Fetching quick health status")
        health_status = await health_check_service.get_quick_health_status()
        return health_status
    except Exception as e:
        logger.error(f"Failed to fetch quick health status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quick health status"
        )

@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics_summary(
    user = Depends(require_read_permission)
):
    """
    Get comprehensive metrics summary.
    
    Returns system and API metrics including:
    - API performance metrics
    - Blockchain metrics
    - System resource metrics
    - Error rates and response times
    - Throughput and capacity metrics
    """
    try:
        logger.info("Fetching metrics summary")
        metrics_summary = metrics_service.get_metrics_summary()
        return metrics_summary
    except Exception as e:
        logger.error(f"Failed to fetch metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics summary"
        )

@router.get("/metrics/prometheus")
async def get_prometheus_metrics(
    user = Depends(require_read_permission)
):
    """
    Get metrics in Prometheus format.
    
    Returns metrics formatted for Prometheus scraping:
    - Counter metrics
    - Gauge metrics
    - Histogram metrics
    - Custom metrics
    
    Compatible with Prometheus monitoring systems.
    """
    try:
        logger.info("Fetching Prometheus metrics")
        prometheus_metrics = metrics_service.get_prometheus_metrics()
        return prometheus_metrics
    except Exception as e:
        logger.error(f"Failed to fetch Prometheus metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Prometheus metrics"
        )

@router.get("/metrics/dashboard", response_model=Dict[str, Any])
async def get_dashboard_metrics(
    user = Depends(require_read_permission)
):
    """
    Get metrics formatted for dashboard display.
    
    Returns key metrics optimized for dashboard visualization:
    - API performance indicators
    - Blockchain status metrics
    - System resource usage
    - Error rates and response times
    
    Suitable for real-time dashboard displays.
    """
    try:
        logger.info("Fetching dashboard metrics")
        dashboard_metrics = metrics_service.get_metrics_for_dashboard()
        return dashboard_metrics
    except Exception as e:
        logger.error(f"Failed to fetch dashboard metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard metrics"
        )

@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_metrics(
    user = Depends(require_read_permission)
):
    """
    Get detailed performance metrics.
    
    Returns performance information including:
    - Endpoint performance statistics
    - Response time percentiles
    - Request throughput
    - Error rates by endpoint
    - Performance trends
    
    Useful for performance analysis and optimization.
    """
    try:
        logger.info("Fetching performance metrics")
        performance_metrics = performance_monitor.get_all_endpoint_metrics()
        return {
            "timestamp": metrics_collector.start_time.isoformat(),
            "performance_metrics": performance_metrics
        }
    except Exception as e:
        logger.error(f"Failed to fetch performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )

@router.get("/system", response_model=Dict[str, Any])
async def get_system_metrics(
    user = Depends(require_read_permission)
):
    """
    Get system resource metrics.
    
    Returns system resource information including:
    - CPU usage and load
    - Memory usage and availability
    - Disk usage and I/O
    - Network I/O statistics
    - Database connection metrics
    - Redis connection metrics
    
    Useful for system monitoring and capacity planning.
    """
    try:
        logger.info("Fetching system metrics")
        system_metrics = metrics_collector.collect_system_metrics()
        return {
            "timestamp": system_metrics.timestamp.isoformat(),
            "system_metrics": system_metrics.__dict__
        }
    except Exception as e:
        logger.error(f"Failed to fetch system metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics"
        )
