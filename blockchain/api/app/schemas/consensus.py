"""
Consensus Schema Models

This module defines Pydantic models for consensus mechanism API endpoints.
Implements the OpenAPI 3.0 specification for PoOT (Proof of Observation Time) consensus.

Models:
- ConsensusStatus: Current consensus status
- ConsensusParticipants: List of consensus participants
- ConsensusVoteRequest: Consensus vote request
- ConsensusVoteResponse: Consensus vote response
- ConsensusHistory: Consensus history
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class NodeInfo(BaseModel):
    """Information about a consensus participant node."""
    node_id: str = Field(..., description="Node identifier")
    address: str = Field(..., description="Node network address")
    status: str = Field(..., description="Node status", enum=["active", "standby", "offline"])
    stake: float = Field(..., description="Node stake amount")
    last_activity: datetime = Field(..., description="Last activity timestamp")


class ConsensusStatus(BaseModel):
    """Current status of the consensus mechanism."""
    current_round: int = Field(..., description="Current consensus round")
    phase: str = Field(..., description="Current consensus phase", enum=["proposal", "voting", "finalization"])
    block_height: int = Field(..., description="Current block height")
    active_validators: int = Field(..., description="Number of active validators")
    total_stake: float = Field(..., description="Total stake in the network")
    consensus_reached: bool = Field(..., description="Whether consensus has been reached")
    last_block_time: datetime = Field(..., description="Last block timestamp")


class ConsensusParticipants(BaseModel):
    """List of nodes participating in consensus."""
    participants: List[NodeInfo] = Field(..., description="List of consensus participants")
    total_count: int = Field(..., description="Total number of participants")
    active_count: int = Field(..., description="Number of active participants")


class ConsensusVoteRequest(BaseModel):
    """Request for submitting a consensus vote."""
    node_id: str = Field(..., description="Node identifier")
    block_hash: str = Field(..., description="Block hash to vote on", regex=r'^[a-fA-F0-9]{64}$')
    vote: str = Field(..., description="Vote decision", enum=["approve", "reject"])
    signature: str = Field(..., description="Vote signature")
    timestamp: datetime = Field(..., description="Vote timestamp")


class ConsensusVoteResponse(BaseModel):
    """Response after submitting a consensus vote."""
    vote_id: str = Field(..., description="Unique vote identifier")
    status: str = Field(..., description="Vote status", enum=["accepted", "rejected", "pending"])
    submitted_at: datetime = Field(..., description="Vote submission timestamp")
    block_height: int = Field(..., description="Block height for the vote")


class ConsensusEvent(BaseModel):
    """A single consensus event in the history."""
    event_id: str = Field(..., description="Unique event identifier")
    type: str = Field(..., description="Event type", enum=["block_proposed", "vote_submitted", "consensus_reached", "block_finalized"])
    block_height: int = Field(..., description="Block height")
    timestamp: datetime = Field(..., description="Event timestamp")
    details: Dict[str, Any] = Field(..., description="Event details")


class ConsensusHistory(BaseModel):
    """History of consensus decisions and votes."""
    events: List[ConsensusEvent] = Field(..., description="List of consensus events")
    total_events: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of events per page")
