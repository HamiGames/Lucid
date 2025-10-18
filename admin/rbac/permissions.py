#!/usr/bin/env python3
"""
Lucid Admin Interface - RBAC Permissions
Step 24: Admin Container & Integration

Permission definitions and mappings for the Lucid admin interface.
"""

from enum import Enum
from typing import Dict, Set, List
from dataclasses import dataclass


class PermissionType(Enum):
    """Permission types"""
    SYSTEM = "system"
    USER = "user"
    SESSION = "session"
    NODE = "node"
    BLOCKCHAIN = "blockchain"
    AUDIT = "audit"
    EMERGENCY = "emergency"


@dataclass
class Permission:
    """Permission definition"""
    name: str
    display_name: str
    description: str
    permission_type: PermissionType
    resource: str
    action: str
    metadata: Dict[str, any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# Permission definitions
PERMISSIONS = {
    # System permissions
    "system.view": Permission(
        name="system.view",
        display_name="View System Information",
        description="View system status and information",
        permission_type=PermissionType.SYSTEM,
        resource="system",
        action="view"
    ),
    
    "system.configure": Permission(
        name="system.configure",
        display_name="Configure System",
        description="Configure system settings and parameters",
        permission_type=PermissionType.SYSTEM,
        resource="system",
        action="configure"
    ),
    
    "system.shutdown": Permission(
        name="system.shutdown",
        display_name="Shutdown System",
        description="Shutdown the system",
        permission_type=PermissionType.SYSTEM,
        resource="system",
        action="shutdown"
    ),
    
    "system.restart": Permission(
        name="system.restart",
        display_name="Restart System",
        description="Restart the system",
        permission_type=PermissionType.SYSTEM,
        resource="system",
        action="restart"
    ),
    
    # User management permissions
    "users.view": Permission(
        name="users.view",
        display_name="View Users",
        description="View user information and list",
        permission_type=PermissionType.USER,
        resource="users",
        action="view"
    ),
    
    "users.create": Permission(
        name="users.create",
        display_name="Create Users",
        description="Create new users",
        permission_type=PermissionType.USER,
        resource="users",
        action="create"
    ),
    
    "users.edit": Permission(
        name="users.edit",
        display_name="Edit Users",
        description="Edit user information",
        permission_type=PermissionType.USER,
        resource="users",
        action="edit"
    ),
    
    "users.delete": Permission(
        name="users.delete",
        display_name="Delete Users",
        description="Delete users",
        permission_type=PermissionType.USER,
        resource="users",
        action="delete"
    ),
    
    "users.manage_roles": Permission(
        name="users.manage_roles",
        display_name="Manage User Roles",
        description="Assign and revoke user roles",
        permission_type=PermissionType.USER,
        resource="users",
        action="manage_roles"
    ),
    
    # Session management permissions
    "sessions.view": Permission(
        name="sessions.view",
        display_name="View Sessions",
        description="View session information and list",
        permission_type=PermissionType.SESSION,
        resource="sessions",
        action="view"
    ),
    
    "sessions.terminate": Permission(
        name="sessions.terminate",
        display_name="Terminate Sessions",
        description="Terminate individual sessions",
        permission_type=PermissionType.SESSION,
        resource="sessions",
        action="terminate"
    ),
    
    "sessions.bulk_terminate": Permission(
        name="sessions.bulk_terminate",
        display_name="Bulk Terminate Sessions",
        description="Terminate multiple sessions at once",
        permission_type=PermissionType.SESSION,
        resource="sessions",
        action="bulk_terminate"
    ),
    
    "sessions.monitor": Permission(
        name="sessions.monitor",
        display_name="Monitor Sessions",
        description="Monitor session activity and performance",
        permission_type=PermissionType.SESSION,
        resource="sessions",
        action="monitor"
    ),
    
    # Node management permissions
    "nodes.view": Permission(
        name="nodes.view",
        display_name="View Nodes",
        description="View node information and list",
        permission_type=PermissionType.NODE,
        resource="nodes",
        action="view"
    ),
    
    "nodes.manage": Permission(
        name="nodes.manage",
        display_name="Manage Nodes",
        description="Manage node operations and settings",
        permission_type=PermissionType.NODE,
        resource="nodes",
        action="manage"
    ),
    
    "nodes.maintenance": Permission(
        name="nodes.maintenance",
        display_name="Node Maintenance",
        description="Perform node maintenance operations",
        permission_type=PermissionType.NODE,
        resource="nodes",
        action="maintenance"
    ),
    
    "nodes.payouts": Permission(
        name="nodes.payouts",
        display_name="Manage Node Payouts",
        description="Manage node payout operations",
        permission_type=PermissionType.NODE,
        resource="nodes",
        action="payouts"
    ),
    
    # Blockchain permissions
    "blockchain.view": Permission(
        name="blockchain.view",
        display_name="View Blockchain",
        description="View blockchain status and information",
        permission_type=PermissionType.BLOCKCHAIN,
        resource="blockchain",
        action="view"
    ),
    
    "blockchain.anchor": Permission(
        name="blockchain.anchor",
        display_name="Anchor to Blockchain",
        description="Anchor sessions to blockchain",
        permission_type=PermissionType.BLOCKCHAIN,
        resource="blockchain",
        action="anchor"
    ),
    
    "blockchain.pause": Permission(
        name="blockchain.pause",
        display_name="Pause Blockchain",
        description="Pause blockchain operations",
        permission_type=PermissionType.BLOCKCHAIN,
        resource="blockchain",
        action="pause"
    ),
    
    "blockchain.resume": Permission(
        name="blockchain.resume",
        display_name="Resume Blockchain",
        description="Resume blockchain operations",
        permission_type=PermissionType.BLOCKCHAIN,
        resource="blockchain",
        action="resume"
    ),
    
    # Audit permissions
    "audit.view": Permission(
        name="audit.view",
        display_name="View Audit Logs",
        description="View audit logs and history",
        permission_type=PermissionType.AUDIT,
        resource="audit",
        action="view"
    ),
    
    "audit.export": Permission(
        name="audit.export",
        display_name="Export Audit Logs",
        description="Export audit logs in various formats",
        permission_type=PermissionType.AUDIT,
        resource="audit",
        action="export"
    ),
    
    "audit.retention": Permission(
        name="audit.retention",
        display_name="Manage Audit Retention",
        description="Manage audit log retention policies",
        permission_type=PermissionType.AUDIT,
        resource="audit",
        action="retention"
    ),
    
    # Emergency permissions
    "emergency.lockdown": Permission(
        name="emergency.lockdown",
        display_name="System Lockdown",
        description="Execute system lockdown procedures",
        permission_type=PermissionType.EMERGENCY,
        resource="emergency",
        action="lockdown"
    ),
    
    "emergency.shutdown": Permission(
        name="emergency.shutdown",
        display_name="Emergency Shutdown",
        description="Execute emergency shutdown procedures",
        permission_type=PermissionType.EMERGENCY,
        resource="emergency",
        action="shutdown"
    ),
    
    "emergency.notify": Permission(
        name="emergency.notify",
        display_name="Emergency Notifications",
        description="Send emergency notifications",
        permission_type=PermissionType.EMERGENCY,
        resource="emergency",
        action="notify"
    )
}


def get_permission_mapping() -> Dict[str, Permission]:
    """Get permission mapping"""
    return PERMISSIONS


def get_permission(name: str) -> Permission:
    """Get permission by name"""
    return PERMISSIONS.get(name)


def get_all_permissions() -> List[Permission]:
    """Get all permissions"""
    return list(PERMISSIONS.values())


def get_permissions_by_type(permission_type: PermissionType) -> List[Permission]:
    """Get permissions by type"""
    return [perm for perm in PERMISSIONS.values() if perm.permission_type == permission_type]


def get_permissions_by_resource(resource: str) -> List[Permission]:
    """Get permissions by resource"""
    return [perm for perm in PERMISSIONS.values() if perm.resource == resource]


def get_permissions_by_action(action: str) -> List[Permission]:
    """Get permissions by action"""
    return [perm for perm in PERMISSIONS.values() if perm.action == action]


def permission_exists(name: str) -> bool:
    """Check if permission exists"""
    return name in PERMISSIONS


def get_permission_hierarchy() -> Dict[str, List[str]]:
    """Get permission hierarchy (if any)"""
    # For now, no hierarchy - all permissions are independent
    return {}


def validate_permission_name(name: str) -> bool:
    """Validate permission name format"""
    # Permission names should be in format: resource.action
    parts = name.split(".")
    return len(parts) == 2 and all(part.isalnum() or "_" in part for part in parts)


def get_permission_dependencies(name: str) -> List[str]:
    """Get permission dependencies"""
    # For now, no dependencies
    return []


def get_permission_dependents(name: str) -> List[str]:
    """Get permissions that depend on this permission"""
    # For now, no dependencies
    return []


def get_permission_stats() -> Dict[str, int]:
    """Get permission statistics"""
    stats = {
        "total_permissions": len(PERMISSIONS),
        "by_type": {},
        "by_resource": {},
        "by_action": {}
    }
    
    # Count by type
    for perm in PERMISSIONS.values():
        perm_type = perm.permission_type.value
        stats["by_type"][perm_type] = stats["by_type"].get(perm_type, 0) + 1
    
    # Count by resource
    for perm in PERMISSIONS.values():
        resource = perm.resource
        stats["by_resource"][resource] = stats["by_resource"].get(resource, 0) + 1
    
    # Count by action
    for perm in PERMISSIONS.values():
        action = perm.action
        stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
    
    return stats
