"""
Lucid API Gateway - Proxy Service
Handles proxying requests to backend services with circuit breaker pattern.

File: 03-api-gateway/services/proxy_service.py
Lines: ~300
Purpose: Backend service proxy with circuit breaker
Dependencies: aiohttp, Circuit Breaker
"""

import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio

from ..config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit open, failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class ServiceUnavailableError(Exception):
    """Backend service unavailable."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by:
    - Opening circuit after failure threshold
    - Failing fast when circuit is open
    - Testing service recovery in half-open state
    """
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time: Optional[datetime] = None
        
    def record_success(self):
        """Record successful request."""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info("Circuit breaker: Closed (service recovered)")
                self.state = CircuitState.CLOSED
                self.success_count = 0
                
    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker: Open (failure threshold {self.failure_threshold} exceeded)"
            )
            self.state = CircuitState.OPEN
            
    def can_attempt(self) -> bool:
        """Check if request attempt is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker: Half-Open (testing recovery)")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return True
            return False
            
        # HALF_OPEN state
        return True


class ProxyService:
    """
    Backend service proxy with circuit breaker pattern.
    
    Handles proxying to:
    - Blockchain Core (Cluster 02)
    - Session Management (Cluster 03)
    - Node Management (Cluster 05)
    """
    
    def __init__(self):
        # Backend service URLs
        self.service_urls = {
            "blockchain": settings.BLOCKCHAIN_SERVICE_URL,
            "session": settings.SESSION_SERVICE_URL,
            "node": settings.NODE_SERVICE_URL,
        }
        
        # Circuit breakers for each service
        self.circuit_breakers = {
            service: CircuitBreaker()
            for service in self.service_urls.keys()
        }
        
        # HTTP session
        self.http_session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize HTTP session."""
        if not self.http_session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300
            )
            self.http_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
            
    async def close(self):
        """Close HTTP session."""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            
    async def proxy_request(
        self,
        service: str,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Proxy request to backend service with circuit breaker.
        
        Args:
            service: Service name (blockchain, session, node)
            endpoint: API endpoint path
            method: HTTP method
            data: Request data
            headers: Request headers
            
        Returns:
            Response data dictionary
            
        Raises:
            ServiceUnavailableError: If service is unavailable
        """
        await self.initialize()
        
        # Check if service exists
        if service not in self.service_urls:
            raise ValueError(f"Unknown service: {service}")
            
        # Get circuit breaker
        circuit_breaker = self.circuit_breakers[service]
        
        # Check if circuit allows attempt
        if not circuit_breaker.can_attempt():
            logger.warning(f"Circuit breaker open for {service}, failing fast")
            raise ServiceUnavailableError(
                f"{service} service is currently unavailable"
            )
            
        # Build request URL
        base_url = self.service_urls[service]
        url = f"{base_url}{endpoint}"
        
        try:
            # Make request
            async with self.http_session.request(
                method=method,
                url=url,
                json=data,
                headers=headers
            ) as response:
                # Check response status
                if response.status >= 500:
                    # Server error, record failure
                    circuit_breaker.record_failure()
                    raise ServiceUnavailableError(
                        f"{service} service error: {response.status}"
                    )
                    
                # Success
                circuit_breaker.record_success()
                
                # Parse response
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {"data": await response.text()}
                    
        except aiohttp.ClientError as e:
            # Network error, record failure
            circuit_breaker.record_failure()
            logger.error(f"Proxy request error to {service}: {e}")
            raise ServiceUnavailableError(
                f"Failed to connect to {service} service"
            )
        except asyncio.TimeoutError:
            # Timeout, record failure
            circuit_breaker.record_failure()
            logger.error(f"Proxy request timeout to {service}")
            raise ServiceUnavailableError(
                f"{service} service timeout"
            )
            
    async def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Get status of all circuit breakers.
        
        Returns:
            Dictionary with circuit breaker status for each service
        """
        status = {}
        for service, breaker in self.circuit_breakers.items():
            status[service] = {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "last_failure": (
                    breaker.last_failure_time.isoformat()
                    if breaker.last_failure_time
                    else None
                )
            }
        return status


# Global proxy service instance
proxy_service = ProxyService()

