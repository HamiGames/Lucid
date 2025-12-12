"""
Data Storage Backend
Abstracts storage operations for data chunks

This module provides storage backend abstraction for data chunks,
supporting multiple storage backends (MongoDB, filesystem, S3, etc.).
"""

from __future__ import annotations

import os
import logging
import gzip
from typing import Dict, Any, Optional, List, BinaryIO
from pathlib import Path
from abc import ABC, abstractmethod

# Initialize logger first
logger = logging.getLogger(__name__)

# Optional compression libraries (gracefully handle if not available)
try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False
    logger.warning("lz4 not available, lz4 compression will be disabled")

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    logger.warning("zstandard not available, zstd compression will be disabled")

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..config.config import get_blockchain_config

# Environment variable configuration (required, no hardcoded defaults)
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL or MONGODB_URL environment variable not set")

# Storage configuration from environment
STORAGE_BACKEND = os.getenv("DATA_CHAIN_CHUNK_STORAGE_BACKEND", os.getenv("DATA_CHAIN_STORAGE_BACKEND", "mongodb")).lower()
COMPRESSION_ALGORITHM = os.getenv("DATA_CHAIN_CHUNK_COMPRESSION_ALGORITHM", os.getenv("DATA_CHAIN_COMPRESSION_ALGORITHM", "zstd")).lower()
CHUNK_STORAGE_PATH = os.getenv("DATA_CHAIN_CHUNK_STORAGE_PATH", os.getenv("CHUNK_STORAGE_PATH", "/data/chunks"))
STORE_METADATA = os.getenv("DATA_CHAIN_STORE_METADATA", "true").lower() in ("true", "1", "yes")
STORE_CONTENT = os.getenv("DATA_CHAIN_STORE_CONTENT", "true").lower() in ("true", "1", "yes")
STORE_HASHES = os.getenv("DATA_CHAIN_STORE_HASHES", "true").lower() in ("true", "1", "yes")


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def store_chunk(self, chunk_id: str, data: bytes, metadata: Dict[str, Any]) -> bool:
        """Store chunk data and metadata."""
        pass
    
    @abstractmethod
    async def retrieve_chunk(self, chunk_id: str) -> Optional[bytes]:
        """Retrieve chunk data."""
        pass
    
    @abstractmethod
    async def get_chunk_metadata(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get chunk metadata."""
        pass
    
    @abstractmethod
    async def delete_chunk(self, chunk_id: str) -> bool:
        """Delete chunk."""
        pass
    
    @abstractmethod
    async def list_chunks(self, session_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List chunks."""
        pass


class MongoDBStorageBackend(StorageBackend):
    """MongoDB storage backend for data chunks."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize MongoDB storage backend.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.chunks_collection = db.chunks
        self.metadata_collection = db.chunk_metadata
        
        # Get configuration
        config = get_blockchain_config()
        data_chain_config = config.get_data_chain_config()
        storage_config = data_chain_config.get("chunk_management", {}).get("storage", {})
        
        # Compression enabled from config or environment
        self.compression_enabled = os.getenv("DATA_CHAIN_COMPRESSION_ENABLED", str(storage_config.get("compression_enabled", True))).lower() in ("true", "1", "yes")
        self.compression_algorithm = COMPRESSION_ALGORITHM
        
        logger.info(f"MongoDBStorageBackend initialized with compression={self.compression_enabled}, algorithm={self.compression_algorithm}")
    
    def _compress(self, data: bytes) -> bytes:
        """Compress data using configured algorithm."""
        if not self.compression_enabled:
            return data
        
        if self.compression_algorithm == "gzip":
            return gzip.compress(data)
        elif self.compression_algorithm == "lz4":
            if not LZ4_AVAILABLE:
                logger.warning("lz4 compression requested but library not available, using gzip")
                return gzip.compress(data)
            return lz4.frame.compress(data)
        elif self.compression_algorithm == "zstd":
            if not ZSTD_AVAILABLE:
                logger.warning("zstd compression requested but library not available, using gzip")
                return gzip.compress(data)
            return zstd.compress(data)
        else:
            # Default to no compression
            return data
    
    def _decompress(self, data: bytes) -> bytes:
        """Decompress data using configured algorithm."""
        if not self.compression_enabled:
            return data
        
        if self.compression_algorithm == "gzip":
            return gzip.decompress(data)
        elif self.compression_algorithm == "lz4":
            if not LZ4_AVAILABLE:
                logger.warning("lz4 decompression requested but library not available, trying gzip")
                return gzip.decompress(data)
            return lz4.frame.decompress(data)
        elif self.compression_algorithm == "zstd":
            if not ZSTD_AVAILABLE:
                logger.warning("zstd decompression requested but library not available, trying gzip")
                return gzip.decompress(data)
            return zstd.decompress(data)
        else:
            # Assume no compression
            return data
    
    async def store_chunk(self, chunk_id: str, data: bytes, metadata: Dict[str, Any]) -> bool:
        """Store chunk in MongoDB."""
        try:
            # Compress data if enabled
            compressed_data = self._compress(data)
            
            # Store chunk content
            if STORE_CONTENT:
                chunk_doc = {
                    "_id": chunk_id,
                    "data": compressed_data,
                    "compressed": self.compression_enabled,
                    "compression_algorithm": self.compression_algorithm if self.compression_enabled else None,
                    "original_size": len(data),
                    "compressed_size": len(compressed_data),
                    "created_at": metadata.get("created_at")
                }
                await self.chunks_collection.replace_one(
                    {"_id": chunk_id},
                    chunk_doc,
                    upsert=True
                )
            
            # Store metadata
            if STORE_METADATA:
                metadata_doc = {
                    "_id": chunk_id,
                    **metadata
                }
                await self.metadata_collection.replace_one(
                    {"_id": chunk_id},
                    metadata_doc,
                    upsert=True
                )
            
            logger.debug(f"Stored chunk {chunk_id} in MongoDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store chunk {chunk_id} in MongoDB: {e}")
            return False
    
    async def retrieve_chunk(self, chunk_id: str) -> Optional[bytes]:
        """Retrieve chunk from MongoDB."""
        try:
            chunk_doc = await self.chunks_collection.find_one({"_id": chunk_id})
            if not chunk_doc:
                return None
            
            data = chunk_doc.get("data")
            if not data:
                return None
            
            # Decompress if needed
            if chunk_doc.get("compressed", False):
                data = self._decompress(data)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunk {chunk_id} from MongoDB: {e}")
            return None
    
    async def get_chunk_metadata(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get chunk metadata from MongoDB."""
        try:
            metadata_doc = await self.metadata_collection.find_one({"_id": chunk_id})
            if metadata_doc:
                metadata_doc.pop("_id", None)
            return metadata_doc
            
        except Exception as e:
            logger.error(f"Failed to get chunk metadata {chunk_id} from MongoDB: {e}")
            return None
    
    async def update_chunk_metadata(self, chunk_id: str, updates: Dict[str, Any]) -> bool:
        """Update chunk metadata."""
        try:
            result = await self.metadata_collection.update_one(
                {"_id": chunk_id},
                {"$set": updates}
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update chunk metadata {chunk_id}: {e}")
            return False
    
    async def delete_chunk(self, chunk_id: str) -> bool:
        """Delete chunk from MongoDB."""
        try:
            # Delete content
            if STORE_CONTENT:
                result1 = await self.chunks_collection.delete_one({"_id": chunk_id})
            
            # Delete metadata
            if STORE_METADATA:
                result2 = await self.metadata_collection.delete_one({"_id": chunk_id})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chunk {chunk_id} from MongoDB: {e}")
            return False
    
    async def list_chunks(self, session_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List chunks from MongoDB."""
        try:
            query = {}
            if session_id:
                query["session_id"] = session_id
            
            cursor = self.metadata_collection.find(query).skip(offset).limit(limit)
            chunks = await cursor.to_list(length=limit)
            
            # Remove _id from results
            for chunk in chunks:
                chunk.pop("_id", None)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to list chunks from MongoDB: {e}")
            return []


class DataStorage:
    """
    Data storage manager.
    
    Provides unified interface for data chunk storage operations,
    abstracting the underlying storage backend.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize data storage.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        
        # Initialize backend based on configuration
        if STORAGE_BACKEND == "mongodb":
            self.backend: StorageBackend = MongoDBStorageBackend(db)
        else:
            # Default to MongoDB
            logger.warning(f"Unknown storage backend {STORAGE_BACKEND}, defaulting to MongoDB")
            self.backend = MongoDBStorageBackend(db)
        
        logger.info(f"DataStorage initialized with backend={STORAGE_BACKEND}")
    
    async def store_chunk(self, chunk_id: str, data: bytes, metadata: Dict[str, Any]) -> bool:
        """Store chunk data and metadata."""
        return await self.backend.store_chunk(chunk_id, data, metadata)
    
    async def retrieve_chunk(self, chunk_id: str) -> Optional[bytes]:
        """Retrieve chunk data."""
        return await self.backend.retrieve_chunk(chunk_id)
    
    async def get_chunk_metadata(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get chunk metadata."""
        return await self.backend.get_chunk_metadata(chunk_id)
    
    async def update_chunk_metadata(self, chunk_id: str, updates: Dict[str, Any]) -> bool:
        """Update chunk metadata."""
        if isinstance(self.backend, MongoDBStorageBackend):
            return await self.backend.update_chunk_metadata(chunk_id, updates)
        return False
    
    async def delete_chunk(self, chunk_id: str) -> bool:
        """Delete chunk."""
        return await self.backend.delete_chunk(chunk_id)
    
    async def list_chunks(self, session_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List chunks."""
        return await self.backend.list_chunks(session_id, limit, offset)

