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
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL, MONGODB_URL, or MONGODB_URI environment variable not set")

# Substitute password placeholder if present in connection string
# This handles cases where env files have {MONGODB_PASSWORD} placeholder
if "{MONGODB_PASSWORD}" in MONGO_URL:
    mongodb_password = os.getenv("MONGODB_PASSWORD")
    if not mongodb_password:
        raise RuntimeError("MONGODB_PASSWORD environment variable required but not set (connection string contains placeholder)")
    MONGO_URL = MONGO_URL.replace("{MONGODB_PASSWORD}", mongodb_password)

# BLOCKCHAIN_ENGINE_URL is optional - data-chain is a storage service that doesn't directly call blockchain-engine
# The blockchain-engine would call data-chain, not the other way around
BLOCKCHAIN_ENGINE_URL = os.getenv("BLOCKCHAIN_ENGINE_URL")
if BLOCKCHAIN_ENGINE_URL:
    logger.info(f"Blockchain engine URL configured: {BLOCKCHAIN_ENGINE_URL}")
else:
    logger.warning("BLOCKCHAIN_ENGINE_URL not set - data-chain will operate in standalone mode")

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
            # Get connection pool settings from environment variables (aligned with blockchain-engine)
            server_selection_timeout_ms = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"))
            connect_timeout_ms = int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "10000"))
            socket_timeout_ms = int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "20000"))
            max_pool_size = int(os.getenv("MONGODB_MAX_POOL_SIZE", "50"))
            min_pool_size = int(os.getenv("MONGODB_MIN_POOL_SIZE", "5"))
            max_idle_time_ms = int(os.getenv("MONGODB_MAX_IDLE_TIME_MS", "30000"))
            retry_writes = os.getenv("MONGODB_RETRY_WRITES", "true").lower() in ("true", "1", "yes")
            retry_reads = os.getenv("MONGODB_RETRY_READS", "true").lower() in ("true", "1", "yes")
            
            # Create client with connection options (aligned with blockchain-engine)
            self.mongo_client = AsyncIOMotorClient(
                MONGO_URL,
                serverSelectionTimeoutMS=server_selection_timeout_ms,
                connectTimeoutMS=connect_timeout_ms,
                socketTimeoutMS=socket_timeout_ms,
                maxPoolSize=max_pool_size,
                minPoolSize=min_pool_size,
                maxIdleTimeMS=max_idle_time_ms,
                retryWrites=retry_writes,
                retryReads=retry_reads
            )
        
        # Extract database name from connection string or use environment variable, default to "lucid"
        # Parse database name from MONGO_URL if present, otherwise use env var or default
        database_name = os.getenv("MONGO_DB") or os.getenv("DATABASE_NAME") or os.getenv("DATA_CHAIN_DB_NAME", "lucid")
        
        # Try to extract database name from connection string
        try:
            from urllib.parse import urlparse
            parsed = urlparse(MONGO_URL)
            if parsed.path and parsed.path != "/":
                # Connection string has database in path (e.g., mongodb://host/dbname)
                db_from_url = parsed.path.lstrip("/").split("?")[0]
                if db_from_url:
                    database_name = db_from_url
        except Exception:
            # If parsing fails, use the database_name from env/default
            pass
        
        self.db: AsyncIOMotorDatabase = self.mongo_client.get_database(database_name)
        
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
    
    async def check_mongodb_connection(self) -> bool:
        """
        Check MongoDB connection health.
        
        Returns:
            True if MongoDB is accessible, False otherwise
        """
        try:
            await self.mongo_client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB connection check failed: {e}")
            return False
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get data chain service status.
        
        Returns:
            Dictionary with service status information
        """
        try:
            # Verify MongoDB connection
            mongodb_healthy = await self.check_mongodb_connection()
            
            if not mongodb_healthy:
                return {
                    "status": "unhealthy",
                    "service": "data-chain",
                    "error": "MongoDB connection failed",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Get deduplication stats
            dedup_stats = await self.deduplication_manager.get_deduplication_stats()
            
            # Get chunk count
            chunks = await self.chunk_manager.list_chunks(limit=1)
            total_chunks = await self.db.chunk_metadata.count_documents({})
            
            return {
                "status": "healthy",
                "service": "data-chain",
                "mongodb": "connected",
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

