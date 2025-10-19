"""
Lucid Service Mesh - Consul Client
Consul integration for service discovery.

File: infrastructure/service-mesh/discovery/consul_client.py
Lines: ~300
Purpose: Consul integration
Dependencies: consul, asyncio
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Optional import for consul
try:
    import consul.aio
    CONSUL_AVAILABLE = True
except ImportError:
    CONSUL_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConsulClient:
    """
    Consul client for service discovery.
    
    Handles:
    - Service registration
    - Service discovery
    - Health checking
    - Key-value operations
    """
    
    def __init__(self, host: str = "consul", port: int = 8500):
        self.host = host
        self.port = port
        self.consul: Optional[consul.aio.Consul] = None
        self.registered_services: Dict[str, str] = {}
        
    async def initialize(self):
        """Initialize Consul client."""
        try:
            logger.info(f"Initializing Consul client: {self.host}:{self.port}")
            
            if not CONSUL_AVAILABLE:
                logger.warning("Consul library not available, using mock mode")
                self.consul = None
                return
            
            # Create Consul client
            self.consul = consul.aio.Consul(host=self.host, port=self.port)
            
            # Test connection
            await self._test_connection()
            
            logger.info("Consul client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Consul client: {e}")
            raise
            
    async def _test_connection(self):
        """Test Consul connection."""
        try:
            # Get leader status
            leader = await self.consul.status.leader()
            logger.info(f"Consul leader: {leader}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Consul: {e}")
            raise
            
    async def register_service(
        self,
        service_id: str,
        service_name: str,
        address: str,
        port: int,
        tags: List[str] = None,
        health_check_url: str = None,
        health_check_interval: str = "30s",
        health_check_timeout: str = "10s"
    ) -> bool:
        """
        Register a service with Consul.
        
        Args:
            service_id: Unique service identifier
            service_name: Service name
            address: Service address
            port: Service port
            tags: Service tags
            health_check_url: Health check URL
            health_check_interval: Health check interval
            health_check_timeout: Health check timeout
            
        Returns:
            True if registration successful
        """
        try:
            logger.info(f"Registering service: {service_name} ({service_id})")
            
            # Prepare service definition
            service_definition = {
                "ID": service_id,
                "Name": service_name,
                "Address": address,
                "Port": port,
                "Tags": tags or []
            }
            
            # Add health check if provided
            if health_check_url:
                service_definition["Check"] = consul.Check.http(
                    url=health_check_url,
                    interval=health_check_interval,
                    timeout=health_check_timeout
                )
                
            # Register service
            await self.consul.agent.service.register(**service_definition)
            
            # Track registered service
            self.registered_services[service_id] = service_name
            
            logger.info(f"Service {service_name} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
            return False
            
    async def deregister_service(self, service_id: str) -> bool:
        """
        Deregister a service from Consul.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if deregistration successful
        """
        try:
            logger.info(f"Deregistering service: {service_id}")
            
            # Deregister service
            await self.consul.agent.service.deregister(service_id)
            
            # Remove from tracking
            if service_id in self.registered_services:
                del self.registered_services[service_id]
                
            logger.info(f"Service {service_id} deregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
            
    async def discover_service(
        self,
        service_name: str,
        passing_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Discover services by name.
        
        Args:
            service_name: Service name to discover
            passing_only: Only return healthy services
            
        Returns:
            List of service instances
        """
        try:
            logger.debug(f"Discovering service: {service_name}")
            
            # Get service instances
            if passing_only:
                _, services = await self.consul.health.service(
                    service_name,
                    passing=True
                )
            else:
                _, services = await self.consul.health.service(service_name)
                
            # Format service data
            service_instances = []
            for service in services:
                service_data = service['Service']
                health_data = service.get('Checks', [])
                
                instance = {
                    "id": service_data['ID'],
                    "name": service_data['Name'],
                    "address": service_data['Address'],
                    "port": service_data['Port'],
                    "tags": service_data.get('Tags', []),
                    "health": self._determine_health_status(health_data)
                }
                service_instances.append(instance)
                
            logger.debug(f"Found {len(service_instances)} instances of {service_name}")
            return service_instances
            
        except Exception as e:
            logger.error(f"Failed to discover service {service_name}: {e}")
            return []
            
    def _determine_health_status(self, health_checks: List[Dict[str, Any]]) -> str:
        """Determine overall health status from health checks."""
        if not health_checks:
            return "unknown"
            
        # Check if all health checks are passing
        for check in health_checks:
            if check.get('Status') != 'passing':
                return "unhealthy"
                
        return "healthy"
        
    async def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """
        Get health status of a service.
        
        Args:
            service_name: Service name
            
        Returns:
            Health status information
        """
        try:
            # Get service health
            _, health_data = await self.consul.health.service(service_name)
            
            # Analyze health data
            total_instances = len(health_data)
            healthy_instances = 0
            unhealthy_instances = 0
            
            for service in health_data:
                health_status = self._determine_health_status(service.get('Checks', []))
                if health_status == "healthy":
                    healthy_instances += 1
                else:
                    unhealthy_instances += 1
                    
            return {
                "service_name": service_name,
                "total_instances": total_instances,
                "healthy_instances": healthy_instances,
                "unhealthy_instances": unhealthy_instances,
                "health_percentage": (healthy_instances / total_instances * 100) if total_instances > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get health for service {service_name}: {e}")
            return {
                "service_name": service_name,
                "total_instances": 0,
                "healthy_instances": 0,
                "unhealthy_instances": 0,
                "health_percentage": 0
            }
            
    async def set_key_value(self, key: str, value: str) -> bool:
        """
        Set a key-value pair in Consul.
        
        Args:
            key: Key name
            value: Value to store
            
        Returns:
            True if successful
        """
        try:
            await self.consul.kv.put(key, value)
            logger.debug(f"Set key-value: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set key-value {key}: {e}")
            return False
            
    async def get_key_value(self, key: str) -> Optional[str]:
        """
        Get a value by key from Consul.
        
        Args:
            key: Key name
            
        Returns:
            Value if found, None otherwise
        """
        try:
            _, data = await self.consul.kv.get(key)
            if data:
                return data['Value'].decode('utf-8')
            return None
            
        except Exception as e:
            logger.error(f"Failed to get key-value {key}: {e}")
            return None
            
    async def delete_key_value(self, key: str) -> bool:
        """
        Delete a key-value pair from Consul.
        
        Args:
            key: Key name
            
        Returns:
            True if successful
        """
        try:
            await self.consul.kv.delete(key)
            logger.debug(f"Deleted key-value: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete key-value {key}: {e}")
            return False
            
    async def list_services(self) -> List[str]:
        """
        List all registered services.
        
        Returns:
            List of service names
        """
        try:
            _, services = await self.consul.catalog.services()
            return list(services.keys())
            
        except Exception as e:
            logger.error(f"Failed to list services: {e}")
            return []
            
    async def get_consul_status(self) -> Dict[str, Any]:
        """
        Get Consul cluster status.
        
        Returns:
            Status information
        """
        try:
            # Get leader
            leader = await self.consul.status.leader()
            
            # Get peers
            peers = await self.consul.status.peers()
            
            # Get services count
            services = await self.list_services()
            
            return {
                "leader": leader,
                "peers": peers,
                "services_count": len(services),
                "registered_services": len(self.registered_services),
                "status": "connected"
            }
            
        except Exception as e:
            logger.error(f"Failed to get Consul status: {e}")
            return {
                "leader": None,
                "peers": [],
                "services_count": 0,
                "registered_services": len(self.registered_services),
                "status": "disconnected",
                "error": str(e)
            }
            
    async def cleanup(self):
        """Cleanup Consul client."""
        logger.info("Cleaning up Consul client...")
        
        # Deregister all registered services
        for service_id in list(self.registered_services.keys()):
            await self.deregister_service(service_id)
            
        logger.info("Consul client cleanup complete")
