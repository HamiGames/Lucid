"""
LUCID Payment Systems - TRON Payout Models
Payout data models for TRON payment operations
Distroless container: lucid-tron-payment-service:latest
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

class PayoutStatus(str, Enum):
    """Payout status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PayoutType(str, Enum):
    """Payout type enumeration"""
    V0 = "v0"
    KYC = "kyc"
    DIRECT = "direct"

class PayoutRoute(str, Enum):
    """Payout route enumeration"""
    V0_ROUTE = "v0_route"
    KYC_ROUTE = "kyc_route"
    DIRECT_ROUTE = "direct_route"

class PayoutCreateRequest(BaseModel):
    """Payout creation request"""
    recipient_address: str = Field(..., description="Recipient TRON address")
    amount: float = Field(..., description="Payout amount", gt=0)
    currency: str = Field("USDT", description="Currency (USDT, TRX)")
    description: Optional[str] = Field(None, description="Payout description", max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('recipient_address')
    def validate_recipient_address(cls, v):
        if not v.startswith('T') or len(v) != 34:
            raise ValueError('Invalid recipient address format')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        allowed_currencies = ['USDT', 'TRX']
        if v not in allowed_currencies:
            raise ValueError(f'Invalid currency. Must be one of: {allowed_currencies}')
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Payout amount must be greater than 0')
        if v > 1000000:  # 1 million max
            raise ValueError('Payout amount cannot exceed 1,000,000')
        return v

class PayoutUpdateRequest(BaseModel):
    """Payout update request"""
    status: Optional[PayoutStatus] = Field(None, description="Payout status")
    description: Optional[str] = Field(None, description="Payout description", max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    txid: Optional[str] = Field(None, description="Transaction ID")
    error_message: Optional[str] = Field(None, description="Error message", max_length=1000)
    
    @validator('txid')
    def validate_txid(cls, v):
        if v is not None and len(v) != 64:
            raise ValueError('Invalid transaction ID format')
        return v

class PayoutResponse(BaseModel):
    """Payout response model"""
    payout_id: str = Field(..., description="Unique payout identifier")
    recipient_address: str = Field(..., description="Recipient TRON address")
    amount: float = Field(..., description="Payout amount")
    currency: str = Field(..., description="Currency")
    payout_type: str = Field(..., description="Payout type")
    status: str = Field(..., description="Payout status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    description: Optional[str] = Field(None, description="Payout description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    fee: float = Field(..., description="Payout fee")
    txid: Optional[str] = Field(None, description="Transaction ID")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "payout_id": "payout_abc123def456",
                "recipient_address": "TRecipientAddress1234567890123456789012345",
                "amount": 100.0,
                "currency": "USDT",
                "payout_type": "v0",
                "status": "pending",
                "created_at": "2025-01-10T19:08:00Z",
                "updated_at": "2025-01-10T19:08:00Z",
                "description": "Payment for services",
                "metadata": {"user_id": "user123", "service": "lucid"},
                "fee": 1.0,
                "txid": None,
                "completed_at": None,
                "error_message": None
            }
        }

class PayoutListRequest(BaseModel):
    """Payout list request"""
    recipient_address: Optional[str] = Field(None, description="Filter by recipient address")
    status: Optional[PayoutStatus] = Field(None, description="Filter by status")
    payout_type: Optional[PayoutType] = Field(None, description="Filter by payout type")
    currency: Optional[str] = Field(None, description="Filter by currency")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    skip: int = Field(0, description="Number of records to skip", ge=0)
    limit: int = Field(100, description="Number of records to return", ge=1, le=1000)
    
    @validator('recipient_address')
    def validate_recipient_address(cls, v):
        if v is not None and (not v.startswith('T') or len(v) != 34):
            raise ValueError('Invalid recipient address format')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        if v is not None:
            allowed_currencies = ['USDT', 'TRX']
            if v not in allowed_currencies:
                raise ValueError(f'Invalid currency. Must be one of: {allowed_currencies}')
        return v

class PayoutListResponse(BaseModel):
    """Payout list response"""
    payouts: list[PayoutResponse] = Field(..., description="List of payouts")
    total_count: int = Field(..., description="Total number of payouts")
    total_amount: float = Field(..., description="Total payout amount")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Number of records returned")
    timestamp: str = Field(..., description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "payouts": [],
                "total_count": 50,
                "total_amount": 5000.0,
                "skip": 0,
                "limit": 100,
                "timestamp": "2025-01-10T19:08:00Z"
            }
        }

class PayoutStats(BaseModel):
    """Payout statistics model"""
    total_payouts: int = Field(..., description="Total number of payouts")
    total_amount: float = Field(..., description="Total payout amount")
    pending_payouts: int = Field(..., description="Number of pending payouts")
    completed_payouts: int = Field(..., description="Number of completed payouts")
    failed_payouts: int = Field(..., description="Number of failed payouts")
    average_amount: float = Field(..., description="Average payout amount")
    total_fees: float = Field(..., description="Total fees paid")
    period_start: str = Field(..., description="Statistics period start")
    period_end: str = Field(..., description="Statistics period end")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_payouts": 50,
                "total_amount": 5000.0,
                "pending_payouts": 5,
                "completed_payouts": 42,
                "failed_payouts": 3,
                "average_amount": 100.0,
                "total_fees": 50.0,
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-10T23:59:59Z"
            }
        }

class PayoutBatch(BaseModel):
    """Payout batch model"""
    batch_id: str = Field(..., description="Unique batch identifier")
    batch_name: str = Field(..., description="Batch name")
    payout_ids: list[str] = Field(..., description="List of payout IDs")
    total_count: int = Field(..., description="Total number of payouts")
    total_amount: float = Field(..., description="Total batch amount")
    status: str = Field(..., description="Batch status")
    priority: int = Field(..., description="Batch priority (1-10)")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch_abc123def456",
                "batch_name": "Monthly Payouts",
                "payout_ids": ["payout_1", "payout_2", "payout_3"],
                "total_count": 3,
                "total_amount": 300.0,
                "status": "pending",
                "priority": 5,
                "created_at": "2025-01-10T19:08:00Z",
                "updated_at": "2025-01-10T19:08:00Z"
            }
        }
