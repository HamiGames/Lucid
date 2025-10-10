#!/usr/bin/env python3
"""
LucidChunkStore Smart Contract Interface
Based on rebuild-blockchain-engine.md specifications

Implements On-System Chain encrypted chunk metadata storage:
- storeChunkMetadata(chunkId, sessionId, chunkHash, size, storagePath)
- retrieveChunkMetadata(chunkId)
- verifyChunkStorage(chunkId)
- Gas-efficient chunk metadata management
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class ChunkStatus(Enum):
    """Chunk status states"""
    PENDING = "pending"
    STORED = "stored"
    VERIFIED = "verified"
    REPLICATED = "replicated"
    MISSING = "missing"
    CORRUPTED = "corrupted"
    ARCHIVED = "archived"


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
        """Convert to dictionary for contract call"""
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
class StorageProof:
    """Proof of storage for chunk"""
    proof_id: str
    chunk_id: str
    node_id: str
    proof_hash: str
    proof_data: bytes
    timestamp: datetime
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
            "validatorSignature": self.validator_signature.hex() if self.validator_signature else None
        }


class LucidChunkStoreInterface(ABC):
    """Abstract interface for LucidChunkStore contract"""
    
    @abstractmethod
    async def store_chunk_metadata(self, metadata: ChunkMetadata, gas_limit: int = 500000) -> str:
        """
        Store chunk metadata on blockchain.
        
        Args:
            metadata: Chunk metadata to store
            gas_limit: Maximum gas to use
            
        Returns:
            Transaction hash
        """
        pass
    
    @abstractmethod
    async def retrieve_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """
        Retrieve chunk metadata from blockchain.
        
        Args:
            chunk_id: Chunk ID to retrieve
            
        Returns:
            ChunkMetadata or None
        """
        pass
    
    @abstractmethod
    async def verify_chunk_storage(self, chunk_id: str) -> bool:
        """
        Verify chunk storage integrity.
        
        Args:
            chunk_id: Chunk ID to verify
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def update_chunk_status(self, chunk_id: str, status: ChunkStatus, gas_limit: int = 200000) -> str:
        """
        Update chunk status.
        
        Args:
            chunk_id: Chunk ID to update
            status: New status
            gas_limit: Maximum gas to use
            
        Returns:
            Transaction hash
        """
        pass


