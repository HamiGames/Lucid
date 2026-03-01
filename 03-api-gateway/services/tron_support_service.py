"""
TRON Support Services

File: 03-api-gateway/services/tron_support_service.py
Purpose: Service for handling TRON support services (payout router, wallet manager, USDT manager)
"""

import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TronSupportServiceError(Exception):
    """TRON support service error"""
    pass


class TronSupportService:
    """Service for managing TRON support services integration"""
    
    def __init__(self):
        """Initialize TRON support services"""
        self.payout_router_url = settings.TRON_PAYOUT_ROUTER_URL
        self.wallet_manager_url = settings.TRON_WALLET_MANAGER_URL
        self.usdt_manager_url = settings.TRON_USDT_MANAGER_URL
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
            logger.info("TRON support services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize TRON support services: {e}")
            raise TronSupportServiceError(f"Failed to initialize: {e}")
    
    async def close(self):
        """Close HTTP session"""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            logger.info("TRON support services session closed")
    
    # Payout Router Methods
    async def check_payout_health(self) -> bool:
        """Check TRON Payout Router health"""
        if not self.payout_router_url:
            logger.warning("TRON_PAYOUT_ROUTER_URL not configured")
            return False
        
        try:
            await self.initialize()
            async with self.http_session.get(
                f"{self.payout_router_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"TRON Payout Router health check failed: {e}")
            return False
    
    async def get_payout_info(self) -> Dict[str, Any]:
        """Get TRON Payout Router info"""
        if not self.payout_router_url:
            raise TronSupportServiceError("TRON_PAYOUT_ROUTER_URL not configured")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.payout_router_url}/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise TronSupportServiceError(f"Failed to get payout info: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get payout info: {e}")
            raise TronSupportServiceError(f"Failed to get payout info: {e}")
    
    async def get_payout_status(self) -> Dict[str, Any]:
        """Get TRON Payout Router status"""
        if not self.payout_router_url:
            raise TronSupportServiceError("TRON_PAYOUT_ROUTER_URL not configured")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.payout_router_url}/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise TronSupportServiceError(f"Failed to get payout status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get payout status: {e}")
            raise TronSupportServiceError(f"Failed to get payout status: {e}")
    
    # Wallet Manager Methods
    async def check_wallet_health(self) -> bool:
        """Check TRON Wallet Manager health"""
        if not self.wallet_manager_url:
            logger.warning("TRON_WALLET_MANAGER_URL not configured")
            return False
        
        try:
            await self.initialize()
            async with self.http_session.get(
                f"{self.wallet_manager_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"TRON Wallet Manager health check failed: {e}")
            return False
    
    async def get_wallet_info(self) -> Dict[str, Any]:
        """Get TRON Wallet Manager info"""
        if not self.wallet_manager_url:
            raise TronSupportServiceError("TRON_WALLET_MANAGER_URL not configured")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.wallet_manager_url}/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise TronSupportServiceError(f"Failed to get wallet info: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get wallet info: {e}")
            raise TronSupportServiceError(f"Failed to get wallet info: {e}")
    
    async def list_wallets(self) -> Dict[str, Any]:
        """List TRON wallets"""
        if not self.wallet_manager_url:
            raise TronSupportServiceError("TRON_WALLET_MANAGER_URL not configured")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.wallet_manager_url}/wallets") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise TronSupportServiceError(f"Failed to list wallets: {response.status}")
        except Exception as e:
            logger.error(f"Failed to list wallets: {e}")
            raise TronSupportServiceError(f"Failed to list wallets: {e}")
    
    # USDT Manager Methods
    async def check_usdt_health(self) -> bool:
        """Check TRON USDT Manager health"""
        if not self.usdt_manager_url:
            logger.warning("TRON_USDT_MANAGER_URL not configured")
            return False
        
        try:
            await self.initialize()
            async with self.http_session.get(
                f"{self.usdt_manager_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"TRON USDT Manager health check failed: {e}")
            return False
    
    async def get_usdt_info(self) -> Dict[str, Any]:
        """Get TRON USDT Manager info"""
        if not self.usdt_manager_url:
            raise TronSupportServiceError("TRON_USDT_MANAGER_URL not configured")
        
        try:
            await self.initialize()
            async with self.http_session.get(f"{self.usdt_manager_url}/info") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise TronSupportServiceError(f"Failed to get USDT info: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get USDT info: {e}")
            raise TronSupportServiceError(f"Failed to get USDT info: {e}")
    
    async def get_usdt_balance(self, wallet_id: str) -> Dict[str, Any]:
        """Get USDT balance for wallet"""
        if not self.usdt_manager_url:
            raise TronSupportServiceError("TRON_USDT_MANAGER_URL not configured")
        
        try:
            await self.initialize()
            async with self.http_session.get(
                f"{self.usdt_manager_url}/balance/{wallet_id}"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise TronSupportServiceError(f"Failed to get USDT balance: {response.status}")
        except Exception as e:
            logger.error(f"Failed to get USDT balance: {e}")
            raise TronSupportServiceError(f"Failed to get USDT balance: {e}")
    
    async def transfer_usdt(self) -> Dict[str, Any]:
        """Transfer USDT"""
        if not self.usdt_manager_url:
            raise TronSupportServiceError("TRON_USDT_MANAGER_URL not configured")
        
        try:
            await self.initialize()
            async with self.http_session.post(f"{self.usdt_manager_url}/transfer") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise TronSupportServiceError(f"Failed to transfer USDT: {response.status}")
        except Exception as e:
            logger.error(f"Failed to transfer USDT: {e}")
            raise TronSupportServiceError(f"Failed to transfer USDT: {e}")


# Global service instance
tron_support_service = TronSupportService()
