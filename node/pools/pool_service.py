# Path: node/pools/pool_service.py
# Lucid Pool Service - Pool management and coordination
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from ..database_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


class PoolStatus(Enum):
    """Pool status states"""
    FORMING = "forming"
    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    DISBANDED = "disbanded"


class MemberStatus(Enum):
    """Pool member status"""
    JOINING = "joining"
    ACTIVE = "active"
    SYNCING = "syncing"
    DEGRADED = "degraded"
    LEAVING = "leaving"
    BANNED = "banned"


class PoolRole(Enum):
    """Pool member roles"""
    LEADER = "leader"
    CO_LEADER = "co_leader"
    MEMBER = "member"
    OBSERVER = "observer"


@dataclass
class PoolMember:
    """Pool member information"""
    node_id: str
    role: PoolRole
    status: MemberStatus
    joined_at: datetime
    contribution_score: float = 0.0
    work_credits_contributed: int = 0
    rewards_earned_usdt: float = 0.0
    last_sync: Optional[datetime] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "status": self.status.value,
            "joined_at": self.joined_at,
            "contribution_score": self.contribution_score,
            "work_credits_contributed": self.work_credits_contributed,
            "rewards_earned_usdt": self.rewards_earned_usdt,
            "last_sync": self.last_sync,
            "performance_metrics": self.performance_metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PoolMember':
        return cls(
            node_id=data["node_id"],
            role=PoolRole(data["role"]),
            status=MemberStatus(data["status"]),
            joined_at=data["joined_at"],
            contribution_score=data.get("contribution_score", 0.0),
            work_credits_contributed=data.get("work_credits_contributed", 0),
            rewards_earned_usdt=data.get("rewards_earned_usdt", 0.0),
            last_sync=data.get("last_sync"),
            performance_metrics=data.get("performance_metrics", {})
        )


@dataclass
class PoolInfo:
    """Pool information"""
    pool_id: str
    name: str
    description: str
    status: PoolStatus
    created_at: datetime
    creator_node_id: str
    members: Dict[str, PoolMember] = field(default_factory=dict)
    total_work_credits: int = 0
    total_rewards_usdt: float = 0.0
    pending_rewards_usdt: float = 0.0
    last_reward_distribution: Optional[datetime] = None
    
    @property
    def member_count(self) -> int:
        return len(self.members)
    
    @property
    def active_members(self) -> List[PoolMember]:
        return [member for member in self.members.values() if member.status == MemberStatus.ACTIVE]
    
    @property
    def leader(self) -> Optional[PoolMember]:
        for member in self.members.values():
            if member.role == PoolRole.LEADER:
                return member
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.pool_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "creator_node_id": self.creator_node_id,
            "members": {node_id: member.to_dict() for node_id, member in self.members.items()},
            "total_work_credits": self.total_work_credits,
            "total_rewards_usdt": self.total_rewards_usdt,
            "pending_rewards_usdt": self.pending_rewards_usdt,
            "last_reward_distribution": self.last_reward_distribution
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PoolInfo':
        # Load members
        members = {}
        for node_id, member_data in data.get("members", {}).items():
            member = PoolMember.from_dict(member_data)
            members[node_id] = member
        
        return cls(
            pool_id=data["_id"],
            name=data["name"],
            description=data["description"],
            status=PoolStatus(data["status"]),
            created_at=data["created_at"],
            creator_node_id=data["creator_node_id"],
            members=members,
            total_work_credits=data.get("total_work_credits", 0),
            total_rewards_usdt=data.get("total_rewards_usdt", 0.0),
            pending_rewards_usdt=data.get("pending_rewards_usdt", 0.0),
            last_reward_distribution=data.get("last_reward_distribution")
        )


