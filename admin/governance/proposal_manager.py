# Path: admin/governance/proposal_manager.py
# Lucid Governance - Proposal Management System
# Handles governance proposals, voting, and decision making
# LUCID-STRICT Layer 1 Core Infrastructure

from __future__ import annotations

import asyncio
import logging
import os
import json
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import aiofiles
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Configuration from environment
PROPOSAL_STORAGE_PATH = Path(os.getenv("PROPOSAL_STORAGE_PATH", "/data/governance/proposals"))
VOTING_PERIOD_HOURS = int(os.getenv("VOTING_PERIOD_HOURS", "168"))  # 7 days
MINIMUM_QUORUM_PERCENT = float(os.getenv("MINIMUM_QUORUM_PERCENT", "51.0"))
MINIMUM_APPROVAL_PERCENT = float(os.getenv("MINIMUM_APPROVAL_PERCENT", "66.7"))
PROPOSAL_FEE_AMOUNT = float(os.getenv("PROPOSAL_FEE_AMOUNT", "100.0"))


class ProposalType(Enum):
    """Types of governance proposals"""
    SYSTEM_UPGRADE = "system_upgrade"
    PARAMETER_CHANGE = "parameter_change"
    TREASURY_ALLOCATION = "treasury_allocation"
    VALIDATOR_CHANGE = "validator_change"
    EMERGENCY_ACTION = "emergency_action"
    POLICY_UPDATE = "policy_update"
    FEATURE_REQUEST = "feature_request"


