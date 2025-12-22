"""
Chunk Processor Service Main Entry Point
FastAPI application for the chunk processing service.

This module provides the main entry point for the chunk processor service,
including FastAPI application setup, health checks, and API endpoints.
"""

import asyncio
import base64
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
from pydantic import BaseModel, Field, field_validator
import uvicorn

from .config import ChunkProcessorConfig, get_config
from .chunk_processor import ChunkProcessorService, ProcessingResult
from .encryption import EncryptionManager
from .merkle_builder import MerkleTreeManager
from core.logging import setup_logging, get_logger

# Initialize logging
setup_logging()

logger = get_logger(__name__)

# Global service instances
chunk_processor_service: Optional[ChunkProcessorService] = None
encryption_manager: Optional[EncryptionManager] = None
merkle_tree_manager: Optional[MerkleTreeManager] = None
config: Optional[ChunkProcessorConfig] = None
integrations: Optional[Any] = None


# Request/Response Models
class ProcessChunkRequest(BaseModel):
    """Request model for processing a single chunk."""
    session_id: str = Field(..., description="ID of the session")
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    chunk_data_base64: str = Field(..., description="Base64-encoded chunk data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for the chunk")
    
    @field_validator('chunk_data_base64')
    @classmethod
    def validate_chunk_data(cls, v: str) -> str:
        """Validate and decode base64 chunk data."""
        if not v:
            raise ValueError("chunk_data_base64 cannot be empty")
        try:
            # Validate base64 encoding
            base64.b64decode(v, validate=True)
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {str(e)}")
        return v
    
    def get_chunk_data(self) -> bytes:
        """Decode base64 chunk data to bytes."""
        return base64.b64decode(self.chunk_data_base64)


class ChunkData(BaseModel):
    """Single chunk data for batch processing."""
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    chunk_data_base64: str = Field(..., description="Base64-encoded chunk data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata for the chunk")
    
    @field_validator('chunk_data_base64')
    @classmethod
    def validate_chunk_data(cls, v: str) -> str:
        """Validate and decode base64 chunk data."""
        if not v:
            raise ValueError("chunk_data_base64 cannot be empty")
        try:
            # Validate base64 encoding
            base64.b64decode(v, validate=True)
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {str(e)}")
        return v
    
    def get_chunk_data(self) -> bytes:
        """Decode base64 chunk data to bytes."""
        return base64.b64decode(self.chunk_data_base64)