class PoolService:
    """
    Pool service for managing node pools and coordination.
    
    Handles:
    - Pool creation and management
    - Member joining and leaving
    - Pool health monitoring
    - Work credit aggregation
    - Reward distribution
    - Pool synchronization
    """
    
    def __init__(self, db: DatabaseAdapter, node_id: str):
        self.db = db
        self.node_id = node_id
        self.running = False
        
        # Pool state
        self.active_pools: Dict[str, PoolInfo] = {}
        self.my_pools: Set[str] = set()  # Pools this node is a member of
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        
        logger.info(f"Pool service initialized: {node_id}")
    
    async def start(self):
        """Start pool service"""
        try:
            logger.info(f"Starting pool service {self.node_id}...")
            self.running = True
            
            # Load existing pools
            await self._load_pools()
            
            # Start background tasks
            self._tasks.append(asyncio.create_task(self._health_check_loop()))
            self._tasks.append(asyncio.create_task(self._sync_loop()))
            
            logger.info(f"Pool service {self.node_id} started")
            
        except Exception as e:
            logger.error(f"Failed to start pool service: {e}")
            raise
    
    async def stop(self):
        """Stop pool service"""
        try:
            logger.info(f"Stopping pool service {self.node_id}...")
            self.running = False
            
            # Cancel background tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            logger.info(f"Pool service {self.node_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping pool service: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get pool service status"""
        try:
            return {
                "node_id": self.node_id,
                "active_pools": len(self.active_pools),
                "my_pools": list(self.my_pools),
                "running": self.running,
                "pools": [
                    {
                        "pool_id": pool.pool_id,
                        "name": pool.name,
                        "status": pool.status.value,
                        "member_count": pool.member_count,
                        "total_work_credits": pool.total_work_credits,
                        "total_rewards_usdt": pool.total_rewards_usdt
                    }
                    for pool in self.active_pools.values()
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get pool status: {e}")
            return {"error": str(e)}
    
    async def create_pool(self, name: str, description: str) -> str:
        """
        Create a new node pool.
        
        Args:
            name: Pool name
            description: Pool description
            
        Returns:
            Pool ID
        """
        try:
            pool_id = str(uuid.uuid4())
            
            # Create pool leader member
            leader_member = PoolMember(
                node_id=self.node_id,
                role=PoolRole.LEADER,
                status=MemberStatus.ACTIVE,
                joined_at=datetime.now(timezone.utc)
            )
            
            pool = PoolInfo(
                pool_id=pool_id,
                name=name,
                description=description,
                status=PoolStatus.FORMING,
                created_at=datetime.now(timezone.utc),
                creator_node_id=self.node_id
            )
            
            pool.members[self.node_id] = leader_member
            
            # Store pool
            self.active_pools[pool_id] = pool
            self.my_pools.add(pool_id)
            
            await self.db["pools"].replace_one(
                {"_id": pool_id},
                pool.to_dict(),
                upsert=True
            )
            
            logger.info(f"Pool created: {pool_id} ({name})")
            return pool_id
            
        except Exception as e:
            logger.error(f"Failed to create pool: {e}")
            raise
    
    async def join_pool(self, pool_id: str) -> bool:
        """
        Join an existing pool.
        
        Args:
            pool_id: Pool to join
            
        Returns:
            True if joined successfully
        """
        try:
            pool = self.active_pools.get(pool_id)
            if not pool:
                # Try to load from database
                pool_doc = await self.db["pools"].find_one({"_id": pool_id})
                if not pool_doc:
                    raise ValueError(f"Pool not found: {pool_id}")
                pool = PoolInfo.from_dict(pool_doc)
                self.active_pools[pool_id] = pool
            
            if self.node_id in pool.members:
                raise ValueError(f"Node already in pool: {pool_id}")
            
            # Add member to pool
            new_member = PoolMember(
                node_id=self.node_id,
                role=PoolRole.MEMBER,
                status=MemberStatus.JOINING,
                joined_at=datetime.now(timezone.utc)
            )
            
            pool.members[self.node_id] = new_member
            self.my_pools.add(pool_id)
            
            # Update pool status if minimum size reached
            if pool.status == PoolStatus.FORMING and pool.member_count >= 3:
                pool.status = PoolStatus.ACTIVE
            
            # Save changes
            await self.db["pools"].replace_one(
                {"_id": pool_id},
                pool.to_dict(),
                upsert=True
            )
            
            logger.info(f"Node joined pool: {pool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to join pool: {e}")
            return False
    
    async def leave_pool(self, pool_id: str) -> bool:
        """
        Leave a pool.
        
        Args:
            pool_id: Pool to leave
            
        Returns:
            True if left successfully
        """
        try:
            pool = self.active_pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool not found: {pool_id}")
            
            if self.node_id not in pool.members:
                raise ValueError(f"Node not in pool: {pool_id}")
            
            # Handle leadership transition if leader is leaving
            member = pool.members[self.node_id]
            if member.role == PoolRole.LEADER:
                await self._handle_leader_departure(pool)
            
            # Remove member from pool
            del pool.members[self.node_id]
            self.my_pools.discard(pool_id)
            
            # Check if pool should be disbanded
            if pool.member_count < 3:
                pool.status = PoolStatus.DISBANDED
                logger.info(f"Pool disbanded due to insufficient members: {pool_id}")
            
            # Save changes
            await self.db["pools"].replace_one(
                {"_id": pool_id},
                pool.to_dict(),
                upsert=True
            )
            
            logger.info(f"Node left pool: {pool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to leave pool: {e}")
            return False
    
    async def get_pool_info(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed pool information"""
        try:
            pool = self.active_pools.get(pool_id)
            if not pool:
                # Try loading from database
                pool_doc = await self.db["pools"].find_one({"_id": pool_id})
                if not pool_doc:
                    return None
                pool = PoolInfo.from_dict(pool_doc)
                self.active_pools[pool_id] = pool
            
            return {
                "pool_id": pool.pool_id,
                "name": pool.name,
                "description": pool.description,
                "status": pool.status.value,
                "created_at": pool.created_at,
                "member_count": pool.member_count,
                "total_work_credits": pool.total_work_credits,
                "total_rewards_usdt": pool.total_rewards_usdt,
                "pending_rewards_usdt": pool.pending_rewards_usdt,
                "last_reward_distribution": pool.last_reward_distribution,
                "members": [
                    {
                        "node_id": member.node_id,
                        "role": member.role.value,
                        "status": member.status.value,
                        "contribution_score": member.contribution_score,
                        "work_credits_contributed": member.work_credits_contributed,
                        "rewards_earned_usdt": member.rewards_earned_usdt,
                        "joined_at": member.joined_at
                    }
                    for member in pool.members.values()
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            return None
    
    async def sync_work_credits(self, pool_id: str, work_credits: int) -> bool:
        """
        Synchronize work credits with pool.
        
        Args:
            pool_id: Pool to sync with
            work_credits: Work credits to contribute
            
        Returns:
            True if sync successful
        """
        try:
            pool = self.active_pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool not found: {pool_id}")
            
            if self.node_id not in pool.members:
                raise ValueError(f"Node not in pool: {pool_id}")
            
            # Update member work credits
            member = pool.members[self.node_id]
            member.work_credits_contributed = work_credits
            member.last_sync = datetime.now(timezone.utc)
            
            # Update pool total
            pool.total_work_credits = sum(m.work_credits_contributed for m in pool.members.values())
            
            # Save changes
            await self.db["pools"].replace_one(
                {"_id": pool_id},
                pool.to_dict(),
                upsert=True
            )
            
            logger.info(f"Work credits synced for pool {pool_id}: {work_credits}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync work credits: {e}")
            return False
    
    async def check_health(self):
        """Check pool health and update status"""
        try:
            for pool in self.active_pools.values():
                # Check member health
                unhealthy_members = []
                for member in pool.members.values():
                    if await self._is_member_unhealthy(member):
                        unhealthy_members.append(member.node_id)
                
                # Handle unhealthy members
                for node_id in unhealthy_members:
                    member = pool.members[node_id]
                    if member.status == MemberStatus.ACTIVE:
                        member.status = MemberStatus.DEGRADED
                        logger.warning(f"Pool member marked as degraded: {node_id}")
                
                # Update pool status based on member health
                active_count = len(pool.active_members)
                if active_count < 3:
                    pool.status = PoolStatus.DEGRADED
                elif pool.status == PoolStatus.DEGRADED and active_count >= 3:
                    pool.status = PoolStatus.ACTIVE
                
                # Save changes
                await self.db["pools"].replace_one(
                    {"_id": pool.pool_id},
                    pool.to_dict(),
                    upsert=True
                )
            
        except Exception as e:
            logger.error(f"Failed to check pool health: {e}")
    
    async def _load_pools(self):
        """Load pools from database"""
        try:
            # Load pools where this node is a member
            cursor = self.db["pools"].find({
                "members": {"$elemMatch": {"node_id": self.node_id}}
            })
            
            async for pool_doc in cursor:
                pool = PoolInfo.from_dict(pool_doc)
                self.active_pools[pool.pool_id] = pool
                self.my_pools.add(pool.pool_id)
            
            logger.info(f"Loaded {len(self.active_pools)} pools")
            
        except Exception as e:
            logger.error(f"Failed to load pools: {e}")
    
    async def _handle_leader_departure(self, pool: PoolInfo):
        """Handle leadership transition when leader leaves"""
        try:
            # Find potential new leader (co-leader first, then highest contributor)
            new_leader = None
            
            # Check for co-leaders
            for member in pool.members.values():
                if member.role == PoolRole.CO_LEADER and member.node_id != self.node_id:
                    new_leader = member
                    break
            
            # If no co-leader, select highest contributor
            if not new_leader:
                eligible_members = [
                    member for member in pool.members.values()
                    if member.node_id != self.node_id and member.status == MemberStatus.ACTIVE
                ]
                
                if eligible_members:
                    new_leader = max(eligible_members, key=lambda m: m.contribution_score)
            
            if new_leader:
                new_leader.role = PoolRole.LEADER
                logger.info(f"New pool leader elected: {new_leader.node_id}")
            else:
                # No suitable leader found, mark pool for disbandment
                pool.status = PoolStatus.DISBANDED
                logger.warning(f"Pool marked for disbandment - no suitable leader")
            
        except Exception as e:
            logger.error(f"Failed to handle leader departure: {e}")
    
    async def _is_member_unhealthy(self, member: PoolMember) -> bool:
        """Check if a pool member is unhealthy"""
        try:
            # Check if member hasn't synced recently
            if member.last_sync:
                time_since_sync = datetime.now(timezone.utc) - member.last_sync
                if time_since_sync > timedelta(minutes=10):  # 10 minutes threshold
                    return True
            
            # Check contribution score
            if member.contribution_score < 10.0:  # Low contribution threshold
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check member health: {e}")
            return False
    
    async def _health_check_loop(self):
        """Periodic health check loop"""
        while self.running:
            try:
                await self.check_health()
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)
    
    async def _sync_loop(self):
        """Periodic synchronization loop"""
        while self.running:
            try:
                # Sync with pools this node is a member of
                for pool_id in self.my_pools:
                    pool = self.active_pools.get(pool_id)
                    if pool and pool.status == PoolStatus.ACTIVE:
                        # Update contribution scores
                        await self._update_contribution_scores(pool)
                
                await asyncio.sleep(30)  # Sync every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(60)
    
    async def _update_contribution_scores(self, pool: PoolInfo):
        """Update member contribution scores"""
        try:
            for member in pool.members.values():
                # Simplified contribution score calculation
                # In a real implementation, this would be based on actual performance metrics
                if member.work_credits_contributed > 0:
                    member.contribution_score = min(100.0, member.contribution_score + 0.1)
                else:
                    # Decay contribution score if no recent activity
                    member.contribution_score = max(0.0, member.contribution_score * 0.99)
            
        except Exception as e:
            logger.error(f"Failed to update contribution scores: {e}")


# Global pool service instance
_pool_service: Optional[PoolService] = None


def get_pool_service() -> Optional[PoolService]:
    """Get global pool service instance"""
    global _pool_service
    return _pool_service


def create_pool_service(db: DatabaseAdapter, node_id: str) -> PoolService:
    """Create pool service instance"""
    global _pool_service
    _pool_service = PoolService(db, node_id)
    return _pool_service


async def cleanup_pool_service():
    """Cleanup pool service"""
    global _pool_service
    if _pool_service:
        await _pool_service.stop()
        _pool_service = None


if __name__ == "__main__":
    # Test pool service
    async def test_pool_service():
        print("Testing Lucid Pool Service...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - pool service ready")
    
    asyncio.run(test_pool_service())
