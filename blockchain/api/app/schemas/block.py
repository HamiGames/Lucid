"""
Block Schema Models

This module defines Pydantic models for block-related API endpoints.
Implements the OpenAPI 3.0 specification for block management and validation.

Models:
- BlockDetails: Detailed block information
- BlockListResponse: Paginated list of blocks
- BlockValidationRequest: Block validation request
- BlockValidationResponse: Block validation results
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


class TransactionSummary(BaseModel):
    """Summary information about a transaction in a block."""
    tx_id: str = Field(..., description="Transaction ID")
    type: str = Field(..., description="Transaction type", enum=["session_anchor", "data_storage", "consensus_vote", "system"])
    size_bytes: int = Field(..., description="Transaction size in bytes")
    fee: float = Field(..., description="Transaction fee")
    timestamp: datetime = Field(..., description="Transaction timestamp")


class BlockDetails(BaseModel):
    """Detailed information about a blockchain block."""
    block_id: str = Field(..., description="Unique block identifier")
    height: int = Field(..., description="Block height in the chain")
    hash: str = Field(..., description="Block hash")
    previous_hash: str = Field(..., description="Previous block hash")
    merkle_root: str = Field(..., description="Merkle tree root hash")
    timestamp: datetime = Field(..., description="Block creation timestamp")
    nonce: int = Field(..., description="Block nonce")
    difficulty: float = Field(..., description="Block difficulty")
    transaction_count: int = Field(..., description="Number of transactions in block")
    block_size_bytes: int = Field(..., description="Block size in bytes")
    transactions: List[TransactionSummary] = Field(..., description="List of transactions in block")
    validator: str = Field(..., description="Block validator address")
    signature: str = Field(..., description="Block signature")


class BlockSummary(BaseModel):
    """Summary information about a blockchain block."""
    block_id: str = Field(..., description="Unique block identifier")
    height: int = Field(..., description="Block height in the chain")
    hash: str = Field(..., description="Block hash")
    timestamp: datetime = Field(..., description="Block creation timestamp")
    transaction_count: int = Field(..., description="Number of transactions in block")
    block_size_bytes: int = Field(..., description="Block size in bytes")
    validator: str = Field(..., description="Block validator address")


class PaginationInfo(BaseModel):
    """Pagination information for list responses."""
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")


class BlockListResponse(BaseModel):
    """Paginated response containing a list of blocks."""
    blocks: List[BlockSummary] = Field(..., description="List of blocks")
    pagination: PaginationInfo = Field(..., description="Pagination information")


class BlockValidationRequest(BaseModel):
    """Request for validating block structure."""
    block_data: Dict[str, Any] = Field(..., description="Block data to validate")


class BlockValidationResults(BaseModel):
    """Results of block validation checks."""
    structure_valid: bool = Field(..., description="Whether block structure is valid")
    signature_valid: bool = Field(..., description="Whether block signature is valid")
    merkle_root_valid: bool = Field(..., description="Whether Merkle root is valid")
    timestamp_valid: bool = Field(..., description="Whether timestamp is valid")
    transactions_valid: bool = Field(..., description="Whether transactions are valid")


class BlockValidationResponse(BaseModel):
    """Response containing block validation results."""
    valid: bool = Field(..., description="Whether the block is valid overall")
    validation_results: BlockValidationResults = Field(..., description="Detailed validation results")
    errors: List[str] = Field(..., description="List of validation errors")
