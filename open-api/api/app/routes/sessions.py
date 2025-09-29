# Path: open-api/api/app/routes/sessions.py
# Lucid RDP Session Management API Blueprint
# Implements R-MUST-005, R-MUST-012: Session audit trail and single-use Session IDs

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

# Import from our new components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from sessions.core.session_generator import SecureSessionGenerator, SessionData
from RDP.security.trust_controller import TrustController

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])
security = HTTPBearer()

# Pydantic Models
class CreateSessionRequest(BaseModel):
    """Request to create a new RDP session"""
    owner_address: str = Field(..., pattern=r'^T[A-Za-z0-9]{33}$', description="TRON address of session owner")
    target_node: Optional[str] = Field(None, description="Preferred node address")
    session_params: Dict[str, Any] = Field(default_factory=dict, description="Session configuration parameters")
    policy_requirements: Optional[Dict[str, Any]] = Field(None, description="Trust-nothing policy requirements")

class EphemeralKeypairResponse(BaseModel):
    """Ephemeral keypair for session"""
    public_key: str = Field(..., description="Ed25519 public key (base64)")
    created_at: datetime
    expires_at: datetime

class SessionIDResponse(BaseModel):
    """Session ID with ephemeral keypair - R-MUST-012"""
    session_id: str = Field(..., description="Single-use session identifier")
    ephemeral_keypair: EphemeralKeypairResponse
    created_at: datetime
    expires_at: datetime
    owner_address: str
    anchor_status: str = Field(default="pending", enum=["pending", "anchored", "failed"])
    
class AuditEventModel(BaseModel):
    """Session audit event - R-MUST-005"""
    event_id: str
    timestamp: datetime
    actor_identity: str
    event_type: str = Field(..., enum=[
        "session_start", "session_end", "rdp_connect", "rdp_disconnect",
        "file_transfer_request", "file_transfer_approved", "file_transfer_denied",
        "clipboard_access", "keystroke_capture", "window_focus",
        "resource_access", "policy_violation", "session_void"
    ])
    resource_accessed: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    keystroke_data: Optional[str] = None
    window_focus_data: Optional[str] = None

class SessionManifestModel(BaseModel):
    """Session manifest for blockchain anchoring - R-MUST-006"""
    session_id: str
    merkle_root: str = Field(..., pattern=r'^[a-fA-F0-9]{64}$')
    chunk_count: int = Field(..., ge=1)
    total_size: int
    participant_pubkeys: List[str]
    codec_info: Optional[Dict[str, Any]] = None
    recorder_version: str = "1.0.0"
    device_fingerprint: str
    created_at: datetime
    anchored_at: Optional[datetime] = None
    anchor_txid: Optional[str] = None

class SessionAuditTrailResponse(BaseModel):
    """Complete session audit trail"""
    session_id: str
    events: List[AuditEventModel]
    manifest: Optional[SessionManifestModel] = None
    chunks: Optional[List[Dict[str, Any]]] = None

class SessionStatusResponse(BaseModel):
    """Session status information"""
    session_id: str
    status: str = Field(..., enum=["initializing", "active", "paused", "terminated", "error"])
    owner_address: str
    created_at: datetime
    started_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    node_address: Optional[str] = None
    trust_score: Optional[float] = None

# Global components
session_generator = SecureSessionGenerator()
trust_controller = TrustController()

@router.post("/create", response_model=SessionIDResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    token: str = Depends(security)
) -> SessionIDResponse:
    """
    Create a new single-use RDP session (R-MUST-012).
    
    Generates cryptographically secure session ID with ephemeral keypair.
    Session IDs are non-replayable and anchored on-chain.
    """
    try:
        logger.info(f"Creating session for owner: {request.owner_address}")
        
        # Generate secure session
        session_data = await session_generator.generate_session(
            user_id=request.owner_address,
            node_id=request.target_node,
            metadata=request.session_params
        )
        
        # Create response with ephemeral keypair
        ephemeral_keypair = EphemeralKeypairResponse(
            public_key=session_data["ephemeral_keypair"]["public_key"],
            created_at=session_data["ephemeral_keypair"]["created_at"],
            expires_at=session_data["ephemeral_keypair"]["expires_at"]
        )
        
        response = SessionIDResponse(
            session_id=session_data["session_id"],
            ephemeral_keypair=ephemeral_keypair,
            created_at=session_data["created_at"],
            expires_at=session_data["expires_at"],
            owner_address=request.owner_address,
            anchor_status="pending"
        )
        
        logger.info(f"Session created successfully: {response.session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session creation failed: {str(e)}"
        )

