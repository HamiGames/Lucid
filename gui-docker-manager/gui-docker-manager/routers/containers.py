"""
Container Management Routers
File: gui-docker-manager/gui-docker-manager/routers/containers.py
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency to get docker manager from app state
async def get_docker_manager():
    """Dependency to get Docker manager instance"""
    from ..main import docker_manager
    if not docker_manager:
        raise HTTPException(status_code=503, detail="Docker Manager not initialized")
    return docker_manager


@router.get("")
async def list_containers(all: bool = False, manager = Depends(get_docker_manager)):
    """List all containers"""
    try:
        containers = await manager.list_containers(all=all)
        return {
            "status": "success",
            "data": containers,
            "count": len(containers)
        }
    except Exception as e:
        logger.error(f"Failed to list containers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{container_id}")
async def get_container(container_id: str, manager = Depends(get_docker_manager)):
    """Get container details"""
    try:
        container = await manager.get_container(container_id)
        return {
            "status": "success",
            "data": container
        }
    except Exception as e:
        logger.error(f"Failed to get container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{container_id}/start")
async def start_container(container_id: str, manager = Depends(get_docker_manager)):
    """Start a container"""
    try:
        result = await manager.start_container(container_id)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to start container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{container_id}/stop")
async def stop_container(container_id: str, timeout: int = 10, manager = Depends(get_docker_manager)):
    """Stop a container"""
    try:
        result = await manager.stop_container(container_id, timeout=timeout)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to stop container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{container_id}/restart")
async def restart_container(container_id: str, timeout: int = 10, manager = Depends(get_docker_manager)):
    """Restart a container"""
    try:
        result = await manager.restart_container(container_id, timeout=timeout)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to restart container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{container_id}/logs")
async def get_container_logs(container_id: str, tail: int = 100, manager = Depends(get_docker_manager)):
    """Get container logs"""
    try:
        logs = await manager.get_container_logs(container_id, tail=tail)
        return {
            "status": "success",
            "data": logs
        }
    except Exception as e:
        logger.error(f"Failed to get logs for container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{container_id}/stats")
async def get_container_stats(container_id: str, manager = Depends(get_docker_manager)):
    """Get container statistics"""
    try:
        stats = await manager.get_container_stats(container_id)
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get stats for container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{container_id}/pause")
async def pause_container(container_id: str, manager = Depends(get_docker_manager)):
    """Pause a running container (freeze its processes)"""
    try:
        result = await manager.pause_container(container_id)
        return {
            "status": "success",
            "message": f"Container {container_id} paused",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to pause container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{container_id}/unpause")
async def unpause_container(container_id: str, manager = Depends(get_docker_manager)):
    """Unpause a paused container (resume its processes)"""
    try:
        result = await manager.unpause_container(container_id)
        return {
            "status": "success",
            "message": f"Container {container_id} unpaused",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to unpause container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{container_id}")
async def remove_container(container_id: str, force: bool = False, manager = Depends(get_docker_manager)):
    """
    Remove a container

    Parameters:
    - container_id: Container ID or name
    - force: Force removal even if running (default: false)
    """
    try:
        result = await manager.remove_container(container_id, force=force)
        return {
            "status": "success",
            "message": f"Container {container_id} removed",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to remove container {container_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
