"""
Transaction Data Models
Pydantic models for blockchain transactions and related structures.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REJECTED = "rejected"


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    TRANSFER = "transfer"
    SESSION_ANCHOR = "session_anchor"
    CONSENSUS_VOTE = "consensus_vote"
    VALIDATOR_REGISTRATION = "validator_registration"
    SYSTEM = "system"


class Transaction(BaseModel):
    """Complete transaction with all data."""
    
    hash: str = Field(..., description="Transaction hash (SHA-256)")
    type: TransactionType = Field(..., description="Transaction type")
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    amount: float = Field(default=0.0, ge=0, description="Transaction amount")
    fee: float = Field(default=0.0, ge=0, description="Transaction fee")
    nonce: int = Field(..., ge=0, description="Transaction nonce")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    
    # Block information (set when transaction is included in a block)
    block_hash: Optional[str] = Field(None, description="Hash of containing block")
    block_height: Optional[int] = Field(None, ge=0, description="Height of containing block")
    transaction_index: Optional[int] = Field(None, ge=0, description="Index within block")
    
    # Transaction data and metadata
    data: Optional[Dict[str, Any]] = Field(None, description="Transaction-specific data")
    signature: str = Field(..., description="Transaction signature")
    public_key: str = Field(..., description="Sender's public key")
    
    # Status and processing
    status: TransactionStatus = Field(default=TransactionStatus.PENDING, description="Transaction status")
    gas_limit: int = Field(default=21000, ge=0, description="Gas limit for transaction")
    gas_used: Optional[int] = Field(None, ge=0, description="Gas actually used")
    
    # Validation and confirmation
    confirmations: int = Field(default=0, ge=0, description="Number of confirmations")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    @validator('hash', 'signature', 'public_key')
    def validate_hex_fields(cls, v, field):
        if not isinstance(v, str):
            raise ValueError(f'{field.name} must be a string')
        if field.name == 'hash' and len(v) != 64:
            raise ValueError('Transaction hash must be 64 characters')
        if field.name in ['signature', 'public_key'] and len(v) < 64:
            raise ValueError(f'{field.name} must be at least 64 characters')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError(f'{field.name} must be a valid hexadecimal string')
        return v.lower()
        
    @validator('block_hash')
    def validate_block_hash(cls, v):
        if v is not None:
            if not isinstance(v, str) or len(v) != 64:
                raise ValueError('Block hash must be a 64-character hexadecimal string')
            try:
                int(v, 16)
            except ValueError:
                raise ValueError('Block hash must be a valid hexadecimal string')
            return v.lower()
        return v
        
    @validator('from_address', 'to_address')
    def validate_addresses(cls, v):
        if not isinstance(v, str) or len(v) < 20:
            raise ValueError('Address must be at least 20 characters')
        return v
        
    def is_confirmed(self, required_confirmations: int = 6) -> bool:
        """Check if transaction has enough confirmations."""
        return self.confirmations >= required_confirmations
        
    def is_finalized(self) -> bool:
        """Check if transaction is in a final state."""
        return self.status in [
            TransactionStatus.CONFIRMED,
            TransactionStatus.FAILED,
            TransactionStatus.REJECTED
        ]
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TransactionSummary(BaseModel):
    """Lightweight transaction summary for list views."""
    
    hash: str = Field(..., description="Transaction hash")
    type: TransactionType = Field(..., description="Transaction type")
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    amount: float = Field(..., ge=0, description="Transaction amount")
    fee: float = Field(..., ge=0, description="Transaction fee")
    status: TransactionStatus = Field(..., description="Transaction status")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    block_hash: Optional[str] = Field(None, description="Block hash if confirmed")
    block_height: Optional[int] = Field(None, ge=0, description="Block height if confirmed")
    
    @validator('hash')
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Transaction hash must be a 64-character hexadecimal string')
        return v.lower()
        
    @validator('block_hash')
    def validate_block_hash(cls, v):
        if v is not None:
            if not isinstance(v, str) or len(v) != 64:
                raise ValueError('Block hash must be a 64-character hexadecimal string')
            return v.lower()
        return v
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TransactionInput(BaseModel):
    """Transaction input for creating new transactions."""
    
    type: TransactionType = Field(..., description="Transaction type")
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    amount: float = Field(default=0.0, ge=0, description="Transaction amount")
    fee: float = Field(default=0.0, ge=0, description="Transaction fee")
    nonce: int = Field(..., ge=0, description="Transaction nonce")
    data: Optional[Dict[str, Any]] = Field(None, description="Transaction-specific data")
    gas_limit: int = Field(default=21000, ge=0, description="Gas limit")
    
    @validator('from_address', 'to_address')
    def validate_addresses(cls, v):
        if not isinstance(v, str) or len(v) < 20:
            raise ValueError('Address must be at least 20 characters')
        return v


class TransactionReceipt(BaseModel):
    """Transaction receipt with execution details."""
    
    transaction_hash: str = Field(..., description="Transaction hash")
    block_hash: str = Field(..., description="Block hash")
    block_height: int = Field(..., ge=0, description="Block height")
    transaction_index: int = Field(..., ge=0, description="Transaction index in block")
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    gas_used: int = Field(..., ge=0, description="Gas used by transaction")
    status: TransactionStatus = Field(..., description="Transaction status")
    logs: List[Dict[str, Any]] = Field(default_factory=list, description="Transaction logs")
    created_at: datetime = Field(..., description="Receipt creation time")
    
    @validator('transaction_hash', 'block_hash')
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Hash must be a 64-character hexadecimal string')
        return v.lower()
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TransactionValidationResult(BaseModel):
    """Result of transaction validation."""
    
    valid: bool = Field(..., description="Whether the transaction is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    transaction_hash: str = Field(..., description="Hash of validated transaction")
    estimated_gas: int = Field(..., ge=0, description="Estimated gas usage")
    validation_time_ms: float = Field(..., ge=0, description="Validation time in milliseconds")
    
    @validator('transaction_hash')
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Transaction hash must be a 64-character hexadecimal string')
        return v.lower()


class TransactionStats(BaseModel):
    """Statistics about transactions."""
    
    total_transactions: int = Field(..., ge=0, description="Total number of transactions")
    pending_transactions: int = Field(..., ge=0, description="Number of pending transactions")
    processed_transactions: int = Field(..., ge=0, description="Number of processed transactions")
    failed_transactions: int = Field(..., ge=0, description="Number of failed transactions")
    average_fee: float = Field(..., ge=0, description="Average transaction fee")
    average_amount: float = Field(..., ge=0, description="Average transaction amount")
    average_gas_used: float = Field(..., ge=0, description="Average gas used per transaction")
    transactions_per_second: float = Field(..., ge=0, description="Current TPS")
    last_updated: datetime = Field(..., description="When stats were last updated")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MempoolInfo(BaseModel):
    """Information about the transaction mempool."""
    
    transaction_count: int = Field(..., ge=0, description="Number of transactions in mempool")
    total_size_bytes: int = Field(..., ge=0, description="Total size of mempool in bytes")
    total_fees: float = Field(..., ge=0, description="Total fees of all transactions")
    average_fee: float = Field(..., ge=0, description="Average fee per transaction")
    oldest_transaction: Optional[datetime] = Field(None, description="Timestamp of oldest transaction")
    newest_transaction: Optional[datetime] = Field(None, description="Timestamp of newest transaction")
    fee_percentiles: Dict[str, float] = Field(default_factory=dict, description="Fee percentiles")
    last_updated: datetime = Field(..., description="When info was last updated")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionAnchorTransaction(Transaction):
    """Specialized transaction for session anchoring."""
    
    type: TransactionType = Field(TransactionType.SESSION_ANCHOR, description="Always session_anchor")
    session_id: str = Field(..., description="ID of anchored session")
    merkle_root: str = Field(..., description="Merkle root of session chunks")
    chunk_count: int = Field(..., ge=1, description="Number of chunks in session")
    
    def __init__(self, **data):
        # Ensure transaction type is correct
        data['type'] = TransactionType.SESSION_ANCHOR
        super().__init__(**data)
        
    @validator('merkle_root')
    def validate_merkle_root(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Merkle root must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Merkle root must be a valid hexadecimal string')
        return v.lower()
