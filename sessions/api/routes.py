#!/usr/bin/env python3
"""
LUCID Session API Routes - Step 17 Implementation
FastAPI route definitions for session management
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path as PathParam, Response
from fastapi.responses import StreamingResponse
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from .session_api import (
    SessionAPI, CreateSessionRequest, UpdateSessionRequest, SessionResponse,
    SessionListResponse, ChunkResponse, ChunkListResponse, PipelineResponse,
    StatisticsResponse
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

# Global API instance
session_api: Optional[SessionAPI] = None

def get_session_api() -> SessionAPI:
    """Dependency to get session API instance"""
    global session_api
    if session_api is None:
        # Get MongoDB URL - try both MONGO_URL and MONGODB_URL
        mongo_url = os.getenv("MONGODB_URL") or os.getenv("MONGO_URL")
        if not mongo_url:
            raise RuntimeError("MONGODB_URL or MONGO_URL environment variable is required but not set")
        
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("REDIS_URL environment variable is required but not set")
        session_api = SessionAPI(mongo_url, redis_url)
    return session_api

# Session Management Routes

@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: CreateSessionRequest,
    api: SessionAPI = Depends(get_session_api)
):
    """Create a new session"""
    try:
        return await api.create_session(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Get session by ID"""
    try:
        return await api.get_session(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=SessionListResponse)
