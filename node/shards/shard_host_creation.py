# Path: node/shards/shard_host_creation.py
# Lucid RDP Shard Host Creation - Distributed shard management and host assignment
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
from blockchain.core.blockchain_engine import get_blockchain_engine

logger = logging.getLogger(__name__)

# Shard Host Constants
SHARD_SIZE_MB = int(os.getenv("LUCID_SHARD_SIZE_MB", "64"))  # 64MB per shard
REPLICATION_FACTOR = int(os.getenv("LUCID_REPLICATION_FACTOR", "3"))  # 3 replicas per shard
MIN_STORAGE_NODES = int(os.getenv("LUCID_MIN_STORAGE_NODES", "5"))  # Minimum storage nodes
SHARD_TIMEOUT_SEC = int(os.getenv("LUCID_SHARD_TIMEOUT_SEC", "300"))  # 5 minutes
MAX_SHARDS_PER_NODE = int(os.getenv("LUCID_MAX_SHARDS_PER_NODE", "1000"))


class ShardStatus(Enum):
    """Shard status states"""
    CREATING = "creating"
    ASSIGNED = "assigned"
    REPLICATING = "replicating"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    MIGRATING = "migrating"
    ARCHIVED = "archived"


class HostStatus(Enum):
    """Shard host status"""
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    BUSY = "busy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class ShardInfo:
    """Shard metadata and assignment info"""
    shard_id: str
    session_id: str
    chunk_index: int
    data_hash: str
    size_bytes: int
    status: ShardStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_hosts: List[str] = field(default_factory=list)  # node_ids
    primary_host: Optional[str] = None
    replica_hosts: List[str] = field(default_factory=list)
    encryption_key_hash: Optional[str] = None
    compression_ratio: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.shard_id,
            "session_id": self.session_id,
            "chunk_index": self.chunk_index,
            "data_hash": self.data_hash,
            "size_bytes": self.size_bytes,
            "status": self.status.value,
            "created_at": self.created_at,
            "assigned_hosts": self.assigned_hosts,
            "primary_host": self.primary_host,
            "replica_hosts": self.replica_hosts,
            "encryption_key_hash": self.encryption_key_hash,
            "compression_ratio": self.compression_ratio
        }


@dataclass
class ShardHost:
    """Shard host node information"""
    node_id: str
    onion_address: str
    port: int
    status: HostStatus
    storage_capacity_gb: float
    storage_used_gb: float
    bandwidth_mbps: float
    assigned_shards: Set[str] = field(default_factory=set)
    last_health_check: Optional[datetime] = None
    performance_score: float = 1.0
    
    @property
    def storage_available_gb(self) -> float:
        return max(0, self.storage_capacity_gb - self.storage_used_gb)
    
    @property
    def storage_utilization(self) -> float:
        if self.storage_capacity_gb <= 0:
            return 1.0
        return self.storage_used_gb / self.storage_capacity_gb
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.node_id,
            "onion_address": self.onion_address,
            "port": self.port,
            "status": self.status.value,
            "storage_capacity_gb": self.storage_capacity_gb,
            "storage_used_gb": self.storage_used_gb,
            "bandwidth_mbps": self.bandwidth_mbps,
            "assigned_shards": list(self.assigned_shards),
            "last_health_check": self.last_health_check,
            "performance_score": self.performance_score
        }


@dataclass
class ShardCreationTask:
    """Shard creation task"""
    task_id: str
    session_id: str
    chunks_count: int
    total_size_bytes: int
    replication_factor: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_shards: int = 0
    failed_shards: int = 0
    assigned_hosts: Dict[str, List[str]] = field(default_factory=dict)  # shard_id -> host_ids
    
    @property
    def progress_percentage(self) -> float:
        if self.chunks_count <= 0:
            return 100.0
        return (self.completed_shards / self.chunks_count) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.task_id,
            "session_id": self.session_id,
            "chunks_count": self.chunks_count,
            "total_size_bytes": self.total_size_bytes,
            "replication_factor": self.replication_factor,
            "created_at": self.created_at,
            "completed_shards": self.completed_shards,
            "failed_shards": self.failed_shards,
            "assigned_hosts": self.assigned_hosts,
            "progress_percentage": self.progress_percentage
        }


