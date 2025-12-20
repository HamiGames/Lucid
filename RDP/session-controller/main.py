"""
RDP Session Controller - Main Entry Point

FastAPI application for RDP session management service.
"""

import asyncio
import logging
import os
import sys
import uvicorn
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

from session_controller import SessionController
from connection_manager import ConnectionManager
from common.models import RdpSession, SessionStatus, SessionMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
connection_manager = None
session_controller = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""
    global connection_manager, session_controller
    
    # Startup
    logger.info("Starting RDP Session Controller")
    
    connection_manager = ConnectionManager()
    session_controller = SessionController(connection_manager)
    
    # Start background monitoring tasks
    asyncio.create_task(session_controller.start_session_monitoring())
    asyncio.create_task(connection_manager.start_connection_monitoring())
    
    logger.info("RDP Session Controller started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RDP Session Controller")
    logger.info("RDP Session Controller shut down successfully")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Lucid RDP Session Controller",
        description="RDP session management and monitoring service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "rdp-session-controller",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Session management endpoints
    @app.post("/api/v1/sessions", response_model=dict)
    async def create_session(
        user_id: str,
        server_id: UUID,
        session_config: dict
    ):
        """Create a new RDP session"""
        try:
            session = await session_controller.create_session(
                user_id=user_id,
                server_id=server_id,
                session_config=session_config
            )
            return session.to_dict()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create session: {str(e)}"
            )
    
    @app.get("/api/v1/sessions/{session_id}")
    async def get_session(session_id: UUID):
        """Get session by ID"""
        session = await session_controller.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        return session.to_dict()
    
    @app.get("/api/v1/sessions")
    async def list_sessions(user_id: str = None):
        """List sessions"""
        if user_id:
            sessions = await session_controller.list_user_sessions(user_id)
        else:
            sessions = list(session_controller.active_sessions.values())
        
        return [session.to_dict() for session in sessions]
    
    @app.put("/api/v1/sessions/{session_id}/status")
    async def update_session_status(
        session_id: UUID,
        status: str
    ):
        """Update session status"""
        try:
            session_status = SessionStatus(status)
            success = await session_controller.update_session_status(
                session_id, session_status
            )
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            return {"status": "updated"}
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status"
            )
    
    @app.delete("/api/v1/sessions/{session_id}")
    async def terminate_session(session_id: UUID):
        """Terminate a session"""
        success = await session_controller.terminate_session(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        return {"status": "terminated"}
    
    @app.get("/api/v1/sessions/{session_id}/metrics")
    async def get_session_metrics(session_id: UUID):
        """Get session metrics"""
        metrics = await session_controller.get_session_metrics(session_id)
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session metrics not found"
            )
        return metrics.to_dict()
    
    @app.get("/api/v1/sessions/{session_id}/health")
    async def get_session_health(session_id: UUID):
        """Get session health status"""
        health = await session_controller.get_session_health(session_id)
        return health
    
    # Connection management endpoints
    @app.get("/api/v1/connections")
    async def list_connections(server_id: UUID = None):
        """List connections"""
        connections = await connection_manager.list_connections(server_id)
        return [conn.to_dict() for conn in connections]
    
    @app.get("/api/v1/connections/{connection_id}/health")
    async def get_connection_health(connection_id: UUID):
        """Get connection health"""
        health = await connection_manager.check_connection_health(connection_id)
        return health
    
    @app.get("/api/v1/connections/{connection_id}/metrics")
    async def get_connection_metrics(connection_id: UUID):
        """Get connection metrics"""
        metrics = await connection_manager.get_connection_metrics(connection_id)
        return metrics
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "LUCID_ERR_2200",
                    "message": "Internal server error",
                    "service": "rdp-session-controller",
                    "version": "v1"
                }
            }
        )
    
    return app

app = create_app()

if __name__ == "__main__":
    import os
    # Get configuration from environment (from docker-compose.application.yml)
    host = "0.0.0.0"  # Always bind to all interfaces in container
    port_str = os.getenv("RDP_CONTROLLER_PORT", "8092")
    try:
        port = int(port_str)
    except ValueError:
        logger.error(f"Invalid RDP_CONTROLLER_PORT value: {port_str}")
        sys.exit(1)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