class ProposalStatus(Enum):
    """Proposal status states"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACTIVE = "active"
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


class VoterType(Enum):
    """Types of voters"""
    VALIDATOR = "validator"
    DELEGATOR = "delegator"
    STAKEHOLDER = "stakeholder"
    SYSTEM_ADMIN = "system_admin"


@dataclass
class ProposalContent:
    """Content of a governance proposal"""
    title: str
    description: str
    proposal_type: ProposalType
    parameters: Dict[str, Any] = field(default_factory=dict)
    implementation_plan: str = ""
    expected_impact: str = ""
    risk_assessment: str = ""
    references: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)


@dataclass
class Vote:
    """Individual vote on a proposal"""
    voter_id: str
    voter_type: VoterType
    choice: VoteChoice
    voting_power: float
    timestamp: datetime
    signature: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposal:
    """Governance proposal"""
    proposal_id: str
    proposer_id: str
    content: ProposalContent
    status: ProposalStatus
    created_at: datetime
    submitted_at: Optional[datetime] = None
    voting_start: Optional[datetime] = None
    voting_end: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    votes: List[Vote] = field(default_factory=list)
    total_voting_power: float = 0.0
    yes_votes: float = 0.0
    no_votes: float = 0.0
    abstain_votes: float = 0.0
    quorum_met: bool = False
    passed: bool = False
    execution_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VotingResult:
    """Result of proposal voting"""
    proposal_id: str
    total_votes: int
    total_voting_power: float
    yes_power: float
    no_power: float
    abstain_power: float
    quorum_percentage: float
    approval_percentage: float
    quorum_met: bool
    passed: bool
    executed: bool


class ProposalManager:
    """Governance proposal management system"""
    
    def __init__(self):
        self.storage_path = PROPOSAL_STORAGE_PATH
        self.voting_period = timedelta(hours=VOTING_PERIOD_HOURS)
        self.min_quorum = MINIMUM_QUORUM_PERCENT
        self.min_approval = MINIMUM_APPROVAL_PERCENT
        self.proposal_fee = PROPOSAL_FEE_AMOUNT
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize proposal storage"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True, mode=0o755)
            logger.info(f"Proposal storage initialized at {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to initialize proposal storage: {e}")
            raise
    
    def _generate_proposal_id(self, proposer_id: str, content: ProposalContent) -> str:
        """Generate a unique proposal ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.sha256(
            f"{content.title}{content.description}{content.proposal_type.value}".encode()
        ).hexdigest()[:8]
        random_suffix = secrets.token_hex(4)
        return f"prop_{timestamp}_{content_hash}_{random_suffix}"
    
    async def create_proposal(self, proposer_id: str, content: ProposalContent) -> str:
        """Create a new governance proposal"""
        try:
            proposal_id = self._generate_proposal_id(proposer_id, content)
            
            proposal = Proposal(
                proposal_id=proposal_id,
                proposer_id=proposer_id,
                content=content,
                status=ProposalStatus.DRAFT,
                created_at=datetime.now(timezone.utc)
            )
            
            await self._save_proposal(proposal)
            
            logger.info(f"Created proposal {proposal_id} by {proposer_id}")
            return proposal_id
            
        except Exception as e:
            logger.error(f"Failed to create proposal: {e}")
            raise
    
    async def submit_proposal(self, proposal_id: str, proposer_signature: str) -> bool:
        """Submit a proposal for voting"""
        try:
            proposal = await self._load_proposal(proposal_id)
            
            if proposal.status != ProposalStatus.DRAFT:
                raise ValueError(f"Proposal {proposal_id} is not in draft status")
            
            # Verify proposer signature
            if not await self._verify_proposer_signature(proposal, proposer_signature):
                raise ValueError("Invalid proposer signature")
            
            # Check if proposer has sufficient stake/fee
            if not await self._check_proposer_eligibility(proposal.proposer_id):
                raise ValueError("Proposer not eligible to submit proposals")
            
            # Update proposal status
            proposal.status = ProposalStatus.SUBMITTED
            proposal.submitted_at = datetime.now(timezone.utc)
            proposal.voting_start = datetime.now(timezone.utc)
            proposal.voting_end = proposal.voting_start + self.voting_period
            
            await self._save_proposal(proposal)
            
            # Notify validators and stakeholders
            await self._notify_proposal_submitted(proposal)
            
            logger.info(f"Submitted proposal {proposal_id} for voting")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit proposal {proposal_id}: {e}")
            return False
    
    async def cast_vote(self, proposal_id: str, voter_id: str, choice: VoteChoice, 
                       voting_power: float, signature: str) -> bool:
        """Cast a vote on a proposal"""
        try:
            proposal = await self._load_proposal(proposal_id)
            
            if proposal.status != ProposalStatus.ACTIVE:
                raise ValueError(f"Proposal {proposal_id} is not active for voting")
            
            if datetime.now(timezone.utc) > proposal.voting_end:
                raise ValueError(f"Voting period has ended for proposal {proposal_id}")
            
            # Check if voter has already voted
            existing_vote = next((v for v in proposal.votes if v.voter_id == voter_id), None)
            if existing_vote:
                raise ValueError(f"Voter {voter_id} has already voted on proposal {proposal_id}")
            
            # Verify voter signature
            if not await self._verify_voter_signature(voter_id, proposal_id, choice, signature):
                raise ValueError("Invalid voter signature")
            
            # Verify voting power
            if not await self._verify_voting_power(voter_id, voting_power):
                raise ValueError("Invalid voting power")
            
            # Create vote
            vote = Vote(
                voter_id=voter_id,
                voter_type=await self._get_voter_type(voter_id),
                choice=choice,
                voting_power=voting_power,
                timestamp=datetime.now(timezone.utc),
                signature=signature
            )
            
            # Add vote to proposal
            proposal.votes.append(vote)
            proposal.total_voting_power += voting_power
            
            # Update vote counts
            if choice == VoteChoice.YES:
                proposal.yes_votes += voting_power
            elif choice == VoteChoice.NO:
                proposal.no_votes += voting_power
            elif choice == VoteChoice.ABSTAIN:
                proposal.abstain_votes += voting_power
            
            # Check if proposal should be activated
            if proposal.status == ProposalStatus.SUBMITTED:
                proposal.status = ProposalStatus.ACTIVE
            
            await self._save_proposal(proposal)
            
            logger.info(f"Vote cast on proposal {proposal_id} by {voter_id}: {choice.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cast vote on proposal {proposal_id}: {e}")
            return False
    
    async def finalize_proposal(self, proposal_id: str) -> VotingResult:
        """Finalize a proposal and determine the result"""
        try:
            proposal = await self._load_proposal(proposal_id)
            
            if proposal.status not in [ProposalStatus.ACTIVE, ProposalStatus.SUBMITTED]:
                raise ValueError(f"Proposal {proposal_id} is not in a finalizable state")
            
            if datetime.now(timezone.utc) < proposal.voting_end:
                raise ValueError(f"Voting period has not ended for proposal {proposal_id}")
            
            # Calculate voting results
            total_power = proposal.total_voting_power
            yes_power = proposal.yes_votes
            no_power = proposal.no_votes
            abstain_power = proposal.abstain_votes
            
            # Get total available voting power
            total_available_power = await self._get_total_voting_power()
            quorum_percentage = (total_power / total_available_power) * 100 if total_available_power > 0 else 0
            
            # Check quorum
            quorum_met = quorum_percentage >= self.min_quorum
            
            # Calculate approval percentage
            total_decision_power = yes_power + no_power
            approval_percentage = (yes_power / total_decision_power) * 100 if total_decision_power > 0 else 0
            
            # Determine if proposal passed
            passed = quorum_met and approval_percentage >= self.min_approval
            
            # Update proposal status
            proposal.status = ProposalStatus.PASSED if passed else ProposalStatus.REJECTED
            proposal.quorum_met = quorum_met
            proposal.passed = passed
            
            await self._save_proposal(proposal)
            
            # Create voting result
            result = VotingResult(
                proposal_id=proposal_id,
                total_votes=len(proposal.votes),
                total_voting_power=total_power,
                yes_power=yes_power,
                no_power=no_power,
                abstain_power=abstain_power,
                quorum_percentage=quorum_percentage,
                approval_percentage=approval_percentage,
                quorum_met=quorum_met,
                passed=passed,
                executed=False
            )
            
            # Notify about result
            await self._notify_proposal_result(proposal, result)
            
            logger.info(f"Finalized proposal {proposal_id}: {'PASSED' if passed else 'REJECTED'}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to finalize proposal {proposal_id}: {e}")
            raise
    
    async def execute_proposal(self, proposal_id: str, executor_id: str) -> bool:
        """Execute a passed proposal"""
        try:
            proposal = await self._load_proposal(proposal_id)
            
            if proposal.status != ProposalStatus.PASSED:
                raise ValueError(f"Proposal {proposal_id} has not passed")
            
            if proposal.executed_at:
                raise ValueError(f"Proposal {proposal_id} has already been executed")
            
            # Verify executor permissions
            if not await self._verify_executor_permissions(executor_id, proposal):
                raise ValueError(f"Executor {executor_id} not authorized to execute proposal {proposal_id}")
            
            # Execute the proposal
            execution_success = await self._execute_proposal_content(proposal)
            
            if execution_success:
                proposal.status = ProposalStatus.EXECUTED
                proposal.executed_at = datetime.now(timezone.utc)
                proposal.execution_data = {
                    "executor_id": executor_id,
                    "execution_timestamp": proposal.executed_at.isoformat(),
                    "success": True
                }
                
                await self._save_proposal(proposal)
                
                # Notify about execution
                await self._notify_proposal_executed(proposal)
                
                logger.info(f"Executed proposal {proposal_id} by {executor_id}")
                return True
            else:
                proposal.execution_data = {
                    "executor_id": executor_id,
                    "execution_timestamp": datetime.now(timezone.utc).isoformat(),
                    "success": False,
                    "error": "Execution failed"
                }
                
                await self._save_proposal(proposal)
                
                logger.error(f"Failed to execute proposal {proposal_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute proposal {proposal_id}: {e}")
            return False
    
    async def _save_proposal(self, proposal: Proposal):
        """Save proposal to storage"""
        try:
            proposal_file = self.storage_path / f"{proposal.proposal_id}.json"
            
            proposal_dict = {
                "proposal_id": proposal.proposal_id,
                "proposer_id": proposal.proposer_id,
                "content": {
                    "title": proposal.content.title,
                    "description": proposal.content.description,
                    "proposal_type": proposal.content.proposal_type.value,
                    "parameters": proposal.content.parameters,
                    "implementation_plan": proposal.content.implementation_plan,
                    "expected_impact": proposal.content.expected_impact,
                    "risk_assessment": proposal.content.risk_assessment,
                    "references": proposal.content.references,
                    "attachments": proposal.content.attachments
                },
                "status": proposal.status.value,
                "created_at": proposal.created_at.isoformat(),
                "submitted_at": proposal.submitted_at.isoformat() if proposal.submitted_at else None,
                "voting_start": proposal.voting_start.isoformat() if proposal.voting_start else None,
                "voting_end": proposal.voting_end.isoformat() if proposal.voting_end else None,
                "executed_at": proposal.executed_at.isoformat() if proposal.executed_at else None,
                "votes": [
                    {
                        "voter_id": vote.voter_id,
                        "voter_type": vote.voter_type.value,
                        "choice": vote.choice.value,
                        "voting_power": vote.voting_power,
                        "timestamp": vote.timestamp.isoformat(),
                        "signature": vote.signature,
                        "metadata": vote.metadata
                    } for vote in proposal.votes
                ],
                "total_voting_power": proposal.total_voting_power,
                "yes_votes": proposal.yes_votes,
                "no_votes": proposal.no_votes,
                "abstain_votes": proposal.abstain_votes,
                "quorum_met": proposal.quorum_met,
                "passed": proposal.passed,
                "execution_data": proposal.execution_data,
                "metadata": proposal.metadata
            }
            
            async with aiofiles.open(proposal_file, 'w') as f:
                await f.write(json.dumps(proposal_dict, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to save proposal {proposal.proposal_id}: {e}")
            raise
    
    async def _load_proposal(self, proposal_id: str) -> Proposal:
        """Load proposal from storage"""
        try:
            proposal_file = self.storage_path / f"{proposal_id}.json"
            
            if not proposal_file.exists():
                raise FileNotFoundError(f"Proposal {proposal_id} not found")
            
            async with aiofiles.open(proposal_file, 'r') as f:
                proposal_dict = json.loads(await f.read())
            
            # Reconstruct proposal object
            content = ProposalContent(
                title=proposal_dict["content"]["title"],
                description=proposal_dict["content"]["description"],
                proposal_type=ProposalType(proposal_dict["content"]["proposal_type"]),
                parameters=proposal_dict["content"]["parameters"],
                implementation_plan=proposal_dict["content"]["implementation_plan"],
                expected_impact=proposal_dict["content"]["expected_impact"],
                risk_assessment=proposal_dict["content"]["risk_assessment"],
                references=proposal_dict["content"]["references"],
                attachments=proposal_dict["content"]["attachments"]
            )
            
            votes = [
                Vote(
                    voter_id=vote_dict["voter_id"],
                    voter_type=VoterType(vote_dict["voter_type"]),
                    choice=VoteChoice(vote_dict["choice"]),
                    voting_power=vote_dict["voting_power"],
                    timestamp=datetime.fromisoformat(vote_dict["timestamp"]),
                    signature=vote_dict["signature"],
                    metadata=vote_dict["metadata"]
                ) for vote_dict in proposal_dict["votes"]
            ]
            
            proposal = Proposal(
                proposal_id=proposal_dict["proposal_id"],
                proposer_id=proposal_dict["proposer_id"],
                content=content,
                status=ProposalStatus(proposal_dict["status"]),
                created_at=datetime.fromisoformat(proposal_dict["created_at"]),
                submitted_at=datetime.fromisoformat(proposal_dict["submitted_at"]) if proposal_dict["submitted_at"] else None,
                voting_start=datetime.fromisoformat(proposal_dict["voting_start"]) if proposal_dict["voting_start"] else None,
                voting_end=datetime.fromisoformat(proposal_dict["voting_end"]) if proposal_dict["voting_end"] else None,
                executed_at=datetime.fromisoformat(proposal_dict["executed_at"]) if proposal_dict["executed_at"] else None,
                votes=votes,
                total_voting_power=proposal_dict["total_voting_power"],
                yes_votes=proposal_dict["yes_votes"],
                no_votes=proposal_dict["no_votes"],
                abstain_votes=proposal_dict["abstain_votes"],
                quorum_met=proposal_dict["quorum_met"],
                passed=proposal_dict["passed"],
                execution_data=proposal_dict["execution_data"],
                metadata=proposal_dict["metadata"]
            )
            
            return proposal
            
        except Exception as e:
            logger.error(f"Failed to load proposal {proposal_id}: {e}")
            raise
    
    async def list_proposals(self, status: Optional[ProposalStatus] = None, 
                           proposer_id: Optional[str] = None,
                           proposal_type: Optional[ProposalType] = None) -> List[Proposal]:
        """List proposals with optional filters"""
        try:
            proposals = []
            
            for proposal_file in self.storage_path.glob("*.json"):
                try:
                    proposal_id = proposal_file.stem
                    proposal = await self._load_proposal(proposal_id)
                    
                    # Apply filters
                    if status and proposal.status != status:
                        continue
                    if proposer_id and proposal.proposer_id != proposer_id:
                        continue
                    if proposal_type and proposal.content.proposal_type != proposal_type:
                        continue
                    
                    proposals.append(proposal)
                    
                except Exception as e:
                    logger.warning(f"Failed to load proposal from {proposal_file}: {e}")
                    continue
            
            return sorted(proposals, key=lambda p: p.created_at, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list proposals: {e}")
            raise
    
    async def get_proposal_summary(self, proposal_id: str) -> Dict[str, Any]:
        """Get a summary of a proposal"""
        try:
            proposal = await self._load_proposal(proposal_id)
            
            return {
                "proposal_id": proposal.proposal_id,
                "title": proposal.content.title,
                "proposal_type": proposal.content.proposal_type.value,
                "status": proposal.status.value,
                "created_at": proposal.created_at.isoformat(),
                "voting_end": proposal.voting_end.isoformat() if proposal.voting_end else None,
                "total_votes": len(proposal.votes),
                "total_voting_power": proposal.total_voting_power,
                "yes_votes": proposal.yes_votes,
                "no_votes": proposal.no_votes,
                "abstain_votes": proposal.abstain_votes,
                "quorum_met": proposal.quorum_met,
                "passed": proposal.passed,
                "executed": proposal.status == ProposalStatus.EXECUTED
            }
            
        except Exception as e:
            logger.error(f"Failed to get proposal summary for {proposal_id}: {e}")
            raise
    
    # Placeholder methods for external integrations
    async def _verify_proposer_signature(self, proposal: Proposal, signature: str) -> bool:
        """Verify proposer signature"""
        # In production, this would verify cryptographic signatures
        return True
    
    async def _check_proposer_eligibility(self, proposer_id: str) -> bool:
        """Check if proposer is eligible to submit proposals"""
        # In production, this would check stake, reputation, etc.
        return True
    
    async def _verify_voter_signature(self, voter_id: str, proposal_id: str, 
                                    choice: VoteChoice, signature: str) -> bool:
        """Verify voter signature"""
        # In production, this would verify cryptographic signatures
        return True
    
    async def _verify_voting_power(self, voter_id: str, voting_power: float) -> bool:
        """Verify voter's voting power"""
        # In production, this would check actual stake/delegation
        return voting_power > 0
    
    async def _get_voter_type(self, voter_id: str) -> VoterType:
        """Get voter type"""
        # In production, this would determine based on actual role
        return VoterType.VALIDATOR
    
    async def _get_total_voting_power(self) -> float:
        """Get total available voting power in the system"""
        # In production, this would query the actual stake/delegation system
        return 1000000.0  # Placeholder
    
    async def _verify_executor_permissions(self, executor_id: str, proposal: Proposal) -> bool:
        """Verify executor has permission to execute the proposal"""
        # In production, this would check actual permissions
        return True
    
    async def _execute_proposal_content(self, proposal: Proposal) -> bool:
        """Execute the actual proposal content"""
        try:
            # In production, this would execute the actual proposal logic
            logger.info(f"Executing proposal {proposal.proposal_id}: {proposal.content.title}")
            
            # Simulate execution based on proposal type
            if proposal.content.proposal_type == ProposalType.PARAMETER_CHANGE:
                # Update system parameters
                pass
            elif proposal.content.proposal_type == ProposalType.TREASURY_ALLOCATION:
                # Allocate treasury funds
                pass
            elif proposal.content.proposal_type == ProposalType.SYSTEM_UPGRADE:
                # Trigger system upgrade
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute proposal content: {e}")
            return False
    
    async def _notify_proposal_submitted(self, proposal: Proposal):
        """Notify stakeholders about proposal submission"""
        logger.info(f"Notifying stakeholders about proposal {proposal.proposal_id}")
        # In production, this would send actual notifications
    
    async def _notify_proposal_result(self, proposal: Proposal, result: VotingResult):
        """Notify stakeholders about proposal result"""
        logger.info(f"Notifying stakeholders about proposal {proposal.proposal_id} result: {'PASSED' if result.passed else 'REJECTED'}")
        # In production, this would send actual notifications
    
    async def _notify_proposal_executed(self, proposal: Proposal):
        """Notify stakeholders about proposal execution"""
        logger.info(f"Notifying stakeholders about proposal {proposal.proposal_id} execution")
        # In production, this would send actual notifications


# Global proposal manager instance
proposal_manager = ProposalManager()


async def create_governance_proposal(proposer_id: str, title: str, description: str,
                                   proposal_type: ProposalType, **kwargs) -> str:
    """Create a new governance proposal"""
    content = ProposalContent(
        title=title,
        description=description,
        proposal_type=proposal_type,
        **kwargs
    )
    return await proposal_manager.create_proposal(proposer_id, content)


async def submit_proposal_for_voting(proposal_id: str, proposer_signature: str) -> bool:
    """Submit a proposal for voting"""
    return await proposal_manager.submit_proposal(proposal_id, proposer_signature)


async def vote_on_proposal(proposal_id: str, voter_id: str, choice: VoteChoice,
                          voting_power: float, signature: str) -> bool:
    """Cast a vote on a proposal"""
    return await proposal_manager.cast_vote(proposal_id, voter_id, choice, voting_power, signature)


async def get_proposal_status(proposal_id: str) -> Dict[str, Any]:
    """Get proposal status and summary"""
    return await proposal_manager.get_proposal_summary(proposal_id)


async def list_active_proposals() -> List[Proposal]:
    """List all active proposals"""
    return await proposal_manager.list_proposals(status=ProposalStatus.ACTIVE)


async def finalize_voting(proposal_id: str) -> VotingResult:
    """Finalize voting on a proposal"""
    return await proposal_manager.finalize_proposal(proposal_id)


if __name__ == "__main__":
    # Test the proposal management system
    async def test_proposal_management():
        # Create a test proposal
        proposal_id = await create_governance_proposal(
            proposer_id="test_proposer",
            title="Test System Upgrade",
            description="This is a test proposal for system upgrade",
            proposal_type=ProposalType.SYSTEM_UPGRADE
        )
        print(f"Created proposal: {proposal_id}")
        
        # Submit for voting
        success = await submit_proposal_for_voting(proposal_id, "test_signature")
        print(f"Submitted proposal: {success}")
        
        # Get status
        status = await get_proposal_status(proposal_id)
        print(f"Proposal status: {status['status']}")
        
        # List active proposals
        active_proposals = await list_active_proposals()
        print(f"Active proposals: {len(active_proposals)}")
    
    asyncio.run(test_proposal_management())
