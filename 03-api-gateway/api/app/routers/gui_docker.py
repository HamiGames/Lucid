"""
GUI Docker Manager Proxy Endpoints Router

File: 03-api-gateway/api/app/routers/gui_docker.py
Purpose: Proxy endpoints to gui-docker-manager service for Docker management via GUI

Architecture Note: This router proxies to gui-docker-manager service
"""

import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/info")
async def get_gui_docker_manager_info():
    """Get GUI Docker Manager service information"""
    try:
        from app.services.gui_docker_manager_service import gui_docker_manager_service
        await gui_docker_manager_service.initialize()
        info = await gui_docker_manager_service.get_manager_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get GUI Docker Manager info: {e}")
        raise HTTPException(status_code=503, detail=f"GUI Docker Manager unavailable: {str(e)}")


@router.get("/health")
async def check_gui_docker_manager_health():
    """Check GUI Docker Manager service health"""
    try:
        from app.services.gui_docker_manager_service import gui_docker_manager_service
        is_healthy = await gui_docker_manager_service.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "gui-docker-manager",
            "connected": is_healthy
        }
    except Exception as e:
        logger.error(f"GUI Docker Manager health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "gui-docker-manager",
            "connected": False,
            "error": str(e)
        }


@router.get("/containers")
async def list_containers():
    """List Docker containers via GUI Docker Manager"""
    try:
        from app.services.gui_docker_manager_service import gui_docker_manager_service
        await gui_docker_manager_service.initialize()
        containers = await gui_docker_manager_service.list_containers()
        return containers
    except Exception as e:
        logger.error(f"Failed to list containers: {e}")
        raise HTTPException(status_code=503, detail=f"Container listing failed: {str(e)}")


@router.get("/containers/{container_id}")
async def get_container_details(container_id: str):
    """Get Docker container details via GUI Docker Manager"""
    try:
        from app.services.gui_docker_manager_service import gui_docker_manager_service
        await gui_docker_manager_service.initialize()
        details = await gui_docker_manager_service.get_container_details(container_id)
        return details
    except Exception as e:
        logger.error(f"Failed to get container details: {e}")
        raise HTTPException(status_code=503, detail=f"Container details failed: {str(e)}")


@router.post("/containers/{container_id}/start")
async def start_container(container_id: str):
    """Start Docker container via GUI Docker Manager"""
    try:
        from app.services.gui_docker_manager_service import gui_docker_manager_service
        await gui_docker_manager_service.initialize()
        result = await gui_docker_manager_service.start_container(container_id)
        logger.info(f"Container started: {container_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to start container: {e}")
        raise HTTPException(status_code=503, detail=f"Container start failed: {str(e)}")


@router.post("/containers/{container_id}/stop")
async def stop_container(container_id: str):
    """Stop Docker container via GUI Docker Manager"""
    try:
        from app.services.gui_docker_manager_service import gui_docker_manager_service
        await gui_docker_manager_service.initialize()
        result = await gui_docker_manager_service.stop_container(container_id)
        logger.info(f"Container stopped: {container_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to stop container: {e}")
        raise HTTPException(status_code=503, detail=f"Container stop failed: {str(e)}")
