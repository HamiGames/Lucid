# Path: node/peer_discovery.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json

# Optional import for HTTP client functionality
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False
    # logger.warning("aiohttp not available - HTTP functionality will be limited")

# Use database adapter to handle motor/pymongo compatibility
from .database_adapter import DatabaseAdapter, get_database_adapter

logger = logging.getLogger(__name__)


@dataclass
class PeerInfo:
    """Information about a peer node."""
    node_id: str
    onion_address: str
    port: int
    last_seen: datetime
    work_credits: float = 0.0
    uptime_percentage: float = 0.0
    role: str = "worker"  # worker, admin, server, dev
    capabilities: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "onion_address": self.onion_address,
            "port": self.port,
            "last_seen": self.last_seen.isoformat(),
            "work_credits": self.work_credits,
            "uptime_percentage": self.uptime_percentage,
            "role": self.role,
            "capabilities": list(self.capabilities)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> PeerInfo:
        return cls(
            node_id=data["node_id"],
            onion_address=data["onion_address"],
            port=data["port"],
            last_seen=datetime.fromisoformat(data["last_seen"]),
            work_credits=data.get("work_credits", 0.0),
            uptime_percentage=data.get("uptime_percentage", 0.0),
            role=data.get("role", "worker"),
            capabilities=set(data.get("capabilities", []))
        )


