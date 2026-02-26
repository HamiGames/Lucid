"""
Health Router for GUI Tor Manager
Provides health check endpoints
"""

from fastapi import APIRouter, HTTPException, status
from ..healthcheck import get_health_check
from ..models.common import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def get_health():
    """
    Get service health status
    
    Returns:
        HealthCheckResponse with service and component status
    """
    health_manager = get_health_check()
    status_data = await health_manager.get_overall_status()
    
    return HealthCheckResponse(
        status=status_data["status"],
        timestamp=status_data["timestamp"],
        service=status_data["service"],
        version=status_data["version"],
        components=status_data["components"],
    )
