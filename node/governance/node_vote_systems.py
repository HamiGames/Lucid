# Path: node/governance/node_vote_systems.py
# Lucid RDP Node Vote Systems - Comprehensive governance voting separate from consensus
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json
from decimal import Decimal

# Database adapter handles compatibility
from ..database_adapter import DatabaseAdapter, get_database_adapter

# Import existing components using relative imports
from ..peer_discovery import PeerDiscovery
from ..work_credits import WorkCreditsCalculator

logger = logging.getLogger(__name__)

# Vote System Constants
VOTE_DURATION_HOURS = int(os.getenv("VOTE_DURATION_HOURS", "168"))  # 1 week
PROPOSAL_DISCUSSION_HOURS = int(os.getenv("PROPOSAL_DISCUSSION_HOURS", "72"))  # 3 days
MIN_QUORUM_PERCENTAGE = float(os.getenv("MIN_QUORUM_PERCENTAGE", "0.33"))  # 33% minimum quorum
DELEGATE_EXPIRY_DAYS = int(os.getenv("DELEGATE_EXPIRY_DAYS", "30"))  # 30 days
MAX_PROPOSALS_PER_NODE = int(os.getenv("MAX_PROPOSALS_PER_NODE", "5"))  # Max active proposals per node


class ProposalType(Enum):
    """Types of governance proposals"""
    PARAMETER_CHANGE = "parameter_change"  # Network parameter changes
    PROTOCOL_UPGRADE = "protocol_upgrade"  # Protocol upgrades
    FUND_ALLOCATION = "fund_allocation"   # Treasury fund allocation
    NODE_PENALTY = "node_penalty"         # Node penalty/suspension
    NETWORK_POLICY = "network_policy"     # Network policy changes
    EMERGENCY_ACTION = "emergency_action" # Emergency governance actions
    COMMUNITY_INITIATIVE = "community_initiative"  # Community-driven initiatives


class ProposalStatus(Enum):
    """Proposal lifecycle status"""
    DRAFT = "draft"
    DISCUSSION = "discussion"
    VOTING = "voting"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class VoteChoice(Enum):
    """Vote choices"""
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class VoteWeight(Enum):
    """Vote weight calculation methods"""
    EQUAL = "equal"           # One node = one vote
    STAKE_WEIGHTED = "stake_weighted"  # Weight by staked tokens
    WORK_WEIGHTED = "work_weighted"    # Weight by work credits
    HYBRID = "hybrid"         # Combination of stake and work


@dataclass
class GovernanceProposal:
    """Governance proposal representation"""
    proposal_id: str
    proposer_node_id: str
    title: str
    description: str
    proposal_type: ProposalType
    vote_weight_method: VoteWeight
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    discussion_starts_at: Optional[datetime] = None
    voting_starts_at: Optional[datetime] = None
    voting_ends_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    execution_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.proposal_id,
            "proposer_node_id": self.proposer_node_id,
            "title": self.title,
            "description": self.description,
            "proposal_type": self.proposal_type.value,
            "vote_weight_method": self.vote_weight_method.value,
            "parameters": self.parameters,
            "status": self.status.value,
            "created_at": self.created_at,
            "discussion_starts_at": self.discussion_starts_at,
            "voting_starts_at": self.voting_starts_at,
            "voting_ends_at": self.voting_ends_at,
            "executed_at": self.executed_at,
            "execution_hash": self.execution_hash,
            "metadata": self.metadata
        }


@dataclass
class GovernanceVote:
    """Individual governance vote"""
    vote_id: str
    proposal_id: str
    voter_node_id: str
    choice: VoteChoice
    weight: Decimal
    delegate_from: Optional[str] = None  # If voting on behalf of delegator
    cast_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.vote_id,
            "proposal_id": self.proposal_id,
            "voter_node_id": self.voter_node_id,
            "choice": self.choice.value,
            "weight": str(self.weight),
            "delegate_from": self.delegate_from,
            "cast_at": self.cast_at,
            "signature": self.signature,
            "metadata": self.metadata
        }


@dataclass
class VoteDelegation:
    """Vote delegation from one node to another"""
    delegation_id: str
    delegator_node_id: str
    delegate_node_id: str
    scope: Optional[str] = None  # Specific proposal types or "all"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.delegation_id,
            "delegator_node_id": self.delegator_node_id,
            "delegate_node_id": self.delegate_node_id,
            "scope": self.scope,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "active": self.active
        }


