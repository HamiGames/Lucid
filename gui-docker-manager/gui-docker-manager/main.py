#!/usr/bin/env python3
"""
LUCID GUI Docker Manager Service - Main Entry Point
File: gui-docker-manager/gui-docker-manager/main.py
"""

import asyncio
import logging
import signal
import sys
import os
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .docker_manager_service import DockerManagerService
from .config import get_config
from .routers import containers_router, services_router, compose_router, health_router
from .routers import networks_router, volumes_router, events_router
from .services.authentication_service import AuthenticationService
from .middleware.auth import AuthenticationMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
docker_manager: Optional[DockerManagerService] = None
config_manager = get_config()
auth_service: Optional[AuthenticationService] = None


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
    global docker_manager, auth_service
    
    logger.info("Starting Lucid GUI Docker Manager Service")
    
    try:
        # Validate configuration
        if not config_manager.get_config_dict():
            raise RuntimeError("Docker Manager configuration validation failed")
        
        # Initialize Authentication Service
        jwt_secret = os.getenv('JWT_SECRET_KEY', '')
        if not jwt_secret:
            logger.warning("JWT_SECRET_KEY not set - authentication may be disabled")
            jwt_secret = 'default-insecure-key'
        
        auth_service = AuthenticationService(secret_key=jwt_secret)
        logger.info("Authentication service initialized")
        
        # Initialize Docker Manager Service
        docker_manager = DockerManagerService(config_manager)
        await docker_manager.initialize()
        
        # Setup signal handlers
        setup_signal_handlers()
        
        logger.info("GUI Docker Manager Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start GUI Docker Manager Service: {str(e)}")
        raise
    finally:
        # Shutdown
        if docker_manager:
            try:
                await docker_manager.close()
            except Exception as e:
                logger.warning(f"Error closing Docker Manager: {e}")
        
        logger.info("GUI Docker Manager Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="LUCID GUI Docker Manager Service",
    description="Docker container management for Lucid Electron GUI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
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

# Add authentication middleware (if JWT_SECRET_KEY is set)
jwt_secret = os.getenv('JWT_SECRET_KEY', '')
if jwt_secret and jwt_secret != 'default-insecure-key':
    auth_middleware_instance = AuthenticationMiddleware(
        auth_service=auth_service or AuthenticationService(secret_key=jwt_secret)
    )
    app.add_middleware(lambda app: auth_middleware_instance(app))
    logger.info("Authentication middleware enabled")
else:
    logger.warning("Authentication middleware disabled - JWT_SECRET_KEY not configured")

# Include routers
app.include_router(containers_router, prefix="/api/v1/containers", tags=["containers"])
app.include_router(services_router, prefix="/api/v1/services", tags=["services"])
app.include_router(compose_router, prefix="/api/v1/compose", tags=["compose"])
app.include_router(networks_router, prefix="/api/v1/networks", tags=["networks"])
app.include_router(volumes_router, prefix="/api/v1/volumes", tags=["volumes"])
app.include_router(events_router, prefix="/api/v1/events", tags=["events"])
app.include_router(health_router, prefix="/api/v1", tags=["health"])

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
        "service": "LUCID GUI Docker Manager Service",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


# Health check endpoint (also available via health router)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if docker_manager is None:
            return {
                "status": "unhealthy",
                "error": "Docker Manager not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return await docker_manager.health_check()
        
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
        if docker_manager is None:
            raise HTTPException(status_code=503, detail="Docker Manager not available")
        
        containers = await docker_manager.list_containers(all=True)
        running_containers = sum(1 for c in containers if c.get('State') == 'running')
        
        metrics = []
        metrics.append("# HELP lucid_containers_total Total number of Lucid containers")
        metrics.append("# TYPE lucid_containers_total gauge")
        metrics.append(f"lucid_containers_total{{state=\"running\"}} {running_containers}")
        metrics.append(f"lucid_containers_total{{state=\"total\"}} {len(containers)}")
        
        return Response(
            content="\n".join(metrics),
            media_type="text/plain"
        )
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
