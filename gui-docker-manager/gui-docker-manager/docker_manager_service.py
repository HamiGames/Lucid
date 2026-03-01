"""
Core Docker Manager Service
File: gui-docker-manager/gui-docker-manager/docker_manager_service.py
"""

import logging
from typing import Dict, List, Any, Optional
from .integration.docker_client import DockerClientAsync
from .config import DockerManagerConfigManager

logger = logging.getLogger(__name__)


class DockerManagerService:
    """Main service for Docker container management"""
    
    def __init__(self, config: DockerManagerConfigManager):
        """
        Initialize Docker Manager Service
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.docker_client: Optional[DockerClientAsync] = None
    
    async def initialize(self):
        """Initialize Docker client connection"""
        try:
            self.docker_client = DockerClientAsync(
                base_url=self.config.settings.DOCKER_HOST,
                timeout=30.0,
                retry_count=3,
                retry_delay=1.0
            )
            logger.info("Docker Manager Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service and Docker daemon health"""
        try:
            if not self.docker_client:
                return {
                    "status": "unhealthy",
                    "error": "Docker client not initialized",
                }
            
            docker_health = await self.docker_client.health_check()
            
            return {
                "status": "healthy" if docker_health.get("status") == "healthy" else "unhealthy",
                "docker": docker_health,
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }
    
    async def list_containers(self, all: bool = False) -> List[Dict[str, Any]]:
        """
        List Docker containers
        
        Args:
            all: Include stopped containers
            
        Returns:
            List of container dictionaries
        """
        if not self.docker_client:
            raise RuntimeError("Docker client not initialized")
        
        return await self.docker_client.list_containers(all=all)
    
    async def get_container(self, container_id: str) -> Dict[str, Any]:
        """
        Get container details
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Container information dictionary
        """
        if not self.docker_client:
            raise RuntimeError("Docker client not initialized")
        
        return await self.docker_client.get_container(container_id)
    
    async def start_container(self, container_id: str) -> Dict[str, Any]:
        """
        Start a container
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Operation result
        """
        if not self.docker_client:
            raise RuntimeError("Docker client not initialized")
        
        return await self.docker_client.start_container(container_id)
    
    async def stop_container(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Stop a container
        
        Args:
            container_id: Container ID or name
            timeout: Shutdown timeout in seconds
            
        Returns:
            Operation result
        """
        if not self.docker_client:
            raise RuntimeError("Docker client not initialized")
        
        return await self.docker_client.stop_container(container_id, timeout=timeout)
    
    async def restart_container(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Restart a container
        
        Args:
            container_id: Container ID or name
            timeout: Shutdown timeout in seconds
            
        Returns:
            Operation result
        """
        if not self.docker_client:
            raise RuntimeError("Docker client not initialized")
        
        return await self.docker_client.restart_container(container_id, timeout=timeout)
    
    async def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """
        Get container logs
        
        Args:
            container_id: Container ID or name
            tail: Number of log lines to retrieve
            
        Returns:
            Log output as string
        """
        if not self.docker_client:
            raise RuntimeError("Docker client not initialized")
        
        return await self.docker_client.get_logs(container_id, tail=tail)
    
    async def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """
        Get container statistics
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Container statistics
        """
        if not self.docker_client:
            raise RuntimeError("Docker client not initialized")
        
        return await self.docker_client.get_stats(container_id)
    
    async def close(self):
        """Close Docker client connection"""
        if self.docker_client:
            await self.docker_client.close()
            logger.info("Docker Manager Service closed")
