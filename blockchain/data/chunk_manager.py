"""
Chunk Manager
Handles data chunk creation, storage, and retrieval operations

This module manages data chunks for the data chain service, including
chunk creation, splitting, storage, and retrieval operations.
"""

from __future__ import annotations

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, BinaryIO
from datetime import datetime, timezone
from pathlib import Path
import uuid
import hashlib

import blake3

from motor.motor_asyncio import AsyncIOMotorDatabase
from ..config.config import get_blockchain_config
from .storage import DataStorage
from .deduplication import DeduplicationManager

logger = logging.getLogger(__name__)

# Environment variable configuration (required, no hardcoded defaults)
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL, MONGODB_URL, or MONGODB_URI environment variable not set")

# Chunk configuration from environment
CHUNK_SIZE_BYTES = int(os.getenv("DATA_CHAIN_CHUNK_SIZE_BYTES", os.getenv("CHUNK_SIZE_BYTES", "1048576")))  # 1MB default
MAX_CHUNK_SIZE_BYTES = int(os.getenv("DATA_CHAIN_MAX_CHUNK_SIZE_BYTES", os.getenv("MAX_CHUNK_SIZE_BYTES", "10485760")))  # 10MB
MIN_CHUNK_SIZE_BYTES = int(os.getenv("DATA_CHAIN_MIN_CHUNK_SIZE_BYTES", os.getenv("MIN_CHUNK_SIZE_BYTES", "1024")))  # 1KB
SPLIT_THRESHOLD_BYTES = int(os.getenv("DATA_CHAIN_SPLIT_THRESHOLD_BYTES", os.getenv("SPLIT_THRESHOLD_BYTES", "1048576")))  # 1MB
CHUNK_OVERLAP_BYTES = int(os.getenv("DATA_CHAIN_CHUNK_OVERLAP_BYTES", os.getenv("CHUNK_OVERLAP_BYTES", "0")))

# Hash algorithm from environment
HASH_ALGORITHM = os.getenv("DATA_CHAIN_HASH_ALGORITHM", os.getenv("ANCHORING_HASH_ALGORITHM", "BLAKE3")).upper()


