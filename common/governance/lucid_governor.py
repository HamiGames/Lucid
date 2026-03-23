# Path: common/governance/lucid_governor.py
# Lucid RDP Governor Implementation
# Implements decentralized governance for Lucid RDP network
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Database integration
try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorDatabase = None

logger = logging.getLogger(__name__)

# Configuration from environment
GOVERNANCE_DB = os.getenv("GOVERNANCE_DB", "lucid_governance")
GOVERNANCE_CONTRACT_ADDRESS = os.getenv("GOVERNANCE_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000")
VOTING_PERIOD_DAYS = int(os.getenv("VOTING_PERIOD_DAYS", "3"))
EXECUTION_DELAY_HOURS = int(os.getenv("EXECUTION_DELAY_HOURS", "24"))
QUORUM_THRESHOLD = float(os.getenv("QUORUM_THRESHOLD", "0.1"))  # 10%
SUPPORT_THRESHOLD = float(os.getenv("SUPPORT_THRESHOLD", "0.5"))  # 50%


class ProposalStatus(Enum):
    """Proposal status states"""
    PENDING = "pending"
    ACTIVE = "active"
    SUCCEEDED = "succeeded"
    DEFEATED = "defeated"
    EXECUTED = "executed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ProposalType(Enum):
    """Types of governance proposals"""
    PARAMETER_CHANGE = "parameter_change"
    CONTRACT_UPGRADE = "contract_upgrade"
    TREASURY_ALLOCATION = "treasury_allocation"
    NETWORK_CONFIG = "network_config"
    EMERGENCY_ACTION = "emergency_action"
    POLICY_UPDATE = "policy_update"
    MEMBERSHIP_CHANGE = "membership_change"


class VoteType(Enum):
    """Vote types"""
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


class GovernanceRole(Enum):
    """Governance roles"""
    MEMBER = "member"
    DELEGATE = "delegate"
    ADMIN = "admin"
    EMERGENCY_ADMIN = "emergency_admin"


