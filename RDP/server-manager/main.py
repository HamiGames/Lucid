# LUCID RDP Server Manager - Main Entry Point
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

# Import server manager components
from server_manager import RDPServerManager
from port_manager import PortManager
from config_manager import ConfigManager

logger = logging.getLogger(__name__)

# Configuration from environment
SERVICE_NAME = os.getenv("SERVICE_NAME", "rdp-server-manager")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8090"))
MONGODB_URL = os.getenv("MONGODB_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8089")

# CRITICAL: MONGODB_URL and REDIS_URL must be set via docker-compose environment variables
# from .env.secrets file. Defaults are empty strings to fail fast if not configured.
if not MONGODB_URL:
    raise ValueError("MONGODB_URL environment variable is required. Set it in docker-compose.yml or .env.secrets")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable is required. Set it in docker-compose.yml or .env.secrets")

# Port allocation range
PORT_RANGE_START = int(os.getenv("PORT_RANGE_START", "13389"))
PORT_RANGE_END = int(os.getenv("PORT_RANGE_END", "14389"))
MAX_CONCURRENT_SERVERS = int(os.getenv("MAX_CONCURRENT_SERVERS", "50"))

# Initialize components
config_manager = ConfigManager()
port_manager = PortManager(PORT_RANGE_START, PORT_RANGE_END)
server_manager = RDPServerManager(config_manager, port_manager)

# FastAPI application
app = FastAPI(
    title="Lucid RDP Server Manager",
    description="RDP server lifecycle management for Lucid system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Pydantic models
class CreateServerRequest(BaseModel):
    user_id: str
    session_id: str
    display_config: Optional[Dict[str, Any]] = None
    resource_limits: Optional[Dict[str, Any]] = None

class ServerResponse(BaseModel):
    server_id: str
    status: str
    port: int
    created_at: str
    connection_info: Dict[str, Any]

class ServerStatusResponse(BaseModel):
    server_id: str
    status: str
    port: int
    created_at: str
    started_at: Optional[str] = None
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
        "active_servers": len(server_manager.active_servers),
        "max_servers": MAX_CONCURRENT_SERVERS,
        "available_ports": port_manager.get_available_ports_count()
    }

@app.post("/servers", response_model=ServerResponse)
async def create_server(request: CreateServerRequest):
    """Create new RDP server instance"""
    try:
        # Check server limits
        if len(server_manager.active_servers) >= MAX_CONCURRENT_SERVERS:
            raise HTTPException(429, "Maximum concurrent servers reached")
        
        # Create server
        server = await server_manager.create_server(
            user_id=request.user_id,
            session_id=request.session_id,
            display_config=request.display_config,
            resource_limits=request.resource_limits
        )
        
        return ServerResponse(
            server_id=server.server_id,
            status=server.status.value,
            port=server.port,
            created_at=server.created_at.isoformat(),
            connection_info=server.connection_info
        )
        
    except Exception as e:
        logger.error(f"Server creation failed: {e}")
        raise HTTPException(500, f"Server creation failed: {str(e)}")

@app.get("/servers/{server_id}", response_model=ServerStatusResponse)
async def get_server(server_id: str):
    """Get server status"""
    try:
        server = await server_manager.get_server(server_id)
        if not server:
            raise HTTPException(404, "Server not found")
        
        return ServerStatusResponse(
            server_id=server.server_id,
            status=server.status.value,
            port=server.port,
            created_at=server.created_at.isoformat(),
            started_at=server.started_at.isoformat() if server.started_at else None,
            resource_usage=server.resource_usage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get server failed: {e}")
        raise HTTPException(500, f"Get server failed: {str(e)}")

@app.post("/servers/{server_id}/start")
async def start_server(server_id: str):
    """Start RDP server"""
    try:
        result = await server_manager.start_server(server_id)
        return result
        
    except Exception as e:
        logger.error(f"Start server failed: {e}")
        raise HTTPException(500, f"Start server failed: {str(e)}")

@app.post("/servers/{server_id}/stop")
async def stop_server(server_id: str):
    """Stop RDP server"""
    try:
        result = await server_manager.stop_server(server_id)
        return result
        
    except Exception as e:
        logger.error(f"Stop server failed: {e}")
        raise HTTPException(500, f"Stop server failed: {str(e)}")

@app.post("/servers/{server_id}/restart")
async def restart_server(server_id: str):
    """Restart RDP server"""
    try:
        result = await server_manager.restart_server(server_id)
        return result
        
    except Exception as e:
        logger.error(f"Restart server failed: {e}")
        raise HTTPException(500, f"Restart server failed: {str(e)}")

@app.get("/servers")
async def list_servers():
    """List all active servers"""
    try:
        servers = await server_manager.list_servers()
        return {
            "servers": [
                {
                    "server_id": server.server_id,
                    "user_id": server.user_id,
                    "session_id": server.session_id,
                    "status": server.status.value,
                    "port": server.port,
                    "created_at": server.created_at.isoformat()
                }
                for server in servers
            ],
            "total": len(servers),
            "max_servers": MAX_CONCURRENT_SERVERS
        }
        
    except Exception as e:
        logger.error(f"List servers failed: {e}")
        raise HTTPException(500, f"List servers failed: {str(e)}")

@app.delete("/servers/{server_id}")
async def delete_server(server_id: str):
    """Delete RDP server"""
    try:
        result = await server_manager.delete_server(server_id)
        return result
        
    except Exception as e:
        logger.error(f"Delete server failed: {e}")
        raise HTTPException(500, f"Delete server failed: {str(e)}")

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info(f"Starting {SERVICE_NAME}...")
    
    # Initialize components
    await config_manager.initialize()
    await port_manager.initialize()
    await server_manager.initialize()
    
    logger.info(f"{SERVICE_NAME} started on port {SERVICE_PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info(f"Shutting down {SERVICE_NAME}...")
    
    # Stop all active servers
    await server_manager.shutdown()
    
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
