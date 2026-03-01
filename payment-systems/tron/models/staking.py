"""
LUCID Payment Systems - TRON Staking Data Models
Pydantic models for staking operations
Distroless container: lucid-trx-staking:latest
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class StakingResourceType(str, Enum):
    """Staking resource types"""
    BANDWIDTH = "bandwidth"
    ENERGY = "energy"


class StakingOperationType(str, Enum):
    """Staking operation types"""
    FREEZE = "freeze"
    UNFREEZE = "unfreeze"
    VOTE = "vote"
    DELEGATE = "delegate"
    UNDELEGATE = "undelegate"
    CLAIM_REWARD = "claim_reward"


class StakingStatusType(str, Enum):
    """Staking status types"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    EXPIRED = "expired"
    COMPLETED = "completed"
    FAILED = "failed"


class FreezeBalanceRequest(BaseModel):
    """Freeze balance request"""
    address: str = Field(..., description="Address to freeze balance from")
    amount: float = Field(..., description="Amount to freeze in TRX", gt=0)
    duration: int = Field(3, description="Lock duration in days", ge=1, le=365)
    resource: StakingResourceType = Field(
        StakingResourceType.BANDWIDTH,
        description="Resource type to stake (BANDWIDTH or ENERGY)"
    )

    @validator('address')
    def validate_address(cls, v):
        """Validate TRON address format"""
        if not v.startswith('T'):
            raise ValueError("TRON address must start with 'T'")
        if len(v) != 34:
            raise ValueError("TRON address must be 34 characters long")
        return v


class UnfreezeBalanceRequest(BaseModel):
    """Unfreeze balance request"""
    address: str = Field(..., description="Address to unfreeze balance from")
    resource: StakingResourceType = Field(
        StakingResourceType.BANDWIDTH,
        description="Resource type to unfreeze (BANDWIDTH or ENERGY)"
    )

    @validator('address')
    def validate_address(cls, v):
        """Validate TRON address format"""
        if not v.startswith('T'):
            raise ValueError("TRON address must start with 'T'")
        if len(v) != 34:
            raise ValueError("TRON address must be 34 characters long")
        return v


class StakingRecord(BaseModel):
    """Staking record model"""
    staking_id: str = Field(..., description="Unique staking ID")
    address: str = Field(..., description="Address that initiated staking")
    amount: float = Field(..., description="Amount staked in TRX")
    resource: StakingResourceType = Field(..., description="Resource type")
    duration: int = Field(..., description="Staking duration in days")
    operation_type: StakingOperationType = Field(..., description="Type of operation")
    status: StakingStatusType = Field(..., description="Current status")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    transaction_hash: Optional[str] = Field(None, description="TRON transaction hash")
    block_number: Optional[int] = Field(None, description="Block number when recorded")
    energy_reward: Optional[float] = Field(None, description="Energy reward earned")
    bandwidth_reward: Optional[float] = Field(None, description="Bandwidth reward earned")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class StakingResponse(BaseModel):
    """Staking operation response"""
    staking_id: str = Field(..., description="Staking ID")
    address: str = Field(..., description="Address")
    amount: float = Field(..., description="Amount staked")
    resource: str = Field(..., description="Resource type")
    status: str = Field(..., description="Status")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")
    transaction_hash: Optional[str] = Field(None, description="Transaction hash")
    message: str = Field(..., description="Response message")


class StakingListResponse(BaseModel):
    """Staking list response"""
    stakings: List[StakingRecord] = Field(..., description="List of staking records")
    total_count: int = Field(..., description="Total staking count")
    active_count: int = Field(..., description="Active staking count")
    total_staked_trx: float = Field(..., description="Total TRX staked")
    timestamp: str = Field(..., description="Response timestamp")


class RewardInfo(BaseModel):
    """Reward information"""
    address: str = Field(..., description="Address")
    energy_reward: float = Field(..., description="Energy reward")
    bandwidth_reward: float = Field(..., description="Bandwidth reward")
    total_reward: float = Field(..., description="Total reward")
    last_reward_time: Optional[str] = Field(None, description="Last reward timestamp")


