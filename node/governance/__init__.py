# node/governance/__init__.py
# Lucid Node Governance Module
# LUCID-STRICT Layer 1 Core Infrastructure

"""
Governance module for Lucid node operations.

This module provides:
- Node voting and governance systems
- Proposal creation and management
- Vote casting and delegation
- Governance decision tracking

Core Components:
- NodeVoteSystem: Main governance system
- GovernanceProposal: Proposal representation
- GovernanceVote: Individual votes
- VoteDelegation: Vote delegation system
"""

from .node_vote_systems import (
    NodeVoteSystem,
    GovernanceProposal,
    ProposalType,
    ProposalStatus,
    GovernanceVote,
    VoteChoice,
    VoteWeight,
    VoteDelegation,
    VoteTally,
    GovernanceComment,
    get_node_vote_system,
    create_node_vote_system,
    cleanup_node_vote_system
)

__all__ = [
    'NodeVoteSystem',
    'GovernanceProposal',
    'ProposalType',
    'ProposalStatus',
    'GovernanceVote',
    'VoteChoice',
    'VoteWeight',
    'VoteDelegation',
    'VoteTally',
    'GovernanceComment',
    'get_node_vote_system',
    'create_node_vote_system',
    'cleanup_node_vote_system'
]
