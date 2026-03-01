# Path: node/pools/node_pool_systems.py
# Lucid RDP Node Pool Systems - Comprehensive pool management for coordinated node operations
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json

# Database adapter handles compatibility
from ..database_adapter import DatabaseAdapter, get_database_adapter

# Import existing components using relative imports
from ..peer_discovery import PeerDiscovery
from ..work_credits import WorkCreditsCalculator

logger = logging.getLogger(__name__)

# Optional blockchain integration
try:
    from blockchain.core.blockchain_engine import get_blockchain_engine
except ImportError:
    get_blockchain_engine = None
    logger.warning("Blockchain engine not available - blockchain integration disabled")

# Pool System Constants
MIN_POOL_SIZE = int(os.getenv("LUCID_MIN_POOL_SIZE", "3"))  # Minimum 3 nodes per pool
MAX_POOL_SIZE = int(os.getenv("LUCID_MAX_POOL_SIZE", "50"))  # Maximum 50 nodes per pool
POOL_SYNC_INTERVAL_SEC = int(os.getenv("LUCID_POOL_SYNC_INTERVAL_SEC", "30"))  # 30 seconds
POOL_HEALTH_CHECK_SEC = int(os.getenv("LUCID_POOL_HEALTH_CHECK_SEC", "120"))  # 2 minutes
REWARD_DISTRIBUTION_THRESHOLD = float(os.getenv("LUCID_REWARD_DISTRIBUTION_THRESHOLD", "1.0"))  # 1 USDT


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


@dataclass
class PoolConfiguration:
    """Pool configuration settings"""
    reward_distribution_method: str = "contribution_weighted"  # equal, contribution_weighted, work_credits
    minimum_uptime_requirement: float = 0.95  # 95% minimum uptime
    auto_kick_threshold: float = 0.8  # Auto-kick if performance below 80%
    leader_rotation_enabled: bool = True
    leader_rotation_interval_hours: int = 168  # Weekly rotation
    sync_tolerance_ms: int = 1000  # 1 second sync tolerance
    require_unanimous_decisions: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "reward_distribution_method": self.reward_distribution_method,
            "minimum_uptime_requirement": self.minimum_uptime_requirement,
            "auto_kick_threshold": self.auto_kick_threshold,
            "leader_rotation_enabled": self.leader_rotation_enabled,
            "leader_rotation_interval_hours": self.leader_rotation_interval_hours,
            "sync_tolerance_ms": self.sync_tolerance_ms,
            "require_unanimous_decisions": self.require_unanimous_decisions
        }


@dataclass
class NodePool:
    """Node pool representation"""
    pool_id: str
    name: str
    description: str
    status: PoolStatus
    created_at: datetime
    creator_node_id: str
    members: Dict[str, PoolMember] = field(default_factory=dict)
    configuration: PoolConfiguration = field(default_factory=PoolConfiguration)
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
            "configuration": self.configuration.to_dict(),
            "total_work_credits": self.total_work_credits,
            "total_rewards_usdt": self.total_rewards_usdt,
            "pending_rewards_usdt": self.pending_rewards_usdt,
            "last_reward_distribution": self.last_reward_distribution
        }


@dataclass
class JoinRequest:
    """Pool join request"""
    request_id: str
    pool_id: str
    node_id: str
    message: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending, approved, rejected
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.request_id,
            "pool_id": self.pool_id,
            "node_id": self.node_id,
            "message": self.message,
            "created_at": self.created_at,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at
        }


@dataclass
class PoolSyncOperation:
    """Pool synchronization operation"""
    sync_id: str
    pool_id: str
    operation_type: str  # work_credits_sync, reward_distribution, member_update
    initiated_by: str
    data: Dict[str, Any]
    members_synced: Set[str] = field(default_factory=set)
    members_pending: Set[str] = field(default_factory=set)
    completed: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.sync_id,
            "pool_id": self.pool_id,
            "operation_type": self.operation_type,
            "initiated_by": self.initiated_by,
            "data": self.data,
            "members_synced": list(self.members_synced),
            "members_pending": list(self.members_pending),
            "completed": self.completed,
            "timestamp": self.timestamp
        }


