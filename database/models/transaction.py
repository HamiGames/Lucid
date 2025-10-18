"""
Transaction Data Models

Pydantic models for blockchain transaction entities (lucid_blocks).
Handles transaction structure, types, and metadata.

Database Collection: transactions
Phase: Phase 1 - Foundation
Blockchain: lucid_blocks (on-chain)
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    """Transaction type enumeration"""
    SESSION_ANCHOR = "session_anchor"
    STATE_UPDATE = "state_update"
    GOVERNANCE = "governance"
    SYSTEM = "system"


class TransactionStatus(str, Enum):
    """Transaction status enumeration"""
    PENDING = "pending"
    IN_MEMPOOL = "in_mempool"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"
    FAILED = "failed"
    REJECTED = "rejected"


class TransactionBase(BaseModel):
    """Base transaction model with common fields"""
    transaction_type: TransactionType = Field(..., description="Transaction type")
    from_address: Optional[str] = Field(None, description="Sender address (if applicable)")
    to_address: Optional[str] = Field(None, description="Recipient address (if applicable)")
    data: Dict[str, Any] = Field(..., description="Transaction data payload")
    
    class Config:
        use_enum_values = True


class TransactionCreate(TransactionBase):
    """Model for creating a new transaction"""
    signature: Optional[str] = Field(None, description="Transaction signature")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class Transaction(TransactionBase):
    """Transaction model for API responses"""
    transaction_id: str = Field(..., description="Unique transaction identifier (hash)")
    
    # Transaction status
    status: TransactionStatus = Field(default=TransactionStatus.PENDING, description="Transaction status")
    
    # Block information
    block_id: Optional[str] = Field(None, description="Block ID containing this transaction")
    block_height: Optional[int] = Field(None, description="Block height")
    transaction_index: Optional[int] = Field(None, description="Index within block")
    
    # Transaction size and fees
    size_bytes: int = Field(..., ge=0, description="Transaction size in bytes")
    fee: Optional[int] = Field(None, description="Transaction fee (if applicable)")
    
    # Timing information
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    submitted_at: Optional[datetime] = Field(None, description="Mempool submission timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")
    finalized_at: Optional[datetime] = Field(None, description="Finalization timestamp")
    
    # Confirmation information
    confirmations: int = Field(default=0, ge=0, description="Number of confirmations")
    
    # Cryptographic information
    hash: str = Field(..., description="Transaction hash")
    signature: Optional[str] = Field(None, description="Transaction signature")
    public_key: Optional[str] = Field(None, description="Sender public key")
    
    # Transaction metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Error information (if failed)
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TransactionInDB(Transaction):
    """Transaction model as stored in database (includes internal fields)"""
    
    # Raw transaction data
    raw_transaction: Optional[bytes] = Field(None, description="Raw transaction bytes")
    
    # Validation information
    validated: bool = Field(default=False, description="Whether transaction is validated")
    validation_error: Optional[str] = Field(None, description="Validation error if any")
    
    # Processing information
    processing_time_ms: Optional[int] = Field(None, description="Processing time in ms")
    verification_time_ms: Optional[int] = Field(None, description="Verification time in ms")
    
    # Network propagation
    propagated_to_nodes: List[str] = Field(default_factory=list, description="Node IDs transaction was propagated to")
    propagation_time_ms: Optional[int] = Field(None, description="Propagation time in ms")
    
    # Audit fields
    created_by: Optional[str] = Field(None, description="Node/user that created transaction")
    imported_at: Optional[datetime] = Field(None, description="Import timestamp")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    
    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SessionAnchorTransaction(BaseModel):
    """Session anchor transaction data"""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="Session owner ID")
    merkle_root: str = Field(..., description="Session merkle root")
    chunk_count: int = Field(..., ge=0, description="Number of chunks")
    total_size_bytes: int = Field(..., ge=0, description="Total session size")
    session_created_at: datetime = Field(..., description="Session creation time")
    manifest_hash: str = Field(..., description="Session manifest hash")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class StateUpdateTransaction(BaseModel):
    """State update transaction data"""
    state_type: str = Field(..., description="Type of state being updated")
    state_key: str = Field(..., description="State key")
    old_value: Optional[Any] = Field(None, description="Previous state value")
    new_value: Any = Field(..., description="New state value")
    reason: Optional[str] = Field(None, description="Update reason")


class GovernanceTransaction(BaseModel):
    """Governance transaction data"""
    proposal_id: Optional[str] = Field(None, description="Governance proposal ID")
    action: str = Field(..., description="Governance action")
    parameters: Dict[str, Any] = Field(..., description="Governance parameters")
    voter_id: Optional[str] = Field(None, description="Voter ID (if vote)")
    vote: Optional[str] = Field(None, description="Vote value (if vote)")


class TransactionSummary(BaseModel):
    """Simplified transaction information for lists"""
    transaction_id: str = Field(..., description="Transaction identifier")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    block_height: Optional[int] = Field(None, description="Block height")
    status: TransactionStatus = Field(..., description="Transaction status")
    confirmations: int = Field(..., description="Number of confirmations")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TransactionStatistics(BaseModel):
    """Transaction statistics and metrics"""
    transaction_id: str = Field(..., description="Transaction identifier")
    
    # Size metrics
    size_bytes: int = Field(..., description="Transaction size in bytes")
    
    # Time metrics
    created_at: datetime = Field(..., description="Creation timestamp")
    time_to_inclusion_seconds: Optional[int] = Field(None, description="Time until included in block")
    time_to_confirmation_seconds: Optional[int] = Field(None, description="Time until confirmed")
    processing_time_ms: int = Field(..., description="Processing time")
    
    # Block metrics
    block_height: Optional[int] = Field(None, description="Block height")
    transaction_index: Optional[int] = Field(None, description="Index in block")
    confirmations: int = Field(..., description="Number of confirmations")
    
    # Network metrics
    propagation_time_ms: Optional[int] = Field(None, description="Network propagation time")
    node_count: Optional[int] = Field(None, description="Number of nodes received by")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

