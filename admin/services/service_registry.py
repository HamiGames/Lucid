#!/usr/bin/env python3
"""
Lucid Admin Interface - Service Registry
Step 24: Admin Container & Integration

Service registry integration for registering admin-interface service
and discovering other services in the Lucid ecosystem.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field
import httpx
import json

from admin.config import get_admin_config

logger = logging.getLogger(__name__)


@dataclass
class RegistryConfig:
    """Service registry configuration"""
    enabled: bool = True
    registry_url: str = ""
    service_name: str = "lucid-admin-interface"
    service_port: int = 8083
    health_endpoint: str = "/admin/health"
    heartbeat_interval: int = 30
    registration_timeout: int = 10


class ServiceRegistry:
    """
    Service registry integration for admin-interface.
    
    Handles:
    - Service registration
    - Heartbeat updates
    - Service discovery
    - Health status reporting
    """
    
    def __init__(self):
        self.config = get_admin_config()
        self.registry_config = RegistryConfig(
            enabled=os.getenv("SERVICE_REGISTRY_ENABLED", "true").lower() == "true",
            registry_url=os.getenv("SERVICE_REGISTRY_URL", ""),
            service_name=self.config.service.service_name,
            service_port=self.config.service.port,
            health_endpoint="/admin/health",
            heartbeat_interval=int(os.getenv("SERVICE_REGISTRY_HEARTBEAT_INTERVAL", "30")),
            registration_timeout=int(os.getenv("SERVICE_REGISTRY_TIMEOUT", "10"))
        )
        self.http_client: Optional[httpx.AsyncClient] = None
        self.registered: bool = False
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize service registry"""
        try:
            if not self.registry_config.enabled:
                logger.info("Service registry is disabled")
                return
            
            if not self.registry_config.registry_url:
                logger.warning("Service registry URL not configured")
                return
            
            self.http_client = httpx.AsyncClient(timeout=self.registry_config.registration_timeout)
            
            # Register service
            await self.register()
            
            # Start heartbeat task
            if self.registered:
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info("Service registry initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize service registry: {e}")
            # Continue without registry - not critical
    
    async def close(self):
        """Close service registry"""
        # Stop heartbeat
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Unregister service
        if self.registered:
            await self.unregister()
        
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    async def register(self) -> bool:
        """
        Register admin-interface service with registry.
        
        Returns:
            True if registration successful, False otherwise
        """
        if not self.registry_config.enabled or not self.registry_config.registry_url:
            return False
        
        try:
            if not self.http_client:
                self.http_client = httpx.AsyncClient(timeout=self.registry_config.registration_timeout)
            
            # Get service hostname (container name or host)
            service_host = os.getenv("ADMIN_INTERFACE_HOST", "lucid-admin-interface")
            if service_host == "0.0.0.0":
                service_host = "lucid-admin-interface"  # Use container name in Docker
            
            service_url = f"http://{service_host}:{self.registry_config.service_port}"
            
            registration_data = {
                "name": self.registry_config.service_name,
                "url": service_url,
                "port": self.registry_config.service_port,
                "health_endpoint": self.registry_config.health_endpoint,
                "metadata": {
                    "version": self.config.service.version,
                    "service_type": "admin-interface",
                    "cluster": "support",
                    "environment": os.getenv("LUCID_ENV", "production"),
                    "platform": os.getenv("LUCID_PLATFORM", "arm64")
                }
            }
            
            registry_endpoint = f"{self.registry_config.registry_url.rstrip('/')}/api/v1/services/register"
            
            response = await self.http_client.post(
                registry_endpoint,
                json=registration_data,
                timeout=self.registry_config.registration_timeout
            )
            
            if response.status_code in [200, 201]:
                self.registered = True
                logger.info(f"Service {self.registry_config.service_name} registered successfully")
                return True
            else:
                logger.warning(f"Service registration failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Service registration error: {e}")
            return False
    
    async def unregister(self) -> bool:
        """
        Unregister admin-interface service from registry.
        
        Returns:
            True if unregistration successful, False otherwise
        """
        if not self.registered or not self.http_client:
            return False
        
        try:
            registry_endpoint = f"{self.registry_config.registry_url.rstrip('/')}/api/v1/services/{self.registry_config.service_name}"
            
            response = await self.http_client.delete(
                registry_endpoint,
                timeout=self.registry_config.registration_timeout
            )
            
            if response.status_code in [200, 204]:
                self.registered = False
                logger.info(f"Service {self.registry_config.service_name} unregistered successfully")
                return True
            else:
                logger.warning(f"Service unregistration failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Service unregistration error: {e}")
            return False
    
    async def send_heartbeat(self) -> bool:
        """
        Send heartbeat to registry.
        
        Returns:
            True if heartbeat successful, False otherwise
        """
        if not self.registered or not self.http_client:
            return False
        
        try:
            registry_endpoint = f"{self.registry_config.registry_url.rstrip('/')}/api/v1/services/{self.registry_config.service_name}/heartbeat"
            
            response = await self.http_client.post(
                registry_endpoint,
                timeout=self.registry_config.registration_timeout
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Heartbeat failed: {response.status_code}")
                # Try to re-register if heartbeat fails
                if response.status_code == 404:
                    await self.register()
                return False
                
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False
    
    async def _heartbeat_loop(self):
        """Background task for sending heartbeats"""
        while self.registered:
            try:
                await asyncio.sleep(self.registry_config.heartbeat_interval)
                await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Discover a service from registry.
        
        Args:
            service_name: Name of the service to discover
            
        Returns:
            Service information dict if found, None otherwise
        """
        if not self.registry_config.enabled or not self.http_client:
            return None
        
        try:
            registry_endpoint = f"{self.registry_config.registry_url.rstrip('/')}/api/v1/services/discover/{service_name}"
            
            response = await self.http_client.get(
                registry_endpoint,
                timeout=self.registry_config.registration_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("service")
            else:
                return None
                
        except Exception as e:
            logger.error(f"Service discovery error: {e}")
            return None
    
    async def list_services(self) -> List[Dict[str, Any]]:
        """
        List all registered services.
        
        Returns:
            List of service information dicts
        """
        if not self.registry_config.enabled or not self.http_client:
            return []
        
        try:
            registry_endpoint = f"{self.registry_config.registry_url.rstrip('/')}/api/v1/services"
            
            response = await self.http_client.get(
                registry_endpoint,
                timeout=self.registry_config.registration_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("services", [])
            else:
                return []
                
        except Exception as e:
            logger.error(f"List services error: {e}")
            return []


# Global service registry instance
_service_registry: Optional[ServiceRegistry] = None


async def get_service_registry() -> ServiceRegistry:
    """Get global service registry instance"""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
        await _service_registry.initialize()
    return _service_registry


async def close_service_registry():
    """Close global service registry instance"""
    global _service_registry
    if _service_registry:
        await _service_registry.close()
        _service_registry = None