@dataclass
class Proposal:
    """Governance proposal"""
    proposal_id: str
    title: str
    description: str
    proposal_type: ProposalType
    proposer: str
    targets: List[str]  # Contract addresses to call
    values: List[int]   # ETH values to send
    calldatas: List[str]  # Function call data
    start_block: int
    end_block: int
    status: ProposalStatus
    for_votes: int = 0
    against_votes: int = 0
    abstain_votes: int = 0
    total_votes: int = 0
    quorum_reached: bool = False
    support_threshold_reached: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Vote:
    """Governance vote"""
    vote_id: str
    proposal_id: str
    voter: str
    vote_type: VoteType
    voting_power: int
    reason: Optional[str] = None
    voted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Delegate:
    """Vote delegation"""
    delegate_id: str
    delegator: str
    delegatee: str
    voting_power: int
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GovernanceMember:
    """Governance member"""
    member_id: str
    address: str
    role: GovernanceRole
    voting_power: int
    is_active: bool = True
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GovernanceEvent:
    """Governance event"""
    event_id: str
    event_type: str
    proposal_id: Optional[str] = None
    voter: Optional[str] = None
    amount: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class LucidGovernor:
    """
    Lucid RDP Governance Implementation
    
    Implements decentralized governance with:
    - Proposal creation and management
    - Voting mechanisms
    - Vote delegation
    - Quorum and threshold enforcement
    - Proposal execution
    - Emergency actions
    """
    
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """Initialize Lucid Governor"""
        self.db = db
        self.proposals: Dict[str, Proposal] = {}
        self.votes: Dict[str, Vote] = {}
        self.delegates: Dict[str, Delegate] = {}
        self.members: Dict[str, GovernanceMember] = {}
        self.events: List[GovernanceEvent] = []
        
        # Governance parameters
        self.voting_period_days = VOTING_PERIOD_DAYS
        self.execution_delay_hours = EXECUTION_DELAY_HOURS
        self.quorum_threshold = QUORUM_THRESHOLD
        self.support_threshold = SUPPORT_THRESHOLD
        
        # Initialize default members
        self._initialize_default_members()
        
        logger.info("Lucid Governor initialized")
    
    def _initialize_default_members(self) -> None:
        """Initialize default governance members"""
        default_members = [
            GovernanceMember(
                member_id="admin_001",
                address="0x0000000000000000000000000000000000000001",
                role=GovernanceRole.ADMIN,
                voting_power=1000
            ),
            GovernanceMember(
                member_id="member_001",
                address="0x0000000000000000000000000000000000000002",
                role=GovernanceRole.MEMBER,
                voting_power=100
            ),
            GovernanceMember(
                member_id="member_002",
                address="0x0000000000000000000000000000000000000003",
                role=GovernanceRole.MEMBER,
                voting_power=100
            )
        ]
        
        for member in default_members:
            self.members[member.member_id] = member
        
        logger.info(f"Initialized {len(default_members)} default governance members")
    
    async def start(self) -> bool:
        """Start the governance service"""
        try:
            if self.db:
                await self._setup_database_indexes()
                await self._load_governance_data()
            
            # Start background tasks
            asyncio.create_task(self._process_proposals())
            asyncio.create_task(self._cleanup_expired_data())
            
            logger.info("Lucid Governor started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Lucid Governor: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the governance service"""
        try:
            if self.db:
                await self._save_governance_data()
            
            logger.info("Lucid Governor stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping Lucid Governor: {e}")
            return False
    
    async def create_proposal(
        self,
        title: str,
        description: str,
        proposal_type: ProposalType,
        proposer: str,
        targets: List[str],
        values: List[int],
        calldatas: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new governance proposal"""
        try:
            # Validate proposer
            if not self._is_valid_member(proposer):
                raise ValueError(f"Invalid proposer: {proposer}")
            
            # Generate proposal ID
            proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
            
            # Calculate voting period
            start_time = datetime.now(timezone.utc)
            end_time = start_time + timedelta(days=self.voting_period_days)
            
            # Create proposal
            proposal = Proposal(
                proposal_id=proposal_id,
                title=title,
                description=description,
                proposal_type=proposal_type,
                proposer=proposer,
                targets=targets,
                values=values,
                calldatas=calldatas,
                start_block=0,  # Would be actual block number in real implementation
                end_block=0,    # Would be actual block number in real implementation
                status=ProposalStatus.PENDING,
                metadata=metadata or {}
            )
            
            self.proposals[proposal_id] = proposal
            
            if self.db:
                await self.db.proposals.insert_one(proposal.__dict__)
            
            # Create governance event
            event = GovernanceEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type="proposal_created",
                proposal_id=proposal_id,
                metadata={"proposer": proposer, "proposal_type": proposal_type.value}
            )
            self.events.append(event)
            
            logger.info(f"Created proposal: {proposal_id} by {proposer}")
            return proposal_id
            
        except Exception as e:
            logger.error(f"Failed to create proposal: {e}")
            raise
    
    async def cast_vote(
        self,
        proposal_id: str,
        voter: str,
        vote_type: VoteType,
        reason: Optional[str] = None
    ) -> bool:
        """Cast a vote on a proposal"""
        try:
            # Validate proposal
            if proposal_id not in self.proposals:
                raise ValueError(f"Proposal not found: {proposal_id}")
            
            proposal = self.proposals[proposal_id]
            
            # Check if proposal is active
            if proposal.status != ProposalStatus.ACTIVE:
                raise ValueError(f"Proposal is not active: {proposal.status.value}")
            
            # Check if voting period has ended
            if datetime.now(timezone.utc) > proposal.created_at + timedelta(days=self.voting_period_days):
                raise ValueError("Voting period has ended")
            
            # Validate voter
            if not self._is_valid_member(voter):
                raise ValueError(f"Invalid voter: {voter}")
            
            # Check if voter has already voted
            existing_vote = self._get_vote(proposal_id, voter)
            if existing_vote:
                raise ValueError("Voter has already voted on this proposal")
            
            # Calculate voting power
            voting_power = self._calculate_voting_power(voter)
            if voting_power == 0:
                raise ValueError("Voter has no voting power")
            
            # Create vote
            vote_id = f"vote_{uuid.uuid4().hex[:8]}"
            vote = Vote(
                vote_id=vote_id,
                proposal_id=proposal_id,
                voter=voter,
                vote_type=vote_type,
                voting_power=voting_power,
                reason=reason
            )
            
            self.votes[vote_id] = vote
            
            # Update proposal vote counts
            if vote_type == VoteType.FOR:
                proposal.for_votes += voting_power
            elif vote_type == VoteType.AGAINST:
                proposal.against_votes += voting_power
            elif vote_type == VoteType.ABSTAIN:
                proposal.abstain_votes += voting_power
            
            proposal.total_votes += voting_power
            
            # Check thresholds
            await self._check_proposal_thresholds(proposal)
            
            if self.db:
                await self.db.votes.insert_one(vote.__dict__)
                await self.db.proposals.replace_one(
                    {"proposal_id": proposal_id},
                    proposal.__dict__
                )
            
            # Create governance event
            event = GovernanceEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type="vote_cast",
                proposal_id=proposal_id,
                voter=voter,
                amount=voting_power,
                metadata={"vote_type": vote_type.value, "reason": reason}
            )
            self.events.append(event)
            
            logger.info(f"Vote cast: {voter} voted {vote_type.value} on {proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cast vote: {e}")
            return False
    
    async def execute_proposal(self, proposal_id: str, executor: str) -> bool:
        """Execute a successful proposal"""
        try:
            # Validate proposal
            if proposal_id not in self.proposals:
                raise ValueError(f"Proposal not found: {proposal_id}")
            
            proposal = self.proposals[proposal_id]
            
            # Check if proposal can be executed
            if proposal.status != ProposalStatus.SUCCEEDED:
                raise ValueError(f"Proposal cannot be executed: {proposal.status.value}")
            
            # Check execution delay
            execution_time = proposal.created_at + timedelta(hours=self.execution_delay_hours)
            if datetime.now(timezone.utc) < execution_time:
                raise ValueError("Execution delay not yet passed")
            
            # Validate executor
            if not self._is_valid_member(executor):
                raise ValueError(f"Invalid executor: {executor}")
            
            # Execute proposal (simulate contract calls)
            execution_success = await self._execute_proposal_calls(proposal)
            
            if execution_success:
                proposal.status = ProposalStatus.EXECUTED
                proposal.executed_at = datetime.now(timezone.utc)
                
                if self.db:
                    await self.db.proposals.replace_one(
                        {"proposal_id": proposal_id},
                        proposal.__dict__
                    )
                
                # Create governance event
                event = GovernanceEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    event_type="proposal_executed",
                    proposal_id=proposal_id,
                    metadata={"executor": executor}
                )
                self.events.append(event)
                
                logger.info(f"Proposal executed: {proposal_id} by {executor}")
                return True
            else:
                logger.error(f"Failed to execute proposal calls: {proposal_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute proposal: {e}")
            return False
    
    async def cancel_proposal(self, proposal_id: str, canceller: str) -> bool:
        """Cancel a proposal"""
        try:
            # Validate proposal
            if proposal_id not in self.proposals:
                raise ValueError(f"Proposal not found: {proposal_id}")
            
            proposal = self.proposals[proposal_id]
            
            # Check if proposal can be cancelled
            if proposal.status not in [ProposalStatus.PENDING, ProposalStatus.ACTIVE]:
                raise ValueError(f"Proposal cannot be cancelled: {proposal.status.value}")
            
            # Validate canceller (must be proposer or admin)
            if canceller != proposal.proposer and not self._is_admin(canceller):
                raise ValueError("Only proposer or admin can cancel proposal")
            
            # Cancel proposal
            proposal.status = ProposalStatus.CANCELLED
            proposal.cancelled_at = datetime.now(timezone.utc)
            
            if self.db:
                await self.db.proposals.replace_one(
                    {"proposal_id": proposal_id},
                    proposal.__dict__
                )
            
            # Create governance event
            event = GovernanceEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type="proposal_cancelled",
                proposal_id=proposal_id,
                metadata={"canceller": canceller}
            )
            self.events.append(event)
            
            logger.info(f"Proposal cancelled: {proposal_id} by {canceller}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel proposal: {e}")
            return False
    
    async def delegate_votes(self, delegator: str, delegatee: str) -> bool:
        """Delegate voting power to another member"""
        try:
            # Validate members
            if not self._is_valid_member(delegator):
                raise ValueError(f"Invalid delegator: {delegator}")
            
            if not self._is_valid_member(delegatee):
                raise ValueError(f"Invalid delegatee: {delegatee}")
            
            if delegator == delegatee:
                raise ValueError("Cannot delegate to self")
            
            # Check if delegation already exists
            existing_delegation = self._get_delegation(delegator)
            if existing_delegation:
                # Update existing delegation
                existing_delegation.delegatee = delegatee
                existing_delegation.updated_at = datetime.now(timezone.utc)
            else:
                # Create new delegation
                delegate_id = f"del_{uuid.uuid4().hex[:8]}"
                delegation = Delegate(
                    delegate_id=delegate_id,
                    delegator=delegator,
                    delegatee=delegatee,
                    voting_power=self._calculate_voting_power(delegator)
                )
                self.delegates[delegate_id] = delegation
            
            # Create governance event
            event = GovernanceEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type="votes_delegated",
                metadata={"delegator": delegator, "delegatee": delegatee}
            )
            self.events.append(event)
            
            logger.info(f"Votes delegated: {delegator} -> {delegatee}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delegate votes: {e}")
            return False
    
    async def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get proposal by ID"""
        return self.proposals.get(proposal_id)
    
    async def list_proposals(
        self,
        status: Optional[ProposalStatus] = None,
        proposer: Optional[str] = None,
        limit: int = 50
    ) -> List[Proposal]:
        """List proposals with optional filters"""
        proposals = list(self.proposals.values())
        
        # Apply filters
        if status:
            proposals = [p for p in proposals if p.status == status]
        
        if proposer:
            proposals = [p for p in proposals if p.proposer == proposer]
        
        # Sort by creation date (newest first)
        proposals.sort(key=lambda p: p.created_at, reverse=True)
        
        return proposals[:limit]
    
    async def get_proposal_votes(self, proposal_id: str) -> List[Vote]:
        """Get all votes for a proposal"""
        return [vote for vote in self.votes.values() if vote.proposal_id == proposal_id]
    
    async def get_member_voting_power(self, member_address: str) -> int:
        """Get voting power for a member"""
        return self._calculate_voting_power(member_address)
    
    async def get_governance_stats(self) -> Dict[str, Any]:
        """Get governance statistics"""
        total_proposals = len(self.proposals)
        active_proposals = len([p for p in self.proposals.values() if p.status == ProposalStatus.ACTIVE])
        executed_proposals = len([p for p in self.proposals.values() if p.status == ProposalStatus.EXECUTED])
        total_votes = len(self.votes)
        total_members = len(self.members)
        total_delegations = len(self.delegates)
        
        return {
            "total_proposals": total_proposals,
            "active_proposals": active_proposals,
            "executed_proposals": executed_proposals,
            "total_votes": total_votes,
            "total_members": total_members,
            "total_delegations": total_delegations,
            "quorum_threshold": self.quorum_threshold,
            "support_threshold": self.support_threshold,
            "voting_period_days": self.voting_period_days,
            "execution_delay_hours": self.execution_delay_hours
        }
    
    def _is_valid_member(self, address: str) -> bool:
        """Check if address is a valid governance member"""
        return any(member.address == address and member.is_active for member in self.members.values())
    
    def _is_admin(self, address: str) -> bool:
        """Check if address is an admin"""
        return any(
            member.address == address and 
            member.is_active and 
            member.role in [GovernanceRole.ADMIN, GovernanceRole.EMERGENCY_ADMIN]
            for member in self.members.values()
        )
    
    def _calculate_voting_power(self, address: str) -> int:
        """Calculate voting power for an address"""
        # Find member
        member = next((m for m in self.members.values() if m.address == address and m.is_active), None)
        if not member:
            return 0
        
        # Check for delegations
        delegation = self._get_delegation(address)
        if delegation:
            # If this address has delegated, they have no voting power
            return 0
        
        # Check if this address is a delegatee
        delegatee_power = sum(
            d.voting_power for d in self.delegates.values() 
            if d.delegatee == address and d.is_active
        )
        
        return member.voting_power + delegatee_power
    
    def _get_delegation(self, delegator: str) -> Optional[Delegate]:
        """Get delegation for a delegator"""
        return next((d for d in self.delegates.values() if d.delegator == delegator and d.is_active), None)
    
    def _get_vote(self, proposal_id: str, voter: str) -> Optional[Vote]:
        """Get vote for a proposal by a voter"""
        return next((v for v in self.votes.values() if v.proposal_id == proposal_id and v.voter == voter), None)
    
    async def _check_proposal_thresholds(self, proposal: Proposal) -> None:
        """Check if proposal has reached required thresholds"""
        total_voting_power = sum(member.voting_power for member in self.members.values() if member.is_active)
        
        # Check quorum
        quorum_votes = proposal.total_votes
        quorum_percentage = quorum_votes / total_voting_power if total_voting_power > 0 else 0
        proposal.quorum_reached = quorum_percentage >= self.quorum_threshold
        
        # Check support threshold
        if proposal.for_votes + proposal.against_votes > 0:
            support_percentage = proposal.for_votes / (proposal.for_votes + proposal.against_votes)
            proposal.support_threshold_reached = support_percentage >= self.support_threshold
        
        # Update proposal status
        if proposal.quorum_reached and proposal.support_threshold_reached:
            proposal.status = ProposalStatus.SUCCEEDED
        elif not proposal.quorum_reached or not proposal.support_threshold_reached:
            proposal.status = ProposalStatus.DEFEATED
    
    async def _execute_proposal_calls(self, proposal: Proposal) -> bool:
        """Execute proposal contract calls (simulated)"""
        try:
            # In a real implementation, this would execute actual contract calls
            # For now, we'll simulate the execution
            
            logger.info(f"Executing proposal calls for {proposal.proposal_id}")
            logger.info(f"Targets: {proposal.targets}")
            logger.info(f"Values: {proposal.values}")
            logger.info(f"Calldatas: {proposal.calldatas}")
            
            # Simulate execution delay
            await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute proposal calls: {e}")
            return False
    
    async def _process_proposals(self) -> None:
        """Background task to process proposals"""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                
                for proposal in self.proposals.values():
                    # Activate pending proposals
                    if proposal.status == ProposalStatus.PENDING:
                        proposal.status = ProposalStatus.ACTIVE
                    
                    # Check for expired proposals
                    if (proposal.status == ProposalStatus.ACTIVE and 
                        current_time > proposal.created_at + timedelta(days=self.voting_period_days)):
                        proposal.status = ProposalStatus.EXPIRED
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error processing proposals: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_expired_data(self) -> None:
        """Background task to cleanup expired data"""
        while True:
            try:
                # Cleanup old events (keep last 1000)
                if len(self.events) > 1000:
                    self.events = self.events[-1000:]
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                logger.error(f"Error cleaning up expired data: {e}")
                await asyncio.sleep(3600)
    
    async def _setup_database_indexes(self) -> None:
        """Setup database indexes for governance"""
        try:
            if not self.db:
                return
            
            # Proposals indexes
            await self.db.proposals.create_index("proposal_id", unique=True)
            await self.db.proposals.create_index("proposer")
            await self.db.proposals.create_index("status")
            await self.db.proposals.create_index("created_at")
            
            # Votes indexes
            await self.db.votes.create_index("vote_id", unique=True)
            await self.db.votes.create_index("proposal_id")
            await self.db.votes.create_index("voter")
            await self.db.votes.create_index("voted_at")
            
            # Delegates indexes
            await self.db.delegates.create_index("delegate_id", unique=True)
            await self.db.delegates.create_index("delegator")
            await self.db.delegates.create_index("delegatee")
            
            logger.info("Database indexes created for governance")
            
        except Exception as e:
            logger.error(f"Failed to setup database indexes: {e}")
    
    async def _load_governance_data(self) -> None:
        """Load governance data from database"""
        try:
            if not self.db:
                return
            
            # Load proposals
            proposals_cursor = self.db.proposals.find({})
            async for proposal_doc in proposals_cursor:
                proposal = Proposal(**proposal_doc)
                self.proposals[proposal.proposal_id] = proposal
            
            # Load votes
            votes_cursor = self.db.votes.find({})
            async for vote_doc in votes_cursor:
                vote = Vote(**vote_doc)
                self.votes[vote.vote_id] = vote
            
            # Load delegates
            delegates_cursor = self.db.delegates.find({})
            async for delegate_doc in delegates_cursor:
                delegate = Delegate(**delegate_doc)
                self.delegates[delegate.delegate_id] = delegate
            
            logger.info(f"Loaded governance data: {len(self.proposals)} proposals, {len(self.votes)} votes, {len(self.delegates)} delegations")
            
        except Exception as e:
            logger.error(f"Failed to load governance data: {e}")
    
    async def _save_governance_data(self) -> None:
        """Save governance data to database"""
        try:
            if not self.db:
                return
            
            # Save proposals
            for proposal in self.proposals.values():
                await self.db.proposals.replace_one(
                    {"proposal_id": proposal.proposal_id},
                    proposal.__dict__,
                    upsert=True
                )
            
            # Save votes
            for vote in self.votes.values():
                await self.db.votes.replace_one(
                    {"vote_id": vote.vote_id},
                    vote.__dict__,
                    upsert=True
                )
            
            # Save delegates
            for delegate in self.delegates.values():
                await self.db.delegates.replace_one(
                    {"delegate_id": delegate.delegate_id},
                    delegate.__dict__,
                    upsert=True
                )
            
            logger.info("Saved governance data to database")
            
        except Exception as e:
            logger.error(f"Failed to save governance data: {e}")


# Global governor instance
_governor: Optional[LucidGovernor] = None


def get_governor() -> Optional[LucidGovernor]:
    """Get the global governor instance"""
    return _governor


def create_governor(db: Optional[AsyncIOMotorDatabase] = None) -> LucidGovernor:
    """Create and configure governor"""
    global _governor
    _governor = LucidGovernor(db)
    return _governor


async def start_governor():
    """Start the governor service"""
    global _governor
    if _governor:
        await _governor.start()


async def stop_governor():
    """Stop the governor service"""
    global _governor
    if _governor:
        await _governor.stop()


# Example usage and testing
async def test_governor():
    """Test governor functionality"""
    try:
        # Create governor
        governor = create_governor()
        await governor.start()
        
        # Create a proposal
        proposal_id = await governor.create_proposal(
            title="Increase voting period",
            description="Proposal to increase voting period from 3 to 5 days",
            proposal_type=ProposalType.PARAMETER_CHANGE,
            proposer="0x0000000000000000000000000000000000000001",
            targets=["0x0000000000000000000000000000000000000000"],
            values=[0],
            calldatas=["0x12345678"]
        )
        
        print(f"Created proposal: {proposal_id}")
        
        # Cast votes
        await governor.cast_vote(proposal_id, "0x0000000000000000000000000000000000000001", VoteType.FOR, "Good proposal")
        await governor.cast_vote(proposal_id, "0x0000000000000000000000000000000000000002", VoteType.FOR, "Agree")
        await governor.cast_vote(proposal_id, "0x0000000000000000000000000000000000000003", VoteType.AGAINST, "Disagree")
        
        # Get proposal
        proposal = await governor.get_proposal(proposal_id)
        print(f"Proposal status: {proposal.status.value}")
        print(f"For votes: {proposal.for_votes}")
        print(f"Against votes: {proposal.against_votes}")
        
        # Get governance stats
        stats = await governor.get_governance_stats()
        print(f"Governance stats: {stats}")
        
        await governor.stop()
        print("Governor test completed successfully")
        
    except Exception as e:
        print(f"Governor test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_governor())
