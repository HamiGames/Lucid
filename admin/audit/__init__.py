"""
File: /app/admin/audit/__init__.py
x-lucid-file-path: /app/admin/audit/__init__.py
x-lucid-file-type: python

Lucid Admin Interface - Audit Package
 Step 24: Admin Container & Integration
 Audit logging system for the Lucid admin interface.
 Provides comprehensive audit trail for all administrative actions.
"""
from .events import dataclass, AuditEventType, AuditSeverity, AuditEvent, create_audit_event, get_event_by_action
from ..utils.logging import get_logger
from .logger import AuditLogger, get_audit_logger

__all__ =[
    'dataclass',
    'AuditEventType', 'AuditSeverity',
    'AuditEvent',
    'create_audit_event',
    'get_event_by_action',
    'get_logger',
    'AuditLogger',
    'get_audit_logger'
]
