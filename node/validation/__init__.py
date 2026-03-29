# node/validation/__init__.py
# Lucid Node Validation Module
# LUCID-STRICT Layer 1 Core Infrastructure

"""
File: /app/node/validation/__init__.py
x-lucid-file-path: /app/node/validation/__init__.py
x-lucid-file-type: python

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

from ..validation.node_poot_validations import (
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
from ..validation.work_credits import (
    WorkCreditsCalculator,
    WorkCreditValidationRequest,
    WorkCreditValidationResponse,
    WorkCreditValidationStatus,
    WorkCreditPreferences,
    WorkCreditStats,
    WorkCreditValidationReport,
    WorkCreditVerification,
    WorkCreditReport,
    WorkCreditValidationSettings,
    WorkCreditHistory,
    WorkCreditRequest,
    WorkCreditResponse,
    WorkCreditSettings, WorkCredit
)
from ..validation.peer_discovery import (
    PeerDiscovery, PeerInfo, DatabaseSearchParameters
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
    'WorkCreditsCalculator',
    'WorkCreditValidationRequest',
    'WorkCreditValidationResponse',
    'WorkCreditValidationStatus',
    'WorkCreditPreferences',
    'WorkCreditStats',
    'WorkCreditValidationReport',
    'WorkCreditVerification',
    'WorkCreditReport',
    'WorkCreditValidationSettings',
    'WorkCreditHistory',
    'WorkCreditRequest',
    'WorkCreditResponse',
    'WorkCreditSettings',
    'WorkCredit',
    'PeerDiscovery',
    'PeerInfo',
    'DatabaseSearchParameters', 
    'get_node_poot_validation',
    'create_node_poot_validation'
]
