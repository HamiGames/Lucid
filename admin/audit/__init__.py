# Lucid Admin Interface - Audit Package
# Step 24: Admin Container & Integration
#
# Audit logging system for the Lucid admin interface.
# Provides comprehensive audit trail for all administrative actions.

import admin.utils.logging as logging

from admin.audit.logger import (
    AuditLogger, 
    get_audit_logger,
    AuditEventType as LoggerEventType,
    AuditEventSeverity,
    AuditEventStatus,
    AuditEvent as LoggerAuditEvent
)
from admin.audit.events import AuditEvent, AuditEventType, AuditSeverity

logger = logging.get_logger(__name__)
setup_logging= logging.setup_logging(__name__)

__all__ = [
    "AuditLogger",
    "get_audit_logger",
    "AuditEvent", 
    "AuditEventType",
    "AuditSeverity",
    "AuditEventSeverity",
    "AuditEventStatus",
    "LoggerEventType", "LoggerAuditEvent",
    "logger", "setup_logging",
]
