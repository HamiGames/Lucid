"""
Session Data Models

Models for session management operations including:
- Session creation and lifecycle
- Session manifests
- Chunks and Merkle trees
- Session status tracking

All session models integrate with Cluster 03 (Session Management).
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session status values"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class PipelineState(str, Enum):
    """Session pipeline state"""
    CREATED = "created"
    RECORDING = "recording"
    PROCESSING = "processing"
    ENCRYPTING = "encrypting"
    STORING = "storing"
    ANCHORING = "anchoring"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionCreateRequest(BaseModel):
    """
    Request model for creating a new session.
    
    Attributes:
        configuration: Session configuration parameters
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "configuration": {
                "screen_resolution": "1920x1080",
                "color_depth": 24,
                "compression_enabled": True
            }
        }
    })
    
    configuration: Optional[Dict[str, Any]] = Field(
        None,
        description="Session configuration parameters"
    )


class SessionResponse(BaseModel):
    """
    Standard session response model.
    
    Attributes:
        session_id: Unique session identifier
        user_id: Owner user identifier
        status: Current session status
        created_at: Session creation timestamp
        rdp_host: RDP server hostname
        rdp_port: RDP server port
        connection_url: Full RDP connection URL
        expires_at: Session expiration timestamp
        configuration: Session configuration
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_id": "sess-123",
            "user_id": "user-123",
            "status": "active",
            "created_at": "2025-10-14T12:00:00Z",
            "rdp_host": "localhost",
            "rdp_port": 13389,
            "connection_url": "rdp://localhost:13389?session=sess-123",
            "expires_at": "2025-10-14T13:00:00Z",
            "configuration": {}
        }
    })
    
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    status: str = Field(..., description="Session status")
    created_at: datetime = Field(..., description="Creation timestamp")
    rdp_host: str = Field(..., description="RDP hostname")
    rdp_port: int = Field(..., description="RDP port")
    connection_url: str = Field(..., description="Connection URL")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    configuration: Dict[str, Any] = Field(..., description="Configuration")


class SessionDetail(BaseModel):
    """
    Detailed session information model.
    
    Includes complete session data and pipeline state.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_id": "sess-123",
            "user_id": "user-123",
            "status": "active",
            "created_at": "2025-10-14T12:00:00Z",
            "started_at": "2025-10-14T12:00:00Z",
            "ended_at": None,
            "rdp_host": "localhost",
            "rdp_port": 13389,
            "connection_url": "rdp://localhost:13389?session=sess-123",
            "configuration": {},
            "pipeline_state": "recording",
            "chunks_processed": 0,
            "total_size_bytes": 0,
            "merkle_root": None,
            "blockchain_anchor": None,
            "metadata": {}
        }
    })
    
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    status: str = Field(..., description="Session status")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    ended_at: Optional[datetime] = Field(None, description="End timestamp")
    rdp_host: str = Field(..., description="RDP hostname")
    rdp_port: int = Field(..., description="RDP port")
    connection_url: str = Field(..., description="Connection URL")
    configuration: Dict[str, Any] = Field(..., description="Configuration")
    pipeline_state: str = Field(..., description="Pipeline state")
    chunks_processed: int = Field(..., description="Chunks processed")
    total_size_bytes: int = Field(..., description="Total size in bytes")
    merkle_root: Optional[str] = Field(None, description="Merkle root hash")
    blockchain_anchor: Optional[Dict[str, Any]] = Field(None, description="Blockchain anchor info")
    metadata: Dict[str, Any] = Field(..., description="Session metadata")


class SessionListResponse(BaseModel):
    """
    Paginated list of sessions response.
    
    Attributes:
        sessions: List of session responses
        total: Total number of sessions
        skip: Number of records skipped
        limit: Maximum records returned
        has_more: Whether more records are available
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "sessions": [],
            "total": 100,
            "skip": 0,
            "limit": 100,
            "has_more": False
        }
    })
    
    sessions: List[SessionResponse] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total session count")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Maximum records")
    has_more: bool = Field(..., description="More records available")


class SessionTerminateRequest(BaseModel):
    """
    Request model for terminating a session.
    
    Attributes:
        reason: Reason for termination
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "reason": "user_requested"
        }
    })
    
    reason: Optional[str] = Field(None, description="Termination reason")


