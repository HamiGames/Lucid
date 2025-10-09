"""
Lucid RDP Blockchain Governance Module

This module provides governance functionality for the Lucid RDP blockchain system,
including timelock mechanisms, proposal management, and execution controls.

Components:
- timelock.py: Timelock governance system for secure proposal execution
- TimelockGovernance: Main governance controller class
- TimelockProposal: Proposal data structure
- Various proposal types and execution levels

Author: Lucid RDP Team
Version: 1.0.0
"""

from .timelock import (
    TimelockGovernance,
    TimelockProposal,
    TimelockConfig,
    TimelockStatus,
    ProposalType,
    ExecutionLevel,
    get_timelock_governance,
    create_timelock_governance,
    cleanup_timelock_governance,
    CreateProposalRequest,
    ExecuteProposalRequest,
    CancelProposalRequest
)

__all__ = [
    "TimelockGovernance",
    "TimelockProposal", 
    "TimelockConfig",
    "TimelockStatus",
    "ProposalType",
    "ExecutionLevel",
    "get_timelock_governance",
    "create_timelock_governance",
    "cleanup_timelock_governance",
    "CreateProposalRequest",
    "ExecuteProposalRequest",
    "CancelProposalRequest"
]

__version__ = "1.0.0"
__author__ = "Lucid RDP Team"
