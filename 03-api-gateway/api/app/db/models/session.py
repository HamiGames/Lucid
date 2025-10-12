# Path: 03-api-gateway/api/app/db/models/session.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SessionState(str, Enum):
    """Session pipeline states matching sessions/pipeline/pipeline_manager.py"""
    INITIALIZING = "initializing"
    RECORDING = "recording"
    FINALIZING = "finalizing"
    ANCHORING = "anchoring"
    COMPLETED = "completed"
    FAILED = "failed"


class RDPSession(BaseModel):
    """Extended session model with blockchain integration"""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str = Field(..., description="User identifier")
    owner_address: str = Field(..., description="TRON wallet address of session owner")
    node_id: str = Field(..., description="Node identifier for session hosting")
    host: str = Field(..., description="Host address (e.g., raspberry pi host/ip)")
    port: int = Field(..., description="RDP port")
    state: SessionState = Field(default=SessionState.INITIALIZING, description="Current session state")
    policy_hash: Optional[str] = Field(None, description="Hash of trust policy")
    manifest_hash: Optional[str] = Field(None, description="BLAKE3 hash of session manifest")
    merkle_root: Optional[str] = Field(None, description="Merkle tree root hash")
    anchor_txid: Optional[str] = Field(None, description="Blockchain anchor transaction ID")
    total_chunks: Optional[int] = Field(None, description="Total number of session chunks")
    total_size: Optional[int] = Field(None, description="Total session size in bytes")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation timestamp")
    recording_started_at: Optional[datetime] = Field(None, description="Recording start timestamp")
    ended_at: Optional[datetime] = Field(None, description="Session end timestamp")
    
    class Config:
        use_enum_values = True
