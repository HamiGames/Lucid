# LUCID RDP Server Manager - Main RDP server coordination
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx

# Database integration
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None

logger = logging.getLogger(__name__)

# Configuration from environment
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin")
RDP_SESSIONS_PATH = Path(os.getenv("RDP_SESSIONS_PATH", "/data/sessions"))
RDP_RECORDINGS_PATH = Path(os.getenv("RDP_RECORDINGS_PATH", "/data/recordings"))
RDP_DISPLAY_PATH = Path(os.getenv("RDP_DISPLAY_PATH", "/data/display"))
XRDP_PORT = int(os.getenv("XRDP_PORT", "3389"))
MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", "5"))


class SessionStatus(Enum):
    """RDP session status states"""
    CREATING = "creating"
    ACTIVE = "active"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RDPSession:
    """RDP session metadata"""
    session_id: str
    owner_address: str
    node_id: str
    status: SessionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    recording_path: Optional[Path] = None
    display_config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RDPServerManager:
    """
    Main RDP server manager for Lucid RDP system.
    
    Coordinates RDP session hosting, xrdp integration, and session recording.
    Implements LUCID-STRICT Layer 2 Service Integration requirements.
    """
    
    def __init__(self):
        """Initialize RDP server manager"""
        self.app = FastAPI(
            title="Lucid RDP Server Manager",
            description="RDP server coordination for Lucid RDP system",
            version="1.0.0"
        )
        
        # Database connection
        self.db_client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
        # Session tracking
        self.active_sessions: Dict[str, RDPSession] = {}
        self.session_tasks: Dict[str, asyncio.Task] = {}
        
        # Service URLs
        self.session_orchestrator_url = os.getenv(
            "SESSION_ORCHESTRATOR_URL", 
            "http://session-orchestrator:8084"
        )
        
        # Setup routes
        self._setup_routes()
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create required directories"""
        for path in [RDP_SESSIONS_PATH, RDP_RECORDINGS_PATH, RDP_DISPLAY_PATH]:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "rdp-server-manager",
                "active_sessions": len(self.active_sessions),
                "max_sessions": MAX_CONCURRENT_SESSIONS
            }
        
        @self.app.post("/sessions/create")
        async def create_rdp_session(request: CreateSessionRequest):
            """Create new RDP session"""
            return await self.create_session(
                owner_address=request.owner_address,
                node_id=request.node_id,
                metadata=request.metadata
            )
        
        @self.app.get("/sessions/{session_id}")
        async def get_session(session_id: str):
            """Get session information"""
            if session_id not in self.active_sessions:
                raise HTTPException(404, "Session not found")
            
            session = self.active_sessions[session_id]
            return {
                "session_id": session.session_id,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "recording_path": str(session.recording_path) if session.recording_path else None
            }
        
        @self.app.post("/sessions/{session_id}/start")
        async def start_session(session_id: str):
            """Start RDP session"""
            return await self.start_rdp_session(session_id)
        
        @self.app.post("/sessions/{session_id}/stop")
        async def stop_session(session_id: str):
            """Stop RDP session"""
            return await self.stop_rdp_session(session_id)
        
        @self.app.get("/sessions")
        async def list_sessions():
            """List all active sessions"""
            return {
                "sessions": [
                    {
                        "session_id": session.session_id,
                        "owner_address": session.owner_address,
                        "status": session.status.value,
                        "created_at": session.created_at.isoformat()
                    }
                    for session in self.active_sessions.values()
                ]
            }
    
    async def _setup_database(self) -> None:
        """Setup database connection"""
        if not HAS_MOTOR:
            logger.warning("Motor not available, database operations disabled")
            return
        
        try:
            self.db_client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.db_client.lucid
            
            # Test connection
            await self.db_client.admin.command('ping')
            logger.info("Database connection established")
            
            # Create indexes
            await self._create_database_indexes()
            
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            self.db_client = None
            self.db = None
    
    async def _create_database_indexes(self) -> None:
        """Create database indexes for RDP sessions"""
        if not self.db:
            return
        
        try:
            # RDP sessions collection
            await self.db.rdp_sessions.create_index("session_id", unique=True)
            await self.db.rdp_sessions.create_index("owner_address")
            await self.db.rdp_sessions.create_index("status")
            await self.db.rdp_sessions.create_index("created_at")
            
            logger.info("Database indexes created")
            
        except Exception as e:
            logger.error(f"Database index creation failed: {e}")
    
    async def create_session(self, 
                           owner_address: str, 
                           node_id: str,
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create new RDP session"""
        try:
            # Check session limits
            if len(self.active_sessions) >= MAX_CONCURRENT_SESSIONS:
                raise HTTPException(429, "Maximum concurrent sessions reached")
            
            # Generate session ID
            session_id = f"rdp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
            
            # Create session object
            session = RDPSession(
                session_id=session_id,
                owner_address=owner_address,
                node_id=node_id,
                status=SessionStatus.CREATING,
                created_at=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            
            # Store in memory
            self.active_sessions[session_id] = session
            
            # Store in database
            if self.db:
                await self.db.rdp_sessions.insert_one(session.__dict__)
            
            logger.info(f"Created RDP session: {session_id}")
            
            return {
                "session_id": session_id,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "rdp_port": XRDP_PORT,
                "connection_info": {
                    "host": "localhost",
                    "port": XRDP_PORT,
                    "username": f"lucid_{session_id[:8]}",
                    "password": f"lucid_{session_id[-8:]}"
                }
            }
            
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            raise HTTPException(500, f"Session creation failed: {str(e)}")
    
    async def start_rdp_session(self, session_id: str) -> Dict[str, Any]:
        """Start RDP session"""
        if session_id not in self.active_sessions:
            raise HTTPException(404, "Session not found")
        
        session = self.active_sessions[session_id]
        
        try:
            # Update status
            session.status = SessionStatus.ACTIVE
            session.started_at = datetime.now(timezone.utc)
            
            # Setup recording path
            session.recording_path = RDP_RECORDINGS_PATH / session_id
            session.recording_path.mkdir(parents=True, exist_ok=True)
            
            # Start session task
            task = asyncio.create_task(self._run_rdp_session(session))
            self.session_tasks[session_id] = task
            
            # Update database
            if self.db:
                await self.db.rdp_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "status": session.status.value,
                        "started_at": session.started_at,
                        "recording_path": str(session.recording_path)
                    }}
                )
            
            logger.info(f"Started RDP session: {session_id}")
            
            return {
                "session_id": session_id,
                "status": session.status.value,
                "started_at": session.started_at.isoformat(),
                "recording_path": str(session.recording_path)
            }
            
        except Exception as e:
            logger.error(f"Session start failed: {e}")
            session.status = SessionStatus.FAILED
            raise HTTPException(500, f"Session start failed: {str(e)}")
    
    async def stop_rdp_session(self, session_id: str) -> Dict[str, Any]:
        """Stop RDP session"""
        if session_id not in self.active_sessions:
            raise HTTPException(404, "Session not found")
        
        session = self.active_sessions[session_id]
        
        try:
            # Update status
            session.status = SessionStatus.STOPPING
            session.ended_at = datetime.now(timezone.utc)
            
            # Cancel session task
            if session_id in self.session_tasks:
                self.session_tasks[session_id].cancel()
                del self.session_tasks[session_id]
            
            # Update database
            if self.db:
                await self.db.rdp_sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "status": session.status.value,
                        "ended_at": session.ended_at
                    }}
                )
            
            # Cleanup
            del self.active_sessions[session_id]
            
            logger.info(f"Stopped RDP session: {session_id}")
            
            return {
                "session_id": session_id,
                "status": "stopped",
                "ended_at": session.ended_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Session stop failed: {e}")
            raise HTTPException(500, f"Session stop failed: {str(e)}")
    
    async def _run_rdp_session(self, session: RDPSession) -> None:
        """Run RDP session (simulated)"""
        try:
            logger.info(f"Running RDP session: {session.session_id}")
            
            # Simulate RDP session running
            # In real implementation, this would coordinate with xrdp
            session.status = SessionStatus.ACTIVE
            
            # Simulate session duration
            await asyncio.sleep(60)  # 1 minute simulation
            
            # Mark as completed
            session.status = SessionStatus.COMPLETED
            session.ended_at = datetime.now(timezone.utc)
            
            logger.info(f"RDP session completed: {session.session_id}")
            
        except asyncio.CancelledError:
            logger.info(f"RDP session cancelled: {session.session_id}")
            session.status = SessionStatus.STOPPING
        except Exception as e:
            logger.error(f"RDP session error: {e}")
            session.status = SessionStatus.FAILED


# Pydantic models
class CreateSessionRequest(BaseModel):
    owner_address: str
    node_id: str
    metadata: Optional[Dict[str, Any]] = None


# Global manager instance
rdp_manager = RDPServerManager()

# FastAPI app instance
app = rdp_manager.app

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting RDP Server Manager...")
    await rdp_manager._setup_database()
    logger.info("RDP Server Manager started")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down RDP Server Manager...")
    
    # Stop all active sessions
    for session_id in list(rdp_manager.active_sessions.keys()):
        await rdp_manager.stop_rdp_session(session_id)
    
    # Close database connection
    if rdp_manager.db_client:
        rdp_manager.db_client.close()
    
    logger.info("RDP Server Manager stopped")


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[rdp-server-manager] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    uvicorn.run(
        "rdp_server_manager:app",
        host="0.0.0.0",
        port=8087,
        log_level="info"
    )


if __name__ == "__main__":
    main()
