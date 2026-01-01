#!/usr/bin/env python3
"""
Lucid Admin Interface - Service Client
Step 24: Admin Container & Integration

HTTP client wrapper for inter-service communication with retry logic,
circuit breaker pattern, and timeout handling.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

from admin.config import get_admin_config

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration"""
    name: str
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_path: str = "/health"
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: Optional[datetime] = None
    failure_count: int = 0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


class ServiceClient:
    """
    HTTP client wrapper for inter-service communication.
    
    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker pattern
    - Health checking
    - Timeout handling
    - Request/response logging
    """
    
    def __init__(self):
        self.config = get_admin_config()
        self.endpoints: Dict[str, ServiceEndpoint] = {}
        self.http_client: Optional[httpx.AsyncClient] = None
        self.circuit_breakers: Dict[str, datetime] = {}
        self._initialize_endpoints()
    
    def _initialize_endpoints(self):
        """Initialize service endpoints from configuration"""
        endpoints_config = {
            "api_gateway": {
                "base_url": self.config.api_gateway_url,
                "health_check_path": "/health"
            },
            "blockchain": {
                "base_url": self.config.blockchain_url,
                "health_check_path": "/health"
            },
            "session_management": {
                "base_url": self.config.session_management_url,
                "health_check_path": "/health"
            },
            "node_management": {
                "base_url": self.config.node_management_url,
                "health_check_path": "/health"
            },
            "auth_service": {
                "base_url": self.config.auth_service_url,
                "health_check_path": "/health"
            }
        }
        
        for name, config in endpoints_config.items():
            if config["base_url"]:
                self.endpoints[name] = ServiceEndpoint(
                    name=name,
                    base_url=config["base_url"],
                    health_check_path=config.get("health_check_path", "/health"),
                    timeout=int(os.getenv(f"{name.upper()}_TIMEOUT", "30")),
                    max_retries=int(os.getenv(f"{name.upper()}_MAX_RETRIES", "3")),
                    circuit_breaker_threshold=int(os.getenv(f"{name.upper()}_CIRCUIT_BREAKER_THRESHOLD", "5"))
                )
    
    async def initialize(self):
        """Initialize HTTP client"""
        try:
            timeout = httpx.Timeout(
                connect=10.0,
                read=30.0,
                write=10.0,
                pool=5.0
            )
            
            self.http_client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100
                ),
                follow_redirects=True
            )
            
            logger.info("Service client initialized")
            
            # Perform initial health checks
            await self._health_check_all()
            
        except Exception as e:
            logger.error(f"Failed to initialize service client: {e}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
            logger.info("Service client closed")
    
    def _is_circuit_open(self, service_name: str) -> bool:
        """Check if circuit breaker is open for a service"""
        if service_name not in self.circuit_breakers:
            return False
        
        breaker_time = self.circuit_breakers[service_name]
        endpoint = self.endpoints.get(service_name)
        
        if not endpoint:
            return False
        
        time_since_breaker = (datetime.now(timezone.utc) - breaker_time).total_seconds()
        
        if time_since_breaker > endpoint.circuit_breaker_timeout:
            # Reset circuit breaker
            del self.circuit_breakers[service_name]
            endpoint.failure_count = 0
            return False
        
        return True
    
    def _open_circuit(self, service_name: str):
        """Open circuit breaker for a service"""
        self.circuit_breakers[service_name] = datetime.now(timezone.utc)
        endpoint = self.endpoints.get(service_name)
        if endpoint:
            endpoint.status = ServiceStatus.UNHEALTHY
            logger.warning(f"Circuit breaker opened for service: {service_name}")
    
    async def _health_check(self, service_name: str) -> bool:
        """Check health of a specific service"""
        endpoint = self.endpoints.get(service_name)
        if not endpoint:
            return False
        
        try:
            if not self.http_client:
                await self.initialize()
            
            health_url = f"{endpoint.base_url.rstrip('/')}{endpoint.health_check_path}"
            response = await self.http_client.get(
                health_url,
                timeout=endpoint.timeout
            )
            
            endpoint.last_check = datetime.now(timezone.utc)
            
            if response.status_code == 200:
                endpoint.status = ServiceStatus.HEALTHY
                endpoint.failure_count = 0
                return True
            else:
                endpoint.status = ServiceStatus.DEGRADED
                endpoint.failure_count += 1
                return False
                
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            endpoint.status = ServiceStatus.UNHEALTHY
            endpoint.failure_count += 1
            endpoint.last_check = datetime.now(timezone.utc)
            
            if endpoint.failure_count >= endpoint.circuit_breaker_threshold:
                self._open_circuit(service_name)
            
            return False
    
    async def _health_check_all(self):
        """Check health of all services"""
        tasks = [self._health_check(name) for name in self.endpoints.keys()]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError))
    )
    async def request(
        self,
        service_name: str,
        method: str,
        path: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request to a service.
        
        Args:
            service_name: Name of the service
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API path (e.g., "/api/v1/users")
            **kwargs: Additional arguments for httpx request
            
        Returns:
            httpx.Response object
            
        Raises:
            ValueError: If service not found or circuit breaker is open
            httpx.HTTPError: If request fails after retries
        """
        endpoint = self.endpoints.get(service_name)
        if not endpoint:
            raise ValueError(f"Service {service_name} not configured")
        
        # Check circuit breaker
        if self._is_circuit_open(service_name):
            raise ValueError(f"Circuit breaker is open for service {service_name}")
        
        if not self.http_client:
            await self.initialize()
        
        # Build full URL
        url = f"{endpoint.base_url.rstrip('/')}{path}"
        
        # Make request
        try:
            response = await self.http_client.request(
                method=method,
                url=url,
                timeout=endpoint.timeout,
                **kwargs
            )
            
            # Reset failure count on success
            endpoint.failure_count = 0
            
            # Check if response indicates service is healthy
            if response.status_code < 500:
                endpoint.status = ServiceStatus.HEALTHY
            else:
                endpoint.status = ServiceStatus.DEGRADED
                endpoint.failure_count += 1
            
            return response
            
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
            endpoint.failure_count += 1
            endpoint.status = ServiceStatus.UNHEALTHY
            
            if endpoint.failure_count >= endpoint.circuit_breaker_threshold:
                self._open_circuit(service_name)
            
            logger.error(f"Request failed for {service_name}: {e}")
            raise
    
    async def get(self, service_name: str, path: str, **kwargs) -> httpx.Response:
        """GET request"""
        return await self.request(service_name, "GET", path, **kwargs)
    
    async def post(self, service_name: str, path: str, **kwargs) -> httpx.Response:
        """POST request"""
        return await self.request(service_name, "POST", path, **kwargs)
    
    async def put(self, service_name: str, path: str, **kwargs) -> httpx.Response:
        """PUT request"""
        return await self.request(service_name, "PUT", path, **kwargs)
    
    async def delete(self, service_name: str, path: str, **kwargs) -> httpx.Response:
        """DELETE request"""
        return await self.request(service_name, "DELETE", path, **kwargs)
    
    async def patch(self, service_name: str, path: str, **kwargs) -> httpx.Response:
        """PATCH request"""
        return await self.request(service_name, "PATCH", path, **kwargs)
    
    def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """Get status of a service"""
        endpoint = self.endpoints.get(service_name)
        return endpoint.status if endpoint else None
    
    def get_all_service_statuses(self) -> Dict[str, ServiceStatus]:
        """Get status of all services"""
        return {name: endpoint.status for name, endpoint in self.endpoints.items()}


# Global service client instance
_service_client: Optional[ServiceClient] = None


async def get_service_client() -> ServiceClient:
    """Get global service client instance"""
    global _service_client
    if _service_client is None:
        _service_client = ServiceClient()
        await _service_client.initialize()
    return _service_client


async def close_service_client():
    """Close global service client instance"""
    global _service_client
    if _service_client:
        await _service_client.close()
        _service_client = None

