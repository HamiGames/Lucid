#!/usr/bin/env python3
"""
Lucid Admin Interface - Audit Events
Step 24: Admin Container & Integration

Audit event definitions and types for the Lucid admin interface.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


class AuditEventType(Enum):
    """Audit event types"""
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"
    EMERGENCY_ACTION = "emergency_action"
    ERROR = "error"
    CONFIGURATION_CHANGE = "configuration_change"
    DATA_ACCESS = "data_access"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"


class AuditSeverity(Enum):
    """Audit severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event model"""
    event_type: AuditEventType
    severity: AuditSeverity
    action: str
    resource: str
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


# Predefined audit events
class AuditEvents:
    """Predefined audit events"""
    
    # User Management Events
    USER_LOGIN = AuditEvent(
        event_type=AuditEventType.AUTHENTICATION,
        severity=AuditSeverity.INFO,
        action="user_login",
        resource="authentication"
    )
    
    USER_LOGOUT = AuditEvent(
        event_type=AuditEventType.AUTHENTICATION,
        severity=AuditSeverity.INFO,
        action="user_logout",
        resource="authentication"
    )
    
    USER_CREATED = AuditEvent(
        event_type=AuditEventType.USER_ACTION,
        severity=AuditSeverity.INFO,
        action="user_created",
        resource="user_management"
    )
    
    USER_UPDATED = AuditEvent(
        event_type=AuditEventType.USER_ACTION,
        severity=AuditSeverity.INFO,
        action="user_updated",
        resource="user_management"
    )
    
    USER_DELETED = AuditEvent(
        event_type=AuditEventType.USER_ACTION,
        severity=AuditSeverity.WARNING,
        action="user_deleted",
        resource="user_management"
    )
    
    # Session Management Events
    SESSION_CREATED = AuditEvent(
        event_type=AuditEventType.SYSTEM_EVENT,
        severity=AuditSeverity.INFO,
        action="session_created",
        resource="session_management"
    )
    
    SESSION_TERMINATED = AuditEvent(
        event_type=AuditEventType.SYSTEM_EVENT,
        severity=AuditSeverity.WARNING,
        action="session_terminated",
        resource="session_management"
    )
    
    SESSION_BULK_TERMINATED = AuditEvent(
        event_type=AuditEventType.SYSTEM_EVENT,
        severity=AuditSeverity.WARNING,
        action="session_bulk_terminated",
        resource="session_management"
    )
    
    # Node Management Events
    NODE_REGISTERED = AuditEvent(
        event_type=AuditEventType.SYSTEM_EVENT,
        severity=AuditSeverity.INFO,
        action="node_registered",
        resource="node_management"
    )
    
    NODE_DEREGISTERED = AuditEvent(
        event_type=AuditEventType.SYSTEM_EVENT,
        severity=AuditSeverity.WARNING,
        action="node_deregistered",
        resource="node_management"
    )
    
    NODE_MAINTENANCE = AuditEvent(
        event_type=AuditEventType.SYSTEM_EVENT,
        severity=AuditSeverity.INFO,
        action="node_maintenance",
        resource="node_management"
    )
    
    # Blockchain Events
    BLOCKCHAIN_ANCHOR = AuditEvent(
        event_type=AuditEventType.SYSTEM_EVENT,
        severity=AuditSeverity.INFO,
        action="blockchain_anchor",
        resource="blockchain"
    )
    
    BLOCKCHAIN_PAUSE = AuditEvent(
        event_type=AuditEventType.SYSTEM_EVENT,
        severity=AuditSeverity.WARNING,
        action="blockchain_pause",
        resource="blockchain"
    )
    
    BLOCKCHAIN_RESUME = AuditEvent(
        event_type=AuditEventType.SYSTEM_EVENT,
        severity=AuditSeverity.INFO,
        action="blockchain_resume",
        resource="blockchain"
    )
    
    # Security Events
    LOGIN_FAILED = AuditEvent(
        event_type=AuditEventType.SECURITY_EVENT,
        severity=AuditSeverity.WARNING,
        action="login_failed",
        resource="authentication"
    )
    
    PERMISSION_DENIED = AuditEvent(
        event_type=AuditEventType.SECURITY_EVENT,
        severity=AuditSeverity.WARNING,
        action="permission_denied",
        resource="authorization"
    )
    
    SUSPICIOUS_ACTIVITY = AuditEvent(
        event_type=AuditEventType.SECURITY_EVENT,
        severity=AuditSeverity.ERROR,
        action="suspicious_activity",
        resource="security"
    )
    
    # Emergency Events
    EMERGENCY_LOCKDOWN = AuditEvent(
        event_type=AuditEventType.EMERGENCY_ACTION,
        severity=AuditSeverity.CRITICAL,
        action="emergency_lockdown",
        resource="emergency_controls"
    )
    
    EMERGENCY_SHUTDOWN = AuditEvent(
        event_type=AuditEventType.EMERGENCY_ACTION,
        severity=AuditSeverity.CRITICAL,
        action="emergency_shutdown",
        resource="emergency_controls"
    )
    
    EMERGENCY_RESOLVED = AuditEvent(
        event_type=AuditEventType.EMERGENCY_ACTION,
        severity=AuditSeverity.INFO,
        action="emergency_resolved",
        resource="emergency_controls"
    )
    
    # Configuration Events
    CONFIG_CHANGED = AuditEvent(
        event_type=AuditEventType.CONFIGURATION_CHANGE,
        severity=AuditSeverity.INFO,
        action="configuration_changed",
        resource="system_configuration"
    )
    
    # Data Access Events
    DATA_EXPORTED = AuditEvent(
        event_type=AuditEventType.DATA_ACCESS,
        severity=AuditSeverity.INFO,
        action="data_exported",
        resource="data_access"
    )
    
    DATA_DELETED = AuditEvent(
        event_type=AuditEventType.DATA_ACCESS,
        severity=AuditSeverity.WARNING,
        action="data_deleted",
        resource="data_access"
    )
    
    # Error Events
    SYSTEM_ERROR = AuditEvent(
        event_type=AuditEventType.ERROR,
        severity=AuditSeverity.ERROR,
        action="system_error",
        resource="system"
    )
    
    DATABASE_ERROR = AuditEvent(
        event_type=AuditEventType.ERROR,
        severity=AuditSeverity.ERROR,
        action="database_error",
        resource="database"
    )
    
    NETWORK_ERROR = AuditEvent(
        event_type=AuditEventType.ERROR,
        severity=AuditSeverity.ERROR,
        action="network_error",
        resource="network"
    )


def create_audit_event(event_type: AuditEventType, severity: AuditSeverity,
                      action: str, resource: str, details: Dict[str, Any] = None,
                      metadata: Dict[str, Any] = None) -> AuditEvent:
    """Create a custom audit event"""
    return AuditEvent(
        event_type=event_type,
        severity=severity,
        action=action,
        resource=resource,
        details=details or {},
        metadata=metadata or {}
    )


def get_event_by_action(action: str) -> Optional[AuditEvent]:
    """Get predefined event by action name"""
    events = {
        "user_login": AuditEvents.USER_LOGIN,
        "user_logout": AuditEvents.USER_LOGOUT,
        "user_created": AuditEvents.USER_CREATED,
        "user_updated": AuditEvents.USER_UPDATED,
        "user_deleted": AuditEvents.USER_DELETED,
        "session_created": AuditEvents.SESSION_CREATED,
        "session_terminated": AuditEvents.SESSION_TERMINATED,
        "session_bulk_terminated": AuditEvents.SESSION_BULK_TERMINATED,
        "node_registered": AuditEvents.NODE_REGISTERED,
        "node_deregistered": AuditEvents.NODE_DEREGISTERED,
        "node_maintenance": AuditEvents.NODE_MAINTENANCE,
        "blockchain_anchor": AuditEvents.BLOCKCHAIN_ANCHOR,
        "blockchain_pause": AuditEvents.BLOCKCHAIN_PAUSE,
        "blockchain_resume": AuditEvents.BLOCKCHAIN_RESUME,
        "login_failed": AuditEvents.LOGIN_FAILED,
        "permission_denied": AuditEvents.PERMISSION_DENIED,
        "suspicious_activity": AuditEvents.SUSPICIOUS_ACTIVITY,
        "emergency_lockdown": AuditEvents.EMERGENCY_LOCKDOWN,
        "emergency_shutdown": AuditEvents.EMERGENCY_SHUTDOWN,
        "emergency_resolved": AuditEvents.EMERGENCY_RESOLVED,
        "configuration_changed": AuditEvents.CONFIG_CHANGED,
        "data_exported": AuditEvents.DATA_EXPORTED,
        "data_deleted": AuditEvents.DATA_DELETED,
        "system_error": AuditEvents.SYSTEM_ERROR,
        "database_error": AuditEvents.DATABASE_ERROR,
        "network_error": AuditEvents.NETWORK_ERROR
    }
    
    return events.get(action)
