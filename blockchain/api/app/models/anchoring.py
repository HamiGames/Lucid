"""
Anchoring Data Models
Pydantic models for session anchoring, Merkle trees, and related structures.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator


class AnchorStatus(str, Enum):
    """Session anchor status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"


class MerkleNode(BaseModel):
    """Node in a Merkle tree."""
    
    hash: str = Field(..., description="Hash value of the node")
    left: Optional['MerkleNode'] = Field(None, description="Left child node")
    right: Optional['MerkleNode'] = Field(None, description="Right child node")
    is_leaf: bool = Field(default=False, description="Whether this is a leaf node")
    data: Optional[str] = Field(None, description="Original data (for leaf nodes)")
    
    @validator('hash')
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Hash must be a valid hexadecimal string')
        return v.lower()
        
    class Config:
        # Allow self-referencing models
        arbitrary_types_allowed = True


# Update forward reference
MerkleNode.model_rebuild()


class MerkleTree(BaseModel):
    """Merkle tree structure."""
    
    root: MerkleNode = Field(..., description="Root node of the tree")
    leaves: List[MerkleNode] = Field(..., description="Leaf nodes of the tree")
    height: int = Field(..., ge=0, description="Height of the tree")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Tree creation time")
    
    @validator('leaves')
    def validate_leaves(cls, v):
        if not v:
            raise ValueError('Tree must have at least one leaf')
        for leaf in v:
            if not leaf.is_leaf:
                raise ValueError('All items in leaves list must be leaf nodes')
        return v
        
    @property
    def leaf_count(self) -> int:
        """Get the number of leaves in the tree."""
        return len(self.leaves)
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MerkleProofElement(BaseModel):
    """Element in a Merkle proof path."""
    
    hash: str = Field(..., description="Hash value")
    position: str = Field(..., description="Position relative to sibling (left/right)")
    
    @validator('hash')
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Hash must be a valid hexadecimal string')
        return v.lower()
        
    @validator('position')
    def validate_position(cls, v):
        if v not in ['left', 'right']:
            raise ValueError('Position must be either "left" or "right"')
        return v


class MerkleProof(BaseModel):
    """Merkle proof for a specific leaf."""
    
    leaf_index: int = Field(..., ge=0, description="Index of the leaf being proven")
    leaf_hash: str = Field(..., description="Hash of the leaf being proven")
    path: List[MerkleProofElement] = Field(..., description="Proof path from leaf to root")
    root_hash: str = Field(..., description="Expected root hash")
    
    @validator('leaf_hash', 'root_hash')
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Hash must be a valid hexadecimal string')
        return v.lower()
        
    @validator('path')
    def validate_path(cls, v):
        if not v:
            raise ValueError('Proof path cannot be empty')
        return v


