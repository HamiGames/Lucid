"""
Health check endpoint module
Provides service health status and component status
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from gui_hardware_manager.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint - basic service status
    Returns: Service status and timestamp
    """
    try:
        settings = get_settings()
        
        return {
            "status": "healthy",
            "service": settings.SERVICE_NAME,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "port": settings.PORT,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@router.get("/health/detailed")
async def health_check_detailed(request: Request):
    """
    Detailed health check endpoint
    Returns: Comprehensive service and component status
    """
    try:
        settings = get_settings()
        
        # Get hardware service from app state if available
        hardware_service = None
        if hasattr(request.app, "state") and hasattr(request.app.state, "hardware_service"):
            hardware_service = request.app.state.hardware_service
        
        components_status = {
            "service": "operational",
            "configuration": "valid",
        }
        
        # Check hardware support status
        if settings.HARDWARE_WALLET_ENABLED:
            components_status["hardware_detection"] = "operational"
            components_status["ledger_support"] = "enabled" if settings.LEDGER_ENABLED else "disabled"
            components_status["trezor_support"] = "enabled" if settings.TREZOR_ENABLED else "disabled"
            components_status["keepkey_support"] = "enabled" if settings.KEEPKEY_ENABLED else "disabled"
            components_status["tron_support"] = "enabled" if settings.TRON_WALLET_SUPPORT else "disabled"
        else:
            components_status["hardware_detection"] = "disabled"
        
        # Check optional services
        if settings.MONGODB_URL:
            components_status["mongodb"] = "configured"
        if settings.REDIS_URL:
            components_status["redis"] = "configured"
        if settings.TOR_PROXY_URL:
            components_status["tor_proxy"] = "configured"
        
        return {
            "status": "healthy",
            "service": settings.SERVICE_NAME,
            "version": "1.0.0",
            "environment": settings.LUCID_ENV,
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": {
                "host": settings.HOST,
                "port": settings.PORT,
                "cors_enabled": settings.CORS_ENABLED,
                "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
            },
            "components": components_status,
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")
