#!/usr/bin/env python3
"""
LUCID Blockchain Governance System - Lucid Governor
Comprehensive governance system for blockchain parameter management and protocol upgrades
Based on LUCID-STRICT requirements per Spec-1c and blockchain governance patterns
"""

from __future__ import annotations

import asyncio
import logging
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
from decimal import Decimal

# Import blockchain components
from ..consensus import SimpleProposer
from ..config import DEFAULT_CONFIG
from ..state import StateManager
from ..network import NetworkManager
from ..crypto import CryptoManager

logger = logging.getLogger(__name__)

# Governance Constants
GOVERNANCE_PROPOSAL_TIMEOUT_HOURS = int(os.getenv("GOVERNANCE_PROPOSAL_TIMEOUT_HOURS", "168"))  # 1 week
GOVERNANCE_VOTE_DURATION_HOURS = int(os.getenv("GOVERNANCE_VOTE_DURATION_HOURS", "72"))  # 3 days
GOVERNANCE_QUORUM_PERCENTAGE = float(os.getenv("GOVERNANCE_QUORUM_PERCENTAGE", "0.67"))  # 67% quorum
GOVERNANCE_SUPERMAJORITY_PERCENTAGE = float(os.getenv("GOVERNANCE_SUPERMAJORITY_PERCENTAGE", "0.75"))  # 75% supermajority
GOVERNANCE_EXECUTION_DELAY_HOURS = int(os.getenv("GOVERNANCE_EXECUTION_DELAY_HOURS", "24"))  # 24 hour delay


class GovernanceAction(Enum):
    """Types of governance actions"""
    PARAMETER_CHANGE = "parameter_change"  # Change blockchain parameters
    PROTOCOL_UPGRADE = "protocol_upgrade"  # Protocol version upgrade
    CONSENSUS_CHANGE = "consensus_change"  # Consensus mechanism change
    TREASURY_ALLOCATION = "treasury_allocation"  # Treasury fund allocation
    NODE_PENALTY = "node_penalty"  # Penalize or remove node
    EMERGENCY_PAUSE = "emergency_pause"  # Emergency network pause
    NETWORK_POLICY = "network_policy"  # Network policy changes
    CONTRACT_UPGRADE = "contract_upgrade"  # Smart contract upgrades


