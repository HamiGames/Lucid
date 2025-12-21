"""
Chunk Processor Service Main Entry Point
FastAPI application for the chunk processing service.

This module provides the main entry point for the chunk processor service,
including FastAPI application setup, health checks, and API endpoints.
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import ChunkProcessorConfig, get_config
from .chunk_processor import ChunkProcessorService, ProcessingResult
from .encryption import EncryptionManager
from .merkle_builder import MerkleTreeManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
chunk_processor_service: Optional[ChunkProcessorService] = None
encryption_manager: Optional[EncryptionManager] = None
merkle_tree_manager: Optional[MerkleTreeManager] = None
config: Optional[ChunkProcessorConfig] = None
integrations: Optional[Any] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting chunk processor service...")
    
    try:
        # Load configuration
        global config
        config = get_config()
        
        # Initialize integration manager
        global integrations
        try:
            from .integration.integration_manager import IntegrationManager
            integrations = IntegrationManager(
                service_timeout=float(os.getenv('SERVICE_TIMEOUT_SECONDS', '30')),
                service_retry_count=int(os.getenv('SERVICE_RETRY_COUNT', '3')),
                service_retry_delay=float(os.getenv('SERVICE_RETRY_DELAY_SECONDS', '1.0'))
            )
            logger.info("Integration manager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize integration manager: {str(e)}")
            integrations = None
        
        # Initialize services
        global chunk_processor_service, encryption_manager, merkle_tree_manager
        
        encryption_manager = EncryptionManager(config.encryption_key)
        merkle_tree_manager = MerkleTreeManager()
        chunk_processor_service = ChunkProcessorService(config)
        
        # Start services
        await chunk_processor_service.start()
        
        logger.info("Chunk processor service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start chunk processor service: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down chunk processor service...")
    
    try:
        if chunk_processor_service:
            await chunk_processor_service.stop()
        
        # Close integration clients
        if integrations:
            try:
                await integrations.close_all()
            except Exception as e:
                logger.warning(f"Error closing integrations: {str(e)}")
        
        logger.info("Chunk processor service stopped successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="Lucid Chunk Processor Service",
    description="Chunk processing service for session data encryption and Merkle tree building",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins if config else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


# Dependency injection
def get_chunk_processor() -> ChunkProcessorService:
    """Get the chunk processor service instance."""
    if chunk_processor_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chunk processor service not available"
        )
    return chunk_processor_service


def get_encryption_manager() -> EncryptionManager:
    """Get the encryption manager instance."""
    if encryption_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Encryption manager not available"
        )
    return encryption_manager


def get_merkle_tree_manager() -> MerkleTreeManager:
    """Get the Merkle tree manager instance."""
    if merkle_tree_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Merkle tree manager not available"
        )
    return merkle_tree_manager


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Service health status
    """
    try:
        if chunk_processor_service is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "service": "chunk-processor",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": "Service not initialized"
                }
            )
        
        # Get service health
        health_data = await chunk_processor_service.health_check()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=health_data
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "chunk-processor",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """
    Get service metrics.
    
    Returns:
        Service metrics data
    """
    try:
        if chunk_processor_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not available"
            )
        
        metrics = chunk_processor_service.get_metrics()
        
        return {
            "service": "chunk-processor",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


# Chunk processing endpoints
@app.post("/api/v1/chunks/process")
async def process_chunk(
    session_id: str,
    chunk_id: str,
    chunk_data: bytes,
    background_tasks: BackgroundTasks,
    processor: ChunkProcessorService = Depends(get_chunk_processor)
):
    """
    Process a single chunk.
    
    Args:
        session_id: ID of the session
        chunk_id: ID of the chunk
        chunk_data: Raw chunk data
        background_tasks: FastAPI background tasks
        
    Returns:
        Processing result
    """
    try:
        logger.info(f"Processing chunk {chunk_id} for session {session_id}")
        
        # Process chunk
        result = await processor.process_chunk(session_id, chunk_id, chunk_data)
        
        if result.success:
            return {
                "success": True,
                "chunk_id": chunk_id,
                "session_id": session_id,
                "metadata": result.chunk_metadata,
                "processing_time_ms": result.processing_time_ms,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error_message
            )
        
    except Exception as e:
        logger.error(f"Failed to process chunk {chunk_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chunk: {str(e)}"
        )


@app.post("/api/v1/chunks/process-batch")
async def process_chunks_batch(
    session_id: str,
    chunks: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    processor: ChunkProcessorService = Depends(get_chunk_processor)
):
    """
    Process multiple chunks in batch.
    
    Args:
        session_id: ID of the session
        chunks: List of chunk data
        background_tasks: FastAPI background tasks
        
    Returns:
        Batch processing results
    """
    try:
        logger.info(f"Processing batch of {len(chunks)} chunks for session {session_id}")
        
        # Convert chunks to the expected format
        chunk_tuples = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            chunk_data = chunk.get("chunk_data", b"")
            metadata = chunk.get("metadata")
            
            if not chunk_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="chunk_id is required for each chunk"
                )
            
            chunk_tuples.append((chunk_id, chunk_data, metadata))
        
        # Process chunks
        results = await processor.process_chunks_batch(session_id, chunk_tuples)
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "success": result.success,
                "chunk_id": result.chunk_metadata.chunk_id if result.chunk_metadata else None,
                "error_message": result.error_message,
                "processing_time_ms": result.processing_time_ms
            })
        
        return {
            "success": True,
            "session_id": session_id,
            "total_chunks": len(chunks),
            "successful_chunks": len([r for r in results if r.success]),
            "failed_chunks": len([r for r in results if not r.success]),
            "results": formatted_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process chunk batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chunk batch: {str(e)}"
        )


