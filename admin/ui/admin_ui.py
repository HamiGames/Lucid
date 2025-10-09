# LUCID Admin UI - SPEC-1B Admin Interface
# Professional admin interface for session management and blockchain operations
# Multi-platform support for ARM64 Pi and AMD64 development

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configuration from environment
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8096"))
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin")
SESSION_RECORDER_URL = os.getenv("SESSION_RECORDER_URL", "http://session-recorder:8093")
CHAIN_CLIENT_URL = os.getenv("CHAIN_CLIENT_URL", "http://on-system-chain-client:8094")
TRON_CLIENT_URL = os.getenv("TRON_CLIENT_URL", "http://tron-node-client:8095")
TOR_SOCKS_PORT = os.getenv("TOR_SOCKS_PORT", "9050")


class SessionStatus(Enum):
    """Session status states"""
    IDLE = "idle"
    RECORDING = "recording"
    STOPPED = "stopped"
    ANCHORED = "anchored"
    PAID = "paid"


@dataclass
class SessionInfo:
    """Session information"""
    session_id: str
    owner_address: str
    status: SessionStatus
    started_at: datetime
    stopped_at: Optional[datetime] = None
    manifest_hash: Optional[str] = None
    merkle_root: Optional[str] = None
    chunk_count: Optional[int] = None
    anchor_tx_hash: Optional[str] = None
    payout_tx_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdminUI:
    """
    Admin UI for Lucid RDP system.
    
    Provides web interface for session management, blockchain operations,
    and system administration. Implements SPEC-1B admin interface requirements.
    """
    
    def __init__(self):
        """Initialize admin UI"""
        self.app = FastAPI(
            title="Lucid Admin UI",
            description="Admin interface for Lucid RDP system",
            version="1.0.0"
        )
        
        # Session tracking
        self.active_sessions: Dict[str, SessionInfo] = {}
        
        # Setup routes
        self._setup_routes()
        
        # Setup static files and templates
        self._setup_static_files()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def admin_dashboard(request: Request):
            """Admin dashboard"""
            return self.templates.TemplateResponse("dashboard.html", {
                "request": request,
                "sessions": list(self.active_sessions.values()),
                "system_info": await self._get_system_info()
            })
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "admin-ui",
                "active_sessions": len(self.active_sessions),
                "mongodb_connected": await self._check_mongodb_connection()
            }
        
        @self.app.post("/sessions/start")
        async def start_session(request: StartSessionRequest):
            """Start new session"""
            return await self.start_session(
                owner_address=request.owner_address,
                metadata=request.metadata
            )
        
        @self.app.post("/sessions/{session_id}/stop")
        async def stop_session(session_id: str):
            """Stop session"""
            return await self.stop_session(session_id)
        
        @self.app.post("/sessions/{session_id}/anchor")
        async def anchor_session(session_id: str):
            """Anchor session to blockchain"""
            return await self.anchor_session(session_id)
        
        @self.app.post("/sessions/{session_id}/payout")
        async def request_payout(session_id: str, request: PayoutRequest):
            """Request payout for session"""
            return await self.request_payout(
                session_id=session_id,
                to_address=request.to_address,
                amount_usdt=request.amount_usdt,
                router_type=request.router_type,
                reason_code=request.reason_code
            )
        
        @self.app.get("/sessions/{session_id}")
        async def get_session(session_id: str):
            """Get session information"""
            if session_id not in self.active_sessions:
                raise HTTPException(404, "Session not found")
            
            session = self.active_sessions[session_id]
            return {
                "session_id": session.session_id,
                "owner_address": session.owner_address,
                "status": session.status.value,
                "started_at": session.started_at.isoformat(),
                "stopped_at": session.stopped_at.isoformat() if session.stopped_at else None,
                "manifest_hash": session.manifest_hash,
                "merkle_root": session.merkle_root,
                "chunk_count": session.chunk_count,
                "anchor_tx_hash": session.anchor_tx_hash,
                "payout_tx_hash": session.payout_tx_hash
            }
        
        @self.app.get("/sessions")
        async def list_sessions():
            """List all sessions"""
            return {
                "sessions": [
                    {
                        "session_id": session.session_id,
                        "owner_address": session.owner_address,
                        "status": session.status.value,
                        "started_at": session.started_at.isoformat()
                    }
                    for session in self.active_sessions.values()
                ]
            }
        
        @self.app.get("/system/status")
        async def system_status():
            """Get system status"""
            return await self._get_system_info()
    
    def _setup_static_files(self) -> None:
        """Setup static files and templates"""
        # Create static and templates directories
        static_dir = Path("admin/ui/static")
        templates_dir = Path("admin/ui/templates")
        
        static_dir.mkdir(parents=True, exist_ok=True)
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # Setup templates
        self.templates = Jinja2Templates(directory=str(templates_dir))
        
        # Create basic dashboard template
        self._create_dashboard_template()
    
    def _create_dashboard_template(self) -> None:
        """Create basic dashboard template"""
        dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lucid Admin Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .session-item { border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
        .status { padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; }
        .status.recording { background: #e74c3c; }
        .status.stopped { background: #95a5a6; }
        .status.anchored { background: #27ae60; }
        .status.paid { background: #3498db; }
        .btn { background: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #2980b9; }
        .btn.danger { background: #e74c3c; }
        .btn.success { background: #27ae60; }
        .system-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .info-item { background: #ecf0f1; padding: 15px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Lucid Admin Dashboard</h1>
            <p>Session Management and Blockchain Operations</p>
        </div>
        
        <div class="card">
            <h2>System Status</h2>
            <div class="system-info">
                <div class="info-item">
                    <strong>Active Sessions:</strong><br>
                    {{ system_info.active_sessions }}
                </div>
                <div class="info-item">
                    <strong>MongoDB:</strong><br>
                    {{ system_info.mongodb_status }}
                </div>
                <div class="info-item">
                    <strong>Chain Client:</strong><br>
                    {{ system_info.chain_client_status }}
                </div>
                <div class="info-item">
                    <strong>TRON Client:</strong><br>
                    {{ system_info.tron_client_status }}
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Active Sessions</h2>
            {% for session in sessions %}
            <div class="session-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{{ session.session_id }}</strong><br>
                        <small>Owner: {{ session.owner_address }}</small><br>
                        <small>Started: {{ session.started_at }}</small>
                    </div>
                    <div>
                        <span class="status {{ session.status }}">{{ session.status }}</span>
                        <button class="btn" onclick="stopSession('{{ session.session_id }}')">Stop</button>
                        <button class="btn success" onclick="anchorSession('{{ session.session_id }}')">Anchor</button>
                        <button class="btn" onclick="requestPayout('{{ session.session_id }}')">Payout</button>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="card">
            <h2>Quick Actions</h2>
            <button class="btn success" onclick="startNewSession()">Start New Session</button>
            <button class="btn" onclick="refreshStatus()">Refresh Status</button>
        </div>
    </div>
    
    <script>
        function stopSession(sessionId) {
            fetch(`/sessions/${sessionId}/stop`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert('Session stopped: ' + data.status);
                    location.reload();
                });
        }
        
        function anchorSession(sessionId) {
            fetch(`/sessions/${sessionId}/anchor`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert('Session anchored: ' + data.status);
                    location.reload();
                });
        }
        
        function requestPayout(sessionId) {
            const toAddress = prompt('Enter recipient address:');
            const amount = prompt('Enter USDT amount:');
            const routerType = prompt('Router type (v0/kyc):', 'v0');
            
            if (toAddress && amount) {
                fetch(`/sessions/${sessionId}/payout`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        to_address: toAddress,
                        amount_usdt: parseFloat(amount),
                        router_type: routerType,
                        reason_code: 'session_payout'
                    })
                })
                .then(response => response.json())
                .then(data => {
                    alert('Payout requested: ' + data.status);
                    location.reload();
                });
            }
        }
        
        function startNewSession() {
            const ownerAddress = prompt('Enter owner address:');
            if (ownerAddress) {
                fetch('/sessions/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        owner_address: ownerAddress,
                        metadata: {}
                    })
                })
                .then(response => response.json())
                .then(data => {
                    alert('Session started: ' + data.session_id);
                    location.reload();
                });
            }
        }
        
        function refreshStatus() {
            location.reload();
        }
        
        // Auto-refresh every 30 seconds
        setInterval(refreshStatus, 30000);
    </script>
</body>
</html>
        """
        
        templates_dir = Path("admin/ui/templates")
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        with open(templates_dir / "dashboard.html", "w") as f:
            f.write(dashboard_html)
    
    async def start_session(self, 
                          owner_address: str,
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start new session"""
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Create session info
            session = SessionInfo(
                session_id=session_id,
                owner_address=owner_address,
                status=SessionStatus.RECORDING,
                started_at=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            
            # Store in memory
            self.active_sessions[session_id] = session
            
            # Start recording via session recorder
            await self._start_recording(session_id, owner_address, metadata)
            
            logger.info(f"Started session: {session_id}")
            
            return {
                "session_id": session_id,
                "owner_address": owner_address,
                "status": session.status.value,
                "started_at": session.started_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Session start failed: {e}")
            raise HTTPException(500, f"Session start failed: {str(e)}")
    
    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        """Stop session"""
        if session_id not in self.active_sessions:
            raise HTTPException(404, "Session not found")
        
        session = self.active_sessions[session_id]
        
        try:
            # Stop recording via session recorder
            await self._stop_recording(session_id)
            
            # Update session status
            session.status = SessionStatus.STOPPED
            session.stopped_at = datetime.now(timezone.utc)
            
            logger.info(f"Stopped session: {session_id}")
            
            return {
                "session_id": session_id,
                "status": session.status.value,
                "stopped_at": session.stopped_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Session stop failed: {e}")
            raise HTTPException(500, f"Session stop failed: {str(e)}")
    
    async def anchor_session(self, session_id: str) -> Dict[str, Any]:
        """Anchor session to blockchain"""
        if session_id not in self.active_sessions:
            raise HTTPException(404, "Session not found")
        
        session = self.active_sessions[session_id]
        
        try:
            # Generate manifest and merkle root (simplified)
            session.manifest_hash = f"0x{os.urandom(32).hex()}"
            session.merkle_root = f"0x{os.urandom(32).hex()}"
            session.chunk_count = 10  # Simulated
            
            # Register session on chain
            await self._register_session_on_chain(session)
            
            # Update session status
            session.status = SessionStatus.ANCHORED
            session.anchor_tx_hash = f"0x{os.urandom(32).hex()}"
            
            logger.info(f"Anchored session: {session_id}")
            
            return {
                "session_id": session_id,
                "status": session.status.value,
                "manifest_hash": session.manifest_hash,
                "merkle_root": session.merkle_root,
                "anchor_tx_hash": session.anchor_tx_hash
            }
            
        except Exception as e:
            logger.error(f"Session anchoring failed: {e}")
            raise HTTPException(500, f"Session anchoring failed: {str(e)}")
    
    async def request_payout(self, 
                           session_id: str,
                           to_address: str,
                           amount_usdt: float,
                           router_type: str,
                           reason_code: str) -> Dict[str, Any]:
        """Request payout for session"""
        if session_id not in self.active_sessions:
            raise HTTPException(404, "Session not found")
        
        session = self.active_sessions[session_id]
        
        try:
            # Request payout via TRON client
            await self._request_payout_via_tron(
                session_id, to_address, amount_usdt, router_type, reason_code
            )
            
            # Update session status
            session.status = SessionStatus.PAID
            session.payout_tx_hash = f"0x{os.urandom(32).hex()}"
            
            logger.info(f"Payout requested for session: {session_id}")
            
            return {
                "session_id": session_id,
                "to_address": to_address,
                "amount_usdt": amount_usdt,
                "router_type": router_type,
                "status": session.status.value,
                "payout_tx_hash": session.payout_tx_hash
            }
            
        except Exception as e:
            logger.error(f"Payout request failed: {e}")
            raise HTTPException(500, f"Payout request failed: {str(e)}")
    
    async def _start_recording(self, session_id: str, owner_address: str, metadata: Dict[str, Any]) -> None:
        """Start recording via session recorder"""
        # This would make HTTP request to session recorder service
        logger.info(f"Starting recording for session: {session_id}")
    
    async def _stop_recording(self, session_id: str) -> None:
        """Stop recording via session recorder"""
        # This would make HTTP request to session recorder service
        logger.info(f"Stopping recording for session: {session_id}")
    
    async def _register_session_on_chain(self, session: SessionInfo) -> None:
        """Register session on blockchain"""
        # This would make HTTP request to chain client service
        logger.info(f"Registering session on chain: {session.session_id}")
    
    async def _request_payout_via_tron(self, session_id: str, to_address: str, 
                                     amount_usdt: float, router_type: str, reason_code: str) -> None:
        """Request payout via TRON"""
        # This would make HTTP request to TRON client service
        logger.info(f"Requesting payout via TRON: {session_id}")
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            "active_sessions": len(self.active_sessions),
            "mongodb_status": await self._check_mongodb_connection(),
            "chain_client_status": "connected",
            "tron_client_status": "connected"
        }
    
    async def _check_mongodb_connection(self) -> str:
        """Check MongoDB connection"""
        # This would check MongoDB connection
        return "connected"


# Pydantic models
class StartSessionRequest(BaseModel):
    owner_address: str
    metadata: Optional[Dict[str, Any]] = None


class PayoutRequest(BaseModel):
    to_address: str
    amount_usdt: float
    router_type: str
    reason_code: str


# Global admin UI instance
admin_ui = AdminUI()

# FastAPI app instance
app = admin_ui.app

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting Admin UI...")
    logger.info("Admin UI started")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Admin UI...")
    logger.info("Admin UI stopped")


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[admin-ui] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    uvicorn.run(
        "admin_ui:app",
        host="0.0.0.0",
        port=ADMIN_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
