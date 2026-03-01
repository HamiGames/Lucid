"""
GUI Tor Manager Service

File: 03-api-gateway/api/app/services/gui_tor_manager_service.py
Purpose: Service for handling GUI Tor Manager integration and proxy operations
"""

import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GuiTorManagerServiceError(Exception):
    """GUI Tor Manager service error"""
    pass


class GuiTorManagerService:
    """Service for managing GUI Tor Manager integration"""
    
    def __init__(self):
        """Initialize GUI Tor Manager service"""
        self.base_url = settings.GUI_TOR_MANAGER_URL
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
            logger.info(f"GUI Tor Manager service initialized with URL: {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize GUI Tor Manager service: {e}")
            raise GuiTorManagerServiceError(f"Failed to initialize: {e}")
    
    async def close(self):
        """Close HTTP session"""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            logger.info("GUI Tor Manager service session closed")
    
    async def health_check(self) -> bool:
        """Check service health"""
        if not self.base_url:
            logger.warning("GUI_TOR_MANAGER_URL not configured")
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
            logger.warning(f"GUI Tor Manager health check failed: {e}")
            self.is_connected = False
            return False
    
    async def get_manager_info(self) -> Dict[str, Any]:
        """Get manager information"""
        if not self.is_connected:
            raise GuiTorManagerServiceError("GUI Tor Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiTorManagerServiceError(f"Failed to get info: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get GUI Tor Manager info: {e}")
            raise GuiTorManagerServiceError(f"Failed to get info: {e}")
    
    async def get_tor_status(self) -> Dict[str, Any]:
        """Get Tor status"""
        if not self.is_connected:
            raise GuiTorManagerServiceError("GUI Tor Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiTorManagerServiceError(f"Failed to get status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get Tor status: {e}")
            raise GuiTorManagerServiceError(f"Failed to get status: {e}")
    
    async def list_circuits(self) -> Dict[str, Any]:
        """List Tor circuits"""
        if not self.is_connected:
            raise GuiTorManagerServiceError("GUI Tor Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/circuits") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiTorManagerServiceError(f"Failed to list circuits: {response.status}")
        except Exception as e:
            logger.error(f"Failed to list circuits: {e}")
            raise GuiTorManagerServiceError(f"Failed to list circuits: {e}")
    
    async def request_new_circuit(self) -> Dict[str, Any]:
        """Request new Tor circuit"""
        if not self.is_connected:
            raise GuiTorManagerServiceError("GUI Tor Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.post(f"{self.base_url}/circuits/new") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiTorManagerServiceError(f"Failed to request circuit: {response.status}")
        except Exception as e:
            logger.error(f"Failed to request new circuit: {e}")
            raise GuiTorManagerServiceError(f"Failed to request circuit: {e}")
    
    async def get_onion_address(self) -> Dict[str, Any]:
        """Get Tor onion address"""
        if not self.is_connected:
            raise GuiTorManagerServiceError("GUI Tor Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/onion/address") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiTorManagerServiceError(f"Failed to get onion address: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get onion address: {e}")
            raise GuiTorManagerServiceError(f"Failed to get onion address: {e}")


# Global service instance
gui_tor_manager_service = GuiTorManagerService()
