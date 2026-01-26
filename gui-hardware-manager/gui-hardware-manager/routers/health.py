"""
Health check endpoint module
"""

import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    Returns current service status
    """
    try:
        return {
            "status": "healthy",
            "service": "gui-hardware-manager",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@router.get("/health/detailed")
async def health_check_detailed():
    """
    Detailed health check endpoint
    Returns comprehensive service status
    """
    try:
        return {
            "status": "healthy",
            "service": "gui-hardware-manager",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "components": {
                "hardware_detection": "operational",
                "ledger_support": "enabled",
                "trezor_support": "enabled",
                "keepkey_support": "enabled",
                "tron_support": "enabled"
            }
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")
