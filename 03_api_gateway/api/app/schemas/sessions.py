# Session Management Schemas
# Comprehensive data models for session lifecycle, manifests, and trust policies

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
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


class ChunkState(str, Enum):
    """Chunk processing states"""
    PENDING = "pending"
    ENCRYPTED = "encrypted"
    ANCHORED = "anchored"


class SessionCreate(BaseModel):
    """Request schema for creating a new session"""
    user_id: str = Field(..., description="User identifier")
    owner_address: str = Field(..., description="TRON wallet address of session owner")
    node_id: str = Field(..., description="Node identifier for session hosting")
    policy_hash: Optional[str] = Field(None, description="Hash of trust policy (optional)")
    
    @validator('owner_address')
    def validate_owner_address(cls, v):
        if not v.startswith('T') or len(v) != 34:
            raise ValueError('Invalid TRON address format')
        return v
    
    @validator('node_id')
    def validate_node_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Node ID must be at least 3 characters')
        return v


class SessionResponse(BaseModel):
    """Basic session response schema"""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    owner_address: str = Field(..., description="TRON wallet address")
    node_id: str = Field(..., description="Node identifier")
    state: SessionState = Field(..., description="Current session state")
    created_at: datetime = Field(..., description="Session creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Session start timestamp")
    ended_at: Optional[datetime] = Field(None, description="Session end timestamp")
    policy_hash: Optional[str] = Field(None, description="Trust policy hash")


class SessionDetail(BaseModel):
    """Detailed session response with blockchain metadata"""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    owner_address: str = Field(..., description="TRON wallet address")
    node_id: str = Field(..., description="Node identifier")
    state: SessionState = Field(..., description="Current session state")
    created_at: datetime = Field(..., description="Session creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Session start timestamp")
    ended_at: Optional[datetime] = Field(None, description="Session end timestamp")
    policy_hash: Optional[str] = Field(None, description="Trust policy hash")
    
    # Blockchain metadata (populated after finalization)
    manifest_hash: Optional[str] = Field(None, description="BLAKE3 hash of session manifest")
    merkle_root: Optional[str] = Field(None, description="Merkle tree root hash")
    anchor_txid: Optional[str] = Field(None, description="Blockchain anchor transaction ID")
    total_chunks: Optional[int] = Field(None, description="Total number of session chunks")
    total_size: Optional[int] = Field(None, description="Total session size in bytes")


class SessionList(BaseModel):
    """Paginated session list response"""
    items: List[SessionResponse] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total number of sessions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")


class SessionStateUpdate(BaseModel):
    """Request schema for session state transitions"""
    action: str = Field(..., description="Action to perform: start, finalize, cancel")
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['start', 'finalize', 'cancel']
        if v not in allowed_actions:
            raise ValueError(f'Action must be one of: {allowed_actions}')
        return v


class ManifestResponse(BaseModel):
    """Session manifest with chunk metadata"""
    session_id: str = Field(..., description="Session identifier")
    manifest_hash: str = Field(..., description="BLAKE3 hash of manifest")
    merkle_root: str = Field(..., description="Merkle tree root")
    chunk_count: int = Field(..., description="Total number of chunks")
    total_size: int = Field(..., description="Total session size in bytes")
    created_at: datetime = Field(..., description="Manifest creation timestamp")
    anchor_txid: Optional[str] = Field(None, description="Blockchain transaction ID")


