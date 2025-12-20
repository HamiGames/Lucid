#!/usr/bin/env python3
"""
Lucid Session Management Recorder Service
Main entry point for the session recorder service
"""

import asyncio
import signal
import sys
import logging
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .session_recorder import SessionRecorder, RecordingStatus
from .chunk_generator import ChunkProcessor, ChunkConfig
from .compression import CompressionManager

# Global instances
session_recorder: Optional[SessionRecorder] = None
chunk_processor: Optional[ChunkProcessor] = None
compression_manager: Optional[CompressionManager] = None

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger = logging.getLogger(__name__)
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global session_recorder, chunk_processor, compression_manager
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Lucid Session Recorder Service")
    
    try:
        # Initialize components
        session_recorder = SessionRecorder()
        chunk_processor = ChunkProcessor(ChunkConfig())
        compression_manager = CompressionManager(default_level=6)
        
        # Setup signal handlers
        setup_signal_handlers()
        
        logger.info("Session Recorder Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Session Recorder Service: {str(e)}")
        raise
    finally:
        # Cleanup
        if chunk_processor:
            await chunk_processor.cleanup_all_sessions()
        
        logger.info("Session Recorder Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lucid Session Recorder API",
    description="Session recording and chunk generation service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "LUCID_ERR_5000",
                "message": "Internal server error",
                "details": str(exc) if app.debug else "An unexpected error occurred"
            }
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global session_recorder, chunk_processor, compression_manager
    
    if not all([session_recorder, chunk_processor, compression_manager]):
        raise HTTPException(status_code=503, detail="Service not fully initialized")
    
    try:
        # Get basic health information
        active_recordings = len(session_recorder.active_recordings)
        chunk_stats = chunk_processor.get_all_statistics()
        compression_stats = compression_manager.get_statistics()
        
        return {
            "status": "healthy",
            "service": "lucid-session-recorder",
            "version": "1.0.0",
            "active_recordings": active_recordings,
            "total_sessions_with_chunks": len(chunk_stats),
            "compression_stats": {
                "total_compressions": compression_stats["total_compressions"],
                "total_decompressions": compression_stats["total_decompressions"]
            },
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Health check failed")

@app.get("/status")
async def get_service_status():
    """Get detailed service status"""
    global session_recorder, chunk_processor, compression_manager
    
    if not all([session_recorder, chunk_processor, compression_manager]):
        raise HTTPException(status_code=503, detail="Service not fully initialized")
    
    try:
        # Get detailed status information
        recordings = []
        for recording in session_recorder.active_recordings.values():
            recordings.append({
                "session_id": recording.session_id,
                "owner_address": recording.owner_address,
                "status": recording.status.value,
                "started_at": recording.started_at.isoformat(),
                "chunks_created": recording.chunks_created,
                "total_chunk_size": recording.total_chunk_size
            })
        
        chunk_stats = chunk_processor.get_all_statistics()
        compression_stats = compression_manager.get_statistics()
        
        return {
            "service": "lucid-session-recorder",
            "status": "running",
            "active_recordings": recordings,
            "total_recordings": len(recordings),
            "chunk_statistics": chunk_stats,
            "compression_statistics": compression_stats,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Status check failed")

@app.post("/recordings/start")
async def start_recording(session_id: str, owner_address: str, metadata: dict = None):
    """Start session recording with chunk generation"""
    global session_recorder, chunk_processor
    
    if not session_recorder or not chunk_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Start recording
        result = await session_recorder.start_recording(
            session_id=session_id,
            owner_address=owner_address,
            metadata=metadata or {}
        )
        
        # Initialize chunk generation
        await chunk_processor.get_or_create_generator(session_id)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Started recording with chunk generation for session {session_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to start recording for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start recording")

@app.post("/recordings/{session_id}/stop")
async def stop_recording(session_id: str):
    """Stop session recording and finalize chunks"""
    global session_recorder, chunk_processor
    
    if not session_recorder or not chunk_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Stop recording
        result = await session_recorder.stop_recording(session_id)
        
        # Finalize chunk generation
        final_chunks = await chunk_processor.finalize_session(session_id)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Stopped recording and generated {len(final_chunks)} final chunks for session {session_id}")
        
        # Add chunk information to result
        result["final_chunks"] = len(final_chunks)
        result["chunk_metadata"] = [
            {
                "chunk_id": chunk.chunk_id,
                "size_bytes": chunk.size_bytes,
                "compression_ratio": chunk.compression_ratio,
                "quality_score": chunk.quality_score
            }
            for chunk in final_chunks
        ]
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to stop recording for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to stop recording")

@app.get("/recordings/{session_id}")
async def get_recording(session_id: str):
    """Get recording information with chunk statistics"""
    global session_recorder, chunk_processor
    
    if not session_recorder or not chunk_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Get recording information
        if session_id not in session_recorder.active_recordings:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        recording = session_recorder.active_recordings[session_id]
        
        # Get chunk statistics
        chunk_stats = await chunk_processor.get_session_statistics(session_id)
        
        result = {
            "session_id": recording.session_id,
            "owner_address": recording.owner_address,
            "status": recording.status.value,
            "started_at": recording.started_at.isoformat(),
            "stopped_at": recording.stopped_at.isoformat() if recording.stopped_at else None,
            "output_path": str(recording.output_path) if recording.output_path else None,
            "chunks_created": recording.chunks_created,
            "total_chunk_size": recording.total_chunk_size,
            "chunk_statistics": chunk_stats
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get recording info for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get recording info")

@app.get("/recordings")
async def list_recordings():
    """List all recordings with chunk statistics"""
    global session_recorder, chunk_processor
    
    if not session_recorder or not chunk_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        recordings = []
        for recording in session_recorder.active_recordings.values():
            chunk_stats = await chunk_processor.get_session_statistics(recording.session_id)
            
            recordings.append({
                "session_id": recording.session_id,
                "owner_address": recording.owner_address,
                "status": recording.status.value,
                "started_at": recording.started_at.isoformat(),
                "chunks_created": recording.chunks_created,
                "total_chunk_size": recording.total_chunk_size,
                "chunk_statistics": chunk_stats
            })
        
        return {
            "recordings": recordings,
            "total_recordings": len(recordings)
        }
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to list recordings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list recordings")

@app.delete("/recordings/{session_id}")
async def cleanup_recording(session_id: str):
    """Clean up recording and all associated chunks"""
    global session_recorder, chunk_processor
    
    if not session_recorder or not chunk_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Clean up chunks first
        deleted_chunks = await chunk_processor.cleanup_session(session_id)
        
        # Remove from active recordings if exists
        if session_id in session_recorder.active_recordings:
            del session_recorder.active_recordings[session_id]
        
        logger = logging.getLogger(__name__)
        logger.info(f"Cleaned up recording and {deleted_chunks} chunks for session {session_id}")
        
        return {
            "session_id": session_id,
            "status": "cleaned_up",
            "deleted_chunks": deleted_chunks,
            "message": "Recording and chunks cleaned up successfully"
        }
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to cleanup recording for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup recording")

@app.get("/chunks/{session_id}")
async def get_session_chunks(session_id: str):
    """Get all chunks for a session"""
    global chunk_processor
    
    if not chunk_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Get chunk statistics
        chunk_stats = await chunk_processor.get_session_statistics(session_id)
        
        if chunk_stats is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return chunk_stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get chunks for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get chunks")

@app.post("/chunks/{session_id}/process")
async def process_chunk_data(session_id: str, data: bytes):
    """Process chunk data for a session"""
    global chunk_processor
    
    if not chunk_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Process chunk data
        completed_chunks = await chunk_processor.process_session_data(session_id, data)
        
        return {
            "session_id": session_id,
            "processed_bytes": len(data),
            "completed_chunks": len(completed_chunks),
            "chunk_metadata": [
                {
                    "chunk_id": chunk.chunk_id,
                    "size_bytes": chunk.size_bytes,
                    "compression_ratio": chunk.compression_ratio,
                    "quality_score": chunk.quality_score
                }
                for chunk in completed_chunks
            ]
        }
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to process chunk data for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process chunk data")

@app.get("/compression/stats")
async def get_compression_stats():
    """Get compression statistics"""
    global compression_manager
    
    if not compression_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        return compression_manager.get_statistics()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get compression stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get compression stats")

@app.post("/compression/reset")
async def reset_compression_stats():
    """Reset compression statistics"""
    global compression_manager
    
    if not compression_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        compression_manager.reset_statistics()
        return {"message": "Compression statistics reset successfully"}
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to reset compression stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset compression stats")

def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[session-recorder] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get configuration from environment (from docker-compose)
        host = "0.0.0.0"  # Always bind to all interfaces in container
        port_str = os.getenv("SESSION_RECORDER_PORT", "8090")
        try:
            port = int(port_str)
        except ValueError:
            logger.error(f"Invalid SESSION_RECORDER_PORT value: {port_str}")
            sys.exit(1)
        
        logger.info(f"Starting Lucid Session Recorder Service on {host}:{port}")
        
        uvicorn.run(
            "sessions.recorder.main:app",
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Failed to start Session Recorder Service: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
