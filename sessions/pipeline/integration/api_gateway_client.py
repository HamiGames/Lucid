#!/usr/bin/env python3
"""
API Gateway Integration Client
Handles interaction with api-gateway service for routing and request coordination
"""

import logging
import os
from typing import Dict, Any, Optional

from .service_base import ServiceClientBase, ServiceError
from core.logging import get_logger

logger = get_logger(__name__)


class APIGatewayClient(ServiceClientBase):
    """
    Client for interacting with api-gateway service
    Handles request routing, rate limiting coordination, and API access
    """
    
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """
        Initialize API Gateway client
        
        Args:
            base_url: Base URL for api-gateway (from API_GATEWAY_URL env var if not provided)
            **kwargs: Additional arguments passed to ServiceClientBase
        """
        url = base_url or os.getenv('API_GATEWAY_URL', '')
        if not url:
            raise ValueError("API_GATEWAY_URL environment variable is required")
        
        super().__init__(base_url=url, **kwargs)
    
    async def get_service_routes(self) -> Dict[str, Any]:
        """
        Get available service routes from API Gateway
        
        Returns:
            Route information
        """
        try:
            response = await self._make_request(
                method='GET',
                endpoint='/api/v1/routes'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get service routes: {str(e)}")
            raise ServiceError(f"Failed to get service routes: {str(e)}")
    
    async def get_rate_limit_status(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Get rate limit status for endpoint
        
        Args:
            endpoint: Optional endpoint path (gets global status if not provided)
            
        Returns:
            Rate limit status
        """
        try:
            params = {}
            if endpoint:
                params['endpoint'] = endpoint
            
            response = await self._make_request(
                method='GET',
                endpoint='/api/v1/rate-limit/status',
                params=params
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {str(e)}")
            raise ServiceError(f"Failed to get rate limit status: {str(e)}")
    
    async def validate_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Validate request through API Gateway
        
        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            
        Returns:
            Validation result
        """
        try:
            payload = {
                "method": method,
                "path": path,
                "headers": headers or {}
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/validate',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to validate request: {str(e)}")
            raise ServiceError(f"Request validation failed: {str(e)}")
    
    async def proxy_request(
        self,
        method: str,
        service: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Proxy request to another service through API Gateway
        
        Args:
            method: HTTP method
            service: Target service name
            path: Service endpoint path
            data: Optional request data
            headers: Optional request headers
            
        Returns:
            Service response
        """
        try:
            payload = {
                "method": method,
                "service": service,
                "path": path,
                "data": data,
                "headers": headers or {}
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/proxy',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to proxy request to {service}: {str(e)}")
            raise ServiceError(f"Request proxy failed: {str(e)}")
    
    async def get_circuit_breaker_status(self, service: str) -> Dict[str, Any]:
        """
        Get circuit breaker status for a service
        
        Args:
            service: Service name
            
        Returns:
            Circuit breaker status
        """
        try:
            response = await self._make_request(
                method='GET',
                endpoint=f'/api/v1/circuit-breaker/{service}/status'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get circuit breaker status for {service}: {str(e)}")
            raise ServiceError(f"Failed to get circuit breaker status: {str(e)}")

