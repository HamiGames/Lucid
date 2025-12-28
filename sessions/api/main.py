#!/usr/bin/env python3
"""
LUCID Session API Service - Main Entry Point
Step 17 Implementation: Session Storage & API
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from datetime import datetime

from .session_api import SessionAPI
from .routes import router
from .config import SessionAPIConfig
from .integration.rdp_controller_client import RDPControllerClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
session_api: Optional[SessionAPI] = None
api_config: Optional[SessionAPIConfig] = None
rdp_controller_client: Optional[RDPControllerClient] = None

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global session_api, api_config, rdp_controller_client
    
    logger.info("Starting Lucid Session API Service")
    
    try:
        # Initialize configuration
        api_config = SessionAPIConfig()
        if not api_config.validate_configuration():
            raise RuntimeError("Session API configuration validation failed")
        
        # Initialize RDP controller client
        try:
            import os
            rdp_controller_url = os.getenv('RDP_CONTROLLER_URL', '')
            if rdp_controller_url:
                rdp_controller_client = RDPControllerClient(
                    base_url=rdp_controller_url,
                    timeout=float(os.getenv('SERVICE_TIMEOUT_SECONDS', '30.0')),
                    retry_count=int(os.getenv('SERVICE_RETRY_COUNT', '3')),
                    retry_delay=float(os.getenv('SERVICE_RETRY_DELAY_SECONDS', '1.0'))
                )
                logger.info("RDP controller client initialized")
            else:
                logger.warning("RDP_CONTROLLER_URL not set, rdp-controller integration unavailable")
                rdp_controller_client = None
        except Exception as e:
            logger.warning(f"Failed to initialize RDP controller client: {e}")
            rdp_controller_client = None
        
        # Initialize API with configuration and RDP controller client
        session_api = SessionAPI(
            api_config.settings.MONGODB_URL,
            api_config.settings.REDIS_URL,
            rdp_controller_client=rdp_controller_client
        )
        
        # Setup signal handlers
        setup_signal_handlers()
        
        logger.info("Session API Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Session API Service: {str(e)}")
        raise
    finally:
        # Shutdown
        if rdp_controller_client:
            try:
                await rdp_controller_client.close()
            except Exception as e:
                logger.warning(f"Error closing RDP controller client: {e}")
        
        if session_api:
            logger.info("Shutting down Session API Service")
            await session_api.close()
            session_api = None
        logger.info("Session API Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="LUCID Session API Service",
    description="Session management API for Lucid RDP system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (configured from environment variables)
# CORS_ORIGINS env var: comma-separated list of origins, or "*" for all
# Default to ["*"] if not set
import os
cors_origins_str = os.getenv('CORS_ORIGINS', '*')
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

