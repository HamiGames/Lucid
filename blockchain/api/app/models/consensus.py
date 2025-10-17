"""
Consensus Data Models
Pydantic models for PoOT consensus, voting, and validator operations.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator


class ConsensusState(str, Enum):
    """Consensus round state enumeration."""
    INITIALIZED = "initialized"
    VOTING = "voting"
    COUNTING = "counting"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class VoteType(str, Enum):
    """Vote type enumeration."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class ValidatorStatus(str, Enum):
    """Validator status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    SLASHED = "slashed"


class ConsensusVote(BaseModel):
    """Individual consensus vote."""
    
    vote_id: Optional[str] = Field(None, description="Unique vote identifier")
    round_id: str = Field(..., description="Consensus round identifier")
    block_hash: str = Field(..., description="Hash of block being voted on")
    voter_id: str = Field(..., description="ID of voting validator")
    vote: VoteType = Field(..., description="Vote decision")
    poot_score: float = Field(..., ge=0, description="PoOT score of voter")
    signature: str = Field(..., description="Vote signature")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Vote timestamp")
    
    # Additional vote metadata
    voting_power: float = Field(default=1.0, ge=0, description="Voting power weight")
    justification: Optional[str] = Field(None, description="Vote justification")
    
    @validator('block_hash')
    def validate_block_hash(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Block hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Block hash must be a valid hexadecimal string')
        return v.lower()
        
    @validator('signature')
    def validate_signature(cls, v):
        if not isinstance(v, str) or len(v) < 64:
            raise ValueError('Signature must be at least 64 characters')
        return v
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConsensusRound(BaseModel):
    """Consensus round for block validation."""
    
    round_id: str = Field(..., description="Unique round identifier")
    block_hash: str = Field(..., description="Hash of block being validated")
    block_height: int = Field(..., ge=0, description="Height of block being validated")
    state: ConsensusState = Field(default=ConsensusState.INITIALIZED, description="Round state")
    
    # Participants and voting
    participants: List[str] = Field(..., description="List of validator IDs")
    votes: List[ConsensusVote] = Field(default_factory=list, description="Votes received")
    required_votes: int = Field(..., ge=1, description="Minimum votes required")
    consensus_threshold: float = Field(default=0.67, ge=0.5, le=1.0, description="Consensus threshold")
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Round start time")
    voting_deadline: datetime = Field(..., description="Voting deadline")
    completed_at: Optional[datetime] = Field(None, description="Round completion time")
    
    # Results
    consensus_reached: bool = Field(default=False, description="Whether consensus was reached")
    final_decision: Optional[VoteType] = Field(None, description="Final consensus decision")
    winning_vote_count: int = Field(default=0, ge=0, description="Number of winning votes")
    total_voting_power: float = Field(default=0.0, ge=0, description="Total voting power")
    
    @validator('block_hash')
    def validate_block_hash(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Block hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Block hash must be a valid hexadecimal string')
        return v.lower()
        
    @validator('participants')
    def validate_participants(cls, v):
        if not v:
            raise ValueError('At least one participant is required')
        return v
        
    def get_vote_counts(self) -> Dict[VoteType, int]:
        """Get count of votes by type."""
        counts = {vote_type: 0 for vote_type in VoteType}
        for vote in self.votes:
            counts[vote.vote] += 1
        return counts
        
    def get_voting_power_by_type(self) -> Dict[VoteType, float]:
        """Get total voting power by vote type."""
        power = {vote_type: 0.0 for vote_type in VoteType}
        for vote in self.votes:
            power[vote.vote] += vote.voting_power
        return power
        
    def is_expired(self) -> bool:
        """Check if voting deadline has passed."""
        return datetime.utcnow() > self.voting_deadline
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PoOTScore(BaseModel):
    """Proof of Observation Time score."""
    
    validator_id: str = Field(..., description="Validator identifier")
    session_id: str = Field(..., description="Session being observed")
    observation_time_seconds: float = Field(..., ge=0, description="Observation time in seconds")
    base_score: float = Field(..., ge=0, description="Base PoOT score")
    multiplier: float = Field(default=1.0, ge=0, description="Score multiplier")
    final_score: float = Field(..., ge=0, description="Final calculated score")
    
    # Score calculation metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow, description="Score calculation time")
    block_height: int = Field(..., ge=0, description="Block height when calculated")
    verification_hash: str = Field(..., description="Hash for score verification")
    
    @validator('verification_hash')
    def validate_verification_hash(cls, v):
        if not isinstance(v, str) or len(v) != 64:
            raise ValueError('Verification hash must be a 64-character hexadecimal string')
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('Verification hash must be a valid hexadecimal string')
        return v.lower()
        
    @validator('final_score')
    def validate_final_score(cls, v, values):
        base_score = values.get('base_score', 0)
        multiplier = values.get('multiplier', 1.0)
        expected_score = base_score * multiplier
        if abs(v - expected_score) > 0.001:  # Allow small floating point differences
            raise ValueError('Final score must equal base_score * multiplier')
        return v
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ValidatorInfo(BaseModel):
    """Information about a validator."""
    
    validator_id: str = Field(..., description="Unique validator identifier")
    public_key: str = Field(..., description="Validator public key")
    address: str = Field(..., description="Validator address")
    status: ValidatorStatus = Field(default=ValidatorStatus.ACTIVE, description="Validator status")
    
    # Staking and rewards
    stake_amount: float = Field(default=0.0, ge=0, description="Staked amount")
    voting_power: float = Field(default=1.0, ge=0, description="Voting power")
    total_rewards: float = Field(default=0.0, ge=0, description="Total rewards earned")
    
    # Performance metrics
    total_votes: int = Field(default=0, ge=0, description="Total votes cast")
    successful_votes: int = Field(default=0, ge=0, description="Successful votes")
    missed_votes: int = Field(default=0, ge=0, description="Missed votes")
    average_poot_score: float = Field(default=0.0, ge=0, description="Average PoOT score")
    
    # Registration and activity
    registered_at: datetime = Field(default_factory=datetime.utcnow, description="Registration time")
    last_active: datetime = Field(default_factory=datetime.utcnow, description="Last activity time")
    last_vote_block: Optional[int] = Field(None, ge=0, description="Last block voted on")
    
    @validator('public_key')
    def validate_public_key(cls, v):
        if not isinstance(v, str) or len(v) < 64:
            raise ValueError('Public key must be at least 64 characters')
        return v
        
    def get_success_rate(self) -> float:
        """Calculate vote success rate."""
        if self.total_votes == 0:
            return 0.0
        return self.successful_votes / self.total_votes
        
    def is_active(self) -> bool:
        """Check if validator is currently active."""
        return self.status == ValidatorStatus.ACTIVE
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConsensusConfig(BaseModel):
    """Configuration for consensus mechanism."""
    
    consensus_algorithm: str = Field(default="PoOT", description="Consensus algorithm name")
    block_time_seconds: int = Field(default=10, ge=1, description="Target block time")
    consensus_timeout_seconds: int = Field(default=30, ge=1, description="Consensus timeout")
    min_validators: int = Field(default=3, ge=1, description="Minimum validators required")
    consensus_threshold: float = Field(default=0.67, ge=0.5, le=1.0, description="Consensus threshold")
    
    # PoOT specific settings
    min_observation_time_seconds: int = Field(default=60, ge=1, description="Minimum observation time")
    poot_score_multiplier: float = Field(default=1.0, ge=0, description="PoOT score multiplier")
    validator_rotation_blocks: int = Field(default=100, ge=1, description="Validator rotation frequency")
    
    # Penalties and rewards
    missed_vote_penalty: float = Field(default=0.01, ge=0, description="Penalty for missed votes")
    successful_vote_reward: float = Field(default=0.1, ge=0, description="Reward for successful votes")
    slash_threshold: int = Field(default=10, ge=1, description="Consecutive misses before slashing")


class ConsensusStats(BaseModel):
    """Statistics about consensus operations."""
    
    total_rounds: int = Field(..., ge=0, description="Total consensus rounds")
    successful_rounds: int = Field(..., ge=0, description="Successful consensus rounds")
    failed_rounds: int = Field(..., ge=0, description="Failed consensus rounds")
    timeout_rounds: int = Field(..., ge=0, description="Timed out consensus rounds")
    
    average_round_time_seconds: float = Field(..., ge=0, description="Average round completion time")
    average_votes_per_round: float = Field(..., ge=0, description="Average votes per round")
    current_validators: int = Field(..., ge=0, description="Current number of validators")
    active_validators: int = Field(..., ge=0, description="Currently active validators")
    
    last_round_id: Optional[str] = Field(None, description="ID of last consensus round")
    last_round_time: Optional[datetime] = Field(None, description="Time of last consensus round")
    last_updated: datetime = Field(..., description="When stats were last updated")
    
    def get_success_rate(self) -> float:
        """Calculate consensus success rate."""
        if self.total_rounds == 0:
            return 0.0
        return self.successful_rounds / self.total_rounds
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
