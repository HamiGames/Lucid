"""
LUCID Payment Systems - Payment Models
Data models and enums for payment operations
Distroless container: lucid-payment-gateway:latest
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Enums for Payment Types and Status
# ============================================================================

class PaymentStatus(Enum):
    """Payment status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentType(Enum):
    """Payment types enum"""
    TRX_TRANSFER = "trx_transfer"
    USDT_TRANSFER = "usdt_transfer"
    CONTRACT_PAYMENT = "contract_payment"
    STAKING_PAYMENT = "staking_payment"
    FEE_PAYMENT = "fee_payment"


class PaymentMethod(Enum):
    """Payment methods enum"""
    WALLET = "wallet"
    HARDWARE_WALLET = "hardware_wallet"
    MULTISIG = "multisig"
    DELEGATED = "delegated"


# ============================================================================
# Data Classes for Internal Storage
# ============================================================================

@dataclass
class PaymentInfo:
    """Payment information - internal data structure"""
    payment_id: str
    from_address: str
    to_address: str
    amount: float
    currency: str
    payment_type: PaymentType
    payment_method: PaymentMethod
    status: PaymentStatus
    transaction_id: Optional[str]
    fee: float
    created_at: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]]


@dataclass
class PaymentRequest:
    """Payment request - internal data structure"""
    from_address: str
    to_address: str
    amount: float
    currency: str
    payment_type: PaymentType
    payment_method: PaymentMethod
    private_key: Optional[str]
    metadata: Optional[Dict[str, Any]]


# ============================================================================
# Pydantic Models for API
# ============================================================================

class PaymentCreateRequest(BaseModel):
    """Payment creation request"""
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(..., description="Currency (TRX, USDT)")
    payment_type: PaymentType = Field(..., description="Payment type")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    private_key: Optional[str] = Field(None, description="Private key for signing")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class PaymentResponse(BaseModel):
    """Payment response"""
    payment_id: str
    transaction_id: Optional[str]
    status: str
    amount: float
    currency: str
    from_address: str
    to_address: str
    fee: float
    created_at: str
    processed_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]


class PaymentStatusRequest(BaseModel):
    """Payment status request"""
    payment_id: str = Field(..., description="Payment ID")


class PaymentStatusResponse(BaseModel):
    """Payment status response"""
    payment_id: str
    status: str
    transaction_id: Optional[str]
    amount: float
    currency: str
    from_address: str
    to_address: str
    fee: float
    created_at: str
    processed_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]


# ============================================================================
# Additional Request/Response Models
# ============================================================================

class PaymentListResponse(BaseModel):
    """Payment list response"""
    payments: list
    total: int
    limit: int
    offset: int


class PaymentStatsResponse(BaseModel):
    """Payment statistics response"""
    total_payments: int
    pending_payments: int
    processing_payments: int
    completed_payments: int
    failed_payments: int
    total_amount: float
    completed_amount: float
    payment_status: Dict[str, int]
    payment_types: Dict[str, int]
    timestamp: str


class PaymentCancelRequest(BaseModel):
    """Cancel payment request"""
    reason: Optional[str] = Field(None, description="Cancellation reason")


class PaymentRefundRequest(BaseModel):
    """Refund payment request"""
    reason: Optional[str] = Field(None, description="Refund reason")
    amount: Optional[float] = Field(None, description="Partial refund amount (if not specified, full amount will be refunded)")


class BatchPaymentRequest(BaseModel):
    """Batch payment request"""
    payments: list = Field(..., description="List of payment requests")
    batch_id: Optional[str] = Field(None, description="Batch identifier")


class BatchPaymentResponse(BaseModel):
    """Batch payment response"""
    batch_id: str
    total_payments: int
    created_payments: int
    failed_payments: int
    payment_ids: list
    timestamp: str
