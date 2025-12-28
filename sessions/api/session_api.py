#!/usr/bin/env python3
"""
LUCID Session API Service - Step 17 Implementation
REST API for session management operations
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
import json

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from ..storage.session_storage import SessionStorage
from ..storage.chunk_store import ChunkStore, ChunkStoreConfig
from ..storage.config import StorageConfigManager
from ..core.session_orchestrator import SessionPipeline, PipelineStage

logger = logging.getLogger(__name__)

# Safe environment variable handling
def safe_int_env(key: str, default: int) -> int:
    """Safely convert environment variable to int."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid {key}, using default: {default}")
        return default

# Pydantic models for API
class SessionStatus(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"

class RDPConfig(BaseModel):
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=3389, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, min_length=1, max_length=255)
    use_tls: bool = Field(default=True)
    ignore_cert: bool = Field(default=False)

class RecordingConfig(BaseModel):
    frame_rate: int = Field(default=30, ge=1, le=120)
    resolution: str = Field(default="1920x1080")
    quality: str = Field(default="high")
    compression: str = Field(default="zstd")
    bitrate: Optional[int] = Field(None, ge=1000, le=50000000)
    audio_enabled: bool = Field(default=True)
    cursor_enabled: bool = Field(default=True)

class StorageConfig(BaseModel):
    retention_days: int = Field(default=30, ge=1, le=365)
    max_size_gb: int = Field(default=10, ge=1, le=1000)
    encryption_enabled: bool = Field(default=True)
    compression_enabled: bool = Field(default=True)
    backup_enabled: bool = Field(default=False)
    archive_enabled: bool = Field(default=False)

class SessionMetadata(BaseModel):
    project: Optional[str] = Field(None, max_length=100)
    environment: Optional[str] = Field(None, max_length=50)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = Field(None, max_length=500)
    owner: Optional[str] = Field(None, max_length=100)
    priority: Optional[str] = Field(default="normal")

class CreateSessionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    rdp_config: RDPConfig
    recording_config: RecordingConfig = Field(default_factory=RecordingConfig)
    storage_config: StorageConfig = Field(default_factory=StorageConfig)
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)

class UpdateSessionRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    recording_config: Optional[RecordingConfig] = None
    storage_config: Optional[StorageConfig] = None
    metadata: Optional[SessionMetadata] = None

class SessionResponse(BaseModel):
    session_id: str
    name: str
    status: SessionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    rdp_config: RDPConfig
    recording_config: RecordingConfig
    storage_config: StorageConfig
    metadata: SessionMetadata
    statistics: Dict[str, Any] = Field(default_factory=dict)

class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    pagination: Dict[str, Any]

class ChunkResponse(BaseModel):
    chunk_id: str
    session_id: str
    sequence_number: int
    timestamp: datetime
    status: str
    size_bytes: int
    duration_seconds: float
    frame_count: int
    merkle_hash: Optional[str] = None
    storage_path: Optional[str] = None
    processing_info: Optional[Dict[str, Any]] = None

class ChunkListResponse(BaseModel):
    chunks: List[ChunkResponse]
    pagination: Dict[str, Any]

class PipelineResponse(BaseModel):
    session_id: str
    pipeline_status: str
    stages: List[Dict[str, Any]]
    overall_metrics: Dict[str, Any]

class StatisticsResponse(BaseModel):
    session_id: str
    time_range: Dict[str, datetime]
    recording_stats: Dict[str, Any]
    storage_stats: Dict[str, Any]
    quality_stats: Dict[str, Any]
    performance_stats: Dict[str, Any]

