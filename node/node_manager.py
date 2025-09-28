# Path: node/node_manager.py

from __future__ import annotations
import asyncio
import logging
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from node.peer_discovery import PeerDiscovery, PeerInfo
from node.work_credits import WorkCreditsCalculator
import uuid
import json

logger = logging.getLogger(__name__)


@dataclass  
class NodeConfig:
    """Configuration for a Lucid node."""
    node_id: str
    role: str  # server, worker, admin, dev
    onion_address: str
    port: int
    pool_id: Optional[str] = None
    bootstrap_peers: List[str] = None
    work_credits_enabled: bool = True
    relay_enabled: bool = True
    storage_enabled: bool = True
    
    def __post_init__(self):
        if self.bootstrap_peers is None:
            self.bootstrap_peers = []


class NodeManager:
    """
    Main node management system for Lucid RDP.
    Coordinates peer discovery, work credits, and node services.
    """
    
    def __init__(self, config: NodeConfig, db: AsyncIOMotorDatabase):
        self.config = config
        self.db = db
        self.running = False
        
        # Initialize components
        self.peer_discovery = PeerDiscovery(
            db=db,
            node_id=config.node_id,
            onion_address=config.onion_address,
            port=config.port,
            bootstrap_peers=config.bootstrap_peers
        )
        
        self.work_credits = WorkCreditsCalculator(db=db)
        
        # Service tasks
        self._service_tasks: List[asyncio.Task] = []
        self._last_beacon_time: Optional[datetime] = None
        
        # Node metrics
        self.metrics = {
            "uptime_start": datetime.now(timezone.utc),
            "sessions_processed": 0,
            "bytes_relayed": 0,
            "storage_challenges_passed": 0,
            "validation_signatures": 0
        }
        
    async def start(self) -> None:
        """Start the node manager and all services."""
        if self.running:
            return
            
        logger.info(f"Starting Lucid node {self.config.node_id} ({self.config.role})")
        self.running = True
        
        try:
            # Ensure database indexes
            await self._ensure_indexes()
            
            # Start peer discovery
            await self.peer_discovery.start()
            
            # Register this node in the network
            await self._register_node()
            
            # Start service tasks
            if self.config.work_credits_enabled:
                task = asyncio.create_task(self._uptime_beacon_loop())
                self._service_tasks.append(task)
                
            task = asyncio.create_task(self._metrics_update_loop())
            self._service_tasks.append(task)
            
            if self.config.relay_enabled:
                task = asyncio.create_task(self._relay_service())
                self._service_tasks.append(task)
                
            logger.info(f"Node {self.config.node_id} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start node: {e}")
            await self.stop()
            raise
            
    async def stop(self) -> None:
        """Stop the node manager and all services."""
        if not self.running:
            return
            
        logger.info(f"Stopping node {self.config.node_id}")
        self.running = False
        
        # Cancel service tasks
        for task in self._service_tasks:
            if not task.done():
                task.cancel()
                
        # Wait for tasks to finish
        if self._service_tasks:
            await asyncio.gather(*self._service_tasks, return_exceptions=True)
            
        # Stop peer discovery
        await self.peer_discovery.stop()
        
        logger.info("Node stopped successfully")
        
    async def get_node_status(self) -> Dict:
        """Get current node status and metrics."""
        now = datetime.now(timezone.utc)
        uptime_seconds = (now - self.metrics["uptime_start"]).total_seconds()
        
        # Get peer information
        active_peers = await self.peer_discovery.get_active_peers()
        known_peers = len(self.peer_discovery.known_peers)
        
        # Get work credits ranking
        rank = await self.work_credits.get_entity_rank(
            self.config.pool_id or self.config.node_id
        )
        
        return {
            "node_id": self.config.node_id,
            "role": self.config.role,
            "pool_id": self.config.pool_id,
            "running": self.running,
            "uptime_seconds": uptime_seconds,
            "last_beacon": self._last_beacon_time.isoformat() if self._last_beacon_time else None,
            "peers": {
                "known": known_peers,
                "active": len(active_peers)
            },
            "metrics": self.metrics.copy(),
            "work_credits_rank": rank,
            "timestamp": now.isoformat()
        }
        
    async def process_session(self, session_id: str, data_size: int) -> None:
        """Process a session and update metrics."""
        self.metrics["sessions_processed"] += 1
        
        # Record storage proof if enabled
        if self.config.storage_enabled:
            self.metrics["storage_challenges_passed"] += 1
            # In production, this would involve actual storage challenges
            
        logger.debug(f"Processed session {session_id}, size: {data_size} bytes")
        
    async def relay_data(self, data_size: int) -> None:
        """Record data relaying activity."""
        self.metrics["bytes_relayed"] += data_size
        
        # Submit work proof for relay bandwidth
        if self.config.work_credits_enabled:
            await self.work_credits.record_relay_bandwidth(
                self.config.node_id,
                data_size,
                self.config.pool_id
            )
            
    async def validate_transaction(self, tx_hash: str) -> bool:
        """Validate a transaction and record validation signature."""
        # Simplified validation - in production would verify actual transaction
        is_valid = True  # Placeholder
        
        if is_valid:
            self.metrics["validation_signatures"] += 1
            
        return is_valid
        
    async def get_network_topology(self) -> Dict:
        """Get current network topology information."""
        active_peers = await self.peer_discovery.get_active_peers()
        
        topology = {
            "total_peers": len(active_peers),
            "peers_by_role": {},
            "top_performers": []
        }
        
        # Group peers by role
        for peer in active_peers:
            role = peer.role
            if role not in topology["peers_by_role"]:
                topology["peers_by_role"][role] = 0
            topology["peers_by_role"][role] += 1
            
        # Get top performing entities
        top_entities = await self.work_credits.get_top_entities(limit=10)
        topology["top_performers"] = [
            {
                "entity_id": entity.entity_id,
                "credits": entity.credits,
                "rank": entity.rank,
                "live_score": entity.live_score
            }
            for entity in top_entities
        ]
        
        return topology
        
    async def join_pool(self, pool_id: str) -> bool:
        """Join a node pool for shared work credits."""
        try:
            # Update configuration
            self.config.pool_id = pool_id
            
            # Update node registration
            await self._register_node()
            
            logger.info(f"Node {self.config.node_id} joined pool {pool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to join pool {pool_id}: {e}")
            return False
            
    async def leave_pool(self) -> bool:
        """Leave current node pool."""
        if not self.config.pool_id:
            return True
            
        try:
            pool_id = self.config.pool_id
            self.config.pool_id = None
            
            # Update node registration
            await self._register_node()
            
            logger.info(f"Node {self.config.node_id} left pool {pool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to leave pool: {e}")
            return False
            
    async def _register_node(self) -> None:
        """Register this node in the peer discovery system."""
        try:
            peer_info = PeerInfo(
                node_id=self.config.node_id,
                onion_address=self.config.onion_address,
                port=self.config.port,
                last_seen=datetime.now(timezone.utc),
                role=self.config.role
            )
            
            # Add capabilities based on configuration
            capabilities = set()
            if self.config.relay_enabled:
                capabilities.add("relay")
            if self.config.storage_enabled:
                capabilities.add("storage")
            if self.config.work_credits_enabled:
                capabilities.add("poot")  # Proof of Operational Tasks
                
            peer_info.capabilities = capabilities
            
            await self.peer_discovery.add_peer(peer_info)
            
        except Exception as e:
            logger.error(f"Failed to register node: {e}")
            
    async def _uptime_beacon_loop(self) -> None:
        """Periodically send uptime beacons."""
        while self.running:
            try:
                await self.work_credits.record_uptime_beacon(
                    self.config.node_id,
                    self.config.pool_id
                )
                self._last_beacon_time = datetime.now(timezone.utc)
                
                # Wait for next slot (120 seconds)
                await asyncio.sleep(120)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in uptime beacon loop: {e}")
                await asyncio.sleep(60)
                
    async def _metrics_update_loop(self) -> None:
        """Periodically update node metrics in peer discovery."""
        while self.running:
            try:
                # Calculate uptime percentage
                now = datetime.now(timezone.utc)
                uptime_seconds = (now - self.metrics["uptime_start"]).total_seconds()
                uptime_percentage = min(100.0, (uptime_seconds / 86400) * 100)  # Last 24h
                
                # Get current work credits
                entity_id = self.config.pool_id or self.config.node_id
                work_credits = await self.work_credits.calculate_work_credits(entity_id)
                
                # Update peer metrics
                await self.peer_discovery.update_peer_metrics(
                    self.config.node_id,
                    work_credits,
                    uptime_percentage
                )
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics update loop: {e}")
                await asyncio.sleep(60)
                
    async def _relay_service(self) -> None:
        """Relay service for network bandwidth contribution."""
        # Simplified relay service - in production would implement actual relay
        while self.running:
            try:
                # Simulate relay activity
                simulated_bytes = 1024 * 1024  # 1MB
                await self.relay_data(simulated_bytes)
                
                await asyncio.sleep(60)  # Relay activity every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in relay service: {e}")
                await asyncio.sleep(30)
                
    async def _ensure_indexes(self) -> None:
        """Ensure all required database indexes."""
        try:
            await self.peer_discovery.ensure_indexes()
            await self.work_credits.ensure_indexes()
        except Exception as e:
            logger.warning(f"Failed to ensure indexes: {e}")


def create_node_config(
    role: str = "worker",
    onion_address: Optional[str] = None,
    port: int = 5050,
    bootstrap_peers: Optional[List[str]] = None
) -> NodeConfig:
    """Create a node configuration with defaults."""
    node_id = str(uuid.uuid4())
    
    # Generate default onion address (would be actual .onion in production)
    if onion_address is None:
        onion_address = f"{node_id[:16]}.onion"
        
    return NodeConfig(
        node_id=node_id,
        role=role,
        onion_address=onion_address,
        port=port,
        bootstrap_peers=bootstrap_peers or []
    )