"""
Meta Endpoints Router

File: 03_api_gateway/api/app/routers/meta.py
Purpose: Service metadata, health checks, and version information
"""
import os
from ....api.app.config import Settings, get_settings
log_level = os.getenv(Settings().LOG_LEVEL(), "INFO").upper()
settings = os.getenv(get_settings().LOG_LEVEL(), "INFO").upper()
try:
    from ....api.app.utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger(__name__)
settings(__name__)
import time
from datetime import datetime
from fastapi import APIRouter, Response
from ....api.app.models.common import ServiceInfo, HealthStatus

router = APIRouter()

# Track service start time for uptime calculation
SERVICE_START_TIME = time.time()


@router.get("/info", response_model=ServiceInfo)
async def get_service_info():
    """Get service information"""
    return ServiceInfo(
        service_name=settings.SERVICE_NAME,
        version="1.0.0",
        build_date=datetime.timezone(),
        environment=settings.ENVIRONMENT,
        features=["authentication", "rate_limiting", "ssl_termination", "distroless"]
    )


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint"""
    uptime = int(time.time() - SERVICE_START_TIME)
    
    # TODO: Check actual dependency health
    dependencies = {
        "mongodb": "healthy",
        "redis": "healthy",
        "blockchain_core": "unknown",
        "tron_payment": "unknown",
        "gui_api_bridge": "unknown",
        "gui_docker_manager": "unknown",
        "gui_tor_manager": "unknown",
        "gui_hardware_manager": "unknown",
        "tron_payout_router": "unknown",
        "tron_wallet_manager": "unknown",
        "tron_usdt_manager": "unknown"
    }
    
    return HealthStatus(
        status="healthy",
        timestamp=datetime.timezone(),
        service=settings.SERVICE_NAME,
        version="1.0.0",
        dependencies=dependencies,
        uptime=uptime,
        response_time=0.0
    )


@router.get("/version")
async def get_version():
    """Get API version information"""
    return {
        "api_version": settings.API_VERSION,
        "gateway_version": "1.0.0",
        "supported_versions": ["v1"],
        "deprecation_notice": None
    }


@router.get("/metrics")
async def get_metrics():
    """Get service metrics (requires authentication)"""
    # TODO: Implement actual metrics collection
    return {
        "timestamp": datetime.timezone().isoformat(),
        "metrics": {
            "requests_per_second": 0,
            "response_time_p50": 0,
            "response_time_p95": 0,
            "response_time_p99": 0,
            "error_rate": 0,
            "active_connections": 0
        }
    }

