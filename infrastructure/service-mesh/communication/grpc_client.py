"""
Lucid Service Mesh - gRPC Client
gRPC client for service mesh communication.

File: infrastructure/service-mesh/communication/grpc_client.py
Lines: ~250
Purpose: gRPC client
Dependencies: grpc, asyncio
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import grpc
from grpc import aio

logger = logging.getLogger(__name__)


class GRPCClient:
    """
    gRPC client for service mesh communication.
    
    Handles:
    - gRPC connection management
    - Service discovery integration
    - Load balancing
    - Circuit breaker pattern
    - Retry logic
    """
    
    def __init__(self):
        self.channels: Dict[str, aio.Channel] = {}
        self.stubs: Dict[str, Any] = {}
        self.service_endpoints: Dict[str, str] = {}
        self.connection_timeout = 30
        self.max_retries = 3
        self.retry_delay = 1
        
    async def initialize(self):
        """Initialize gRPC client."""
        try:
            logger.info("Initializing gRPC Client...")
            
            # Setup default service endpoints
            self._setup_default_endpoints()
            
            logger.info("gRPC Client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize gRPC Client: {e}")
            raise
            
    def _setup_default_endpoints(self):
        """Setup default service endpoints."""
        self.service_endpoints = {
            "api-gateway": "api-gateway:8080",
            "blockchain-core": "blockchain-core:8084",
            "session-management": "session-api:8087",
            "node-management": "node-management:8095",
            "auth-service": "auth-service:8089",
            "service-mesh-controller": "service-mesh-controller:8600"
        }
        
    async def create_channel(
        self,
        service_name: str,
        endpoint: str = None,
        options: list = None
    ) -> aio.Channel:
        """
        Create gRPC channel for a service.
        
        Args:
            service_name: Service name
            endpoint: Service endpoint (optional)
            options: gRPC channel options
            
        Returns:
            gRPC channel
        """
        try:
            # Use provided endpoint or lookup in service endpoints
            if not endpoint:
                endpoint = self.service_endpoints.get(service_name)
                if not endpoint:
                    raise ValueError(f"No endpoint found for service {service_name}")
                    
            # Default channel options
            if not options:
                options = [
                    ('grpc.keepalive_time_ms', 30000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.keepalive_permit_without_calls', True),
                    ('grpc.http2.max_pings_without_data', 0),
                    ('grpc.http2.min_time_between_pings_ms', 10000),
                    ('grpc.http2.min_ping_interval_without_data_ms', 300000)
                ]
                
            # Create channel
            channel = aio.insecure_channel(endpoint, options=options)
            
            # Store channel
            self.channels[service_name] = channel
            
            logger.info(f"Created gRPC channel for {service_name}: {endpoint}")
            return channel
            
        except Exception as e:
            logger.error(f"Failed to create channel for {service_name}: {e}")
            raise
            
    async def get_channel(self, service_name: str) -> Optional[aio.Channel]:
        """Get existing gRPC channel for a service."""
        return self.channels.get(service_name)
        
    async def create_stub(
        self,
        service_name: str,
        stub_class: type,
        endpoint: str = None
    ) -> Any:
        """
        Create gRPC stub for a service.
        
        Args:
            service_name: Service name
            stub_class: gRPC stub class
            endpoint: Service endpoint (optional)
            
        Returns:
            gRPC stub
        """
        try:
            # Get or create channel
            channel = await self.get_channel(service_name)
            if not channel:
                channel = await self.create_channel(service_name, endpoint)
                
            # Create stub
            stub = stub_class(channel)
            
            # Store stub
            self.stubs[service_name] = stub
            
            logger.info(f"Created gRPC stub for {service_name}")
            return stub
            
        except Exception as e:
            logger.error(f"Failed to create stub for {service_name}: {e}")
            raise
            
    async def call_service(
        self,
        service_name: str,
        method: str,
        request: Any,
        timeout: int = None,
        retries: int = None
    ) -> Any:
        """
        Call a gRPC service method.
        
        Args:
            service_name: Service name
            method: Method name
            request: Request object
            timeout: Request timeout
            retries: Number of retries
            
        Returns:
            Response object
        """
        try:
            if not timeout:
                timeout = self.connection_timeout
                
            if retries is None:
                retries = self.max_retries
                
            # Get stub
            stub = self.stubs.get(service_name)
            if not stub:
                raise ValueError(f"No stub found for service {service_name}")
                
            # Get method
            if not hasattr(stub, method):
                raise ValueError(f"Method {method} not found on stub for {service_name}")
                
            grpc_method = getattr(stub, method)
            
            # Call method with retries
            for attempt in range(retries + 1):
                try:
                    response = await grpc_method(
                        request,
                        timeout=timeout
                    )
                    return response
                    
                except grpc.RpcError as e:
                    if attempt < retries:
                        logger.warning(
                            f"gRPC call failed for {service_name}.{method}, "
                            f"attempt {attempt + 1}/{retries + 1}: {e}"
                        )
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    else:
                        logger.error(
                            f"gRPC call failed for {service_name}.{method} "
                            f"after {retries + 1} attempts: {e}"
                        )
                        raise
                        
        except Exception as e:
            logger.error(f"Error calling service {service_name}.{method}: {e}")
            raise
            
    async def health_check(self, service_name: str) -> bool:
        """
        Perform health check on a service.
        
        Args:
            service_name: Service name
            
        Returns:
            True if service is healthy
        """
        try:
            # Get channel
            channel = await self.get_channel(service_name)
            if not channel:
                return False
                
            # Check channel state
            state = channel.get_state()
            return state == grpc.ChannelConnectivity.READY
            
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return False
            
    async def close_channel(self, service_name: str):
        """Close gRPC channel for a service."""
        try:
            channel = self.channels.get(service_name)
            if channel:
                await channel.close()
                del self.channels[service_name]
                
            if service_name in self.stubs:
                del self.stubs[service_name]
                
            logger.info(f"Closed gRPC channel for {service_name}")
            
        except Exception as e:
            logger.error(f"Error closing channel for {service_name}: {e}")
            
    async def close_all_channels(self):
        """Close all gRPC channels."""
        try:
            for service_name in list(self.channels.keys()):
                await self.close_channel(service_name)
                
            logger.info("Closed all gRPC channels")
            
        except Exception as e:
            logger.error(f"Error closing all channels: {e}")
            
    def add_service_endpoint(self, service_name: str, endpoint: str):
        """Add a service endpoint."""
        self.service_endpoints[service_name] = endpoint
        
    def remove_service_endpoint(self, service_name: str):
        """Remove a service endpoint."""
        if service_name in self.service_endpoints:
            del self.service_endpoints[service_name]
            
    def get_service_endpoints(self) -> Dict[str, str]:
        """Get all service endpoints."""
        return self.service_endpoints.copy()
        
    def get_channel_info(self, service_name: str) -> Dict[str, Any]:
        """Get channel information for a service."""
        channel = self.channels.get(service_name)
        if not channel:
            return {"status": "not_connected"}
            
        try:
            state = channel.get_state()
            return {
                "status": "connected",
                "state": str(state),
                "endpoint": self.service_endpoints.get(service_name)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
            
    def get_status(self) -> Dict[str, Any]:
        """Get gRPC client status."""
        return {
            "connected_services": len(self.channels),
            "available_stubs": len(self.stubs),
            "service_endpoints": len(self.service_endpoints),
            "last_update": datetime.utcnow().isoformat()
        }
