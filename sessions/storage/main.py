#!/usr/bin/env python3
"""
LUCID Session Storage Service - Main Entry Point
Step 17 Implementation: Session Storage & API
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .session_storage import SessionStorage, StorageConfig as StorageConfigDataclass, StorageMetrics
from .chunk_store import ChunkStore, ChunkStoreConfig
from .config import StorageConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global storage instances
session_storage: Optional[SessionStorage] = None
chunk_store: Optional[ChunkStore] = None
storage_config_manager: Optional[StorageConfigManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global session_storage, chunk_store, storage_config_manager
    
    # Startup
    logger.info("Starting Session Storage Service...")
    
    try:
        # Initialize configuration using Pydantic Settings
        storage_config_manager = StorageConfig()
        
        # Get configuration dictionaries for dataclass-based configs
        storage_config_dict = storage_config_manager.get_storage_config_dict()
        chunk_config_dict = storage_config_manager.get_chunk_store_config_dict()
        
        # Create dataclass-based configs (for backward compatibility with existing code)
        storage_config = StorageConfigDataclass(**storage_config_dict)
        chunk_config = ChunkStoreConfig(**chunk_config_dict)
        
        # Get database URLs from settings (already validated)
        mongo_url = storage_config_manager.settings.MONGODB_URL
        redis_url = storage_config_manager.settings.REDIS_URL
        
        # Initialize storage services
        session_storage = SessionStorage(storage_config, mongo_url, redis_url)
        chunk_store = ChunkStore(chunk_config)
        
        logger.info("Session Storage Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Session Storage Service: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Session Storage Service...")
        
        if session_storage:
            await session_storage.close()
        
        logger.info("Session Storage Service stopped")

# Create FastAPI application
app = FastAPI(
    title="LUCID Session Storage Service",
    description="Session storage and chunk management service for Lucid RDP system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (configured from environment)
# Parse CORS origins from environment (same logic as config, but read here for middleware setup)
cors_origins_str = os.getenv("CORS_ORIGINS", "*")
if cors_origins_str == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get session storage
def get_session_storage() -> SessionStorage:
    if session_storage is None:
        raise HTTPException(status_code=503, detail="Session storage not available")
    return session_storage

# Dependency to get chunk store
def get_chunk_store() -> ChunkStore:
    if chunk_store is None:
        raise HTTPException(status_code=503, detail="Chunk store not available")
    return chunk_store

@app.get("/health")
async def health_check(
    storage: SessionStorage = Depends(get_session_storage),
    chunk_store: ChunkStore = Depends(get_chunk_store)
):
    """Health check endpoint"""
    try:
        # Get health status from both services
        storage_health = await storage.health_check()
        chunk_health = await chunk_store.health_check()
        
        # Determine overall health
        overall_healthy = (
            storage_health.get("status") == "healthy" and
            chunk_health.get("status") == "healthy"
        )
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
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

@app.get("/metrics")
async def get_metrics(
    storage: SessionStorage = Depends(get_session_storage),
    chunk_store: ChunkStore = Depends(get_chunk_store)
):
    """Get storage metrics"""
    try:
        # Get metrics from both services
        storage_metrics = await storage.get_storage_metrics()
        chunk_stats = await chunk_store.get_storage_stats()
        
        return {
            "session_storage": storage_metrics,
            "chunk_store": chunk_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/chunks")
async def store_chunk(
    session_id: str,
    chunk_data: bytes,
    chunk_metadata: dict,
    background_tasks: BackgroundTasks,
    storage: SessionStorage = Depends(get_session_storage),
    chunk_store: ChunkStore = Depends(get_chunk_store)
):
    """Store a chunk for a session"""
    try:
        # Create ChunkMetadata object with safe timestamp parsing
        try:
            from ..recorder.session_recorder import ChunkMetadata
            from datetime import datetime
            
            # Safe timestamp parsing
            timestamp_str = chunk_metadata["timestamp"]
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError as e:
                logger.warning(f"Invalid timestamp format '{timestamp_str}', using current time: {e}")
                timestamp = datetime.utcnow()
            
            chunk = ChunkMetadata(
                chunk_id=chunk_metadata["chunk_id"],
                session_id=session_id,
                chunk_index=chunk_metadata["chunk_index"],
                size_bytes=len(chunk_data),
                hash_sha256=chunk_metadata["hash_sha256"],
                timestamp=timestamp,
                compressed=chunk_metadata.get("compressed", False),
                compression_ratio=chunk_metadata.get("compression_ratio", 0.0),
                quality_score=chunk_metadata.get("quality_score", 0.0)
            )
        except ImportError as e:
            logger.error(f"Failed to import ChunkMetadata: {e}")
            raise HTTPException(status_code=500, detail="Session recorder module not available")
        
        # Store chunk in chunk store
        success, storage_path, metadata = await chunk_store.store_chunk(
            session_id, chunk, chunk_data
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store chunk")
        
        # Store chunk in session storage
        success, storage_path = await storage.store_chunk(chunk, chunk_data, session_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store chunk metadata")
        
        # Update session statistics in background
        background_tasks.add_task(storage.update_session_statistics, session_id)
        
        return {
            "chunk_id": chunk.chunk_id,
            "session_id": session_id,
            "storage_path": storage_path,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to store chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/chunks/{chunk_id}")
async def get_chunk(
    session_id: str,
    chunk_id: str,
    chunk_store: ChunkStore = Depends(get_chunk_store)
):
    """Retrieve a chunk"""
    try:
        success, chunk_data, metadata = await chunk_store.retrieve_chunk(
            session_id, chunk_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        return {
            "chunk_id": chunk_id,
            "session_id": session_id,
            "data": chunk_data,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/chunks")
async def list_session_chunks(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    storage: SessionStorage = Depends(get_session_storage)
):
    """List chunks for a session"""
    try:
        chunks = await storage.get_session_chunks(session_id, limit, offset)
        
        return {
            "session_id": session_id,
            "chunks": chunks,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(chunks)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list session chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}/chunks/{chunk_id}")
async def delete_chunk(
    session_id: str,
    chunk_id: str,
    chunk_store: ChunkStore = Depends(get_chunk_store)
):
    """Delete a chunk"""
    try:
        success = await chunk_store.delete_chunk(session_id, chunk_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        return {
            "chunk_id": chunk_id,
            "session_id": session_id,
            "deleted": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}/chunks")
async def delete_session_chunks(
    session_id: str,
    chunk_store: ChunkStore = Depends(get_chunk_store)
):
    """Delete all chunks for a session"""
    try:
        deleted_count = await chunk_store.delete_session_chunks(session_id)
        
        return {
            "session_id": session_id,
            "deleted_chunks": deleted_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to delete session chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/archive")
async def archive_session(
    session_id: str,
    chunk_store: ChunkStore = Depends(get_chunk_store)
):
    """Archive session chunks"""
    try:
        success = await chunk_store.archive_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "archived": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/restore")
async def restore_session(
    session_id: str,
    chunk_store: ChunkStore = Depends(get_chunk_store)
):
    """Restore session from archive"""
    try:
        success = await chunk_store.restore_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session archive not found")
        
        return {
            "session_id": session_id,
            "restored": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup")
async def cleanup_storage(
    background_tasks: BackgroundTasks,
    storage: SessionStorage = Depends(get_session_storage),
    chunk_store: ChunkStore = Depends(get_chunk_store)
):
    """Trigger storage cleanup"""
    try:
        # Run cleanup tasks in background
        background_tasks.add_task(storage.cleanup_old_sessions)
        background_tasks.add_task(chunk_store.cleanup_temp_files)
        
        return {
            "cleanup_started": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Note: Entrypoint logic moved to entrypoint.py for distroless container compatibility
# This file is now used as the FastAPI application module only
