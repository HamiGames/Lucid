"""
Base Service Client for GUI Tor Manager
Provides common functionality for all backend service clients
"""

import httpx
import asyncio
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from ..utils.logging import get_logger
from ..utils.errors import GuiTorManagerException

logger = get_logger(__name__)


class ServiceBaseClient(ABC):
    """Abstract base class for service clients"""
    
    def __init__(self, base_url: str, timeout: int = 30, retries: int = 3):
        """
        Initialize service client
        
        Args:
            base_url: Base URL for the service
            timeout: Request timeout in seconds
            retries: Number of retries on failure
        """
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client connection"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> bool:
        """
        Check if service is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(
                "/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for {self.base_url}: {e}")
            return False
    
    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx.request
        
        Returns:
            Response object
        
        Raises:
            GuiTorManagerException: If all retries fail
        """
        client = await self._get_client()
        last_error = None
        
        for attempt in range(self.retries):
            try:
                logger.debug(
                    f"Request attempt {attempt + 1}/{self.retries}: {method} {endpoint}",
                    extra={"method": method, "endpoint": endpoint, "attempt": attempt + 1}
                )
                
                response = await client.request(method, endpoint, **kwargs)
                
                # Log successful response
                logger.debug(
                    f"Response received: {response.status_code}",
                    extra={"status_code": response.status_code, "endpoint": endpoint}
                )
                
                return response
            
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                if attempt < self.retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            except Exception as e:
                last_error = e
                logger.warning(f"Error on attempt {attempt + 1}: {e}")
                if attempt < self.retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        raise GuiTorManagerException(
            message=f"Failed to connect to service after {self.retries} attempts",
            code="SERVICE_CONNECTION_ERROR",
            details={"service_url": self.base_url, "last_error": str(last_error)}
        )
    
    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """GET request"""
        return await self._request_with_retry("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """POST request"""
        return await self._request_with_retry("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> httpx.Response:
        """PUT request"""
        return await self._request_with_retry("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """DELETE request"""
        return await self._request_with_retry("DELETE", endpoint, **kwargs)
