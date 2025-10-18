#!/usr/bin/env python3
"""
Lucid Admin Interface - RBAC Roles
Step 24: Admin Container & Integration

Role definitions and hierarchy for the Lucid admin interface.
"""

from enum import Enum
from typing import Dict, List, Set
from dataclasses import dataclass


class RoleType(Enum):
    """Role types"""
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass
class Role:
    """Role definition"""
    name: str
    display_name: str
    description: str
    role_type: RoleType
    permissions: Set[str]
    is_system: bool = True
    metadata: Dict[str, any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# Role definitions
ROLES = {
    "super_admin": Role(
        name="super_admin",
        display_name="Super Administrator",
        description="Full system access with all permissions",
        role_type=RoleType.SYSTEM,
        permissions={
            "system.view", "system.configure", "system.shutdown", "system.restart",
            "users.view", "users.create", "users.edit", "users.delete", "users.manage_roles",
            "sessions.view", "sessions.terminate", "sessions.bulk_terminate", "sessions.monitor",
            "nodes.view", "nodes.manage", "nodes.maintenance", "nodes.payouts",
            "blockchain.view", "blockchain.anchor", "blockchain.pause", "blockchain.resume",
            "audit.view", "audit.export", "audit.retention",
            "emergency.lockdown", "emergency.shutdown", "emergency.notify"
        },
        is_system=True
    ),
    
    "admin": Role(
        name="admin",
        display_name="Administrator",
        description="Administrative access with most permissions",
        role_type=RoleType.SYSTEM,
        permissions={
            "system.view", "system.configure",
            "users.view", "users.create", "users.edit", "users.manage_roles",
            "sessions.view", "sessions.terminate", "sessions.bulk_terminate", "sessions.monitor",
            "nodes.view", "nodes.manage", "nodes.maintenance", "nodes.payouts",
            "blockchain.view", "blockchain.anchor", "blockchain.pause", "blockchain.resume",
            "audit.view", "audit.export",
            "emergency.notify"
        },
        is_system=True
    ),
    
    "operator": Role(
        name="operator",
        display_name="Operator",
        description="Operational access for system management",
        role_type=RoleType.SYSTEM,
        permissions={
            "system.view",
            "users.view",
            "sessions.view", "sessions.terminate", "sessions.monitor",
            "nodes.view", "nodes.maintenance",
            "blockchain.view",
            "audit.view"
        },
        is_system=True
    ),
    
    "read_only": Role(
        name="read_only",
        display_name="Read Only",
        description="Read-only access for monitoring",
        role_type=RoleType.SYSTEM,
        permissions={
            "system.view",
            "users.view",
            "sessions.view", "sessions.monitor",
            "nodes.view",
            "blockchain.view",
            "audit.view"
        },
        is_system=True
    )
}


def get_role_hierarchy() -> Dict[str, List[str]]:
    """Get role hierarchy"""
    return {
        "super_admin": ["admin", "operator", "read_only"],
        "admin": ["operator", "read_only"],
        "operator": ["read_only"],
        "read_only": []
    }


def get_role(name: str) -> Role:
    """Get role by name"""
    return ROLES.get(name)


def get_all_roles() -> List[Role]:
    """Get all roles"""
    return list(ROLES.values())


def get_system_roles() -> List[Role]:
    """Get system roles"""
    return [role for role in ROLES.values() if role.is_system]


def get_custom_roles() -> List[Role]:
    """Get custom roles"""
    return [role for role in ROLES.values() if not role.is_system]


def role_exists(name: str) -> bool:
    """Check if role exists"""
    return name in ROLES


def get_role_permissions(name: str) -> Set[str]:
    """Get permissions for a role"""
    role = get_role(name)
    if role:
        return role.permissions
    return set()


def get_inherited_permissions(name: str) -> Set[str]:
    """Get inherited permissions for a role"""
    hierarchy = get_role_hierarchy()
    permissions = set()
    
    # Get direct permissions
    permissions.update(get_role_permissions(name))
    
    # Get inherited permissions
    for inherited_role in hierarchy.get(name, []):
        permissions.update(get_inherited_permissions(inherited_role))
    
    return permissions


def validate_role_hierarchy() -> bool:
    """Validate role hierarchy for circular dependencies"""
    hierarchy = get_role_hierarchy()
    visited = set()
    rec_stack = set()
    
    def has_cycle(node):
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in hierarchy.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        
        rec_stack.remove(node)
        return False
    
    for role in hierarchy:
        if role not in visited:
            if has_cycle(role):
                return False
    
    return True


def get_role_dependencies(name: str) -> List[str]:
    """Get role dependencies"""
    hierarchy = get_role_hierarchy()
    return hierarchy.get(name, [])


def get_role_dependents(name: str) -> List[str]:
    """Get roles that depend on this role"""
    hierarchy = get_role_hierarchy()
    dependents = []
    
    for role, deps in hierarchy.items():
        if name in deps:
            dependents.append(role)
    
    return dependents