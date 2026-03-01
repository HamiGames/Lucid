"""
Block Data Models
Pydantic models for blockchain blocks and related structures.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class BlockHeader(BaseModel):
    """Block header containing metadata without full transaction data."""
    
    hash: str = Field(..., description="Block hash (SHA-256)")
    height: int = Field(..., ge=0, description="Block height in the chain")
    previous_hash: str = Field(..., description="Hash of the previous block")
    merkle_root: str = Field(..., description="Merkle root of transactions")
    timestamp: datetime = Field(..., description="Block creation timestamp")
    nonce: int = Field(default=0, description="Proof-of-work nonce")
    difficulty: float = Field(default=1.0, ge=0, description="Mining difficulty")
    transaction_count: int = Field(..., ge=0, description="Number of transactions in block")
    
    @field_validator('hash', 'previous_hash', 'merkle_root')
    @classmethod
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Hash must be a valid hexadecimal string')
        return v.lower()
        
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class Block(BaseModel):
    """Complete block with all transaction data."""
    
    hash: str = Field(..., description="Block hash (SHA-256)")
    height: int = Field(..., ge=0, description="Block height in the chain")
    previous_hash: str = Field(..., description="Hash of the previous block")
    merkle_root: str = Field(..., description="Merkle root of transactions")
    timestamp: datetime = Field(..., description="Block creation timestamp")
    nonce: int = Field(default=0, description="Proof-of-work nonce")
    difficulty: float = Field(default=1.0, ge=0, description="Mining difficulty")
    transactions: List[Dict[str, Any]] = Field(default_factory=list, description="Block transactions")
    size_bytes: int = Field(default=0, ge=0, description="Block size in bytes")
    version: int = Field(default=1, ge=1, description="Block version")
    
    # Consensus-related fields
    validator_signature: Optional[str] = Field(None, description="Validator signature for PoOT")
    consensus_round: Optional[str] = Field(None, description="Consensus round ID")
    
    @field_validator('hash', 'previous_hash', 'merkle_root')
    @classmethod
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Hash must be a valid hexadecimal string')
        return v.lower()
        
    @field_validator('transactions')
    @classmethod
    def validate_transactions(cls, v):
        if not isinstance(v, list):
            raise ValueError('Transactions must be a list')
        return v
        
    @property
    def transaction_count(self) -> int:
        """Get the number of transactions in this block."""
        return len(self.transactions)
        
    def to_header(self) -> BlockHeader:
        """Convert block to header (without transaction data)."""
        return BlockHeader(
            hash=self.hash,
            height=self.height,
            previous_hash=self.previous_hash,
            merkle_root=self.merkle_root,
            timestamp=self.timestamp,
            nonce=self.nonce,
            difficulty=self.difficulty,
            transaction_count=self.transaction_count
        )
        
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class BlockSummary(BaseModel):
    """Lightweight block summary for list views."""
    
    hash: str = Field(..., description="Block hash")
    height: int = Field(..., ge=0, description="Block height")
    timestamp: datetime = Field(..., description="Block timestamp")
    transaction_count: int = Field(..., ge=0, description="Number of transactions")
    size_bytes: int = Field(..., ge=0, description="Block size in bytes")
    previous_hash: str = Field(..., description="Previous block hash")
    
    @field_validator('hash', 'previous_hash')
    @classmethod
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Hash must be a 64-character hexadecimal string')
        return v.lower()
        
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class BlockInfo(BaseModel):
    """Extended block information with additional metadata."""
    
    block: Block = Field(..., description="Block data")
    confirmations: int = Field(default=0, ge=0, description="Number of confirmations")
    next_block_hash: Optional[str] = Field(None, description="Hash of next block")
    is_orphaned: bool = Field(default=False, description="Whether block is orphaned")
    total_fees: float = Field(default=0.0, ge=0, description="Total transaction fees")
    reward: float = Field(default=0.0, ge=0, description="Block reward")
    
    @field_validator('next_block_hash')
    @classmethod
    def validate_next_hash_format(cls, v):
        if v is not None:
            if not isinstance(v, str) or len(v) != 64:
                raise ValueError('Next block hash must be a 64-character hexadecimal string')
            try:
                int(v, 16)
            except ValueError:
                raise ValueError('Next block hash must be a valid hexadecimal string')
            return v.lower()
        return v
        
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class GenesisBlock(Block):
    """Genesis block with special properties."""
    
    height: int = Field(0, description="Genesis block height (always 0)")
    previous_hash: str = Field("0" * 64, description="Genesis block previous hash (all zeros)")
    
    def __init__(self, **data):
        # Ensure genesis block properties
        data['height'] = 0
        data['previous_hash'] = "0" * 64
        super().__init__(**data)


class BlockValidationResult(BaseModel):
    """Result of block validation."""
    
    valid: bool = Field(..., description="Whether the block is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    block_hash: str = Field(..., description="Hash of validated block")
    validation_time_ms: float = Field(..., ge=0, description="Validation time in milliseconds")
    
    @field_validator('block_hash')
    @classmethod
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Block hash must be a 64-character hexadecimal string')
        return v.lower()


class BlockStats(BaseModel):
    """Statistics about blocks in the blockchain."""
    
    total_blocks: int = Field(..., ge=0, description="Total number of blocks")
    latest_height: int = Field(..., ge=0, description="Height of latest block")
    latest_hash: str = Field(..., description="Hash of latest block")
    average_block_size_bytes: float = Field(..., ge=0, description="Average block size")
    average_transactions_per_block: float = Field(..., ge=0, description="Average transactions per block")
    average_block_time_seconds: float = Field(..., ge=0, description="Average time between blocks")
    total_transactions: int = Field(..., ge=0, description="Total transactions across all blocks")
    last_updated: datetime = Field(..., description="When stats were last updated")
    
    @field_validator('latest_hash')
    @classmethod
    def validate_hash_format(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Latest hash must be a 64-character hexadecimal string')
        return v.lower()
        
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
