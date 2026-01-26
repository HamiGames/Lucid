"""
Base Service Client for Backend Integration
File: gui-api-bridge/gui-api-bridge/integration/service_base.py
Pattern: Follow sessions/pipeline/integration/ structure
"""

import logging
import asyncio
from typing import Optional, Dict, Any
import httpx
from ..config import GuiAPIBridgeSettings

logger = logging.getLogger(__name__)


class ServiceBaseClient:
    """
    Base client for backend service integration
    Provides common functionality for all backend service clients
    """
    
    def __init__(self, service_name: str, service_url: str, config: GuiAPIBridgeSettings):
        """Initialize base service client"""
        self.service_name = service_name
        self.service_url = service_url
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.retry_attempts = 3
        self.retry_delay = 1.0  # seconds
    
    async def initialize(self):
        """Initialize HTTP client"""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.service_url,
                timeout=30.0,
                follow_redirects=True,
            )
            logger.info(f"Initialized {self.service_name} client: {self.service_url}")
        except Exception as e:
            logger.error(f"Failed to initialize {self.service_name} client: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup HTTP client"""
        if self.client:
            await self.client.aclose()
            logger.info(f"Cleaned up {self.service_name} client")
    
    async def health_check(self) -> bool:
        """
        Check if backend service is healthy
        Returns True if service is reachable and healthy
        """
        try:
            response = await self.client.get("/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for {self.service_name}: {e}")
            return False
    
    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx
        
        Returns:
            Response JSON or None on error
        """
        if not self.client:
            logger.error(f"{self.service_name} client not initialized")
            return None
        
        url = f"{endpoint}" if endpoint.startswith("/") else f"/{endpoint}"
        
        for attempt in range(self.retry_attempts):
            try:
                response = await self.client.request(method, url, **kwargs)
                
                if response.status_code >= 200 and response.status_code < 300:
                    logger.debug(f"{self.service_name} {method} {url}: {response.status_code}")
                    return response.json()
                
                elif response.status_code >= 400 and response.status_code < 500:
                    # Client error - don't retry
                    logger.warning(f"{self.service_name} {method} {url}: {response.status_code}")
                    return None
                
                else:
                    # Server error - might retry
                    logger.warning(f"{self.service_name} {method} {url}: {response.status_code}")
                    
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    return None
            
            except httpx.TimeoutException:
                logger.warning(f"{self.service_name} {method} {url}: timeout (attempt {attempt + 1})")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return None
            
            except Exception as e:
                logger.error(f"{self.service_name} {method} {url}: {e} (attempt {attempt + 1})")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return None
        
        return None
    
    async def get(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make GET request"""
        return await self.request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make POST request"""
        return await self.request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make PUT request"""
        return await self.request("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make DELETE request"""
        return await self.request("DELETE", endpoint, **kwargs)
    
    async def patch(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make PATCH request"""
        return await self.request("PATCH", endpoint, **kwargs)
