"""
Network Management Routers
File: gui-docker-manager/gui-docker-manager/routers/networks.py

REST API endpoints for Docker network management.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_docker_manager():
    """Dependency to get Docker manager instance"""
    from ..main import docker_manager
    if not docker_manager:
        raise HTTPException(status_code=503, detail="Docker Manager not initialized")
    return docker_manager


@router.get("")
async def list_networks(
    driver: Optional[str] = None,
    manager=Depends(get_docker_manager)
):
    """
    List all Docker networks

    Query Parameters:
    - driver: Optional filter by network driver (bridge/overlay/host/macvlan)
    """
    try:
        filters = {}
        if driver:
            filters["driver"] = driver

        from ..services.network_service import NetworkService
        network_service = NetworkService(manager.docker_client)
        networks = await network_service.list_networks(filters=filters)

        return {
            "status": "success",
            "data": [net.dict() for net in networks],
            "count": len(networks)
        }
    except Exception as e:
        logger.error(f"Failed to list networks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{network_id}")
async def get_network(
    network_id: str,
    manager=Depends(get_docker_manager)
):
    """Get details for a specific network"""
    try:
        from ..services.network_service import NetworkService
        network_service = NetworkService(manager.docker_client)
        network = await network_service.get_network(network_id)

        return {
            "status": "success",
            "data": network.dict()
        }
    except Exception as e:
        logger.error(f"Failed to get network {network_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_network(
    name: str,
    driver: str = "bridge",
    labels: Optional[Dict[str, str]] = None,
    manager=Depends(get_docker_manager)
):
    """
    Create a new Docker network

    Parameters:
    - name: Network name (required)
    - driver: Network driver (default: bridge)
    - labels: Optional network labels
    """
    try:
        from ..services.network_service import NetworkService
        network_service = NetworkService(manager.docker_client)
        result = await network_service.create_network(
            name=name,
            driver=driver,
            labels=labels
        )

        return {
            "status": "success",
            "message": f"Network {name} created successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to create network {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{network_id}")
async def remove_network(
    network_id: str,
    manager=Depends(get_docker_manager)
):
    """Remove a Docker network"""
    try:
        from ..services.network_service import NetworkService
        network_service = NetworkService(manager.docker_client)
        result = await network_service.remove_network(network_id)

        return {
            "status": "success",
            "message": f"Network {network_id} removed successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to remove network {network_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{network_id}/connect")
async def connect_container(
    network_id: str,
    container_id: str,
    ip_address: Optional[str] = None,
    manager=Depends(get_docker_manager)
):
    """Connect a container to a network"""
    try:
        from ..services.network_service import NetworkService
        network_service = NetworkService(manager.docker_client)
        result = await network_service.connect_container(
            network_id=network_id,
            container_id=container_id,
            ip_address=ip_address
        )

        return {
            "status": "success",
            "message": f"Container {container_id} connected to network {network_id}",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to connect container {container_id} to network {network_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{network_id}/disconnect")
async def disconnect_container(
    network_id: str,
    container_id: str,
    force: bool = False,
    manager=Depends(get_docker_manager)
):
    """Disconnect a container from a network"""
    try:
        from ..services.network_service import NetworkService
        network_service = NetworkService(manager.docker_client)
        result = await network_service.disconnect_container(
            network_id=network_id,
            container_id=container_id,
            force=force
        )

        return {
            "status": "success",
            "message": f"Container {container_id} disconnected from network {network_id}",
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to disconnect container {container_id} from network {network_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
