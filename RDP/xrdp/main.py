#!/usr/bin/env python3
"""
LUCID XRDP Service - Main Entry Point
LUCID-STRICT Layer 2 Service Integration
Multi-platform support for Pi 5 ARM64
Distroless container implementation
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Import XRDP service components
from xrdp.xrdp_service import XRDPServiceManager
from xrdp.xrdp_config import XRDPConfigManager, SecurityLevel

# Configure logging (structured logging per master design)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
config_manager: Optional[XRDPConfigManager] = None
service_manager: Optional[XRDPServiceManager] = None

# Configuration from environment
SERVICE_NAME = os.getenv("SERVICE_NAME", "xrdp-service")
SERVICE_PORT = int(os.getenv("XRDP_PORT", "3389"))
MONGODB_URL = os.getenv("MONGODB_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8089")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global config_manager, service_manager
    
    # Startup
    logger.info("Starting Lucid XRDP Service...")
    
    try:
        # CRITICAL: MONGODB_URL and REDIS_URL must be set via docker-compose environment variables
        # from .env.secrets file. Defaults are empty strings to fail fast if not configured.
        if not MONGODB_URL:
            raise ValueError("MONGODB_URL environment variable is required. Set it in docker-compose.yml or .env.secrets")
        if not REDIS_URL:
            raise ValueError("REDIS_URL environment variable is required. Set it in docker-compose.yml or .env.secrets")
        
        # Initialize components
        config_manager = XRDPConfigManager()
        service_manager = XRDPServiceManager()
        
        # Initialize components
        await config_manager.initialize()
        await service_manager.initialize()
        
        logger.info(f"{SERVICE_NAME} started on port {SERVICE_PORT}")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start {SERVICE_NAME}: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown (graceful shutdown per master design)
        logger.info(f"Shutting down {SERVICE_NAME}...")
        
        try:
            if service_manager:
                await service_manager.shutdown_all()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
        
        logger.info(f"{SERVICE_NAME} stopped")

# FastAPI application
app = FastAPI(
    title="Lucid XRDP Service",
    description="XRDP service management for Lucid system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Pydantic models
class StartServiceRequest(BaseModel):
    process_id: str
    port: int
    config_path: str
    log_path: str
    session_path: str

class ServiceResponse(BaseModel):
    process_id: str
    status: str
    port: int
    started_at: str
    pid: Optional[int] = None

class ServiceStatusResponse(BaseModel):
    process_id: str
    status: str
    port: int
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    pid: Optional[int] = None
    resource_usage: Optional[Dict[str, Any]] = None

# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global service_manager
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_processes": len(service_manager.active_processes) if service_manager else 0,
        "max_processes": service_manager.max_processes if service_manager else 0
    }

@app.post("/services", response_model=ServiceResponse)
async def start_service(request: StartServiceRequest):
    """Start XRDP service"""
    global service_manager
    if not service_manager:
        raise HTTPException(503, "Service not initialized")
    
    try:
        # Convert string paths to Path objects
        config_path = Path(request.config_path)
        log_path = Path(request.log_path)
        session_path = Path(request.session_path)
        
        # Start XRDP service
        xrdp_process = await service_manager.start_xrdp_service(
            process_id=request.process_id,
            port=request.port,
            config_path=config_path,
            log_path=log_path,
            session_path=session_path
        )
        
        return ServiceResponse(
            process_id=xrdp_process.process_id,
            status=xrdp_process.status.value,
            port=xrdp_process.port,
            started_at=xrdp_process.started_at.isoformat(),
            pid=xrdp_process.pid
        )
        
    except Exception as e:
        logger.error(f"Service start failed: {e}")
        raise HTTPException(500, f"Service start failed: {str(e)}")

@app.get("/services/{process_id}", response_model=ServiceStatusResponse)
async def get_service(process_id: str):
    """Get XRDP service status"""
    global service_manager
    if not service_manager:
        raise HTTPException(503, "Service not initialized")
    
    try:
        xrdp_process = await service_manager.get_process_status(process_id)
        if not xrdp_process:
            raise HTTPException(404, "Service not found")
        
        return ServiceStatusResponse(
            process_id=xrdp_process.process_id,
            status=xrdp_process.status.value,
            port=xrdp_process.port,
            started_at=xrdp_process.started_at.isoformat() if xrdp_process.started_at else None,
            stopped_at=xrdp_process.stopped_at.isoformat() if xrdp_process.stopped_at else None,
            pid=xrdp_process.pid,
            resource_usage=xrdp_process.resource_usage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get service failed: {e}")
        raise HTTPException(500, f"Get service failed: {str(e)}")

@app.post("/services/{process_id}/stop")
async def stop_service(process_id: str):
    """Stop XRDP service"""
    global service_manager
    if not service_manager:
        raise HTTPException(503, "Service not initialized")
    
    try:
        result = await service_manager.stop_xrdp_service(process_id)
        return result
        
    except Exception as e:
        logger.error(f"Service stop failed: {e}")
        raise HTTPException(500, f"Service stop failed: {str(e)}")

@app.post("/services/{process_id}/restart")
async def restart_service(process_id: str):
    """Restart XRDP service"""
    global service_manager
    if not service_manager:
        raise HTTPException(503, "Service not initialized")
    
    try:
        result = await service_manager.restart_xrdp_service(process_id)
        return result
        
    except Exception as e:
        logger.error(f"Service restart failed: {e}")
        raise HTTPException(500, f"Service restart failed: {str(e)}")

@app.get("/services")
async def list_services():
    """List all XRDP services"""
    global service_manager
    if not service_manager:
        raise HTTPException(503, "Service not initialized")
    
    try:
        processes = await service_manager.list_processes()
        return {
            "services": [
                {
                    "process_id": p.process_id,
                    "port": p.port,
                    "status": p.status.value,
                    "pid": p.pid,
                    "started_at": p.started_at.isoformat() if p.started_at else None
                }
                for p in processes
            ],
            "total": len(processes),
            "max_processes": service_manager.max_processes
        }
        
    except Exception as e:
        logger.error(f"List services failed: {e}")
        raise HTTPException(500, f"List services failed: {str(e)}")

@app.get("/statistics")
async def get_statistics():
    """Get service statistics"""
    global service_manager
    if not service_manager:
        raise HTTPException(503, "Service not initialized")
    
    try:
        stats = await service_manager.get_service_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Statistics failed: {e}")
        raise HTTPException(500, f"Statistics failed: {str(e)}")

@app.post("/config/create")
async def create_config(
    server_id: str,
    port: int,
    user_id: str,
    session_id: str,
    display_config: Optional[Dict[str, Any]] = None,
    security_level: str = "high"
):
    """Create XRDP configuration"""
    global config_manager
    if not config_manager:
        raise HTTPException(503, "Service not initialized")
    
    try:
        # Map security level
        security_levels = {
            "low": SecurityLevel.LOW,
            "medium": SecurityLevel.MEDIUM,
            "high": SecurityLevel.HIGH,
            "maximum": SecurityLevel.MAXIMUM
        }
        
        security = security_levels.get(security_level, SecurityLevel.HIGH)
        
        # Create configuration
        config = await config_manager.create_server_config(
            server_id=server_id,
            port=port,
            user_id=user_id,
            session_id=session_id,
            display_config=display_config,
            security_level=security
        )
        
        return {
            "server_id": server_id,
            "port": port,
            "config_path": str(config.config_path),
            "log_path": str(config.log_path),
            "session_path": str(config.session_path),
            "security_level": config.security_level.value,
            "ssl_enabled": config.ssl_enabled
        }
        
    except Exception as e:
        logger.error(f"Config creation failed: {e}")
        raise HTTPException(500, f"Config creation failed: {str(e)}")

@app.post("/config/validate")
async def validate_config(config_path: str):
    """Validate XRDP configuration"""
    global config_manager
    if not config_manager:
        raise HTTPException(503, "Service not initialized")
    
    try:
        path = Path(config_path)
        is_valid = await config_manager.validate_config(path)
        
        return {
            "config_path": str(path),
            "valid": is_valid
        }
        
    except Exception as e:
        logger.error(f"Config validation failed: {e}")
        raise HTTPException(500, f"Config validation failed: {str(e)}")

@app.delete("/config/{server_id}")
async def cleanup_config(server_id: str):
    """Cleanup XRDP configuration"""
    global config_manager
    if not config_manager:
        raise HTTPException(503, "Service not initialized")
    
    try:
        config_path = config_manager.config_path / server_id
        await config_manager.cleanup_config(config_path)
        
        return {
            "server_id": server_id,
            "cleaned": True
        }
        
    except Exception as e:
        logger.error(f"Config cleanup failed: {e}")
        raise HTTPException(500, f"Config cleanup failed: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "xrdp-service", "status": "running"}