class ChunkMetadata(BaseModel):
    """Individual chunk metadata"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    session_id: str = Field(..., description="Parent session identifier")
    sequence: int = Field(..., description="Chunk sequence number")
    size_bytes: int = Field(..., description="Chunk size in bytes")
    hash: str = Field(..., description="BLAKE3 hash of chunk data")
    state: ChunkState = Field(..., description="Current chunk state")
    encryption_nonce: Optional[str] = Field(None, description="Encryption nonce (base64)")
    created_at: datetime = Field(..., description="Chunk creation timestamp")


class MerkleProof(BaseModel):
    """Merkle proof for chunk verification"""
    chunk_id: str = Field(..., description="Chunk identifier")
    session_id: str = Field(..., description="Session identifier")
    chunk_hash: str = Field(..., description="Chunk data hash")
    merkle_path: List[str] = Field(..., description="Merkle tree path nodes")
    merkle_root: str = Field(..., description="Merkle tree root")
    proof_valid: bool = Field(..., description="Whether proof is valid")


class AnchorReceipt(BaseModel):
    """Blockchain anchor transaction receipt"""
    session_id: str = Field(..., description="Session identifier")
    anchor_txid: str = Field(..., description="Blockchain transaction ID")
    block_number: Optional[int] = Field(None, description="Block number")
    gas_used: Optional[int] = Field(None, description="Gas used for transaction")
    status: str = Field(..., description="Transaction status: pending, confirmed, failed")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")


# Trust Policy Schemas (per SPEC-2)

class InputControls(BaseModel):
    """Input control policy"""
    mouse_enabled: bool = Field(True, description="Allow mouse input")
    keyboard_enabled: bool = Field(True, description="Allow keyboard input")
    mouse_blocklist: List[str] = Field(default_factory=list, description="Blocked mouse actions")
    keyboard_blocklist: List[str] = Field(default_factory=list, description="Blocked keyboard shortcuts")
    mouse_allowlist: Optional[List[str]] = Field(None, description="Allowed mouse actions only")
    keyboard_allowlist: Optional[List[str]] = Field(None, description="Allowed keyboard shortcuts only")


class ClipboardControls(BaseModel):
    """Clipboard control policy"""
    host_to_remote: bool = Field(True, description="Allow clipboard host → remote")
    remote_to_host: bool = Field(True, description="Allow clipboard remote → host")
    max_bytes: int = Field(1024 * 1024, description="Maximum clipboard size (1MB default)")
    allowed_formats: List[str] = Field(default_factory=lambda: ["text/plain"], description="Allowed clipboard formats")


class FileTransferControls(BaseModel):
    """File transfer control policy"""
    upload_enabled: bool = Field(True, description="Allow file uploads")
    download_enabled: bool = Field(True, description="Allow file downloads")
    allowed_dirs: List[str] = Field(default_factory=list, description="Allowed directories")
    blocked_dirs: List[str] = Field(default_factory=list, description="Blocked directories")
    allowed_extensions: List[str] = Field(default_factory=list, description="Allowed file extensions")
    blocked_extensions: List[str] = Field(default_factory=list, description="Blocked file extensions")
    max_file_size: int = Field(100 * 1024 * 1024, description="Maximum file size (100MB default)")


class SystemControls(BaseModel):
    """System access control policy"""
    screenshare_enabled: bool = Field(True, description="Allow screen sharing")
    audio_enabled: bool = Field(True, description="Allow audio access")
    camera_enabled: bool = Field(False, description="Allow camera access")
    printing_enabled: bool = Field(False, description="Allow printing")
    shell_channels: bool = Field(False, description="Allow shell/terminal access")
    system_commands: bool = Field(False, description="Allow system command execution")


class TrustPolicy(BaseModel):
    """Comprehensive trust policy per SPEC-2"""
    policy_id: str = Field(..., description="Unique policy identifier")
    session_id: str = Field(..., description="Associated session identifier")
    input_controls: InputControls = Field(..., description="Input control settings")
    clipboard_controls: ClipboardControls = Field(..., description="Clipboard control settings")
    file_transfer_controls: FileTransferControls = Field(..., description="File transfer control settings")
    system_controls: SystemControls = Field(..., description="System access control settings")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Policy creation timestamp")
    policy_hash: str = Field(..., description="SHA256 hash of policy")
    signature: Optional[str] = Field(None, description="Ed25519 signature of policy")


class PolicyValidationRequest(BaseModel):
    """Request to validate policy before session start"""
    policy: TrustPolicy = Field(..., description="Policy to validate")
    session_id: str = Field(..., description="Session identifier")


class PolicyValidationResponse(BaseModel):
    """Policy validation response"""
    valid: bool = Field(..., description="Whether policy is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    accepted_at: Optional[datetime] = Field(None, description="Policy acceptance timestamp")


# Error Response Schema
class SessionErrorResponse(BaseModel):
    """Error response for session operations"""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
