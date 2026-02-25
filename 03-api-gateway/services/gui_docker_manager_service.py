"""
GUI Docker Manager Service

File: 03-api-gateway/services/gui_docker_manager_service.py
Purpose: Service for handling GUI Docker Manager integration and proxy operations
"""

import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GuiDockerManagerServiceError(Exception):
    """GUI Docker Manager service error"""
    pass


class GuiDockerManagerService:
    """Service for managing GUI Docker Manager integration"""
    
    def __init__(self):
        """Initialize GUI Docker Manager service"""
        self.base_url = settings.GUI_DOCKER_MANAGER_URL
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        self.last_check: Optional[datetime] = None
        
    async def initialize(self):
        """Initialize HTTP session"""
        try:
            if not self.http_session:
                timeout = aiohttp.ClientTimeout(total=10, connect=5)
                connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
                self.http_session = aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector
                )
            logger.info(f"GUI Docker Manager service initialized with URL: {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize GUI Docker Manager service: {e}")
            raise GuiDockerManagerServiceError(f"Failed to initialize: {e}")
    
    async def close(self):
        """Close HTTP session"""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            logger.info("GUI Docker Manager service session closed")
    
    async def health_check(self) -> bool:
        """Check service health"""
        if not self.base_url:
            logger.warning("GUI_DOCKER_MANAGER_URL not configured")
            return False
        
        try:
            await self.initialize()
            
            async with self.http_session.get(
                f"{self.base_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self.last_check = datetime.utcnow()
                self.is_connected = response.status == 200
                return self.is_connected
                
        except Exception as e:
            logger.warning(f"GUI Docker Manager health check failed: {e}")
            self.is_connected = False
            return False
    
    async def get_manager_info(self) -> Dict[str, Any]:
        """Get manager information"""
        if not self.is_connected:
            raise GuiDockerManagerServiceError("GUI Docker Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiDockerManagerServiceError(f"Failed to get info: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get GUI Docker Manager info: {e}")
            raise GuiDockerManagerServiceError(f"Failed to get info: {e}")
    
    async def list_containers(self) -> Dict[str, Any]:
        """List Docker containers"""
        if not self.is_connected:
            raise GuiDockerManagerServiceError("GUI Docker Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/containers") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiDockerManagerServiceError(f"Failed to list containers: {response.status}")
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            raise GuiDockerManagerServiceError(f"Failed to list containers: {e}")
    
    async def get_container_details(self, container_id: str) -> Dict[str, Any]:
        """Get container details"""
        if not self.is_connected:
            raise GuiDockerManagerServiceError("GUI Docker Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/containers/{container_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiDockerManagerServiceError(f"Failed to get container: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get container details: {e}")
            raise GuiDockerManagerServiceError(f"Failed to get container: {e}")
    
    async def start_container(self, container_id: str) -> Dict[str, Any]:
        """Start a container"""
        if not self.is_connected:
            raise GuiDockerManagerServiceError("GUI Docker Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.post(
                f"{self.base_url}/containers/{container_id}/start"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiDockerManagerServiceError(f"Failed to start container: {response.status}")
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            raise GuiDockerManagerServiceError(f"Failed to start container: {e}")
    
    async def stop_container(self, container_id: str) -> Dict[str, Any]:
        """Stop a container"""
        if not self.is_connected:
            raise GuiDockerManagerServiceError("GUI Docker Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.post(
                f"{self.base_url}/containers/{container_id}/stop"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiDockerManagerServiceError(f"Failed to stop container: {response.status}")
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            raise GuiDockerManagerServiceError(f"Failed to stop container: {e}")


# Global service instance
gui_docker_manager_service = GuiDockerManagerService()
