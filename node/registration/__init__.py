# node/registration/__init__.py
# Lucid Node Registration Module
# LUCID-STRICT Layer 1 Core Infrastructure

"""
Registration module for Lucid node operations.

This module provides:
- Node registration protocol
- Registration challenges and verification
- Stake validation and proof systems
- Node onboarding and approval

Core Components:
- NodeRegistrationProtocol: Main registration system
- NodeRegistration: Registration record
- RegistrationChallenge: Challenge verification
- ChallengeType: Types of challenges
"""

from .node_registration_protocol import (
    NodeRegistrationProtocol,
    NodeRegistration,
    RegistrationStatus,
    RegistrationChallenge,
    ChallengeType,
    get_registration_protocol,
    create_registration_protocol,
    cleanup_registration_protocol
)

__all__ = [
    'NodeRegistrationProtocol',
    'NodeRegistration',
    'RegistrationStatus',
    'RegistrationChallenge',
    'ChallengeType',
    'get_registration_protocol',
    'create_registration_protocol',
    'cleanup_registration_protocol'
]
