#!/usr/bin/env python3
"""
LUCID Session Storage Service - Step 17 Implementation
Implements chunk persistence to filesystem and session metadata storage
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import aiofiles
import aiofiles.os
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import zstd

from ..core.session_orchestrator import SessionPipeline, PipelineStage

logger = logging.getLogger(__name__)

# Optional imports from recorder (lazy loading to avoid module initialization issues)
# Note: Module-level initialization in recorder tries to create directories which fails in read-only containers
try:
    from ..recorder.session_recorder import ChunkMetadata, RecordingSession
except (ImportError, OSError) as e:
    # Define minimal types if recorder module is not available or initialization fails
    logger.warning(f"Failed to import recorder module (will use graceful degradation): {e}")
    ChunkMetadata = None
    RecordingSession = None

@dataclass
class StorageConfig:
    """Storage configuration"""
    base_path: str = "/app/data/sessions"  # Default should match config default (volume mount: /app/data)
    chunk_size_mb: int = 10
    compression_level: int = 6
    encryption_enabled: bool = True
    retention_days: int = 30
    max_sessions: int = 1000
    cleanup_interval_hours: int = 24

@dataclass
class StorageMetrics:
    """Storage metrics"""
    total_sessions: int = 0
    total_chunks: int = 0
    total_size_bytes: int = 0
    available_space_bytes: int = 0
    compression_ratio: float = 0.0
    error_count: int = 0
    last_cleanup: Optional[datetime] = None

class SessionStorage:
    """
    Session storage service for Lucid RDP system.
    
    Handles chunk persistence to filesystem and session metadata storage in MongoDB.
    Implements SPEC-1B session storage requirements for Step 17.
    """
    
    def __init__(
        self,
        storage_config: StorageConfig,
        mongo_url: str | None = None,
        redis_url: str | None = None
    ):
        """Initialize SessionStorage with MongoDB and Redis URLs from environment"""
        # Get from environment if not provided
        if mongo_url is None:
            mongo_url = os.getenv("MONGODB_URL") or os.getenv("MONGO_URL")
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL")
        
        # Validate required environment variables
        if not mongo_url:
            raise ValueError("MONGODB_URL or MONGO_URL environment variable is required but not set")
        if "localhost" in mongo_url or "127.0.0.1" in mongo_url:
            raise ValueError("MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)")
        
        if not redis_url:
            raise ValueError("REDIS_URL environment variable is required but not set")
        if "localhost" in redis_url or "127.0.0.1" in redis_url:
            raise ValueError("REDIS_URL must not use localhost - use service name (e.g., lucid-redis)")
        self.config = storage_config
        self.base_path = Path(storage_config.base_path)
        # In read-only containers, parent directory (e.g., /app/data) should exist via volume mount
        # Check that parent directory exists (from volume mount), then create base_path if needed
        parent_path = self.base_path.parent
        if not parent_path.exists():
            raise OSError(
                f"Parent directory does not exist: {parent_path}. "
                f"This directory should be provided via a volume mount in docker-compose. "
                f"Check that the volume is mounted correctly at {parent_path}. "
                f"Storage base path would be: {self.base_path}"
            )
        # Create base_path if it doesn't exist (parent already exists from volume mount)
        # Handle permission errors gracefully (user 65532:65532 needs write access)
        try:
            self.base_path.mkdir(exist_ok=True)
        except PermissionError as e:
            raise PermissionError(
                f"Permission denied creating directory: {self.base_path}. "
                f"The container runs as user 65532:65532 and needs write access to the volume mount. "
                f"On the host, ensure the directory has correct permissions: "
                f"sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/session-api && "
                f"sudo chmod -R 755 /mnt/myssd/Lucid/Lucid/data/session-api. "
                f"Original error: {e}"
            )
        
        # MongoDB connection
        self.mongo_client = MongoClient(mongo_url)
        self.db: Database = self.mongo_client.lucid
        self.sessions_collection: Collection = self.db.sessions
        self.chunks_collection: Collection = self.db.chunks
        self.pipeline_collection: Collection = self.db.pipeline
        
        # Storage metrics
        self.metrics = StorageMetrics()
        
        # Initialize storage structure
        self._initialize_storage()
        
        logger.info(f"SessionStorage initialized with base path: {self.base_path}")
    
    def _initialize_storage(self):
        """Initialize storage directory structure"""
        directories = [
            "sessions",
            "chunks", 
            "metadata",
            "temp",
            "backup"
        ]
        
        for directory in directories:
            try:
                (self.base_path / directory).mkdir(exist_ok=True)
            except PermissionError as e:
                raise PermissionError(
                    f"Permission denied creating directory: {self.base_path / directory}. "
                    f"The container runs as user 65532:65532 and needs write access to the volume mount. "
                    f"On the host, ensure the directory has correct permissions: "
                    f"sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/session-api && "
                    f"sudo chmod -R 755 /mnt/myssd/Lucid/Lucid/data/session-api. "
                    f"Original error: {e}"
                )
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create MongoDB indexes for optimal performance"""
        try:
            # Sessions collection indexes
            self.sessions_collection.create_index("session_id", unique=True)
            self.sessions_collection.create_index("status")
            self.sessions_collection.create_index([("created_at", -1)])  # Descending index for sorting
            self.sessions_collection.create_index("metadata.project")
            self.sessions_collection.create_index("metadata.environment")
            self.sessions_collection.create_index("metadata.tags")
            
            # Chunks collection indexes
            self.chunks_collection.create_index("chunk_id", unique=True)
            self.chunks_collection.create_index([("session_id", 1), ("sequence_number", 1)])
            self.chunks_collection.create_index([("session_id", 1), ("timestamp", 1)])
            self.chunks_collection.create_index("status")
            self.chunks_collection.create_index("merkle_hash")
            self.chunks_collection.create_index([("created_at", -1)])  # Descending index for sorting
            
            # Pipeline collection indexes
            self.pipeline_collection.create_index("session_id", unique=True)
            self.pipeline_collection.create_index("pipeline_status")
            self.pipeline_collection.create_index([("updated_at", -1)])  # Descending index for sorting
            
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise  # Don't silently pass - index creation is critical
    
    async def store_session_metadata(self, session: RecordingSession) -> bool:
        """Store session metadata in MongoDB"""
        try:
            session_doc = {
                "session_id": session.session_id,
                "name": getattr(session, 'name', f"Session {session.session_id}"),
                "status": session.status.value,
                "created_at": session.started_at,
                "started_at": session.started_at,
                "stopped_at": session.stopped_at,
                "rdp_config": session.metadata.get('rdp_config', {}),
                "recording_config": session.metadata.get('recording_config', {}),
                "storage_config": session.metadata.get('storage_config', {}),
                "metadata": {
                    "project": session.metadata.get('project', 'lucid-rdp'),
                    "environment": session.metadata.get('environment', 'development'),
                    "tags": session.metadata.get('tags', []),
                    "description": session.metadata.get('description', ''),
                    "owner": session.metadata.get('owner', 'system'),
                    "priority": session.metadata.get('priority', 'normal')
                },
                "statistics": {
                    "duration_seconds": 0,
                    "chunks_count": session.chunks_created,
                    "size_bytes": session.total_chunk_size,
                    "frame_count": 0,
                    "dropped_frames": 0,
                    "error_count": 0,
                    "average_fps": 0.0,
                    "compression_ratio": 0.0
                },
                "updated_at": datetime.utcnow()
            }
            
            # Upsert session document
            result = self.sessions_collection.replace_one(
                {"session_id": session.session_id},
                session_doc,
                upsert=True
            )
            
            logger.info(f"Session metadata stored: {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store session metadata: {e}")
            self.metrics.error_count += 1
            return False
    
    async def store_chunk(
        self, 
        chunk: ChunkMetadata, 
        chunk_data: bytes,
        session_id: str
    ) -> Tuple[bool, str]:
        """
        Store chunk data to filesystem and metadata to MongoDB
        
        Returns:
            Tuple[bool, str]: (success, storage_path)
        """
        try:
            # Create session directory
            session_dir = self.base_path / "sessions" / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Compress chunk data
            try:
                compressed_data = zstd.compress(chunk_data, level=self.config.compression_level)
                compression_ratio = len(compressed_data) / len(chunk_data) if chunk_data else 0.0
            except zstd.error as e:
                logger.error(f"Compression failed for chunk {chunk.chunk_id}: {e}")
                # Fallback to uncompressed storage
                compressed_data = chunk_data
                compression_ratio = 1.0
            
            # Generate storage path
            chunk_filename = f"{chunk.chunk_id}.zstd"
            storage_path = session_dir / "chunks" / chunk_filename
            storage_path.parent.mkdir(exist_ok=True)
            
            # Write compressed data to filesystem
            async with aiofiles.open(storage_path, 'wb') as f:
                await f.write(compressed_data)
            
            # Store chunk metadata in MongoDB
            chunk_doc = {
                "chunk_id": chunk.chunk_id,
                "session_id": session_id,
                "sequence_number": chunk.chunk_index,
                "timestamp": chunk.timestamp,
                "status": "stored",
                "size_bytes": len(chunk_data),
                "compressed_size_bytes": len(compressed_data),
                "duration_seconds": 1.0,  # Default 1 second per chunk
                "frame_count": 30,  # Default 30 frames per chunk
                "merkle_hash": chunk.hash_sha256,
                "storage_path": str(storage_path),
                "compression_ratio": compression_ratio,
                "quality_score": chunk.quality_score,
                "encryption_key_id": None,  # TODO: Implement encryption
                "created_at": datetime.utcnow(),
                "processed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = self.chunks_collection.replace_one(
                {"chunk_id": chunk.chunk_id},
                chunk_doc,
                upsert=True
            )
            
            # Update metrics
            self.metrics.total_chunks += 1
            self.metrics.total_size_bytes += len(compressed_data)
            
            logger.info(f"Chunk stored: {chunk.chunk_id} -> {storage_path}")
            return True, str(storage_path)
            
        except Exception as e:
            logger.error(f"Failed to store chunk {chunk.chunk_id}: {e}")
            self.metrics.error_count += 1
            return False, ""
    
    async def retrieve_chunk(self, chunk_id: str, session_id: str) -> Optional[bytes]:
        """Retrieve chunk data from filesystem"""
        try:
            # Get chunk metadata
            chunk_doc = self.chunks_collection.find_one({
                "chunk_id": chunk_id,
                "session_id": session_id
            })
            
            if not chunk_doc:
                logger.warning(f"Chunk not found: {chunk_id}")
                return None
            
            storage_path = Path(chunk_doc["storage_path"])
            if not storage_path.exists():
                logger.warning(f"Chunk file not found: {storage_path}")
                return None
            
            # Read and decompress chunk data
            async with aiofiles.open(storage_path, 'rb') as f:
                compressed_data = await f.read()
            
            try:
                chunk_data = zstd.decompress(compressed_data)
            except zstd.error as e:
                logger.error(f"Decompression failed for chunk {chunk_id}: {e}")
                # Return compressed data as fallback
                chunk_data = compressed_data
            logger.info(f"Chunk retrieved: {chunk_id}")
            return chunk_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunk {chunk_id}: {e}")
            self.metrics.error_count += 1
            return None
    
    async def get_session_chunks(
        self, 
        session_id: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get chunks for a session with pagination"""
        try:
            cursor = self.chunks_collection.find(
                {"session_id": session_id}
            ).sort("sequence_number", 1).skip(offset).limit(limit)
            
            chunks = []
            async for chunk_doc in cursor:
                chunks.append({
                    "chunk_id": chunk_doc["chunk_id"],
                    "session_id": chunk_doc["session_id"],
                    "sequence_number": chunk_doc["sequence_number"],
                    "timestamp": chunk_doc["timestamp"],
                    "status": chunk_doc["status"],
                    "size_bytes": chunk_doc["size_bytes"],
                    "duration_seconds": chunk_doc["duration_seconds"],
                    "frame_count": chunk_doc["frame_count"],
                    "merkle_hash": chunk_doc.get("merkle_hash"),
                    "storage_path": chunk_doc.get("storage_path"),
                    "compression_ratio": chunk_doc.get("compression_ratio"),
                    "quality_score": chunk_doc.get("quality_score")
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get session chunks: {e}")
            return []
    
    async def update_session_statistics(self, session_id: str) -> bool:
        """Update session statistics from chunks"""
        try:
            # Aggregate chunk statistics
            pipeline = [
                {"$match": {"session_id": session_id}},
                {"$group": {
                    "_id": None,
                    "total_chunks": {"$sum": 1},
                    "total_size": {"$sum": "$size_bytes"},
                    "total_compressed_size": {"$sum": "$compressed_size_bytes"},
                    "avg_compression_ratio": {"$avg": "$compression_ratio"},
                    "avg_quality_score": {"$avg": "$quality_score"}
                }}
            ]
            
            result = list(self.chunks_collection.aggregate(pipeline))
            if not result:
                return False
            
            stats = result[0]
            compression_ratio = stats.get("avg_compression_ratio", 0.0)
            if stats.get("total_compressed_size", 0) > 0:
                compression_ratio = stats["total_compressed_size"] / stats["total_size"]
            
            # Update session statistics
            update_doc = {
                "statistics.chunks_count": stats["total_chunks"],
                "statistics.size_bytes": stats["total_size"],
                "statistics.compression_ratio": compression_ratio,
                "statistics.updated_at": datetime.utcnow()
            }
            
            self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": update_doc}
            )
            
            logger.info(f"Session statistics updated: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session statistics: {e}")
            return False
    
    async def cleanup_old_sessions(self) -> int:
        """Cleanup old sessions based on retention policy"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.config.retention_days)
            
            # Find old sessions
            old_sessions = self.sessions_collection.find({
                "created_at": {"$lt": cutoff_date},
                "status": {"$in": ["stopped", "completed", "failed"]}
            })
            
            deleted_count = 0
            for session in old_sessions:
                session_id = session["session_id"]
                
                # Delete chunks
                chunk_result = self.chunks_collection.delete_many({"session_id": session_id})
                
                # Delete session files
                session_dir = self.base_path / "sessions" / session_id
                if session_dir.exists():
                    shutil.rmtree(session_dir)
                
                # Delete session document
                self.sessions_collection.delete_one({"session_id": session_id})
                
                # Delete pipeline document
                self.pipeline_collection.delete_one({"session_id": session_id})
                
                deleted_count += 1
                logger.info(f"Cleaned up old session: {session_id}")
            
            self.metrics.last_cleanup = datetime.utcnow()
            logger.info(f"Cleanup completed: {deleted_count} sessions removed")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
    
    async def get_storage_metrics(self) -> Dict[str, Any]:
        """Get storage metrics"""
        try:
            # Get available space
            statvfs = os.statvfs(self.base_path)
            available_space = statvfs.f_frsize * statvfs.f_bavail
            
            # Get session count
            total_sessions = self.sessions_collection.count_documents({})
            active_sessions = self.sessions_collection.count_documents({
                "status": {"$in": ["recording", "processing"]}
            })
            
            # Get chunk count and total size
            chunk_stats = list(self.chunks_collection.aggregate([
                {"$group": {
                    "_id": None,
                    "total_chunks": {"$sum": 1},
                    "total_size": {"$sum": "$size_bytes"}
                }}
            ]))
            
            total_chunks = chunk_stats[0]["total_chunks"] if chunk_stats else 0
            total_size = chunk_stats[0]["total_size"] if chunk_stats else 0
            
            self.metrics.total_sessions = total_sessions
            self.metrics.total_chunks = total_chunks
            self.metrics.total_size_bytes = total_size
            self.metrics.available_space_bytes = available_space
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_chunks": total_chunks,
                "total_size_bytes": total_size,
                "available_space_bytes": available_space,
                "compression_ratio": self.metrics.compression_ratio,
                "error_count": self.metrics.error_count,
                "last_cleanup": self.metrics.last_cleanup
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage metrics: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            # Check MongoDB connection
            mongo_healthy = self.mongo_client.admin.command('ping')['ok'] == 1
            
            # Check storage space
            statvfs = os.statvfs(self.base_path)
            available_space = statvfs.f_frsize * statvfs.f_bavail
            storage_healthy = available_space > 1024 * 1024 * 1024  # 1GB minimum
            
            # Check storage directory
            storage_accessible = self.base_path.exists() and self.base_path.is_dir()
            
            return {
                "status": "healthy" if all([mongo_healthy, storage_healthy, storage_accessible]) else "unhealthy",
                "mongo_db": "healthy" if mongo_healthy else "unhealthy",
                "storage": "healthy" if storage_healthy else "unhealthy",
                "accessible": "healthy" if storage_accessible else "unhealthy",
                "available_space_bytes": available_space,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    async def close(self):
        """Close storage connections"""
        try:
            self.mongo_client.close()
            logger.info("SessionStorage connections closed")
        except Exception as e:
            logger.error(f"Failed to close storage connections: {e}")
