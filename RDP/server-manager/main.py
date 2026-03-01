#!/usr/bin/env python3
"""
LUCID RDP Server Manager Service - Main Entry Point
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

from .server_manager import RDPServerManager
from .port_manager import PortManager
from .config_manager import ConfigManager
from .config import RDPServerManagerConfigManager

# Configure logging (structured logging per master design)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
server_manager_instance: Optional[RDPServerManager] = None
port_manager_instance: Optional[PortManager] = None
config_manager_instance: Optional[ConfigManager] = None
config_manager: Optional[RDPServerManagerConfigManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global server_manager_instance, port_manager_instance, config_manager_instance, config_manager
    
    # Startup
    logger.info("Starting RDP Server Manager Service...")
    
    try:
        # Initialize configuration using Pydantic Settings (per master design)
        config_manager = RDPServerManagerConfigManager()
        
        # Get configuration dictionary
        config_dict = config_manager.get_server_manager_config_dict()
        
        # Get database URLs from settings (already validated)
        mongo_url = config_manager.get_mongodb_url()
        redis_url = config_manager.get_redis_url()
        
        # Initialize components
        config_manager_instance = ConfigManager()
        await config_manager_instance.initialize()
        
        port_manager_instance = PortManager(
            config_dict["port_range_start"],
            config_dict["port_range_end"]
        )
        await port_manager_instance.initialize()
        
        server_manager_instance = RDPServerManager(config_manager_instance, port_manager_instance)
        await server_manager_instance.initialize()
        
        logger.info("RDP Server Manager Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start RDP Server Manager Service: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown (graceful shutdown per master design)
        logger.info("Shutting down RDP Server Manager Service...")
        
        try:
            if server_manager_instance:
                await server_manager_instance.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

# Create FastAPI application
app = FastAPI(
    title="RDP Server Manager Service",
    description="RDP server lifecycle management for Lucid system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global server_manager_instance, port_manager_instance, config_manager
    return {
        "status": "healthy",
        "service": "rdp-server-manager",
        "timestamp": datetime.utcnow().isoformat(),
        "active_servers": len(server_manager_instance.active_servers) if server_manager_instance else 0,
        "max_servers": config_manager.get_server_manager_config_dict()["max_concurrent_servers"] if config_manager else 50,
        "available_ports": port_manager_instance.get_available_ports_count() if port_manager_instance else 0
    }

@app.post("/servers", response_model=ServerResponse)
async def create_server(request: CreateServerRequest):
    """Create new RDP server instance"""
    global server_manager_instance, config_manager
    try:
        # Check server limits
        max_servers = config_manager.get_server_manager_config_dict()["max_concurrent_servers"] if config_manager else 50
        if len(server_manager_instance.active_servers) >= max_servers:
            raise HTTPException(429, "Maximum concurrent servers reached")
        
        # Create server
        server = await server_manager_instance.create_server(
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
    global server_manager_instance
    try:
        server = await server_manager_instance.get_server(server_id)
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
    global server_manager_instance
    try:
        result = await server_manager_instance.start_server(server_id)
        return result
        
    except Exception as e:
        logger.error(f"Start server failed: {e}")
        raise HTTPException(500, f"Start server failed: {str(e)}")

@app.post("/servers/{server_id}/stop")
async def stop_server(server_id: str):
    """Stop RDP server"""
    global server_manager_instance
    try:
        result = await server_manager_instance.stop_server(server_id)
        return result
        
    except Exception as e:
        logger.error(f"Stop server failed: {e}")
        raise HTTPException(500, f"Stop server failed: {str(e)}")

@app.post("/servers/{server_id}/restart")
async def restart_server(server_id: str):
    """Restart RDP server"""
    global server_manager_instance
    try:
        result = await server_manager_instance.restart_server(server_id)
        return result
        
    except Exception as e:
        logger.error(f"Restart server failed: {e}")
        raise HTTPException(500, f"Restart server failed: {str(e)}")

@app.get("/servers")
async def list_servers():
    """List all active servers"""
    global server_manager_instance, config_manager
    try:
        servers = await server_manager_instance.list_servers()
        max_servers = config_manager.get_server_manager_config_dict()["max_concurrent_servers"] if config_manager else 50
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
            "max_servers": max_servers
        }
        
    except Exception as e:
        logger.error(f"List servers failed: {e}")
        raise HTTPException(500, f"List servers failed: {str(e)}")

@app.delete("/servers/{server_id}")
async def delete_server(server_id: str):
    """Delete RDP server"""
    global server_manager_instance
    try:
        result = await server_manager_instance.delete_server(server_id)
        return result
        
    except Exception as e:
        logger.error(f"Delete server failed: {e}")
        raise HTTPException(500, f"Delete server failed: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "rdp-server-manager", "status": "running"}