class ManifestCreateRequest(BaseModel):
    """
    Request model for creating a session manifest.
    
    Attributes:
        session_id: Session identifier
        chunk_hashes: List of chunk hashes
        metadata: Optional manifest metadata
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_id": "sess-123",
            "chunk_hashes": ["0x123...", "0x456..."],
            "metadata": {}
        }
    })
    
    session_id: str = Field(..., description="Session identifier")
    chunk_hashes: List[str] = Field(..., description="List of chunk hashes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Manifest metadata")


class ManifestResponse(BaseModel):
    """
    Standard manifest response model.
    
    Attributes:
        manifest_id: Unique manifest identifier
        session_id: Associated session identifier
        version: Manifest version
        created_at: Creation timestamp
        chunk_count: Number of chunks
        merkle_root: Merkle tree root hash
        status: Manifest status
        blockchain_anchor: Blockchain anchoring information
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "manifest_id": "manifest-123",
            "session_id": "sess-123",
            "version": "1.0",
            "created_at": "2025-10-14T12:00:00Z",
            "chunk_count": 10,
            "merkle_root": "0x123...",
            "status": "created",
            "blockchain_anchor": None
        }
    })
    
    manifest_id: str = Field(..., description="Manifest identifier")
    session_id: str = Field(..., description="Session identifier")
    version: str = Field(..., description="Manifest version")
    created_at: datetime = Field(..., description="Creation timestamp")
    chunk_count: int = Field(..., description="Chunk count")
    merkle_root: str = Field(..., description="Merkle root hash")
    status: str = Field(..., description="Manifest status")
    blockchain_anchor: Optional[Dict[str, Any]] = Field(None, description="Blockchain anchor")


class ManifestDetail(BaseModel):
    """
    Detailed manifest information model.
    
    Includes complete manifest data and chunk information.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "manifest_id": "manifest-123",
            "session_id": "sess-123",
            "version": "1.0",
            "created_at": "2025-10-14T12:00:00Z",
            "chunks": [],
            "merkle_root": "0x123...",
            "merkle_tree_height": 4,
            "total_size_bytes": 1024000,
            "compression_algorithm": "gzip",
            "encryption_algorithm": "AES-256-GCM",
            "status": "anchored",
            "blockchain_anchor": {},
            "metadata": {}
        }
    })
    
    manifest_id: str = Field(..., description="Manifest identifier")
    session_id: str = Field(..., description="Session identifier")
    version: str = Field(..., description="Manifest version")
    created_at: datetime = Field(..., description="Creation timestamp")
    chunks: List[Dict[str, Any]] = Field(..., description="Chunk information")
    merkle_root: str = Field(..., description="Merkle root hash")
    merkle_tree_height: int = Field(..., description="Merkle tree height")
    total_size_bytes: int = Field(..., description="Total size")
    compression_algorithm: str = Field(..., description="Compression algorithm")
    encryption_algorithm: str = Field(..., description="Encryption algorithm")
    status: str = Field(..., description="Manifest status")
    blockchain_anchor: Optional[Dict[str, Any]] = Field(None, description="Blockchain anchor")
    metadata: Dict[str, Any] = Field(..., description="Manifest metadata")


class ChunkInfo(BaseModel):
    """
    Chunk information model.
    
    Attributes:
        chunk_index: Chunk index in sequence
        chunk_hash: Hash of chunk data
        size_bytes: Chunk size in bytes
        encrypted: Whether chunk is encrypted
        compressed: Whether chunk is compressed
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "chunk_index": 0,
            "chunk_hash": "0x123...",
            "size_bytes": 10485760,
            "encrypted": True,
            "compressed": True
        }
    })
    
    chunk_index: int = Field(..., description="Chunk index")
    chunk_hash: str = Field(..., description="Chunk hash")
    size_bytes: int = Field(..., description="Size in bytes")
    encrypted: bool = Field(..., description="Encryption status")
    compressed: bool = Field(..., description="Compression status")


class MerkleProof(BaseModel):
    """
    Merkle proof model for chunk verification.
    
    Attributes:
        manifest_id: Manifest identifier
        chunk_index: Chunk index
        chunk_hash: Chunk hash
        merkle_root: Merkle root hash
        proof_hashes: List of proof hashes
        proof_directions: List of proof directions (left/right)
        verified: Whether proof is verified
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "manifest_id": "manifest-123",
            "chunk_index": 0,
            "chunk_hash": "0x123...",
            "merkle_root": "0x456...",
            "proof_hashes": ["0x789...", "0xabc..."],
            "proof_directions": ["left", "right"],
            "verified": True
        }
    })
    
    manifest_id: str = Field(..., description="Manifest identifier")
    chunk_index: int = Field(..., description="Chunk index")
    chunk_hash: str = Field(..., description="Chunk hash")
    merkle_root: str = Field(..., description="Merkle root")
    proof_hashes: List[str] = Field(..., description="Proof hashes")
    proof_directions: List[str] = Field(..., description="Proof directions")
    verified: bool = Field(..., description="Verification status")

