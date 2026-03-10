#!/usr/bin/env python3
"""
Lucid RDP DHT Node
Distributed Hash Table with CRDT support for peer-to-peer networking
"""

import asyncio
import logging
import time
import hashlib
import json
from typing import Optional, Dict, Any, List, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog
from datetime import datetime, timedelta
import uuid

logger = structlog.get_logger(__name__)

try:
    import kademlia
    from kademlia.network import Server
    from kademlia.utils import digest
    KADEMLIA_AVAILABLE = True
    logger.info("Kademlia DHT library loaded successfully")
except ImportError:
    logger.warning("Kademlia not available, using simplified DHT implementation")
    KADEMLIA_AVAILABLE = False

try:
    import y_py as Y
    YJS_AVAILABLE = True
    logger.info("Yjs CRDT library loaded successfully")
except ImportError:
    logger.warning("Yjs not available, using simplified CRDT implementation")
    YJS_AVAILABLE = False


class NodeStatus(Enum):
    """DHT node status"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class DataType(Enum):
    """Data types supported by DHT"""
    KEY_VALUE = "key_value"
    CRDT_DOCUMENT = "crdt_document"
    SESSION_DATA = "session_data"
    BLOCKCHAIN_DATA = "blockchain_data"


@dataclass
class DHTNode:
    """DHT node information"""
    node_id: str
    address: str
    port: int
    last_seen: datetime
    status: NodeStatus = NodeStatus.RUNNING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DHTData:
    """Data stored in DHT"""
    key: str
    value: Any
    data_type: DataType
    created_at: datetime
    expires_at: Optional[datetime] = None
    replicas: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CRDTDocument:
    """CRDT document for collaborative editing"""
    document_id: str
    content: Dict[str, Any]
    version: int
    last_modified: datetime
    contributors: Set[str] = field(default_factory=set)


class SimpleDHT:
    """Simplified DHT implementation"""
    
    def __init__(self, node_id: str, port: int = 8468):
        self.node_id = node_id
        self.port = port
        self.status = NodeStatus.STOPPED
        self.peers: Dict[str, DHTNode] = {}
        self.data: Dict[str, DHTData] = {}
        self.replication_factor = 3
        
        # Statistics
        self.stats = {
            'peers_count': 0,
            'data_items': 0,
            'operations_performed': 0,
            'replication_events': 0,
            'errors': 0
        }
    
    async def start(self):
        """Start the DHT node"""
        try:
            self.status = NodeStatus.STARTING
            logger.info("Starting DHT node", node_id=self.node_id, port=self.port)
            
            # Start peer discovery
            asyncio.create_task(self._peer_discovery_loop())
            
            # Start data replication
            asyncio.create_task(self._replication_loop())
            
            # Start cleanup
            asyncio.create_task(self._cleanup_loop())
            
            self.status = NodeStatus.RUNNING
            logger.info("DHT node started successfully")
            
        except Exception as e:
            self.status = NodeStatus.ERROR
            logger.error("Failed to start DHT node", error=str(e))
            raise
    
    async def stop(self):
        """Stop the DHT node"""
        try:
            self.status = NodeStatus.STOPPING
            logger.info("Stopping DHT node")
            
            # Notify peers
            await self._notify_peers_disconnect()
            
            self.status = NodeStatus.STOPPED
            logger.info("DHT node stopped")
            
        except Exception as e:
            logger.error("Failed to stop DHT node", error=str(e))
    
    async def store(self, key: str, value: Any, data_type: DataType = DataType.KEY_VALUE, 
                   expires_in: Optional[int] = None) -> bool:
        """Store data in DHT"""
        try:
            # Create data object
            expires_at = None
            if expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            data_item = DHTData(
                key=key,
                value=value,
                data_type=data_type,
                created_at=datetime.utcnow(),
                expires_at=expires_at
            )
            
            # Store locally
            self.data[key] = data_item
            
            # Replicate to peers
            await self._replicate_data(data_item)
            
            self.stats['data_items'] = len(self.data)
            self.stats['operations_performed'] += 1
            
            logger.debug("Data stored", key=key, data_type=data_type.value)
            return True
            
        except Exception as e:
            logger.error("Failed to store data", key=key, error=str(e))
            self.stats['errors'] += 1
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get data from DHT"""
        try:
            # Check local storage
            if key in self.data:
                data_item = self.data[key]
                
                # Check expiration
                if data_item.expires_at and datetime.utcnow() > data_item.expires_at:
                    del self.data[key]
                    return None
                
                self.stats['operations_performed'] += 1
                return data_item.value
            
            # Query peers
            value = await self._query_peers(key)
            if value:
                # Cache locally
                await self.store(key, value)
                return value
            
            return None
            
        except Exception as e:
            logger.error("Failed to get data", key=key, error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete data from DHT"""
        try:
            # Delete locally
            if key in self.data:
                del self.data[key]
            
            # Notify peers to delete
            await self._notify_peers_delete(key)
            
            self.stats['data_items'] = len(self.data)
            self.stats['operations_performed'] += 1
            
            logger.debug("Data deleted", key=key)
            return True
            
        except Exception as e:
            logger.error("Failed to delete data", key=key, error=str(e))
            self.stats['errors'] += 1
            return False
    
    async def _peer_discovery_loop(self):
        """Discover and maintain peer connections"""
        while self.status == NodeStatus.RUNNING:
            try:
                # Discover new peers (simplified)
                await self._discover_peers()
                
                # Update peer status
                await self._update_peer_status()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error("Peer discovery error", error=str(e))
                await asyncio.sleep(10)
    
    async def _discover_peers(self):
        """Discover new peers"""
        # In a real implementation, this would use peer discovery protocols
        # like mDNS, DHT bootstrapping, or manual peer lists
        pass
    
    async def _update_peer_status(self):
        """Update peer status and remove dead peers"""
        current_time = datetime.utcnow()
        dead_peers = []
        
        for peer_id, peer in self.peers.items():
            # Check if peer is still alive
            if current_time - peer.last_seen > timedelta(minutes=5):
                dead_peers.append(peer_id)
        
        # Remove dead peers
        for peer_id in dead_peers:
            del self.peers[peer_id]
        
        self.stats['peers_count'] = len(self.peers)
    
    async def _replication_loop(self):
        """Replicate data to peers"""
        while self.status == NodeStatus.RUNNING:
            try:
                # Replicate data to peers
                for data_item in self.data.values():
                    await self._replicate_data(data_item)
                
                await asyncio.sleep(60)  # Replicate every minute
                
            except Exception as e:
                logger.error("Replication error", error=str(e))
                await asyncio.sleep(10)
    
    async def _replicate_data(self, data_item: DHTData):
        """Replicate data to peers"""
        try:
            # In a real implementation, this would send data to peers
            # based on DHT routing rules
            self.stats['replication_events'] += 1
            
        except Exception as e:
            logger.error("Data replication failed", key=data_item.key, error=str(e))
    
    async def _query_peers(self, key: str) -> Optional[Any]:
        """Query peers for data"""
        try:
            # In a real implementation, this would query peers
            # based on DHT routing rules
            return None
            
        except Exception as e:
            logger.error("Peer query failed", key=key, error=str(e))
            return None
    
    async def _notify_peers_disconnect(self):
        """Notify peers of disconnection"""
        try:
            # In a real implementation, this would notify peers
            pass
            
        except Exception as e:
            logger.error("Failed to notify peers of disconnect", error=str(e))
    
    async def _notify_peers_delete(self, key: str):
        """Notify peers to delete data"""
        try:
            # In a real implementation, this would notify peers to delete data
            pass
            
        except Exception as e:
            logger.error("Failed to notify peers to delete data", key=key, error=str(e))
    
    async def _cleanup_loop(self):
        """Cleanup expired data"""
        while self.status == NodeStatus.RUNNING:
            try:
                current_time = datetime.utcnow()
                expired_keys = []
                
                for key, data_item in self.data.items():
                    if data_item.expires_at and current_time > data_item.expires_at:
                        expired_keys.append(key)
                
                # Remove expired data
                for key in expired_keys:
                    del self.data[key]
                
                if expired_keys:
                    logger.info("Cleaned up expired data", count=len(expired_keys))
                
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
            except Exception as e:
                logger.error("Cleanup error", error=str(e))
                await asyncio.sleep(60)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get DHT statistics"""
        return {
            **self.stats,
            'status': self.status.value,
            'node_id': self.node_id,
            'port': self.port
        }


class CRDTManager:
    """CRDT document management"""
    
    def __init__(self, dht: SimpleDHT):
        self.dht = dht
        self.documents: Dict[str, CRDTDocument] = {}
        self.y_docs: Dict[str, Any] = {}  # Yjs documents
        
        # Initialize Yjs if available
        if YJS_AVAILABLE:
            self._initialize_yjs()
    
    def _initialize_yjs(self):
        """Initialize Yjs CRDT library"""
        try:
            # Create Yjs document store
            self.ydoc = Y.YDoc()
            logger.info("Yjs CRDT library initialized")
        except Exception as e:
            logger.error("Failed to initialize Yjs", error=str(e))
    
    async def create_document(self, document_id: str, initial_content: Dict[str, Any] = None) -> bool:
        """Create a new CRDT document"""
        try:
            if initial_content is None:
                initial_content = {}
            
            # Create CRDT document
            document = CRDTDocument(
                document_id=document_id,
                content=initial_content,
                version=1,
                last_modified=datetime.utcnow()
            )
            
            # Store locally
            self.documents[document_id] = document
            
            # Store in DHT
            await self.dht.store(
                f"crdt_doc_{document_id}",
                document.__dict__,
                DataType.CRDT_DOCUMENT,
                expires_in=86400  # 24 hours
            )
            
            # Initialize Yjs document if available
            if YJS_AVAILABLE:
                y_doc = Y.YDoc()
                self.y_docs[document_id] = y_doc
            
            logger.info("CRDT document created", document_id=document_id)
            return True
            
        except Exception as e:
            logger.error("Failed to create CRDT document", document_id=document_id, error=str(e))
            return False
    
    async def update_document(self, document_id: str, updates: Dict[str, Any], 
                             contributor_id: str) -> bool:
        """Update CRDT document"""
        try:
            if document_id not in self.documents:
                return False
            
            document = self.documents[document_id]
            
            # Apply updates
            document.content.update(updates)
            document.version += 1
            document.last_modified = datetime.utcnow()
            document.contributors.add(contributor_id)
            
            # Store in DHT
            await self.dht.store(
                f"crdt_doc_{document_id}",
                document.__dict__,
                DataType.CRDT_DOCUMENT,
                expires_in=86400
            )
            
            logger.debug("CRDT document updated", document_id=document_id, version=document.version)
            return True
            
        except Exception as e:
            logger.error("Failed to update CRDT document", document_id=document_id, error=str(e))
            return False
    
    async def get_document(self, document_id: str) -> Optional[CRDTDocument]:
        """Get CRDT document"""
        try:
            # Check local cache
            if document_id in self.documents:
                return self.documents[document_id]
            
            # Query DHT
            data = await self.dht.get(f"crdt_doc_{document_id}")
            if data:
                document = CRDTDocument(**data)
                self.documents[document_id] = document
                return document
            
            return None
            
        except Exception as e:
            logger.error("Failed to get CRDT document", document_id=document_id, error=str(e))
            return None
    
    async def merge_document(self, document_id: str, remote_document: Dict[str, Any]) -> bool:
        """Merge remote document changes"""
        try:
            if document_id not in self.documents:
                # Create new document from remote
                await self.create_document(document_id, remote_document.get('content', {}))
                return True
            
            local_document = self.documents[document_id]
            
            # Simple merge strategy (in real implementation, use proper CRDT merge)
            if remote_document.get('version', 0) > local_document.version:
                local_document.content.update(remote_document.get('content', {}))
                local_document.version = remote_document.get('version', 0)
                local_document.last_modified = datetime.utcnow()
                
                # Store merged document
                await self.dht.store(
                    f"crdt_doc_{document_id}",
                    local_document.__dict__,
                    DataType.CRDT_DOCUMENT,
                    expires_in=86400
                )
                
                logger.info("CRDT document merged", document_id=document_id, version=local_document.version)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to merge CRDT document", document_id=document_id, error=str(e))
            return False


class DHTService:
    """Main DHT service"""
    
    def __init__(self, node_id: str = None, port: int = 8468):
        self.node_id = node_id or str(uuid.uuid4())
        self.port = port
        self.dht = SimpleDHT(self.node_id, port)
        self.crdt_manager = CRDTManager(self.dht)
        self.is_running = False
    
    async def start(self):
        """Start the DHT service"""
        try:
            await self.dht.start()
            self.is_running = True
            logger.info("DHT service started", node_id=self.node_id, port=self.port)
        except Exception as e:
            logger.error("Failed to start DHT service", error=str(e))
            raise
    
    async def stop(self):
        """Stop the DHT service"""
        try:
            await self.dht.stop()
            self.is_running = False
            logger.info("DHT service stopped")
        except Exception as e:
            logger.error("Failed to stop DHT service", error=str(e))
    
    async def store_data(self, key: str, value: Any, data_type: DataType = DataType.KEY_VALUE,
                        expires_in: Optional[int] = None) -> bool:
        """Store data in DHT"""
        return await self.dht.store(key, value, data_type, expires_in)
    
    async def get_data(self, key: str) -> Optional[Any]:
        """Get data from DHT"""
        return await self.dht.get(key)
    
    async def delete_data(self, key: str) -> bool:
        """Delete data from DHT"""
        return await self.dht.delete(key)
    
    async def create_crdt_document(self, document_id: str, initial_content: Dict[str, Any] = None) -> bool:
        """Create CRDT document"""
        return await self.crdt_manager.create_document(document_id, initial_content)
    
    async def update_crdt_document(self, document_id: str, updates: Dict[str, Any], 
                                  contributor_id: str) -> bool:
        """Update CRDT document"""
        return await self.crdt_manager.update_document(document_id, updates, contributor_id)
    
    async def get_crdt_document(self, document_id: str) -> Optional[CRDTDocument]:
        """Get CRDT document"""
        return await self.crdt_manager.get_document(document_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'dht_stats': self.dht.get_stats(),
            'documents_count': len(self.crdt_manager.documents),
            'is_running': self.is_running,
            'kademlia_available': KADEMLIA_AVAILABLE,
            'yjs_available': YJS_AVAILABLE
        }


async def main():
    """Main entry point for DHT node"""
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create and start service
    service = DHTService()
    
    try:
        await service.start()
        
        # Keep running
        logger.info("DHT node running")
        while service.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
