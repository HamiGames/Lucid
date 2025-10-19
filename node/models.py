#!/usr/bin/env python3
"""
Lucid Node Management - Data Models
Pydantic models for node management service
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum

class NodeStatus(str, Enum):
    """Node status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    PENDING = "pending"

class PoolStatus(str, Enum):
    """Pool status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    FULL = "full"
    EMPTY = "empty"

class PayoutStatus(str, Enum):
    """Payout status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProofType(str, Enum):
    """PoOT proof type enumeration"""
    STAKE_PROOF = "stake_proof"
    BALANCE_PROOF = "balance_proof"
    DELEGATION_PROOF = "delegation_proof"
    CUSTODY_PROOF = "custody_proof"
    LIQUIDITY_PROOF = "liquidity_proof"

class NodeInfo(BaseModel):
    """Node information model"""
    node_id: str = Field(..., description="Unique node identifier")
    address: str = Field(..., description="Node address")
    stake_amount: float = Field(..., description="Stake amount in USDT")
    status: NodeStatus = Field(..., description="Node status")
    created_at: datetime = Field(..., description="Node creation timestamp")
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")
    performance_metrics: Optional[Dict[str, Any]] = Field(None, description="Performance metrics")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PoolInfo(BaseModel):
    """Pool information model"""
    pool_id: str = Field(..., description="Unique pool identifier")
    pool_name: str = Field(..., description="Pool name")
    max_nodes: int = Field(..., description="Maximum number of nodes")
    current_nodes: int = Field(..., description="Current number of nodes")
    status: PoolStatus = Field(..., description="Pool status")
    created_at: datetime = Field(..., description="Pool creation timestamp")
    last_updated: datetime = Field(..., description="Last update timestamp")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Pool configuration")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PayoutInfo(BaseModel):
    """Payout information model"""
    payout_id: str = Field(..., description="Unique payout identifier")
    node_id: str = Field(..., description="Node identifier")
    amount_usdt: float = Field(..., description="Payout amount in USDT")
    fee_usdt: float = Field(..., description="Processing fee in USDT")
    net_amount_usdt: float = Field(..., description="Net payout amount in USDT")
    payout_address: str = Field(..., description="Destination address")
    status: PayoutStatus = Field(..., description="Payout status")
    description: Optional[str] = Field(None, description="Payout description")
    created_at: datetime = Field(..., description="Payout creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    transaction_id: Optional[str] = Field(None, description="Transaction ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PoOTProof(BaseModel):
    """PoOT (Proof of Ownership of Token) proof model"""
    node_id: str = Field(..., description="Node identifier")
    proof_type: ProofType = Field(..., description="Type of proof")
    stake_amount: float = Field(..., description="Stake amount used for proof")
    challenge: str = Field(..., description="Challenge string")
    proof_hash: str = Field(..., description="Proof hash")
    signature: str = Field(..., description="Proof signature")
    timestamp: datetime = Field(..., description="Proof timestamp")
    valid_until: datetime = Field(..., description="Proof validity expiration")
    confidence_score: float = Field(..., description="Confidence score (0.0-1.0)")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "node_id": self.node_id,
            "proof_type": self.proof_type.value,
            "stake_amount": self.stake_amount,
            "challenge": self.challenge,
            "proof_hash": self.proof_hash,
            "signature": self.signature,
            "timestamp": self.timestamp.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "confidence_score": self.confidence_score
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NodeMetrics(BaseModel):
    """Node metrics model"""
    node_id: str = Field(..., description="Node identifier")
    uptime_hours: float = Field(..., description="Uptime in hours")
    sessions_processed: int = Field(..., description="Number of sessions processed")
    bytes_relayed: int = Field(..., description="Bytes relayed")
    storage_challenges_passed: int = Field(..., description="Storage challenges passed")
    validation_signatures: int = Field(..., description="Validation signatures")
    work_credits: float = Field(..., description="Work credits earned")
    performance_score: float = Field(..., description="Performance score (0.0-1.0)")
    last_updated: datetime = Field(..., description="Last metrics update")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PoolMetrics(BaseModel):
    """Pool metrics model"""
    total_pools: int = Field(0, description="Total number of pools")
    total_nodes: int = Field(0, description="Total number of nodes")
    active_pools: int = Field(0, description="Number of active pools")
    full_pools: int = Field(0, description="Number of full pools")
    empty_pools: int = Field(0, description="Number of empty pools")
    max_nodes_per_pool: int = Field(100, description="Maximum nodes per pool")
    average_nodes_per_pool: float = Field(0.0, description="Average nodes per pool")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PayoutStatistics(BaseModel):
    """Payout statistics model"""
    total_payouts: int = Field(0, description="Total number of payouts")
    total_amount_usdt: float = Field(0.0, description="Total payout amount")
    total_fees_usdt: float = Field(0.0, description="Total fees collected")
    total_net_usdt: float = Field(0.0, description="Total net payouts")
    status_breakdown: Dict[str, int] = Field(default_factory=dict, description="Status breakdown")
    recent_payouts_24h: int = Field(0, description="Recent payouts in 24 hours")
    threshold_usdt: float = Field(10.0, description="Payout threshold")
    processing_fee_percent: float = Field(1.0, description="Processing fee percentage")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class HealthCheck(BaseModel):
    """Health check model"""
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SuccessResponse(BaseModel):
    """Success response model"""
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
