#!/usr/bin/env python3
"""
Base Service Client for Integration Modules
Provides common functionality for service communication
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import httpx
from datetime import datetime

# Use core.logging if available, fallback to standard logging
try:
    from core.logging import get_logger
except ImportError:
    logger = logging.getLogger(__name__)
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)


class ServiceError(Exception):
    """Base exception for service communication errors"""
    pass


class ServiceTimeoutError(ServiceError):
    """Exception raised when service call times out"""
    pass


class ServiceClientBase(ABC):
    """
    Base class for service integration clients
    Provides common HTTP client functionality with retries and error handling
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: Optional[float] = None,
        retry_count: Optional[int] = None,
        retry_delay: Optional[float] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize service client
        
        Args:
            base_url: Base URL for the service (from environment variable)
            timeout: Request timeout in seconds (from SERVICE_TIMEOUT_SECONDS)
            retry_count: Number of retry attempts (from SERVICE_RETRY_COUNT)
            retry_delay: Delay between retries in seconds (from SERVICE_RETRY_DELAY_SECONDS)
            api_key: Optional API key for authentication
        """
        if not base_url:
            raise ValueError(f"Service base_url is required but not provided")
        
        # Validate URL doesn't use localhost
        if "localhost" in base_url or "127.0.0.1" in base_url:
            raise ValueError(f"Service URL must not use localhost: {base_url}. Use service name instead.")
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout or float(os.getenv('SERVICE_TIMEOUT_SECONDS', '30'))
        self.retry_count = retry_count or int(os.getenv('SERVICE_RETRY_COUNT', '3'))
        self.retry_delay = retry_delay or float(os.getenv('SERVICE_RETRY_DELAY_SECONDS', '1.0'))
        self.api_key = api_key or os.getenv('JWT_SECRET_KEY', '')
        
        # Create HTTP client with timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
            follow_redirects=True
        )
        
        logger.info(f"Initialized {self.__class__.__name__} with base_url={self.base_url}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            json_data: JSON request body
            headers: Additional headers
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            ServiceError: On service communication error
            ServiceTimeoutError: On timeout
        """
        url = f"{self.base_url}{endpoint}"
        
        # Prepare headers
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self.api_key:
            request_headers['Authorization'] = f'Bearer {self.api_key}'
        if headers:
            request_headers.update(headers)
        
        # Retry logic
        last_error = None
        for attempt in range(self.retry_count):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1}/{self.retry_count})")
                
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers
                )
                
                # Check for successful response
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    return response.json()
                except Exception:
                    # If response is not JSON, return text or empty dict
                    return {"status": "success", "data": response.text} if response.text else {}
                
            except httpx.TimeoutException as e:
                last_error = ServiceTimeoutError(f"Request to {url} timed out after {self.timeout}s")
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
                
            except httpx.HTTPStatusError as e:
                last_error = ServiceError(f"HTTP error {e.response.status_code}: {e.response.text}")
                logger.warning(f"HTTP error (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
                
                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise last_error
                
            except Exception as e:
                last_error = ServiceError(f"Request failed: {str(e)}")
                logger.warning(f"Request error (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
        
        # All retries exhausted
        raise last_error or ServiceError(f"Request to {url} failed after {self.retry_count} attempts")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            return await self._make_request('GET', '/health')
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.debug(f"Closed {self.__class__.__name__} client")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

