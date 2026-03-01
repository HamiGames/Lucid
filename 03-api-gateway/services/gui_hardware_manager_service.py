"""
GUI Hardware Manager Service

File: 03-api-gateway/services/gui_hardware_manager_service.py
Purpose: Service for handling GUI Hardware Manager integration and proxy operations
"""

import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GuiHardwareManagerServiceError(Exception):
    """GUI Hardware Manager service error"""
    pass


class GuiHardwareManagerService:
    """Service for managing GUI Hardware Manager integration"""
    
    def __init__(self):
        """Initialize GUI Hardware Manager service"""
        self.base_url = settings.GUI_HARDWARE_MANAGER_URL
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
            logger.info(f"GUI Hardware Manager service initialized with URL: {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize GUI Hardware Manager service: {e}")
            raise GuiHardwareManagerServiceError(f"Failed to initialize: {e}")
    
    async def close(self):
        """Close HTTP session"""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            logger.info("GUI Hardware Manager service session closed")
    
    async def health_check(self) -> bool:
        """Check service health"""
        if not self.base_url:
            logger.warning("GUI_HARDWARE_MANAGER_URL not configured")
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
            logger.warning(f"GUI Hardware Manager health check failed: {e}")
            self.is_connected = False
            return False
    
    async def get_manager_info(self) -> Dict[str, Any]:
        """Get manager information"""
        if not self.is_connected:
            raise GuiHardwareManagerServiceError("GUI Hardware Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiHardwareManagerServiceError(f"Failed to get info: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get GUI Hardware Manager info: {e}")
            raise GuiHardwareManagerServiceError(f"Failed to get info: {e}")
    
    async def list_devices(self) -> Dict[str, Any]:
        """List hardware devices"""
        if not self.is_connected:
            raise GuiHardwareManagerServiceError("GUI Hardware Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/devices") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiHardwareManagerServiceError(f"Failed to list devices: {response.status}")
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            raise GuiHardwareManagerServiceError(f"Failed to list devices: {e}")
    
    async def get_device_details(self, device_id: str) -> Dict[str, Any]:
        """Get device details"""
        if not self.is_connected:
            raise GuiHardwareManagerServiceError("GUI Hardware Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/devices/{device_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiHardwareManagerServiceError(f"Failed to get device: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get device details: {e}")
            raise GuiHardwareManagerServiceError(f"Failed to get device: {e}")
    
    async def verify_device(self, device_id: str) -> Dict[str, Any]:
        """Verify device connection"""
        if not self.is_connected:
            raise GuiHardwareManagerServiceError("GUI Hardware Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.post(
                f"{self.base_url}/devices/{device_id}/verify"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiHardwareManagerServiceError(f"Failed to verify: {response.status}")
        except Exception as e:
            logger.error(f"Failed to verify device: {e}")
            raise GuiHardwareManagerServiceError(f"Failed to verify: {e}")
    
    async def list_wallets(self) -> Dict[str, Any]:
        """List hardware wallets"""
        if not self.is_connected:
            raise GuiHardwareManagerServiceError("GUI Hardware Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.base_url}/wallets") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiHardwareManagerServiceError(f"Failed to list wallets: {response.status}")
        except Exception as e:
            logger.error(f"Failed to list wallets: {e}")
            raise GuiHardwareManagerServiceError(f"Failed to list wallets: {e}")
    
    async def sign_transaction(self, wallet_id: str) -> Dict[str, Any]:
        """Sign transaction with hardware wallet"""
        if not self.is_connected:
            raise GuiHardwareManagerServiceError("GUI Hardware Manager not connected")
        
        try:
            await self.initialize()
            async with self.http_session.post(
                f"{self.base_url}/wallets/{wallet_id}/sign"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise GuiHardwareManagerServiceError(f"Failed to sign: {response.status}")
        except Exception as e:
            logger.error(f"Failed to sign transaction: {e}")
            raise GuiHardwareManagerServiceError(f"Failed to sign: {e}")


# Global service instance
gui_hardware_manager_service = GuiHardwareManagerService()