class ProcessBatchRequest(BaseModel):
    """Request model for batch chunk processing."""
    session_id: str = Field(..., description="ID of the session")
    chunks: List[ChunkData] = Field(..., description="List of chunks to process", min_length=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    global config, integrations, chunk_processor_service, encryption_manager, merkle_tree_manager
    
    logger.info("Starting chunk processor service...")
    
    try:
        # Load and validate configuration
        config = get_config()
        if not config.validate_config():
            raise RuntimeError("Configuration validation failed")
        
        # Setup signal handlers
        setup_signal_handlers()
        
        # Initialize integration manager
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
        encryption_manager = EncryptionManager(config.encryption_key)
        merkle_tree_manager = MerkleTreeManager()
        chunk_processor_service = ChunkProcessorService(config)
        
        # Start services
        await chunk_processor_service.start()
        
        logger.info("Chunk processor service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start chunk processor service: {str(e)}")
        raise
    finally:
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
# Note: config is initialized in lifespan, so use default for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Will be overridden by config in lifespan if needed
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
    request: ProcessChunkRequest,
    processor: ChunkProcessorService = Depends(get_chunk_processor)
):
    """
    Process a single chunk.
    
    Args:
        request: ProcessChunkRequest containing session_id, chunk_id, base64-encoded chunk_data, and optional metadata
        
    Returns:
        Processing result with chunk metadata and processing time
    """
    try:
        logger.info(f"Processing chunk {request.chunk_id} for session {request.session_id}")
        
        # Decode chunk data from base64
        chunk_data = request.get_chunk_data()
        
        # Process chunk
        result = await processor.process_chunk(
            request.session_id,
            request.chunk_id,
            chunk_data,
            request.metadata
        )
        
        if result.success:
            # Convert ChunkMetadata dataclass to dict for JSON serialization
            metadata_dict = None
            if result.chunk_metadata:
                metadata_dict = {
                    "chunk_id": result.chunk_metadata.chunk_id,
                    "session_id": result.chunk_metadata.session_id,
                    "original_size": result.chunk_metadata.original_size,
                    "encrypted_size": result.chunk_metadata.encrypted_size,
                    "compression_ratio": result.chunk_metadata.compression_ratio,
                    "hash": result.chunk_metadata.hash,
                    "encrypted_hash": result.chunk_metadata.encrypted_hash,
                    "timestamp": result.chunk_metadata.timestamp.isoformat(),
                    "processing_time_ms": result.chunk_metadata.processing_time_ms,
                    "worker_id": result.chunk_metadata.worker_id
                }
            
            return {
                "success": True,
                "chunk_id": request.chunk_id,
                "session_id": request.session_id,
                "metadata": metadata_dict,
                "processing_time_ms": result.processing_time_ms,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Return error response instead of raising exception for better error handling
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "chunk_id": request.chunk_id,
                    "session_id": request.session_id,
                    "error": result.error_message,
                    "processing_time_ms": result.processing_time_ms,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error processing chunk {request.chunk_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to process chunk {request.chunk_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chunk: {str(e)}"
        )


@app.post("/api/v1/chunks/process-batch")
async def process_chunks_batch(
    request: ProcessBatchRequest,
    processor: ChunkProcessorService = Depends(get_chunk_processor)
):
    """
    Process multiple chunks in batch.
    
    Args:
        request: ProcessBatchRequest containing session_id and list of chunks with base64-encoded data
        
    Returns:
        Batch processing results with success/failure counts and individual chunk results
    """
    try:
        logger.info(f"Processing batch of {len(request.chunks)} chunks for session {request.session_id}")
        
        # Convert chunks to the expected format (chunk_id, chunk_data_bytes, metadata)
        chunk_tuples = []
        for chunk in request.chunks:
            chunk_data = chunk.get_chunk_data()
            chunk_tuples.append((chunk.chunk_id, chunk_data, chunk.metadata))
        
        # Process chunks
        results = await processor.process_chunks_batch(request.session_id, chunk_tuples)
        
        # Format results
        formatted_results = []
        for result in results:
            metadata_dict = None
            if result.chunk_metadata:
                metadata_dict = {
                    "chunk_id": result.chunk_metadata.chunk_id,
                    "session_id": result.chunk_metadata.session_id,
                    "original_size": result.chunk_metadata.original_size,
                    "encrypted_size": result.chunk_metadata.encrypted_size,
                    "compression_ratio": result.chunk_metadata.compression_ratio,
                    "hash": result.chunk_metadata.hash,
                    "encrypted_hash": result.chunk_metadata.encrypted_hash,
                    "timestamp": result.chunk_metadata.timestamp.isoformat(),
                    "processing_time_ms": result.chunk_metadata.processing_time_ms,
                    "worker_id": result.chunk_metadata.worker_id
                }
            
            formatted_results.append({
                "success": result.success,
                "chunk_id": result.chunk_metadata.chunk_id if result.chunk_metadata else None,
                "metadata": metadata_dict,
                "error_message": result.error_message,
                "processing_time_ms": result.processing_time_ms
            })
        
        successful_count = len([r for r in results if r.success])
        failed_count = len([r for r in results if not r.success])
        
        return {
            "success": failed_count == 0,  # Overall success if no failures
            "session_id": request.session_id,
            "total_chunks": len(request.chunks),
            "successful_chunks": successful_count,
            "failed_chunks": failed_count,
            "results": formatted_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error processing batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to process chunk batch: {str(e)}", exc_info=True)
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
        Merkle root hash with session_id and timestamp
    """
    try:
        if not session_id or not session_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id cannot be empty"
            )
        
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
        
    except HTTPException:
        # Re-raise HTTP exceptions (including 404)
        raise
    except Exception as e:
        logger.error(f"Failed to get Merkle root for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Merkle root: {str(e)}"
        )


@app.post("/api/v1/sessions/{session_id}/finalize")
async def finalize_session(
    session_id: str,
    processor: ChunkProcessorService = Depends(get_chunk_processor)
):
    """
    Finalize a session and return the final Merkle root.
    
    Args:
        session_id: ID of the session to finalize
        
    Returns:
        Final Merkle root hash with finalized status and timestamp
    """
    try:
        if not session_id or not session_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id cannot be empty"
            )
        
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
        
    except HTTPException:
        # Re-raise HTTP exceptions (including 404)
        raise
    except Exception as e:
        logger.error(f"Failed to finalize session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize session: {str(e)}"
        )


# Configuration endpoint
@app.get("/api/v1/config")
async def get_configuration():
    """
    Get service configuration (without sensitive data).
    
    Returns:
        Service configuration excluding sensitive fields like encryption keys
    """
    try:
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Configuration not available"
            )
        
        # Return configuration without sensitive data
        config_dict = config.to_dict()
        # Remove sensitive data fields
        config_dict.pop("encryption_key", None)
        # Also check for any nested sensitive fields
        if "mongodb_url" in config_dict and config_dict["mongodb_url"]:
            # Redact password from MongoDB URL if present
            mongodb_url = config_dict["mongodb_url"]
            if "@" in mongodb_url and ":" in mongodb_url:
                # Format: mongodb://user:password@host:port/db
                parts = mongodb_url.split("@")
                if len(parts) == 2:
                    user_pass = parts[0].split("://")[-1]
                    if ":" in user_pass:
                        user = user_pass.split(":")[0]
                        config_dict["mongodb_url"] = mongodb_url.replace(user_pass, f"{user}:***")
        
        if "redis_url" in config_dict and config_dict["redis_url"]:
            # Redact password from Redis URL if present
            redis_url = config_dict["redis_url"]
            if "@" in redis_url:
                parts = redis_url.split("@")
                if len(parts) == 2:
                    config_dict["redis_url"] = f"redis://:***@{parts[1]}"
        
        return {
            "service": "chunk-processor",
            "configuration": config_dict,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}", exc_info=True)
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
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point for the chunk processor service."""
    try:
        # Load configuration
        config = get_config()
        
        # Configure logging level from config
        import logging as std_logging
        std_logging.getLogger().setLevel(getattr(std_logging, config.log_level))
        
        # Get host and port from config (or environment for container compatibility)
        host = os.getenv("SESSION_PROCESSOR_HOST", config.host)
        port_str = os.getenv("SESSION_PROCESSOR_PORT", str(config.port))
        try:
            port = int(port_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid SESSION_PROCESSOR_PORT value: {port_str}")
            sys.exit(1)
        
        # Map log level to uvicorn-compatible values
        # Uvicorn accepts: critical, error, warning, info, debug, trace
        log_level_map = {
            "CRITICAL": "critical",
            "ERROR": "error",
            "WARNING": "warning",
            "INFO": "info",
            "DEBUG": "debug",
            "TRACE": "trace"
        }
        uvicorn_log_level = log_level_map.get(config.log_level.upper(), "info")
        
        logger.info(f"Starting chunk processor service on {host}:{port}")
        
        # Run the application
        # Note: reload is disabled for production/distroless containers
        # Access log is enabled for monitoring and debugging
        # Workers are not used with uvicorn.run() - single worker for distroless compatibility
        uvicorn.run(
            "sessions.processor.main:app",
            host=host,
            port=port,
            reload=False,  # Never enable reload in production/distroless containers
            log_level=uvicorn_log_level,
            access_log=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start chunk processor service: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
