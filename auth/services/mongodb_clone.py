"""
Lucid Authentication Service - MongoDB Clone Manager
Manages MongoDB clone instances for nodes

File: auth/services/mongodb_clone.py
Purpose: Create and manage MongoDB clone instances for node operations
Dependencies: orchestrator, motor, asyncio, logging
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

from .orchestrator import ServiceOrchestrator, ServiceStatus

logger = logging.getLogger(__name__)


class MongoDBCloneManager:
    """
    Manages MongoDB clone instances for nodes.
    
    Provides:
    - Create MongoDB clones for nodes
    - Configure MongoDB replica sets
    - Manage MongoDB connections
    - Monitor clone health
    """
    
    def __init__(self, orchestrator: ServiceOrchestrator):
        """
        Initialize MongoDB clone manager.
        
        Args:
            orchestrator: ServiceOrchestrator instance
        """
        self.orchestrator = orchestrator
        self.clones: Dict[str, Dict[str, Any]] = {}
    
    async def create_node_mongodb(
        self,
        node_id: str,
        node_tron_address: str,
        port: Optional[int] = None,
        network: str = "lucid-pi-network",
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a MongoDB clone instance for a node.
        
        Args:
            node_id: Node ID
            node_tron_address: Node's TRON address
            port: MongoDB port (default: auto-assign)
            network: Docker network
            ip_address: Static IP address (optional)
        
        Returns:
            MongoDB clone information
        """
        if not self.orchestrator.is_enabled():
            raise RuntimeError("Service orchestration is not enabled")
        
        try:
            logger.info(f"Creating MongoDB clone for node {node_id}")
            
            # Generate instance name
            instance_name = f"node-{node_id[:8]}"
            
            # Spawn MongoDB container
            service_info = await self.orchestrator.spawn_mongodb_clone(
                node_id=node_id,
                instance_name=instance_name,
                port=port,
                network=network,
                ip_address=ip_address,
                resource_limits={
                    "memory": "256m",  # Smaller for node instances
                    "cpu": "0.25"
                }
            )
            
            # Wait for MongoDB to be ready
            await self._wait_for_mongodb_ready(service_info)
            
            # Configure MongoDB for node
            await self._configure_node_mongodb(service_info, node_id, node_tron_address)
            
            # Store clone information
            mongodb_password = os.getenv("MONGODB_PASSWORD")
            if not mongodb_password:
                raise RuntimeError("MONGODB_PASSWORD environment variable is required")
            clone_info = {
                "clone_id": service_info["service_id"],
                "node_id": node_id,
                "node_tron_address": node_tron_address,
                "instance_name": instance_name,
                "mongodb_uri": f"mongodb://lucid:{mongodb_password}@{service_info.get('ip_address', 'localhost')}:{service_info.get('port', 27017)}/lucid_node_{node_id}?authSource=admin",
                "database_name": f"lucid_node_{node_id}",
                "status": ServiceStatus.RUNNING.value,
                "created_at": datetime.utcnow().isoformat(),
                "service_info": service_info
            }
            
            self.clones[node_id] = clone_info
            
            logger.info(f"MongoDB clone created for node {node_id}: {clone_info['mongodb_uri']}")
            return clone_info
            
        except Exception as e:
            logger.error(f"Failed to create MongoDB clone for node {node_id}: {e}", exc_info=True)
            raise
    
    async def _wait_for_mongodb_ready(self, service_info: Dict[str, Any], max_attempts: int = 30) -> bool:
        """
        Wait for MongoDB to be ready.
        
        Args:
            service_info: Service information
            max_attempts: Maximum connection attempts
        
        Returns:
            True if ready, False otherwise
        """
        mongodb_password = os.getenv("MONGODB_PASSWORD")
        if not mongodb_password:
            raise RuntimeError("MONGODB_PASSWORD environment variable is required")
        mongodb_uri = f"mongodb://lucid:{mongodb_password}@{service_info.get('ip_address', 'localhost')}:{service_info.get('port', 27017)}/admin?authSource=admin"
        
        for attempt in range(max_attempts):
            try:
                client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=2000)
                await client.admin.command('ping')
                client.close()
                logger.info(f"MongoDB clone ready after {attempt + 1} attempts")
                return True
            except Exception:
                await asyncio.sleep(2)
        
        logger.error(f"MongoDB clone not ready after {max_attempts} attempts")
        return False
    
    async def _configure_node_mongodb(
        self,
        service_info: Dict[str, Any],
        node_id: str,
        node_tron_address: str
    ):
        """
        Configure MongoDB instance for node.
        
        Args:
            service_info: Service information
            node_id: Node ID
            node_tron_address: Node's TRON address
        """
        try:
            mongodb_password = os.getenv("MONGODB_PASSWORD")
            if not mongodb_password:
                raise RuntimeError("MONGODB_PASSWORD environment variable is required")
            mongodb_uri = f"mongodb://lucid:{mongodb_password}@{service_info.get('ip_address', 'localhost')}:{service_info.get('port', 27017)}/admin?authSource=admin"
            
            client = AsyncIOMotorClient(mongodb_uri)
            db = client[f"lucid_node_{node_id}"]
            
            # Create node-specific collections
            await db.create_collection("node_data")
            await db.create_collection("node_sessions")
            await db.create_collection("node_work_credits")
            
            # Create indexes
            await db["node_data"].create_index("node_id", unique=True)
            await db["node_sessions"].create_index("session_id")
            await db["node_work_credits"].create_index("node_id")
            
            # Store node metadata
            await db["node_metadata"].insert_one({
                "node_id": node_id,
                "tron_address": node_tron_address,
                "created_at": datetime.utcnow(),
                "mongodb_instance": service_info["container_name"]
            })
            
            client.close()
            logger.info(f"MongoDB configured for node {node_id}")
            
        except Exception as e:
            logger.error(f"Failed to configure MongoDB for node {node_id}: {e}", exc_info=True)
            raise
    
    async def get_node_mongodb(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get MongoDB clone information for a node.
        
        Args:
            node_id: Node ID
        
        Returns:
            Clone information or None if not found
        """
        return self.clones.get(node_id)
    
    async def list_node_clones(self) -> List[Dict[str, Any]]:
        """
        List all node MongoDB clones.
        
        Returns:
            List of clone information
        """
        return list(self.clones.values())
    
    async def remove_node_mongodb(self, node_id: str) -> bool:
        """
        Remove MongoDB clone for a node.
        
        Args:
            node_id: Node ID
        
        Returns:
            True if successful, False otherwise
        """
        if node_id not in self.clones:
            return False
        
        try:
            clone_info = self.clones[node_id]
            service_id = clone_info["clone_id"]
            
            # Stop and remove service
            success = await self.orchestrator.remove_service(service_id)
            
            if success:
                del self.clones[node_id]
                logger.info(f"MongoDB clone removed for node {node_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to remove MongoDB clone for node {node_id}: {e}")
            return False
    
    async def health_check(self, node_id: str) -> Dict[str, Any]:
        """
        Perform health check on node MongoDB clone.
        
        Args:
            node_id: Node ID
        
        Returns:
            Health check results
        """
        if node_id not in self.clones:
            return {
                "healthy": False,
                "error": "Clone not found"
            }
        
        try:
            clone_info = self.clones[node_id]
            service_id = clone_info["clone_id"]
            
            # Check container status
            status = await self.orchestrator.get_service_status(service_id)
            
            if not status or status.get("status") != "running":
                return {
                    "healthy": False,
                    "status": status.get("status") if status else "unknown",
                    "error": "Container not running"
                }
            
            # Check MongoDB connection
            try:
                client = AsyncIOMotorClient(clone_info["mongodb_uri"], serverSelectionTimeoutMS=2000)
                await client.admin.command('ping')
                client.close()
                
                return {
                    "healthy": True,
                    "status": "running",
                    "mongodb_uri": clone_info["mongodb_uri"],
                    "container_status": status
                }
            except Exception as e:
                return {
                    "healthy": False,
                    "status": "running",
                    "error": f"MongoDB connection failed: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Health check failed for node {node_id}: {e}")
            return {
                "healthy": False,
                "error": str(e)
            }

