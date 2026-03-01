#!/usr/bin/env python3
"""
LUCID DHT/CRDT Node - SPEC-1B Implementation
Distributed hash table, conflict-free replicated data, peer discovery, gossip protocol
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """DHT node status"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"

class MessageType(Enum):
    """DHT message types"""
    PING = "ping"
    PONG = "pong"
    FIND_NODE = "find_node"
    FIND_VALUE = "find_value"
    STORE = "store"
    GOSSIP = "gossip"

@dataclass
class DHTNode:
    """DHT node information"""
    node_id: str
    address: str
    port: int
    last_seen: float
    status: NodeStatus
    public_key: Optional[str] = None

@dataclass
class DHTEntry:
    """DHT key-value entry"""
    key: str
    value: Any
    timestamp: float
    ttl: int
    replicas: List[str]  # Node IDs storing this entry

@dataclass
class CRDTEntry:
    """CRDT entry for conflict-free replication"""
    key: str
    value: Any
    vector_clock: Dict[str, int]
    timestamp: float
    node_id: str

@dataclass
class GossipMessage:
    """Gossip protocol message"""
    message_id: str
    sender_id: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: float
    ttl: int = 3

class DHTCRDTNode:
    """
    DHT/CRDT node for encrypted metadata overlay per SPEC-1b
    """
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        address: str = "0.0.0.0",
        port: int = 8089,
        bootstrap_nodes: Optional[List[Tuple[str, int]]] = None,
        output_dir: str = "/data/dht"
    ):
        self.node_id = node_id or self._generate_node_id()
        self.address = address
        self.port = port
        self.bootstrap_nodes = bootstrap_nodes or []
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Node state
        self.status = NodeStatus.STOPPED
        self.peers: Dict[str, DHTNode] = {}
        self.dht_entries: Dict[str, DHTEntry] = {}
        self.crdt_entries: Dict[str, CRDTEntry] = {}
        self.gossip_messages: Dict[str, GossipMessage] = {}
        
        # Network components
        self.server: Optional[asyncio.Server] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"DHT/CRDT node initialized: {self.node_id}")
    
    def _generate_node_id(self) -> str:
        """Generate unique node ID"""
        return hashlib.sha256(f"{uuid.uuid4()}:{time.time()}".encode()).hexdigest()[:16]
    
    async def start(self):
        """Start the DHT/CRDT node"""
        if self.status != NodeStatus.STOPPED:
            raise RuntimeError(f"Node is not stopped (status: {self.status})")
        
        self.status = NodeStatus.STARTING
        logger.info(f"Starting DHT/CRDT node {self.node_id}")
        
        try:
            # Start HTTP server
            self.server = await asyncio.start_server(
                self._handle_connection,
                self.address,
                self.port
            )
            
            # Create HTTP session
            self.http_session = aiohttp.ClientSession()
            
            # Bootstrap with known nodes
            await self._bootstrap()
            
            # Start background tasks
            asyncio.create_task(self._gossip_loop())
            asyncio.create_task(self._cleanup_loop())
            
            self.status = NodeStatus.RUNNING
            logger.info(f"DHT/CRDT node {self.node_id} started on {self.address}:{self.port}")
            
        except Exception as e:
            self.status = NodeStatus.STOPPED
            logger.error(f"Failed to start DHT/CRDT node: {e}")
            raise
    
    async def stop(self):
        """Stop the DHT/CRDT node"""
        if self.status == NodeStatus.STOPPED:
            return
        
        self.status = NodeStatus.STOPPING
        logger.info(f"Stopping DHT/CRDT node {self.node_id}")
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
        
        # Save state
        await self._save_node_state()
        
        self.status = NodeStatus.STOPPED
        logger.info(f"DHT/CRDT node {self.node_id} stopped")
    
    async def store_value(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Store value in DHT
        
        Args:
            key: DHT key
            value: Value to store
            ttl: Time to live in seconds
            
        Returns:
            True if stored successfully
        """
        try:
            # Create DHT entry
            entry = DHTEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                replicas=[self.node_id]
            )
            
            # Store locally
            self.dht_entries[key] = entry
            
            # Replicate to peers
            await self._replicate_entry(entry)
            
            logger.debug(f"Stored value for key {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store value for key {key}: {e}")
            return False
    
    async def get_value(self, key: str) -> Optional[Any]:
        """
        Get value from DHT
        
        Args:
            key: DHT key
            
        Returns:
            Value if found, None otherwise
        """
        # Check local storage first
        if key in self.dht_entries:
            entry = self.dht_entries[key]
            if time.time() - entry.timestamp < entry.ttl:
                return entry.value
            else:
                # Entry expired
                del self.dht_entries[key]
        
        # Query peers
        return await self._query_peers_for_key(key)
    
    async def update_crdt_value(self, key: str, value: Any) -> bool:
        """
        Update CRDT value with conflict-free replication
        
        Args:
            key: CRDT key
            value: New value
            
        Returns:
            True if updated successfully
        """
        try:
            # Get current vector clock
            current_entry = self.crdt_entries.get(key)
            vector_clock = {}
            
            if current_entry:
                vector_clock = current_entry.vector_clock.copy()
            
            # Update vector clock for this node
            vector_clock[self.node_id] = vector_clock.get(self.node_id, 0) + 1
            
            # Create CRDT entry
            entry = CRDTEntry(
                key=key,
                value=value,
                vector_clock=vector_clock,
                timestamp=time.time(),
                node_id=self.node_id
            )
            
            # Merge with existing entry if present
            if current_entry:
                entry = self._merge_crdt_entries(current_entry, entry)
            
            # Store locally
            self.crdt_entries[key] = entry
            
            # Gossip to peers
            await self._gossip_crdt_update(entry)
            
            logger.debug(f"Updated CRDT value for key {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update CRDT value for key {key}: {e}")
            return False
    
    async def get_crdt_value(self, key: str) -> Optional[Any]:
        """Get CRDT value"""
        entry = self.crdt_entries.get(key)
        return entry.value if entry else None
    
    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming connections"""
        try:
            # Read message
            data = await reader.read(4096)
            message = json.loads(data.decode())
            
            # Process message
            response = await self._process_message(message)
            
            # Send response
            writer.write(json.dumps(response).encode())
            await writer.drain()
            
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            writer.close()
    
    async def _process_message(self, message: dict) -> dict:
        """Process incoming DHT message"""
        message_type = MessageType(message.get("type"))
        
        if message_type == MessageType.PING:
            return await self._handle_ping(message)
        elif message_type == MessageType.FIND_NODE:
            return await self._handle_find_node(message)
        elif message_type == MessageType.FIND_VALUE:
            return await self._handle_find_value(message)
        elif message_type == MessageType.STORE:
            return await self._handle_store(message)
        elif message_type == MessageType.GOSSIP:
            return await self._handle_gossip(message)
        else:
            return {"error": "Unknown message type"}
    
    async def _handle_ping(self, message: dict) -> dict:
        """Handle ping message"""
        return {
            "type": MessageType.PONG.value,
            "node_id": self.node_id,
            "timestamp": time.time()
        }
    
    async def _handle_find_node(self, message: dict) -> dict:
        """Handle find node message"""
        target_id = message.get("target_id")
        closest_nodes = self._find_closest_nodes(target_id, 8)
        
        return {
            "type": "nodes",
            "nodes": [{"node_id": node.node_id, "address": node.address, "port": node.port} 
                     for node in closest_nodes]
        }
    
    async def _handle_find_value(self, message: dict) -> dict:
        """Handle find value message"""
        key = message.get("key")
        value = await self.get_value(key)
        
        if value is not None:
            return {
                "type": "value",
                "key": key,
                "value": value
            }
        else:
            # Return closest nodes for further querying
            closest_nodes = self._find_closest_nodes(key, 8)
            return {
                "type": "nodes",
                "nodes": [{"node_id": node.node_id, "address": node.address, "port": node.port} 
                         for node in closest_nodes]
            }
    
    async def _handle_store(self, message: dict) -> dict:
        """Handle store message"""
        key = message.get("key")
        value = message.get("value")
        ttl = message.get("ttl", 3600)
        
        success = await self.store_value(key, value, ttl)
        return {"success": success}
    
    async def _handle_gossip(self, message: dict) -> dict:
        """Handle gossip message"""
        message_id = message.get("message_id")
        sender_id = message.get("sender_id")
        payload = message.get("payload", {})
        
        # Check if we've seen this message
        if message_id in self.gossip_messages:
            return {"ack": True}
        
        # Store message
        gossip_msg = GossipMessage(
            message_id=message_id,
            sender_id=sender_id,
            message_type=MessageType.GOSSIP,
            payload=payload,
            timestamp=time.time()
        )
        
        self.gossip_messages[message_id] = gossip_msg
        
        # Process gossip payload
        await self._process_gossip_payload(payload)
        
        # Forward to other peers
        await self._forward_gossip(gossip_msg)
        
        return {"ack": True}
    
    async def _bootstrap(self):
        """Bootstrap with known nodes"""
        for address, port in self.bootstrap_nodes:
            try:
                await self._ping_node(address, port)
            except Exception as e:
                logger.debug(f"Bootstrap ping failed for {address}:{port}: {e}")
    
    async def _ping_node(self, address: str, port: int) -> bool:
        """Ping a remote node"""
        try:
            if not self.http_session:
                return False
            
            url = f"http://{address}:{port}/ping"
            async with self.http_session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    node_id = data.get("node_id")
                    
                    if node_id:
                        # Add to peers
                        peer = DHTNode(
                            node_id=node_id,
                            address=address,
                            port=port,
                            last_seen=time.time(),
                            status=NodeStatus.RUNNING
                        )
                        self.peers[node_id] = peer
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Ping failed for {address}:{port}: {e}")
            return False
    
    async def _query_peers_for_key(self, key: str) -> Optional[Any]:
        """Query peers for a key"""
        if not self.http_session:
            return None
        
        for peer in self.peers.values():
            try:
                url = f"http://{peer.address}:{peer.port}/find_value"
                data = {"key": key}
                
                async with self.http_session.post(url, json=data, timeout=5) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("type") == "value":
                            return result.get("value")
            
            except Exception as e:
                logger.debug(f"Query failed for peer {peer.node_id}: {e}")
        
        return None
    
    async def _replicate_entry(self, entry: DHTEntry):
        """Replicate entry to peers"""
        if not self.http_session:
            return
        
        for peer in self.peers.values():
            try:
                url = f"http://{peer.address}:{peer.port}/store"
                data = {
                    "key": entry.key,
                    "value": entry.value,
                    "ttl": entry.ttl
                }
                
                async with self.http_session.post(url, json=data, timeout=5) as response:
                    if response.status == 200:
                        entry.replicas.append(peer.node_id)
            
            except Exception as e:
                logger.debug(f"Replication failed for peer {peer.node_id}: {e}")
    
    async def _gossip_crdt_update(self, entry: CRDTEntry):
        """Gossip CRDT update to peers"""
        message_id = f"crdt_{entry.key}_{int(time.time())}"
        
        gossip_msg = GossipMessage(
            message_id=message_id,
            sender_id=self.node_id,
            message_type=MessageType.GOSSIP,
            payload={
                "type": "crdt_update",
                "key": entry.key,
                "value": entry.value,
                "vector_clock": entry.vector_clock,
                "timestamp": entry.timestamp,
                "node_id": entry.node_id
            },
            timestamp=time.time()
        )
        
        await self._forward_gossip(gossip_msg)
    
    async def _forward_gossip(self, message: GossipMessage):
        """Forward gossip message to peers"""
        if not self.http_session or message.ttl <= 0:
            return
        
        # Decrease TTL
        message.ttl -= 1
        
        for peer in self.peers.values():
            if peer.node_id != message.sender_id:
                try:
                    url = f"http://{peer.address}:{peer.port}/gossip"
                    data = asdict(message)
                    data['type'] = message.message_type.value
                    
                    async with self.http_session.post(url, json=data, timeout=5) as response:
                        if response.status == 200:
                            logger.debug(f"Forwarded gossip to {peer.node_id}")
            
                except Exception as e:
                    logger.debug(f"Gossip forwarding failed for {peer.node_id}: {e}")
    
    async def _process_gossip_payload(self, payload: dict):
        """Process gossip payload"""
        if payload.get("type") == "crdt_update":
            key = payload.get("key")
            value = payload.get("value")
            vector_clock = payload.get("vector_clock", {})
            timestamp = payload.get("timestamp", time.time())
            node_id = payload.get("node_id")
            
            if key and value is not None:
                # Create CRDT entry from gossip
                entry = CRDTEntry(
                    key=key,
                    value=value,
                    vector_clock=vector_clock,
                    timestamp=timestamp,
                    node_id=node_id
                )
                
                # Merge with existing entry
                if key in self.crdt_entries:
                    entry = self._merge_crdt_entries(self.crdt_entries[key], entry)
                
                self.crdt_entries[key] = entry
    
    def _merge_crdt_entries(self, entry1: CRDTEntry, entry2: CRDTEntry) -> CRDTEntry:
        """Merge two CRDT entries using vector clocks"""
        # Compare vector clocks
        merged_clock = {}
        for node_id in set(entry1.vector_clock.keys()) | set(entry2.vector_clock.keys()):
            merged_clock[node_id] = max(
                entry1.vector_clock.get(node_id, 0),
                entry2.vector_clock.get(node_id, 0)
            )
        
        # Use the entry with the higher timestamp
        if entry1.timestamp >= entry2.timestamp:
            return CRDTEntry(
                key=entry1.key,
                value=entry1.value,
                vector_clock=merged_clock,
                timestamp=entry1.timestamp,
                node_id=entry1.node_id
            )
        else:
            return CRDTEntry(
                key=entry2.key,
                value=entry2.value,
                vector_clock=merged_clock,
                timestamp=entry2.timestamp,
                node_id=entry2.node_id
            )
    
    def _find_closest_nodes(self, target_id: str, count: int) -> List[DHTNode]:
        """Find closest nodes to target ID"""
        # Simple distance calculation (XOR)
        def distance(node_id: str) -> int:
            return int(node_id, 16) ^ int(target_id, 16)
        
        sorted_peers = sorted(self.peers.values(), key=lambda n: distance(n.node_id))
        return sorted_peers[:count]
    
    async def _gossip_loop(self):
        """Background gossip loop"""
        while self.status == NodeStatus.RUNNING:
            try:
                # Send periodic gossip messages
                await self._send_periodic_gossip()
                await asyncio.sleep(30)  # Gossip every 30 seconds
            except Exception as e:
                logger.error(f"Gossip loop error: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.status == NodeStatus.RUNNING:
            try:
                # Clean up expired entries
                current_time = time.time()
                
                # Clean DHT entries
                expired_keys = [
                    key for key, entry in self.dht_entries.items()
                    if current_time - entry.timestamp > entry.ttl
                ]
                for key in expired_keys:
                    del self.dht_entries[key]
                
                # Clean gossip messages
                expired_messages = [
                    msg_id for msg_id, msg in self.gossip_messages.items()
                    if current_time - msg.timestamp > 300  # 5 minutes
                ]
                for msg_id in expired_messages:
                    del self.gossip_messages[msg_id]
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(10)
    
    async def _send_periodic_gossip(self):
        """Send periodic gossip messages"""
        # Send node status updates
        status_message = GossipMessage(
            message_id=f"status_{self.node_id}_{int(time.time())}",
            sender_id=self.node_id,
            message_type=MessageType.GOSSIP,
            payload={
                "type": "node_status",
                "node_id": self.node_id,
                "status": self.status.value,
                "peer_count": len(self.peers),
                "timestamp": time.time()
            },
            timestamp=time.time()
        )
        
        await self._forward_gossip(status_message)
    
    async def _save_node_state(self):
        """Save node state to disk"""
        state_file = self.output_dir / f"{self.node_id}_state.json"
        
        state_data = {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "status": self.status.value,
            "peers": {node_id: asdict(peer) for node_id, peer in self.peers.items()},
            "dht_entries": {key: asdict(entry) for key, entry in self.dht_entries.items()},
            "crdt_entries": {key: asdict(entry) for key, entry in self.crdt_entries.items()}
        }
        
        async with aiofiles.open(state_file, 'w') as f:
            await f.write(json.dumps(state_data, indent=2))
    
    def get_node_stats(self) -> dict:
        """Get node statistics"""
        return {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "status": self.status.value,
            "peer_count": len(self.peers),
            "dht_entries": len(self.dht_entries),
            "crdt_entries": len(self.crdt_entries),
            "gossip_messages": len(self.gossip_messages)
        }

# CLI interface for testing
async def main():
    """Test the DHT/CRDT node"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LUCID DHT/CRDT Node")
    parser.add_argument("--node-id", help="Node ID")
    parser.add_argument("--address", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8089, help="Bind port")
    parser.add_argument("--bootstrap", help="Bootstrap nodes (format: host:port,host:port)")
    parser.add_argument("--output-dir", default="/data/dht", help="Output directory")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Parse bootstrap nodes
    bootstrap_nodes = []
    if args.bootstrap:
        for node in args.bootstrap.split(','):
            host, port = node.split(':')
            bootstrap_nodes.append((host, int(port)))
    
    # Create DHT/CRDT node
    node = DHTCRDTNode(
        node_id=args.node_id,
        address=args.address,
        port=args.port,
        bootstrap_nodes=bootstrap_nodes,
        output_dir=args.output_dir
    )
    
    try:
        # Start node
        await node.start()
        
        # Test operations
        await node.store_value("test_key", "test_value")
        value = await node.get_value("test_key")
        print(f"Retrieved value: {value}")
        
        await node.update_crdt_value("crdt_key", {"data": "test"})
        crdt_value = await node.get_crdt_value("crdt_key")
        print(f"CRDT value: {crdt_value}")
        
        # Keep running
        print(f"DHT/CRDT node running on {args.address}:{args.port}")
        print("Press Ctrl+C to stop")
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Stopping node...")
    finally:
        await node.stop()

if __name__ == "__main__":
    asyncio.run(main())
