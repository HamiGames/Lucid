"""
Lucid Service Mesh - gRPC Server
gRPC server for service mesh communication.

File: infrastructure/service-mesh/communication/grpc_server.py
Lines: ~280
Purpose: gRPC server
Dependencies: grpc, asyncio
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent import futures
import grpc
from grpc import aio

logger = logging.getLogger(__name__)


class GRPCServer:
    """
    gRPC server for service mesh communication.
    
    Handles:
    - gRPC server lifecycle
    - Service registration
    - Health checking
    - Metrics collection
    - Graceful shutdown
    """
    
    def __init__(self, port: int = 50051, max_workers: int = 10):
        self.port = port
        self.max_workers = max_workers
        self.server: Optional[aio.Server] = None
        self.registered_services: Dict[str, Any] = {}
        self.health_checks: Dict[str, callable] = {}
        self.running = False
        
    async def initialize(self):
        """Initialize gRPC server."""
        try:
            logger.info(f"Initializing gRPC Server on port {self.port}...")
            
            # Create server
            self.server = aio.server(
                futures.ThreadPoolExecutor(max_workers=self.max_workers)
            )
            
            # Add default services
            await self._add_default_services()
            
            logger.info("gRPC Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize gRPC Server: {e}")
            raise
            
    async def _add_default_services(self):
        """Add default services to the server."""
        # Add health check service
        await self.add_health_check_service()
        
    async def add_health_check_service(self):
        """Add health check service."""
        try:
            # Import health check service
            from grpc_health.v1 import health_pb2_grpc
            from grpc_health.v1.health import HealthServicer
            
            # Create health servicer
            health_servicer = HealthServicer()
            
            # Add to server
            health_pb2_grpc.add_HealthServicer_to_server(health_servicer, self.server)
            
            # Set all services as healthy
            for service_name in self.registered_services:
                health_servicer.set(service_name, health_pb2_grpc.HealthCheckResponse.SERVING)
                
            logger.info("Health check service added")
            
        except ImportError:
            logger.warning("grpc-health-checking not available, skipping health service")
        except Exception as e:
            logger.error(f"Failed to add health check service: {e}")
            
    async def add_service(
        self,
        service_name: str,
        servicer: Any,
        add_servicer_func: callable
    ):
        """
        Add a service to the gRPC server.
        
        Args:
            service_name: Service name
            servicer: Service implementation
            add_servicer_func: Function to add servicer to server
        """
        try:
            logger.info(f"Adding service: {service_name}")
            
            # Add servicer to server
            add_servicer_func(servicer, self.server)
            
            # Register service
            self.registered_services[service_name] = {
                "servicer": servicer,
                "add_func": add_servicer_func,
                "added_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Service {service_name} added successfully")
            
        except Exception as e:
            logger.error(f"Failed to add service {service_name}: {e}")
            raise
            
    async def remove_service(self, service_name: str):
        """Remove a service from the gRPC server."""
        try:
            if service_name in self.registered_services:
                del self.registered_services[service_name]
                logger.info(f"Service {service_name} removed")
            else:
                logger.warning(f"Service {service_name} not found")
                
        except Exception as e:
            logger.error(f"Failed to remove service {service_name}: {e}")
            
    async def start(self):
        """Start the gRPC server."""
        try:
            if self.running:
                logger.warning("gRPC server is already running")
                return
                
            logger.info(f"Starting gRPC server on port {self.port}...")
            
            # Add server port
            listen_addr = f'[::]:{self.port}'
            self.server.add_insecure_port(listen_addr)
            
            # Start server
            await self.server.start()
            self.running = True
            
            logger.info(f"gRPC server started on {listen_addr}")
            
        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}")
            raise
            
    async def stop(self, grace_period: int = 30):
        """Stop the gRPC server."""
        try:
            if not self.running:
                logger.warning("gRPC server is not running")
                return
                
            logger.info("Stopping gRPC server...")
            
            # Stop server
            await self.server.stop(grace_period)
            self.running = False
            
            logger.info("gRPC server stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop gRPC server: {e}")
            raise
            
    async def wait_for_termination(self):
        """Wait for server termination."""
        try:
            if self.server:
                await self.server.wait_for_termination()
                
        except Exception as e:
            logger.error(f"Error waiting for server termination: {e}")
            
    def add_health_check(self, service_name: str, health_check_func: callable):
        """Add health check function for a service."""
        self.health_checks[service_name] = health_check_func
        
    def remove_health_check(self, service_name: str):
        """Remove health check function for a service."""
        if service_name in self.health_checks:
            del self.health_checks[service_name]
            
    async def check_service_health(self, service_name: str) -> bool:
        """Check health of a specific service."""
        try:
            if service_name in self.health_checks:
                health_func = self.health_checks[service_name]
                return await health_func()
            else:
                # Default health check - service is healthy if registered
                return service_name in self.registered_services
                
        except Exception as e:
            logger.error(f"Health check failed for service {service_name}: {e}")
            return False
            
    async def get_server_health(self) -> Dict[str, Any]:
        """Get overall server health."""
        try:
            health_status = {}
            
            for service_name in self.registered_services:
                health_status[service_name] = await self.check_service_health(service_name)
                
            return {
                "server_running": self.running,
                "services_count": len(self.registered_services),
                "healthy_services": sum(1 for healthy in health_status.values() if healthy),
                "service_health": health_status,
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get server health: {e}")
            return {
                "server_running": self.running,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
            
    def get_registered_services(self) -> List[str]:
        """Get list of registered service names."""
        return list(self.registered_services.keys())
        
    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered service."""
        return self.registered_services.get(service_name)
        
    def get_status(self) -> Dict[str, Any]:
        """Get gRPC server status."""
        return {
            "running": self.running,
            "port": self.port,
            "max_workers": self.max_workers,
            "registered_services": len(self.registered_services),
            "health_checks": len(self.health_checks),
            "last_update": datetime.utcnow().isoformat()
        }
        
    async def cleanup(self):
        """Cleanup gRPC server."""
        logger.info("Cleaning up gRPC server...")
        
        if self.running:
            await self.stop()
            
        # Clear registered services
        self.registered_services.clear()
        self.health_checks.clear()
        
        logger.info("gRPC server cleanup complete")
