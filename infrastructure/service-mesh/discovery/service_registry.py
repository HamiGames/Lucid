"""
Lucid Service Mesh - Service Registry
Service registration and discovery management.

File: infrastructure/service-mesh/discovery/service_registry.py
Lines: ~280
Purpose: Service registration
Dependencies: consul_client, asyncio
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .consul_client import ConsulClient

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Service registry for service discovery.
    
    Handles:
    - Service registration
    - Service discovery
    - Health monitoring
    - Service metadata management
    """
    
    def __init__(self, consul_host: str = "consul", consul_port: int = 8500):
        self.consul_client = ConsulClient(consul_host, consul_port)
        self.registered_services: Dict[str, Dict[str, Any]] = {}
        self.service_metadata: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize service registry."""
        try:
            logger.info("Initializing Service Registry...")
            
            # Initialize Consul client
            await self.consul_client.initialize()
            
            logger.info("Service Registry initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Service Registry: {e}")
            raise
            
    async def register_service(
        self,
        service_id: str,
        service_name: str,
        address: str,
        port: int,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        health_check_url: str = None
    ) -> bool:
        """
        Register a service in the registry.
        
        Args:
            service_id: Unique service identifier
            service_name: Service name
            address: Service address
            port: Service port
            tags: Service tags
            metadata: Service metadata
            health_check_url: Health check URL
            
        Returns:
            True if registration successful
        """
        try:
            logger.info(f"Registering service: {service_name} ({service_id})")
            
            # Register with Consul
            success = await self.consul_client.register_service(
                service_id=service_id,
                service_name=service_name,
                address=address,
                port=port,
                tags=tags,
                health_check_url=health_check_url
            )
            
            if success:
                # Store service information
                self.registered_services[service_id] = {
                    "service_id": service_id,
                    "service_name": service_name,
                    "address": address,
                    "port": port,
                    "tags": tags or [],
                    "health_check_url": health_check_url,
                    "registered_at": datetime.utcnow().isoformat()
                }
                
                # Store metadata
                if metadata:
                    self.service_metadata[service_id] = metadata
                    
                logger.info(f"Service {service_name} registered successfully")
                return True
            else:
                logger.error(f"Failed to register service {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering service {service_name}: {e}")
            return False
            
    async def deregister_service(self, service_id: str) -> bool:
        """
        Deregister a service from the registry.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if deregistration successful
        """
        try:
            logger.info(f"Deregistering service: {service_id}")
            
            # Deregister from Consul
            success = await self.consul_client.deregister_service(service_id)
            
            if success:
                # Remove from local tracking
                if service_id in self.registered_services:
                    del self.registered_services[service_id]
                    
                if service_id in self.service_metadata:
                    del self.service_metadata[service_id]
                    
                logger.info(f"Service {service_id} deregistered successfully")
                return True
            else:
                logger.error(f"Failed to deregister service {service_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deregistering service {service_id}: {e}")
            return False
            
    async def discover_service(
        self,
        service_name: str,
        passing_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Discover service instances.
        
        Args:
            service_name: Service name to discover
            passing_only: Only return healthy services
            
        Returns:
            List of service instances
        """
        try:
            logger.debug(f"Discovering service: {service_name}")
            
            # Discover from Consul
            instances = await self.consul_client.discover_service(
                service_name, passing_only
            )
            
            # Add metadata to instances
            for instance in instances:
                service_id = instance["id"]
                if service_id in self.service_metadata:
                    instance["metadata"] = self.service_metadata[service_id]
                    
            logger.debug(f"Found {len(instances)} instances of {service_name}")
            return instances
            
        except Exception as e:
            logger.error(f"Error discovering service {service_name}: {e}")
            return []
            
    async def get_service_instances(
        self,
        service_name: str,
        filter_tags: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get service instances with optional tag filtering.
        
        Args:
            service_name: Service name
            filter_tags: Tags to filter by
            
        Returns:
            List of filtered service instances
        """
        try:
            # Get all instances
            instances = await self.discover_service(service_name)
            
            # Filter by tags if provided
            if filter_tags:
                filtered_instances = []
                for instance in instances:
                    instance_tags = instance.get("tags", [])
                    if any(tag in instance_tags for tag in filter_tags):
                        filtered_instances.append(instance)
                return filtered_instances
                
            return instances
            
        except Exception as e:
            logger.error(f"Error getting service instances for {service_name}: {e}")
            return []
            
    async def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """
        Get health status of a service.
        
        Args:
            service_name: Service name
            
        Returns:
            Health status information
        """
        try:
            return await self.consul_client.get_service_health(service_name)
            
        except Exception as e:
            logger.error(f"Error getting health for service {service_name}: {e}")
            return {
                "service_name": service_name,
                "total_instances": 0,
                "healthy_instances": 0,
                "unhealthy_instances": 0,
                "health_percentage": 0
            }
            
    async def update_service_metadata(
        self,
        service_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update service metadata.
        
        Args:
            service_id: Service identifier
            metadata: New metadata
            
        Returns:
            True if update successful
        """
        try:
            if service_id in self.registered_services:
                self.service_metadata[service_id] = metadata
                logger.info(f"Updated metadata for service {service_id}")
                return True
            else:
                logger.warning(f"Service {service_id} not found for metadata update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating metadata for service {service_id}: {e}")
            return False
            
    async def get_service_metadata(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Get service metadata.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Service metadata or None
        """
        return self.service_metadata.get(service_id)
        
    async def list_registered_services(self) -> List[Dict[str, Any]]:
        """
        List all registered services.
        
        Returns:
            List of registered service information
        """
        return list(self.registered_services.values())
        
    async def list_available_services(self) -> List[str]:
        """
        List all available services in the registry.
        
        Returns:
            List of service names
        """
        try:
            return await self.consul_client.list_services()
            
        except Exception as e:
            logger.error(f"Error listing available services: {e}")
            return []
            
    async def monitor_service_health(
        self,
        service_name: str,
        callback: callable,
        interval: int = 30
    ):
        """
        Monitor service health and call callback on changes.
        
        Args:
            service_name: Service name to monitor
            callback: Callback function to call on health changes
            interval: Monitoring interval in seconds
        """
        try:
            last_health = None
            
            while True:
                current_health = await self.get_service_health(service_name)
                
                if last_health != current_health:
                    await callback(service_name, current_health, last_health)
                    last_health = current_health
                    
                await asyncio.sleep(interval)
                
        except Exception as e:
            logger.error(f"Error monitoring health for service {service_name}: {e}")
            
    async def get_registry_status(self) -> Dict[str, Any]:
        """
        Get registry status information.
        
        Returns:
            Registry status
        """
        try:
            consul_status = await self.consul_client.get_consul_status()
            
            return {
                "consul_status": consul_status,
                "registered_services_count": len(self.registered_services),
                "services_with_metadata": len(self.service_metadata),
                "last_update": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting registry status: {e}")
            return {
                "consul_status": {"status": "error", "error": str(e)},
                "registered_services_count": len(self.registered_services),
                "services_with_metadata": len(self.service_metadata),
                "last_update": datetime.utcnow().isoformat()
            }
            
    async def cleanup(self):
        """Cleanup service registry."""
        logger.info("Cleaning up Service Registry...")
        
        # Deregister all services
        for service_id in list(self.registered_services.keys()):
            await self.deregister_service(service_id)
            
        # Cleanup Consul client
        await self.consul_client.cleanup()
        
        logger.info("Service Registry cleanup complete")
