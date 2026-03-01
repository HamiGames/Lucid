#!/usr/bin/env python3
"""
Lucid Node Management - Node Pool Manager
Handles node pool management with max 100 nodes per pool
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .database_adapter import DatabaseAdapter
from .models import NodeInfo, PoolInfo, PoolMetrics

logger = logging.getLogger(__name__)

# Pool Configuration
MAX_NODES_PER_POOL = int(os.getenv("MAX_NODES_PER_POOL", "100"))
MIN_NODES_PER_POOL = int(os.getenv("MIN_NODES_PER_POOL", "3"))
POOL_HEALTH_CHECK_INTERVAL = int(os.getenv("POOL_HEALTH_CHECK_INTERVAL", "300"))  # 5 minutes
POOL_SYNC_INTERVAL = int(os.getenv("POOL_SYNC_INTERVAL", "60"))  # 1 minute

class PoolStatus(Enum):
    """Pool status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    FULL = "full"
    EMPTY = "empty"

class NodeStatus(Enum):
    """Node status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    PENDING = "pending"

@dataclass
class PoolMember:
    """Pool member information"""
    node_id: str
    node_address: str
    status: NodeStatus
    joined_at: datetime
    last_seen: datetime
    contribution_score: float = 0.0
    work_credits: float = 0.0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PoolConfiguration:
    """Pool configuration settings"""
    max_nodes: int = MAX_NODES_PER_POOL
    min_nodes: int = MIN_NODES_PER_POOL
    auto_scale: bool = True
    health_check_interval: int = POOL_HEALTH_CHECK_INTERVAL
    sync_interval: int = POOL_SYNC_INTERVAL
    performance_threshold: float = 0.8
    auto_remove_failed: bool = True

class NodePoolManager:
    """
    Node Pool Manager for Node Management Service
    
    Handles:
    - Pool creation and management
    - Node addition and removal
    - Pool health monitoring
    - Performance tracking
    - Load balancing
    """
    
    def __init__(self, db_adapter: DatabaseAdapter, max_nodes_per_pool: int = MAX_NODES_PER_POOL):
        self.db = db_adapter
        self.max_nodes_per_pool = max_nodes_per_pool
        
        # Pool storage
        self.pools: Dict[str, PoolInfo] = {}
        self.pool_members: Dict[str, Dict[str, PoolMember]] = {}  # pool_id -> {node_id -> PoolMember}
        self.node_pools: Dict[str, str] = {}  # node_id -> pool_id
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None
        
        logger.info(f"Node Pool Manager initialized with max {max_nodes_per_pool} nodes per pool")
    
    async def create_pool(self, pool_name: str, max_nodes: int = None) -> str:
        """
        Create a new node pool
        
        Args:
            pool_name: Name of the pool
            max_nodes: Maximum number of nodes (defaults to MAX_NODES_PER_POOL)
            
        Returns:
            Pool ID if successful
        """
        try:
            if max_nodes is None:
                max_nodes = self.max_nodes_per_pool
            
            if max_nodes > self.max_nodes_per_pool:
                raise ValueError(f"Max nodes {max_nodes} exceeds limit {self.max_nodes_per_pool}")
            
            # Generate pool ID
            pool_id = str(uuid.uuid4())
            
            # Create pool info
            pool = PoolInfo(
                pool_id=pool_id,
                pool_name=pool_name,
                max_nodes=max_nodes,
                current_nodes=0,
                status=PoolStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                configuration=PoolConfiguration(max_nodes=max_nodes)
            )
            
            # Store pool
            self.pools[pool_id] = pool
            self.pool_members[pool_id] = {}
            
            # Store in database
            await self._store_pool(pool)
            
            logger.info(f"Pool created: {pool_name} (ID: {pool_id}) with max {max_nodes} nodes")
            return pool_id
            
        except Exception as e:
            logger.error(f"Error creating pool {pool_name}: {e}")
            raise
    
    async def add_node_to_pool(self, node_id: str, pool_id: str) -> bool:
        """
        Add a node to a pool
        
        Args:
            node_id: Node identifier
            pool_id: Pool identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if pool exists
            if pool_id not in self.pools:
                logger.error(f"Pool {pool_id} not found")
                return False
            
            pool = self.pools[pool_id]
            
            # Check if pool is full
            if pool.current_nodes >= pool.max_nodes:
                logger.warning(f"Pool {pool_id} is full ({pool.current_nodes}/{pool.max_nodes})")
                return False
            
            # Check if node is already in a pool
            if node_id in self.node_pools:
                existing_pool = self.node_pools[node_id]
                if existing_pool == pool_id:
                    logger.warning(f"Node {node_id} is already in pool {pool_id}")
                    return True
                else:
                    logger.warning(f"Node {node_id} is already in pool {existing_pool}")
                    return False
            
            # Get node information
            node_info = await self._get_node_info(node_id)
            if not node_info:
                logger.error(f"Node {node_id} not found")
                return False
            
            # Create pool member
            member = PoolMember(
                node_id=node_id,
                node_address=node_info.address,
                status=NodeStatus.ACTIVE,
                joined_at=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            )
            
            # Add to pool
            self.pool_members[pool_id][node_id] = member
            self.node_pools[node_id] = pool_id
            
            # Update pool info
            pool.current_nodes += 1
            pool.last_updated = datetime.now(timezone.utc)
            
            # Update pool status
            if pool.current_nodes >= pool.max_nodes:
                pool.status = PoolStatus.FULL
            elif pool.current_nodes == 0:
                pool.status = PoolStatus.EMPTY
            else:
                pool.status = PoolStatus.ACTIVE
            
            # Store updates
            await self._update_pool(pool)
            await self._store_pool_member(pool_id, member)
            
            logger.info(f"Node {node_id} added to pool {pool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding node {node_id} to pool {pool_id}: {e}")
            return False
    
    async def remove_node_from_pool(self, node_id: str, pool_id: str) -> bool:
        """
        Remove a node from a pool
        
        Args:
            node_id: Node identifier
            pool_id: Pool identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if pool exists
            if pool_id not in self.pools:
                logger.error(f"Pool {pool_id} not found")
                return False
            
            # Check if node is in the pool
            if node_id not in self.pool_members.get(pool_id, {}):
                logger.warning(f"Node {node_id} not found in pool {pool_id}")
                return False
            
            # Remove from pool
            del self.pool_members[pool_id][node_id]
            del self.node_pools[node_id]
            
            # Update pool info
            pool = self.pools[pool_id]
            pool.current_nodes -= 1
            pool.last_updated = datetime.now(timezone.utc)
            
            # Update pool status
            if pool.current_nodes == 0:
                pool.status = PoolStatus.EMPTY
            elif pool.current_nodes < pool.max_nodes:
                pool.status = PoolStatus.ACTIVE
            
            # Store updates
            await self._update_pool(pool)
            await self._remove_pool_member(pool_id, node_id)
            
            logger.info(f"Node {node_id} removed from pool {pool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing node {node_id} from pool {pool_id}: {e}")
            return False
    
    async def get_pool(self, pool_id: str) -> Optional[PoolInfo]:
        """
        Get pool information
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            PoolInfo object if found, None otherwise
        """
        try:
            return self.pools.get(pool_id)
        except Exception as e:
            logger.error(f"Error getting pool {pool_id}: {e}")
            return None
    
    async def list_pools(self) -> List[PoolInfo]:
        """
        List all pools
        
        Returns:
            List of PoolInfo objects
        """
        try:
            return list(self.pools.values())
        except Exception as e:
            logger.error(f"Error listing pools: {e}")
            return []
    
    async def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """
        Get node information
        
        Args:
            node_id: Node identifier
            
        Returns:
            NodeInfo object if found, None otherwise
        """
        try:
            # Check if node is in a pool
            if node_id not in self.node_pools:
                return None
            
            pool_id = self.node_pools[node_id]
            if pool_id not in self.pool_members:
                return None
            
            member = self.pool_members[pool_id].get(node_id)
            if not member:
                return None
            
            # Convert to NodeInfo
            return NodeInfo(
                node_id=node_id,
                address=member.node_address,
                stake_amount=0.0,  # Would be loaded from database
                status=member.status.value,
                created_at=member.joined_at
            )
            
        except Exception as e:
            logger.error(f"Error getting node {node_id}: {e}")
            return None
    
    async def list_nodes(self, pool_id: Optional[str] = None, 
                        status: Optional[str] = None) -> List[NodeInfo]:
        """
        List nodes, optionally filtered by pool and status
        
        Args:
            pool_id: Filter by pool ID
            status: Filter by status
            
        Returns:
            List of NodeInfo objects
        """
        try:
            nodes = []
            
            if pool_id:
                # Get nodes from specific pool
                if pool_id in self.pool_members:
                    for member in self.pool_members[pool_id].values():
                        if not status or member.status.value == status:
                            nodes.append(NodeInfo(
                                node_id=member.node_id,
                                address=member.node_address,
                                stake_amount=0.0,
                                status=member.status.value,
                                created_at=member.joined_at
                            ))
            else:
                # Get nodes from all pools
                for pool_members in self.pool_members.values():
                    for member in pool_members.values():
                        if not status or member.status.value == status:
                            nodes.append(NodeInfo(
                                node_id=member.node_id,
                                address=member.node_address,
                                stake_amount=0.0,
                                status=member.status.value,
                                created_at=member.joined_at
                            ))
            
            return nodes
            
        except Exception as e:
            logger.error(f"Error listing nodes: {e}")
            return []
    
    async def health_check_all_pools(self) -> Dict[str, Any]:
        """
        Perform health check on all pools
        
        Returns:
            Dictionary with health check results
        """
        try:
            logger.info("Performing health check on all pools")
            
            results = {
                "total_pools": len(self.pools),
                "healthy_pools": 0,
                "unhealthy_pools": 0,
                "pool_details": []
            }
            
            for pool_id, pool in self.pools.items():
                try:
                    health_status = await self._check_pool_health(pool_id)
                    results["pool_details"].append({
                        "pool_id": pool_id,
                        "pool_name": pool.pool_name,
                        "status": health_status["status"],
                        "healthy_nodes": health_status["healthy_nodes"],
                        "total_nodes": health_status["total_nodes"],
                        "issues": health_status["issues"]
                    })
                    
                    if health_status["status"] == "healthy":
                        results["healthy_pools"] += 1
                    else:
                        results["unhealthy_pools"] += 1
                        
                except Exception as e:
                    logger.error(f"Error checking health for pool {pool_id}: {e}")
                    results["pool_details"].append({
                        "pool_id": pool_id,
                        "pool_name": pool.pool_name,
                        "status": "error",
                        "error": str(e)
                    })
                    results["unhealthy_pools"] += 1
            
            logger.info(f"Health check completed: {results['healthy_pools']} healthy, {results['unhealthy_pools']} unhealthy")
            return results
            
        except Exception as e:
            logger.error(f"Error in health_check_all_pools: {e}")
            return {"error": str(e)}
    
    async def get_metrics(self) -> PoolMetrics:
        """
        Get pool metrics
        
        Returns:
            PoolMetrics object
        """
        try:
            total_pools = len(self.pools)
            total_nodes = sum(pool.current_nodes for pool in self.pools.values())
            active_pools = len([p for p in self.pools.values() if p.status == PoolStatus.ACTIVE])
            full_pools = len([p for p in self.pools.values() if p.status == PoolStatus.FULL])
            empty_pools = len([p for p in self.pools.values() if p.status == PoolStatus.EMPTY])
            
            return PoolMetrics(
                total_pools=total_pools,
                total_nodes=total_nodes,
                active_pools=active_pools,
                full_pools=full_pools,
                empty_pools=empty_pools,
                max_nodes_per_pool=self.max_nodes_per_pool,
                average_nodes_per_pool=total_nodes / total_pools if total_pools > 0 else 0
            )
            
        except Exception as e:
            logger.error(f"Error getting pool metrics: {e}")
            return PoolMetrics()
    
    async def _get_node_info(self, node_id: str) -> Optional[NodeInfo]:
        """Get node information from database"""
        try:
            # This would typically query the database
            # For now, return a mock node info
            return NodeInfo(
                node_id=node_id,
                address=f"mock_address_{node_id}",
                stake_amount=1000.0,
                status="active",
                created_at=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting node info for {node_id}: {e}")
            return None
    
    async def _check_pool_health(self, pool_id: str) -> Dict[str, Any]:
        """Check health of a specific pool"""
        try:
            if pool_id not in self.pools:
                return {"status": "error", "error": "Pool not found"}
            
            pool = self.pools[pool_id]
            members = self.pool_members.get(pool_id, {})
            
            healthy_nodes = 0
            total_nodes = len(members)
            issues = []
            
            for member in members.values():
                # Check if node is responsive
                time_since_last_seen = datetime.now(timezone.utc) - member.last_seen
                if time_since_last_seen > timedelta(minutes=5):
                    issues.append(f"Node {member.node_id} not seen for {time_since_last_seen}")
                else:
                    healthy_nodes += 1
            
            # Determine overall status
            if total_nodes == 0:
                status = "empty"
            elif healthy_nodes == total_nodes:
                status = "healthy"
            elif healthy_nodes >= total_nodes * 0.8:
                status = "degraded"
            else:
                status = "unhealthy"
            
            return {
                "status": status,
                "healthy_nodes": healthy_nodes,
                "total_nodes": total_nodes,
                "issues": issues
            }
            
        except Exception as e:
            logger.error(f"Error checking pool health for {pool_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _store_pool(self, pool: PoolInfo):
        """Store pool in database"""
        try:
            # This would store the pool in the database
            logger.info(f"Storing pool {pool.pool_id}")
        except Exception as e:
            logger.error(f"Error storing pool: {e}")
    
    async def _update_pool(self, pool: PoolInfo):
        """Update pool in database"""
        try:
            # This would update the pool in the database
            logger.info(f"Updating pool {pool.pool_id}")
        except Exception as e:
            logger.error(f"Error updating pool: {e}")
    
    async def _store_pool_member(self, pool_id: str, member: PoolMember):
        """Store pool member in database"""
        try:
            # This would store the pool member in the database
            logger.info(f"Storing pool member {member.node_id} in pool {pool_id}")
        except Exception as e:
            logger.error(f"Error storing pool member: {e}")
    
    async def _remove_pool_member(self, pool_id: str, node_id: str):
        """Remove pool member from database"""
        try:
            # This would remove the pool member from the database
            logger.info(f"Removing pool member {node_id} from pool {pool_id}")
        except Exception as e:
            logger.error(f"Error removing pool member: {e}")