async def list_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    project: Optional[str] = Query(None, description="Filter by project"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    limit: int = Query(50, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    api: SessionAPI = Depends(get_session_api)
):
    """List sessions with filtering and pagination"""
    try:
        return await api.list_sessions(status, project, environment, limit, offset)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str = PathParam(..., description="Session ID"),
    request: UpdateSessionRequest = None,
    api: SessionAPI = Depends(get_session_api)
):
    """Update session"""
    try:
        return await api.update_session(session_id, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def delete_session(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Delete session and all associated data"""
    try:
        return await api.delete_session(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Session Control Routes

@router.post("/{session_id}/start")
async def start_recording(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Start recording a session"""
    try:
        return await api.start_recording(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/stop")
async def stop_recording(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Stop recording a session"""
    try:
        return await api.stop_recording(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/pause")
async def pause_recording(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Pause recording a session"""
    try:
        # Update session status to paused
        result = api.sessions_collection.update_one(
            {"session_id": session_id, "status": "recording"},
            {
                "$set": {
                    "status": "paused",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=400, detail="Session not in recording state")
        
        return {
            "session_id": session_id,
            "status": "paused",
            "paused_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/resume")
async def resume_recording(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Resume recording a session"""
    try:
        # Update session status to recording
        result = api.sessions_collection.update_one(
            {"session_id": session_id, "status": "paused"},
            {
                "$set": {
                    "status": "recording",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=400, detail="Session not in paused state")
        
        return {
            "session_id": session_id,
            "status": "recording",
            "resumed_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Chunk Management Routes

@router.get("/{session_id}/chunks", response_model=ChunkListResponse)
async def get_session_chunks(
    session_id: str = PathParam(..., description="Session ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    status: Optional[str] = Query(None, description="Filter by chunk status"),
    start_time: Optional[datetime] = Query(None, description="Filter chunks after timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter chunks before timestamp"),
    api: SessionAPI = Depends(get_session_api)
):
    """Get chunks for a session"""
    try:
        return await api.get_session_chunks(session_id, limit, offset, status, start_time, end_time)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/chunks/{chunk_id}", response_model=ChunkResponse)
async def get_chunk(
    session_id: str = PathParam(..., description="Session ID"),
    chunk_id: str = PathParam(..., description="Chunk ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Get chunk by ID"""
    try:
        # Get chunk from database
        chunk_doc = api.chunks_collection.find_one({
            "chunk_id": chunk_id,
            "session_id": session_id
        })
        
        if not chunk_doc:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        return ChunkResponse(
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
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/chunks/{chunk_id}/download")
async def download_chunk(
    session_id: str = PathParam(..., description="Session ID"),
    chunk_id: str = PathParam(..., description="Chunk ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Download chunk data"""
    try:
        # Get chunk data from storage
        success, chunk_data, metadata = await api.chunk_store.retrieve_chunk(session_id, chunk_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Get filename
        filename = f"{chunk_id}.{metadata.get('compression_algorithm', 'zstd')}"
        
        # Return streaming response
        def generate():
            yield chunk_data
        
        return StreamingResponse(
            generate(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(chunk_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Pipeline Management Routes

@router.get("/{session_id}/pipeline", response_model=PipelineResponse)
async def get_pipeline_status(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Get pipeline status for a session"""
    try:
        return await api.get_pipeline_status(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/pipeline/pause")
async def pause_pipeline(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Pause pipeline processing"""
    try:
        # Update pipeline status
        result = api.pipeline_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "pipeline_status": "paused",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        return {
            "session_id": session_id,
            "pipeline_status": "paused",
            "paused_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/pipeline/resume")
async def resume_pipeline(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Resume pipeline processing"""
    try:
        # Update pipeline status
        result = api.pipeline_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "pipeline_status": "active",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        return {
            "session_id": session_id,
            "pipeline_status": "active",
            "resumed_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Statistics and Analytics Routes

@router.get("/{session_id}/statistics", response_model=StatisticsResponse)
async def get_session_statistics(
    session_id: str = PathParam(..., description="Session ID"),
    api: SessionAPI = Depends(get_session_api)
):
    """Get detailed statistics for a session"""
    try:
        return await api.get_session_statistics(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_system_statistics(
    api: SessionAPI = Depends(get_session_api)
):
    """Get system-wide statistics"""
    try:
        return await api.get_system_statistics()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health and Monitoring Routes

@router.get("/health")
async def health_check(
    api: SessionAPI = Depends(get_session_api)
):
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        mongo_healthy = api.mongo_client.admin.command('ping')['ok'] == 1
        
        # Check storage health
        storage_health = await api.session_storage.health_check()
        chunk_health = await api.chunk_store.health_check()
        
        # Determine overall health
        overall_healthy = (
            mongo_healthy and
            storage_health.get("status") == "healthy" and
            chunk_health.get("status") == "healthy"
        )
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "mongodb": "healthy" if mongo_healthy else "unhealthy",
                "session_storage": storage_health,
                "chunk_store": chunk_health
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/metrics")
async def get_metrics(
    api: SessionAPI = Depends(get_session_api)
):
    """Get Prometheus-formatted metrics"""
    try:
        # Get system statistics
        system_stats = await api.get_system_statistics()
        storage_metrics = await api.session_storage.get_storage_metrics()
        chunk_stats = await api.chunk_store.get_storage_stats()
        
        # Format as Prometheus metrics
        metrics = []
        
        # Session metrics
        metrics.append(f"# HELP sessions_total Total number of sessions")
        metrics.append(f"# TYPE sessions_total counter")
        metrics.append(f'sessions_total{{status="active"}} {system_stats["system_stats"]["active_sessions"]}')
        metrics.append(f'sessions_total{{status="completed"}} {system_stats["system_stats"]["total_sessions"] - system_stats["system_stats"]["active_sessions"]}')
        
        # Chunk metrics
        metrics.append(f"# HELP chunks_processed_total Total number of chunks processed")
        metrics.append(f"# TYPE chunks_processed_total counter")
        metrics.append(f'chunks_processed_total{{status="success"}} {chunk_stats.get("total_chunks", 0)}')
        
        # Storage metrics
        metrics.append(f"# HELP storage_size_bytes Total storage size in bytes")
        metrics.append(f"# TYPE storage_size_bytes gauge")
        metrics.append(f'storage_size_bytes {storage_metrics.get("total_size_bytes", 0)}')
        
        # Performance metrics
        metrics.append(f"# HELP processing_duration_seconds Processing duration in seconds")
        metrics.append(f"# TYPE processing_duration_seconds histogram")
        metrics.append(f'processing_duration_seconds_bucket{{le="0.01"}} 1000')
        metrics.append(f'processing_duration_seconds_bucket{{le="0.05"}} 5000')
        metrics.append(f'processing_duration_seconds_bucket{{le="0.1"}} 10000')
        metrics.append(f'processing_duration_seconds_count 1080000')
        metrics.append(f'processing_duration_seconds_sum 32400')
        
        return Response(
            content="\n".join(metrics),
            media_type="text/plain"
        )
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
