#!/usr/bin/env python3
"""
LUCID Session Storage Service - SPEC-1B Implementation
Handles session data storage with MongoDB integration and compression
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, BinaryIO
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import bson
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
import redis.asyncio as redis
from pymongo.errors import DuplicateKeyError, OperationFailure
import gzip

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StorageConfig:
    """Storage service configuration"""
    mongodb_uri: str = "mongodb://localhost:27017/lucid_sessions"
    redis_url: str = "redis://localhost:6379/0"
    compression_enabled: bool = True
    compression_level: int = 6
    chunk_size_mb: int = 10
    max_session_duration_hours: int = 24
    cleanup_interval_hours: int = 6
    cache_ttl_seconds: int = 3600

@dataclass
class SessionDocument:
    """Session document structure"""
    session_id: str
    user_id: str
    created_at: datetime
    last_updated: datetime
    state: str
    config: Dict[str, Any]
    rdp_connection: Optional[Dict[str, Any]]
    chunks: List[Dict[str, Any]]
    merkle_tree: Optional[Dict[str, Any]]
    blockchain_anchor: Optional[Dict[str, Any]]
    metrics: Dict[str, Any]
    is_active: bool = True
    expires_at: Optional[datetime] = None

@dataclass
class ChunkDocument:
    """Chunk document structure"""
    chunk_id: str
    session_id: str
    sequence_number: int
    metadata: Dict[str, Any]
    data: bytes
    created_at: datetime
    expires_at: Optional[datetime] = None

class SessionStorageService:
    """
    LUCID Session Storage Service
    
    Handles session data storage with:
    1. MongoDB for persistent storage
    2. Redis for caching and session state
    3. Compression for data optimization
    4. Automatic cleanup of expired sessions
    """
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.mongodb_client: Optional[AsyncIOMotorClient] = None
        self.mongodb_db: Optional[AsyncIOMotorDatabase] = None
        self.sessions_collection: Optional[AsyncIOMotorCollection] = None
        self.chunks_collection: Optional[AsyncIOMotorCollection] = None
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
        
    async def initialize(self) -> bool:
        """
        Initialize storage connections
        
        Returns:
            success: True if initialization successful
        """
        try:
            logger.info("Initializing session storage service")
            
            # Initialize MongoDB connection
            await self._initialize_mongodb()
            
            # Initialize Redis connection
            await self._initialize_redis()
            
            # Create indexes
            await self._create_indexes()
            
            self.is_connected = True
            logger.info("Session storage service initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize session storage service: {e}")
            return False
    
    async def _initialize_mongodb(self):
        """Initialize MongoDB connection and collections"""
        try:
            self.mongodb_client = AsyncIOMotorClient(self.config.mongodb_uri)
            self.mongodb_db = self.mongodb_client.get_database()
            
            # Get collections
            self.sessions_collection = self.mongodb_db.sessions
            self.chunks_collection = self.mongodb_db.chunks
            
            # Test connection
            await self.mongodb_client.admin.command('ping')
            logger.info("MongoDB connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB: {e}")
            raise
    
    async def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.config.redis_url)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Session collection indexes
            await self.sessions_collection.create_index("session_id", unique=True)
            await self.sessions_collection.create_index("user_id")
            await self.sessions_collection.create_index("created_at")
            await self.sessions_collection.create_index("expires_at")
            await self.sessions_collection.create_index("is_active")
            await self.sessions_collection.create_index([("user_id", 1), ("is_active", 1)])
            
            # Chunks collection indexes
            await self.chunks_collection.create_index("chunk_id", unique=True)
            await self.chunks_collection.create_index("session_id")
            await self.chunks_collection.create_index("sequence_number")
            await self.chunks_collection.create_index("created_at")
            await self.chunks_collection.create_index("expires_at")
            await self.chunks_collection.create_index([("session_id", 1), ("sequence_number", 1)])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise
    
    async def store_session(self, session_doc: SessionDocument) -> bool:
        """
        Store session document
        
        Args:
            session_doc: Session document to store
            
        Returns:
            success: True if stored successfully
        """
        try:
            if not self.is_connected:
                raise ConnectionError("Storage service not initialized")
            
            # Convert to dict and handle datetime serialization
            session_dict = asdict(session_doc)
            session_dict["created_at"] = session_doc.created_at
            session_dict["last_updated"] = session_doc.last_updated
            
            # Set expiration time
            if session_doc.expires_at:
                session_dict["expires_at"] = session_doc.expires_at
            else:
                session_dict["expires_at"] = session_doc.created_at + timedelta(hours=self.config.max_session_duration_hours)
            
            # Store in MongoDB
            await self.sessions_collection.insert_one(session_dict)
            
            # Cache in Redis
            await self._cache_session(session_doc.session_id, session_dict)
            
            logger.info(f"Stored session {session_doc.session_id}")
            
            return True
            
        except DuplicateKeyError:
            logger.warning(f"Session {session_doc.session_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Failed to store session {session_doc.session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[SessionDocument]:
        """
        Retrieve session document
        
        Args:
            session_id: Session identifier
            
        Returns:
            session_doc: Session document or None if not found
        """
        try:
            if not self.is_connected:
                raise ConnectionError("Storage service not initialized")
            
            # Try Redis cache first
            cached_session = await self._get_cached_session(session_id)
            if cached_session:
                return self._dict_to_session_document(cached_session)
            
            # Get from MongoDB
            session_dict = await self.sessions_collection.find_one({"session_id": session_id})
            
            if session_dict:
                # Cache in Redis
                await self._cache_session(session_id, session_dict)
                
                return self._dict_to_session_document(session_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session document
        
        Args:
            session_id: Session identifier
            updates: Fields to update
            
        Returns:
            success: True if updated successfully
        """
        try:
            if not self.is_connected:
                raise ConnectionError("Storage service not initialized")
            
            # Add update timestamp
            updates["last_updated"] = datetime.utcnow()
            
            # Update in MongoDB
            result = await self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": updates}
            )
            
            if result.modified_count > 0:
                # Update cache
                await self._invalidate_session_cache(session_id)
                
                logger.debug(f"Updated session {session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    async def store_chunk(self, chunk_doc: ChunkDocument) -> bool:
        """
        Store chunk document
        
        Args:
            chunk_doc: Chunk document to store
            
        Returns:
            success: True if stored successfully
        """
        try:
            if not self.is_connected:
                raise ConnectionError("Storage service not initialized")
            
            # Compress chunk data if enabled
            chunk_data = chunk_doc.data
            if self.config.compression_enabled:
                chunk_data = gzip.compress(chunk_doc.data, compresslevel=self.config.compression_level)
            
            # Convert to dict
            chunk_dict = asdict(chunk_doc)
            chunk_dict["data"] = chunk_data
            chunk_dict["created_at"] = chunk_doc.created_at
            
            # Set expiration time
            if chunk_doc.expires_at:
                chunk_dict["expires_at"] = chunk_doc.expires_at
            else:
                chunk_dict["expires_at"] = chunk_doc.created_at + timedelta(hours=self.config.max_session_duration_hours)
            
            # Store in MongoDB
            await self.chunks_collection.insert_one(chunk_dict)
            
            logger.debug(f"Stored chunk {chunk_doc.chunk_id} for session {chunk_doc.session_id}")
            
            return True
            
        except DuplicateKeyError:
            logger.warning(f"Chunk {chunk_doc.chunk_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Failed to store chunk {chunk_doc.chunk_id}: {e}")
            return False
    
    async def get_chunk(self, chunk_id: str) -> Optional[ChunkDocument]:
        """
        Retrieve chunk document
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            chunk_doc: Chunk document or None if not found
        """
        try:
            if not self.is_connected:
                raise ConnectionError("Storage service not initialized")
            
            # Get from MongoDB
            chunk_dict = await self.chunks_collection.find_one({"chunk_id": chunk_id})
            
            if chunk_dict:
                # Decompress if needed
                chunk_data = chunk_dict["data"]
                if self.config.compression_enabled and len(chunk_data) > 0:
                    try:
                        chunk_data = gzip.decompress(chunk_data)
                    except:
                        # Data might not be compressed
                        pass
                
                return ChunkDocument(
                    chunk_id=chunk_dict["chunk_id"],
                    session_id=chunk_dict["session_id"],
                    sequence_number=chunk_dict["sequence_number"],
                    metadata=chunk_dict["metadata"],
                    data=chunk_data,
                    created_at=chunk_dict["created_at"],
                    expires_at=chunk_dict.get("expires_at")
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {e}")
            return None
    
    async def get_session_chunks(self, session_id: str, limit: int = 1000) -> List[ChunkDocument]:
        """
        Retrieve all chunks for a session
        
        Args:
            session_id: Session identifier
            limit: Maximum number of chunks to retrieve
            
        Returns:
            chunks: List of chunk documents
        """
        try:
            if not self.is_connected:
                raise ConnectionError("Storage service not initialized")
            
            # Get chunks from MongoDB
            cursor = self.chunks_collection.find(
                {"session_id": session_id}
            ).sort("sequence_number", 1).limit(limit)
            
            chunks = []
            async for chunk_dict in cursor:
                # Decompress if needed
                chunk_data = chunk_dict["data"]
                if self.config.compression_enabled and len(chunk_data) > 0:
                    try:
                        chunk_data = gzip.decompress(chunk_data)
                    except:
                        # Data might not be compressed
                        pass
                
                chunk_doc = ChunkDocument(
                    chunk_id=chunk_dict["chunk_id"],
                    session_id=chunk_dict["session_id"],
                    sequence_number=chunk_dict["sequence_number"],
                    metadata=chunk_dict["metadata"],
                    data=chunk_data,
                    created_at=chunk_dict["created_at"],
                    expires_at=chunk_dict.get("expires_at")
                )
                chunks.append(chunk_doc)
            
            logger.debug(f"Retrieved {len(chunks)} chunks for session {session_id}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get chunks for session {session_id}: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session and all associated chunks
        
        Args:
            session_id: Session identifier
            
        Returns:
            success: True if deleted successfully
        """
        try:
            if not self.is_connected:
                raise ConnectionError("Storage service not initialized")
            
            # Delete session chunks
            chunk_result = await self.chunks_collection.delete_many({"session_id": session_id})
            
            # Delete session
            session_result = await self.sessions_collection.delete_one({"session_id": session_id})
            
            # Remove from cache
            await self._invalidate_session_cache(session_id)
            
            logger.info(f"Deleted session {session_id} and {chunk_result.deleted_count} chunks")
            
            return session_result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> Dict[str, int]:
        """
        Cleanup expired sessions and chunks
        
        Returns:
            cleanup_stats: Statistics about cleanup operation
        """
        try:
            if not self.is_connected:
                raise ConnectionError("Storage service not initialized")
            
            current_time = datetime.utcnow()
            
            # Find expired sessions
            expired_sessions = await self.sessions_collection.find(
                {"expires_at": {"$lt": current_time}}
            ).to_list(length=None)
            
            expired_session_ids = [session["session_id"] for session in expired_sessions]
            
            # Delete expired chunks
            chunk_result = await self.chunks_collection.delete_many(
                {"session_id": {"$in": expired_session_ids}}
            )
            
            # Delete expired sessions
            session_result = await self.sessions_collection.delete_many(
                {"expires_at": {"$lt": current_time}}
            )
            
            # Cleanup cache
            for session_id in expired_session_ids:
                await self._invalidate_session_cache(session_id)
            
            stats = {
                "expired_sessions": session_result.deleted_count,
                "expired_chunks": chunk_result.deleted_count,
                "cleanup_time": current_time
            }
            
            logger.info(f"Cleanup completed: {stats['expired_sessions']} sessions, {stats['expired_chunks']} chunks")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return {"error": str(e)}
    
    async def get_session_statistics(self) -> Dict[str, Any]:
        """Get storage service statistics"""
        try:
            if not self.is_connected:
                raise ConnectionError("Storage service not initialized")
            
            # Get collection statistics
            sessions_count = await self.sessions_collection.count_documents({})
            chunks_count = await self.chunks_collection.count_documents({})
            active_sessions = await self.sessions_collection.count_documents({"is_active": True})
            
            # Get storage sizes
            sessions_stats = await self.sessions_collection.database.command("collStats", "sessions")
            chunks_stats = await self.chunks_collection.database.command("collStats", "chunks")
            
            return {
                "sessions": {
                    "total": sessions_count,
                    "active": active_sessions,
                    "size_bytes": sessions_stats.get("size", 0),
                    "storage_size_bytes": sessions_stats.get("storageSize", 0)
                },
                "chunks": {
                    "total": chunks_count,
                    "size_bytes": chunks_stats.get("size", 0),
                    "storage_size_bytes": chunks_stats.get("storageSize", 0)
                },
                "config": {
                    "compression_enabled": self.config.compression_enabled,
                    "compression_level": self.config.compression_level,
                    "max_session_duration_hours": self.config.max_session_duration_hours,
                    "cache_ttl_seconds": self.config.cache_ttl_seconds
                },
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {"error": str(e)}
    
    async def _cache_session(self, session_id: str, session_dict: Dict[str, Any]):
        """Cache session in Redis"""
        try:
            if self.redis_client:
                cache_key = f"session:{session_id}"
                cache_data = json.dumps(session_dict, default=str)
                await self.redis_client.setex(
                    cache_key,
                    self.config.cache_ttl_seconds,
                    cache_data
                )
        except Exception as e:
            logger.warning(f"Failed to cache session {session_id}: {e}")
    
    async def _get_cached_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session from Redis cache"""
        try:
            if self.redis_client:
                cache_key = f"session:{session_id}"
                cache_data = await self.redis_client.get(cache_key)
                if cache_data:
                    return json.loads(cache_data)
        except Exception as e:
            logger.warning(f"Failed to get cached session {session_id}: {e}")
        return None
    
    async def _invalidate_session_cache(self, session_id: str):
        """Invalidate session cache"""
        try:
            if self.redis_client:
                cache_key = f"session:{session_id}"
                await self.redis_client.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for session {session_id}: {e}")
    
    def _dict_to_session_document(self, session_dict: Dict[str, Any]) -> SessionDocument:
        """Convert dictionary to SessionDocument"""
        return SessionDocument(
            session_id=session_dict["session_id"],
            user_id=session_dict["user_id"],
            created_at=session_dict["created_at"],
            last_updated=session_dict["last_updated"],
            state=session_dict["state"],
            config=session_dict["config"],
            rdp_connection=session_dict.get("rdp_connection"),
            chunks=session_dict.get("chunks", []),
            merkle_tree=session_dict.get("merkle_tree"),
            blockchain_anchor=session_dict.get("blockchain_anchor"),
            metrics=session_dict.get("metrics", {}),
            is_active=session_dict.get("is_active", True),
            expires_at=session_dict.get("expires_at")
        )
    
    async def close(self):
        """Close storage connections"""
        try:
            if self.mongodb_client:
                self.mongodb_client.close()
            
            if self.redis_client:
                await self.redis_client.close()
            
            self.is_connected = False
            logger.info("Storage service connections closed")
            
        except Exception as e:
            logger.error(f"Failed to close storage connections: {e}")

# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize storage service
        config = StorageConfig(
            mongodb_uri="mongodb://localhost:27017/lucid_sessions",
            redis_url="redis://localhost:6379/0",
            compression_enabled=True,
            compression_level=6
        )
        
        storage = SessionStorageService(config)
        
        # Initialize
        success = await storage.initialize()
        print(f"Storage initialized: {success}")
        
        if success:
            # Create sample session
            session_doc = SessionDocument(
                session_id="session_123",
                user_id="user_456",
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                state="active",
                config={"chunk_size_mb": 10},
                rdp_connection={"host": "192.168.1.100"},
                chunks=[],
                merkle_tree=None,
                blockchain_anchor=None,
                metrics={"chunks_processed": 0}
            )
            
            # Store session
            stored = await storage.store_session(session_doc)
            print(f"Session stored: {stored}")
            
            # Retrieve session
            retrieved_session = await storage.get_session("session_123")
            print(f"Session retrieved: {retrieved_session.session_id if retrieved_session else None}")
            
            # Create sample chunk
            chunk_doc = ChunkDocument(
                chunk_id="chunk_1",
                session_id="session_123",
                sequence_number=1,
                metadata={"size": 1024, "compression_ratio": 2.5},
                data=b"Sample chunk data" * 100,
                created_at=datetime.utcnow()
            )
            
            # Store chunk
            chunk_stored = await storage.store_chunk(chunk_doc)
            print(f"Chunk stored: {chunk_stored}")
            
            # Get statistics
            stats = await storage.get_session_statistics()
            print(f"Storage statistics: {stats}")
            
            # Close connections
            await storage.close()
    
    asyncio.run(main())
