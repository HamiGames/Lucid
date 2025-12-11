"""
Data Chain Service
Core service for data chain operations

This service integrates with the blockchain core to provide
data chain functionality for the Lucid RDP system, managing
data chunks, Merkle trees, and integrity verification.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..core.merkle_tree_builder import MerkleTreeBuilder, MerkleTree, MerkleProof
from .chunk_manager import ChunkManager, ChunkMetadata
from .storage import DataStorage
from .integrity import IntegrityVerifier
from .deduplication import DeduplicationManager

logger = logging.getLogger(__name__)

# Environment variable configuration (required, no hardcoded defaults)
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL or MONGODB_URL environment variable not set")

BLOCKCHAIN_ENGINE_URL = os.getenv("BLOCKCHAIN_ENGINE_URL")
if not BLOCKCHAIN_ENGINE_URL:
    raise RuntimeError("BLOCKCHAIN_ENGINE_URL environment variable not set")

# Data chain configuration from environment
DATA_CHAIN_PORT = int(os.getenv("DATA_CHAIN_PORT", "8087"))
DATA_CHAIN_HOST = os.getenv("DATA_CHAIN_HOST", "0.0.0.0")
DATA_CHAIN_URL = os.getenv("DATA_CHAIN_URL", f"http://{DATA_CHAIN_HOST}:{DATA_CHAIN_PORT}")


class DataChainService:
    """
    Main data chain service.
    
    Handles data chain operations including chunk management,
    Merkle tree construction, integrity verification, and deduplication.
    Integrates with MongoDB for persistence and blockchain engine for operations.
    """
    
    def __init__(self, mongo_client: Optional[AsyncIOMotorClient] = None):
        """
        Initialize data chain service.
        
        Args:
            mongo_client: Optional MongoDB client. If not provided, creates new client.
        """
        if mongo_client:
            self.mongo_client = mongo_client
        else:
            self.mongo_client = AsyncIOMotorClient(MONGO_URL)
        
        self.db: AsyncIOMotorDatabase = self.mongo_client.get_database("lucid")
        
        # Initialize storage
        self.storage = DataStorage(self.db)
        
        # Initialize deduplication manager
        self.deduplication_manager = DeduplicationManager(self.db)
        
        # Initialize chunk manager
        self.chunk_manager = ChunkManager(
            self.db,
            self.storage,
            self.deduplication_manager
        )
        
        # Initialize integrity verifier
        self.integrity_verifier = IntegrityVerifier(self.db)
        
        # Initialize Merkle tree builder
        self.merkle_builder = MerkleTreeBuilder(self.db)
        
        logger.info("DataChainService initialized")
    
    async def start(self) -> bool:
        """
        Start the data chain service.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info("Starting DataChainService")
            
            # Verify database connection
            await self.mongo_client.admin.command('ping')
            
            # Initialize collections if needed
            await self._initialize_collections()
            
            logger.info("DataChainService started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start DataChainService: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the data chain service.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            logger.info("Stopping DataChainService")
            self.mongo_client.close()
            logger.info("DataChainService stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop DataChainService: {e}")
            return False
    
    async def _initialize_collections(self):
        """Initialize MongoDB collections with indexes."""
        try:
            # Chunks collection
            await self.db.chunks.create_index("chunk_id", unique=True)
            await self.db.chunks.create_index("session_id")
            await self.db.chunks.create_index("created_at")
            
            # Chunk metadata collection
            await self.db.chunk_metadata.create_index("chunk_id", unique=True)
            await self.db.chunk_metadata.create_index("session_id")
            await self.db.chunk_metadata.create_index("hash_value")
            await self.db.chunk_metadata.create_index("created_at")
            
            # Deduplication collection
            await self.db.chunk_deduplication.create_index("hash", unique=True)
            await self.db.chunk_deduplication.create_index("primary_chunk_id")
            await self.db.chunk_deduplication.create_index("gc_eligible")
            
            # Verification results collection
            await self.db.integrity_verification_results.create_index("chunk_id")
            await self.db.integrity_verification_results.create_index("timestamp")
            await self.db.integrity_verification_results.create_index([("chunk_id", 1), ("timestamp", -1)])
            
            logger.info("Data chain collections initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            raise
    
    async def store_chunk(
        self,
        data: bytes,
        session_id: Optional[str] = None,
        index: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a data chunk.
        
        Args:
            data: Chunk data bytes
            session_id: Optional session identifier
            index: Chunk index in sequence
            metadata: Optional chunk metadata
            
        Returns:
            Dictionary with chunk information
        """
        try:
            chunk_metadata = await self.chunk_manager.create_chunk(
                data,
                session_id,
                index,
                metadata
            )
            
            # Verify chunk if verification on storage is enabled
            if self.integrity_verifier.verification_on_storage:
                verification_result = await self.integrity_verifier.verify_chunk(
                    chunk_metadata.chunk_id,
                    data,
                    expected_hash=chunk_metadata.hash_value,
                    expected_size=chunk_metadata.size_bytes
                )
                chunk_metadata.metadata["verification"] = verification_result
            
            return chunk_metadata.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to store chunk: {e}")
            raise
    
    async def retrieve_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a data chunk.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Dictionary with chunk data and metadata, or None if not found
        """
        try:
            # Get chunk data
            data = await self.chunk_manager.get_chunk(chunk_id)
            if not data:
                return None
            
            # Get metadata
            metadata = await self.chunk_manager.get_chunk_metadata(chunk_id)
            if not metadata:
                return None
            
            # Verify chunk if verification on retrieval is enabled
            if self.integrity_verifier.verification_on_retrieval:
                verification_result = await self.integrity_verifier.verify_chunk(
                    chunk_id,
                    data,
                    expected_hash=metadata.get("hash_value"),
                    expected_size=metadata.get("size_bytes")
                )
                metadata["verification"] = verification_result
            
            return {
                "chunk_id": chunk_id,
                "data": data,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunk {chunk_id}: {e}")
            return None
    
    async def build_merkle_tree(
        self,
        chunk_ids: List[str],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build Merkle tree from chunks.
        
        Args:
            chunk_ids: List of chunk identifiers
            session_id: Optional session identifier
            
        Returns:
            Dictionary with Merkle tree information
        """
        try:
            # Get chunk metadata for all chunks
            chunk_metadata_list = []
            for chunk_id in chunk_ids:
                metadata = await self.chunk_manager.get_chunk_metadata(chunk_id)
                if metadata:
                    # Create a simple object with required attributes for MerkleTreeBuilder
                    # The builder expects objects with chunk_id, chunk_hash, and size attributes
                    class ChunkMeta:
                        def __init__(self, chunk_id, chunk_hash, size):
                            self.chunk_id = chunk_id
                            self.chunk_hash = chunk_hash
                            self.size = size
                    
                    chunk_meta = ChunkMeta(
                        chunk_id=metadata.get("chunk_id", chunk_id),
                        chunk_hash=metadata.get("hash_value", ""),
                        size=metadata.get("size_bytes", 0)
                    )
                    chunk_metadata_list.append(chunk_meta)
            
            if not chunk_metadata_list:
                raise ValueError("No valid chunks found")
            
            # Build Merkle tree from chunk metadata
            merkle_tree = await self.merkle_builder.build_session_merkle_tree(
                session_id or "default",
                chunk_metadata_list
            )
            
            return {
                "root_hash": merkle_tree.root_hash,
                "leaf_count": len(chunk_ids),
                "tree_depth": merkle_tree.tree_depth,
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to build Merkle tree: {e}")
            raise
    
    async def verify_merkle_proof(
        self,
        root_hash: str,
        leaf_hash: str,
        proof: MerkleProof,
        leaf_index: int
    ) -> Dict[str, Any]:
        """
        Verify Merkle proof.
        
        Args:
            root_hash: Expected root hash
            leaf_hash: Leaf hash to verify
            proof: Merkle proof
            leaf_index: Leaf index
            
        Returns:
            Dictionary with verification results
        """
        return await self.integrity_verifier.verify_merkle_proof(
            root_hash,
            leaf_hash,
            proof,
            leaf_index
        )
    
    async def verify_session(
        self,
        session_id: str,
        expected_merkle_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify all chunks for a session.
        
        Args:
            session_id: Session identifier
            expected_merkle_root: Expected Merkle root hash (optional)
            
        Returns:
            Dictionary with verification results
        """
        try:
            # Get all chunks for session
            chunks = await self.chunk_manager.list_chunks(session_id=session_id, limit=10000)
            chunk_ids = [chunk["chunk_id"] for chunk in chunks]
            
            if not chunk_ids:
                return {
                    "session_id": session_id,
                    "verified": False,
                    "error": "No chunks found for session"
                }
            
            # Verify chunks
            return await self.integrity_verifier.verify_session_chunks(
                session_id,
                chunk_ids,
                expected_merkle_root
            )
            
        except Exception as e:
            logger.error(f"Failed to verify session {session_id}: {e}")
            return {
                "session_id": session_id,
                "verified": False,
                "error": str(e)
            }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get data chain service status.
        
        Returns:
            Dictionary with service status information
        """
        try:
            # Get deduplication stats
            dedup_stats = await self.deduplication_manager.get_deduplication_stats()
            
            # Get chunk count
            chunks = await self.chunk_manager.list_chunks(limit=1)
            total_chunks = await self.db.chunk_metadata.count_documents({})
            
            return {
                "status": "healthy",
                "service": "data-chain",
                "total_chunks": total_chunks,
                "deduplication": dedup_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

