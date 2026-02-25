"""
GUI API Bridge Service

File: 03-api-gateway/api/app/services/gui_bridge_service.py
Purpose: Service for handling GUI API Bridge integration and proxy operations
Manages communication with gui-api-bridge service for Electron GUI integration
"""

import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GuiBridgeServiceError(Exception):
    """GUI Bridge service error"""
    pass


class GuiBridgeService:
    """
    Service for managing GUI API Bridge integration.
    
    Responsibilities:
    - Proxy requests to gui-api-bridge service
    - Validate GUI bridge connectivity
    - Handle Electron GUI connection lifecycle
    - Manage GUI-specific API routes
    """
    
    def __init__(self):
        """Initialize GUI Bridge service"""
        self.base_url = settings.GUI_API_BRIDGE_URL
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        self.last_check: Optional[datetime] = None
        
    async def initialize(self):
        """Initialize HTTP session for GUI bridge communication"""
        try:
            if not self.http_session:
                timeout = aiohttp.ClientTimeout(total=10, connect=5)
                connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
                self.http_session = aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector
                )
            logger.info(f"GUI Bridge service initialized with URL: {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize GUI Bridge service: {e}")
            raise GuiBridgeServiceError(f"Failed to initialize: {e}")
    
    async def close(self):
        """Close HTTP session"""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            logger.info("GUI Bridge service session closed")
    
    async def health_check(self) -> bool:
        """
        Check GUI Bridge service health
        
        Returns:
            True if service is healthy, False otherwise
        """
        if not self.base_url:
            logger.warning("GUI_API_BRIDGE_URL not configured")
            return False
        
        try:
            await self.initialize()
            
            async with self.http_session.get(
                f"{self.base_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self.last_check = datetime.utcnow()
                self.is_connected = response.status == 200
                logger.info(f"GUI Bridge health check: {response.status}")
                return self.is_connected
                
        except aiohttp.ClientError as e:
            logger.warning(f"GUI Bridge health check failed: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"GUI Bridge health check error: {e}")
            return False
    
    async def get_bridge_info(self) -> Dict[str, Any]:
        """
        Get GUI Bridge service information
        
        Returns:
            Dictionary with service info
        """
        if not self.is_connected:
            raise GuiBridgeServiceError("GUI Bridge service not connected")
        
        try:
            await self.initialize()
            
            async with self.http_session.get(
                f"{self.base_url}/info"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiBridgeServiceError(f"Failed to get bridge info: {response.status}")
                    
        except Exception as e:
            logger.error(f"Failed to get GUI Bridge info: {e}")
            raise GuiBridgeServiceError(f"Failed to get bridge info: {e}")
    
    async def handle_electron_connect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Electron GUI connection
        
        Args:
            data: Connection data from Electron GUI
            
        Returns:
            Connection response
        """
        if not self.is_connected:
            raise GuiBridgeServiceError("GUI Bridge service not connected")
        
        try:
            await self.initialize()
            
            async with self.http_session.post(
                f"{self.base_url}/electron/connect",
                json=data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiBridgeServiceError(f"Connection failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"Failed to handle Electron connect: {e}")
            raise GuiBridgeServiceError(f"Connection failed: {e}")
    
    async def handle_electron_disconnect(self, session_id: str) -> Dict[str, Any]:
        """
        Handle Electron GUI disconnection
        
        Args:
            session_id: Session ID to disconnect
            
        Returns:
            Disconnection response
        """
        if not self.is_connected:
            raise GuiBridgeServiceError("GUI Bridge service not connected")
        
        try:
            await self.initialize()
            
            async with self.http_session.post(
                f"{self.base_url}/electron/disconnect",
                json={"session_id": session_id}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiBridgeServiceError(f"Disconnection failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"Failed to handle Electron disconnect: {e}")
            raise GuiBridgeServiceError(f"Disconnection failed: {e}")
    
    async def proxy_gui_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Proxy request to GUI Bridge service
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            data: Request data
            headers: Request headers
            
        Returns:
            Response data
        """
        if not self.is_connected:
            raise GuiBridgeServiceError("GUI Bridge service not connected")
        
        try:
            await self.initialize()
            
            url = f"{self.base_url}{endpoint}"
            
            async with self.http_session.request(
                method=method,
                url=url,
                json=data,
                headers=headers
            ) as response:
                if response.status >= 500:
                    raise GuiBridgeServiceError(f"Service error: {response.status}")
                
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {"data": await response.text()}
                    
        except Exception as e:
            logger.error(f"GUI Bridge proxy request failed: {e}")
            raise GuiBridgeServiceError(f"Proxy request failed: {e}")


# Global GUI Bridge service instance
gui_bridge_service = GuiBridgeService()