class PeerDiscovery:
    """
    Peer discovery service for Lucid RDP network.
    Manages peer connections via Tor .onion addresses and maintains network topology.
    """
    
    def __init__(
        self,
        db: DatabaseAdapter,
        node_id: str,
        onion_address: str,
        port: int = 5050,
        bootstrap_peers: Optional[List[str]] = None
    ):
        self.db = db
        self.node_id = node_id
        self.onion_address = onion_address
        self.port = port
        self.bootstrap_peers = bootstrap_peers or []
        self.known_peers: Dict[str, PeerInfo] = {}
        self.active_connections: Set[str] = set()
        self._discovery_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self) -> None:
        """Start peer discovery service."""
        if self._running:
            return
            
        logger.info(f"Starting peer discovery for node {self.node_id}")
        self._running = True
        
        # Load known peers from DB
        await self._load_peers_from_db()
        
        # Start discovery loop
        self._discovery_task = asyncio.create_task(self._discovery_loop())
        
    async def stop(self) -> None:
        """Stop peer discovery service."""
        if not self._running:
            return
            
        logger.info("Stopping peer discovery")
        self._running = False
        
        if self._discovery_task and not self._discovery_task.done():
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass
                
    async def add_peer(self, peer_info: PeerInfo) -> None:
        """Add a new peer to the network."""
        self.known_peers[peer_info.node_id] = peer_info
        await self._save_peer_to_db(peer_info)
        logger.info(f"Added peer: {peer_info.node_id}@{peer_info.onion_address}")
        
    async def remove_peer(self, node_id: str) -> None:
        """Remove a peer from the network."""
        if node_id in self.known_peers:
            del self.known_peers[node_id]
            await self.db["peers"].delete_one({"node_id": node_id})
            self.active_connections.discard(node_id)
            logger.info(f"Removed peer: {node_id}")
            
    async def get_active_peers(self) -> List[PeerInfo]:
        """Get list of currently active peers."""
        active_peers = []
        for peer_id in self.active_connections:
            if peer_id in self.known_peers:
                active_peers.append(self.known_peers[peer_id])
        return active_peers
        
    async def get_peers_by_role(self, role: str) -> List[PeerInfo]:
        """Get peers with specific role."""
        return [peer for peer in self.known_peers.values() if peer.role == role]
        
    async def update_peer_metrics(self, node_id: str, work_credits: float, uptime: float) -> None:
        """Update peer performance metrics."""
        if node_id in self.known_peers:
            peer = self.known_peers[node_id]
            peer.work_credits = work_credits
            peer.uptime_percentage = uptime
            peer.last_seen = datetime.now(timezone.utc)
            await self._save_peer_to_db(peer)
            
    async def ping_peer(self, peer_info: PeerInfo) -> bool:
        """Ping a peer to check if it's alive."""
        if not AIOHTTP_AVAILABLE:
            logger.debug(f"Cannot ping peer {peer_info.node_id} - aiohttp not available")
            return False
            
        try:
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Use Tor proxy for .onion addresses
                proxy_url = "socks5://127.0.0.1:9050"  # Standard Tor SOCKS proxy
                url = f"http://{peer_info.onion_address}:{peer_info.port}/health"
                
                async with session.get(url, proxy=proxy_url) as response:
                    if response.status == 200:
                        peer_info.last_seen = datetime.now(timezone.utc)
                        self.active_connections.add(peer_info.node_id)
                        await self._save_peer_to_db(peer_info)
                        return True
                        
        except Exception as e:
            logger.debug(f"Failed to ping peer {peer_info.node_id}: {e}")
            self.active_connections.discard(peer_info.node_id)
            
        return False
        
    async def discover_peers_from_bootstrap(self) -> None:
        """Discover peers from bootstrap nodes."""
        for bootstrap_addr in self.bootstrap_peers:
            try:
                # Parse bootstrap address (format: node_id@onion_address:port)
                if "@" in bootstrap_addr and ":" in bootstrap_addr:
                    node_part, addr_part = bootstrap_addr.split("@")
                    onion_addr, port_str = addr_part.split(":")
                    
                    peer_info = PeerInfo(
                        node_id=node_part,
                        onion_address=onion_addr,
                        port=int(port_str),
                        last_seen=datetime.now(timezone.utc),
                        role="server"  # Bootstrap nodes are typically servers
                    )
                    
                    if await self.ping_peer(peer_info):
                        await self.add_peer(peer_info)
                        
            except Exception as e:
                logger.warning(f"Failed to process bootstrap peer {bootstrap_addr}: {e}")
                
    async def request_peer_list(self, peer_info: PeerInfo) -> List[PeerInfo]:
        """Request peer list from another node."""
        if not AIOHTTP_AVAILABLE:
            logger.debug(f"Cannot request peer list from {peer_info.node_id} - aiohttp not available")
            return []
            
        try:
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=15)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                proxy_url = "socks5://127.0.0.1:9050"
                url = f"http://{peer_info.onion_address}:{peer_info.port}/api/peers"
                
                async with session.get(url, proxy=proxy_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        peers = []
                        for peer_data in data.get("peers", []):
                            try:
                                peer = PeerInfo.from_dict(peer_data)
                                peers.append(peer)
                            except Exception as e:
                                logger.warning(f"Invalid peer data: {e}")
                        return peers
                        
        except Exception as e:
            logger.debug(f"Failed to get peer list from {peer_info.node_id}: {e}")
            
        return []
        
    async def _discovery_loop(self) -> None:
        """Main discovery loop."""
        while self._running:
            try:
                # Discover from bootstrap nodes
                if not self.known_peers:
                    await self.discover_peers_from_bootstrap()
                    
                # Ping known peers and discover new ones
                tasks = []
                for peer in list(self.known_peers.values()):
                    tasks.append(self._process_peer(peer))
                    
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                # Clean up stale peers (not seen in 24 hours)
                await self._cleanup_stale_peers()
                
                await asyncio.sleep(60)  # Discovery interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
                await asyncio.sleep(10)
                
    async def _process_peer(self, peer: PeerInfo) -> None:
        """Process a single peer - ping and discover new peers."""
        try:
            # Ping the peer
            is_alive = await self.ping_peer(peer)
            
            if is_alive:
                # Request peer list from active peer
                discovered_peers = await self.request_peer_list(peer)
                for new_peer in discovered_peers:
                    if new_peer.node_id not in self.known_peers and new_peer.node_id != self.node_id:
                        await self.add_peer(new_peer)
                        
        except Exception as e:
            logger.debug(f"Error processing peer {peer.node_id}: {e}")
            
    async def _cleanup_stale_peers(self) -> None:
        """Remove peers that haven't been seen for 24 hours."""
        cutoff = datetime.now(timezone.utc).timestamp() - 86400  # 24 hours
        stale_peers = []
        
        for node_id, peer in self.known_peers.items():
            if peer.last_seen.timestamp() < cutoff:
                stale_peers.append(node_id)
                
        for node_id in stale_peers:
            await self.remove_peer(node_id)
            
    async def _load_peers_from_db(self) -> None:
        """Load known peers from database."""
        try:
            cursor = self.db["peers"].find({})
            async for doc in cursor:
                try:
                    peer = PeerInfo.from_dict(doc)
                    self.known_peers[peer.node_id] = peer
                except Exception as e:
                    logger.warning(f"Failed to load peer from DB: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to load peers from database: {e}")
            
    async def _save_peer_to_db(self, peer: PeerInfo) -> None:
        """Save peer information to database."""
        try:
            await self.db["peers"].replace_one(
                {"node_id": peer.node_id},
                peer.to_dict(),
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save peer to database: {e}")
            
    async def ensure_indexes(self) -> None:
        """Ensure database indexes for peers collection."""
        try:
            await self.db["peers"].create_index("node_id", unique=True)
            await self.db["peers"].create_index("role")
            await self.db["peers"].create_index("last_seen")
        except Exception as e:
            logger.warning(f"Failed to create peer indexes: {e}")