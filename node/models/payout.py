# Path: node/models/payout.py
# Lucid Node Management Models - Payout Data Models
# Based on LUCID-STRICT requirements per Spec-1c

"""
Payout data models for Lucid system.

This module provides Pydantic models for:
- Payout processing and tracking
- Batch payout operations
- Payment status monitoring
- TRON integration
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import re

class PayoutStatus(str, Enum):
    """Payout processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PayoutPriority(str, Enum):
    """Payout processing priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class Currency(str, Enum):
    """Supported currencies"""
    USDT = "USDT"
    LUCID = "LUCID"

class Payout(BaseModel):
    """Payout model"""
    payout_id: str = Field(..., description="Unique payout identifier", regex="^payout_[a-zA-Z0-9_-]+$")
    node_id: str = Field(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$")
    amount: float = Field(..., ge=0.000001, le=1000000, description="Payout amount")
    currency: Currency = Field(default=Currency.USDT, description="Currency type")
    wallet_address: str = Field(..., description="Destination wallet address")
    status: PayoutStatus = Field(..., description="Payout status")
    priority: PayoutPriority = Field(default=PayoutPriority.NORMAL, description="Processing priority")
    transaction_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    batch_id: Optional[str] = Field(None, description="Batch identifier for grouped payouts")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled execution time")
    processed_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, ge=0, le=5, description="Number of retry attempts")
    max_retries: int = Field(default=3, ge=0, le=5, description="Maximum retry attempts")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    
    @validator('payout_id')
    def validate_payout_id(cls, v):
        if not re.match(r'^payout_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Payout ID must match pattern: ^payout_[a-zA-Z0-9_-]+$")
        return v
    
    @validator('node_id')
    def validate_node_id(cls, v):
        if not re.match(r'^node_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Node ID must match pattern: ^node_[a-zA-Z0-9_-]+$")
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Payout amount must be greater than 0")
        return v
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v, values):
        if 'currency' in values:
            currency = values['currency']
            if currency == Currency.USDT:
                if not re.match(r'^[a-zA-Z0-9]{34}$', v):
                    raise ValueError("Invalid TRON wallet address format")
            elif currency == Currency.LUCID:
                if not re.match(r'^[a-zA-Z0-9]{42}$', v):
                    raise ValueError("Invalid LUCID wallet address format")
        return v
    
    @validator('retry_count')
    def validate_retry_count(cls, v, values):
        if 'max_retries' in values and v > values['max_retries']:
            raise ValueError("Retry count cannot exceed max retries")
        return v

class PayoutRequest(BaseModel):
    """Payout request model"""
    node_id: str = Field(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$")
    amount: float = Field(..., ge=0.000001, le=1000000, description="Payout amount")
    currency: Currency = Field(default=Currency.USDT, description="Currency type")
    wallet_address: str = Field(..., description="Destination wallet address")
    priority: PayoutPriority = Field(default=PayoutPriority.NORMAL, description="Processing priority")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled execution time")
    
    @validator('node_id')
    def validate_node_id(cls, v):
        if not re.match(r'^node_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Node ID must match pattern: ^node_[a-zA-Z0-9_-]+$")
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Payout amount must be greater than 0")
        return v
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v, values):
        if 'currency' in values:
            currency = values['currency']
            if currency == Currency.USDT:
                if not re.match(r'^[a-zA-Z0-9]{34}$', v):
                    raise ValueError("Invalid TRON wallet address format")
            elif currency == Currency.LUCID:
                if not re.match(r'^[a-zA-Z0-9]{42}$', v):
                    raise ValueError("Invalid LUCID wallet address format")
        return v

class BatchPayoutRequest(BaseModel):
    """Batch payout request model"""
    batch_id: str = Field(..., description="Batch identifier", regex="^batch_[a-zA-Z0-9_-]+$")
    payout_requests: List[PayoutRequest] = Field(..., min_items=1, max_items=1000, description="Payout requests")
    priority: PayoutPriority = Field(default=PayoutPriority.NORMAL, description="Batch processing priority")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled execution time")
    notification_url: Optional[str] = Field(None, description="Webhook URL for batch completion notification")
    
    @validator('batch_id')
    def validate_batch_id(cls, v):
        if not re.match(r'^batch_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Batch ID must match pattern: ^batch_[a-zA-Z0-9_-]+$")
        return v
    
    @validator('payout_requests')
    def validate_payout_requests(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Batch must contain at least one payout request")
        if len(v) > 1000:
            raise ValueError("Batch size cannot exceed 1000 payouts")
        return v

class PayoutBatch(BaseModel):
    """Payout batch model"""
    batch_id: str = Field(..., description="Batch identifier", regex="^batch_[a-zA-Z0-9_-]+$")
    total_payouts: int = Field(..., ge=1, description="Total number of payouts in batch")
    completed_payouts: int = Field(default=0, ge=0, description="Number of completed payouts")
    failed_payouts: int = Field(default=0, ge=0, description="Number of failed payouts")
    total_amount: float = Field(..., ge=0, description="Total payout amount")
    currency: Currency = Field(..., description="Currency type")
    status: PayoutStatus = Field(..., description="Batch status")
    priority: PayoutPriority = Field(..., description="Processing priority")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    @validator('batch_id')
    def validate_batch_id(cls, v):
        if not re.match(r'^batch_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Batch ID must match pattern: ^batch_[a-zA-Z0-9_-]+$")
        return v
    
    @validator('completed_payouts')
    def validate_completed_payouts(cls, v, values):
        if 'total_payouts' in values and v > values['total_payouts']:
            raise ValueError("Completed payouts cannot exceed total payouts")
        return v
    
    @validator('failed_payouts')
    def validate_failed_payouts(cls, v, values):
        if 'total_payouts' in values and v > values['total_payouts']:
            raise ValueError("Failed payouts cannot exceed total payouts")
        return v

class PayoutStatistics(BaseModel):
    """Payout statistics model"""
    time_range: str = Field(..., description="Time range for statistics")
    total_payouts: int = Field(..., ge=0, description="Total number of payouts")
    completed_payouts: int = Field(..., ge=0, description="Number of completed payouts")
    failed_payouts: int = Field(..., ge=0, description="Number of failed payouts")
    pending_payouts: int = Field(..., ge=0, description="Number of pending payouts")
    total_amount: float = Field(..., ge=0, description="Total payout amount")
    average_amount: float = Field(..., ge=0, description="Average payout amount")
    success_rate: float = Field(..., ge=0, le=100, description="Success rate percentage")
    average_processing_time: float = Field(..., ge=0, description="Average processing time in minutes")
    currency_breakdown: Dict[str, int] = Field(..., description="Payout count by currency")
    priority_breakdown: Dict[str, int] = Field(..., description="Payout count by priority")
    
    @validator('completed_payouts')
    def validate_completed_payouts(cls, v, values):
        if 'total_payouts' in values and v > values['total_payouts']:
            raise ValueError("Completed payouts cannot exceed total payouts")
        return v
    
    @validator('failed_payouts')
    def validate_failed_payouts(cls, v, values):
        if 'total_payouts' in values and v > values['total_payouts']:
            raise ValueError("Failed payouts cannot exceed total payouts")
        return v
    
    @validator('success_rate')
    def validate_success_rate(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Success rate must be between 0 and 100")
        return v

class PayoutQueue(BaseModel):
    """Payout queue status model"""
    queue_length: int = Field(..., ge=0, description="Number of payouts in queue")
    estimated_wait_time: int = Field(..., ge=0, description="Estimated wait time in minutes")
    processing_capacity: int = Field(..., ge=0, description="Current processing capacity")
    priority_distribution: Dict[str, int] = Field(..., description="Queue distribution by priority")
    currency_distribution: Dict[str, int] = Field(..., description="Queue distribution by currency")
    oldest_payout: Optional[datetime] = Field(None, description="Oldest payout in queue")
    newest_payout: Optional[datetime] = Field(None, description="Newest payout in queue")
    
    @validator('queue_length')
    def validate_queue_length(cls, v):
        if v < 0:
            raise ValueError("Queue length cannot be negative")
        return v
    
    @validator('estimated_wait_time')
    def validate_estimated_wait_time(cls, v):
        if v < 0:
            raise ValueError("Estimated wait time cannot be negative")
        return v
