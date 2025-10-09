# Path: RDP/security/__init__.py
# Lucid RDP Security Module - Comprehensive security framework
# Implements R-MUST-003: Remote Desktop Host Support with security controls
# LUCID-STRICT Layer 2 Service Integration

"""
Lucid RDP Security Module

This module provides comprehensive security functionality for RDP sessions including:
- Access control and authorization
- Session validation and integrity checking
- Trust management and security policies
- Security event monitoring and logging

Key Components:
- AccessController: Manages access control rules and permissions
- SessionValidator: Validates session integrity and security
- TrustController: Manages trust relationships and security policies
"""

from .access_controller import (
    AccessController,
    AccessLevel,
    ResourceType,
    PermissionType,
    SecurityPolicy,
    AccessRule,
    AccessRequest,
    AccessDecision,
    SecurityContext,
    SessionAccess,
    get_access_controller,
    create_access_controller,
    start_access_controller,
    stop_access_controller
)

from .session_validator import (
    SessionValidator,
    ValidationStatus,
    ValidationLevel,
    SessionRiskLevel,
    ValidationType,
    SessionValidationRule,
    SessionValidationResult,
    SessionSecurityContext,
    SessionIntegrityCheck,
    get_session_validator,
    create_session_validator,
    start_session_validator,
    stop_session_validator
)

from .trust_controller import (
    TrustController,
    TrustLevel,
    EntityType,
    TrustEvent,
    SecurityPolicy as TrustSecurityPolicy,
    TrustEntity,
    TrustEvent as TrustEventRecord,
    SecurityPolicy as TrustPolicy,
    TrustDecision,
    register_trusted_entity,
    evaluate_entity_trust,
    create_trusted_session,
    record_trust_event,
    get_trust_statistics
)

__all__ = [
    # Access Controller
    "AccessController",
    "AccessLevel", 
    "ResourceType",
    "PermissionType",
    "SecurityPolicy",
    "AccessRule",
    "AccessRequest", 
    "AccessDecision",
    "SecurityContext",
    "SessionAccess",
    "get_access_controller",
    "create_access_controller",
    "start_access_controller",
    "stop_access_controller",
    
    # Session Validator
    "SessionValidator",
    "ValidationStatus",
    "ValidationLevel",
    "SessionRiskLevel",
    "ValidationType",
    "SessionValidationRule",
    "SessionValidationResult",
    "SessionSecurityContext",
    "SessionIntegrityCheck",
    "get_session_validator",
    "create_session_validator",
    "start_session_validator",
    "stop_session_validator",
    
    # Trust Controller
    "TrustController",
    "TrustLevel",
    "EntityType",
    "TrustEvent",
    "TrustSecurityPolicy",
    "TrustEntity",
    "TrustEventRecord",
    "TrustPolicy",
    "TrustDecision",
    "register_trusted_entity",
    "evaluate_entity_trust",
    "create_trusted_session",
    "record_trust_event",
    "get_trust_statistics"
]

# Version information
__version__ = "1.0.0"
__author__ = "Lucid RDP Security Team"
__description__ = "Comprehensive security framework for Lucid RDP sessions"

# Convenience functions for quick setup
def create_security_manager():
    """Create and return a configured security manager with all components"""
    access_controller = create_access_controller()
    session_validator = create_session_validator()
    trust_controller = TrustController()
    
    return {
        "access_controller": access_controller,
        "session_validator": session_validator,
        "trust_controller": trust_controller
    }

async def start_security_services():
    """Start all security services"""
    await start_access_controller()
    await start_session_validator()
    # TrustController doesn't have a start method, it's initialized directly

async def stop_security_services():
    """Stop all security services"""
    await stop_access_controller()
    await stop_session_validator()
    # TrustController doesn't have a stop method

# Export convenience functions
__all__.extend([
    "create_security_manager",
    "start_security_services", 
    "stop_security_services"
])
