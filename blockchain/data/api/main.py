"""
Data Chain API Main Application

FastAPI application for the data chain service.
Provides REST API endpoints for data chunk management, Merkle tree operations,
and integrity verification.
"""

from __future__ import annotations

import os
import logging
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any

from .routes import router
from .dependencies import get_data_chain_service, shutdown_data_chain_service

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Environment variable configuration (required, no hardcoded defaults)
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL, MONGODB_URL, or MONGODB_URI environment variable not set")

DATA_CHAIN_PORT = int(os.getenv("DATA_CHAIN_PORT", "8087"))
DATA_CHAIN_HOST = os.getenv("DATA_CHAIN_HOST", "0.0.0.0")
API_TITLE = os.getenv("DATA_CHAIN_API_TITLE", "Lucid Data Chain API")
API_VERSION = os.getenv("DATA_CHAIN_API_VERSION", "1.0.0")

# Create FastAPI application
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="API for data chain service - chunk management, Merkle trees, and integrity verification"
)

# CORS configuration
CORS_ORIGINS = os.getenv("DATA_CHAIN_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["Data Chain"])


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Verifies:
    - Service is running
    - MongoDB connection is healthy
    - Service can perform basic operations
    """
    try:
        service = await get_data_chain_service()
        status_info = await service.get_service_status()
        
        # Determine HTTP status based on service status
        if status_info.get("status") == "healthy":
            return {
                "status": "healthy",
                "service": "data-chain",
                "details": status_info
            }
        else:
            # Service is unhealthy (e.g., MongoDB connection failed)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "service": "data-chain",
                    "details": status_info
                }
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "data-chain",
                "error": str(e)
            }
        )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "service": "data-chain",
        "version": API_VERSION,
        "status": "running"
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    logger.info(f"Listening on {DATA_CHAIN_HOST}:{DATA_CHAIN_PORT}")
    
    # Initialize service and verify dependencies
    try:
        service = await get_data_chain_service()
        
        # Verify MongoDB connection before accepting requests (with retry)
        logger.info("Verifying MongoDB connection...")
        import asyncio
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            mongodb_healthy = await service.check_mongodb_connection()
            if mongodb_healthy:
                logger.info("MongoDB connection verified successfully")
                logger.info("Data chain service initialized successfully")
                break
            else:
                if attempt < max_retries - 1:
                    logger.warning(f"MongoDB connection check failed (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("MongoDB connection verification failed after all retries - service will start but may be unhealthy")
                    # Don't raise - allow service to start and health check will report unhealthy
        
    except Exception as e:
        logger.error(f"Failed to initialize data chain service: {e}")
        # Log but don't raise - allow service to start and health check will catch it
        logger.warning("Service starting despite initialization error - health check will report status")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down data chain service")
    await shutdown_data_chain_service()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "blockchain.data.api.main:app",
        host=DATA_CHAIN_HOST,
        port=DATA_CHAIN_PORT,
        log_level=os.getenv("LOG_LEVEL", "INFO").lower()
    )

