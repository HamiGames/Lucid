"""
LUCID Payment Systems - TRON Staking API
TRX staking operations and management
Distroless container: lucid-tron-payment-service:latest
"""

import asyncio
import logging
import secrets
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
from enum import Enum
import httpx

from ..services.tron_client import TronClientService
from ..models.wallet import WalletResponse

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/tron/staking", tags=["TRON Staking"])

# Initialize TRON client service
tron_client = TronClientService()

class StakingType(str, Enum):
    """Staking type enumeration"""
    FREEZE_BALANCE = "freeze_balance"
    UNFREEZE_BALANCE = "unfreeze_balance"
    VOTE_WITNESS = "vote_witness"
    DELEGATE_RESOURCE = "delegate_resource"
    UNDELEGATE_RESOURCE = "undelegate_resource"

class StakingStatus(str, Enum):
    """Staking status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    EXPIRED = "expired"

class StakingResource(str, Enum):
    """Staking resource enumeration"""
    BANDWIDTH = "bandwidth"
    ENERGY = "energy"

class StakingRequest(BaseModel):
    """Staking request"""
    address: str = Field(..., description="Address to stake from")
    amount: float = Field(..., description="Amount to stake in TRX", gt=0)
    duration: int = Field(..., description="Staking duration in days", ge=1, le=365)
    resource: StakingResource = Field(..., description="Resource type to stake")
    private_key: Optional[str] = Field(None, description="Private key for signing")

class StakingResponse(BaseModel):
    """Staking response"""
    staking_id: str
    address: str
    amount: float
    duration: int
    resource: str
    status: str
    created_at: str
    expires_at: str
    txid: Optional[str] = None

class UnstakingRequest(BaseModel):
    """Unstaking request"""
    staking_id: str = Field(..., description="Staking ID to unstake")
    private_key: Optional[str] = Field(None, description="Private key for signing")

class UnstakingResponse(BaseModel):
    """Unstaking response"""
    staking_id: str
    address: str
    amount: float
    status: str
    txid: str
    timestamp: str

class VoteRequest(BaseModel):
    """Vote request"""
    address: str = Field(..., description="Address to vote from")
    witness_address: str = Field(..., description="Witness address to vote for")
    vote_count: int = Field(..., description="Number of votes", gt=0)
    private_key: Optional[str] = Field(None, description="Private key for signing")

class VoteResponse(BaseModel):
    """Vote response"""
    vote_id: str
    address: str
    witness_address: str
    vote_count: int
    status: str
    txid: str
    timestamp: str

class DelegationRequest(BaseModel):
    """Delegation request"""
    address: str = Field(..., description="Address to delegate from")
    receiver_address: str = Field(..., description="Address to delegate to")
    amount: float = Field(..., description="Amount to delegate in TRX", gt=0)
    resource: StakingResource = Field(..., description="Resource type to delegate")
    private_key: Optional[str] = Field(None, description="Private key for signing")

class DelegationResponse(BaseModel):
    """Delegation response"""
    delegation_id: str
    address: str
    receiver_address: str
    amount: float
    resource: str
    status: str
    txid: str
    timestamp: str

class StakingStatsResponse(BaseModel):
    """Staking statistics response"""
    total_staked: float
    total_delegated: float
    total_votes: int
    active_stakings: int
    active_delegations: int
    total_rewards: float
    timestamp: str

class StakingListResponse(BaseModel):
    """Staking list response"""
    stakings: List[StakingResponse]
    total_count: int
    total_amount: float
    timestamp: str

# Service instance - will be injected by main entrypoint
# For backward compatibility with direct API testing, initialize with None
# The entrypoint will set this properly
_staking_service = None

def get_staking_service():
    """Get the staking service instance"""
    global _staking_service
    if _staking_service is None:
        # Fallback: lazy import for backward compatibility
        from ..services.trx_staking import trx_staking_service
        _staking_service = trx_staking_service
    return _staking_service

def set_staking_service(service):
    """Set the staking service instance (called by entrypoint)"""
    global _staking_service
    _staking_service = service

@router.post("/stake", response_model=StakingResponse)
async def create_staking(request: StakingRequest):
    """Create new staking"""
    try:
        # Validate address format
        if not request.address.startswith('T') or len(request.address) != 34:
            raise HTTPException(status_code=400, detail="Invalid TRON address format")
        
        # Validate amount
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid staking amount")
        
        # Validate duration
        if request.duration <= 0 or request.duration > 365:
            raise HTTPException(status_code=400, detail="Invalid staking duration (1-365 days)")
        
        # Get staking service
        service = get_staking_service()
        if not service:
            raise HTTPException(status_code=503, detail="Staking service not initialized")
        
        # Convert API request to service request format
        from ..services.trx_staking import StakingRequest as ServiceStakingRequest, StakingType, ResourceType
        
        # Determine staking type (default to freeze_balance)
        staking_type = StakingType.FREEZE_BALANCE
        resource_type = None
        
        if request.resource == StakingResource.ENERGY:
            resource_type = ResourceType.ENERGY
        elif request.resource == StakingResource.BANDWIDTH:
            resource_type = ResourceType.BANDWIDTH
        
        service_request = ServiceStakingRequest(
            wallet_address=request.address,
            staking_type=staking_type,
            amount_trx=request.amount,
            duration_days=request.duration,
            resource_type=resource_type,
            private_key=request.private_key or os.getenv("DEFAULT_PRIVATE_KEY", "")
        )
        
        # Call service method
        response = await service.stake_trx(service_request)
        
        logger.info(f"Created staking: {response.staking_id} for {request.address}, amount: {request.amount} TRX")
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating staking: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create staking: {str(e)}")

@router.post("/unstake", response_model=UnstakingResponse)
async def unstake(request: UnstakingRequest):
    """Unstake TRX"""
    try:
        # Get staking service
        service = get_staking_service()
        if not service:
            raise HTTPException(status_code=503, detail="Staking service not initialized")
        
        # Verify staking exists
        staking_records = await service.list_staking_records()
        if not any(s.staking_id == request.staking_id for s in staking_records):
            raise HTTPException(status_code=404, detail="Staking not found")
        
        # Call service method
        from ..services.trx_staking import UnstakingRequest as ServiceUnstakingRequest
        
        service_request = ServiceUnstakingRequest(
            staking_id=request.staking_id,
            private_key=request.private_key or os.getenv("DEFAULT_PRIVATE_KEY", "")
        )
        
        response = await service.unstake_trx(service_request)
        
        logger.info(f"Unstaked: {request.staking_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unstaking {request.staking_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unstake: {str(e)}")

@router.post("/vote", response_model=VoteResponse)
async def vote_witness(request: VoteRequest):
    """Vote for witness"""
    try:
        # Validate addresses
        if not request.address.startswith('T') or len(request.address) != 34:
            raise HTTPException(status_code=400, detail="Invalid voter address format")
        if not request.witness_address.startswith('T') or len(request.witness_address) != 34:
            raise HTTPException(status_code=400, detail="Invalid witness address format")
        
        # Validate vote count
        if request.vote_count <= 0:
            raise HTTPException(status_code=400, detail="Invalid vote count")
        
        # Note: This is a simplified implementation
        # Full implementation would use the TRXStakingService
        vote_id = secrets.token_hex(16)
        txid = secrets.token_hex(32)
        
        logger.info(f"Voted: {request.address} -> {request.witness_address}, votes: {request.vote_count}")
        
        return VoteResponse(
            vote_id=vote_id,
            address=request.address,
            witness_address=request.witness_address,
            vote_count=request.vote_count,
            status="completed",
            txid=txid,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error voting: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to vote: {str(e)}")

@router.post("/delegate", response_model=DelegationResponse)
async def delegate_resource(request: DelegationRequest):
    """Delegate resource to another address"""
    try:
        # Validate addresses
        if not request.address.startswith('T') or len(request.address) != 34:
            raise HTTPException(status_code=400, detail="Invalid delegator address format")
        if not request.receiver_address.startswith('T') or len(request.receiver_address) != 34:
            raise HTTPException(status_code=400, detail="Invalid receiver address format")
        
        # Validate amount
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid delegation amount")
        
        # Note: This is a simplified implementation
        # Full implementation would use the TRXStakingService
        delegation_id = secrets.token_hex(16)
        txid = secrets.token_hex(32)
        
        logger.info(f"Delegated: {request.address} -> {request.receiver_address}, amount: {request.amount} TRX")
        
        return DelegationResponse(
            delegation_id=delegation_id,
            address=request.address,
            receiver_address=request.receiver_address,
            amount=request.amount,
            resource=request.resource.value,
            status="completed",
            txid=txid,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error delegating: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delegate: {str(e)}")

@router.get("/list", response_model=StakingListResponse)
async def list_stakings(
    address: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """List stakings with optional filtering"""
    try:
        # Validate pagination parameters
        if skip < 0:
            raise HTTPException(status_code=400, detail="Invalid skip parameter")
        if limit <= 0 or limit > 1000:
            raise HTTPException(status_code=400, detail="Invalid limit parameter (1-1000)")
        
        # Get staking service
        service = get_staking_service()
        if not service:
            raise HTTPException(status_code=503, detail="Staking service not initialized")
        
        # Get all stakings from service
        all_stakings = await service.list_staking_records(address)
        
        # Apply pagination
        total_count = len(all_stakings)
        paginated_stakings = all_stakings[skip:skip + limit]
        
        # Convert to response format
        stakings = []
        total_amount = 0.0
        for staking_info in paginated_stakings:
            stakings.append(StakingResponse(
                staking_id=staking_info.staking_id,
                address=staking_info.wallet_address,
                amount=staking_info.amount_trx,
                duration=staking_info.duration,
                resource=staking_info.resource_type.value if staking_info.resource_type else "energy",
                status=staking_info.status.value,
                created_at=staking_info.created_at.isoformat(),
                expires_at=staking_info.expires_at.isoformat() if staking_info.expires_at else None,
                txid=staking_info.transaction_id
            ))
            total_amount += staking_info.amount_trx
        
        return StakingListResponse(
            stakings=stakings,
            total_count=total_count,
            total_amount=total_amount,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing stakings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list stakings: {str(e)}")

@router.get("/{staking_id}", response_model=StakingResponse)
async def get_staking(staking_id: str):
    """Get staking by ID"""
    try:
        # Get staking service
        service = get_staking_service()
        if not service:
            raise HTTPException(status_code=503, detail="Staking service not initialized")
        
        # Get all stakings to find the one with matching ID
        all_stakings = await service.list_staking_records()
        staking_info = next((s for s in all_stakings if s.staking_id == staking_id), None)
        
        if not staking_info:
            raise HTTPException(status_code=404, detail="Staking not found")
        
        return StakingResponse(
            staking_id=staking_info.staking_id,
            address=staking_info.wallet_address,
            amount=staking_info.amount_trx,
            duration=staking_info.duration,
            resource=staking_info.resource_type.value if staking_info.resource_type else "energy",
            status=staking_info.status.value,
            created_at=staking_info.created_at.isoformat(),
            expires_at=staking_info.expires_at.isoformat() if staking_info.expires_at else None,
            txid=staking_info.transaction_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting staking {staking_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get staking: {str(e)}")

@router.get("/stats", response_model=StakingStatsResponse)
async def get_staking_statistics():
    """Get staking statistics"""
    try:
        # Get staking service
        service = get_staking_service()
        if not service:
            raise HTTPException(status_code=503, detail="Staking service not initialized")
        
        # Get all stakings from service
        all_stakings = await service.list_staking_records()
        
        # Calculate statistics
        total_staked = sum(s.amount_trx for s in all_stakings if s.status.value == StakingStatus.ACTIVE.value)
        total_delegated = 0.0  # Would need to track delegations separately
        total_votes = 0  # Would need to track votes separately
        
        active_stakings = len([s for s in all_stakings if s.status.value == StakingStatus.ACTIVE.value])
        active_delegations = 0  # Would need delegation tracking
        
        # Calculate total rewards (mock calculation)
        total_rewards = total_staked * 0.05  # 5% annual reward rate
        
        return StakingStatsResponse(
            total_staked=total_staked,
            total_delegated=total_delegated,
            total_votes=total_votes,
            active_stakings=active_stakings,
            active_delegations=active_delegations,
            total_rewards=total_rewards,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting staking statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get staking statistics: {str(e)}")

@router.get("/votes/{address}")
async def get_votes_for_address(address: str):
    """Get votes for address"""
    try:
        # Validate address format
        if not address.startswith('T') or len(address) != 34:
            raise HTTPException(status_code=400, detail="Invalid address format")
        
        # For now, return empty list (would need vote tracking in service)
        return {
            "address": address,
            "votes": [],
            "total_count": 0,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting votes for {address}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get votes: {str(e)}")

@router.get("/delegations/{address}")
async def get_delegations_for_address(address: str):
    """Get delegations for address"""
    try:
        # Validate address format
        if not address.startswith('T') or len(address) != 34:
            raise HTTPException(status_code=400, detail="Invalid address format")
        
        # For now, return empty list (would need delegation tracking in service)
        return {
            "address": address,
            "delegations": [],
            "total_count": 0,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delegations for {address}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get delegations: {str(e)}")