class StakingStatsResponse(BaseModel):
    """Staking statistics response"""
    total_staking_records: int = Field(..., description="Total staking records")
    active_staking_records: int = Field(..., description="Active staking records")
    inactive_staking_records: int = Field(..., description="Inactive staking records")
    total_staked_trx: float = Field(..., description="Total TRX staked")
    total_bandwidth_resources: int = Field(..., description="Total bandwidth resources")
    total_energy_resources: int = Field(..., description="Total energy resources")
    total_rewards_earned: float = Field(..., description="Total rewards earned")
    timestamp: str = Field(..., description="Response timestamp")


class VoteWitnessRequest(BaseModel):
    """Vote witness request"""
    address: str = Field(..., description="Address to vote from")
    witness_address: str = Field(..., description="Witness address to vote for")
    vote_count: int = Field(..., description="Number of votes", gt=0)

    @validator('address', 'witness_address')
    def validate_address(cls, v):
        """Validate TRON address format"""
        if not v.startswith('T'):
            raise ValueError("TRON address must start with 'T'")
        if len(v) != 34:
            raise ValueError("TRON address must be 34 characters long")
        return v


class DelegateResourceRequest(BaseModel):
    """Delegate resource request"""
    from_address: str = Field(..., description="Address delegating resources")
    to_address: str = Field(..., description="Address receiving resources")
    amount: float = Field(..., description="Amount to delegate", gt=0)
    resource: StakingResourceType = Field(..., description="Resource type (BANDWIDTH or ENERGY)")
    lock: bool = Field(False, description="Whether to lock the delegation")

    @validator('from_address', 'to_address')
    def validate_address(cls, v):
        """Validate TRON address format"""
        if not v.startswith('T'):
            raise ValueError("TRON address must start with 'T'")
        if len(v) != 34:
            raise ValueError("TRON address must be 34 characters long")
        return v


class ClaimRewardRequest(BaseModel):
    """Claim reward request"""
    address: str = Field(..., description="Address to claim rewards for")
    reward_type: Optional[str] = Field(None, description="Reward type to claim (all/energy/bandwidth)")

    @validator('address')
    def validate_address(cls, v):
        """Validate TRON address format"""
        if not v.startswith('T'):
            raise ValueError("TRON address must start with 'T'")
        if len(v) != 34:
            raise ValueError("TRON address must be 34 characters long")
        return v


class ResourceDelegate(BaseModel):
    """Resource delegation record"""
    id: str = Field(..., description="Delegation ID")
    from_address: str = Field(..., description="From address")
    to_address: str = Field(..., description="To address")
    resource_type: StakingResourceType = Field(..., description="Resource type")
    amount: float = Field(..., description="Amount delegated")
    locked: bool = Field(..., description="Whether delegation is locked")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")


class WithdrawRewardRequest(BaseModel):
    """Withdraw reward request"""
    address: str = Field(..., description="Address to withdraw rewards")
    amount: Optional[float] = Field(None, description="Amount to withdraw (null for all)")

    @validator('address')
    def validate_address(cls, v):
        """Validate TRON address format"""
        if not v.startswith('T'):
            raise ValueError("TRON address must start with 'T'")
        if len(v) != 34:
            raise ValueError("TRON address must be 34 characters long")
        return v


class ResourceInfo(BaseModel):
    """Resource information"""
    address: str = Field(..., description="Address")
    bandwidth_limit: int = Field(..., description="Bandwidth limit")
    bandwidth_used: int = Field(..., description="Bandwidth used")
    bandwidth_available: int = Field(..., description="Bandwidth available")
    energy_limit: int = Field(..., description="Energy limit")
    energy_used: int = Field(..., description="Energy used")
    energy_available: int = Field(..., description="Energy available")
    frozen_balance: float = Field(..., description="Frozen balance for resources")
    delegated_resources: int = Field(..., description="Number of delegated resources")


class StakingHistoryResponse(BaseModel):
    """Staking history response"""
    stakings: List[StakingRecord] = Field(..., description="Staking history")
    total_count: int = Field(..., description="Total count")
    start_date: str = Field(..., description="Start date")
    end_date: str = Field(..., description="End date")
    timestamp: str = Field(..., description="Response timestamp")