class SessionAnchor(BaseModel):
    """Session anchor record."""
    
    anchor_id: Optional[str] = Field(None, description="Unique anchor identifier")
    session_id: str = Field(..., description="ID of the anchored session")
    merkle_root: str = Field(..., description="Merkle root of session chunks")
    chunk_count: int = Field(..., ge=1, description="Number of chunks in session")
    status: AnchorStatus = Field(default=AnchorStatus.PENDING, description="Anchor status")
    
    # Blockchain information (set when confirmed)
    block_hash: Optional[str] = Field(None, description="Hash of block containing anchor")
    block_height: Optional[int] = Field(None, ge=0, description="Height of block containing anchor")
    transaction_hash: Optional[str] = Field(None, description="Hash of anchoring transaction")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Anchor creation time")
    confirmed_at: Optional[datetime] = Field(None, description="Anchor confirmation time")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    
    @validator('merkle_root')
    def validate_merkle_root(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Merkle root must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Merkle root must be a valid hexadecimal string')
        return v.lower()
        
    @validator('block_hash', 'transaction_hash')
    def validate_optional_hashes(cls, v):
        if v is not None:
            if not isinstance(v, str) or len(v) != 64:
                raise ValueError('Hash must be a 64-character hexadecimal string')
            try:
                int(v, 16)
            except ValueError:
                raise ValueError('Hash must be a valid hexadecimal string')
            return v.lower()
        return v
        
    def is_confirmed(self) -> bool:
        """Check if anchor is confirmed."""
        return self.status == AnchorStatus.CONFIRMED
        
    def is_finalized(self) -> bool:
        """Check if anchor is in a final state."""
        return self.status in [AnchorStatus.CONFIRMED, AnchorStatus.FAILED, AnchorStatus.EXPIRED]
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnchorRequest(BaseModel):
    """Request to anchor a session."""
    
    session_id: str = Field(..., description="ID of session to anchor")
    chunk_hashes: List[str] = Field(..., description="List of chunk hashes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    priority: int = Field(default=0, ge=0, le=10, description="Anchoring priority (0-10)")
    
    @validator('chunk_hashes')
    def validate_chunk_hashes(cls, v):
        if not v:
            raise ValueError('At least one chunk hash is required')
        for i, chunk_hash in enumerate(v):
            if not isinstance(chunk_hash, str) or len(chunk_hash) != 64:
                raise ValueError(f'Chunk hash {i} must be a 64-character hexadecimal string')
            try:
                int(chunk_hash, 16)
            except ValueError:
                raise ValueError(f'Chunk hash {i} must be a valid hexadecimal string')
        return [h.lower() for h in v]


class AnchorResponse(BaseModel):
    """Response from anchoring operation."""
    
    session_id: str = Field(..., description="ID of anchored session")
    anchor_id: Optional[str] = Field(None, description="Anchor identifier")
    status: AnchorStatus = Field(..., description="Anchor status")
    merkle_root: Optional[str] = Field(None, description="Merkle root of session")
    block_hash: Optional[str] = Field(None, description="Block hash if confirmed")
    block_height: Optional[int] = Field(None, ge=0, description="Block height if confirmed")
    timestamp: Optional[datetime] = Field(None, description="Confirmation timestamp")
    message: Optional[str] = Field(None, description="Status message")
    
    @validator('merkle_root', 'block_hash')
    def validate_optional_hashes(cls, v):
        if v is not None:
            if not isinstance(v, str) or len(v) != 64:
                raise ValueError('Hash must be a 64-character hexadecimal string')
            try:
                int(v, 16)
            except ValueError:
                raise ValueError('Hash must be a valid hexadecimal string')
            return v.lower()
        return v
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnchorVerificationRequest(BaseModel):
    """Request to verify session anchoring."""
    
    session_id: str = Field(..., description="ID of session to verify")
    chunk_hashes: List[str] = Field(..., description="List of chunk hashes to verify against")
    
    @validator('chunk_hashes')
    def validate_chunk_hashes(cls, v):
        if not v:
            raise ValueError('At least one chunk hash is required')
        for i, chunk_hash in enumerate(v):
            if not isinstance(chunk_hash, str) or len(chunk_hash) != 64:
                raise ValueError(f'Chunk hash {i} must be a 64-character hexadecimal string')
            try:
                int(chunk_hash, 16)
            except ValueError:
                raise ValueError(f'Chunk hash {i} must be a valid hexadecimal string')
        return [h.lower() for h in v]


class AnchorVerificationResponse(BaseModel):
    """Response from anchor verification."""
    
    verified: bool = Field(..., description="Whether the anchor is verified")
    session_id: str = Field(..., description="ID of verified session")
    merkle_root: Optional[str] = Field(None, description="Verified Merkle root")
    block_hash: Optional[str] = Field(None, description="Block containing anchor")
    block_height: Optional[int] = Field(None, ge=0, description="Block height")
    chunk_count: Optional[int] = Field(None, ge=0, description="Number of chunks verified")
    error: Optional[str] = Field(None, description="Error message if verification failed")
    verified_at: Optional[datetime] = Field(None, description="Verification timestamp")
    
    @validator('merkle_root', 'block_hash')
    def validate_optional_hashes(cls, v):
        if v is not None:
            if not isinstance(v, str) or len(v) != 64:
                raise ValueError('Hash must be a 64-character hexadecimal string')
            return v.lower()
        return v
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnchoringStats(BaseModel):
    """Statistics about anchoring operations."""
    
    total_anchors: int = Field(..., ge=0, description="Total number of anchors")
    confirmed_anchors: int = Field(..., ge=0, description="Number of confirmed anchors")
    pending_anchors: int = Field(..., ge=0, description="Number of pending anchors")
    failed_anchors: int = Field(..., ge=0, description="Number of failed anchors")
    success_rate: float = Field(..., ge=0, le=1, description="Success rate (0-1)")
    average_confirmation_time_seconds: float = Field(..., ge=0, description="Average confirmation time")
    total_chunks_anchored: int = Field(..., ge=0, description="Total chunks anchored")
    last_updated: datetime = Field(..., description="When stats were last updated")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
