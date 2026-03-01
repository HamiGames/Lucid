"""
Container Service Business Logic
File: gui-docker-manager/gui-docker-manager/services/container_service.py
"""

import logging
from typing import Dict, List, Any, Optional
from ..integration.docker_client import DockerClientAsync

logger = logging.getLogger(__name__)


class ContainerService:
    """Business logic for container operations"""
    
    def __init__(self, docker_client: DockerClientAsync):
        """Initialize container service"""
        self.docker_client = docker_client
    
    async def list_containers(self, all: bool = False, filter_by: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List containers with optional filtering"""
        containers = await self.docker_client.list_containers(all=all)
        
        if filter_by:
            # Apply filters
            if "status" in filter_by:
                containers = [c for c in containers if c.get("status") == filter_by["status"]]
            if "image" in filter_by:
                containers = [c for c in containers if filter_by["image"] in c.get("image", "")]
        
        return containers
    
    async def get_container_info(self, container_id: str) -> Dict[str, Any]:
        """Get detailed container information"""
        return await self.docker_client.get_container(container_id)
    
    async def start_container_safe(self, container_id: str) -> Dict[str, Any]:
        """Start container with error handling"""
        logger.info(f"Starting container: {container_id}")
        return await self.docker_client.start_container(container_id)
    
    async def stop_container_safe(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """Stop container with error handling"""
        logger.info(f"Stopping container: {container_id} with timeout {timeout}s")
        return await self.docker_client.stop_container(container_id, timeout=timeout)
    
    async def restart_container_safe(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """Restart container with error handling"""
        logger.info(f"Restarting container: {container_id}")
        return await self.docker_client.restart_container(container_id, timeout=timeout)
    
    async def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """Get container logs"""
        return await self.docker_client.get_logs(container_id, tail=tail)
    
    async def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get container statistics"""
        return await self.docker_client.get_stats(container_id)