class ChunkMetadata:
    """Metadata for a data chunk."""
    
    def __init__(
        self,
        chunk_id: str,
        session_id: Optional[str] = None,
        index: int = 0,
        size_bytes: int = 0,
        hash_value: str = "",
        previous_hash: Optional[str] = None,
        next_hash: Optional[str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.chunk_id = chunk_id
        self.session_id = session_id
        self.index = index
        self.size_bytes = size_bytes
        self.hash_value = hash_value
        self.previous_hash = previous_hash
        self.next_hash = next_hash
        self.created_at = created_at or datetime.now(timezone.utc)
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "session_id": self.session_id,
            "index": self.index,
            "size_bytes": self.size_bytes,
            "hash_value": self.hash_value,
            "previous_hash": self.previous_hash,
            "next_hash": self.next_hash,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


class ChunkManager:
    """
    Manages data chunk operations.
    
    Handles chunk creation, splitting, storage, retrieval, and linking.
    Integrates with storage backend and deduplication manager.
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        storage: DataStorage,
        deduplication_manager: Optional[DeduplicationManager] = None
    ):
        """
        Initialize chunk manager.
        
        Args:
            db: MongoDB database instance
            storage: Data storage backend
            deduplication_manager: Optional deduplication manager
        """
        self.db = db
        self.storage = storage
        self.deduplication_manager = deduplication_manager
        
        # Get configuration from YAML
        config = get_blockchain_config()
        data_chain_config = config.get_data_chain_config()
        chunk_config = data_chain_config.get("chunk_management", {})
        creation_config = chunk_config.get("creation", {})
        
        # Override with environment variables if provided
        self.auto_split = os.getenv("DATA_CHAIN_AUTO_SPLIT", str(creation_config.get("auto_split_large_data", True))).lower() in ("true", "1", "yes")
        self.preserve_boundaries = os.getenv("DATA_CHAIN_PRESERVE_BOUNDARIES", str(creation_config.get("preserve_boundaries", True))).lower() in ("true", "1", "yes")
        
        logger.info("ChunkManager initialized")
    
    def _compute_hash(self, data: bytes) -> str:
        """Compute hash of data using configured algorithm."""
        if HASH_ALGORITHM == "BLAKE3":
            hasher = blake3.blake3()
            hasher.update(data)
            return hasher.hexdigest()
        elif HASH_ALGORITHM == "SHA256":
            return hashlib.sha256(data).hexdigest()
        else:
            # Default to BLAKE3
            hasher = blake3.blake3()
            hasher.update(data)
            return hasher.hexdigest()
    
    async def create_chunk(
        self,
        data: bytes,
        session_id: Optional[str] = None,
        index: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChunkMetadata:
        """
        Create a new data chunk.
        
        Args:
            data: Chunk data bytes
            session_id: Optional session identifier
            index: Chunk index in sequence
            metadata: Optional chunk metadata
            
        Returns:
            ChunkMetadata object
        """
        try:
            # Validate chunk size
            if len(data) < MIN_CHUNK_SIZE_BYTES:
                raise ValueError(f"Chunk size {len(data)} bytes is below minimum {MIN_CHUNK_SIZE_BYTES} bytes")
            if len(data) > MAX_CHUNK_SIZE_BYTES:
                if self.auto_split:
                    # Split large chunks
                    return await self._split_and_create_chunks(data, session_id, index, metadata)
                else:
                    raise ValueError(f"Chunk size {len(data)} bytes exceeds maximum {MAX_CHUNK_SIZE_BYTES} bytes")
            
            # Compute hash
            hash_value = self._compute_hash(data)
            
            # Check for deduplication
            if self.deduplication_manager:
                existing_chunk = await self.deduplication_manager.find_duplicate(hash_value)
                if existing_chunk:
                    logger.info(f"Found duplicate chunk with hash {hash_value}, reusing existing chunk")
                    # Return reference to existing chunk
                    chunk_id = existing_chunk.get("chunk_id")
                    return ChunkMetadata(
                        chunk_id=chunk_id,
                        session_id=session_id,
                        index=index,
                        size_bytes=len(data),
                        hash_value=hash_value,
                        metadata=metadata
                    )
            
            # Create new chunk
            chunk_id = str(uuid.uuid4())
            chunk_metadata = ChunkMetadata(
                chunk_id=chunk_id,
                session_id=session_id,
                index=index,
                size_bytes=len(data),
                hash_value=hash_value,
                metadata=metadata
            )
            
            # Store chunk
            await self.storage.store_chunk(chunk_id, data, chunk_metadata.to_dict())
            
            # Register with deduplication manager
            if self.deduplication_manager:
                await self.deduplication_manager.register_chunk(chunk_id, hash_value, len(data))
            
            logger.info(f"Created chunk {chunk_id} with size {len(data)} bytes")
            return chunk_metadata
            
        except Exception as e:
            logger.error(f"Failed to create chunk: {e}")
            raise
    
    async def _split_and_create_chunks(
        self,
        data: bytes,
        session_id: Optional[str],
        start_index: int,
        metadata: Optional[Dict[str, Any]]
    ) -> ChunkMetadata:
        """
        Split large data into multiple chunks.
        
        Args:
            data: Data to split
            session_id: Session identifier
            start_index: Starting index for chunks
            metadata: Optional metadata
            
        Returns:
            First chunk metadata (chunks are linked)
        """
        chunks = []
        offset = 0
        index = start_index
        previous_hash = None
        
        while offset < len(data):
            # Calculate chunk size
            chunk_size = min(CHUNK_SIZE_BYTES, len(data) - offset)
            chunk_data = data[offset:offset + chunk_size]
            
            # Compute hash
            hash_value = self._compute_hash(chunk_data)
            
            # Create chunk
            chunk_id = str(uuid.uuid4())
            chunk_metadata = ChunkMetadata(
                chunk_id=chunk_id,
                session_id=session_id,
                index=start_index + index,
                size_bytes=len(chunk_data),
                hash_value=hash_value,
                previous_hash=previous_hash,
                metadata=metadata
            )
            
            # Store chunk
            await self.storage.store_chunk(chunk_id, chunk_data, chunk_metadata.to_dict())
            
            # Update previous chunk's next_hash
            if chunks:
                chunks[-1].next_hash = hash_value
                await self.storage.update_chunk_metadata(chunks[-1].chunk_id, {"next_hash": hash_value})
            
            chunks.append(chunk_metadata)
            previous_hash = hash_value
            offset += chunk_size
            index += 1
        
        logger.info(f"Split data into {len(chunks)} chunks")
        return chunks[0]  # Return first chunk
    
    async def get_chunk(self, chunk_id: str) -> Optional[bytes]:
        """
        Retrieve chunk data.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Chunk data bytes or None if not found
        """
        try:
            return await self.storage.retrieve_chunk(chunk_id)
        except Exception as e:
            logger.error(f"Failed to retrieve chunk {chunk_id}: {e}")
            return None
    
    async def get_chunk_metadata(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get chunk metadata.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Chunk metadata dictionary or None if not found
        """
        try:
            return await self.storage.get_chunk_metadata(chunk_id)
        except Exception as e:
            logger.error(f"Failed to get chunk metadata {chunk_id}: {e}")
            return None
    
    async def list_chunks(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List chunks with optional filtering.
        
        Args:
            session_id: Optional session identifier filter
            limit: Maximum number of chunks to return
            offset: Number of chunks to skip
            
        Returns:
            List of chunk metadata dictionaries
        """
        try:
            return await self.storage.list_chunks(session_id, limit, offset)
        except Exception as e:
            logger.error(f"Failed to list chunks: {e}")
            return []
    
    async def delete_chunk(self, chunk_id: str) -> bool:
        """
        Delete a chunk.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # Get metadata first
            metadata = await self.get_chunk_metadata(chunk_id)
            if not metadata:
                return False
            
            # Delete from storage
            deleted = await self.storage.delete_chunk(chunk_id)
            
            # Unregister from deduplication manager
            if self.deduplication_manager and deleted:
                await self.deduplication_manager.unregister_chunk(chunk_id, metadata.get("hash_value"))
            
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete chunk {chunk_id}: {e}")
            return False

