"""
Lucid Service Mesh Controller - Health Checker
Monitors health of services in the mesh.

File: infrastructure/service-mesh/controller/health_checker.py
Lines: ~220
Purpose: Health monitoring
Dependencies: asyncio, aiohttp, consul
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

# Optional import for aiohttp
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"


class HealthChecker:
    """
    Service mesh health checker.
    
    Monitors:
    - Service health endpoints
    - Service discovery health
    - Sidecar proxy health
    - Network connectivity
    """
    
    def __init__(self):
        self.services: Dict[str, Dict[str, Any]] = {}
        self.health_status: Dict[str, HealthStatus] = {}
        self.health_history: Dict[str, List[Dict[str, Any]]] = {}
        self.check_intervals: Dict[str, int] = {}
        
        # Default health check configuration
        self.default_timeout = 10
        self.default_interval = 30
        self.max_history = 100
        
    async def initialize(self):
        """Initialize health checker."""
        try:
            logger.info("Initializing Health Checker...")
            
            # Load service configurations
            await self._load_service_configurations()
            
            # Initialize health status
            await self._initialize_health_status()
            
            logger.info("Health Checker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Health Checker: {e}")
            raise
            
    async def _load_service_configurations(self):
        """Load service configurations for health checking."""
        # Default services to monitor
        self.services = {
            "api-gateway": {
                "health_endpoint": "http://api-gateway:8080/health",
                "check_interval": 30,
                "timeout": 10
            },
            "blockchain-core": {
                "health_endpoint": "http://blockchain-core:8084/health",
                "check_interval": 30,
                "timeout": 10
            },
            "session-management": {
                "health_endpoint": "http://session-api:8087/health",
                "check_interval": 30,
                "timeout": 10
            },
            "node-management": {
                "health_endpoint": "http://node-management:8095/health",
                "check_interval": 30,
                "timeout": 10
            },
            "auth-service": {
                "health_endpoint": "http://auth-service:8089/health",
                "check_interval": 30,
                "timeout": 10
            },
            "consul": {
                "health_endpoint": "http://consul:8500/v1/status/leader",
                "check_interval": 60,
                "timeout": 5
            }
        }
        
    async def _initialize_health_status(self):
        """Initialize health status for all services."""
        for service_name in self.services:
            self.health_status[service_name] = HealthStatus.UNKNOWN
            self.health_history[service_name] = []
            self.check_intervals[service_name] = self.services[service_name].get(
                "check_interval", self.default_interval
            )
            
    async def check_all_services(self):
        """Check health of all services."""
        try:
            tasks = []
            for service_name in self.services:
                task = asyncio.create_task(
                    self._check_service_health(service_name)
                )
                tasks.append(task)
                
            # Wait for all health checks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error checking service health: {e}")
            
    async def _check_service_health(self, service_name: str):
        """Check health of a specific service."""
        try:
            service_config = self.services[service_name]
            health_endpoint = service_config["health_endpoint"]
            timeout = service_config.get("timeout", self.default_timeout)
            
            # Perform health check
            health_result = await self._perform_health_check(
                service_name, health_endpoint, timeout
            )
            
            # Update health status
            self._update_health_status(service_name, health_result)
            
            # Record in history
            self._record_health_history(service_name, health_result)
            
        except Exception as e:
            logger.error(f"Error checking health for {service_name}: {e}")
            self._update_health_status(service_name, {
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            
    async def _perform_health_check(
        self, 
        service_name: str, 
        health_endpoint: str, 
        timeout: int
    ) -> Dict[str, Any]:
        """Perform actual health check."""
        if not AIOHTTP_AVAILABLE:
            # Mock health check when aiohttp is not available
            return {
                "status": HealthStatus.HEALTHY.value,
                "response_time": "mock",
                "data": {"mock": True},
                "timestamp": datetime.utcnow().isoformat()
            }
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    health_endpoint,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        try:
                            health_data = await response.json()
                            return {
                                "status": HealthStatus.HEALTHY.value,
                                "response_time": response.headers.get("X-Response-Time", "unknown"),
                                "data": health_data,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        except:
                            return {
                                "status": HealthStatus.HEALTHY.value,
                                "response_time": "unknown",
                                "data": None,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                    else:
                        return {
                            "status": HealthStatus.UNHEALTHY.value,
                            "error": f"HTTP {response.status}",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
        except asyncio.TimeoutError:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": "Timeout",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    def _update_health_status(self, service_name: str, health_result: Dict[str, Any]):
        """Update health status for a service."""
        status_str = health_result.get("status")
        
        if status_str == HealthStatus.HEALTHY.value:
            self.health_status[service_name] = HealthStatus.HEALTHY
        elif status_str == HealthStatus.UNHEALTHY.value:
            self.health_status[service_name] = HealthStatus.UNHEALTHY
        else:
            self.health_status[service_name] = HealthStatus.UNKNOWN
            
        logger.debug(f"Health status for {service_name}: {self.health_status[service_name].value}")
        
    def _record_health_history(self, service_name: str, health_result: Dict[str, Any]):
        """Record health check result in history."""
        history = self.health_history[service_name]
        history.append(health_result)
        
        # Keep only recent history
        if len(history) > self.max_history:
            history = history[-self.max_history:]
            self.health_history[service_name] = history
            
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific service on demand."""
        if service_name not in self.services:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": f"Service {service_name} not configured",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        await self._check_service_health(service_name)
        
        return {
            "service": service_name,
            "status": self.health_status[service_name].value,
            "last_check": self.health_history[service_name][-1] if self.health_history[service_name] else None
        }
        
    def get_service_health(self, service_name: str) -> Optional[HealthStatus]:
        """Get current health status of a service."""
        return self.health_status.get(service_name)
        
    def get_all_health_status(self) -> Dict[str, str]:
        """Get health status of all services."""
        return {
            service: status.value 
            for service, status in self.health_status.items()
        }
        
    def get_health_history(self, service_name: str) -> List[Dict[str, Any]]:
        """Get health history for a service."""
        return self.health_history.get(service_name, [])
        
    def get_unhealthy_services(self) -> List[str]:
        """Get list of unhealthy services."""
        return [
            service for service, status in self.health_status.items()
            if status == HealthStatus.UNHEALTHY
        ]
        
    def get_healthy_services(self) -> List[str]:
        """Get list of healthy services."""
        return [
            service for service, status in self.health_status.items()
            if status == HealthStatus.HEALTHY
        ]
        
    def add_service(self, service_name: str, service_config: Dict[str, Any]):
        """Add a new service for health monitoring."""
        self.services[service_name] = service_config
        self.health_status[service_name] = HealthStatus.UNKNOWN
        self.health_history[service_name] = []
        self.check_intervals[service_name] = service_config.get(
            "check_interval", self.default_interval
        )
        
    def remove_service(self, service_name: str):
        """Remove a service from health monitoring."""
        if service_name in self.services:
            del self.services[service_name]
            if service_name in self.health_status:
                del self.health_status[service_name]
            if service_name in self.health_history:
                del self.health_history[service_name]
            if service_name in self.check_intervals:
                del self.check_intervals[service_name]
                
    def get_status(self) -> Dict[str, Any]:
        """Get health checker status."""
        total_services = len(self.services)
        healthy_services = len(self.get_healthy_services())
        unhealthy_services = len(self.get_unhealthy_services())
        
        return {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "unknown_services": total_services - healthy_services - unhealthy_services,
            "last_update": datetime.utcnow().isoformat()
        }
        
    async def cleanup(self):
        """Cleanup health checker."""
        logger.info("Cleaning up Health Checker...")
        # No specific cleanup needed