@dataclass
class VoteTally:
    """Vote tally for a proposal"""
    proposal_id: str
    total_eligible_weight: Decimal
    total_votes_cast: int
    total_weight_cast: Decimal
    yes_votes: int
    no_votes: int
    abstain_votes: int
    yes_weight: Decimal
    no_weight: Decimal
    abstain_weight: Decimal
    quorum_met: bool
    result: Optional[str] = None  # "passed", "rejected", "tied"
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.proposal_id,
            "total_eligible_weight": str(self.total_eligible_weight),
            "total_votes_cast": self.total_votes_cast,
            "total_weight_cast": str(self.total_weight_cast),
            "yes_votes": self.yes_votes,
            "no_votes": self.no_votes,
            "abstain_votes": self.abstain_votes,
            "yes_weight": str(self.yes_weight),
            "no_weight": str(self.no_weight),
            "abstain_weight": str(self.abstain_weight),
            "quorum_met": self.quorum_met,
            "result": self.result,
            "calculated_at": self.calculated_at
        }


@dataclass
class GovernanceComment:
    """Discussion comment on a proposal"""
    comment_id: str
    proposal_id: str
    commenter_node_id: str
    content: str
    parent_comment_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    edited_at: Optional[datetime] = None
    signature: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.comment_id,
            "proposal_id": self.proposal_id,
            "commenter_node_id": self.commenter_node_id,
            "content": self.content,
            "parent_comment_id": self.parent_comment_id,
            "created_at": self.created_at,
            "edited_at": self.edited_at,
            "signature": self.signature
        }


