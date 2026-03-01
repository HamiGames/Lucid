"""
Volume Management Routers
File: gui-docker-manager/gui-docker-manager/routers/volumes.py

REST API endpoints for Docker volume management.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_docker_manager():
    """Dependency to get Docker manager instance"""
    from ..main import docker_manager
    if not docker_manager:
        raise HTTPException(status_code=503, detail="Docker Manager not initialized")
    return docker_manager


@router.get("")
async def list_volumes(
    manager=Depends(get_docker_manager)
):
    """List all Docker volumes"""
    try:
        from ..services.volume_service import VolumeService
        volume_service = VolumeService(manager.docker_client)
        volumes = await volume_service.list_volumes()

        return {
            "status": "success",
            "data": [vol.dict() for vol in volumes],
            "count": len(volumes)
        }
    except Exception as e:
        logger.error(f"Failed to list volumes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{volume_name}")
async def get_volume(
    volume_name: str,
    manager=Depends(get_docker_manager)
):
    """Get details for a specific volume"""
    try:
        from ..services.volume_service import VolumeService
        volume_service = VolumeService(manager.docker_client)
        volume = await volume_service.get_volume(volume_name)

        return {
            "status": "success",
            "data": volume.dict()
        }
    except Exception as e:
        logger.error(f"Failed to get volume {volume_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_volume(
    name: str,
    driver: str = "local",
    driver_options: Optional[Dict[str, str]] = None,
    labels: Optional[Dict[str, str]] = None,
    manager=Depends(get_docker_manager)
):
    """
    Create a new Docker volume

    Parameters:
    - name: Volume name (required)
    - driver: Volume driver (default: local)
    - driver_options: Optional driver options
    - labels: Optional volume labels
    """
    try:
        from ..services.volume_service import VolumeService
        volume_service = VolumeService(manager.docker_client)
        result = await volume_service.create_volume(
            name=name,
            driver=driver,
            driver_options=driver_options,
            labels=labels
        )

        return {
            "status": "success",
            "message": f"Volume {name} created successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to create volume {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{volume_name}")
async def remove_volume(
    volume_name: str,
    force: bool = False,
    manager=Depends(get_docker_manager)
):
    """
    Remove a Docker volume

    Parameters:
    - volume_name: Volume name to remove
    - force: Force removal even if in use (default: false)
    """
    try:
        from ..services.volume_service import VolumeService
        volume_service = VolumeService(manager.docker_client)
        result = await volume_service.remove_volume(volume_name, force=force)

        return {
            "status": "success",
            "message": f"Volume {volume_name} removed successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to remove volume {volume_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prune")
async def prune_volumes(
    manager=Depends(get_docker_manager)
):
    """Prune unused volumes"""
    try:
        from ..services.volume_service import VolumeService
        volume_service = VolumeService(manager.docker_client)
        result = await volume_service.prune_volumes()

        return {
            "status": "success",
            "message": "Volumes pruned successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to prune volumes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