class LucidChunkStoreContract(LucidChunkStoreInterface):
    """
    LucidChunkStore smart contract implementation.
    
    Implements On-System Chain chunk metadata storage with:
    - storeChunkMetadata function call
    - retrieveChunkMetadata view function
    - verifyChunkStorage verification
    - Gas-efficient chunk metadata management
    """
    
    # Contract ABI for LucidChunkStore
    CONTRACT_ABI = [
        {
            "inputs": [
                {"name": "chunkId", "type": "bytes32"},
                {"name": "sessionId", "type": "bytes32"},
                {"name": "chunkHash", "type": "bytes32"},
                {"name": "size", "type": "uint256"},
                {"name": "storagePaths", "type": "string[]"},
                {"name": "replicationFactor", "type": "uint256"}
            ],
            "name": "storeChunkMetadata",
            "outputs": [{"name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                {"name": "chunkId", "type": "bytes32"}
            ],
            "name": "getChunkMetadata",
            "outputs": [
                {"name": "sessionId", "type": "bytes32"},
                {"name": "chunkHash", "type": "bytes32"},
                {"name": "size", "type": "uint256"},
                {"name": "storagePaths", "type": "string[]"},
                {"name": "replicationFactor", "type": "uint256"},
                {"name": "timestamp", "type": "uint256"},
                {"name": "status", "type": "uint8"}
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {"name": "chunkId", "type": "bytes32"},
                {"name": "status", "type": "uint8"}
            ],
            "name": "updateChunkStatus",
            "outputs": [{"name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "chunkId", "type": "bytes32"},
                {"indexed": True, "name": "sessionId", "type": "bytes32"},
                {"indexed": False, "name": "chunkHash", "type": "bytes32"},
                {"indexed": False, "name": "size", "type": "uint256"},
                {"indexed": False, "name": "replicationFactor", "type": "uint256"}
            ],
            "name": "ChunkStored",
            "type": "event"
        }
    ]
    
    def __init__(self, contract_address: str, evm_client: 'EVMClient'):
        self.contract_address = contract_address
        self.evm_client = evm_client
        self.logger = logging.getLogger(__name__)
        
        # Mock storage for development
        self._chunk_metadata: Dict[str, ChunkMetadata] = {}
        self._storage_proofs: Dict[str, StorageProof] = {}
    
    async def store_chunk_metadata(self, metadata: ChunkMetadata, gas_limit: int = 500000) -> str:
        """
        Store chunk metadata on blockchain.
        
        Per Spec-1b: storeChunkMetadata(chunkId, sessionId, chunkHash, size, storagePaths, replicationFactor)
        """
        try:
            # Prepare function call parameters
            chunk_id_bytes = bytes.fromhex(metadata.chunk_id.replace("-", ""))
            session_id_bytes = bytes.fromhex(metadata.session_id.replace("-", ""))
            chunk_hash_bytes = bytes.fromhex(metadata.chunk_hash.replace("0x", ""))
            
            params = {
                "chunkId": chunk_id_bytes,
                "sessionId": session_id_bytes,
                "chunkHash": chunk_hash_bytes,
                "size": metadata.size,
                "storagePaths": metadata.storage_paths,
                "replicationFactor": metadata.replication_factor
            }
            
            # Submit transaction
            tx_hash = await self.evm_client.call_contract_function(
                contract_address=self.contract_address,
                function_name="storeChunkMetadata",
                parameters=params,
                gas_limit=gas_limit
            )
            
            if not tx_hash:
                raise Exception("Failed to submit storeChunkMetadata transaction")
            
            # Store in mock storage
            self._chunk_metadata[metadata.chunk_id] = metadata
            
            self.logger.info(f"Chunk metadata {metadata.chunk_id} stored with tx {tx_hash}")
            return tx_hash
            
        except Exception as e:
            self.logger.error(f"Failed to store chunk metadata {metadata.chunk_id}: {e}")
            raise
    
    async def retrieve_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Retrieve chunk metadata from blockchain"""
        try:
            # Check mock storage first
            if chunk_id in self._chunk_metadata:
                return self._chunk_metadata[chunk_id]
            
            # Query blockchain
            chunk_id_bytes = bytes.fromhex(chunk_id.replace("-", ""))
            
            result = await self.evm_client.call_contract_view_function(
                contract_address=self.contract_address,
                function_name="getChunkMetadata",
                parameters={"chunkId": chunk_id_bytes}
            )
            
            if result:
                # Parse result and create ChunkMetadata
                metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    session_id=result["sessionId"].hex(),
                    chunk_hash=result["chunkHash"].hex(),
                    size=result["size"],
                    storage_paths=result["storagePaths"],
                    replication_factor=result["replicationFactor"],
                    timestamp=datetime.fromtimestamp(result["timestamp"], timezone.utc),
                    status=ChunkStatus(result["status"])
                )
                
                return metadata
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve chunk metadata for {chunk_id}: {e}")
            return None
    
    async def verify_chunk_storage(self, chunk_id: str) -> bool:
        """Verify chunk storage integrity"""
        try:
            # Get chunk metadata
            metadata = await self.retrieve_chunk_metadata(chunk_id)
            
            if not metadata:
                self.logger.warning(f"No metadata found for chunk {chunk_id}")
                return False
            
            # Verify chunk hash format
            if not metadata.chunk_hash or len(metadata.chunk_hash) != 64:
                self.logger.warning(f"Invalid chunk hash format for {chunk_id}")
                return False
            
            # Verify size is positive
            if metadata.size <= 0:
                self.logger.warning(f"Invalid chunk size for {chunk_id}")
                return False
            
            # Verify storage paths exist
            if not metadata.storage_paths or len(metadata.storage_paths) == 0:
                self.logger.warning(f"No storage paths for chunk {chunk_id}")
                return False
            
            # Verify replication factor
            if metadata.replication_factor <= 0 or metadata.replication_factor > len(metadata.storage_paths):
                self.logger.warning(f"Invalid replication factor for chunk {chunk_id}")
                return False
            
            # Check if checksum matches
            if metadata.checksum:
                if not self._verify_checksum(metadata):
                    self.logger.warning(f"Checksum verification failed for chunk {chunk_id}")
                    return False
            
            self.logger.info(f"Chunk storage verified for {chunk_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to verify chunk storage for {chunk_id}: {e}")
            return False
    
    def _verify_checksum(self, metadata: ChunkMetadata) -> bool:
        """Verify chunk checksum"""
        try:
            if not metadata.checksum:
                return True  # No checksum to verify
            
            # Calculate expected checksum from metadata
            checksum_data = f"{metadata.chunk_id}:{metadata.session_id}:{metadata.chunk_hash}:{metadata.size}"
            expected_checksum = hashlib.sha256(checksum_data.encode()).hexdigest()
            
            return metadata.checksum == expected_checksum
            
        except Exception:
            return False
    
    async def update_chunk_status(self, chunk_id: str, status: ChunkStatus, gas_limit: int = 200000) -> str:
        """Update chunk status"""
        try:
            # Prepare function call parameters
            chunk_id_bytes = bytes.fromhex(chunk_id.replace("-", ""))
            
            params = {
                "chunkId": chunk_id_bytes,
                "status": status.value
            }
            
            # Submit transaction
            tx_hash = await self.evm_client.call_contract_function(
                contract_address=self.contract_address,
                function_name="updateChunkStatus",
                parameters=params,
                gas_limit=gas_limit
            )
            
            if not tx_hash:
                raise Exception("Failed to submit updateChunkStatus transaction")
            
            # Update mock storage
            if chunk_id in self._chunk_metadata:
                self._chunk_metadata[chunk_id].status = status
            
            self.logger.info(f"Chunk status updated for {chunk_id}: {status.value}")
            return tx_hash
            
        except Exception as e:
            self.logger.error(f"Failed to update chunk status for {chunk_id}: {e}")
            raise
    
    async def store_chunk_proof(self, proof: StorageProof, gas_limit: int = 300000) -> str:
        """Store chunk storage proof"""
        try:
            # Store proof in mock storage
            self._storage_proofs[proof.proof_id] = proof
            
            self.logger.info(f"Chunk proof stored: {proof.proof_id}")
            return f"proof_tx_{proof.proof_id}"
            
        except Exception as e:
            self.logger.error(f"Failed to store chunk proof {proof.proof_id}: {e}")
            raise
    
    async def get_chunk_proof(self, proof_id: str) -> Optional[StorageProof]:
        """Get chunk storage proof"""
        try:
            return self._storage_proofs.get(proof_id)
            
        except Exception as e:
            self.logger.error(f"Failed to get chunk proof {proof_id}: {e}")
            return None
    
    async def list_chunk_metadata(self, session_id: Optional[str] = None, limit: int = 100) -> List[ChunkMetadata]:
        """List chunk metadata with optional filtering"""
        try:
            chunks = []
            
            # Get from mock storage
            for metadata in self._chunk_metadata.values():
                if session_id is None or metadata.session_id == session_id:
                    chunks.append(metadata)
            
            # Sort by timestamp
            chunks.sort(key=lambda x: x.timestamp, reverse=True)
            
            return chunks[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to list chunk metadata: {e}")
            return []
    
    async def get_chunks_by_status(self, status: ChunkStatus, limit: int = 100) -> List[ChunkMetadata]:
        """Get chunks by status"""
        try:
            chunks = []
            
            # Get from mock storage
            for metadata in self._chunk_metadata.values():
                if metadata.status == status:
                    chunks.append(metadata)
            
            # Sort by timestamp
            chunks.sort(key=lambda x: x.timestamp, reverse=True)
            
            return chunks[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get chunks by status: {e}")
            return []
    
    async def get_contract_stats(self) -> Dict[str, Any]:
        """Get contract statistics"""
        try:
            total_chunks = len(self._chunk_metadata)
            total_proofs = len(self._storage_proofs)
            
            status_counts = {}
            for metadata in self._chunk_metadata.values():
                status = metadata.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            total_size = sum(metadata.size for metadata in self._chunk_metadata.values())
            
            return {
                "contract_address": self.contract_address,
                "total_chunks": total_chunks,
                "total_proofs": total_proofs,
                "status_counts": status_counts,
                "total_size": total_size
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get contract stats: {e}")
            return {}


# Global contract instance
_chunk_store_contract: Optional[LucidChunkStoreContract] = None


def get_chunk_store_contract() -> Optional[LucidChunkStoreContract]:
    """Get global LucidChunkStore contract instance"""
    return _chunk_store_contract


def create_chunk_store_contract(contract_address: str, evm_client: 'EVMClient') -> LucidChunkStoreContract:
    """Create and initialize LucidChunkStore contract"""
    global _chunk_store_contract
    _chunk_store_contract = LucidChunkStoreContract(contract_address, evm_client)
    return _chunk_store_contract


async def cleanup_chunk_store_contract():
    """Cleanup chunk store contract"""
    global _chunk_store_contract
    _chunk_store_contract = None


if __name__ == "__main__":
    async def test_chunk_store_contract():
        """Test LucidChunkStore contract"""
        from .evm_client import EVMClient
        
        # Mock EVM client for testing
        evm_client = EVMClient("http://localhost:8545")
        
        # Create contract
        contract = create_chunk_store_contract("0x2345678901234567890123456789012345678901", evm_client)
        
        try:
            # Test chunk metadata
            metadata = ChunkMetadata(
                chunk_id="chunk-001",
                session_id="session-001",
                chunk_hash="0x" + "c" * 64,
                size=1024000,
                storage_paths=["/storage/chunk-001-1", "/storage/chunk-001-2"],
                replication_factor=2,
                timestamp=datetime.now(timezone.utc),
                status=ChunkStatus.STORED
            )
            
            # Test storing metadata
            tx_hash = await contract.store_chunk_metadata(metadata)
            print(f"Chunk metadata stored with tx: {tx_hash}")
            
            # Test retrieving metadata
            retrieved = await contract.retrieve_chunk_metadata(metadata.chunk_id)
            if retrieved:
                print(f"Chunk metadata retrieved: {retrieved.status.value}")
            else:
                print("No chunk metadata found")
            
            # Test verification
            is_valid = await contract.verify_chunk_storage(metadata.chunk_id)
            print(f"Chunk storage verification: {'VALID' if is_valid else 'INVALID'}")
            
            # Test contract stats
            stats = await contract.get_contract_stats()
            print(f"Contract stats: {stats}")
            
        finally:
            await evm_client.close()
    
    # Run test
    asyncio.run(test_chunk_store_contract())
