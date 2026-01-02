# Path: node/repositories/pool_repository.py
# Lucid Node Management Repository - Pool Repository
# Based on LUCID-STRICT requirements per Spec-1c

"""
Pool repository for Lucid system.

This module provides data access methods for:
- Pool CRUD operations
- Node assignment and management
- Auto-scaling operations
- Pool metrics and monitoring
"""

from typing import List, Optional, Dict, Any, Tuple
import os
from datetime import datetime, timezone
import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
import uuid

from ..models.pool import (
    NodePool, NodePoolCreateRequest, NodePoolUpdateRequest,
    PoolNode, PoolScalingEvent, PoolMetrics, ScalingPolicy, AutoScalingConfig
)
from ..models.node import Node

logger = logging.getLogger(__name__)

class PoolRepository:
    """Repository for pool management operations"""
    
    def __init__(self, mongo_url: Optional[str] = None, database_name: Optional[str] = None):
        """Initialize pool repository"""
        self.mongo_url = mongo_url or os.getenv("MONGODB_URL")
        self.database_name = database_name or os.getenv("MONGODB_DATABASE", "lucid")
        """Initialize pool repository"""
        self.mongo_url = mongo_url
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.database_name]
            
            # Create indexes
            await self._create_indexes()
            
            logger.info("Connected to MongoDB for pool repository")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes"""
        try:
            # Node pools collection indexes
            await self.db.node_pools.create_index([("pool_id", ASCENDING)], unique=True)
            await self.db.node_pools.create_index([("name", ASCENDING)], unique=True)
            await self.db.node_pools.create_index([("auto_scaling.enabled", ASCENDING)])
            
            # Pool nodes collection indexes
            await self.db.pool_nodes.create_index([("pool_id", ASCENDING), ("node_id", ASCENDING)], unique=True)
            await self.db.pool_nodes.create_index([("node_id", ASCENDING)])
            await self.db.pool_nodes.create_index([("priority", ASCENDING)])
            await self.db.pool_nodes.create_index([("status", ASCENDING)])
            
            # Pool scaling events indexes
            await self.db.pool_scaling_events.create_index([("pool_id", ASCENDING), ("triggered_at", DESCENDING)])
            await self.db.pool_scaling_events.create_index([("event_id", ASCENDING)], unique=True)
            await self.db.pool_scaling_events.create_index([("status", ASCENDING)])
            
            # Pool metrics indexes
            await self.db.pool_metrics.create_index([("pool_id", ASCENDING), ("timestamp", DESCENDING)])
            await self.db.pool_metrics.create_index([("timestamp", DESCENDING)], expireAfterSeconds=7776000)  # 90 days
            
            logger.info("Created pool repository indexes")
            
        except Exception as e:
            logger.error(f"Failed to create pool repository indexes: {e}")
            raise
    
    # Pool CRUD operations
    async def create_pool(self, pool_data: NodePoolCreateRequest) -> NodePool:
        """Create a new pool"""
        try:
            # Generate pool ID
            pool_id = f"pool_{uuid.uuid4().hex[:12]}"
            
            # Create pool document
            pool_doc = {
                "pool_id": pool_id,
                "name": pool_data.name,
                "description": pool_data.description,
                "node_count": 0,
                "max_nodes": pool_data.max_nodes,
                "resource_limits": pool_data.resource_limits,
                "auto_scaling": pool_data.auto_scaling.dict() if pool_data.auto_scaling else AutoScalingConfig().dict(),
                "pricing": pool_data.pricing,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Insert pool
            result = await self.db.node_pools.insert_one(pool_doc)
            if not result.inserted_id:
                raise Exception("Failed to create pool")
            
            # Return created pool
            return NodePool(**pool_doc)
            
        except Exception as e:
            logger.error(f"Failed to create pool: {e}")
            raise
    
    async def get_pool(self, pool_id: str) -> Optional[NodePool]:
        """Get pool by ID"""
        try:
            pool_doc = await self.db.node_pools.find_one({"pool_id": pool_id})
            if not pool_doc:
                return None
            
            return NodePool(**pool_doc)
            
        except Exception as e:
            logger.error(f"Failed to get pool {pool_id}: {e}")
            raise
    
    async def get_pool_by_name(self, name: str) -> Optional[NodePool]:
        """Get pool by name"""
        try:
            pool_doc = await self.db.node_pools.find_one({"name": name})
            if not pool_doc:
                return None
            
            return NodePool(**pool_doc)
            
        except Exception as e:
            logger.error(f"Failed to get pool by name {name}: {e}")
            raise
    
    async def update_pool(self, pool_id: str, pool_data: NodePoolUpdateRequest) -> NodePool:
        """Update pool"""
        try:
            update_doc = {"updated_at": datetime.now(timezone.utc)}
            
            if pool_data.name:
                update_doc["name"] = pool_data.name
            if pool_data.description is not None:
                update_doc["description"] = pool_data.description
            if pool_data.max_nodes:
                update_doc["max_nodes"] = pool_data.max_nodes
            if pool_data.resource_limits:
                update_doc["resource_limits"] = pool_data.resource_limits
            if pool_data.auto_scaling:
                update_doc["auto_scaling"] = pool_data.auto_scaling.dict()
            if pool_data.pricing:
                update_doc["pricing"] = pool_data.pricing
            
            result = await self.db.node_pools.update_one(
                {"pool_id": pool_id},
                {"$set": update_doc}
            )
            
            if result.matched_count == 0:
                raise Exception("Pool not found")
            
            # Return updated pool
            return await self.get_pool(pool_id)
            
        except Exception as e:
            logger.error(f"Failed to update pool {pool_id}: {e}")
            raise
    
    async def delete_pool(self, pool_id: str) -> bool:
        """Delete pool"""
        try:
            # Check if pool has nodes
            pool = await self.get_pool(pool_id)
            if pool and pool.node_count > 0:
                raise Exception("Cannot delete pool with assigned nodes")
            
            # Delete pool
            result = await self.db.node_pools.delete_one({"pool_id": pool_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete pool {pool_id}: {e}")
            raise
    
    async def list_pools(self, page: int = 1, limit: int = 20, filters: Dict[str, Any] = None) -> Tuple[List[NodePool], int]:
        """List pools with pagination and filtering"""
        try:
            # Build query
            query = {}
            if filters:
                query.update(filters)
            
            # Get total count
            total_count = await self.db.node_pools.count_documents(query)
            
            # Get pools
            skip = (page - 1) * limit
            cursor = self.db.node_pools.find(query).skip(skip).limit(limit).sort("created_at", DESCENDING)
            pools = []
            
            async for pool_doc in cursor:
                pools.append(NodePool(**pool_doc))
            
            return pools, total_count
            
        except Exception as e:
            logger.error(f"Failed to list pools: {e}")
            raise
    
    # Node assignment operations
    async def add_node_to_pool(self, pool_id: str, node_id: str, priority: int = 50) -> bool:
        """Add node to pool"""
        try:
            # Check if pool exists
            pool = await self.get_pool(pool_id)
            if not pool:
                raise Exception("Pool not found")
            
            # Check pool capacity
            if pool.node_count >= pool.max_nodes:
                raise Exception("Pool is at maximum capacity")
            
            # Create pool node document
            pool_node_doc = {
                "node_id": node_id,
                "pool_id": pool_id,
                "priority": priority,
                "assigned_at": datetime.now(timezone.utc),
                "status": "active"
            }
            
            # Insert pool node
            await self.db.pool_nodes.insert_one(pool_node_doc)
            
            # Update pool node count
            await self.db.node_pools.update_one(
                {"pool_id": pool_id},
                {"$inc": {"node_count": 1}}
            )
            
            logger.info(f"Added node {node_id} to pool {pool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add node {node_id} to pool {pool_id}: {e}")
            raise
    
    async def remove_node_from_pool(self, pool_id: str, node_id: str) -> bool:
        """Remove node from pool"""
        try:
            # Remove pool node
            result = await self.db.pool_nodes.delete_one({
                "pool_id": pool_id,
                "node_id": node_id
            })
            
            if result.deleted_count > 0:
                # Update pool node count
                await self.db.node_pools.update_one(
                    {"pool_id": pool_id},
                    {"$inc": {"node_count": -1}}
                )
                
                logger.info(f"Removed node {node_id} from pool {pool_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove node {node_id} from pool {pool_id}: {e}")
            raise
    
    async def list_pool_nodes(self, pool_id: str, page: int = 1, limit: int = 20) -> Tuple[List[PoolNode], int]:
        """List nodes in a pool"""
        try:
            # Get total count
            total_count = await self.db.pool_nodes.count_documents({"pool_id": pool_id})
            
            # Get pool nodes
            skip = (page - 1) * limit
            cursor = self.db.pool_nodes.find({"pool_id": pool_id}).skip(skip).limit(limit).sort("priority", DESCENDING)
            pool_nodes = []
            
            async for pool_node_doc in cursor:
                pool_nodes.append(PoolNode(**pool_node_doc))
            
            return pool_nodes, total_count
            
        except Exception as e:
            logger.error(f"Failed to list nodes in pool {pool_id}: {e}")
            raise
    
    # Auto-scaling operations
    async def scale_pool(self, pool_id: str, target_nodes: int) -> bool:
        """Scale pool to target number of nodes"""
        try:
            # Check if pool exists
            pool = await self.get_pool(pool_id)
            if not pool:
                raise Exception("Pool not found")
            
            # Validate target nodes
            if target_nodes > pool.max_nodes:
                raise Exception("Target nodes exceeds pool maximum capacity")
            
            # Create scaling event
            event_id = str(uuid.uuid4())
            event_type = "scale_up" if target_nodes > pool.node_count else "scale_down"
            
            scaling_event = {
                "event_id": event_id,
                "pool_id": pool_id,
                "event_type": event_type,
                "target_nodes": target_nodes,
                "current_nodes": pool.node_count,
                "trigger_reason": "manual_scale",
                "triggered_at": datetime.now(timezone.utc),
                "completed_at": None,
                "status": "pending"
            }
            
            # Insert scaling event
            await self.db.pool_scaling_events.insert_one(scaling_event)
            
            # Update pool node count
            await self.db.node_pools.update_one(
                {"pool_id": pool_id},
                {"$set": {"node_count": target_nodes}}
            )
            
            logger.info(f"Scaled pool {pool_id} to {target_nodes} nodes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale pool {pool_id}: {e}")
            raise
    
    async def get_scaling_events(self, pool_id: str, limit: int = 50) -> List[PoolScalingEvent]:
        """Get scaling events for a pool"""
        try:
            cursor = self.db.pool_scaling_events.find(
                {"pool_id": pool_id}
            ).sort("triggered_at", DESCENDING).limit(limit)
            
            events = []
            async for event_doc in cursor:
                events.append(PoolScalingEvent(**event_doc))
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get scaling events for pool {pool_id}: {e}")
            raise
    
    # Pool metrics
    async def get_pool_metrics(self, pool_id: str, time_range: str = "24h") -> PoolMetrics:
        """Get pool performance metrics"""
        try:
            # Calculate time range
            now = datetime.now(timezone.utc)
            if time_range == "1h":
                start_time = now - timedelta(hours=1)
            elif time_range == "6h":
                start_time = now - timedelta(hours=6)
            elif time_range == "24h":
                start_time = now - timedelta(hours=24)
            elif time_range == "7d":
                start_time = now - timedelta(days=7)
            else:
                start_time = now - timedelta(hours=24)
            
            # Get pool
            pool = await self.get_pool(pool_id)
            if not pool:
                raise Exception("Pool not found")
            
            # Get pool nodes
            pool_nodes = await self.db.pool_nodes.find({"pool_id": pool_id}).to_list(length=None)
            node_ids = [node["node_id"] for node in pool_nodes]
            
            # Get latest metrics for all nodes
            metrics_docs = []
            for node_id in node_ids:
                latest_metrics = await self.db.resource_metrics.find_one(
                    {"node_id": node_id, "timestamp": {"$gte": start_time}},
                    sort=[("timestamp", DESCENDING)]
                )
                if latest_metrics:
                    metrics_docs.append(latest_metrics)
            
            # Calculate aggregated metrics
            if metrics_docs:
                total_cpu = sum(metrics.get("cpu", {}).get("usage_percent", 0) for metrics in metrics_docs)
                total_memory = sum(metrics.get("memory", {}).get("used_bytes", 0) for metrics in metrics_docs)
                total_memory_capacity = sum(metrics.get("memory", {}).get("total_bytes", 1) for metrics in metrics_docs)
                
                average_cpu_percent = total_cpu / len(metrics_docs) if metrics_docs else 0
                average_memory_percent = (total_memory / total_memory_capacity * 100) if total_memory_capacity > 0 else 0
            else:
                average_cpu_percent = 0
                average_memory_percent = 0
            
            # Create pool metrics
            pool_metrics = PoolMetrics(
                pool_id=pool_id,
                timestamp=now,
                total_nodes=pool.node_count,
                active_nodes=len(pool_nodes),
                average_cpu_percent=average_cpu_percent,
                average_memory_percent=average_memory_percent,
                total_sessions=0,  # Placeholder
                throughput_mbps=0.0  # Placeholder
            )
            
            return pool_metrics
            
        except Exception as e:
            logger.error(f"Failed to get pool metrics {pool_id}: {e}")
            raise
    
    async def get_pool_statistics(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get pool statistics"""
        try:
            # Calculate time range
            now = datetime.now(timezone.utc)
            if time_range == "1h":
                start_time = now - timedelta(hours=1)
            elif time_range == "6h":
                start_time = now - timedelta(hours=6)
            elif time_range == "24h":
                start_time = now - timedelta(hours=24)
            elif time_range == "7d":
                start_time = now - timedelta(days=7)
            else:
                start_time = now - timedelta(hours=24)
            
            # Get pool statistics
            total_pools = await self.db.node_pools.count_documents({})
            active_pools = await self.db.node_pools.count_documents({"node_count": {"$gt": 0}})
            total_nodes = await self.db.pool_nodes.count_documents({})
            
            # Get auto-scaling statistics
            auto_scaling_pools = await self.db.node_pools.count_documents({"auto_scaling.enabled": True})
            
            # Get scaling events
            scaling_events = await self.db.pool_scaling_events.count_documents({
                "triggered_at": {"$gte": start_time}
            })
            
            return {
                "time_range": time_range,
                "total_pools": total_pools,
                "active_pools": active_pools,
                "total_nodes": total_nodes,
                "auto_scaling_pools": auto_scaling_pools,
                "scaling_events": scaling_events,
                "generated_at": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get pool statistics: {e}")
            raise
