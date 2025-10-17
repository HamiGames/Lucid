"""
Session Data Models

Pydantic models for session entities in the Lucid system.
Handles RDP session metadata, chunk information, and blockchain anchoring.

Database Collection: sessions
Phase: Phase 1 - Foundation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enumeration"""
    PENDING = "pending"
    RECORDING = "recording"
    PROCESSING = "processing"
    ENCRYPTING = "encrypting"
    MERKLE_BUILDING = "merkle_building"
    ANCHORING = "anchoring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChunkStatus(str, Enum):
    """Chunk status enumeration"""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ENCRYPTED = "encrypted"
    STORED = "stored"
    FAILED = "failed"


class ChunkInfo(BaseModel):
    """Information about a session chunk"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    chunk_index: int = Field(..., ge=0, description="Chunk sequence number")
    size_bytes: int = Field(..., ge=0, description="Chunk size in bytes")
    hash: str = Field(..., description="Chunk content hash (SHA-256)")
    encrypted_hash: Optional[str] = Field(None, description="Hash of encrypted chunk")
    status: ChunkStatus = Field(..., description="Chunk processing status")
    storage_path: Optional[str] = Field(None, description="Storage location path")
    compression_ratio: Optional[float] = Field(None, description="Compression ratio")
    encryption_algorithm: Optional[str] = Field(None, description="Encryption algorithm used")
    uploaded_at: Optional[datetime] = Field(None, description="Upload timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class MerkleTreeInfo(BaseModel):
    """Merkle tree information for session"""
    root_hash: str = Field(..., description="Merkle root hash")
    tree_height: int = Field(..., ge=0, description="Merkle tree height")
    leaf_count: int = Field(..., ge=0, description="Number of leaf nodes")
    built_at: datetime = Field(..., description="Tree construction timestamp")
    verification_hash: Optional[str] = Field(None, description="Verification hash")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BlockchainAnchor(BaseModel):
    """Blockchain anchoring information"""
    block_id: Optional[str] = Field(None, description="Block ID where session is anchored")
    block_height: Optional[int] = Field(None, description="Block height")
    transaction_hash: Optional[str] = Field(None, description="Transaction hash")
    merkle_root: str = Field(..., description="Merkle root anchored to blockchain")
    anchored_at: datetime = Field(..., description="Anchoring timestamp")
    confirmation_count: int = Field(default=0, ge=0, description="Number of confirmations")
    verified: bool = Field(default=False, description="Whether anchor is verified")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SessionBase(BaseModel):
    """Base session model with common fields"""
    user_id: str = Field(..., description="Owner user ID")
    session_name: Optional[str] = Field(None, max_length=200, description="Session name")
    status: SessionStatus = Field(default=SessionStatus.PENDING, description="Session status")
    
    class Config:
        use_enum_values = True


class SessionCreate(SessionBase):
    """Model for creating a new session"""
    rdp_server_id: Optional[str] = Field(None, description="RDP server identifier")
    rdp_port: Optional[int] = Field(None, description="RDP server port")
    initial_metadata: Optional[Dict[str, Any]] = Field(None, description="Initial session metadata")


class SessionUpdate(BaseModel):
    """Model for updating session information"""
    session_name: Optional[str] = Field(None, max_length=200)
    status: Optional[SessionStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class Session(SessionBase):
    """Session model for API responses"""
    session_id: str = Field(..., description="Unique session identifier")
    
    # RDP connection information
    rdp_server_id: Optional[str] = Field(None, description="RDP server identifier")
    rdp_port: Optional[int] = Field(None, description="RDP server port")
    rdp_connection_info: Optional[Dict[str, Any]] = Field(None, description="RDP connection details")
    
    # Session timestamps
    created_at: datetime = Field(..., description="Session creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Session start timestamp")
    ended_at: Optional[datetime] = Field(None, description="Session end timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Recording information
    duration_seconds: Optional[int] = Field(None, ge=0, description="Session duration")
    recorded_size_bytes: Optional[int] = Field(None, ge=0, description="Total recorded size")
    compressed_size_bytes: Optional[int] = Field(None, ge=0, description="Total compressed size")
    compression_ratio: Optional[float] = Field(None, description="Overall compression ratio")
    
    # Chunk information
    total_chunks: int = Field(default=0, ge=0, description="Total number of chunks")
    chunks_uploaded: int = Field(default=0, ge=0, description="Number of uploaded chunks")
    chunks_processed: int = Field(default=0, ge=0, description="Number of processed chunks")
    chunks_encrypted: int = Field(default=0, ge=0, description="Number of encrypted chunks")
    chunks: List[ChunkInfo] = Field(default_factory=list, description="Chunk information list")
    
    # Merkle tree information
    merkle_tree: Optional[MerkleTreeInfo] = Field(None, description="Merkle tree info")
    
    # Blockchain anchoring
    blockchain_anchor: Optional[BlockchainAnchor] = Field(None, description="Blockchain anchor info")
    
    # Session metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")
    
    # Pipeline state
    pipeline_state: Optional[Dict[str, Any]] = Field(None, description="Pipeline processing state")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SessionInDB(Session):
    """Session model as stored in database (includes internal fields)"""
    
    # Internal processing fields
    processing_started_at: Optional[datetime] = Field(None, description="Processing start time")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    encryption_key: Optional[str] = Field(None, description="Encrypted encryption key")
    
    # Storage information
    storage_provider: Optional[str] = Field(default="local", description="Storage provider")
    storage_path: Optional[str] = Field(None, description="Base storage path")
    storage_volume: Optional[str] = Field(None, description="Storage volume name")
    
    # Performance metrics
    upload_bandwidth_mbps: Optional[float] = Field(None, description="Upload bandwidth (Mbps)")
    processing_time_seconds: Optional[int] = Field(None, description="Total processing time")
    
    # Audit fields
    created_by: Optional[str] = Field(None, description="User ID that created session")
    updated_by: Optional[str] = Field(None, description="User ID that last updated session")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SessionStatistics(BaseModel):
    """Session statistics and metrics"""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    
    # Size metrics
    total_size_bytes: int = Field(..., description="Total size in bytes")
    compressed_size_bytes: int = Field(..., description="Compressed size in bytes")
    compression_ratio: float = Field(..., description="Compression ratio")
    
    # Chunk metrics
    total_chunks: int = Field(..., description="Total number of chunks")
    chunk_size_avg_bytes: float = Field(..., description="Average chunk size")
    chunk_size_min_bytes: int = Field(..., description="Minimum chunk size")
    chunk_size_max_bytes: int = Field(..., description="Maximum chunk size")
    
    # Time metrics
    duration_seconds: int = Field(..., description="Session duration")
    processing_time_seconds: int = Field(..., description="Processing time")
    upload_time_seconds: int = Field(..., description="Upload time")
    
    # Performance metrics
    upload_speed_mbps: float = Field(..., description="Upload speed (Mbps)")
    processing_speed_mbps: float = Field(..., description="Processing speed (Mbps)")
    
    # Blockchain metrics
    anchored: bool = Field(..., description="Whether session is anchored")
    anchor_confirmations: int = Field(default=0, description="Anchor confirmations")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SessionManifest(BaseModel):
    """Complete session manifest for blockchain anchoring"""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    total_chunks: int = Field(..., description="Total number of chunks")
    total_size_bytes: int = Field(..., description="Total size in bytes")
    merkle_root: str = Field(..., description="Merkle root hash")
    chunk_hashes: List[str] = Field(..., description="List of all chunk hashes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    signature: Optional[str] = Field(None, description="Manifest signature")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