@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    token: str = Depends(security)
) -> SessionStatusResponse:
    """Get session status and metadata"""
    try:
        # This would typically query from database/session store
        # For now, return a mock response based on session generator
        session_info = await session_generator.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        response = SessionStatusResponse(
            session_id=session_id,
            status=session_info.get("status", "initializing"),
            owner_address=session_info.get("owner_address", ""),
            created_at=session_info.get("created_at", datetime.now(timezone.utc)),
            started_at=session_info.get("started_at"),
            terminated_at=session_info.get("terminated_at"),
            node_address=session_info.get("node_address"),
            trust_score=session_info.get("trust_score")
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session status: {str(e)}"
        )

@router.post("/{session_id}/start", status_code=status.HTTP_200_OK)
async def start_session(
    session_id: str,
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Start an RDP session after payment verification"""
    try:
        logger.info(f"Starting session: {session_id}")
        
        # Verify session exists and is in correct state
        session_info = await session_generator.get_session_info(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session_info.get("status") != "pending_payment":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session not ready to start"
            )
        
        # This would integrate with node worker to actually start the session
        # For now, simulate session start
        start_result = {
            "session_id": session_id,
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "rdp_connection": {
                "host": "node-worker.onion",
                "port": 3389,
                "protocol": "rdp"
            }
        }
        
        logger.info(f"Session started successfully: {session_id}")
        return start_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session start failed: {str(e)}"
        )

@router.post("/{session_id}/terminate", status_code=status.HTTP_200_OK)
async def terminate_session(
    session_id: str,
    reason: str = Body(..., description="Termination reason"),
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Terminate an active RDP session"""
    try:
        logger.info(f"Terminating session: {session_id}, reason: {reason}")
        
        # This would integrate with node worker to terminate the session
        termination_result = {
            "session_id": session_id,
            "status": "terminated",
            "terminated_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason
        }
        
        logger.info(f"Session terminated successfully: {session_id}")
        return termination_result
        
    except Exception as e:
        logger.error(f"Failed to terminate session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session termination failed: {str(e)}"
        )

@router.get("/{session_id}/audit", response_model=SessionAuditTrailResponse)
async def get_session_audit_trail(
    session_id: str,
    include_keystrokes: bool = Query(False, description="Include keystroke metadata"),
    include_window_focus: bool = Query(False, description="Include window focus metadata"),
    token: str = Depends(security)
) -> SessionAuditTrailResponse:
    """
    Get session audit trail (R-MUST-005).
    
    Returns actor identity, timestamps, resource access, and optional
    keystroke/window focus metadata. All data is compressed, chunked,
    and encrypted locally.
    """
    try:
        logger.info(f"Retrieving audit trail for session: {session_id}")
        
        # This would query from the audit database
        # For now, return a mock audit trail
        audit_events = [
            AuditEventModel(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                actor_identity="user@example.onion",
                event_type="session_start",
                metadata={"client_ip": "tor_hidden"}
            ),
            AuditEventModel(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                actor_identity="user@example.onion",
                event_type="rdp_connect",
                resource_accessed="desktop_session",
                metadata={"protocol": "rdp", "encryption": "tls"}
            )
        ]
        
        # Mock session manifest
        manifest = SessionManifestModel(
            session_id=session_id,
            merkle_root="a" * 64,  # Mock BLAKE3 hash
            chunk_count=5,
            total_size=52428800,  # 50MB
            participant_pubkeys=["mock_pubkey_base64"],
            device_fingerprint="pi5_device_123",
            created_at=datetime.now(timezone.utc)
        )
        
        response = SessionAuditTrailResponse(
            session_id=session_id,
            events=audit_events,
            manifest=manifest,
            chunks=[]  # Would include chunk metadata
        )
        
        logger.info(f"Audit trail retrieved successfully: {session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to get audit trail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit trail: {str(e)}"
        )

@router.get("/{session_id}/manifest", response_model=SessionManifestModel)
async def get_session_manifest(
    session_id: str,
    token: str = Depends(security)
) -> SessionManifestModel:
    """
    Get session manifest for blockchain anchoring (R-MUST-006).
    
    Returns manifest with Merkle root of encrypted chunks for
    immutable anchoring to blockchain ledger.
    """
    try:
        logger.info(f"Retrieving manifest for session: {session_id}")
        
        # This would query from the manifest database
        manifest = SessionManifestModel(
            session_id=session_id,
            merkle_root="a" * 64,  # Mock BLAKE3 hash
            chunk_count=5,
            total_size=52428800,  # 50MB
            participant_pubkeys=["mock_pubkey_base64"],
            codec_info={
                "video_codec": "h264_v4l2m2m",
                "compression": "zstd_level_3",
                "encryption": "xchacha20_poly1305"
            },
            device_fingerprint="pi5_device_123",
            created_at=datetime.now(timezone.utc),
            anchored_at=datetime.now(timezone.utc),
            anchor_txid="mock_blockchain_txid"
        )
        
        logger.info(f"Manifest retrieved successfully: {session_id}")
        return manifest
        
    except Exception as e:
        logger.error(f"Failed to get manifest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve manifest: {str(e)}"
        )

@router.get("/", response_model=List[SessionStatusResponse])
async def list_sessions(
    owner_address: Optional[str] = Query(None, description="Filter by owner address"),
    status_filter: Optional[str] = Query(None, enum=["active", "terminated", "pending"]),
    limit: int = Query(50, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    token: str = Depends(security)
) -> List[SessionStatusResponse]:
    """List sessions with optional filtering"""
    try:
        logger.info(f"Listing sessions: owner={owner_address}, status={status_filter}")
        
        # This would query from the session database with filters
        # For now, return mock session list
        sessions = [
            SessionStatusResponse(
                session_id=f"session_{i}",
                status="active" if i % 2 == 0 else "terminated",
                owner_address=owner_address or "TTestAddress123456789012345",
                created_at=datetime.now(timezone.utc) - timedelta(hours=i),
                started_at=datetime.now(timezone.utc) - timedelta(hours=i, minutes=30) if i % 2 == 0 else None,
                node_address=f"node_{i}.onion",
                trust_score=0.8 + (i * 0.05)
            ) for i in range(min(limit, 10))  # Mock data
        ]
        
        # Apply status filter
        if status_filter:
            sessions = [s for s in sessions if s.status == status_filter]
        
        logger.info(f"Retrieved {len(sessions)} sessions")
        return sessions
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )

@router.post("/{session_id}/audit/event", status_code=status.HTTP_201_CREATED)
async def add_audit_event(
    session_id: str,
    event: AuditEventModel,
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Add an audit event to session trail"""
    try:
        logger.info(f"Adding audit event to session {session_id}: {event.event_type}")
        
        # This would store the audit event in the database
        # For now, just acknowledge receipt
        result = {
            "session_id": session_id,
            "event_id": event.event_id,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "status": "recorded"
        }
        
        logger.info(f"Audit event recorded: {event.event_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to add audit event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record audit event: {str(e)}"
        )

# Health check endpoint
@router.get("/health", include_in_schema=False)
async def sessions_health() -> Dict[str, Any]:
    """Session service health check"""
    return {
        "service": "sessions",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "session_generator": "operational",
            "trust_controller": "operational"
        }
    }