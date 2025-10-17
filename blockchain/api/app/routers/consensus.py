"""
Consensus Router

This module contains the consensus mechanism endpoints.
Implements the OpenAPI 3.0 specification for PoOT consensus operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging

from ..schemas.consensus import (
    ConsensusStatus, ConsensusParticipants, ConsensusVoteRequest,
    ConsensusVoteResponse, ConsensusHistory
)
from ..dependencies import get_current_user, verify_api_key, require_read_permission, require_write_permission
from ..services.consensus_service import ConsensusService
from ..errors import ConsensusVoteException

router = APIRouter(
    prefix="/consensus",
    tags=["Consensus"],
    responses={404: {"description": "Consensus data not found"}},
)

logger = logging.getLogger(__name__)

@router.get("/status", response_model=ConsensusStatus)
async def get_consensus_status(
    user = Depends(require_read_permission)
):
    """
    Returns the current status of the consensus mechanism.
    
    Provides real-time consensus information including:
    - Current consensus round and phase
    - Block height and active validators
    - Total stake and consensus reached status
    - Last block timestamp
    
    Consensus phases:
    - proposal: Block proposal phase
    - voting: Vote collection phase
    - finalization: Block finalization phase
    
    Useful for monitoring consensus health and progress.
    """
    try:
        logger.info("Fetching consensus status")
        status_data = await ConsensusService.get_status()
        return ConsensusStatus(**status_data)
    except Exception as e:
        logger.error(f"Failed to fetch consensus status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve consensus status"
        )

@router.get("/participants", response_model=ConsensusParticipants)
async def list_consensus_participants(
    user = Depends(require_read_permission)
):
    """
    Returns a list of nodes participating in consensus.
    
    Provides information about consensus participants including:
    - Node ID and network address
    - Node status (active, standby, offline)
    - Stake amount and last activity
    - Total and active participant counts
    
    Node statuses:
    - active: Currently participating in consensus
    - standby: Available but not actively participating
    - offline: Not available for consensus
    """
    try:
        logger.info("Listing consensus participants")
        participants_data = await ConsensusService.list_participants()
        return ConsensusParticipants(**participants_data)
    except Exception as e:
        logger.error(f"Failed to list consensus participants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve consensus participants"
        )

@router.post("/vote", response_model=ConsensusVoteResponse)
async def submit_consensus_vote(
    vote_request: ConsensusVoteRequest,
    user = Depends(require_write_permission)
):
    """
    Submits a vote for consensus on a block or proposal.
    
    Allows consensus participants to submit votes on:
    - Block proposals
    - Consensus decisions
    - Network proposals
    
    Vote process:
    1. Validates vote request
    2. Verifies node identity and stake
    3. Records vote in consensus system
    4. Returns vote ID and status
    
    Vote decisions:
    - approve: Approve the proposal/block
    - reject: Reject the proposal/block
    
    Requires valid node credentials and sufficient stake.
    """
    try:
        logger.info("Submitting consensus vote")
        vote_response = await ConsensusService.submit_vote(vote_request.dict())
        return ConsensusVoteResponse(**vote_response)
    except Exception as e:
        logger.error(f"Failed to submit consensus vote: {e}")
        raise ConsensusVoteException(
            vote_id=vote_request.node_id,
            reason=str(e)
        )

@router.get("/history", response_model=ConsensusHistory)
async def get_consensus_history(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    user = Depends(require_read_permission)
):
    """
    Returns the history of consensus decisions and votes.
    
    Provides historical consensus information including:
    - Consensus events and decisions
    - Vote submissions and results
    - Block proposals and finalizations
    - Consensus round history
    
    Event types:
    - block_proposed: New block proposal
    - vote_submitted: Consensus vote submitted
    - consensus_reached: Consensus decision reached
    - block_finalized: Block finalized in consensus
    
    Useful for auditing consensus decisions and analyzing consensus behavior.
    """
    try:
        logger.info(f"Fetching consensus history with limit={limit}, offset={offset}")
        history_data = await ConsensusService.get_history(limit, offset)
        return ConsensusHistory(**history_data)
    except Exception as e:
        logger.error(f"Failed to fetch consensus history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve consensus history"
        )