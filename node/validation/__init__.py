# node/validation/__init__.py
# Lucid Node Validation Module
# LUCID-STRICT Layer 1 Core Infrastructure

"""
Validation module for Lucid node operations.

This module provides:
- Proof of Operational Tasks (PoOT) validation
- Token ownership proof verification
- Stake validation and fraud detection
- Validation statistics and monitoring

Core Components:
- NodePootValidation: Main validation system
- TokenOwnershipChallenge: Ownership challenges
- TokenOwnershipProof: Ownership proofs
- StakeValidation: Stake verification
"""

from .node_poot_validations import (
    NodePootValidation,
    TokenOwnershipChallenge,
    TokenOwnershipProof,
    ProofType,
    ValidationStatus,
    StakeValidation,
    FraudDetectionEvent,
    FraudRisk,
    ValidationStats,
    get_node_poot_validation,
    create_node_poot_validation,
    cleanup_node_poot_validation
)

__all__ = [
    'NodePootValidation',
    'TokenOwnershipChallenge',
    'TokenOwnershipProof',
    'ProofType',
    'ValidationStatus',
    'StakeValidation',
    'FraudDetectionEvent',
    'FraudRisk',
    'ValidationStats',
    'get_node_poot_validation',
    'create_node_poot_validation',
    'cleanup_node_poot_validation'
]
