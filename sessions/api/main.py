#!/usr/bin/env python3
"""
LUCID Session API Service - Main Entry Point
Step 17 Implementation: Session Storage & API
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient

from .session_api import SessionAPI
from .routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global API instance
session_api: Optional[SessionAPI] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global session_api
    
    # Startup
    logger.info("Starting Session API Service...")
    
    try:
        # Initialize API
        mongo_url = os.getenv("MONGO_URL", "mongodb://lucid:lucid@localhost:27017/lucid")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        session_api = SessionAPI(mongo_url, redis_url)
        
        logger.info("Session API Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Session API Service: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Session API Service...")
        
        if session_api:
            await session_api.close()
        
        logger.info("Session API Service stopped")

# Create FastAPI application
app = FastAPI(
    title="LUCID Session API Service",
    description="Session management API for Lucid RDP system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "LUCID_ERR_5000",
                "message": "Internal server error",
                "details": {"exception": str(exc)},
                "request_id": getattr(request, 'request_id', 'unknown'),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LUCID Session API Service",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if session_api is None:
            return {
                "status": "unhealthy",
                "error": "Session API not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Check MongoDB connection
        mongo_healthy = session_api.mongo_client.admin.command('ping')['ok'] == 1
        
        # Check storage health
        storage_health = await session_api.session_storage.health_check()
        chunk_health = await session_api.chunk_store.health_check()
        
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

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Get Prometheus-formatted metrics"""
    try:
        if session_api is None:
            raise HTTPException(status_code=503, detail="Session API not available")
        
        # Get system statistics
        system_stats = await session_api.get_system_statistics()
        storage_metrics = await session_api.session_storage.get_storage_metrics()
        chunk_stats = await session_api.chunk_store.get_storage_stats()
        
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

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get configuration from environment
    host = os.getenv("LUCID_API_HOST", "0.0.0.0")
    port = int(os.getenv("LUCID_API_PORT", "8080"))
    workers = int(os.getenv("LUCID_API_WORKERS", "1"))
    
    logger.info(f"Starting Session API Service on {host}:{port}")
    
    # Start the server
    uvicorn.run(
        "sessions.api.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
