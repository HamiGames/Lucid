# LUCID XRDP Service - Main Entry Point
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64
# Distroless container implementation

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Import XRDP service components
from xrdp_service import XRDPServiceManager
from xrdp_config import XRDPConfigManager

logger = logging.getLogger(__name__)

# Configuration from environment
SERVICE_NAME = os.getenv("SERVICE_NAME", "xrdp-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8091"))
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin")
REDIS_URL = os.getenv("REDIS_URL", "redis://lucid_redis:6379/0")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8089")

# Initialize components
config_manager = XRDPConfigManager()
service_manager = XRDPServiceManager()

# FastAPI application
app = FastAPI(
    title="Lucid XRDP Service",
    description="XRDP service management for Lucid system",
    version="1.0.0",
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
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_processes": len(service_manager.active_processes),
        "max_processes": service_manager.max_processes
    }

@app.post("/services", response_model=ServiceResponse)
async def start_service(request: StartServiceRequest):
    """Start XRDP service"""
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
    try:
        result = await service_manager.stop_xrdp_service(process_id)
        return result
        
    except Exception as e:
        logger.error(f"Service stop failed: {e}")
        raise HTTPException(500, f"Service stop failed: {str(e)}")

@app.post("/services/{process_id}/restart")
async def restart_service(process_id: str):
    """Restart XRDP service"""
    try:
        result = await service_manager.restart_xrdp_service(process_id)
        return result
        
    except Exception as e:
        logger.error(f"Service restart failed: {e}")
        raise HTTPException(500, f"Service restart failed: {str(e)}")

@app.get("/services")
async def list_services():
    """List all XRDP services"""
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
    try:
        from .xrdp_config import SecurityLevel
        
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

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info(f"Starting {SERVICE_NAME}...")
    
    # Initialize components
    await config_manager.initialize()
    await service_manager.initialize()
    
    logger.info(f"{SERVICE_NAME} started on port {SERVICE_PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info(f"Shutting down {SERVICE_NAME}...")
    
    # Stop all XRDP processes
    await service_manager.shutdown_all()
    
    logger.info(f"{SERVICE_NAME} stopped")

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format=f'[{SERVICE_NAME}] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
