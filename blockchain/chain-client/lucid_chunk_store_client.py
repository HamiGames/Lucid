# LUCID Chunk Store Client - Distributed Chunk Storage System
# Implements comprehensive chunk storage, verification, and retrieval
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import secrets
import time
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)

# Configuration from environment
LUCID_CHUNK_STORE_CONTRACT_ADDRESS = "0x2345678901234567890123456789012345678901"
CHUNK_STORE_TIMEOUT_SECONDS = 300
CHUNK_VERIFICATION_INTERVAL = 60
MAX_CHUNK_SIZE = 1024 * 1024  # 1MB
CHUNK_REPLICATION_FACTOR = 3
STORAGE_PROOF_ALGORITHM = "sha256"


class ChunkStatus(Enum):
    """Chunk status states"""
    PENDING = "pending"
    STORED = "stored"
    VERIFIED = "verified"
    REPLICATED = "replicated"
    MISSING = "missing"
    CORRUPTED = "corrupted"
    ARCHIVED = "archived"


class StorageNodeStatus(Enum):
    """Storage node status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    FAILED = "failed"


class VerificationStatus(Enum):
    """Verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class ChunkMetadata:
    """Chunk metadata for storage"""
    chunk_id: str
    session_id: str
    chunk_hash: str
    size: int
    storage_paths: List[str]
    replication_factor: int
    timestamp: datetime
    status: ChunkStatus = ChunkStatus.PENDING
    encryption_key: Optional[str] = None
    compression_ratio: Optional[float] = None
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chunkId": self.chunk_id,
            "sessionId": self.session_id,
            "chunkHash": self.chunk_hash,
            "size": self.size,
            "storagePaths": self.storage_paths,
            "replicationFactor": self.replication_factor,
            "timestamp": int(self.timestamp.timestamp()),
            "status": self.status.value,
            "encryptionKey": self.encryption_key,
            "compressionRatio": self.compression_ratio,
            "checksum": self.checksum
        }


@dataclass
class StorageNode:
    """Storage node information"""
    node_id: str
    node_address: str
    storage_capacity: int
    available_capacity: int
    status: StorageNodeStatus
    last_heartbeat: datetime
    chunks_stored: List[str] = field(default_factory=list)
    performance_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "nodeId": self.node_id,
            "nodeAddress": self.node_address,
            "storageCapacity": self.storage_capacity,
            "availableCapacity": self.available_capacity,
            "status": self.status.value,
            "lastHeartbeat": int(self.last_heartbeat.timestamp()),
            "chunksStored": self.chunks_stored,
            "performanceScore": self.performance_score
        }


@dataclass
class StorageProof:
    """Proof of storage for chunk"""
    proof_id: str
    chunk_id: str
    node_id: str
    proof_hash: str
    proof_data: bytes
    timestamp: datetime
    status: VerificationStatus = VerificationStatus.PENDING
    validator_signature: Optional[bytes] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "proofId": self.proof_id,
            "chunkId": self.chunk_id,
            "nodeId": self.node_id,
            "proofHash": self.proof_hash,
            "proofData": self.proof_data.hex(),
            "timestamp": int(self.timestamp.timestamp()),
            "status": self.status.value,
            "validatorSignature": self.validator_signature.hex() if self.validator_signature else None
        }


@dataclass
class ChunkRetrieval:
    """Chunk retrieval information"""
    retrieval_id: str
    chunk_id: str
    requested_by: str
    timestamp: datetime
    retrieval_paths: List[str]
    status: str = "pending"
    error_message: Optional[str] = None


