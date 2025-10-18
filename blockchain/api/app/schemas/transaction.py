"""
Transaction Schema Models

This module defines Pydantic models for transaction-related API endpoints.
Implements the OpenAPI 3.0 specification for transaction processing and management.

Models:
- TransactionSubmitRequest: Transaction submission request
- TransactionResponse: Transaction submission response
- TransactionDetails: Detailed transaction information
- TransactionListResponse: List of transactions
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


class TransactionSubmitRequest(BaseModel):
    """Request for submitting a transaction to the blockchain."""
    type: str = Field(..., description="Transaction type", enum=["session_anchor", "data_storage", "consensus_vote", "system"])
    data: Dict[str, Any] = Field(..., description="Transaction data payload")
    signature: str = Field(..., description="Transaction signature")
    fee: Optional[float] = Field(0, description="Transaction fee", ge=0)
    timestamp: Optional[datetime] = Field(None, description="Transaction timestamp")


class TransactionResponse(BaseModel):
    """Response after submitting a transaction."""
    tx_id: str = Field(..., description="Transaction ID")
    status: str = Field(..., description="Transaction status", enum=["pending", "confirmed", "failed"])
    submitted_at: datetime = Field(..., description="Transaction submission timestamp")
    confirmation_time: Optional[datetime] = Field(None, description="Transaction confirmation timestamp")
    block_height: Optional[int] = Field(None, description="Block height where transaction was confirmed")


class TransactionDetails(BaseModel):
    """Detailed information about a transaction."""
    tx_id: str = Field(..., description="Transaction ID")
    type: str = Field(..., description="Transaction type")
    data: Dict[str, Any] = Field(..., description="Transaction data payload")
    signature: str = Field(..., description="Transaction signature")
    fee: float = Field(..., description="Transaction fee")
    status: str = Field(..., description="Transaction status")
    submitted_at: datetime = Field(..., description="Transaction submission timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Transaction confirmation timestamp")
    block_height: Optional[int] = Field(None, description="Block height where transaction was confirmed")
    block_hash: Optional[str] = Field(None, description="Block hash containing the transaction")
    transaction_index: Optional[int] = Field(None, description="Transaction index in the block")


class TransactionSummary(BaseModel):
    """Summary information about a transaction."""
    tx_id: str = Field(..., description="Transaction ID")
    type: str = Field(..., description="Transaction type")
    size_bytes: int = Field(..., description="Transaction size in bytes")
    fee: float = Field(..., description="Transaction fee")
    timestamp: datetime = Field(..., description="Transaction timestamp")


class PaginationInfo(BaseModel):
    """Pagination information for list responses."""
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")


class TransactionListResponse(BaseModel):
    """Paginated response containing a list of transactions."""
    transactions: List[TransactionSummary] = Field(..., description="List of transactions")
    pagination: PaginationInfo = Field(..., description="Pagination information")


class TransactionBatchRequest(BaseModel):
    """Request for submitting multiple transactions in a batch."""
    transactions: List[TransactionSubmitRequest] = Field(..., description="List of transactions to submit", min_items=1, max_items=100)


class TransactionBatchResponse(BaseModel):
    """Response after submitting a batch of transactions."""
    batch_id: str = Field(..., description="Batch ID")
    submitted_count: int = Field(..., description="Number of transactions successfully submitted")
    failed_count: int = Field(..., description="Number of transactions that failed")
    transaction_ids: List[str] = Field(..., description="List of submitted transaction IDs")
    errors: List[str] = Field(..., description="List of error messages for failed transactions")