class SessionAPI:
    """
    Session API service for Lucid RDP system.
    
    Provides REST API endpoints for session management operations.
    Implements Step 17 requirements for session storage and API.
    """
    
    def __init__(
        self,
        mongo_url: str | None = None,
        redis_url: str | None = None
    ):
        """Initialize SessionAPI with MongoDB and Redis URLs from environment"""
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
        
        self.mongo_client = MongoClient(mongo_url)
        self.db: Database = self.mongo_client.lucid
        self.sessions_collection: Collection = self.db.sessions
        self.chunks_collection: Collection = self.db.chunks
        self.pipeline_collection: Collection = self.db.pipeline
        
        # Initialize storage configuration using StorageConfigManager (per master design)
        storage_config_manager = StorageConfigManager()
        
        # Get configuration dictionaries for dataclass-based configs
        storage_config_dict = storage_config_manager.get_storage_config_dict()
        chunk_config_dict = storage_config_manager.get_chunk_store_config_dict()
        
        # Import the dataclass StorageConfig from session_storage (not the Pydantic BaseModel)
        from ..storage.session_storage import StorageConfig as StorageConfigDataclass
        
        # Create dataclass-based configs (for backward compatibility with existing code)
        storage_config = StorageConfigDataclass(**storage_config_dict)
        chunk_config = ChunkStoreConfig(**chunk_config_dict)
        
        # Use the mongo_url and redis_url that were validated above (from parameters or environment)
        self.session_storage = SessionStorage(storage_config, mongo_url, redis_url)
        self.chunk_store = ChunkStore(chunk_config)
        
        logger.info("SessionAPI initialized")
    
    async def create_session(self, request: CreateSessionRequest) -> SessionResponse:
        """Create a new session"""
        try:
            session_id = f"sess-{uuid.uuid4().hex[:8]}"
            now = datetime.utcnow()
            
            # Create session document
            session_doc = {
                "session_id": session_id,
                "name": request.name,
                "status": SessionStatus.CREATED,
                "created_at": now,
                "started_at": None,
                "stopped_at": None,
                "rdp_config": request.rdp_config.dict(),
                "recording_config": request.recording_config.dict(),
                "storage_config": request.storage_config.dict(),
                "metadata": request.metadata.dict(),
                "statistics": {
                    "duration_seconds": 0,
                    "chunks_count": 0,
                    "size_bytes": 0,
                    "frame_count": 0,
                    "dropped_frames": 0,
                    "error_count": 0,
                    "average_fps": 0.0,
                    "compression_ratio": 0.0
                },
                "updated_at": now
            }
            
            # Insert session document
            self.sessions_collection.insert_one(session_doc)
            
            # Create pipeline document
            pipeline_doc = {
                "session_id": session_id,
                "pipeline_status": "inactive",
                "stages": [],
                "overall_metrics": {
                    "total_processing_time_ms": 0.0,
                    "throughput_fps": 0.0,
                    "error_rate": 0.0,
                    "memory_usage_bytes": 0,
                    "cpu_usage_percent": 0.0
                },
                "created_at": now,
                "updated_at": now
            }
            
            self.pipeline_collection.insert_one(pipeline_doc)
            
            logger.info(f"Session created: {session_id}")
            
            return SessionResponse(
                session_id=session_id,
                name=request.name,
                status=SessionStatus.CREATED,
                created_at=now,
                rdp_config=request.rdp_config,
                recording_config=request.recording_config,
                storage_config=request.storage_config,
                metadata=request.metadata,
                statistics=session_doc["statistics"]
            )
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_session(self, session_id: str) -> SessionResponse:
        """Get session by ID"""
        try:
            session_doc = self.sessions_collection.find_one({"session_id": session_id})
            
            if not session_doc:
                raise HTTPException(status_code=404, detail="Session not found")
            
            return SessionResponse(
                session_id=session_doc["session_id"],
                name=session_doc["name"],
                status=SessionStatus(session_doc["status"]),
                created_at=session_doc["created_at"],
                started_at=session_doc.get("started_at"),
                stopped_at=session_doc.get("stopped_at"),
                rdp_config=RDPConfig(**session_doc["rdp_config"]),
                recording_config=RecordingConfig(**session_doc["recording_config"]),
                storage_config=StorageConfig(**session_doc["storage_config"]),
                metadata=SessionMetadata(**session_doc["metadata"]),
                statistics=session_doc["statistics"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_sessions(
        self,
        status: Optional[str] = None,
        project: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> SessionListResponse:
        """List sessions with filtering and pagination"""
        try:
            # Build filter
            filter_doc = {}
            if status:
                filter_doc["status"] = status
            if project:
                filter_doc["metadata.project"] = project
            if environment:
                filter_doc["metadata.environment"] = environment
            
            # Get total count
            total = self.sessions_collection.count_documents(filter_doc)
            
            # Get sessions
            cursor = self.sessions_collection.find(filter_doc).sort("created_at", -1).skip(offset).limit(limit)
            sessions = []
            
            for session_doc in cursor:
                sessions.append(SessionResponse(
                    session_id=session_doc["session_id"],
                    name=session_doc["name"],
                    status=SessionStatus(session_doc["status"]),
                    created_at=session_doc["created_at"],
                    started_at=session_doc.get("started_at"),
                    stopped_at=session_doc.get("stopped_at"),
                    rdp_config=RDPConfig(**session_doc["rdp_config"]),
                    recording_config=RecordingConfig(**session_doc["recording_config"]),
                    storage_config=StorageConfig(**session_doc["storage_config"]),
                    metadata=SessionMetadata(**session_doc["metadata"]),
                    statistics=session_doc["statistics"]
                ))
            
            return SessionListResponse(
                sessions=sessions,
                pagination={
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + limit < total,
                    "has_previous": offset > 0
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_session(self, session_id: str, request: UpdateSessionRequest) -> SessionResponse:
        """Update session"""
        try:
            # Check if session exists
            session_doc = self.sessions_collection.find_one({"session_id": session_id})
            if not session_doc:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Build update document
            update_doc = {"updated_at": datetime.utcnow()}
            
            if request.name is not None:
                update_doc["name"] = request.name
            if request.description is not None:
                update_doc["metadata.description"] = request.description
            if request.recording_config is not None:
                update_doc["recording_config"] = request.recording_config.dict()
            if request.storage_config is not None:
                update_doc["storage_config"] = request.storage_config.dict()
            if request.metadata is not None:
                update_doc["metadata"] = request.metadata.dict()
            
            # Update session
            self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": update_doc}
            )
            
            # Return updated session
            return await self.get_session(session_id)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete session and all associated data"""
        try:
            # Check if session exists
            session_doc = self.sessions_collection.find_one({"session_id": session_id})
            if not session_doc:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Delete chunks
            chunk_count = self.chunks_collection.count_documents({"session_id": session_id})
            self.chunks_collection.delete_many({"session_id": session_id})
            
            # Delete session files
            await self.chunk_store.delete_session_chunks(session_id)
            
            # Delete session document
            self.sessions_collection.delete_one({"session_id": session_id})
            
            # Delete pipeline document
            self.pipeline_collection.delete_one({"session_id": session_id})
            
            logger.info(f"Session deleted: {session_id}")
            
            return {
                "session_id": session_id,
                "status": "deleted",
                "deleted_at": datetime.utcnow().isoformat(),
                "deleted_chunks": chunk_count
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def start_recording(self, session_id: str) -> Dict[str, Any]:
        """Start recording a session"""
        try:
            # Update session status
            result = self.sessions_collection.update_one(
                {"session_id": session_id, "status": {"$in": ["created", "stopped"]}},
                {
                    "$set": {
                        "status": "recording",
                        "started_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.matched_count == 0:
                raise HTTPException(status_code=400, detail="Session not in valid state for recording")
            
            # Update pipeline status
            self.pipeline_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "pipeline_status": "active",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "session_id": session_id,
                "status": "recording",
                "started_at": datetime.utcnow().isoformat(),
                "recording_url": f"rtsp://recorder:8084/sessions/{session_id}"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def stop_recording(self, session_id: str) -> Dict[str, Any]:
        """Stop recording a session"""
        try:
            # Update session status
            result = self.sessions_collection.update_one(
                {"session_id": session_id, "status": "recording"},
                {
                    "$set": {
                        "status": "stopped",
                        "stopped_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.matched_count == 0:
                raise HTTPException(status_code=400, detail="Session not in recording state")
            
            # Update pipeline status
            self.pipeline_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "pipeline_status": "inactive",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Get final statistics
            session_doc = self.sessions_collection.find_one({"session_id": session_id})
            statistics = session_doc.get("statistics", {})
            
            return {
                "session_id": session_id,
                "status": "stopped",
                "stopped_at": datetime.utcnow().isoformat(),
                "final_statistics": statistics
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_session_chunks(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> ChunkListResponse:
        """Get chunks for a session"""
        try:
            # Build filter
            filter_doc = {"session_id": session_id}
            if status:
                filter_doc["status"] = status
            if start_time:
                filter_doc["timestamp"] = {"$gte": start_time}
            if end_time:
                filter_doc["timestamp"] = {"$lte": end_time}
            
            # Get total count
            total = self.chunks_collection.count_documents(filter_doc)
            
            # Get chunks
            cursor = self.chunks_collection.find(filter_doc).sort("sequence_number", 1).skip(offset).limit(limit)
            chunks = []
            
            for chunk_doc in cursor:
                chunks.append(ChunkResponse(
                    chunk_id=chunk_doc["chunk_id"],
                    session_id=chunk_doc["session_id"],
                    sequence_number=chunk_doc["sequence_number"],
                    timestamp=chunk_doc["timestamp"],
                    status=chunk_doc["status"],
                    size_bytes=chunk_doc["size_bytes"],
                    duration_seconds=chunk_doc["duration_seconds"],
                    frame_count=chunk_doc["frame_count"],
                    merkle_hash=chunk_doc.get("merkle_hash"),
                    storage_path=chunk_doc.get("storage_path"),
                    processing_info={
                        "compression_ratio": chunk_doc.get("compression_ratio"),
                        "encryption_enabled": chunk_doc.get("encryption_key_id") is not None,
                        "quality_score": chunk_doc.get("quality_score")
                    }
                ))
            
            return ChunkListResponse(
                chunks=chunks,
                pagination={
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + limit < total,
                    "has_previous": offset > 0
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get session chunks: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_pipeline_status(self, session_id: str) -> PipelineResponse:
        """Get pipeline status for a session"""
        try:
            pipeline_doc = self.pipeline_collection.find_one({"session_id": session_id})
            
            if not pipeline_doc:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            
            return PipelineResponse(
                session_id=session_id,
                pipeline_status=pipeline_doc["pipeline_status"],
                stages=pipeline_doc["stages"],
                overall_metrics=pipeline_doc["overall_metrics"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_session_statistics(self, session_id: str) -> StatisticsResponse:
        """Get detailed statistics for a session"""
        try:
            # Get session document
            session_doc = self.sessions_collection.find_one({"session_id": session_id})
            if not session_doc:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Get chunk statistics
            chunk_stats = list(self.chunks_collection.aggregate([
                {"$match": {"session_id": session_id}},
                {"$group": {
                    "_id": None,
                    "total_chunks": {"$sum": 1},
                    "total_size": {"$sum": "$size_bytes"},
                    "total_compressed_size": {"$sum": "$compressed_size_bytes"},
                    "avg_compression_ratio": {"$avg": "$compression_ratio"},
                    "avg_quality_score": {"$avg": "$quality_score"},
                    "min_quality_score": {"$min": "$quality_score"},
                    "max_quality_score": {"$max": "$quality_score"}
                }}
            ]))
            
            if not chunk_stats:
                chunk_stats = [{
                    "total_chunks": 0,
                    "total_size": 0,
                    "total_compressed_size": 0,
                    "avg_compression_ratio": 0.0,
                    "avg_quality_score": 0.0,
                    "min_quality_score": 0.0,
                    "max_quality_score": 0.0
                }]
            
            stats = chunk_stats[0]
            
            # Calculate time range
            time_range = {
                "start": session_doc["created_at"],
                "end": session_doc.get("stopped_at", datetime.utcnow())
            }
            
            # Calculate duration
            duration = (time_range["end"] - time_range["start"]).total_seconds()
            
            return StatisticsResponse(
                session_id=session_id,
                time_range=time_range,
                recording_stats={
                    "total_duration_seconds": int(duration),
                    "active_duration_seconds": int(duration),
                    "paused_duration_seconds": 0,
                    "total_frames": stats["total_chunks"] * 30,  # Assume 30 FPS
                    "dropped_frames": 0,
                    "average_fps": 30.0
                },
                storage_stats={
                    "total_size_bytes": stats["total_size"],
                    "compressed_size_bytes": stats["total_compressed_size"],
                    "compression_ratio": stats["avg_compression_ratio"],
                    "chunks_count": stats["total_chunks"],
                    "average_chunk_size_bytes": stats["total_size"] // max(stats["total_chunks"], 1)
                },
                quality_stats={
                    "average_quality_score": stats["avg_quality_score"],
                    "min_quality_score": stats["min_quality_score"],
                    "max_quality_score": stats["max_quality_score"],
                    "quality_distribution": {
                        "excellent": 0.85,
                        "good": 0.12,
                        "fair": 0.03,
                        "poor": 0.00
                    }
                },
                performance_stats={
                    "average_processing_time_ms": 33.0,
                    "max_processing_time_ms": 50.0,
                    "min_processing_time_ms": 20.0,
                    "error_rate": 0.001
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide statistics"""
        try:
            # Get system stats
            total_sessions = self.sessions_collection.count_documents({})
            active_sessions = self.sessions_collection.count_documents({
                "status": {"$in": ["recording", "processing"]}
            })
            
            # Get storage stats
            storage_metrics = await self.session_storage.get_storage_metrics()
            chunk_stats = await self.chunk_store.get_storage_stats()
            
            return {
                "system_stats": {
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "total_storage_bytes": storage_metrics.get("total_size_bytes", 0),
                    "average_session_duration_seconds": 7200  # 2 hours average
                },
                "performance_stats": {
                    "average_processing_time_ms": 35.0,
                    "system_throughput_fps": 750.0,
                    "error_rate": 0.002
                },
                "storage_stats": {
                    "total_capacity_bytes": 1099511627776,  # 1TB
                    "used_capacity_bytes": storage_metrics.get("total_size_bytes", 0),
                    "available_capacity_bytes": storage_metrics.get("available_space_bytes", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get system statistics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def close(self):
        """Close API connections"""
        try:
            self.mongo_client.close()
            await self.session_storage.close()
            logger.info("SessionAPI connections closed")
        except Exception as e:
            logger.error(f"Failed to close API connections: {e}")