class NodePoolSystem:
    """
    Node Pool System for coordinated multi-node operations.
    
    Handles:
    - Pool creation, joining, and leaving
    - Coordinated work credit aggregation
    - Reward distribution among pool members
    - Pool leader election and rotation
    - Synchronized operations across pool members
    - Pool health monitoring and maintenance
    """
    
    def __init__(self, db: DatabaseAdapter, peer_discovery: PeerDiscovery, 
                 work_credits: WorkCreditsCalculator):
        self.db = db
        self.peer_discovery = peer_discovery
        self.work_credits = work_credits
        
        # State tracking
        self.active_pools: Dict[str, NodePool] = {}
        self.my_pools: Set[str] = set()  # Pools this node is a member of
        self.join_requests: Dict[str, JoinRequest] = {}
        self.sync_operations: Dict[str, PoolSyncOperation] = {}
        self.running = False
        
        # Background tasks
        self._sync_task: Optional[asyncio.Task] = None
        self._health_task: Optional[asyncio.Task] = None
        self._rewards_task: Optional[asyncio.Task] = None
        
        logger.info("Node pool system initialized")
    
    async def start(self):
        """Start node pool system"""
        try:
            self.running = True
            
            # Setup database indexes
            await self._setup_indexes()
            
            # Load existing pools and membership
            await self._load_pools()
            await self._load_join_requests()
            
            # Start background tasks
            self._sync_task = asyncio.create_task(self._sync_loop())
            self._health_task = asyncio.create_task(self._health_check_loop())
            self._rewards_task = asyncio.create_task(self._rewards_distribution_loop())
            
            logger.info("Node pool system started")
            
        except Exception as e:
            logger.error(f"Failed to start node pool system: {e}")
            raise
    
    async def stop(self):
        """Stop node pool system"""
        try:
            self.running = False
            
            # Cancel background tasks
            tasks = [self._sync_task, self._health_task, self._rewards_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
            
            logger.info("Node pool system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping node pool system: {e}")
    
    async def create_pool(self, creator_node_id: str, name: str, description: str,
                         configuration: Optional[PoolConfiguration] = None) -> str:
        """
        Create a new node pool.
        
        Args:
            creator_node_id: Node ID of the creator
            name: Pool name
            description: Pool description
            configuration: Pool configuration (optional)
            
        Returns:
            Pool ID
        """
        try:
            pool_id = str(uuid.uuid4())
            config = configuration or PoolConfiguration()
            
            # Create pool leader member
            leader_member = PoolMember(
                node_id=creator_node_id,
                role=PoolRole.LEADER,
                status=MemberStatus.ACTIVE,
                joined_at=datetime.now(timezone.utc)
            )
            
            pool = NodePool(
                pool_id=pool_id,
                name=name,
                description=description,
                status=PoolStatus.FORMING,
                created_at=datetime.now(timezone.utc),
                creator_node_id=creator_node_id,
                configuration=config
            )
            
            pool.members[creator_node_id] = leader_member
            
            # Store pool
            self.active_pools[pool_id] = pool
            await self.db["node_pools"].replace_one(
                {"_id": pool_id},
                pool.to_dict(),
                upsert=True
            )
            
            # Add to my pools if I'm the creator
            # In a real implementation, you'd check if creator_node_id is the current node
            self.my_pools.add(pool_id)
            
            logger.info(f"Pool created: {pool_id} ({name}) by {creator_node_id}")
            return pool_id
            
        except Exception as e:
            logger.error(f"Failed to create pool: {e}")
            raise
    
    async def request_join_pool(self, node_id: str, pool_id: str, message: str = "") -> str:
        """
        Request to join a pool.
        
        Args:
            node_id: Node ID requesting to join
            pool_id: Pool to join
            message: Optional message for the request
            
        Returns:
            Request ID
        """
        try:
            pool = self.active_pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool not found: {pool_id}")
            
            if pool.member_count >= MAX_POOL_SIZE:
                raise ValueError(f"Pool is full: {pool.member_count}/{MAX_POOL_SIZE}")
            
            if node_id in pool.members:
                raise ValueError(f"Node already in pool: {node_id}")
            
            request_id = str(uuid.uuid4())
            
            join_request = JoinRequest(
                request_id=request_id,
                pool_id=pool_id,
                node_id=node_id,
                message=message
            )
            
            self.join_requests[request_id] = join_request
            await self.db["pool_join_requests"].replace_one(
                {"_id": request_id},
                join_request.to_dict(),
                upsert=True
            )
            
            logger.info(f"Join request created: {request_id} for pool {pool_id} by {node_id}")
            return request_id
            
        except Exception as e:
            logger.error(f"Failed to create join request: {e}")
            raise
    
    async def approve_join_request(self, request_id: str, approver_node_id: str) -> bool:
        """
        Approve a join request.
        
        Args:
            request_id: Request to approve
            approver_node_id: Node ID of approver
            
        Returns:
            True if approved successfully
        """
        try:
            request = self.join_requests.get(request_id)
            if not request:
                raise ValueError(f"Join request not found: {request_id}")
            
            if request.status != "pending":
                raise ValueError(f"Request already processed: {request.status}")
            
            pool = self.active_pools.get(request.pool_id)
            if not pool:
                raise ValueError(f"Pool not found: {request.pool_id}")
            
            # Check if approver has permission (leader or co-leader)
            approver_member = pool.members.get(approver_node_id)
            if not approver_member or approver_member.role not in [PoolRole.LEADER, PoolRole.CO_LEADER]:
                raise ValueError(f"Approver lacks permission: {approver_node_id}")
            
            # Add member to pool
            new_member = PoolMember(
                node_id=request.node_id,
                role=PoolRole.MEMBER,
                status=MemberStatus.JOINING,
                joined_at=datetime.now(timezone.utc)
            )
            
            pool.members[request.node_id] = new_member
            
            # Update request
            request.status = "approved"
            request.reviewed_by = approver_node_id
            request.reviewed_at = datetime.now(timezone.utc)
            
            # Save changes
            await self.db["node_pools"].replace_one(
                {"_id": pool.pool_id},
                pool.to_dict(),
                upsert=True
            )
            
            await self.db["pool_join_requests"].replace_one(
                {"_id": request_id},
                request.to_dict(),
                upsert=True
            )
            
            # Remove from pending requests
            del self.join_requests[request_id]
            
            # Activate pool if minimum size reached
            if pool.status == PoolStatus.FORMING and pool.member_count >= MIN_POOL_SIZE:
                pool.status = PoolStatus.ACTIVE
                await self.db["node_pools"].update_one(
                    {"_id": pool.pool_id},
                    {"$set": {"status": pool.status.value}}
                )
            
            logger.info(f"Join request approved: {request_id} by {approver_node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve join request: {e}")
            return False
    
    async def leave_pool(self, node_id: str, pool_id: str) -> bool:
        """
        Leave a pool.
        
        Args:
            node_id: Node leaving the pool
            pool_id: Pool to leave
            
        Returns:
            True if left successfully
        """
        try:
            pool = self.active_pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool not found: {pool_id}")
            
            member = pool.members.get(node_id)
            if not member:
                raise ValueError(f"Node not in pool: {node_id}")
            
            # Handle leadership transition if leader is leaving
            if member.role == PoolRole.LEADER:
                await self._handle_leader_departure(pool, node_id)
            
            # Remove member from pool
            del pool.members[node_id]
            self.my_pools.discard(pool_id)
            
            # Check if pool should be disbanded
            if pool.member_count < MIN_POOL_SIZE:
                pool.status = PoolStatus.DISBANDED
                logger.info(f"Pool disbanded due to insufficient members: {pool_id}")
            
            # Save changes
            await self.db["node_pools"].replace_one(
                {"_id": pool_id},
                pool.to_dict(),
                upsert=True
            )
            
            logger.info(f"Node left pool: {node_id} left {pool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to leave pool: {e}")
            return False
    
    async def distribute_rewards(self, pool_id: str) -> bool:
        """
        Distribute pending rewards among pool members.
        
        Args:
            pool_id: Pool to distribute rewards for
            
        Returns:
            True if distribution successful
        """
        try:
            pool = self.active_pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool not found: {pool_id}")
            
            if pool.pending_rewards_usdt < REWARD_DISTRIBUTION_THRESHOLD:
                logger.info(f"Insufficient rewards for distribution: {pool.pending_rewards_usdt} USDT")
                return False
            
            # Calculate individual rewards based on configuration
            member_rewards = await self._calculate_member_rewards(pool)
            
            # Create sync operation for reward distribution
            sync_id = str(uuid.uuid4())
            sync_operation = PoolSyncOperation(
                sync_id=sync_id,
                pool_id=pool_id,
                operation_type="reward_distribution",
                initiated_by="system",  # System-initiated
                data={
                    "total_amount": pool.pending_rewards_usdt,
                    "member_rewards": member_rewards
                },
                members_pending=set(pool.members.keys())
            )
            
            self.sync_operations[sync_id] = sync_operation
            await self.db["pool_sync_operations"].replace_one(
                {"_id": sync_id},
                sync_operation.to_dict(),
                upsert=True
            )
            
            # Update pool state
            pool.total_rewards_usdt += pool.pending_rewards_usdt
            pool.pending_rewards_usdt = 0.0
            pool.last_reward_distribution = datetime.now(timezone.utc)
            
            # Update member rewards
            for node_id, reward in member_rewards.items():
                if node_id in pool.members:
                    pool.members[node_id].rewards_earned_usdt += reward
            
            await self.db["node_pools"].replace_one(
                {"_id": pool_id},
                pool.to_dict(),
                upsert=True
            )
            
            logger.info(f"Rewards distributed for pool {pool_id}: {sum(member_rewards.values())} USDT")
            return True
            
        except Exception as e:
            logger.error(f"Failed to distribute rewards: {e}")
            return False
    
    async def get_pool_info(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed pool information"""
        try:
            pool = self.active_pools.get(pool_id)
            if not pool:
                # Try loading from database
                pool_doc = await self.db["node_pools"].find_one({"_id": pool_id})
                if not pool_doc:
                    return None
                pool = await self._pool_from_dict(pool_doc)
            
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
                ],
                "configuration": pool.configuration.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            return None
    
    async def sync_work_credits(self, pool_id: str, node_work_credits: Dict[str, int]) -> bool:
        """
        Synchronize work credits across pool members.
        
        Args:
            pool_id: Pool to sync
            node_work_credits: Work credits per node
            
        Returns:
            True if sync initiated successfully
        """
        try:
            pool = self.active_pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool not found: {pool_id}")
            
            sync_id = str(uuid.uuid4())
            sync_operation = PoolSyncOperation(
                sync_id=sync_id,
                pool_id=pool_id,
                operation_type="work_credits_sync",
                initiated_by="system",
                data={"work_credits": node_work_credits},
                members_pending=set(pool.members.keys())
            )
            
            self.sync_operations[sync_id] = sync_operation
            await self.db["pool_sync_operations"].replace_one(
                {"_id": sync_id},
                sync_operation.to_dict(),
                upsert=True
            )
            
            # Update pool work credits
            pool.total_work_credits = sum(node_work_credits.values())
            
            # Update member contributions
            for node_id, credits in node_work_credits.items():
                if node_id in pool.members:
                    pool.members[node_id].work_credits_contributed = credits
            
            await self.db["node_pools"].replace_one(
                {"_id": pool_id},
                pool.to_dict(),
                upsert=True
            )
            
            logger.info(f"Work credits sync initiated for pool {pool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync work credits: {e}")
            return False
    
    async def _calculate_member_rewards(self, pool: NodePool) -> Dict[str, float]:
        """Calculate reward distribution for pool members"""
        try:
            member_rewards = {}
            active_members = pool.active_members
            
            if not active_members:
                return member_rewards
            
            total_amount = pool.pending_rewards_usdt
            
            if pool.configuration.reward_distribution_method == "equal":
                # Equal distribution
                per_member = total_amount / len(active_members)
                for member in active_members:
                    member_rewards[member.node_id] = per_member
                    
            elif pool.configuration.reward_distribution_method == "contribution_weighted":
                # Distribution based on contribution scores
                total_contribution = sum(member.contribution_score for member in active_members)
                if total_contribution > 0:
                    for member in active_members:
                        weight = member.contribution_score / total_contribution
                        member_rewards[member.node_id] = total_amount * weight
                else:
                    # Fall back to equal if no contributions
                    per_member = total_amount / len(active_members)
                    for member in active_members:
                        member_rewards[member.node_id] = per_member
                        
            elif pool.configuration.reward_distribution_method == "work_credits":
                # Distribution based on work credits
                total_work_credits = sum(member.work_credits_contributed for member in active_members)
                if total_work_credits > 0:
                    for member in active_members:
                        weight = member.work_credits_contributed / total_work_credits
                        member_rewards[member.node_id] = total_amount * weight
                else:
                    # Fall back to equal if no work credits
                    per_member = total_amount / len(active_members)
                    for member in active_members:
                        member_rewards[member.node_id] = per_member
            
            return member_rewards
            
        except Exception as e:
            logger.error(f"Failed to calculate member rewards: {e}")
            return {}
    
    async def _handle_leader_departure(self, pool: NodePool, departing_leader_id: str):
        """Handle leadership transition when leader leaves"""
        try:
            # Find potential new leader (co-leader first, then highest contributor)
            new_leader = None
            
            # Check for co-leaders
            for member in pool.members.values():
                if member.role == PoolRole.CO_LEADER and member.node_id != departing_leader_id:
                    new_leader = member
                    break
            
            # If no co-leader, select highest contributor
            if not new_leader:
                eligible_members = [
                    member for member in pool.members.values()
                    if member.node_id != departing_leader_id and member.status == MemberStatus.ACTIVE
                ]
                
                if eligible_members:
                    new_leader = max(eligible_members, key=lambda m: m.contribution_score)
            
            if new_leader:
                new_leader.role = PoolRole.LEADER
                logger.info(f"New pool leader elected: {new_leader.node_id} for pool {pool.pool_id}")
            else:
                # No suitable leader found, mark pool for disbandment
                pool.status = PoolStatus.DISBANDED
                logger.warning(f"Pool marked for disbandment - no suitable leader: {pool.pool_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle leader departure: {e}")
    
    async def _sync_loop(self):
        """Periodic synchronization with pool members"""
        while self.running:
            try:
                for pool_id in self.my_pools:
                    pool = self.active_pools.get(pool_id)
                    if not pool or pool.status != PoolStatus.ACTIVE:
                        continue
                    
                    try:
                        # Update contribution scores based on recent activity
                        await self._update_contribution_scores(pool)
                        
                        # Check for pending sync operations
                        await self._process_sync_operations(pool)
                        
                    except Exception as pool_error:
                        logger.error(f"Sync error for pool {pool_id}: {pool_error}")
                
                await asyncio.sleep(POOL_SYNC_INTERVAL_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(30)
    
    async def _health_check_loop(self):
        """Monitor pool and member health"""
        while self.running:
            try:
                for pool in self.active_pools.values():
                    try:
                        # Check member health
                        unhealthy_members = []
                        for member in pool.members.values():
                            if await self._is_member_unhealthy(member):
                                unhealthy_members.append(member.node_id)
                        
                        # Handle unhealthy members
                        for node_id in unhealthy_members:
                            await self._handle_unhealthy_member(pool, node_id)
                        
                        # Check overall pool health
                        await self._update_pool_health(pool)
                        
                    except Exception as pool_error:
                        logger.error(f"Health check error for pool {pool.pool_id}: {pool_error}")
                
                await asyncio.sleep(POOL_HEALTH_CHECK_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)
    
    async def _rewards_distribution_loop(self):
        """Periodic reward distribution"""
        while self.running:
            try:
                for pool in self.active_pools.values():
                    if (pool.status == PoolStatus.ACTIVE and 
                        pool.pending_rewards_usdt >= REWARD_DISTRIBUTION_THRESHOLD):
                        
                        try:
                            await self.distribute_rewards(pool.pool_id)
                        except Exception as pool_error:
                            logger.error(f"Reward distribution error for pool {pool.pool_id}: {pool_error}")
                
                # Check every hour for reward distribution
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rewards distribution loop error: {e}")
                await asyncio.sleep(300)
    
    async def _update_contribution_scores(self, pool: NodePool):
        """Update member contribution scores based on recent activity"""
        try:
            for member in pool.members.values():
                # Get recent work credits for this member
                recent_credits = await self.work_credits.calculate_work_credits(
                    member.node_id, window_days=1
                )
                
                # Update contribution score (simplified calculation)
                if recent_credits > 0:
                    member.contribution_score = min(100.0, member.contribution_score + recent_credits * 0.01)
                else:
                    # Decay contribution score if no recent activity
                    member.contribution_score = max(0.0, member.contribution_score * 0.99)
            
        except Exception as e:
            logger.error(f"Failed to update contribution scores: {e}")
    
    async def _process_sync_operations(self, pool: NodePool):
        """Process pending synchronization operations"""
        try:
            # Get pending sync operations for this pool
            cursor = self.db["pool_sync_operations"].find({
                "pool_id": pool.pool_id,
                "completed": False
            })
            
            async for sync_doc in cursor:
                sync_op = PoolSyncOperation(
                    sync_id=sync_doc["_id"],
                    pool_id=sync_doc["pool_id"],
                    operation_type=sync_doc["operation_type"],
                    initiated_by=sync_doc["initiated_by"],
                    data=sync_doc["data"],
                    members_synced=set(sync_doc.get("members_synced", [])),
                    members_pending=set(sync_doc.get("members_pending", [])),
                    completed=sync_doc["completed"],
                    timestamp=sync_doc["timestamp"]
                )
                
                # In a real implementation, this would communicate with other nodes
                # For now, mark all members as synced
                sync_op.members_synced = set(pool.members.keys())
                sync_op.members_pending = set()
                sync_op.completed = True
                
                await self.db["pool_sync_operations"].update_one(
                    {"_id": sync_op.sync_id},
                    {"$set": {
                        "members_synced": list(sync_op.members_synced),
                        "members_pending": list(sync_op.members_pending),
                        "completed": sync_op.completed
                    }}
                )
            
        except Exception as e:
            logger.error(f"Failed to process sync operations: {e}")
    
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
    
    async def _handle_unhealthy_member(self, pool: NodePool, node_id: str):
        """Handle unhealthy pool member"""
        try:
            member = pool.members.get(node_id)
            if not member:
                return
            
            if member.status == MemberStatus.ACTIVE:
                member.status = MemberStatus.DEGRADED
                logger.warning(f"Pool member marked as degraded: {node_id} in pool {pool.pool_id}")
                
                # Save changes
                await self.db["node_pools"].replace_one(
                    {"_id": pool.pool_id},
                    pool.to_dict(),
                    upsert=True
                )
            
        except Exception as e:
            logger.error(f"Failed to handle unhealthy member: {e}")
    
    async def _update_pool_health(self, pool: NodePool):
        """Update overall pool health status"""
        try:
            active_count = len(pool.active_members)
            degraded_count = sum(1 for m in pool.members.values() if m.status == MemberStatus.DEGRADED)
            
            # Update pool status based on member health
            if active_count < MIN_POOL_SIZE:
                pool.status = PoolStatus.DEGRADED
            elif degraded_count > active_count // 2:  # More than half degraded
                pool.status = PoolStatus.DEGRADED
            elif pool.status == PoolStatus.DEGRADED and active_count >= MIN_POOL_SIZE:
                pool.status = PoolStatus.ACTIVE
            
        except Exception as e:
            logger.error(f"Failed to update pool health: {e}")
    
    async def _setup_indexes(self):
        """Setup database indexes"""
        try:
            # Node pools indexes
            await self.db["node_pools"].create_index("name")
            await self.db["node_pools"].create_index("status")
            await self.db["node_pools"].create_index("created_at")
            await self.db["node_pools"].create_index("creator_node_id")
            
            # Join requests indexes
            await self.db["pool_join_requests"].create_index("pool_id")
            await self.db["pool_join_requests"].create_index("node_id")
            await self.db["pool_join_requests"].create_index("status")
            await self.db["pool_join_requests"].create_index("created_at")
            
            # Sync operations indexes
            await self.db["pool_sync_operations"].create_index("pool_id")
            await self.db["pool_sync_operations"].create_index("completed")
            await self.db["pool_sync_operations"].create_index("timestamp")
            
            logger.info("Node pool system database indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create pool system indexes: {e}")
    
    async def _load_pools(self):
        """Load pools from database"""
        try:
            cursor = self.db["node_pools"].find({"status": {"$ne": PoolStatus.DISBANDED.value}})
            
            async for pool_doc in cursor:
                pool = await self._pool_from_dict(pool_doc)
                self.active_pools[pool.pool_id] = pool
                
                # Check if current node is a member (simplified check)
                # In real implementation, this would be based on actual node ID
                if len(pool.members) > 0:  # Mock membership
                    self.my_pools.add(pool.pool_id)
            
            logger.info(f"Loaded {len(self.active_pools)} active pools")
            
        except Exception as e:
            logger.error(f"Failed to load pools: {e}")
    
    async def _load_join_requests(self):
        """Load pending join requests"""
        try:
            cursor = self.db["pool_join_requests"].find({"status": "pending"})
            
            async for request_doc in cursor:
                request = JoinRequest(
                    request_id=request_doc["_id"],
                    pool_id=request_doc["pool_id"],
                    node_id=request_doc["node_id"],
                    message=request_doc["message"],
                    created_at=request_doc["created_at"],
                    status=request_doc["status"]
                )
                
                self.join_requests[request.request_id] = request
            
            logger.info(f"Loaded {len(self.join_requests)} pending join requests")
            
        except Exception as e:
            logger.error(f"Failed to load join requests: {e}")
    
    async def _pool_from_dict(self, pool_doc: Dict[str, Any]) -> NodePool:
        """Convert database document to NodePool object"""
        # Load members
        members = {}
        for node_id, member_data in pool_doc.get("members", {}).items():
            member = PoolMember(
                node_id=member_data["node_id"],
                role=PoolRole(member_data["role"]),
                status=MemberStatus(member_data["status"]),
                joined_at=member_data["joined_at"],
                contribution_score=member_data.get("contribution_score", 0.0),
                work_credits_contributed=member_data.get("work_credits_contributed", 0),
                rewards_earned_usdt=member_data.get("rewards_earned_usdt", 0.0),
                last_sync=member_data.get("last_sync"),
                performance_metrics=member_data.get("performance_metrics", {})
            )
            members[node_id] = member
        
        # Load configuration
        config_data = pool_doc.get("configuration", {})
        configuration = PoolConfiguration(
            reward_distribution_method=config_data.get("reward_distribution_method", "contribution_weighted"),
            minimum_uptime_requirement=config_data.get("minimum_uptime_requirement", 0.95),
            auto_kick_threshold=config_data.get("auto_kick_threshold", 0.8),
            leader_rotation_enabled=config_data.get("leader_rotation_enabled", True),
            leader_rotation_interval_hours=config_data.get("leader_rotation_interval_hours", 168),
            sync_tolerance_ms=config_data.get("sync_tolerance_ms", 1000),
            require_unanimous_decisions=config_data.get("require_unanimous_decisions", False)
        )
        
        pool = NodePool(
            pool_id=pool_doc["_id"],
            name=pool_doc["name"],
            description=pool_doc["description"],
            status=PoolStatus(pool_doc["status"]),
            created_at=pool_doc["created_at"],
            creator_node_id=pool_doc["creator_node_id"],
            members=members,
            configuration=configuration,
            total_work_credits=pool_doc.get("total_work_credits", 0),
            total_rewards_usdt=pool_doc.get("total_rewards_usdt", 0.0),
            pending_rewards_usdt=pool_doc.get("pending_rewards_usdt", 0.0),
            last_reward_distribution=pool_doc.get("last_reward_distribution")
        )
        
        return pool


# Global node pool system instance
_node_pool_system: Optional[NodePoolSystem] = None


def get_node_pool_system() -> Optional[NodePoolSystem]:
    """Get global node pool system instance"""
    global _node_pool_system
    return _node_pool_system


def create_node_pool_system(db: DatabaseAdapter, peer_discovery: PeerDiscovery,
                           work_credits: WorkCreditsCalculator) -> NodePoolSystem:
    """Create node pool system instance"""
    global _node_pool_system
    _node_pool_system = NodePoolSystem(db, peer_discovery, work_credits)
    return _node_pool_system


async def cleanup_node_pool_system():
    """Cleanup node pool system"""
    global _node_pool_system
    if _node_pool_system:
        await _node_pool_system.stop()
        _node_pool_system = None


if __name__ == "__main__":
    # Test node pool system
    async def test_node_pool_system():
        print("Testing Lucid Node Pool System...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - node pool system ready")
    
    asyncio.run(test_node_pool_system())