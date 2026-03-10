"""
LUCID Payment Systems - TRON Transaction Models
Transaction data models for TRON payment operations
Distroless container: lucid-tron-payment-service:latest
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

class TransactionType(str, Enum):
    """Transaction type enumeration"""
    TRX_TRANSFER = "trx_transfer"
    USDT_TRANSFER = "usdt_transfer"
    CONTRACT_CALL = "contract_call"
    FREEZE_BALANCE = "freeze_balance"
    UNFREEZE_BALANCE = "unfreeze_balance"
    VOTE_WITNESS = "vote_witness"
    DELEGATE_RESOURCE = "delegate_resource"
    UNDELEGATE_RESOURCE = "undelegate_resource"

class TransactionStatus(str, Enum):
    """Transaction status enumeration"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TransactionCreateRequest(BaseModel):
    """Transaction creation request"""
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    amount: float = Field(..., description="Transaction amount", gt=0)
    currency: str = Field("TRX", description="Currency (TRX, USDT)")
    transaction_type: TransactionType = Field(TransactionType.TRX_TRANSFER, description="Transaction type")
    private_key: Optional[str] = Field(None, description="Private key for signing")
    memo: Optional[str] = Field(None, description="Transaction memo", max_length=200)
    fee: Optional[float] = Field(None, description="Transaction fee")
    
    @validator('from_address')
    def validate_from_address(cls, v):
        if not v.startswith('T') or len(v) != 34:
            raise ValueError('Invalid sender address format')
        return v
    
    @validator('to_address')
    def validate_to_address(cls, v):
        if not v.startswith('T') or len(v) != 34:
            raise ValueError('Invalid recipient address format')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        allowed_currencies = ['TRX', 'USDT']
        if v not in allowed_currencies:
            raise ValueError(f'Invalid currency. Must be one of: {allowed_currencies}')
        return v

class TransactionResponse(BaseModel):
    """Transaction response model"""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    txid: str = Field(..., description="TRON transaction ID")
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency")
    transaction_type: str = Field(..., description="Transaction type")
    status: str = Field(..., description="Transaction status")
    fee: float = Field(..., description="Transaction fee")
    energy_used: int = Field(..., description="Energy used")
    bandwidth_used: int = Field(..., description="Bandwidth used")
    block_number: int = Field(..., description="Block number")
    timestamp: int = Field(..., description="Transaction timestamp")
    memo: Optional[str] = Field(None, description="Transaction memo")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "tx_abc123def456",
                "txid": "abc123def456789012345678901234567890123456789012345678901234567890",
                "from_address": "TFromAddress1234567890123456789012345",
                "to_address": "TToAddress1234567890123456789012345",
                "amount": 100.0,
                "currency": "TRX",
                "transaction_type": "trx_transfer",
                "status": "success",
                "fee": 1.0,
                "energy_used": 0,
                "bandwidth_used": 268,
                "block_number": 12345678,
                "timestamp": 1641234567890,
                "memo": "Payment for services",
                "created_at": "2025-01-10T19:08:00Z",
                "updated_at": "2025-01-10T19:08:00Z"
            }
        }

class TransactionListRequest(BaseModel):
    """Transaction list request"""
    address: Optional[str] = Field(None, description="Filter by address")
    transaction_type: Optional[TransactionType] = Field(None, description="Filter by transaction type")
    status: Optional[TransactionStatus] = Field(None, description="Filter by status")
    currency: Optional[str] = Field(None, description="Filter by currency")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    skip: int = Field(0, description="Number of records to skip", ge=0)
    limit: int = Field(100, description="Number of records to return", ge=1, le=1000)
    
    @validator('address')
    def validate_address(cls, v):
        if v is not None and (not v.startswith('T') or len(v) != 34):
            raise ValueError('Invalid address format')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        if v is not None:
            allowed_currencies = ['TRX', 'USDT']
            if v not in allowed_currencies:
                raise ValueError(f'Invalid currency. Must be one of: {allowed_currencies}')
        return v

class TransactionListResponse(BaseModel):
    """Transaction list response"""
    transactions: list[TransactionResponse] = Field(..., description="List of transactions")
    total_count: int = Field(..., description="Total number of transactions")
    total_amount: float = Field(..., description="Total transaction amount")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Number of records returned")
    timestamp: str = Field(..., description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "transactions": [],
                "total_count": 150,
                "total_amount": 5000.0,
                "skip": 0,
                "limit": 100,
                "timestamp": "2025-01-10T19:08:00Z"
            }
        }

class TransactionStats(BaseModel):
    """Transaction statistics model"""
    total_transactions: int = Field(..., description="Total number of transactions")
    total_amount: float = Field(..., description="Total transaction amount")
    successful_transactions: int = Field(..., description="Number of successful transactions")
    failed_transactions: int = Field(..., description="Number of failed transactions")
    pending_transactions: int = Field(..., description="Number of pending transactions")
    average_amount: float = Field(..., description="Average transaction amount")
    total_fees: float = Field(..., description="Total fees paid")
    period_start: str = Field(..., description="Statistics period start")
    period_end: str = Field(..., description="Statistics period end")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_transactions": 150,
                "total_amount": 5000.0,
                "successful_transactions": 145,
                "failed_transactions": 3,
                "pending_transactions": 2,
                "average_amount": 33.33,
                "total_fees": 150.0,
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-10T23:59:59Z"
            }
        }

class TransactionConfirmation(BaseModel):
    """Transaction confirmation model"""
    txid: str = Field(..., description="TRON transaction ID")
    confirmed: bool = Field(..., description="Confirmation status")
    confirmations: int = Field(..., description="Number of confirmations")
    block_number: int = Field(..., description="Block number")
    block_hash: str = Field(..., description="Block hash")
    timestamp: int = Field(..., description="Confirmation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "txid": "abc123def456789012345678901234567890123456789012345678901234567890",
                "confirmed": True,
                "confirmations": 19,
                "block_number": 12345678,
                "block_hash": "def456abc789012345678901234567890123456789012345678901234567890",
                "timestamp": 1641234567890
            }
        }