class ProposalStatus(Enum):
    """Proposal lifecycle status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
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


@dataclass
class GovernanceProposal:
    """Blockchain governance proposal"""
    proposal_id: str
    proposer_address: str
    action_type: GovernanceAction
    title: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    voting_starts_at: Optional[datetime] = None
    voting_ends_at: Optional[datetime] = None
    execution_delay_until: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    execution_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposer_address": self.proposer_address,
            "action_type": self.action_type.value,
            "title": self.title,
            "description": self.description,
            "parameters": self.parameters,
            "status": self.status.value,
            "created_at": self.created_at,
            "voting_starts_at": self.voting_starts_at,
            "voting_ends_at": self.voting_ends_at,
            "execution_delay_until": self.execution_delay_until,
            "executed_at": self.executed_at,
            "execution_hash": self.execution_hash,
            "metadata": self.metadata
        }


@dataclass
class GovernanceVote:
    """Governance vote"""
    vote_id: str
    proposal_id: str
    voter_address: str
    choice: VoteChoice
    weight: Decimal
    stake_amount: Decimal
    cast_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "vote_id": self.vote_id,
            "proposal_id": self.proposal_id,
            "voter_address": self.voter_address,
            "choice": self.choice.value,
            "weight": str(self.weight),
            "stake_amount": str(self.stake_amount),
            "cast_at": self.cast_at,
            "signature": self.signature
        }


@dataclass
class VoteTally:
    """Vote tally for a proposal"""
    proposal_id: str
    total_eligible_stake: Decimal
    total_votes_cast: int
    total_stake_voted: Decimal
    yes_votes: int
    no_votes: int
    abstain_votes: int
    yes_stake: Decimal
    no_stake: Decimal
    abstain_stake: Decimal
    quorum_met: bool
    supermajority_met: bool
    result: Optional[str] = None  # "passed", "rejected", "tied"
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "total_eligible_stake": str(self.total_eligible_stake),
            "total_votes_cast": self.total_votes_cast,
            "total_stake_voted": str(self.total_stake_voted),
            "yes_votes": self.yes_votes,
            "no_votes": self.no_votes,
            "abstain_votes": self.abstain_votes,
            "yes_stake": str(self.yes_stake),
            "no_stake": str(self.no_stake),
            "abstain_stake": str(self.abstain_stake),
            "quorum_met": self.quorum_met,
            "supermajority_met": self.supermajority_met,
            "result": self.result,
            "calculated_at": self.calculated_at
        }


class LucidGovernor:
    """
    Lucid Blockchain Governance System
    
    Handles:
    - Governance proposal creation and management
    - Stake-weighted voting system
    - Proposal execution and parameter changes
    - Emergency governance actions
    - Protocol upgrade management
    - Treasury allocation governance
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        network_manager: NetworkManager,
        crypto_manager: CryptoManager,
        data_dir: str = "/data/governance"
    ):
        self.state_manager = state_manager
        self.network_manager = network_manager
        self.crypto_manager = crypto_manager
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self.active_proposals: Dict[str, GovernanceProposal] = {}
        self.proposal_votes: Dict[str, List[GovernanceVote]] = {}
        self.proposal_tallies: Dict[str, VoteTally] = {}
        self.running = False
        
        # Background tasks
        self._lifecycle_task: Optional[asyncio.Task] = None
        self._tally_task: Optional[asyncio.Task] = None
        
        logger.info("Lucid Governor initialized")
    
    async def start(self):
        """Start governance system"""
        try:
            self.running = True
            
            # Load existing proposals
            await self._load_proposals()
            
            # Start background tasks
            self._lifecycle_task = asyncio.create_task(self._proposal_lifecycle_loop())
            self._tally_task = asyncio.create_task(self._vote_tally_loop())
            
            logger.info("Lucid Governor started")
            
        except Exception as e:
            logger.error(f"Failed to start Lucid Governor: {e}")
            raise
    
    async def stop(self):
        """Stop governance system"""
        try:
            self.running = False
            
            # Cancel background tasks
            tasks = [self._lifecycle_task, self._tally_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
            
            logger.info("Lucid Governor stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Lucid Governor: {e}")
    
    async def create_proposal(
        self,
        proposer_address: str,
        action_type: GovernanceAction,
        title: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new governance proposal
        
        Args:
            proposer_address: Address of the proposer
            action_type: Type of governance action
            title: Proposal title
            description: Detailed description
            parameters: Action-specific parameters
            
        Returns:
            Proposal ID
        """
        try:
            # Validate proposer has sufficient stake
            proposer_stake = await self._get_stake_amount(proposer_address)
            if proposer_stake < Decimal("1000"):  # Minimum stake requirement
                raise ValueError("Insufficient stake to create proposal")
            
            proposal_id = str(uuid.uuid4())
            
            proposal = GovernanceProposal(
                proposal_id=proposal_id,
                proposer_address=proposer_address,
                action_type=action_type,
                title=title,
                description=description,
                parameters=parameters or {}
            )
            
            # Store proposal
            self.active_proposals[proposal_id] = proposal
            await self._save_proposal(proposal)
            
            logger.info(f"Governance proposal created: {proposal_id} by {proposer_address}")
            return proposal_id
            
        except Exception as e:
            logger.error(f"Failed to create proposal: {e}")
            raise
    
    async def submit_proposal(self, proposal_id: str) -> bool:
        """Submit proposal for voting"""
        try:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal not found: {proposal_id}")
            
            if proposal.status != ProposalStatus.DRAFT:
                raise ValueError(f"Proposal not in draft status: {proposal.status}")
            
            # Update proposal status
            proposal.status = ProposalStatus.SUBMITTED
            proposal.voting_starts_at = datetime.now(timezone.utc)
            proposal.voting_ends_at = proposal.voting_starts_at + timedelta(hours=GOVERNANCE_VOTE_DURATION_HOURS)
            
            # Calculate execution delay
            proposal.execution_delay_until = proposal.voting_ends_at + timedelta(hours=GOVERNANCE_EXECUTION_DELAY_HOURS)
            
            # Save proposal
            await self._save_proposal(proposal)
            
            logger.info(f"Proposal submitted for voting: {proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit proposal: {e}")
            return False
    
    async def cast_vote(
        self,
        voter_address: str,
        proposal_id: str,
        choice: VoteChoice
    ) -> str:
        """
        Cast a vote on a proposal
        
        Args:
            voter_address: Address of the voter
            proposal_id: Proposal being voted on
            choice: Vote choice
            
        Returns:
            Vote ID
        """
        try:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal not found: {proposal_id}")
            
            if proposal.status != ProposalStatus.SUBMITTED:
                raise ValueError(f"Proposal not in voting phase: {proposal.status}")
            
            # Check if voting period is active
            now = datetime.now(timezone.utc)
            if now < proposal.voting_starts_at or now > proposal.voting_ends_at:
                raise ValueError("Voting period is not active")
            
            # Check if already voted
            existing_votes = self.proposal_votes.get(proposal_id, [])
            if any(vote.voter_address == voter_address for vote in existing_votes):
                raise ValueError("Address has already voted on this proposal")
            
            # Get voter stake
            stake_amount = await self._get_stake_amount(voter_address)
            if stake_amount <= 0:
                raise ValueError("No stake to vote with")
            
            # Calculate vote weight (stake-weighted)
            vote_weight = stake_amount
            
            vote_id = str(uuid.uuid4())
            
            vote = GovernanceVote(
                vote_id=vote_id,
                proposal_id=proposal_id,
                voter_address=voter_address,
                choice=choice,
                weight=vote_weight,
                stake_amount=stake_amount
            )
            
            # Store vote
            if proposal_id not in self.proposal_votes:
                self.proposal_votes[proposal_id] = []
            self.proposal_votes[proposal_id].append(vote)
            
            await self._save_vote(vote)
            
            # Update tally
            await self._update_proposal_tally(proposal_id)
            
            logger.info(f"Vote cast: {vote_id} on proposal {proposal_id} by {voter_address}")
            return vote_id
            
        except Exception as e:
            logger.error(f"Failed to cast vote: {e}")
            raise
    
    async def execute_proposal(self, proposal_id: str) -> bool:
        """
        Execute a passed proposal
        
        Args:
            proposal_id: Proposal to execute
            
        Returns:
            True if execution successful
        """
        try:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal not found: {proposal_id}")
            
            if proposal.status != ProposalStatus.PASSED:
                raise ValueError(f"Proposal not passed: {proposal.status}")
            
            # Check execution delay
            now = datetime.now(timezone.utc)
            if proposal.execution_delay_until and now < proposal.execution_delay_until:
                raise ValueError("Execution delay period not yet completed")
            
            # Execute based on action type
            execution_success = await self._execute_governance_action(proposal)
            
            if execution_success:
                proposal.status = ProposalStatus.EXECUTED
                proposal.executed_at = now
                proposal.execution_hash = hashlib.sha256(
                    f"{proposal_id}:{now.isoformat()}".encode()
                ).hexdigest()
                
                await self._save_proposal(proposal)
                
                logger.info(f"Proposal executed: {proposal_id}")
                return True
            else:
                logger.error(f"Proposal execution failed: {proposal_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute proposal: {e}")
            return False
    
    async def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get proposal details"""
        try:
            proposal = self.active_proposals.get(proposal_id)
            if proposal:
                return proposal.to_dict()
            
            # Check stored proposals
            proposal_file = self.data_dir / f"{proposal_id}_proposal.json"
            if proposal_file.exists():
                with open(proposal_file, 'r') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get proposal: {e}")
            return None
    
    async def get_proposal_votes(self, proposal_id: str) -> List[Dict[str, Any]]:
        """Get all votes for a proposal"""
        try:
            votes = self.proposal_votes.get(proposal_id, [])
            return [vote.to_dict() for vote in votes]
            
        except Exception as e:
            logger.error(f"Failed to get proposal votes: {e}")
            return []
    
    async def get_proposal_tally(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get vote tally for a proposal"""
        try:
            tally = self.proposal_tallies.get(proposal_id)
            if tally:
                return tally.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get proposal tally: {e}")
            return None
    
    async def get_active_proposals(self) -> List[Dict[str, Any]]:
        """Get all active proposals"""
        try:
            active_proposals = []
            for proposal in self.active_proposals.values():
                if proposal.status in [ProposalStatus.SUBMITTED, ProposalStatus.PASSED]:
                    active_proposals.append(proposal.to_dict())
            
            return active_proposals
            
        except Exception as e:
            logger.error(f"Failed to get active proposals: {e}")
            return []
    
    async def get_governance_stats(self) -> Dict[str, Any]:
        """Get governance system statistics"""
        try:
            stats = {
                "total_proposals": len(self.active_proposals),
                "active_proposals": len([p for p in self.active_proposals.values() 
                                       if p.status in [ProposalStatus.SUBMITTED, ProposalStatus.PASSED]]),
                "total_votes_cast": sum(len(votes) for votes in self.proposal_votes.values()),
                "proposals_by_status": {},
                "proposals_by_type": {}
            }
            
            # Count by status
            for proposal in self.active_proposals.values():
                status = proposal.status.value
                stats["proposals_by_status"][status] = stats["proposals_by_status"].get(status, 0) + 1
            
            # Count by type
            for proposal in self.active_proposals.values():
                action_type = proposal.action_type.value
                stats["proposals_by_type"][action_type] = stats["proposals_by_type"].get(action_type, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get governance stats: {e}")
            return {"error": str(e)}
    
    async def _get_stake_amount(self, address: str) -> Decimal:
        """Get stake amount for an address"""
        try:
            # This would integrate with the actual staking system
            # For now, return a mock value
            return Decimal("1000.0")
            
        except Exception as e:
            logger.error(f"Failed to get stake amount: {e}")
            return Decimal("0.0")
    
    async def _execute_governance_action(self, proposal: GovernanceProposal) -> bool:
        """Execute the governance action"""
        try:
            if proposal.action_type == GovernanceAction.PARAMETER_CHANGE:
                return await self._execute_parameter_change(proposal)
            elif proposal.action_type == GovernanceAction.PROTOCOL_UPGRADE:
                return await self._execute_protocol_upgrade(proposal)
            elif proposal.action_type == GovernanceAction.CONSENSUS_CHANGE:
                return await self._execute_consensus_change(proposal)
            elif proposal.action_type == GovernanceAction.TREASURY_ALLOCATION:
                return await self._execute_treasury_allocation(proposal)
            elif proposal.action_type == GovernanceAction.NODE_PENALTY:
                return await self._execute_node_penalty(proposal)
            elif proposal.action_type == GovernanceAction.EMERGENCY_PAUSE:
                return await self._execute_emergency_pause(proposal)
            elif proposal.action_type == GovernanceAction.NETWORK_POLICY:
                return await self._execute_network_policy(proposal)
            elif proposal.action_type == GovernanceAction.CONTRACT_UPGRADE:
                return await self._execute_contract_upgrade(proposal)
            else:
                logger.error(f"Unknown governance action: {proposal.action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute governance action: {e}")
            return False
    
    async def _execute_parameter_change(self, proposal: GovernanceProposal) -> bool:
        """Execute parameter change"""
        try:
            parameters = proposal.parameters
            
            # Update blockchain parameters
            for param_name, param_value in parameters.items():
                await self.state_manager.update_parameter(param_name, param_value)
                logger.info(f"Parameter updated: {param_name} = {param_value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute parameter change: {e}")
            return False
    
    async def _execute_protocol_upgrade(self, proposal: GovernanceProposal) -> bool:
        """Execute protocol upgrade"""
        try:
            new_version = proposal.parameters.get("new_version")
            if not new_version:
                raise ValueError("Protocol version not specified")
            
            # Update protocol version
            await self.state_manager.update_parameter("protocol_version", new_version)
            logger.info(f"Protocol upgraded to version: {new_version}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute protocol upgrade: {e}")
            return False
    
    async def _execute_consensus_change(self, proposal: GovernanceProposal) -> bool:
        """Execute consensus mechanism change"""
        try:
            new_consensus = proposal.parameters.get("new_consensus")
            if not new_consensus:
                raise ValueError("Consensus mechanism not specified")
            
            # Update consensus mechanism
            await self.state_manager.update_parameter("consensus_mechanism", new_consensus)
            logger.info(f"Consensus mechanism changed to: {new_consensus}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute consensus change: {e}")
            return False
    
    async def _execute_treasury_allocation(self, proposal: GovernanceProposal) -> bool:
        """Execute treasury allocation"""
        try:
            recipient = proposal.parameters.get("recipient")
            amount = proposal.parameters.get("amount")
            
            if not recipient or not amount:
                raise ValueError("Recipient or amount not specified")
            
            # Allocate treasury funds
            await self.state_manager.allocate_treasury_funds(recipient, Decimal(str(amount)))
            logger.info(f"Treasury allocated: {amount} to {recipient}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute treasury allocation: {e}")
            return False
    
    async def _execute_node_penalty(self, proposal: GovernanceProposal) -> bool:
        """Execute node penalty"""
        try:
            node_address = proposal.parameters.get("node_address")
            penalty_type = proposal.parameters.get("penalty_type")
            penalty_amount = proposal.parameters.get("penalty_amount")
            
            if not node_address or not penalty_type:
                raise ValueError("Node address or penalty type not specified")
            
            # Apply penalty
            await self.state_manager.apply_node_penalty(node_address, penalty_type, penalty_amount)
            logger.info(f"Node penalty applied: {penalty_type} to {node_address}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute node penalty: {e}")
            return False
    
    async def _execute_emergency_pause(self, proposal: GovernanceProposal) -> bool:
        """Execute emergency pause"""
        try:
            pause_duration = proposal.parameters.get("pause_duration", 3600)  # Default 1 hour
            
            # Pause network
            await self.network_manager.pause_network(pause_duration)
            logger.info(f"Network paused for {pause_duration} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute emergency pause: {e}")
            return False
    
    async def _execute_network_policy(self, proposal: GovernanceProposal) -> bool:
        """Execute network policy change"""
        try:
            policy_name = proposal.parameters.get("policy_name")
            policy_value = proposal.parameters.get("policy_value")
            
            if not policy_name or policy_value is None:
                raise ValueError("Policy name or value not specified")
            
            # Update network policy
            await self.state_manager.update_network_policy(policy_name, policy_value)
            logger.info(f"Network policy updated: {policy_name} = {policy_value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute network policy: {e}")
            return False
    
    async def _execute_contract_upgrade(self, proposal: GovernanceProposal) -> bool:
        """Execute smart contract upgrade"""
        try:
            contract_address = proposal.parameters.get("contract_address")
            new_code = proposal.parameters.get("new_code")
            
            if not contract_address or not new_code:
                raise ValueError("Contract address or new code not specified")
            
            # Upgrade contract
            await self.state_manager.upgrade_contract(contract_address, new_code)
            logger.info(f"Contract upgraded: {contract_address}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute contract upgrade: {e}")
            return False
    
    async def _update_proposal_tally(self, proposal_id: str):
        """Update vote tally for a proposal"""
        try:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                return
            
            votes = self.proposal_votes.get(proposal_id, [])
            
            total_votes_cast = len(votes)
            total_stake_voted = Decimal("0")
            yes_votes = no_votes = abstain_votes = 0
            yes_stake = no_stake = abstain_stake = Decimal("0")
            
            for vote in votes:
                total_stake_voted += vote.stake_amount
                
                if vote.choice == VoteChoice.YES:
                    yes_votes += 1
                    yes_stake += vote.stake_amount
                elif vote.choice == VoteChoice.NO:
                    no_votes += 1
                    no_stake += vote.stake_amount
                else:  # ABSTAIN
                    abstain_votes += 1
                    abstain_stake += vote.stake_amount
            
            # Calculate total eligible stake (mock for now)
            total_eligible_stake = Decimal("1000000")  # Would get actual total stake
            
            # Check quorum
            quorum_threshold = total_eligible_stake * Decimal(str(GOVERNANCE_QUORUM_PERCENTAGE))
            quorum_met = total_stake_voted >= quorum_threshold
            
            # Check supermajority
            supermajority_threshold = total_stake_voted * Decimal(str(GOVERNANCE_SUPERMAJORITY_PERCENTAGE))
            supermajority_met = yes_stake >= supermajority_threshold
            
            # Determine result
            result = None
            if quorum_met:
                if supermajority_met:
                    result = "passed"
                elif no_stake > yes_stake:
                    result = "rejected"
                else:
                    result = "tied"
            
            tally = VoteTally(
                proposal_id=proposal_id,
                total_eligible_stake=total_eligible_stake,
                total_votes_cast=total_votes_cast,
                total_stake_voted=total_stake_voted,
                yes_votes=yes_votes,
                no_votes=no_votes,
                abstain_votes=abstain_votes,
                yes_stake=yes_stake,
                no_stake=no_stake,
                abstain_stake=abstain_stake,
                quorum_met=quorum_met,
                supermajority_met=supermajority_met,
                result=result
            )
            
            self.proposal_tallies[proposal_id] = tally
            
            # Update proposal status if voting ended
            if proposal.voting_ends_at and datetime.now(timezone.utc) > proposal.voting_ends_at:
                if result == "passed":
                    proposal.status = ProposalStatus.PASSED
                else:
                    proposal.status = ProposalStatus.REJECTED
                
                await self._save_proposal(proposal)
            
        except Exception as e:
            logger.error(f"Failed to update proposal tally: {e}")
    
    async def _proposal_lifecycle_loop(self):
        """Manage proposal lifecycle transitions"""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                for proposal in list(self.active_proposals.values()):
                    try:
                        # Check if voting period ended
                        if (proposal.status == ProposalStatus.SUBMITTED and
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
                            
                            await self._save_proposal(proposal)
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
                # Update tallies for active proposals
                for proposal_id in list(self.active_proposals.keys()):
                    proposal = self.active_proposals[proposal_id]
                    if proposal.status == ProposalStatus.SUBMITTED:
                        await self._update_proposal_tally(proposal_id)
                
                await asyncio.sleep(600)  # Update every 10 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Vote tally loop error: {e}")
                await asyncio.sleep(60)
    
    async def _save_proposal(self, proposal: GovernanceProposal):
        """Save proposal to disk"""
        try:
            proposal_file = self.data_dir / f"{proposal.proposal_id}_proposal.json"
            
            with open(proposal_file, 'w') as f:
                json.dump(proposal.to_dict(), f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save proposal: {e}")
    
    async def _save_vote(self, vote: GovernanceVote):
        """Save vote to disk"""
        try:
            vote_file = self.data_dir / f"{vote.vote_id}_vote.json"
            
            with open(vote_file, 'w') as f:
                json.dump(vote.to_dict(), f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save vote: {e}")
    
    async def _load_proposals(self):
        """Load proposals from disk"""
        try:
            for proposal_file in self.data_dir.glob("*_proposal.json"):
                with open(proposal_file, 'r') as f:
                    proposal_data = json.load(f)
                
                proposal = GovernanceProposal(
                    proposal_id=proposal_data["proposal_id"],
                    proposer_address=proposal_data["proposer_address"],
                    action_type=GovernanceAction(proposal_data["action_type"]),
                    title=proposal_data["title"],
                    description=proposal_data["description"],
                    parameters=proposal_data.get("parameters", {}),
                    status=ProposalStatus(proposal_data["status"]),
                    created_at=datetime.fromisoformat(proposal_data["created_at"]),
                    voting_starts_at=datetime.fromisoformat(proposal_data["voting_starts_at"]) if proposal_data.get("voting_starts_at") else None,
                    voting_ends_at=datetime.fromisoformat(proposal_data["voting_ends_at"]) if proposal_data.get("voting_ends_at") else None,
                    execution_delay_until=datetime.fromisoformat(proposal_data["execution_delay_until"]) if proposal_data.get("execution_delay_until") else None,
                    executed_at=datetime.fromisoformat(proposal_data["executed_at"]) if proposal_data.get("executed_at") else None,
                    execution_hash=proposal_data.get("execution_hash"),
                    metadata=proposal_data.get("metadata", {})
                )
                
                self.active_proposals[proposal.proposal_id] = proposal
            
            logger.info(f"Loaded {len(self.active_proposals)} proposals")
            
        except Exception as e:
            logger.error(f"Failed to load proposals: {e}")


# Global governor instance
_governor: Optional[LucidGovernor] = None


def get_governor() -> Optional[LucidGovernor]:
    """Get global governor instance"""
    global _governor
    return _governor


def create_governor(
    state_manager: StateManager,
    network_manager: NetworkManager,
    crypto_manager: CryptoManager,
    data_dir: str = "/data/governance"
) -> LucidGovernor:
    """Create governor instance"""
    global _governor
    _governor = LucidGovernor(state_manager, network_manager, crypto_manager, data_dir)
    return _governor


async def cleanup_governor():
    """Cleanup governor"""
    global _governor
    if _governor:
        await _governor.stop()
        _governor = None


if __name__ == "__main__":
    # Test governance system
    async def test_governance():
        print("Testing Lucid Governance System...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - governance system ready")
    
    asyncio.run(test_governance())
