#!/usr/bin/env python3
"""
Lucid RDP Blockchain Governance Timelock System

This module implements a timelock mechanism for governance proposals,
ensuring proper delays and security for critical system changes.

Author: Lucid RDP Team
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field


class TimelockStatus(Enum):
    """Timelock status states"""
    PENDING = "pending"
    QUEUED = "queued"
    EXECUTABLE = "executable"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ProposalType(Enum):
    """Governance proposal types"""
    PARAMETER_CHANGE = "parameter_change"
    CONTRACT_UPGRADE = "contract_upgrade"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    KEY_ROTATION = "key_rotation"
    NODE_PROVISIONING = "node_provisioning"
    POLICY_UPDATE = "policy_update"
    FEE_ADJUSTMENT = "fee_adjustment"
    CONSENSUS_CHANGE = "consensus_change"


class ExecutionLevel(Enum):
    """Execution urgency levels"""
    NORMAL = "normal"           # 24 hours delay
    URGENT = "urgent"           # 4 hours delay
    EMERGENCY = "emergency"     # 1 hour delay
    IMMEDIATE = "immediate"     # No delay (admin only)


@dataclass
class TimelockProposal:
    """Timelock governance proposal"""
    proposal_id: str
    proposal_type: ProposalType
    title: str
    description: str
    proposer: str
    target_contract: Optional[str] = None
    target_function: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    execution_level: ExecutionLevel = ExecutionLevel.NORMAL
    delay_seconds: int = 86400  # 24 hours default
    grace_period_seconds: int = 604800  # 7 days default
    status: TimelockStatus = TimelockStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    queued_at: Optional[datetime] = None
    executable_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    executor: Optional[str] = None
    execution_tx_hash: Optional[str] = None
    required_signatures: int = 1
    signatures: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "_id": self.proposal_id,
            "type": self.proposal_type.value,
            "title": self.title,
            "description": self.description,
            "proposer": self.proposer,
            "target_contract": self.target_contract,
            "target_function": self.target_function,
            "parameters": self.parameters,
            "execution_level": self.execution_level.value,
            "delay_seconds": self.delay_seconds,
            "grace_period_seconds": self.grace_period_seconds,
            "status": self.status.value,
            "created_at": self.created_at,
            "queued_at": self.queued_at,
            "executable_at": self.executable_at,
            "executed_at": self.executed_at,
            "cancelled_at": self.cancelled_at,
            "executor": self.executor,
            "execution_tx_hash": self.execution_tx_hash,
            "required_signatures": self.required_signatures,
            "signatures": self.signatures,
            "metadata": self.metadata
        }
    
    def calculate_hash(self) -> str:
        """Calculate proposal hash for verification"""
        proposal_data = {
            "proposal_id": self.proposal_id,
            "type": self.proposal_type.value,
            "target_contract": self.target_contract,
            "target_function": self.target_function,
            "parameters": self.parameters,
            "execution_level": self.execution_level.value,
            "delay_seconds": self.delay_seconds
        }
        data_str = json.dumps(proposal_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def is_executable(self) -> bool:
        """Check if proposal is ready for execution"""
        if self.status != TimelockStatus.EXECUTABLE:
            return False
        
        if self.executable_at is None:
            return False
        
        return datetime.now(timezone.utc) >= self.executable_at
    
    def is_expired(self) -> bool:
        """Check if proposal has expired"""
        if self.executable_at is None:
            return False
        
        expiry_time = self.executable_at + timedelta(seconds=self.grace_period_seconds)
        return datetime.now(timezone.utc) > expiry_time


@dataclass
class TimelockConfig:
    """Timelock configuration"""
    min_delay_seconds: int = 3600  # 1 hour minimum
    max_delay_seconds: int = 2592000  # 30 days maximum
    default_grace_period: int = 604800  # 7 days
    max_grace_period: int = 2592000  # 30 days
    admin_addresses: Set[str] = field(default_factory=set)
    emergency_addresses: Set[str] = field(default_factory=set)
    required_signatures: Dict[ProposalType, int] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.required_signatures:
            self.required_signatures = {
                ProposalType.PARAMETER_CHANGE: 1,
                ProposalType.CONTRACT_UPGRADE: 2,
                ProposalType.EMERGENCY_SHUTDOWN: 3,
                ProposalType.KEY_ROTATION: 2,
                ProposalType.NODE_PROVISIONING: 1,
                ProposalType.POLICY_UPDATE: 1,
                ProposalType.FEE_ADJUSTMENT: 1,
                ProposalType.CONSENSUS_CHANGE: 3
            }


class TimelockGovernance:
    """Timelock governance system for Lucid RDP blockchain"""
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        config: Optional[TimelockConfig] = None,
        output_dir: str = "/data/timelock"
    ):
        self.db = db
        self.config = config or TimelockConfig()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage for active proposals
        self.active_proposals: Dict[str, TimelockProposal] = {}
        self.execution_queue: List[str] = []
        self.is_running = False
        
        # Background tasks
        self._execution_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def start(self) -> bool:
        """Start the timelock governance system"""
        try:
            await self._setup_database()
            await self._load_active_proposals()
            
            self.is_running = True
            self._execution_task = asyncio.create_task(self._execution_loop())
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            await self._log_event("system_start", {"status": "started"})
            return True
            
        except Exception as e:
            await self._log_event("system_start_error", {"error": str(e)})
            return False
    
    async def stop(self) -> None:
        """Stop the timelock governance system"""
        self.is_running = False
        
        if self._execution_task:
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                pass
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        await self._log_event("system_stop", {"status": "stopped"})
    
    async def create_proposal(
        self,
        proposal_type: ProposalType,
        title: str,
        description: str,
        proposer: str,
        target_contract: Optional[str] = None,
        target_function: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        execution_level: ExecutionLevel = ExecutionLevel.NORMAL,
        delay_seconds: Optional[int] = None
    ) -> str:
        """Create a new governance proposal"""
        
        # Generate proposal ID
        proposal_id = f"prop_{int(time.time())}_{hashlib.sha256(f'{proposer}{title}'.encode()).hexdigest()[:8]}"
        
        # Set delay based on execution level
        if delay_seconds is None:
            delay_seconds = self._get_delay_for_level(execution_level)
        
        # Validate delay
        if delay_seconds < self.config.min_delay_seconds:
            raise ValueError(f"Delay too short: minimum {self.config.min_delay_seconds} seconds")
        
        if delay_seconds > self.config.max_delay_seconds:
            raise ValueError(f"Delay too long: maximum {self.config.max_delay_seconds} seconds")
        
        # Create proposal
        proposal = TimelockProposal(
            proposal_id=proposal_id,
            proposal_type=proposal_type,
            title=title,
            description=description,
            proposer=proposer,
            target_contract=target_contract,
            target_function=target_function,
            parameters=parameters or {},
            execution_level=execution_level,
            delay_seconds=delay_seconds,
            grace_period_seconds=self.config.default_grace_period,
            required_signatures=self.config.required_signatures.get(proposal_type, 1)
        )
        
        # Store proposal
        await self._store_proposal(proposal)
        self.active_proposals[proposal_id] = proposal
        
        await self._log_event("proposal_created", {
            "proposal_id": proposal_id,
            "proposer": proposer,
            "type": proposal_type.value,
            "execution_level": execution_level.value
        })
        
        return proposal_id
    
    async def queue_proposal(self, proposal_id: str, executor: str) -> bool:
        """Queue a proposal for execution after delay"""
        
        if proposal_id not in self.active_proposals:
            return False
        
        proposal = self.active_proposals[proposal_id]
        
        if proposal.status != TimelockStatus.PENDING:
            return False
        
        # Calculate execution time
        proposal.queued_at = datetime.now(timezone.utc)
        proposal.executable_at = proposal.queued_at + timedelta(seconds=proposal.delay_seconds)
        proposal.status = TimelockStatus.QUEUED
        proposal.executor = executor
        
        # Update storage
        await self._store_proposal(proposal)
        
        # Add to execution queue
        if proposal_id not in self.execution_queue:
            self.execution_queue.append(proposal_id)
        
        await self._log_event("proposal_queued", {
            "proposal_id": proposal_id,
            "executor": executor,
            "executable_at": proposal.executable_at.isoformat()
        })
        
        return True
    
    async def execute_proposal(self, proposal_id: str, executor: str, tx_hash: Optional[str] = None) -> bool:
        """Execute a queued proposal"""
        
        if proposal_id not in self.active_proposals:
            return False
        
        proposal = self.active_proposals[proposal_id]
        
        if not proposal.is_executable():
            return False
        
        if proposal.is_expired():
            proposal.status = TimelockStatus.EXPIRED
            await self._store_proposal(proposal)
            return False
        
        # Execute the proposal
        try:
            success = await self._execute_proposal_logic(proposal)
            
            if success:
                proposal.status = TimelockStatus.EXECUTED
                proposal.executed_at = datetime.now(timezone.utc)
                proposal.execution_tx_hash = tx_hash
                
                # Remove from execution queue
                if proposal_id in self.execution_queue:
                    self.execution_queue.remove(proposal_id)
                
                await self._log_event("proposal_executed", {
                    "proposal_id": proposal_id,
                    "executor": executor,
                    "tx_hash": tx_hash
                })
            else:
                await self._log_event("proposal_execution_failed", {
                    "proposal_id": proposal_id,
                    "executor": executor
                })
            
            await self._store_proposal(proposal)
            return success
            
        except Exception as e:
            await self._log_event("proposal_execution_error", {
                "proposal_id": proposal_id,
                "executor": executor,
                "error": str(e)
            })
            return False
    
    async def cancel_proposal(self, proposal_id: str, canceller: str) -> bool:
        """Cancel a pending or queued proposal"""
        
        if proposal_id not in self.active_proposals:
            return False
        
        proposal = self.active_proposals[proposal_id]
        
        if proposal.status in [TimelockStatus.EXECUTED, TimelockStatus.CANCELLED, TimelockStatus.EXPIRED]:
            return False
        
        proposal.status = TimelockStatus.CANCELLED
        proposal.cancelled_at = datetime.now(timezone.utc)
        
        # Remove from execution queue
        if proposal_id in self.execution_queue:
            self.execution_queue.remove(proposal_id)
        
        await self._store_proposal(proposal)
        
        await self._log_event("proposal_cancelled", {
            "proposal_id": proposal_id,
            "canceller": canceller
        })
        
        return True
    
    async def get_proposal(self, proposal_id: str) -> Optional[TimelockProposal]:
        """Get proposal by ID"""
        return self.active_proposals.get(proposal_id)
    
    async def list_proposals(
        self,
        status: Optional[TimelockStatus] = None,
        proposal_type: Optional[ProposalType] = None,
        proposer: Optional[str] = None,
        limit: int = 100
    ) -> List[TimelockProposal]:
        """List proposals with optional filters"""
        
        proposals = list(self.active_proposals.values())
        
        if status:
            proposals = [p for p in proposals if p.status == status]
        
        if proposal_type:
            proposals = [p for p in proposals if p.proposal_type == proposal_type]
        
        if proposer:
            proposals = [p for p in proposals if p.proposer == proposer]
        
        # Sort by creation time (newest first)
        proposals.sort(key=lambda p: p.created_at, reverse=True)
        
        return proposals[:limit]
    
    async def get_executable_proposals(self) -> List[TimelockProposal]:
        """Get all proposals ready for execution"""
        executable = []
        
        for proposal in self.active_proposals.values():
            if proposal.is_executable() and not proposal.is_expired():
                executable.append(proposal)
        
        return executable
    
    async def _setup_database(self) -> None:
        """Setup database collections and indexes"""
        
        # Create collections
        collections = await self.db.list_collection_names()
        
        if "timelock_proposals" not in collections:
            await self.db.create_collection("timelock_proposals")
        
        if "timelock_events" not in collections:
            await self.db.create_collection("timelock_events")
        
        # Create indexes
        await self.db.timelock_proposals.create_index("status")
        await self.db.timelock_proposals.create_index("proposal_type")
        await self.db.timelock_proposals.create_index("proposer")
        await self.db.timelock_proposals.create_index("executable_at")
        await self.db.timelock_proposals.create_index("created_at")
        
        await self.db.timelock_events.create_index("event_type")
        await self.db.timelock_events.create_index("timestamp")
        await self.db.timelock_events.create_index("proposal_id")
    
    async def _load_active_proposals(self) -> None:
        """Load active proposals from database"""
        
        cursor = self.db.timelock_proposals.find({
            "status": {"$in": ["pending", "queued", "executable"]}
        })
        
        async for doc in cursor:
            proposal = self._proposal_from_dict(doc)
            self.active_proposals[proposal.proposal_id] = proposal
            
            if proposal.status == TimelockStatus.QUEUED:
                self.execution_queue.append(proposal.proposal_id)
    
    async def _store_proposal(self, proposal: TimelockProposal) -> None:
        """Store proposal in database"""
        await self.db.timelock_proposals.replace_one(
            {"_id": proposal.proposal_id},
            proposal.to_dict(),
            upsert=True
        )
    
    async def _execution_loop(self) -> None:
        """Background task to process execution queue"""
        
        while self.is_running:
            try:
                # Check for executable proposals
                executable_proposals = await self.get_executable_proposals()
                
                for proposal in executable_proposals:
                    if proposal.status == TimelockStatus.QUEUED:
                        proposal.status = TimelockStatus.EXECUTABLE
                        await self._store_proposal(proposal)
                        
                        await self._log_event("proposal_executable", {
                            "proposal_id": proposal.proposal_id,
                            "executable_at": proposal.executable_at.isoformat()
                        })
                
                # Check for expired proposals
                for proposal in list(self.active_proposals.values()):
                    if proposal.is_expired() and proposal.status == TimelockStatus.EXECUTABLE:
                        proposal.status = TimelockStatus.EXPIRED
                        await self._store_proposal(proposal)
                        
                        if proposal.proposal_id in self.execution_queue:
                            self.execution_queue.remove(proposal.proposal_id)
                        
                        await self._log_event("proposal_expired", {
                            "proposal_id": proposal.proposal_id
                        })
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                await self._log_event("execution_loop_error", {"error": str(e)})
                await asyncio.sleep(60)
    
    async def _monitoring_loop(self) -> None:
        """Background task for system monitoring"""
        
        while self.is_running:
            try:
                # Log system stats
                stats = {
                    "active_proposals": len(self.active_proposals),
                    "execution_queue": len(self.execution_queue),
                    "executable_proposals": len(await self.get_executable_proposals())
                }
                
                await self._log_event("system_stats", stats)
                await asyncio.sleep(300)  # Log every 5 minutes
                
            except Exception as e:
                await self._log_event("monitoring_loop_error", {"error": str(e)})
                await asyncio.sleep(300)
    
    async def _execute_proposal_logic(self, proposal: TimelockProposal) -> bool:
        """Execute the actual proposal logic"""
        
        try:
            if proposal.proposal_type == ProposalType.PARAMETER_CHANGE:
                return await self._execute_parameter_change(proposal)
            elif proposal.proposal_type == ProposalType.CONTRACT_UPGRADE:
                return await self._execute_contract_upgrade(proposal)
            elif proposal.proposal_type == ProposalType.EMERGENCY_SHUTDOWN:
                return await self._execute_emergency_shutdown(proposal)
            elif proposal.proposal_type == ProposalType.KEY_ROTATION:
                return await self._execute_key_rotation(proposal)
            elif proposal.proposal_type == ProposalType.NODE_PROVISIONING:
                return await self._execute_node_provisioning(proposal)
            elif proposal.proposal_type == ProposalType.POLICY_UPDATE:
                return await self._execute_policy_update(proposal)
            elif proposal.proposal_type == ProposalType.FEE_ADJUSTMENT:
                return await self._execute_fee_adjustment(proposal)
            elif proposal.proposal_type == ProposalType.CONSENSUS_CHANGE:
                return await self._execute_consensus_change(proposal)
            else:
                return False
                
        except Exception as e:
            await self._log_event("proposal_logic_error", {
                "proposal_id": proposal.proposal_id,
                "error": str(e)
            })
            return False
    
    async def _execute_parameter_change(self, proposal: TimelockProposal) -> bool:
        """Execute parameter change proposal"""
        # Implementation would depend on specific parameter being changed
        await self._log_event("parameter_change_executed", {
            "proposal_id": proposal.proposal_id,
            "parameters": proposal.parameters
        })
        return True
    
    async def _execute_contract_upgrade(self, proposal: TimelockProposal) -> bool:
        """Execute contract upgrade proposal"""
        # Implementation would handle contract upgrades
        await self._log_event("contract_upgrade_executed", {
            "proposal_id": proposal.proposal_id,
            "target_contract": proposal.target_contract
        })
        return True
    
    async def _execute_emergency_shutdown(self, proposal: TimelockProposal) -> bool:
        """Execute emergency shutdown proposal"""
        # Implementation would handle emergency shutdown
        await self._log_event("emergency_shutdown_executed", {
            "proposal_id": proposal.proposal_id
        })
        return True
    
    async def _execute_key_rotation(self, proposal: TimelockProposal) -> bool:
        """Execute key rotation proposal"""
        # Implementation would handle key rotation
        await self._log_event("key_rotation_executed", {
            "proposal_id": proposal.proposal_id
        })
        return True
    
    async def _execute_node_provisioning(self, proposal: TimelockProposal) -> bool:
        """Execute node provisioning proposal"""
        # Implementation would handle node provisioning
        await self._log_event("node_provisioning_executed", {
            "proposal_id": proposal.proposal_id
        })
        return True
    
    async def _execute_policy_update(self, proposal: TimelockProposal) -> bool:
        """Execute policy update proposal"""
        # Implementation would handle policy updates
        await self._log_event("policy_update_executed", {
            "proposal_id": proposal.proposal_id
        })
        return True
    
    async def _execute_fee_adjustment(self, proposal: TimelockProposal) -> bool:
        """Execute fee adjustment proposal"""
        # Implementation would handle fee adjustments
        await self._log_event("fee_adjustment_executed", {
            "proposal_id": proposal.proposal_id
        })
        return True
    
    async def _execute_consensus_change(self, proposal: TimelockProposal) -> bool:
        """Execute consensus change proposal"""
        # Implementation would handle consensus changes
        await self._log_event("consensus_change_executed", {
            "proposal_id": proposal.proposal_id
        })
        return True
    
    def _get_delay_for_level(self, execution_level: ExecutionLevel) -> int:
        """Get delay seconds for execution level"""
        delays = {
            ExecutionLevel.NORMAL: 86400,    # 24 hours
            ExecutionLevel.URGENT: 14400,    # 4 hours
            ExecutionLevel.EMERGENCY: 3600,  # 1 hour
            ExecutionLevel.IMMEDIATE: 0      # No delay
        }
        return delays.get(execution_level, 86400)
    
    def _proposal_from_dict(self, data: Dict[str, Any]) -> TimelockProposal:
        """Create proposal from dictionary"""
        return TimelockProposal(
            proposal_id=data["_id"],
            proposal_type=ProposalType(data["type"]),
            title=data["title"],
            description=data["description"],
            proposer=data["proposer"],
            target_contract=data.get("target_contract"),
            target_function=data.get("target_function"),
            parameters=data.get("parameters", {}),
            execution_level=ExecutionLevel(data.get("execution_level", "normal")),
            delay_seconds=data.get("delay_seconds", 86400),
            grace_period_seconds=data.get("grace_period_seconds", 604800),
            status=TimelockStatus(data.get("status", "pending")),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            queued_at=data.get("queued_at"),
            executable_at=data.get("executable_at"),
            executed_at=data.get("executed_at"),
            cancelled_at=data.get("cancelled_at"),
            executor=data.get("executor"),
            execution_tx_hash=data.get("execution_tx_hash"),
            required_signatures=data.get("required_signatures", 1),
            signatures=data.get("signatures", {}),
            metadata=data.get("metadata", {})
        )
    
    async def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log governance event"""
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc),
            "data": data
        }
        
        await self.db.timelock_events.insert_one(event)
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get timelock system statistics"""
        return {
            "active_proposals": len(self.active_proposals),
            "execution_queue": len(self.execution_queue),
            "executable_proposals": len(await self.get_executable_proposals()),
            "proposals_by_status": {
                status.value: len([p for p in self.active_proposals.values() if p.status == status])
                for status in TimelockStatus
            },
            "proposals_by_type": {
                ptype.value: len([p for p in self.active_proposals.values() if p.proposal_type == ptype])
                for ptype in ProposalType
            }
        }


# Global timelock instance
_timelock_instance: Optional[TimelockGovernance] = None


def get_timelock_governance() -> Optional[TimelockGovernance]:
    """Get global timelock governance instance"""
    return _timelock_instance


def create_timelock_governance(
    db: AsyncIOMotorDatabase,
    config: Optional[TimelockConfig] = None,
    output_dir: str = "/data/timelock"
) -> TimelockGovernance:
    """Create timelock governance instance"""
    global _timelock_instance
    _timelock_instance = TimelockGovernance(db, config, output_dir)
    return _timelock_instance


async def cleanup_timelock_governance():
    """Cleanup timelock governance instance"""
    global _timelock_instance
    if _timelock_instance:
        await _timelock_instance.stop()
        _timelock_instance = None


# Pydantic models for API
class CreateProposalRequest(BaseModel):
    proposal_type: ProposalType
    title: str
    description: str
    proposer: str
    target_contract: Optional[str] = None
    target_function: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    execution_level: ExecutionLevel = ExecutionLevel.NORMAL
    delay_seconds: Optional[int] = None


class ExecuteProposalRequest(BaseModel):
    proposal_id: str
    executor: str
    tx_hash: Optional[str] = None


class CancelProposalRequest(BaseModel):
    proposal_id: str
    canceller: str


if __name__ == "__main__":
    async def test_timelock():
        """Test timelock functionality"""
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Connect to MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.lucid
        
        # Create timelock governance
        timelock = create_timelock_governance(db)
        
        try:
            # Start system
            await timelock.start()
            
            # Create test proposal
            proposal_id = await timelock.create_proposal(
                proposal_type=ProposalType.PARAMETER_CHANGE,
                title="Test Parameter Change",
                description="Test proposal for parameter change",
                proposer="test_proposer",
                execution_level=ExecutionLevel.NORMAL
            )
            
            print(f"Created proposal: {proposal_id}")
            
            # Queue proposal
            await timelock.queue_proposal(proposal_id, "test_executor")
            print("Proposal queued")
            
            # Get system stats
            stats = await timelock.get_system_stats()
            print(f"System stats: {stats}")
            
        finally:
            await timelock.stop()
            client.close()
    
    asyncio.run(test_timelock())