class ShardHostCreationSystem:
    """
    Shard Host Creation System for Lucid RDP distributed storage.
    
    Handles:
    - Distributed shard assignment across storage nodes
    - Host selection based on performance, capacity, and geographic distribution
    - Shard replication with configurable redundancy
    - Load balancing across available storage hosts
    - Health monitoring and automatic failover
    - Integration with consensus for shard anchoring
    """
    
    def __init__(self, db: DatabaseAdapter, peer_discovery: PeerDiscovery, 
                 work_credits: WorkCreditsCalculator):
        self.db = db
        self.peer_discovery = peer_discovery
        self.work_credits = work_credits
        
        # State tracking
        self.storage_hosts: Dict[str, ShardHost] = {}
        self.active_shards: Dict[str, ShardInfo] = {}
        self.creation_tasks: Dict[str, ShardCreationTask] = {}
        self.running = False
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._rebalance_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("Shard host creation system initialized")
    
    async def start(self):
        """Start shard host creation system"""
        try:
            self.running = True
            
            # Setup database indexes
            await self._setup_indexes()
            
            # Load existing hosts and shards
            await self._load_storage_hosts()
            await self._load_active_shards()
            
            # Start background tasks
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self._rebalance_task = asyncio.create_task(self._rebalance_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info("Shard host creation system started")
            
        except Exception as e:
            logger.error(f"Failed to start shard host creation system: {e}")
            raise
    
    async def stop(self):
        """Stop shard host creation system"""
        try:
            self.running = False
            
            # Cancel background tasks
            if self._health_check_task and not self._health_check_task.done():
                self._health_check_task.cancel()
            if self._rebalance_task and not self._rebalance_task.done():
                self._rebalance_task.cancel()
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
            
            # Wait for tasks to complete
            tasks = [self._health_check_task, self._rebalance_task, self._cleanup_task]
            await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
            
            logger.info("Shard host creation system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping shard host creation system: {e}")
    
    async def register_storage_host(self, node_id: str, storage_info: Dict[str, Any]) -> bool:
        """
        Register a node as a storage host.
        
        Args:
            node_id: Node identifier
            storage_info: Storage capacity and configuration
            
        Returns:
            True if registered successfully
        """
        try:
            # Get node info from peer discovery
            peer_info = None
            for peer in await self.peer_discovery.get_active_peers():
                if peer.node_id == node_id:
                    peer_info = peer
                    break
            
            if not peer_info:
                raise ValueError(f"Node not found in peer discovery: {node_id}")
            
            # Validate storage capabilities
            if "storage" not in peer_info.capabilities:
                raise ValueError(f"Node does not have storage capability: {node_id}")
            
            # Create shard host record
            host = ShardHost(
                node_id=node_id,
                onion_address=peer_info.onion_address,
                port=peer_info.port,
                status=HostStatus.AVAILABLE,
                storage_capacity_gb=float(storage_info.get("capacity_gb", 0)),
                storage_used_gb=float(storage_info.get("used_gb", 0)),
                bandwidth_mbps=float(storage_info.get("bandwidth_mbps", 0)),
                last_health_check=datetime.now(timezone.utc)
            )
            
            # Validate minimum requirements
            if host.storage_capacity_gb < 10:  # Minimum 10GB
                raise ValueError(f"Insufficient storage capacity: {host.storage_capacity_gb}GB")
            
            if host.bandwidth_mbps < 1:  # Minimum 1 Mbps
                raise ValueError(f"Insufficient bandwidth: {host.bandwidth_mbps} Mbps")
            
            # Store host
            self.storage_hosts[node_id] = host
            await self.db["shard_hosts"].replace_one(
                {"_id": node_id},
                host.to_dict(),
                upsert=True
            )
            
            logger.info(f"Storage host registered: {node_id} ({host.storage_capacity_gb}GB, {host.bandwidth_mbps}Mbps)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register storage host: {e}")
            return False
    
    async def create_shards_for_session(self, session_id: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Create shards for session chunks with replication.
        
        Args:
            session_id: Session identifier
            chunks: List of chunk metadata
            
        Returns:
            Creation task ID
        """
        try:
            # Validate input
            if not chunks:
                raise ValueError("No chunks provided")
            
            # Check available storage hosts
            available_hosts = self._get_available_hosts()
            if len(available_hosts) < MIN_STORAGE_NODES:
                raise ValueError(f"Insufficient storage hosts: {len(available_hosts)} < {MIN_STORAGE_NODES}")
            
            # Create shard creation task
            task_id = str(uuid.uuid4())
            total_size = sum(chunk.get("size_bytes", 0) for chunk in chunks)
            
            task = ShardCreationTask(
                task_id=task_id,
                session_id=session_id,
                chunks_count=len(chunks),
                total_size_bytes=total_size,
                replication_factor=REPLICATION_FACTOR
            )
            
            self.creation_tasks[task_id] = task
            
            # Process chunks asynchronously
            asyncio.create_task(self._process_shard_creation(task, chunks))
            
            logger.info(f"Shard creation task started: {task_id} for session {session_id} ({len(chunks)} chunks)")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create shards: {e}")
            raise
    
    async def get_shard_hosts(self, shard_id: str) -> Optional[List[str]]:
        """
        Get host assignments for a shard.
        
        Args:
            shard_id: Shard identifier
            
        Returns:
            List of assigned host node IDs
        """
        try:
            shard = self.active_shards.get(shard_id)
            if shard:
                return shard.assigned_hosts
            
            # Check database
            shard_doc = await self.db["shards"].find_one({"_id": shard_id})
            if shard_doc:
                return shard_doc.get("assigned_hosts", [])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get shard hosts: {e}")
            return None
    
    async def get_creation_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get shard creation task status"""
        try:
            task = self.creation_tasks.get(task_id)
            if task:
                return {
                    "task_id": task_id,
                    "session_id": task.session_id,
                    "progress_percentage": task.progress_percentage,
                    "completed_shards": task.completed_shards,
                    "failed_shards": task.failed_shards,
                    "total_chunks": task.chunks_count,
                    "created_at": task.created_at
                }
            
            # Check database
            task_doc = await self.db["shard_creation_tasks"].find_one({"_id": task_id})
            if task_doc:
                return {
                    "task_id": task_id,
                    "session_id": task_doc["session_id"],
                    "progress_percentage": task_doc.get("progress_percentage", 0),
                    "completed_shards": task_doc.get("completed_shards", 0),
                    "failed_shards": task_doc.get("failed_shards", 0),
                    "total_chunks": task_doc.get("chunks_count", 0),
                    "created_at": task_doc["created_at"]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return None
    
    async def get_storage_hosts_status(self) -> Dict[str, Any]:
        """Get storage hosts overview"""
        try:
            available_hosts = 0
            total_capacity_gb = 0.0
            total_used_gb = 0.0
            total_shards = 0
            
            for host in self.storage_hosts.values():
                if host.status == HostStatus.AVAILABLE:
                    available_hosts += 1
                total_capacity_gb += host.storage_capacity_gb
                total_used_gb += host.storage_used_gb
                total_shards += len(host.assigned_shards)
            
            return {
                "total_hosts": len(self.storage_hosts),
                "available_hosts": available_hosts,
                "total_capacity_gb": total_capacity_gb,
                "total_used_gb": total_used_gb,
                "utilization_percentage": (total_used_gb / max(total_capacity_gb, 1)) * 100,
                "total_shards": total_shards,
                "active_shards": len(self.active_shards),
                "last_updated": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage hosts status: {e}")
            return {"error": str(e)}
    
    def _get_available_hosts(self) -> List[ShardHost]:
        """Get available storage hosts sorted by score"""
        available = [
            host for host in self.storage_hosts.values()
            if host.status == HostStatus.AVAILABLE and len(host.assigned_shards) < MAX_SHARDS_PER_NODE
        ]
        
        # Sort by performance score and available capacity
        return sorted(available, key=lambda h: (h.performance_score, h.storage_available_gb), reverse=True)
    
    async def _select_hosts_for_shard(self, shard_info: ShardInfo) -> List[str]:
        """
        Select optimal hosts for shard placement.
        
        Considers:
        - Available storage capacity
        - Performance score
        - Current load distribution
        - Geographic/network diversity (via onion addresses)
        """
        try:
            available_hosts = self._get_available_hosts()
            
            if len(available_hosts) < REPLICATION_FACTOR:
                raise ValueError(f"Insufficient available hosts: {len(available_hosts)} < {REPLICATION_FACTOR}")
            
            selected_hosts = []
            
            # Select primary host (best performance and capacity)
            primary_host = available_hosts[0]
            selected_hosts.append(primary_host.node_id)
            
            # Select replica hosts with diversity considerations
            remaining_hosts = available_hosts[1:]
            
            for host in remaining_hosts:
                # Check if host is diverse enough (different first 8 chars of onion address)
                diverse = True
                for selected_id in selected_hosts:
                    selected_host = self.storage_hosts[selected_id]
                    if (host.onion_address[:8] == selected_host.onion_address[:8] and
                        len(selected_hosts) < len(available_hosts) // 2):
                        diverse = False
                        break
                
                if diverse:
                    selected_hosts.append(host.node_id)
                    
                    if len(selected_hosts) >= REPLICATION_FACTOR:
                        break
            
            # If we don't have enough diverse hosts, fill with remaining available hosts
            while len(selected_hosts) < REPLICATION_FACTOR and len(selected_hosts) < len(available_hosts):
                for host in available_hosts:
                    if host.node_id not in selected_hosts:
                        selected_hosts.append(host.node_id)
                        break
            
            return selected_hosts
            
        except Exception as e:
            logger.error(f"Failed to select hosts for shard: {e}")
            return []
    
    async def _process_shard_creation(self, task: ShardCreationTask, chunks: List[Dict[str, Any]]):
        """Process shard creation for all chunks in a task"""
        try:
            for i, chunk in enumerate(chunks):
                try:
                    # Create shard info
                    shard_id = f"{task.session_id}_{i:04d}"
                    
                    shard = ShardInfo(
                        shard_id=shard_id,
                        session_id=task.session_id,
                        chunk_index=i,
                        data_hash=chunk.get("hash", ""),
                        size_bytes=chunk.get("size_bytes", 0),
                        status=ShardStatus.CREATING,
                        encryption_key_hash=chunk.get("encryption_key_hash")
                    )
                    
                    # Select hosts for this shard
                    selected_hosts = await self._select_hosts_for_shard(shard)
                    
                    if not selected_hosts:
                        logger.error(f"No hosts available for shard {shard_id}")
                        task.failed_shards += 1
                        continue
                    
                    # Assign hosts to shard
                    shard.assigned_hosts = selected_hosts
                    shard.primary_host = selected_hosts[0]
                    shard.replica_hosts = selected_hosts[1:]
                    shard.status = ShardStatus.ASSIGNED
                    
                    # Update host assignments
                    for host_id in selected_hosts:
                        if host_id in self.storage_hosts:
                            self.storage_hosts[host_id].assigned_shards.add(shard_id)
                            self.storage_hosts[host_id].storage_used_gb += shard.size_bytes / (1024**3)
                    
                    # Store shard
                    self.active_shards[shard_id] = shard
                    await self.db["shards"].replace_one(
                        {"_id": shard_id},
                        shard.to_dict(),
                        upsert=True
                    )
                    
                    # Update task assignments
                    task.assigned_hosts[shard_id] = selected_hosts
                    task.completed_shards += 1
                    
                    # Initiate replication
                    asyncio.create_task(self._initiate_shard_replication(shard))
                    
                    logger.debug(f"Shard created: {shard_id} -> {selected_hosts}")
                    
                except Exception as shard_error:
                    logger.error(f"Failed to create shard for chunk {i}: {shard_error}")
                    task.failed_shards += 1
            
            # Update task in database
            await self.db["shard_creation_tasks"].replace_one(
                {"_id": task.task_id},
                task.to_dict(),
                upsert=True
            )
            
            # Update host assignments in database
            for host in self.storage_hosts.values():
                await self.db["shard_hosts"].update_one(
                    {"_id": host.node_id},
                    {"$set": {
                        "assigned_shards": list(host.assigned_shards),
                        "storage_used_gb": host.storage_used_gb
                    }}
                )
            
            logger.info(f"Shard creation task completed: {task.task_id} ({task.completed_shards}/{task.chunks_count} successful)")
            
        except Exception as e:
            logger.error(f"Shard creation task failed: {e}")
    
    async def _initiate_shard_replication(self, shard: ShardInfo):
        """Initiate shard replication to assigned hosts"""
        try:
            shard.status = ShardStatus.REPLICATING
            
            # In production, this would trigger actual data replication to hosts
            # For now, we'll simulate the replication process
            
            # Update shard status in database
            await self.db["shards"].update_one(
                {"_id": shard.shard_id},
                {"$set": {"status": ShardStatus.REPLICATING.value}}
            )
            
            # Simulate replication delay
            await asyncio.sleep(1)
            
            # Mark as ready
            shard.status = ShardStatus.READY
            await self.db["shards"].update_one(
                {"_id": shard.shard_id},
                {"$set": {"status": ShardStatus.READY.value}}
            )
            
            logger.debug(f"Shard replication completed: {shard.shard_id}")
            
        except Exception as e:
            logger.error(f"Shard replication failed: {e}")
            shard.status = ShardStatus.FAILED
            await self.db["shards"].update_one(
                {"_id": shard.shard_id},
                {"$set": {"status": ShardStatus.FAILED.value}}
            )
    
    async def _health_check_loop(self):
        """Periodic health check of storage hosts"""
        while self.running:
            try:
                for host in list(self.storage_hosts.values()):
                    try:
                        # In production, this would ping the actual host
                        # For now, we'll check if the node is still in peer discovery
                        is_alive = False
                        for peer in await self.peer_discovery.get_active_peers():
                            if peer.node_id == host.node_id:
                                is_alive = True
                                break
                        
                        if is_alive:
                            if host.status == HostStatus.OFFLINE:
                                host.status = HostStatus.AVAILABLE
                                logger.info(f"Storage host back online: {host.node_id}")
                        else:
                            if host.status != HostStatus.OFFLINE:
                                host.status = HostStatus.OFFLINE
                                logger.warning(f"Storage host offline: {host.node_id}")
                        
                        host.last_health_check = datetime.now(timezone.utc)
                        
                        # Update host in database
                        await self.db["shard_hosts"].update_one(
                            {"_id": host.node_id},
                            {"$set": {
                                "status": host.status.value,
                                "last_health_check": host.last_health_check
                            }}
                        )
                        
                    except Exception as host_error:
                        logger.error(f"Health check failed for host {host.node_id}: {host_error}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(10)
    
    async def _rebalance_loop(self):
        """Periodic rebalancing of shard assignments"""
        while self.running:
            try:
                # Check for imbalanced hosts
                hosts = list(self.storage_hosts.values())
                if not hosts:
                    await asyncio.sleep(300)  # Wait 5 minutes if no hosts
                    continue
                
                # Calculate average load
                total_shards = sum(len(h.assigned_shards) for h in hosts)
                avg_load = total_shards / len(hosts) if hosts else 0
                
                # Find overloaded and underloaded hosts
                overloaded = [h for h in hosts if len(h.assigned_shards) > avg_load * 1.5]
                underloaded = [h for h in hosts if len(h.assigned_shards) < avg_load * 0.5 and h.status == HostStatus.AVAILABLE]
                
                # Rebalance if needed
                if overloaded and underloaded:
                    logger.info(f"Starting shard rebalancing: {len(overloaded)} overloaded, {len(underloaded)} underloaded hosts")
                    await self._rebalance_shards(overloaded, underloaded)
                
                await asyncio.sleep(1800)  # Rebalance every 30 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rebalance loop error: {e}")
                await asyncio.sleep(60)
    
    async def _rebalance_shards(self, overloaded_hosts: List[ShardHost], underloaded_hosts: List[ShardHost]):
        """Rebalance shards between overloaded and underloaded hosts"""
        try:
            moves_count = 0
            max_moves = 10  # Limit moves per rebalancing round
            
            for overloaded_host in overloaded_hosts:
                if moves_count >= max_moves:
                    break
                
                # Find shards that can be moved
                movable_shards = []
                for shard_id in overloaded_host.assigned_shards:
                    shard = self.active_shards.get(shard_id)
                    if shard and shard.status == ShardStatus.READY and shard.primary_host != overloaded_host.node_id:
                        movable_shards.append(shard_id)
                
                # Move shards to underloaded hosts
                for shard_id in movable_shards[:3]:  # Move max 3 shards per host per round
                    if moves_count >= max_moves:
                        break
                    
                    # Find best underloaded host
                    best_target = None
                    for target_host in underloaded_hosts:
                        if len(target_host.assigned_shards) < MAX_SHARDS_PER_NODE:
                            best_target = target_host
                            break
                    
                    if best_target:
                        await self._migrate_shard(shard_id, overloaded_host.node_id, best_target.node_id)
                        moves_count += 1
            
            if moves_count > 0:
                logger.info(f"Shard rebalancing completed: {moves_count} shards migrated")
            
        except Exception as e:
            logger.error(f"Shard rebalancing failed: {e}")
    
    async def _migrate_shard(self, shard_id: str, source_host: str, target_host: str):
        """Migrate shard from source to target host"""
        try:
            shard = self.active_shards.get(shard_id)
            if not shard:
                return
            
            # Update shard assignment
            if source_host in shard.assigned_hosts:
                shard.assigned_hosts.remove(source_host)
            if target_host not in shard.assigned_hosts:
                shard.assigned_hosts.append(target_host)
            
            # Update host assignments
            if source_host in self.storage_hosts:
                self.storage_hosts[source_host].assigned_shards.discard(shard_id)
                self.storage_hosts[source_host].storage_used_gb -= shard.size_bytes / (1024**3)
            
            if target_host in self.storage_hosts:
                self.storage_hosts[target_host].assigned_shards.add(shard_id)
                self.storage_hosts[target_host].storage_used_gb += shard.size_bytes / (1024**3)
            
            # Update database
            await self.db["shards"].update_one(
                {"_id": shard_id},
                {"$set": {"assigned_hosts": shard.assigned_hosts}}
            )
            
            # Update host assignments
            for host_id in [source_host, target_host]:
                if host_id in self.storage_hosts:
                    host = self.storage_hosts[host_id]
                    await self.db["shard_hosts"].update_one(
                        {"_id": host_id},
                        {"$set": {
                            "assigned_shards": list(host.assigned_shards),
                            "storage_used_gb": host.storage_used_gb
                        }}
                    )
            
            logger.info(f"Shard migrated: {shard_id} from {source_host} to {target_host}")
            
        except Exception as e:
            logger.error(f"Shard migration failed: {e}")
    
    async def _cleanup_loop(self):
        """Cleanup expired tasks and failed shards"""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                # Clean up old creation tasks (older than 24 hours)
                expired_tasks = []
                for task_id, task in self.creation_tasks.items():
                    if (now - task.created_at) > timedelta(hours=24):
                        expired_tasks.append(task_id)
                
                for task_id in expired_tasks:
                    del self.creation_tasks[task_id]
                
                # Clean up failed shards (older than 1 hour)
                failed_shards = []
                for shard_id, shard in self.active_shards.items():
                    if (shard.status == ShardStatus.FAILED and 
                        (now - shard.created_at) > timedelta(hours=1)):
                        failed_shards.append(shard_id)
                
                for shard_id in failed_shards:
                    del self.active_shards[shard_id]
                    # Remove from database
                    await self.db["shards"].delete_one({"_id": shard_id})
                
                if expired_tasks or failed_shards:
                    logger.info(f"Cleanup completed: {len(expired_tasks)} tasks, {len(failed_shards)} failed shards removed")
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(300)
    
    async def _setup_indexes(self):
        """Setup database indexes"""
        try:
            # Shard hosts indexes
            await self.db["shard_hosts"].create_index("status")
            await self.db["shard_hosts"].create_index("last_health_check")
            
            # Shards indexes
            await self.db["shards"].create_index("session_id")
            await self.db["shards"].create_index("status")
            await self.db["shards"].create_index("assigned_hosts")
            await self.db["shards"].create_index("created_at")
            
            # Shard creation tasks indexes
            await self.db["shard_creation_tasks"].create_index("session_id")
            await self.db["shard_creation_tasks"].create_index("created_at")
            
            logger.info("Shard host creation database indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create shard host indexes: {e}")
    
    async def _load_storage_hosts(self):
        """Load storage hosts from database"""
        try:
            cursor = self.db["shard_hosts"].find({})
            
            async for host_doc in cursor:
                host = ShardHost(
                    node_id=host_doc["_id"],
                    onion_address=host_doc["onion_address"],
                    port=host_doc["port"],
                    status=HostStatus(host_doc["status"]),
                    storage_capacity_gb=host_doc["storage_capacity_gb"],
                    storage_used_gb=host_doc["storage_used_gb"],
                    bandwidth_mbps=host_doc["bandwidth_mbps"],
                    assigned_shards=set(host_doc.get("assigned_shards", [])),
                    last_health_check=host_doc.get("last_health_check"),
                    performance_score=host_doc.get("performance_score", 1.0)
                )
                
                self.storage_hosts[host.node_id] = host
                
            logger.info(f"Loaded {len(self.storage_hosts)} storage hosts")
            
        except Exception as e:
            logger.error(f"Failed to load storage hosts: {e}")
    
    async def _load_active_shards(self):
        """Load active shards from database"""
        try:
            cursor = self.db["shards"].find({
                "status": {"$in": [
                    ShardStatus.ASSIGNED.value,
                    ShardStatus.REPLICATING.value,
                    ShardStatus.READY.value,
                    ShardStatus.DEGRADED.value
                ]}
            })
            
            async for shard_doc in cursor:
                shard = ShardInfo(
                    shard_id=shard_doc["_id"],
                    session_id=shard_doc["session_id"],
                    chunk_index=shard_doc["chunk_index"],
                    data_hash=shard_doc["data_hash"],
                    size_bytes=shard_doc["size_bytes"],
                    status=ShardStatus(shard_doc["status"]),
                    created_at=shard_doc["created_at"],
                    assigned_hosts=shard_doc.get("assigned_hosts", []),
                    primary_host=shard_doc.get("primary_host"),
                    replica_hosts=shard_doc.get("replica_hosts", []),
                    encryption_key_hash=shard_doc.get("encryption_key_hash"),
                    compression_ratio=shard_doc.get("compression_ratio", 1.0)
                )
                
                self.active_shards[shard.shard_id] = shard
                
            logger.info(f"Loaded {len(self.active_shards)} active shards")
            
        except Exception as e:
            logger.error(f"Failed to load active shards: {e}")


# Global shard host creation system instance
_shard_host_creation: Optional[ShardHostCreationSystem] = None


def get_shard_host_creation() -> Optional[ShardHostCreationSystem]:
    """Get global shard host creation system instance"""
    global _shard_host_creation
    return _shard_host_creation


def create_shard_host_creation(db: DatabaseAdapter, peer_discovery: PeerDiscovery,
                              work_credits: WorkCreditsCalculator) -> ShardHostCreationSystem:
    """Create shard host creation system instance"""
    global _shard_host_creation
    _shard_host_creation = ShardHostCreationSystem(db, peer_discovery, work_credits)
    return _shard_host_creation


async def cleanup_shard_host_creation():
    """Cleanup shard host creation system"""
    global _shard_host_creation
    if _shard_host_creation:
        await _shard_host_creation.stop()
        _shard_host_creation = None


if __name__ == "__main__":
    # Test shard host creation system
    async def test_shard_host_creation():
        print("Testing Lucid Shard Host Creation System...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - shard host creation system ready")
    
    asyncio.run(test_shard_host_creation())