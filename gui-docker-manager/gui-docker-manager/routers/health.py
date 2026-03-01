"""
Health and Status Routers
File: gui-docker-manager/gui-docker-manager/routers/health.py
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency to get docker manager from app state
async def get_docker_manager():
    """Dependency to get Docker manager instance"""
    from ..main import docker_manager
    if not docker_manager:
        raise HTTPException(status_code=503, detail="Docker Manager not initialized")
    return docker_manager


@router.get("/health")
async def health_check(manager = Depends(get_docker_manager)):
    """Docker Manager and Docker daemon health check"""
    try:
        health = await manager.health_check()
        
        if health.get("status") != "healthy":
            raise HTTPException(status_code=503, detail="Docker Manager unhealthy")
        
        return health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/ready")
async def readiness_check(manager = Depends(get_docker_manager)):
    """Readiness check for Kubernetes"""
    try:
        health = await manager.health_check()
        
        if health.get("status") != "healthy":
            raise HTTPException(status_code=503, detail="Service not ready")
        
        return {
            "status": "ready",
            "service": "gui-docker-manager",
            "message": "Service is ready to handle requests"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/live")
async def liveness_check(manager = Depends(get_docker_manager)):
    """Liveness check for Kubernetes"""
    return {
        "status": "alive",
        "service": "gui-docker-manager",
        "message": "Service is alive"
    }
