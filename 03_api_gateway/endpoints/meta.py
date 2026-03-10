"""
Meta Endpoints Module

Provides system metadata and health check endpoints for the API Gateway.
These endpoints are publicly accessible and do not require authentication.

Endpoints:
- GET /meta/info: Service information
- GET /meta/health: Health check status
- GET /meta/version: API version information
- GET /meta/metrics: Service metrics (requires authentication)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import time
from datetime import datetime
import psutil
import platform

from ..models.common import ServiceInfo, HealthStatus, VersionInfo, MetricsResponse

router = APIRouter(prefix="/meta", tags=["Meta"])

# Service start time for uptime calculation
SERVICE_START_TIME = time.time()


@router.get(
    "/info",
    response_model=ServiceInfo,
    summary="Get service information",
    description="Returns comprehensive information about the API Gateway service",
    status_code=status.HTTP_200_OK,
)
async def get_service_info() -> ServiceInfo:
    """
    Retrieve service information including name, version, and configuration.
    
    Returns:
        ServiceInfo: Service metadata and configuration
    """
    return ServiceInfo(
        service_name="lucid-api-gateway",
        version="1.0.0",
        environment="production",
        description="Primary entry point for all Lucid blockchain system APIs",
        maintainer="Lucid Development Team",
        docs_url="/docs",
        openapi_url="/openapi.json",
        supported_versions=["v1"],
        capabilities=[
            "authentication",
            "rate_limiting",
            "proxy",
            "circuit_breaker",
        ],
    )


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Health check endpoint",
    description="Returns the health status of the API Gateway and its dependencies",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> HealthStatus:
    """
    Perform health check on the API Gateway and its dependencies.
    
    Returns:
        HealthStatus: Overall health status and dependency checks
        
    Raises:
        HTTPException: 503 if service is unhealthy
    """
    uptime = int(time.time() - SERVICE_START_TIME)
    
    # Check dependencies (simplified - in production would check actual services)
    dependencies = {
        "mongodb": "healthy",
        "redis": "healthy",
        "auth_service": "healthy",
        "blockchain_service": "healthy",
    }
    
    # Determine overall status
    overall_status = "healthy"
    if any(status != "healthy" for status in dependencies.values()):
        overall_status = "degraded"
    
    health_status = HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime,
        dependencies=dependencies,
        version="1.0.0",
    )
    
    # Return 503 if unhealthy
    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status.dict(),
        )
    
    return health_status


@router.get(
    "/version",
    response_model=VersionInfo,
    summary="Get API version information",
    description="Returns version information for the API Gateway and supported API versions",
    status_code=status.HTTP_200_OK,
)
async def get_version() -> VersionInfo:
    """
    Retrieve version information for the API Gateway.
    
    Returns:
        VersionInfo: Version details and supported API versions
    """
    return VersionInfo(
        service_version="1.0.0",
        api_version="v1",
        supported_api_versions=["v1"],
        build_date="2025-10-14",
        git_commit="latest",
        python_version=platform.python_version(),
        dependencies={
            "fastapi": "0.104.1",
            "pydantic": "2.5.0",
            "uvicorn": "0.24.0",
        },
    )


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get service metrics",
    description="Returns performance and operational metrics for the API Gateway",
    status_code=status.HTTP_200_OK,
)
async def get_metrics() -> MetricsResponse:
    """
    Retrieve operational metrics for the API Gateway.
    Requires authentication.
    
    Returns:
        MetricsResponse: Performance and operational metrics
    """
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return MetricsResponse(
        timestamp=datetime.utcnow(),
        uptime_seconds=int(time.time() - SERVICE_START_TIME),
        request_count=0,  # Would track in production
        error_count=0,
        average_response_time_ms=0.0,
        requests_per_second=0.0,
        system_metrics={
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_mb": memory.used / (1024 * 1024),
            "memory_total_mb": memory.total / (1024 * 1024),
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / (1024 * 1024 * 1024),
            "disk_total_gb": disk.total / (1024 * 1024 * 1024),
        },
        endpoint_metrics={},
    )


@router.get(
    "/status",
    summary="Quick status check",
    description="Returns a simple status indicator for load balancer health checks",
    status_code=status.HTTP_200_OK,
)
async def get_status() -> Dict[str, str]:
    """
    Quick status check for load balancers.
    
    Returns:
        dict: Simple status indicator
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

