#!/usr/bin/env python3
"""
Lucid Admin Interface - Service Discovery
Step 24: Admin Container & Integration

Service discovery module for finding and connecting to other services
in the Lucid container ecosystem.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import httpx
import aiohttp

from admin.config import get_admin_config

logger = logging.getLogger(__name__)


class DiscoveryMethod(Enum):
    """Service discovery methods"""
    ENV_VARS = "env_vars"  # From environment variables
    DNS = "dns"  # DNS-based discovery
    CONSUL = "consul"  # Consul service discovery
    REDIS = "redis"  # Redis-based registry


@dataclass
class ServiceInfo:
    """Service information"""
    name: str
    url: str
    port: int
    health_endpoint: str
    status: str = "unknown"
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ServiceDiscovery:
    """
    Service discovery for finding other services.
    
    Supports multiple discovery methods:
    - Environment variables (primary)
    - DNS-based discovery
    - Consul service discovery
    - Redis-based registry
    """
    
    def __init__(self):
        self.config = get_admin_config()
        self.discovery_method = os.getenv("SERVICE_DISCOVERY_METHOD", "env_vars")
        self.services: Dict[str, ServiceInfo] = {}
        self.consul_host = os.getenv("CONSUL_HOST", "lucid-service-mesh-controller")
        self.consul_port = int(os.getenv("CONSUL_PORT", "8500"))
        self.redis_url = os.getenv("REDIS_URL", "")
        self.http_client: Optional[httpx.AsyncClient] = None
        self._initialize_from_env()
    
    def _initialize_from_env(self):
        """Initialize services from environment variables"""
        # Port defaults - configurable via environment variables
        api_gateway_port = int(os.getenv("API_GATEWAY_PORT", "8080"))
        blockchain_port = int(os.getenv("BLOCKCHAIN_ENGINE_PORT", os.getenv("BLOCKCHAIN_PORT", "8084")))
        session_port = int(os.getenv("SESSION_API_PORT", os.getenv("SESSION_MANAGEMENT_PORT", "8113")))
        node_mgmt_port = int(os.getenv("NODE_MANAGEMENT_PORT", "8095"))
        auth_port = int(os.getenv("AUTH_SERVICE_PORT", "8089"))
        
        service_mappings = {
            "api_gateway": {
                "url": self.config.api_gateway_url,
                "port": api_gateway_port,
                "health_endpoint": "/health"
            },
            "blockchain": {
                "url": self.config.blockchain_url,
                "port": blockchain_port,
                "health_endpoint": "/health"
            },
            "session_management": {
                "url": self.config.session_management_url,
                "port": session_port,
                "health_endpoint": "/health"
            },
            "node_management": {
                "url": self.config.node_management_url,
                "port": node_mgmt_port,
                "health_endpoint": "/health"
            },
            "auth_service": {
                "url": self.config.auth_service_url,
                "port": auth_port,
                "health_endpoint": "/health"
            }
        }
        
        for name, info in service_mappings.items():
            if info["url"]:
                # Extract port from URL if present
                port = info["port"]
                if ":" in info["url"]:
                    try:
                        port = int(info["url"].split(":")[-1].split("/")[0])
                    except ValueError:
                        pass
                
                self.services[name] = ServiceInfo(
                    name=name,
                    url=info["url"],
                    port=port,
                    health_endpoint=info["health_endpoint"],
                    last_seen=datetime.now(timezone.utc)
                )
    
    async def initialize(self):
        """Initialize service discovery"""
        try:
            self.http_client = httpx.AsyncClient(timeout=10.0)
            
            # Try to discover services based on method
            if self.discovery_method == "consul":
                await self._discover_from_consul()
            elif self.discovery_method == "redis":
                await self._discover_from_redis()
            elif self.discovery_method == "dns":
                await self._discover_from_dns()
            
            logger.info(f"Service discovery initialized with {len(self.services)} services")
            
        except Exception as e:
            logger.error(f"Failed to initialize service discovery: {e}")
            # Fallback to env vars only
            logger.info("Falling back to environment variable discovery")
    
    async def close(self):
        """Close service discovery"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    async def _discover_from_consul(self):
        """Discover services from Consul"""
        try:
            consul_url = f"http://{self.consul_host}:{self.consul_port}/v1/catalog/services"
            
            if not self.http_client:
                self.http_client = httpx.AsyncClient(timeout=10.0)
            
            response = await self.http_client.get(consul_url)
            
            if response.status_code == 200:
                services = response.json()
                
                for service_name, tags in services.items():
                    if service_name.startswith("lucid-"):
                        # Get service details
                        service_url = f"http://{self.consul_host}:{self.consul_port}/v1/health/service/{service_name}"
                        service_response = await self.http_client.get(service_url)
                        
                        if service_response.status_code == 200:
                            service_data = service_response.json()
                            if service_data:
                                service_info = service_data[0]
                                node = service_info.get("Node", {})
                                service = service_info.get("Service", {})
                                
                                default_port = int(os.getenv("API_GATEWAY_PORT", "8080"))
                                default_address = os.getenv("CONSUL_NODE_ADDRESS", "localhost")
                                service_port = service.get("Port", default_port)
                                service_address = service.get('Address', node.get('Address', default_address))
                                
                                self.services[service_name] = ServiceInfo(
                                    name=service_name,
                                    url=f"http://{service_address}:{service_port}",
                                    port=service_port,
                                    health_endpoint="/health",
                                    status="healthy" if service_info.get("Checks", [{}])[0].get("Status") == "passing" else "unhealthy",
                                    last_seen=datetime.now(timezone.utc)
                                )
                
                logger.info(f"Discovered {len(services)} services from Consul")
                
        except Exception as e:
            logger.warning(f"Consul discovery failed: {e}")
    
    async def _discover_from_redis(self):
        """Discover services from Redis registry"""
        try:
            # Try redis.asyncio (redis >= 5.0) first, fallback to aioredis
            try:
                import redis.asyncio as aioredis
            except ImportError:
                try:
                    import aioredis
                except ImportError:
                    logger.warning("Redis async client not available")
                    return
            
            if not self.redis_url:
                logger.warning("Redis URL not configured for service discovery")
                return
            
            redis_client = aioredis.from_url(self.redis_url)
            
            # Get all service keys
            service_keys = await redis_client.keys("service:*")
            
            for key in service_keys:
                service_name = key.decode().replace("service:", "")
                service_data = await redis_client.hgetall(key)
                
                if service_data:
                    port_bytes = service_data.get(b"port", b"")
                    if port_bytes:
                        try:
                            if isinstance(port_bytes, bytes):
                                port = int(port_bytes.decode())
                            else:
                                port = int(port_bytes)
                        except (ValueError, AttributeError, TypeError):
                            port = int(os.getenv("API_GATEWAY_PORT", "8080"))
                    else:
                        port = int(os.getenv("API_GATEWAY_PORT", "8080"))
                    
                    self.services[service_name] = ServiceInfo(
                        name=service_name,
                        url=service_data.get(b"url", b"").decode(),
                        port=port,
                        health_endpoint=service_data.get(b"health_endpoint", b"/health").decode(),
                        status=service_data.get(b"status", b"unknown").decode(),
                        last_seen=datetime.fromisoformat(service_data.get(b"last_heartbeat", datetime.now(timezone.utc).isoformat().encode()).decode())
                    )
            
            await redis_client.close()
            logger.info(f"Discovered {len(service_keys)} services from Redis")
            
        except Exception as e:
            logger.warning(f"Redis discovery failed: {e}")
    
    async def _discover_from_dns(self):
        """Discover services via DNS"""
        try:
            # Standard service names in Docker Compose
            service_names = [
                "lucid-api-gateway",
                "lucid-blockchain-engine",
                "lucid-session-api",
                "lucid-node-management",
                "lucid-auth-service"
            ]
            
            for service_name in service_names:
                # Try to resolve DNS
                try:
                    # In Docker, service names resolve to container IPs
                    # We'll use the service name directly as hostname
                    url = f"http://{service_name}"
                    
                    # Try health check to verify service exists
                    if self.http_client:
                        try:
                            health_url = f"{url}/health"
                            response = await self.http_client.get(health_url, timeout=2.0)
                            if response.status_code == 200:
                                # Extract port from service name or use configurable defaults
                                port = int(os.getenv("API_GATEWAY_PORT", "8080"))
                                if "gateway" in service_name:
                                    port = int(os.getenv("API_GATEWAY_PORT", "8080"))
                                elif "blockchain" in service_name:
                                    port = int(os.getenv("BLOCKCHAIN_ENGINE_PORT", os.getenv("BLOCKCHAIN_PORT", "8084")))
                                elif "session" in service_name:
                                    port = int(os.getenv("SESSION_API_PORT", os.getenv("SESSION_MANAGEMENT_PORT", "8113")))
                                elif "node" in service_name:
                                    port = int(os.getenv("NODE_MANAGEMENT_PORT", "8095"))
                                elif "auth" in service_name:
                                    port = int(os.getenv("AUTH_SERVICE_PORT", "8089"))
                                
                                self.services[service_name] = ServiceInfo(
                                    name=service_name,
                                    url=url,
                                    port=port,
                                    health_endpoint="/health",
                                    status="healthy",
                                    last_seen=datetime.now(timezone.utc)
                                )
                        except Exception:
                            pass  # Service not available
                except Exception:
                    pass  # DNS resolution failed
            
            logger.info(f"Discovered {len(self.services)} services via DNS")
            
        except Exception as e:
            logger.warning(f"DNS discovery failed: {e}")
    
    async def discover_service(self, service_name: str) -> Optional[ServiceInfo]:
        """
        Discover a specific service.
        
        Args:
            service_name: Name of the service to discover
            
        Returns:
            ServiceInfo if found, None otherwise
        """
        # Check if already known
        if service_name in self.services:
            return self.services[service_name]
        
        # Try discovery methods
        if self.discovery_method == "consul":
            await self._discover_from_consul()
        elif self.discovery_method == "redis":
            await self._discover_from_redis()
        elif self.discovery_method == "dns":
            await self._discover_from_dns()
        
        return self.services.get(service_name)
    
    async def discover_all_services(self) -> Dict[str, ServiceInfo]:
        """Discover all available services"""
        if self.discovery_method == "consul":
            await self._discover_from_consul()
        elif self.discovery_method == "redis":
            await self._discover_from_redis()
        elif self.discovery_method == "dns":
            await self._discover_from_dns()
        
        return self.services.copy()
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get URL for a service"""
        service = self.services.get(service_name)
        return service.url if service else None
    
    def get_service_port(self, service_name: str) -> Optional[int]:
        """Get port for a service"""
        service = self.services.get(service_name)
        return service.port if service else None


# Global service discovery instance
_service_discovery: Optional[ServiceDiscovery] = None


async def get_service_discovery() -> ServiceDiscovery:
    """Get global service discovery instance"""
    global _service_discovery
    if _service_discovery is None:
        _service_discovery = ServiceDiscovery()
        await _service_discovery.initialize()
    return _service_discovery


async def close_service_discovery():
    """Close global service discovery instance"""
    global _service_discovery
    if _service_discovery:
        await _service_discovery.close()
        _service_discovery = None