# Merkle tree endpoints
@app.get("/api/v1/sessions/{session_id}/merkle-root")
async def get_session_merkle_root(
    session_id: str,
    processor: ChunkProcessorService = Depends(get_chunk_processor)
):
    """
    Get the Merkle root for a session.
    
    Args:
        session_id: ID of the session
        
    Returns:
        Merkle root hash
    """
    try:
        merkle_root = await processor.get_session_merkle_root(session_id)
        
        if merkle_root:
            return {
                "session_id": session_id,
                "merkle_root": merkle_root,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No Merkle root found for session {session_id}"
            )
        
    except Exception as e:
        logger.error(f"Failed to get Merkle root for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Merkle root: {str(e)}"
        )


@app.post("/api/v1/sessions/{session_id}/finalize")
async def finalize_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    processor: ChunkProcessorService = Depends(get_chunk_processor)
):
    """
    Finalize a session and return the final Merkle root.
    
    Args:
        session_id: ID of the session to finalize
        background_tasks: FastAPI background tasks
        
    Returns:
        Final Merkle root hash
    """
    try:
        logger.info(f"Finalizing session {session_id}")
        
        merkle_root = await processor.finalize_session(session_id)
        
        if merkle_root:
            return {
                "session_id": session_id,
                "merkle_root": merkle_root,
                "finalized": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found or could not be finalized"
            )
        
    except Exception as e:
        logger.error(f"Failed to finalize session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize session: {str(e)}"
        )


# Configuration endpoint
@app.get("/api/v1/config")
async def get_configuration():
    """
    Get service configuration.
    
    Returns:
        Service configuration (without sensitive data)
    """
    try:
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Configuration not available"
            )
        
        # Return configuration without sensitive data
        config_dict = config.to_dict()
        config_dict.pop("encryption_key", None)  # Remove sensitive data
        
        return {
            "service": "chunk-processor",
            "configuration": config_dict,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration: {str(e)}"
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"LUCID_ERR_{exc.status_code}",
                "message": exc.detail,
                "request_id": request.headers.get("X-Request-ID", "unknown"),
                "timestamp": datetime.utcnow().isoformat(),
                "service": "chunk-processor",
                "version": "1.0.0"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "LUCID_ERR_5000",
                "message": "Internal server error",
                "request_id": request.headers.get("X-Request-ID", "unknown"),
                "timestamp": datetime.utcnow().isoformat(),
                "service": "chunk-processor",
                "version": "1.0.0"
            }
        }
    )


# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)


def main():
    """Main entry point for the chunk processor service."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load configuration
        global config
        config = get_config()
        
        # Configure logging
        logging.getLogger().setLevel(getattr(logging, config.log_level))
        
        logger.info(f"Starting chunk processor service on {config.host}:{config.port}")
        
        # Run the application
        uvicorn.run(
            "sessions.processor.main:app",
            host=config.host,
            port=config.port,
            reload=config.debug,
            log_level=config.log_level.lower(),
            access_log=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start chunk processor service: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