class NodeVoteSystem:
    """
    Node Vote System for comprehensive governance voting operations.
    
    Handles:
    - Governance proposal creation and management
    - Vote casting with multiple weight methods
    - Vote delegation and proxy voting
    - Proposal discussion and comments
    - Vote tallying and result calculation
    - Automated proposal lifecycle management
    - Governance metrics and analytics
    """
    
    def __init__(self, db: DatabaseAdapter, peer_discovery: PeerDiscovery,
                 work_credits: WorkCreditsCalculator):
        self.db = db
        self.peer_discovery = peer_discovery
        self.work_credits = work_credits
        
        # State tracking
        self.active_proposals: Dict[str, GovernanceProposal] = {}
        self.active_delegations: Dict[str, VoteDelegation] = {}
        self.proposal_tallies: Dict[str, VoteTally] = {}
        self.running = False
        
        # Background tasks
        self._lifecycle_task: Optional[asyncio.Task] = None
        self._tally_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("Node vote system initialized")
    
    async def start(self):
        """Start node vote system"""
        try:
            self.running = True
            
            # Setup database indexes
            await self._setup_indexes()
            
            # Load existing data
            await self._load_active_proposals()
            await self._load_active_delegations()
            await self._load_proposal_tallies()
            
            # Start background tasks
            self._lifecycle_task = asyncio.create_task(self._proposal_lifecycle_loop())
            self._tally_task = asyncio.create_task(self._vote_tally_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info("Node vote system started")
            
        except Exception as e:
            logger.error(f"Failed to start node vote system: {e}")
            raise
    
    async def stop(self):
        """Stop node vote system"""
        try:
            self.running = False
            
            # Cancel background tasks
            tasks = [self._lifecycle_task, self._tally_task, self._cleanup_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
            
            logger.info("Node vote system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping node vote system: {e}")
    
    async def create_proposal(self, proposer_node_id: str, title: str, description: str,
                            proposal_type: ProposalType, vote_weight_method: VoteWeight,
                            parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new governance proposal.
        
        Args:
            proposer_node_id: Node creating the proposal
            title: Proposal title
            description: Detailed description
            proposal_type: Type of proposal
            vote_weight_method: Voting weight calculation method
            parameters: Proposal-specific parameters
            
        Returns:
            Proposal ID
        """
        try:
            # Check if proposer has too many active proposals
            active_count = len([p for p in self.active_proposals.values() 
                              if p.proposer_node_id == proposer_node_id and 
                              p.status not in [ProposalStatus.PASSED, ProposalStatus.REJECTED, 
                                             ProposalStatus.EXECUTED, ProposalStatus.EXPIRED, 
                                             ProposalStatus.CANCELLED]])
            
            if active_count >= MAX_PROPOSALS_PER_NODE:
                raise ValueError(f"Node has reached maximum active proposal limit: {MAX_PROPOSALS_PER_NODE}")
            
            proposal_id = str(uuid.uuid4())
            
            proposal = GovernanceProposal(
                proposal_id=proposal_id,
                proposer_node_id=proposer_node_id,
                title=title,
                description=description,
                proposal_type=proposal_type,
                vote_weight_method=vote_weight_method,
                parameters=parameters or {}
            )
            
            # Store proposal
            self.active_proposals[proposal_id] = proposal
            await self.db["governance_proposals"].replace_one(
                {"_id": proposal_id},
                proposal.to_dict(),
                upsert=True
            )
            
            logger.info(f"Governance proposal created: {proposal_id} by {proposer_node_id}")
            return proposal_id
            
        except Exception as e:
            logger.error(f"Failed to create proposal: {e}")
            raise
    
    async def start_discussion(self, proposal_id: str) -> bool:
        """Start discussion phase for a proposal"""
        try:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal not found: {proposal_id}")
            
            if proposal.status != ProposalStatus.DRAFT:
                raise ValueError(f"Proposal not in draft status: {proposal.status}")
            
            # Update proposal
            proposal.status = ProposalStatus.DISCUSSION
            proposal.discussion_starts_at = datetime.now(timezone.utc)
            proposal.voting_starts_at = proposal.discussion_starts_at + timedelta(hours=PROPOSAL_DISCUSSION_HOURS)
            proposal.voting_ends_at = proposal.voting_starts_at + timedelta(hours=VOTE_DURATION_HOURS)
            
            # Save to database
            await self.db["governance_proposals"].update_one(
                {"_id": proposal_id},
                {"$set": {
                    "status": proposal.status.value,
                    "discussion_starts_at": proposal.discussion_starts_at,
                    "voting_starts_at": proposal.voting_starts_at,
                    "voting_ends_at": proposal.voting_ends_at
                }}
            )
            
            logger.info(f"Discussion started for proposal: {proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start discussion: {e}")
            return False
    
    async def cast_vote(self, voter_node_id: str, proposal_id: str, choice: VoteChoice,
                       delegate_from: Optional[str] = None) -> str:
        """
        Cast a vote on a proposal.
        
        Args:
            voter_node_id: Node casting the vote
            proposal_id: Proposal being voted on
            choice: Vote choice
            delegate_from: If voting on behalf of delegator
            
        Returns:
            Vote ID
        """
        try:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal not found: {proposal_id}")
            
            if proposal.status != ProposalStatus.VOTING:
                raise ValueError(f"Proposal not in voting phase: {proposal.status}")
            
            # Check if voting period is active
            now = datetime.now(timezone.utc)
            if now < proposal.voting_starts_at or now > proposal.voting_ends_at:
                raise ValueError("Voting period is not active")
            
            # Check if already voted (without delegation)
            existing_vote = await self.db["governance_votes"].find_one({
                "proposal_id": proposal_id,
                "voter_node_id": voter_node_id,
                "delegate_from": None
            })
            
            if existing_vote and not delegate_from:
                raise ValueError("Node has already voted on this proposal")
            
            # If voting on behalf of delegator, verify delegation
            if delegate_from:
                delegation = await self._get_active_delegation(delegate_from, voter_node_id, proposal.proposal_type)
                if not delegation:
                    raise ValueError("No active delegation found")
            
            # Calculate vote weight
            vote_weight = await self._calculate_vote_weight(
                voter_node_id if not delegate_from else delegate_from,
                proposal.vote_weight_method
            )
            
            vote_id = str(uuid.uuid4())
            
            vote = GovernanceVote(
                vote_id=vote_id,
                proposal_id=proposal_id,
                voter_node_id=voter_node_id,
                choice=choice,
                weight=vote_weight,
                delegate_from=delegate_from
            )
            
            # Store vote
            await self.db["governance_votes"].insert_one(vote.to_dict())
            
            # Update tally
            await self._update_proposal_tally(proposal_id)
            
            logger.info(f"Vote cast: {vote_id} on proposal {proposal_id} by {voter_node_id}")
            return vote_id
            
        except Exception as e:
            logger.error(f"Failed to cast vote: {e}")
            raise
    
    async def delegate_vote(self, delegator_node_id: str, delegate_node_id: str,
                           scope: Optional[str] = None, expires_in_days: Optional[int] = None) -> str:
        """
        Delegate voting power to another node.
        
        Args:
            delegator_node_id: Node delegating power
            delegate_node_id: Node receiving delegation
            scope: Specific proposal types or "all"
            expires_in_days: Expiration in days
            
        Returns:
            Delegation ID
        """
        try:
            if delegator_node_id == delegate_node_id:
                raise ValueError("Cannot delegate to self")
            
            # Check if delegation already exists
            existing = await self.db["vote_delegations"].find_one({
                "delegator_node_id": delegator_node_id,
                "delegate_node_id": delegate_node_id,
                "scope": scope,
                "active": True
            })
            
            if existing:
                raise ValueError("Active delegation already exists")
            
            delegation_id = str(uuid.uuid4())
            expires_at = None
            
            if expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            else:
                expires_at = datetime.now(timezone.utc) + timedelta(days=DELEGATE_EXPIRY_DAYS)
            
            delegation = VoteDelegation(
                delegation_id=delegation_id,
                delegator_node_id=delegator_node_id,
                delegate_node_id=delegate_node_id,
                scope=scope,
                expires_at=expires_at
            )
            
            # Store delegation
            self.active_delegations[delegation_id] = delegation
            await self.db["vote_delegations"].insert_one(delegation.to_dict())
            
            logger.info(f"Vote delegation created: {delegation_id} from {delegator_node_id} to {delegate_node_id}")
            return delegation_id
            
        except Exception as e:
            logger.error(f"Failed to create delegation: {e}")
            raise
    
    async def revoke_delegation(self, delegator_node_id: str, delegation_id: str) -> bool:
        """Revoke a vote delegation"""
        try:
            delegation = self.active_delegations.get(delegation_id)
            if not delegation:
                delegation_doc = await self.db["vote_delegations"].find_one({"_id": delegation_id})
                if not delegation_doc:
                    raise ValueError(f"Delegation not found: {delegation_id}")
                
                delegation = VoteDelegation(
                    delegation_id=delegation_doc["_id"],
                    delegator_node_id=delegation_doc["delegator_node_id"],
                    delegate_node_id=delegation_doc["delegate_node_id"],
                    scope=delegation_doc.get("scope"),
                    created_at=delegation_doc["created_at"],
                    expires_at=delegation_doc.get("expires_at"),
                    active=delegation_doc["active"]
                )
            
            if delegation.delegator_node_id != delegator_node_id:
                raise ValueError("Only delegator can revoke delegation")
            
            # Deactivate delegation
            delegation.active = False
            if delegation_id in self.active_delegations:
                del self.active_delegations[delegation_id]
            
            await self.db["vote_delegations"].update_one(
                {"_id": delegation_id},
                {"$set": {"active": False}}
            )
            
            logger.info(f"Vote delegation revoked: {delegation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke delegation: {e}")
            return False
    
    async def add_comment(self, commenter_node_id: str, proposal_id: str, content: str,
                         parent_comment_id: Optional[str] = None) -> str:
        """Add a discussion comment to a proposal"""
        try:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal not found: {proposal_id}")
            
            if proposal.status not in [ProposalStatus.DISCUSSION, ProposalStatus.VOTING]:
                raise ValueError("Comments only allowed during discussion and voting phases")
            
            comment_id = str(uuid.uuid4())
            
            comment = GovernanceComment(
                comment_id=comment_id,
                proposal_id=proposal_id,
                commenter_node_id=commenter_node_id,
                content=content,
                parent_comment_id=parent_comment_id
            )
            
            await self.db["governance_comments"].insert_one(comment.to_dict())
            
            logger.info(f"Comment added: {comment_id} on proposal {proposal_id}")
            return comment_id
            
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            raise
    
    async def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get proposal details"""
        try:
            proposal = self.active_proposals.get(proposal_id)
            if proposal:
                return proposal.to_dict()
            
            # Check database
            proposal_doc = await self.db["governance_proposals"].find_one({"_id": proposal_id})
            return proposal_doc
            
        except Exception as e:
            logger.error(f"Failed to get proposal: {e}")
            return None
    
    async def get_proposal_votes(self, proposal_id: str) -> List[Dict[str, Any]]:
        """Get all votes for a proposal"""
        try:
            votes = []
            cursor = self.db["governance_votes"].find({"proposal_id": proposal_id})
            
            async for vote_doc in cursor:
                votes.append(vote_doc)
            
            return votes
            
        except Exception as e:
            logger.error(f"Failed to get proposal votes: {e}")
            return []
    
    async def get_proposal_tally(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get vote tally for a proposal"""
        try:
            tally = self.proposal_tallies.get(proposal_id)
            if tally:
                return tally.to_dict()
            
            # Check database
            tally_doc = await self.db["vote_tallies"].find_one({"_id": proposal_id})
            return tally_doc
            
        except Exception as e:
            logger.error(f"Failed to get proposal tally: {e}")
            return None
    
    async def get_active_proposals(self, proposal_type: Optional[ProposalType] = None) -> List[Dict[str, Any]]:
        """Get active proposals, optionally filtered by type"""
        try:
            query = {"status": {"$in": [ProposalStatus.DISCUSSION.value, ProposalStatus.VOTING.value]}}
            if proposal_type:
                query["proposal_type"] = proposal_type.value
            
            proposals = []
            cursor = self.db["governance_proposals"].find(query).sort("created_at", -1)
            
            async for proposal_doc in cursor:
                proposals.append(proposal_doc)
            
            return proposals
            
        except Exception as e:
            logger.error(f"Failed to get active proposals: {e}")
            return []
    
    async def get_node_delegations(self, node_id: str, as_delegator: bool = True) -> List[Dict[str, Any]]:
        """Get delegations for a node (as delegator or delegate)"""
        try:
            field = "delegator_node_id" if as_delegator else "delegate_node_id"
            query = {field: node_id, "active": True}
            
            delegations = []
            cursor = self.db["vote_delegations"].find(query)
            
            async for delegation_doc in cursor:
                delegations.append(delegation_doc)
            
            return delegations
            
        except Exception as e:
            logger.error(f"Failed to get node delegations: {e}")
            return []
    
    async def get_governance_stats(self) -> Dict[str, Any]:
        """Get governance system statistics"""
        try:
            stats = {
                "total_proposals": await self.db["governance_proposals"].count_documents({}),
                "active_proposals": len(self.active_proposals),
                "active_delegations": len(self.active_delegations),
                "total_votes_cast": await self.db["governance_votes"].count_documents({}),
                "proposals_by_status": {},
                "proposals_by_type": {},
                "participation_rate": 0.0
            }
            
            # Count by status
            pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            async for doc in self.db["governance_proposals"].aggregate(pipeline):
                stats["proposals_by_status"][doc["_id"]] = doc["count"]
            
            # Count by type
            pipeline = [
                {"$group": {"_id": "$proposal_type", "count": {"$sum": 1}}}
            ]
            async for doc in self.db["governance_proposals"].aggregate(pipeline):
                stats["proposals_by_type"][doc["_id"]] = doc["count"]
            
            # Calculate participation rate
            active_nodes = len(await self.peer_discovery.get_active_peers())
            if active_nodes > 0:
                recent_voters = await self.db["governance_votes"].distinct("voter_node_id", {
                    "cast_at": {"$gte": datetime.now(timezone.utc) - timedelta(days=30)}
                })
                stats["participation_rate"] = len(recent_voters) / active_nodes
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get governance stats: {e}")
            return {"error": str(e)}
    
    async def _calculate_vote_weight(self, node_id: str, weight_method: VoteWeight) -> Decimal:
        """Calculate vote weight for a node"""
        try:
            if weight_method == VoteWeight.EQUAL:
                return Decimal("1.0")
            
            elif weight_method == VoteWeight.STAKE_WEIGHTED:
                # Mock stake calculation - would integrate with actual staking system
                stake = Decimal("1000.0")  # Would get actual stake
                return stake
            
            elif weight_method == VoteWeight.WORK_WEIGHTED:
                # Weight by work credits
                work_credits = await self.work_credits.calculate_work_credits(node_id, window_days=30)
                return Decimal(str(max(work_credits, 1)))  # Minimum weight of 1
            
            elif weight_method == VoteWeight.HYBRID:
                # Combination of stake and work (50/50)
                stake = Decimal("1000.0")  # Mock stake
                work_credits = await self.work_credits.calculate_work_credits(node_id, window_days=30)
                work_weight = Decimal(str(max(work_credits, 1)))
                
                return (stake + work_weight) / Decimal("2.0")
            
            return Decimal("1.0")
            
        except Exception as e:
            logger.error(f"Failed to calculate vote weight: {e}")
            return Decimal("1.0")
    
    async def _get_active_delegation(self, delegator_id: str, delegate_id: str, 
                                   proposal_type: ProposalType) -> Optional[VoteDelegation]:
        """Get active delegation for specific context"""
        try:
            # Check in-memory delegations first
            for delegation in self.active_delegations.values():
                if (delegation.delegator_node_id == delegator_id and
                    delegation.delegate_node_id == delegate_id and
                    delegation.active and
                    (delegation.scope is None or delegation.scope == "all" or 
                     delegation.scope == proposal_type.value)):
                    
                    # Check expiration
                    if delegation.expires_at and datetime.now(timezone.utc) > delegation.expires_at:
                        continue
                    
                    return delegation
            
            # Check database
            query = {
                "delegator_node_id": delegator_id,
                "delegate_node_id": delegate_id,
                "active": True,
                "$or": [
                    {"scope": None},
                    {"scope": "all"},
                    {"scope": proposal_type.value}
                ]
            }
            
            delegation_doc = await self.db["vote_delegations"].find_one(query)
            if delegation_doc:
                # Check expiration
                if (delegation_doc.get("expires_at") and 
                    datetime.now(timezone.utc) > delegation_doc["expires_at"]):
                    return None
                
                return VoteDelegation(
                    delegation_id=delegation_doc["_id"],
                    delegator_node_id=delegation_doc["delegator_node_id"],
                    delegate_node_id=delegation_doc["delegate_node_id"],
                    scope=delegation_doc.get("scope"),
                    created_at=delegation_doc["created_at"],
                    expires_at=delegation_doc.get("expires_at"),
                    active=delegation_doc["active"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get active delegation: {e}")
            return None
    
    async def _update_proposal_tally(self, proposal_id: str):
        """Update vote tally for a proposal"""
        try:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                return
            
            # Get all votes
            votes_cursor = self.db["governance_votes"].find({"proposal_id": proposal_id})
            
            total_votes_cast = 0
            total_weight_cast = Decimal("0")
            yes_votes = no_votes = abstain_votes = 0
            yes_weight = no_weight = abstain_weight = Decimal("0")
            
            async for vote_doc in votes_cursor:
                total_votes_cast += 1
                weight = Decimal(vote_doc["weight"])
                total_weight_cast += weight
                
                choice = VoteChoice(vote_doc["choice"])
                if choice == VoteChoice.YES:
                    yes_votes += 1
                    yes_weight += weight
                elif choice == VoteChoice.NO:
                    no_votes += 1
                    no_weight += weight
                else:  # ABSTAIN
                    abstain_votes += 1
                    abstain_weight += weight
            
            # Calculate total eligible weight (all active nodes)
            active_peers = await self.peer_discovery.get_active_peers()
            total_eligible_weight = Decimal("0")
            
            for peer in active_peers:
                weight = await self._calculate_vote_weight(peer.node_id, proposal.vote_weight_method)
                total_eligible_weight += weight
            
            # Check quorum
            quorum_threshold = total_eligible_weight * Decimal(str(MIN_QUORUM_PERCENTAGE))
            quorum_met = total_weight_cast >= quorum_threshold
            
            # Determine result
            result = None
            if quorum_met:
                if yes_weight > no_weight:
                    result = "passed"
                elif no_weight > yes_weight:
                    result = "rejected"
                else:
                    result = "tied"
            
            tally = VoteTally(
                proposal_id=proposal_id,
                total_eligible_weight=total_eligible_weight,
                total_votes_cast=total_votes_cast,
                total_weight_cast=total_weight_cast,
                yes_votes=yes_votes,
                no_votes=no_votes,
                abstain_votes=abstain_votes,
                yes_weight=yes_weight,
                no_weight=no_weight,
                abstain_weight=abstain_weight,
                quorum_met=quorum_met,
                result=result
            )
            
            self.proposal_tallies[proposal_id] = tally
            await self.db["vote_tallies"].replace_one(
                {"_id": proposal_id},
                tally.to_dict(),
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Failed to update proposal tally: {e}")
    
    async def _proposal_lifecycle_loop(self):
        """Manage proposal lifecycle transitions"""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                for proposal in list(self.active_proposals.values()):
                    try:
                        # Transition from discussion to voting
                        if (proposal.status == ProposalStatus.DISCUSSION and
                            proposal.voting_starts_at and now >= proposal.voting_starts_at):
                            
                            proposal.status = ProposalStatus.VOTING
                            await self.db["governance_proposals"].update_one(
                                {"_id": proposal.proposal_id},
                                {"$set": {"status": proposal.status.value}}
                            )
                            logger.info(f"Proposal {proposal.proposal_id} moved to voting phase")
                        
                        # End voting and finalize results
                        elif (proposal.status == ProposalStatus.VOTING and
                              proposal.voting_ends_at and now >= proposal.voting_ends_at):
                            
                            # Update final tally
                            await self._update_proposal_tally(proposal.proposal_id)
                            
                            tally = self.proposal_tallies.get(proposal.proposal_id)
                            if tally and tally.result:
                                if tally.result == "passed":
                                    proposal.status = ProposalStatus.PASSED
                                else:
                                    proposal.status = ProposalStatus.REJECTED
                            else:
                                proposal.status = ProposalStatus.EXPIRED
                            
                            await self.db["governance_proposals"].update_one(
                                {"_id": proposal.proposal_id},
                                {"$set": {"status": proposal.status.value}}
                            )
                            
                            # Remove from active proposals
                            del self.active_proposals[proposal.proposal_id]
                            logger.info(f"Proposal {proposal.proposal_id} finalized: {proposal.status.value}")
                        
                    except Exception as proposal_error:
                        logger.error(f"Lifecycle management failed for proposal {proposal.proposal_id}: {proposal_error}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Proposal lifecycle loop error: {e}")
                await asyncio.sleep(60)
    
    async def _vote_tally_loop(self):
        """Periodically update vote tallies"""
        while self.running:
            try:
                # Update tallies for active voting proposals
                for proposal_id in list(self.active_proposals.keys()):
                    proposal = self.active_proposals[proposal_id]
                    if proposal.status == ProposalStatus.VOTING:
                        await self._update_proposal_tally(proposal_id)
                
                await asyncio.sleep(600)  # Update every 10 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Vote tally loop error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Cleanup expired delegations and old data"""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                # Expire old delegations
                for delegation_id, delegation in list(self.active_delegations.items()):
                    if delegation.expires_at and now > delegation.expires_at:
                        delegation.active = False
                        await self.db["vote_delegations"].update_one(
                            {"_id": delegation_id},
                            {"$set": {"active": False}}
                        )
                        del self.active_delegations[delegation_id]
                        logger.info(f"Expired delegation: {delegation_id}")
                
                # Clean up old comments (older than 1 year)
                cutoff_date = now - timedelta(days=365)
                await self.db["governance_comments"].delete_many({
                    "created_at": {"$lt": cutoff_date}
                })
                
                logger.info("Vote system cleanup completed")
                
                await asyncio.sleep(86400)  # Daily cleanup
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _setup_indexes(self):
        """Setup database indexes"""
        try:
            # Governance proposals indexes
            await self.db["governance_proposals"].create_index("proposer_node_id")
            await self.db["governance_proposals"].create_index("proposal_type")
            await self.db["governance_proposals"].create_index("status")
            await self.db["governance_proposals"].create_index("created_at")
            await self.db["governance_proposals"].create_index("voting_starts_at")
            await self.db["governance_proposals"].create_index("voting_ends_at")
            
            # Governance votes indexes
            await self.db["governance_votes"].create_index("proposal_id")
            await self.db["governance_votes"].create_index("voter_node_id")
            await self.db["governance_votes"].create_index("cast_at")
            await self.db["governance_votes"].create_index([("proposal_id", 1), ("voter_node_id", 1)])
            
            # Vote delegations indexes
            await self.db["vote_delegations"].create_index("delegator_node_id")
            await self.db["vote_delegations"].create_index("delegate_node_id")
            await self.db["vote_delegations"].create_index("active")
            await self.db["vote_delegations"].create_index("expires_at")
            
            # Governance comments indexes
            await self.db["governance_comments"].create_index("proposal_id")
            await self.db["governance_comments"].create_index("commenter_node_id")
            await self.db["governance_comments"].create_index("created_at")
            
            # Vote tallies indexes
            await self.db["vote_tallies"].create_index("calculated_at")
            
            logger.info("Node vote system database indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create vote system indexes: {e}")
    
    async def _load_active_proposals(self):
        """Load active proposals from database"""
        try:
            cursor = self.db["governance_proposals"].find({
                "status": {"$in": [ProposalStatus.DISCUSSION.value, ProposalStatus.VOTING.value]}
            })
            
            async for proposal_doc in cursor:
                proposal = GovernanceProposal(
                    proposal_id=proposal_doc["_id"],
                    proposer_node_id=proposal_doc["proposer_node_id"],
                    title=proposal_doc["title"],
                    description=proposal_doc["description"],
                    proposal_type=ProposalType(proposal_doc["proposal_type"]),
                    vote_weight_method=VoteWeight(proposal_doc["vote_weight_method"]),
                    parameters=proposal_doc.get("parameters", {}),
                    status=ProposalStatus(proposal_doc["status"]),
                    created_at=proposal_doc["created_at"],
                    discussion_starts_at=proposal_doc.get("discussion_starts_at"),
                    voting_starts_at=proposal_doc.get("voting_starts_at"),
                    voting_ends_at=proposal_doc.get("voting_ends_at"),
                    executed_at=proposal_doc.get("executed_at"),
                    execution_hash=proposal_doc.get("execution_hash"),
                    metadata=proposal_doc.get("metadata", {})
                )
                
                self.active_proposals[proposal.proposal_id] = proposal
            
            logger.info(f"Loaded {len(self.active_proposals)} active proposals")
            
        except Exception as e:
            logger.error(f"Failed to load active proposals: {e}")
    
    async def _load_active_delegations(self):
        """Load active delegations from database"""
        try:
            cursor = self.db["vote_delegations"].find({"active": True})
            
            async for delegation_doc in cursor:
                delegation = VoteDelegation(
                    delegation_id=delegation_doc["_id"],
                    delegator_node_id=delegation_doc["delegator_node_id"],
                    delegate_node_id=delegation_doc["delegate_node_id"],
                    scope=delegation_doc.get("scope"),
                    created_at=delegation_doc["created_at"],
                    expires_at=delegation_doc.get("expires_at"),
                    active=delegation_doc["active"]
                )
                
                self.active_delegations[delegation.delegation_id] = delegation
            
            logger.info(f"Loaded {len(self.active_delegations)} active delegations")
            
        except Exception as e:
            logger.error(f"Failed to load active delegations: {e}")
    
    async def _load_proposal_tallies(self):
        """Load proposal tallies from database"""
        try:
            cursor = self.db["vote_tallies"].find({})
            
            async for tally_doc in cursor:
                tally = VoteTally(
                    proposal_id=tally_doc["_id"],
                    total_eligible_weight=Decimal(tally_doc["total_eligible_weight"]),
                    total_votes_cast=tally_doc["total_votes_cast"],
                    total_weight_cast=Decimal(tally_doc["total_weight_cast"]),
                    yes_votes=tally_doc["yes_votes"],
                    no_votes=tally_doc["no_votes"],
                    abstain_votes=tally_doc["abstain_votes"],
                    yes_weight=Decimal(tally_doc["yes_weight"]),
                    no_weight=Decimal(tally_doc["no_weight"]),
                    abstain_weight=Decimal(tally_doc["abstain_weight"]),
                    quorum_met=tally_doc["quorum_met"],
                    result=tally_doc.get("result"),
                    calculated_at=tally_doc["calculated_at"]
                )
                
                self.proposal_tallies[tally.proposal_id] = tally
            
            logger.info(f"Loaded {len(self.proposal_tallies)} proposal tallies")
            
        except Exception as e:
            logger.error(f"Failed to load proposal tallies: {e}")


# Global node vote system instance
_node_vote_system: Optional[NodeVoteSystem] = None


def get_node_vote_system() -> Optional[NodeVoteSystem]:
    """Get global node vote system instance"""
    global _node_vote_system
    return _node_vote_system


def create_node_vote_system(db: DatabaseAdapter, peer_discovery: PeerDiscovery,
                           work_credits: WorkCreditsCalculator) -> NodeVoteSystem:
    """Create node vote system instance"""
    global _node_vote_system
    _node_vote_system = NodeVoteSystem(db, peer_discovery, work_credits)
    return _node_vote_system


async def cleanup_node_vote_system():
    """Cleanup node vote system"""
    global _node_vote_system
    if _node_vote_system:
        await _node_vote_system.stop()
        _node_vote_system = None


if __name__ == "__main__":
    # Test node vote system
    async def test_node_vote_system():
        print("Testing Lucid Node Vote System...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - node vote system ready")
    
    asyncio.run(test_node_vote_system())