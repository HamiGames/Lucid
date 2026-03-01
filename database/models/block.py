"""
Block Data Models

Pydantic models for blockchain block entities (lucid_blocks).
Handles block structure, headers, and blockchain data.

Database Collection: blocks
Phase: Phase 1 - Foundation
Blockchain: lucid_blocks (on-chain)
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class BlockStatus(str, Enum):
    """Block status enumeration"""
    PENDING = "pending"
    VALIDATING = "validating"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"
    ORPHANED = "orphaned"


class ConsensusAlgorithm(str, Enum):
    """Consensus algorithm enumeration"""
    POOT = "poot"  # Proof of Observation Time


class BlockHeader(BaseModel):
    """Block header information"""
    version: int = Field(default=1, description="Block version")
    height: int = Field(..., ge=0, description="Block height in the chain")
    previous_hash: str = Field(..., description="Hash of the previous block")
    merkle_root: str = Field(..., description="Merkle root of transactions")
    timestamp: datetime = Field(..., description="Block creation timestamp")
    nonce: int = Field(default=0, description="Block nonce")
    difficulty: Optional[float] = Field(None, description="Block difficulty")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SessionAnchor(BaseModel):
    """Session anchoring information in a block"""
    session_id: str = Field(..., description="Anchored session ID")
    user_id: str = Field(..., description="Session owner ID")
    merkle_root: str = Field(..., description="Session merkle root")
    chunk_count: int = Field(..., ge=0, description="Number of chunks in session")
    total_size_bytes: int = Field(..., ge=0, description="Total session size")
    anchored_at: datetime = Field(..., description="Anchoring timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ConsensusInfo(BaseModel):
    """Consensus information for a block"""
    algorithm: ConsensusAlgorithm = Field(default=ConsensusAlgorithm.POOT, description="Consensus algorithm")
    validator_count: int = Field(..., ge=0, description="Number of validators")
    vote_count: int = Field(..., ge=0, description="Number of votes")
    consensus_reached: bool = Field(..., description="Whether consensus was reached")
    consensus_timestamp: datetime = Field(..., description="Consensus timestamp")
    poot_scores: Optional[Dict[str, float]] = Field(None, description="PoOT scores by validator")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BlockBase(BaseModel):
    """Base block model with common fields"""
    height: int = Field(..., ge=0, description="Block height")
    previous_hash: str = Field(..., description="Previous block hash")
    merkle_root: str = Field(..., description="Merkle root")
    
    @validator('previous_hash')
    def validate_previous_hash(cls, v, values):
        """Validate previous hash format"""
        if values.get('height', 0) == 0:
            # Genesis block
            if v != "0" * 64:
                raise ValueError('Genesis block must have zero hash as previous')
        elif len(v) != 64:
            raise ValueError('Previous hash must be 64 characters')
        return v


class BlockCreate(BlockBase):
    """Model for creating a new block"""
    transactions: List[str] = Field(default_factory=list, description="Transaction IDs")
    session_anchors: List[SessionAnchor] = Field(default_factory=list, description="Session anchors")
    consensus_info: Optional[ConsensusInfo] = Field(None, description="Consensus information")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class Block(BlockBase):
    """Block model for API responses"""
    block_id: str = Field(..., description="Unique block identifier (hash)")
    
    # Block header
    version: int = Field(default=1, description="Block version")
    timestamp: datetime = Field(..., description="Block timestamp")
    nonce: int = Field(default=0, description="Block nonce")
    
    # Block status
    status: BlockStatus = Field(default=BlockStatus.CONFIRMED, description="Block status")
    
    # Block contents
    transactions: List[str] = Field(default_factory=list, description="Transaction IDs in this block")
    transaction_count: int = Field(default=0, ge=0, description="Number of transactions")
    session_anchors: List[SessionAnchor] = Field(default_factory=list, description="Anchored sessions")
    session_anchor_count: int = Field(default=0, ge=0, description="Number of anchored sessions")
    
    # Consensus information
    consensus_info: Optional[ConsensusInfo] = Field(None, description="Consensus information")
    
    # Block size and statistics
    size_bytes: Optional[int] = Field(None, ge=0, description="Block size in bytes")
    difficulty: Optional[float] = Field(None, description="Block difficulty")
    
    # Confirmation information
    confirmations: int = Field(default=0, ge=0, description="Number of confirmations")
    finalized: bool = Field(default=False, description="Whether block is finalized")
    
    # Chain information
    chain_work: Optional[str] = Field(None, description="Cumulative chain work")
    next_block_hash: Optional[str] = Field(None, description="Hash of next block")
    
    # Block metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Timing information
    created_at: datetime = Field(..., description="Block creation timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Block confirmation timestamp")
    finalized_at: Optional[datetime] = Field(None, description="Block finalization timestamp")
    
    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BlockInDB(Block):
    """Block model as stored in database (includes internal fields)"""
    
    # Raw block data
    raw_header: Optional[bytes] = Field(None, description="Raw block header bytes")
    raw_transactions: Optional[bytes] = Field(None, description="Raw transactions bytes")
    
    # Validation information
    validated_by: List[str] = Field(default_factory=list, description="Validator node IDs")
    validation_signatures: Optional[Dict[str, str]] = Field(None, description="Validation signatures")
    
    # Processing information
    processing_time_ms: Optional[int] = Field(None, description="Block processing time in ms")
    propagation_time_ms: Optional[int] = Field(None, description="Network propagation time in ms")
    
    # Audit fields
    created_by: Optional[str] = Field(None, description="Node ID that created the block")
    imported_at: Optional[datetime] = Field(None, description="Block import timestamp")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    
    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BlockSummary(BaseModel):
    """Simplified block information for lists"""
    block_id: str = Field(..., description="Block identifier")
    height: int = Field(..., description="Block height")
    timestamp: datetime = Field(..., description="Block timestamp")
    transaction_count: int = Field(..., description="Number of transactions")
    session_anchor_count: int = Field(..., description="Number of session anchors")
    confirmations: int = Field(..., description="Number of confirmations")
    status: BlockStatus = Field(..., description="Block status")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BlockStatistics(BaseModel):
    """Block statistics and metrics"""
    block_id: str = Field(..., description="Block identifier")
    height: int = Field(..., description="Block height")
    
    # Size metrics
    size_bytes: int = Field(..., description="Block size in bytes")
    header_size_bytes: int = Field(..., description="Header size")
    transactions_size_bytes: int = Field(..., description="Transactions size")
    
    # Transaction metrics
    transaction_count: int = Field(..., description="Number of transactions")
    session_anchor_count: int = Field(..., description="Number of session anchors")
    
    # Time metrics
    timestamp: datetime = Field(..., description="Block timestamp")
    time_since_previous_seconds: Optional[int] = Field(None, description="Time since previous block")
    processing_time_ms: int = Field(..., description="Processing time")
    propagation_time_ms: Optional[int] = Field(None, description="Propagation time")
    
    # Consensus metrics
    validator_count: int = Field(..., description="Number of validators")
    consensus_time_ms: Optional[int] = Field(None, description="Time to reach consensus")
    
    # Confirmation metrics
    confirmations: int = Field(..., description="Number of confirmations")
    confirmation_time_seconds: Optional[int] = Field(None, description="Time to first confirmation")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class GenesisBlock(BaseModel):
    """Genesis block configuration"""
    block_id: str = Field(..., description="Genesis block hash")
    height: int = Field(0, description="Genesis block height (always 0)")
    previous_hash: str = Field("0" * 64, description="Genesis previous hash (zeros)")
    merkle_root: str = Field(..., description="Genesis merkle root")
    timestamp: datetime = Field(..., description="Genesis block timestamp")
    message: Optional[str] = Field(None, description="Genesis block message")
    initial_supply: Optional[int] = Field(None, description="Initial token supply")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

