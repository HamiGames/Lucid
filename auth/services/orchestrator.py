"""
Lucid Authentication Service - Service Orchestrator
Manages Docker container orchestration and service spawning

File: auth/services/orchestrator.py
Purpose: Orchestrate Docker containers and spawn clone services
Dependencies: docker (optional), httpx, asyncio, logging
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service status enumeration"""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    REMOVED = "removed"


class ServiceOrchestrator:
    """
    Service orchestrator for spawning and managing Docker containers.
    
    Supports:
    - Spawning MongoDB clone instances for nodes
    - Managing service lifecycle
    - Monitoring spawned services
    - Resource allocation and limits
    """
    
    def __init__(self, docker_socket: Optional[str] = None, enabled: bool = False):
        """
        Initialize service orchestrator.
        
        Args:
            docker_socket: Path to Docker socket (default: /var/run/docker.sock)
            enabled: Whether orchestration is enabled (default: False for security)
        """
        self.enabled = enabled
        self.docker_socket = docker_socket or os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
        self.docker_client = None
        self.spawned_services: Dict[str, Dict[str, Any]] = {}
        
        if self.enabled:
            self._initialize_docker_client()
    
    def _initialize_docker_client(self):
        """Initialize Docker client (if orchestration is enabled)"""
        try:
            # Try to import docker library
            import docker
            self.docker_client = docker.DockerClient(base_url=self.docker_socket)
            logger.info(f"Service orchestrator initialized with Docker socket: {self.docker_socket}")
        except ImportError:
            logger.warning("Docker library not available - orchestration disabled")
            self.enabled = False
            self.docker_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.enabled = False
            self.docker_client = None
    
    async def spawn_mongodb_clone(
        self,
        node_id: str,
        instance_name: str,
        port: Optional[int] = None,
        network: str = "lucid-pi-network",
        ip_address: Optional[str] = None,
        resource_limits: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Spawn a MongoDB clone instance for a node.
        
        Args:
            node_id: Node ID requesting the clone
            instance_name: Unique name for the MongoDB instance
            port: Port for MongoDB (default: auto-assign)
            network: Docker network name
            ip_address: Static IP address (optional)
            resource_limits: Resource limits (memory, CPU)
        
        Returns:
            Dictionary with service information
        """
        if not self.enabled:
            raise RuntimeError("Service orchestration is disabled")
        
        if not self.docker_client:
            raise RuntimeError("Docker client not initialized")
        
        try:
            logger.info(f"Spawning MongoDB clone for node {node_id}: {instance_name}")
            
            # Generate unique container name
            container_name = f"lucid-mongodb-{instance_name}-{node_id[:8]}"
            
            # Default resource limits
            if resource_limits is None:
                resource_limits = {
                    "memory": "512m",
                    "cpu": "0.5"
                }
            
            # MongoDB environment variables
            mongodb_password = os.getenv("MONGODB_PASSWORD", "lucid")
            env_vars = {
                "MONGO_INITDB_ROOT_USERNAME": "lucid",
                "MONGO_INITDB_ROOT_PASSWORD": mongodb_password,
                "MONGO_INITDB_DATABASE": f"lucid_node_{node_id}"
            }
            
            # Container configuration
            container_config = {
                "image": "pickme/lucid-mongodb:latest-arm64",
                "name": container_name,
                "environment": env_vars,
                "network": network,
                "restart_policy": {"Name": "unless-stopped"},
                "mem_limit": resource_limits.get("memory", "512m"),
                "cpu_quota": int(float(resource_limits.get("cpu", "0.5")) * 100000),
                "cpu_period": 100000,
                "labels": {
                    "lucid.service": "mongodb-clone",
                    "lucid.node_id": node_id,
                    "lucid.instance": instance_name,
                    "lucid.spawned_by": "lucid-auth-service",
                    "lucid.spawned_at": datetime.utcnow().isoformat()
                }
            }
            
            # Add port mapping if specified
            if port:
                container_config["ports"] = {f"{port}/tcp": port}
            
            # Add IP address if specified
            if ip_address:
                container_config["network_mode"] = network
                container_config["ipv4_address"] = ip_address
            
            # Create and start container
            container = self.docker_client.containers.run(**container_config, detach=True)
            
            # Wait for container to be ready
            await asyncio.sleep(5)  # Give container time to start
            
            # Get container status
            container.reload()
            
            service_info = {
                "service_id": container.id,
                "container_name": container_name,
                "node_id": node_id,
                "instance_name": instance_name,
                "status": ServiceStatus.RUNNING.value if container.status == "running" else ServiceStatus.STARTING.value,
                "port": port,
                "ip_address": ip_address or container.attrs.get("NetworkSettings", {}).get("IPAddress"),
                "network": network,
                "spawned_at": datetime.utcnow().isoformat(),
                "resource_limits": resource_limits
            }
            
            # Store spawned service
            self.spawned_services[container.id] = service_info
            
            logger.info(f"MongoDB clone spawned successfully: {container_name} ({container.id[:12]})")
            return service_info
            
        except Exception as e:
            logger.error(f"Failed to spawn MongoDB clone: {e}", exc_info=True)
            raise
    
    async def stop_service(self, service_id: str) -> bool:
        """
        Stop a spawned service.
        
        Args:
            service_id: Service/container ID
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.docker_client:
            return False
        
        try:
            container = self.docker_client.containers.get(service_id)
            container.stop(timeout=10)
            
            # Update status
            if service_id in self.spawned_services:
                self.spawned_services[service_id]["status"] = ServiceStatus.STOPPED.value
                self.spawned_services[service_id]["stopped_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Service stopped: {service_id[:12]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop service {service_id}: {e}")
            return False
    
    async def remove_service(self, service_id: str) -> bool:
        """
        Remove a spawned service.
        
        Args:
            service_id: Service/container ID
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.docker_client:
            return False
        
        try:
            container = self.docker_client.containers.get(service_id)
            container.remove(force=True)
            
            # Remove from tracking
            if service_id in self.spawned_services:
                del self.spawned_services[service_id]
            
            logger.info(f"Service removed: {service_id[:12]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove service {service_id}: {e}")
            return False
    
    async def get_service_status(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a spawned service.
        
        Args:
            service_id: Service/container ID
        
        Returns:
            Service status information or None if not found
        """
        if not self.enabled or not self.docker_client:
            return None
        
        try:
            container = self.docker_client.containers.get(service_id)
            container.reload()
            
            status_info = {
                "service_id": service_id,
                "status": container.status,
                "created_at": container.attrs.get("Created"),
                "started_at": container.attrs.get("State", {}).get("StartedAt"),
                "health": container.attrs.get("State", {}).get("Health", {}).get("Status", "unknown")
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Failed to get service status {service_id}: {e}")
            return None
    
    async def list_spawned_services(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all spawned services, optionally filtered by node_id.
        
        Args:
            node_id: Optional node ID filter
        
        Returns:
            List of spawned service information
        """
        if node_id:
            return [
                service for service in self.spawned_services.values()
                if service.get("node_id") == node_id
            ]
        return list(self.spawned_services.values())
    
    async def cleanup_stopped_services(self) -> int:
        """
        Clean up stopped services.
        
        Returns:
            Number of services cleaned up
        """
        if not self.enabled or not self.docker_client:
            return 0
        
        cleaned = 0
        for service_id, service_info in list(self.spawned_services.items()):
            try:
                container = self.docker_client.containers.get(service_id)
                if container.status == "exited" or container.status == "dead":
                    await self.remove_service(service_id)
                    cleaned += 1
            except Exception:
                # Container may have been removed externally
                if service_id in self.spawned_services:
                    del self.spawned_services[service_id]
                cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} stopped services")
        return cleaned
    
    def is_enabled(self) -> bool:
        """Check if orchestration is enabled"""
        return self.enabled and self.docker_client is not None