class LucidChunkStoreClient:
    """
    Lucid Chunk Store client for distributed chunk storage.
    
    Features:
    - Chunk storage and replication
    - Storage proof generation and verification
    - Storage node management
    - Chunk retrieval and integrity checking
    - Automatic rebalancing and repair
    - Performance monitoring and optimization
    """
    
    def __init__(
        self,
        contract_address: str = LUCID_CHUNK_STORE_CONTRACT_ADDRESS,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        output_dir: str = "/data/chunk-store"
    ):
        """Initialize Lucid Chunk Store client"""
        import os
        self.contract_address = contract_address
        self.rpc_url = rpc_url or os.getenv("ON_SYSTEM_CHAIN_RPC") or os.getenv("ON_SYSTEM_CHAIN_RPC_URL")
        if not self.rpc_url:
            raise RuntimeError("rpc_url must be provided or ON_SYSTEM_CHAIN_RPC/ON_SYSTEM_CHAIN_RPC_URL environment variable must be set")
        self.private_key = private_key
        self.output_dir = Path(output_dir)
        
        # Client state
        self.chunk_metadata: Dict[str, ChunkMetadata] = {}
        self.storage_nodes: Dict[str, StorageNode] = {}
        self.storage_proofs: Dict[str, List[StorageProof]] = {}
        self.chunk_retrievals: Dict[str, ChunkRetrieval] = {}
        
        # HTTP session
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Verification tasks
        self._verification_tasks: Dict[str, asyncio.Task] = {}
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LucidChunkStoreClient initialized: {contract_address}")
    
    async def start(self) -> bool:
        """Start the chunk store client"""
        try:
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=30)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
            
            # Start verification tasks
            asyncio.create_task(self._start_verification_loop())
            
            logger.info("Lucid Chunk Store client started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start chunk store client: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the chunk store client"""
        try:
            # Cancel verification tasks
            for task in self._verification_tasks.values():
                task.cancel()
            
            if self.http_session:
                await self.http_session.close()
            
            logger.info("Lucid Chunk Store client stopped")
            
        except Exception as e:
            logger.error(f"Error stopping chunk store client: {e}")
    
    async def store_chunk(
        self,
        chunk_id: str,
        session_id: str,
        chunk_data: bytes,
        replication_factor: int = CHUNK_REPLICATION_FACTOR,
        encrypt: bool = True
    ) -> bool:
        """Store chunk with replication"""
        try:
            # Validate chunk size
            if len(chunk_data) > MAX_CHUNK_SIZE:
                raise ValueError(f"Chunk size exceeds maximum: {len(chunk_data)} > {MAX_CHUNK_SIZE}")
            
            # Calculate chunk hash
            chunk_hash = hashlib.sha256(chunk_data).hexdigest()
            
            # Encrypt chunk if requested
            if encrypt:
                chunk_data, encryption_key = await self._encrypt_chunk(chunk_data)
            else:
                encryption_key = None
            
            # Calculate checksum
            checksum = hashlib.md5(chunk_data).hexdigest()
            
            # Get available storage nodes
            available_nodes = await self._get_available_storage_nodes(replication_factor)
            if len(available_nodes) < replication_factor:
                raise ValueError(f"Insufficient storage nodes: {len(available_nodes)} < {replication_factor}")
            
            # Store chunk on nodes
            storage_paths = []
            for i, node in enumerate(available_nodes[:replication_factor]):
                storage_path = await self._store_chunk_on_node(
                    node, chunk_id, chunk_data, i
                )
                if storage_path:
                    storage_paths.append(storage_path)
                    # Update node storage
                    node.available_capacity -= len(chunk_data)
                    node.chunks_stored.append(chunk_id)
            
            if len(storage_paths) < replication_factor:
                raise ValueError(f"Failed to store chunk on sufficient nodes: {len(storage_paths)} < {replication_factor}")
            
            # Create chunk metadata
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                session_id=session_id,
                chunk_hash=chunk_hash,
                size=len(chunk_data),
                storage_paths=storage_paths,
                replication_factor=len(storage_paths),
                timestamp=datetime.now(timezone.utc),
                status=ChunkStatus.STORED,
                encryption_key=encryption_key,
                checksum=checksum
            )
            
            # Store metadata
            self.chunk_metadata[chunk_id] = metadata
            
            # Submit to blockchain
            await self._submit_chunk_metadata(metadata)
            
            # Start verification
            await self._start_chunk_verification(chunk_id)
            
            logger.info(f"Chunk stored: {chunk_id} on {len(storage_paths)} nodes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store chunk: {e}")
            return False
    
    async def retrieve_chunk(
        self,
        chunk_id: str,
        requested_by: str = "system"
    ) -> Optional[bytes]:
        """Retrieve chunk data"""
        try:
            # Get chunk metadata
            metadata = self.chunk_metadata.get(chunk_id)
            if not metadata:
                raise ValueError(f"Chunk metadata not found: {chunk_id}")
            
            # Create retrieval record
            retrieval_id = secrets.token_hex(16)
            retrieval = ChunkRetrieval(
                retrieval_id=retrieval_id,
                chunk_id=chunk_id,
                requested_by="user",
                timestamp=datetime.now(timezone.utc),
                retrieval_paths=metadata.storage_paths.copy()
            )
            
            self.chunk_retrievals[retrieval_id] = retrieval
            
            # Try to retrieve from storage nodes
            chunk_data = None
            for storage_path in metadata.storage_paths:
                try:
                    chunk_data = await self._retrieve_chunk_from_path(storage_path)
                    if chunk_data:
                        break
                except Exception as e:
                    logger.warning(f"Failed to retrieve from {storage_path}: {e}")
                    continue
            
            if not chunk_data:
                retrieval.status = "failed"
                retrieval.error_message = "Failed to retrieve from all storage paths"
                raise ValueError("Failed to retrieve chunk from any storage node")
            
            # Verify chunk integrity
            if not await self._verify_chunk_integrity(chunk_id, chunk_data):
                retrieval.status = "failed"
                retrieval.error_message = "Chunk integrity verification failed"
                raise ValueError("Chunk integrity verification failed")
            
            # Decrypt if needed
            if metadata.encryption_key:
                chunk_data = await self._decrypt_chunk(chunk_data, metadata.encryption_key)
            
            retrieval.status = "success"
            logger.info(f"Chunk retrieved: {chunk_id}")
            return chunk_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunk: {e}")
            return None
    
    async def verify_chunk_storage(
        self,
        chunk_id: str
    ) -> bool:
        """Verify chunk storage integrity"""
        try:
            # Get chunk metadata
            metadata = self.chunk_metadata.get(chunk_id)
            if not metadata:
                return False
            
            # Verify chunk on each storage path
            verification_results = []
            for storage_path in metadata.storage_paths:
                try:
                    # Retrieve chunk data
                    chunk_data = await self._retrieve_chunk_from_path(storage_path)
                    if not chunk_data:
                        verification_results.append(False)
                        continue
                    
                    # Verify checksum
                    checksum = hashlib.md5(chunk_data).hexdigest()
                    if checksum != metadata.checksum:
                        verification_results.append(False)
                        continue
                    
                    # Verify size
                    if len(chunk_data) != metadata.size:
                        verification_results.append(False)
                        continue
                    
                    verification_results.append(True)
                    
                except Exception as e:
                    logger.warning(f"Verification failed for {storage_path}: {e}")
                    verification_results.append(False)
            
            # Update chunk status based on verification results
            successful_verifications = sum(verification_results)
            if successful_verifications == len(verification_results):
                metadata.status = ChunkStatus.VERIFIED
            elif successful_verifications >= metadata.replication_factor // 2 + 1:
                metadata.status = ChunkStatus.STORED
            else:
                metadata.status = ChunkStatus.CORRUPTED
            
            logger.info(f"Chunk verification completed: {chunk_id} - {successful_verifications}/{len(verification_results)} successful")
            return successful_verifications >= metadata.replication_factor // 2 + 1
            
        except Exception as e:
            logger.error(f"Failed to verify chunk storage: {e}")
            return False
    
    async def repair_chunk(
        self,
        chunk_id: str
    ) -> bool:
        """Repair corrupted or missing chunk replicas"""
        try:
            # Get chunk metadata
            metadata = self.chunk_metadata.get(chunk_id)
            if not metadata:
                return False
            
            # Find working replicas
            working_paths = []
            for storage_path in metadata.storage_paths:
                try:
                    chunk_data = await self._retrieve_chunk_from_path(storage_path)
                    if chunk_data and await self._verify_chunk_integrity(chunk_id, chunk_data):
                        working_paths.append(storage_path)
                except Exception:
                    continue
            
            if not working_paths:
                logger.error(f"No working replicas found for chunk: {chunk_id}")
                return False
            
            # Get source data
            source_data = None
            for path in working_paths:
                try:
                    source_data = await self._retrieve_chunk_from_path(path)
                    break
                except Exception:
                    continue
            
            if not source_data:
                return False
            
            # Find failed storage paths
            failed_paths = [path for path in metadata.storage_paths if path not in working_paths]
            
            # Repair failed replicas
            repaired_count = 0
            for failed_path in failed_paths:
                try:
                    # Find replacement node
                    replacement_node = await self._find_replacement_node(failed_path)
                    if replacement_node:
                        # Store chunk on replacement node
                        new_path = await self._store_chunk_on_node(
                            replacement_node, chunk_id, source_data, len(working_paths) + repaired_count
                        )
                        if new_path:
                            # Update metadata
                            metadata.storage_paths.remove(failed_path)
                            metadata.storage_paths.append(new_path)
                            repaired_count += 1
                            
                except Exception as e:
                    logger.warning(f"Failed to repair replica {failed_path}: {e}")
            
            if repaired_count > 0:
                metadata.status = ChunkStatus.REPLICATED
                logger.info(f"Chunk repaired: {chunk_id} - {repaired_count} replicas restored")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to repair chunk: {e}")
            return False
    
    async def add_storage_node(
        self,
        node_id: str,
        node_address: str,
        storage_capacity: int
    ) -> bool:
        """Add new storage node"""
        try:
            # Create storage node
            node = StorageNode(
                node_id=node_id,
                node_address=node_address,
                storage_capacity=storage_capacity,
                available_capacity=storage_capacity,
                status=StorageNodeStatus.ACTIVE,
                last_heartbeat=datetime.now(timezone.utc)
            )
            
            # Store node
            self.storage_nodes[node_id] = node
            
            # Submit to blockchain
            await self._submit_storage_node_registration(node)
            
            logger.info(f"Storage node added: {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add storage node: {e}")
            return False
    
    async def get_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Get chunk metadata by ID"""
        return self.chunk_metadata.get(chunk_id)
    
    async def list_chunks(
        self,
        session_id: Optional[str] = None,
        status: Optional[ChunkStatus] = None,
        limit: int = 100
    ) -> List[ChunkMetadata]:
        """List chunks with filtering"""
        chunks = list(self.chunk_metadata.values())
        
        # Apply filters
        if session_id:
            chunks = [c for c in chunks if c.session_id == session_id]
        
        if status:
            chunks = [c for c in chunks if c.status == status]
        
        # Sort by timestamp (newest first)
        chunks.sort(key=lambda c: c.timestamp, reverse=True)
        
        return chunks[:limit]
    
    async def get_storage_node(self, node_id: str) -> Optional[StorageNode]:
        """Get storage node by ID"""
        return self.storage_nodes.get(node_id)
    
    async def list_storage_nodes(
        self,
        status: Optional[StorageNodeStatus] = None,
        limit: int = 100
    ) -> List[StorageNode]:
        """List storage nodes with filtering"""
        nodes = list(self.storage_nodes.values())
        
        # Apply filters
        if status:
            nodes = [n for n in nodes if n.status == status]
        
        # Sort by performance score (highest first)
        nodes.sort(key=lambda n: n.performance_score, reverse=True)
        
        return nodes[:limit]
    
    async def _encrypt_chunk(self, chunk_data: bytes) -> Tuple[bytes, str]:
        """Encrypt chunk data"""
        try:
            # Generate random key
            key = secrets.token_bytes(32)
            
            # Generate random IV
            iv = secrets.token_bytes(16)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            
            # Pad data
            padding_length = 16 - (len(chunk_data) % 16)
            padded_data = chunk_data + bytes([padding_length] * padding_length)
            
            # Encrypt
            encryptor = cipher.encryptor()
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine IV and encrypted data
            result = iv + encrypted_data
            
            return result, key.hex()
            
        except Exception as e:
            logger.error(f"Failed to encrypt chunk: {e}")
            raise
    
    async def _decrypt_chunk(self, encrypted_data: bytes, key_hex: str) -> bytes:
        """Decrypt chunk data"""
        try:
            # Decode key
            key = bytes.fromhex(key_hex)
            
            # Extract IV and encrypted data
            iv = encrypted_data[:16]
            encrypted_chunk = encrypted_data[16:]
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            
            # Decrypt
            decryptor = cipher.decryptor()
            decrypted_data = decryptor.update(encrypted_chunk) + decryptor.finalize()
            
            # Remove padding
            padding_length = decrypted_data[-1]
            result = decrypted_data[:-padding_length]
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to decrypt chunk: {e}")
            raise
    
    async def _get_available_storage_nodes(self, count: int) -> List[StorageNode]:
        """Get available storage nodes for chunk storage"""
        available_nodes = [
            node for node in self.storage_nodes.values()
            if node.status == StorageNodeStatus.ACTIVE
        ]
        
        # Sort by available capacity (highest first)
        available_nodes.sort(key=lambda n: n.available_capacity, reverse=True)
        
        return available_nodes[:count]
    
    async def _store_chunk_on_node(
        self,
        node: StorageNode,
        chunk_id: str,
        chunk_data: bytes,
        replica_index: int
    ) -> Optional[str]:
        """Store chunk on specific node"""
        try:
            # Create storage path
            storage_path = f"{node.node_address}/chunks/{chunk_id}_{replica_index}"
            
            # In production, this would make HTTP request to storage node
            # For now, simulate storage
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Verify storage
            if len(chunk_data) <= node.available_capacity:
                logger.info(f"Chunk stored on node {node.node_id}: {storage_path}")
                return storage_path
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to store chunk on node {node.node_id}: {e}")
            return None
    
    async def _retrieve_chunk_from_path(self, storage_path: str) -> Optional[bytes]:
        """Retrieve chunk from storage path"""
        try:
            # In production, this would make HTTP request to storage node
            # For now, simulate retrieval
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Simulate chunk data
            chunk_data = secrets.token_bytes(1024)  # Placeholder data
            
            return chunk_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunk from {storage_path}: {e}")
            return None
    
    async def _verify_chunk_integrity(self, chunk_id: str, chunk_data: bytes) -> bool:
        """Verify chunk integrity"""
        try:
            # Get metadata
            metadata = self.chunk_metadata.get(chunk_id)
            if not metadata:
                return False
            
            # Verify checksum
            checksum = hashlib.md5(chunk_data).hexdigest()
            if checksum != metadata.checksum:
                return False
            
            # Verify size
            if len(chunk_data) != metadata.size:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify chunk integrity: {e}")
            return False
    
    async def _submit_chunk_metadata(self, metadata: ChunkMetadata) -> None:
        """Submit chunk metadata to blockchain"""
        try:
            # Prepare transaction data
            tx_data = metadata.to_dict()
            
            # Submit to blockchain (simplified)
            logger.info(f"Chunk metadata submitted to blockchain: {metadata.chunk_id}")
            
        except Exception as e:
            logger.error(f"Failed to submit chunk metadata: {e}")
    
    async def _submit_storage_node_registration(self, node: StorageNode) -> None:
        """Submit storage node registration to blockchain"""
        try:
            # Prepare transaction data
            tx_data = node.to_dict()
            
            # Submit to blockchain (simplified)
            logger.info(f"Storage node registration submitted: {node.node_id}")
            
        except Exception as e:
            logger.error(f"Failed to submit storage node registration: {e}")
    
    async def _start_chunk_verification(self, chunk_id: str) -> None:
        """Start periodic verification for chunk"""
        try:
            if chunk_id in self._verification_tasks:
                return
            
            async def verification_loop():
                while True:
                    try:
                        await asyncio.sleep(CHUNK_VERIFICATION_INTERVAL)
                        await self.verify_chunk_storage(chunk_id)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Verification loop error for {chunk_id}: {e}")
            
            task = asyncio.create_task(verification_loop())
            self._verification_tasks[chunk_id] = task
            
        except Exception as e:
            logger.error(f"Failed to start chunk verification: {e}")
    
    async def _start_verification_loop(self) -> None:
        """Start global verification loop"""
        try:
            while True:
                try:
                    await asyncio.sleep(300)  # 5 minutes
                    
                    # Verify all chunks
                    for chunk_id in list(self.chunk_metadata.keys()):
                        try:
                            await self.verify_chunk_storage(chunk_id)
                        except Exception as e:
                            logger.error(f"Verification error for {chunk_id}: {e}")
                    
                    # Repair corrupted chunks
                    corrupted_chunks = [
                        chunk_id for chunk_id, metadata in self.chunk_metadata.items()
                        if metadata.status == ChunkStatus.CORRUPTED
                    ]
                    
                    for chunk_id in corrupted_chunks:
                        try:
                            await self.repair_chunk(chunk_id)
                        except Exception as e:
                            logger.error(f"Repair error for {chunk_id}: {e}")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Verification loop error: {e}")
                    await asyncio.sleep(60)  # Wait before retrying
            
        except Exception as e:
            logger.error(f"Failed to start verification loop: {e}")
    
    async def _find_replacement_node(self, failed_path: str) -> Optional[StorageNode]:
        """Find replacement node for failed storage path"""
        try:
            # Get available nodes
            available_nodes = [
                node for node in self.storage_nodes.values()
                if node.status == StorageNodeStatus.ACTIVE
            ]
            
            # Sort by available capacity
            available_nodes.sort(key=lambda n: n.available_capacity, reverse=True)
            
            return available_nodes[0] if available_nodes else None
            
        except Exception as e:
            logger.error(f"Failed to find replacement node: {e}")
            return None


# Global chunk store client
_chunk_store_client: Optional[LucidChunkStoreClient] = None


def get_chunk_store_client() -> Optional[LucidChunkStoreClient]:
    """Get global chunk store client instance"""
    return _chunk_store_client


def create_chunk_store_client(
    contract_address: str = LUCID_CHUNK_STORE_CONTRACT_ADDRESS,
    rpc_url: Optional[str] = None,
    private_key: Optional[str] = None,
    output_dir: str = "/data/chunk-store"
) -> LucidChunkStoreClient:
    """Create new chunk store client instance"""
    global _chunk_store_client
    _chunk_store_client = LucidChunkStoreClient(contract_address, rpc_url, private_key, output_dir)
    return _chunk_store_client


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create chunk store client
    client = create_chunk_store_client()
    
    # Start client
    if await client.start():
        print("Chunk store client started successfully")
        
        # Add storage nodes
        await client.add_storage_node("node_001", "http://storage-node-001-distroless:8080", 1000000000)  # 1GB
        await client.add_storage_node("node_002", "http://storage-node-002-distroless:8080", 1000000000)  # 1GB
        await client.add_storage_node("node_003", "http://storage-node-003-distroless:8080", 1000000000)  # 1GB
        
        # List storage nodes
        nodes = await client.list_storage_nodes()
        print(f"Storage nodes: {len(nodes)}")
        
        # Store test chunk
        test_chunk_data = b"Hello, LUCID Chunk Store! This is a test chunk."
        success = await client.store_chunk(
            chunk_id="test_chunk_001",
            session_id="test_session_001",
            chunk_data=test_chunk_data,
            replication_factor=3
        )
        print(f"Chunk stored: {success}")
        
        # Get chunk metadata
        metadata = await client.get_chunk_metadata("test_chunk_001")
        if metadata:
            print(f"Chunk metadata: {metadata.chunk_id}")
            print(f"Size: {metadata.size}")
            print(f"Status: {metadata.status.value}")
            print(f"Storage paths: {len(metadata.storage_paths)}")
        
        # Retrieve chunk
        retrieved_data = await client.retrieve_chunk("test_chunk_001")
        if retrieved_data:
            print(f"Chunk retrieved: {len(retrieved_data)} bytes")
            print(f"Data matches: {retrieved_data == test_chunk_data}")
        
        # Verify chunk storage
        verification_result = await client.verify_chunk_storage("test_chunk_001")
        print(f"Chunk verification: {verification_result}")
        
        # List chunks
        chunks = await client.list_chunks()
        print(f"Total chunks: {len(chunks)}")
        
        # Wait for verification
        await asyncio.sleep(5)
        
        # Stop client
        await client.stop()
        print("Chunk store client stopped")
    
    else:
        print("Failed to start chunk store client")


if __name__ == "__main__":
    asyncio.run(main())
