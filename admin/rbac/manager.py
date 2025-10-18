#!/usr/bin/env python3
"""
Lucid Admin Interface - RBAC Manager
Step 24: Admin Container & Integration

Role-Based Access Control manager for the Lucid admin interface.
Handles role assignment, permission checking, and access control.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from .roles import Role, RoleType, get_role_hierarchy
from .permissions import Permission, PermissionType, get_permission_mapping

logger = logging.getLogger(__name__)


class RBACError(Exception):
    """RBAC-specific exceptions"""
    pass


@dataclass
class UserRole:
    """User role assignment"""
    user_id: str
    role_name: str
    assigned_by: str
    assigned_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RolePermission:
    """Role permission mapping"""
    role_name: str
    permission_name: str
    granted_by: str
    granted_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class RBACManager:
    """Role-Based Access Control Manager"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.user_roles_collection = database.user_roles
        self.role_permissions_collection = database.role_permissions
        self.permissions_cache: Dict[str, Set[str]] = {}
        self.roles_cache: Dict[str, Set[str]] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = datetime.utcnow()
    
    async def initialize(self):
        """Initialize RBAC system"""
        try:
            # Create indexes
            await self.user_roles_collection.create_index("user_id")
            await self.user_roles_collection.create_index("role_name")
            await self.user_roles_collection.create_index("expires_at")
            await self.role_permissions_collection.create_index("role_name")
            await self.role_permissions_collection.create_index("permission_name")
            
            # Initialize default roles and permissions
            await self._initialize_default_roles()
            await self._initialize_default_permissions()
            
            logger.info("RBAC system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RBAC system: {e}")
            raise RBACError(f"RBAC initialization failed: {e}")
    
    async def _initialize_default_roles(self):
        """Initialize default roles"""
        default_roles = [
            {
                "role_name": "super_admin",
                "display_name": "Super Administrator",
                "description": "Full system access with all permissions",
                "is_system": True,
                "created_at": datetime.utcnow()
            },
            {
                "role_name": "admin",
                "display_name": "Administrator", 
                "description": "Administrative access with most permissions",
                "is_system": True,
                "created_at": datetime.utcnow()
            },
            {
                "role_name": "operator",
                "display_name": "Operator",
                "description": "Operational access for system management",
                "is_system": True,
                "created_at": datetime.utcnow()
            },
            {
                "role_name": "read_only",
                "display_name": "Read Only",
                "description": "Read-only access for monitoring",
                "is_system": True,
                "created_at": datetime.utcnow()
            }
        ]
        
        for role_data in default_roles:
            try:
                await self.database.roles.update_one(
                    {"role_name": role_data["role_name"]},
                    {"$setOnInsert": role_data},
                    upsert=True
                )
            except Exception as e:
                logger.warning(f"Failed to initialize role {role_data['role_name']}: {e}")
    
    async def _initialize_default_permissions(self):
        """Initialize default permissions"""
        default_permissions = [
            # System permissions
            {"permission_name": "system.view", "description": "View system information"},
            {"permission_name": "system.configure", "description": "Configure system settings"},
            {"permission_name": "system.shutdown", "description": "Shutdown system"},
            {"permission_name": "system.restart", "description": "Restart system"},
            
            # User management permissions
            {"permission_name": "users.view", "description": "View users"},
            {"permission_name": "users.create", "description": "Create users"},
            {"permission_name": "users.edit", "description": "Edit users"},
            {"permission_name": "users.delete", "description": "Delete users"},
            {"permission_name": "users.manage_roles", "description": "Manage user roles"},
            
            # Session management permissions
            {"permission_name": "sessions.view", "description": "View sessions"},
            {"permission_name": "sessions.terminate", "description": "Terminate sessions"},
            {"permission_name": "sessions.bulk_terminate", "description": "Bulk terminate sessions"},
            {"permission_name": "sessions.monitor", "description": "Monitor session activity"},
            
            # Node management permissions
            {"permission_name": "nodes.view", "description": "View nodes"},
            {"permission_name": "nodes.manage", "description": "Manage nodes"},
            {"permission_name": "nodes.maintenance", "description": "Node maintenance"},
            {"permission_name": "nodes.payouts", "description": "Manage node payouts"},
            
            # Blockchain permissions
            {"permission_name": "blockchain.view", "description": "View blockchain status"},
            {"permission_name": "blockchain.anchor", "description": "Anchor sessions to blockchain"},
            {"permission_name": "blockchain.pause", "description": "Pause blockchain operations"},
            {"permission_name": "blockchain.resume", "description": "Resume blockchain operations"},
            
            # Audit permissions
            {"permission_name": "audit.view", "description": "View audit logs"},
            {"permission_name": "audit.export", "description": "Export audit logs"},
            {"permission_name": "audit.retention", "description": "Manage audit retention"},
            
            # Emergency permissions
            {"permission_name": "emergency.lockdown", "description": "System lockdown"},
            {"permission_name": "emergency.shutdown", "description": "Emergency shutdown"},
            {"permission_name": "emergency.notify", "description": "Emergency notifications"}
        ]
        
        for perm_data in default_permissions:
            try:
                await self.database.permissions.update_one(
                    {"permission_name": perm_data["permission_name"]},
                    {"$setOnInsert": {**perm_data, "created_at": datetime.utcnow()}},
                    upsert=True
                )
            except Exception as e:
                logger.warning(f"Failed to initialize permission {perm_data['permission_name']}: {e}")
    
    async def assign_role(self, user_id: str, role_name: str, assigned_by: str, 
                         expires_at: Optional[datetime] = None) -> bool:
        """Assign role to user"""
        try:
            # Validate role exists
            role = await self.database.roles.find_one({"role_name": role_name})
            if not role:
                raise RBACError(f"Role {role_name} does not exist")
            
            # Check if user already has this role
            existing = await self.user_roles_collection.find_one({
                "user_id": user_id,
                "role_name": role_name,
                "expires_at": {"$gt": datetime.utcnow()}
            })
            
            if existing:
                logger.warning(f"User {user_id} already has role {role_name}")
                return True
            
            # Assign role
            user_role = UserRole(
                user_id=user_id,
                role_name=role_name,
                assigned_by=assigned_by,
                assigned_at=datetime.utcnow(),
                expires_at=expires_at
            )
            
            await self.user_roles_collection.insert_one(user_role.__dict__)
            
            # Invalidate cache
            self._invalidate_cache()
            
            logger.info(f"Role {role_name} assigned to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign role {role_name} to user {user_id}: {e}")
            raise RBACError(f"Role assignment failed: {e}")
    
    async def revoke_role(self, user_id: str, role_name: str, revoked_by: str) -> bool:
        """Revoke role from user"""
        try:
            result = await self.user_roles_collection.update_many(
                {
                    "user_id": user_id,
                    "role_name": role_name
                },
                {
                    "$set": {
                        "revoked_by": revoked_by,
                        "revoked_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                self._invalidate_cache()
                logger.info(f"Role {role_name} revoked from user {user_id}")
                return True
            else:
                logger.warning(f"User {user_id} does not have role {role_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to revoke role {role_name} from user {user_id}: {e}")
            raise RBACError(f"Role revocation failed: {e}")
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get all active roles for user"""
        try:
            cursor = self.user_roles_collection.find({
                "user_id": user_id,
                "$or": [
                    {"expires_at": {"$exists": False}},
                    {"expires_at": {"$gt": datetime.utcnow()}}
                ]
            })
            
            roles = []
            async for doc in cursor:
                roles.append(doc["role_name"])
            
            return roles
            
        except Exception as e:
            logger.error(f"Failed to get roles for user {user_id}: {e}")
            return []
    
    async def check_permission(self, user_id: str, permission_name: str) -> bool:
        """Check if user has specific permission"""
        try:
            # Get user roles
            user_roles = await self.get_user_roles(user_id)
            if not user_roles:
                return False
            
            # Check cache first
            cache_key = f"{user_id}:{permission_name}"
            if cache_key in self.permissions_cache:
                return permission_name in self.permissions_cache[cache_key]
            
            # Get permissions for all user roles
            permissions = set()
            for role_name in user_roles:
                role_permissions = await self._get_role_permissions(role_name)
                permissions.update(role_permissions)
            
            # Cache result
            self.permissions_cache[cache_key] = permissions
            
            return permission_name in permissions
            
        except Exception as e:
            logger.error(f"Failed to check permission {permission_name} for user {user_id}: {e}")
            return False
    
    async def _get_role_permissions(self, role_name: str) -> Set[str]:
        """Get permissions for a role"""
        try:
            # Check cache first
            if role_name in self.roles_cache:
                return self.roles_cache[role_name]
            
            # Get role permissions from database
            cursor = self.role_permissions_collection.find({"role_name": role_name})
            permissions = set()
            
            async for doc in cursor:
                permissions.add(doc["permission_name"])
            
            # Cache result
            self.roles_cache[role_name] = permissions
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get permissions for role {role_name}: {e}")
            return set()
    
    async def grant_permission(self, role_name: str, permission_name: str, granted_by: str) -> bool:
        """Grant permission to role"""
        try:
            # Validate role and permission exist
            role = await self.database.roles.find_one({"role_name": role_name})
            if not role:
                raise RBACError(f"Role {role_name} does not exist")
            
            permission = await self.database.permissions.find_one({"permission_name": permission_name})
            if not permission:
                raise RBACError(f"Permission {permission_name} does not exist")
            
            # Grant permission
            role_permission = RolePermission(
                role_name=role_name,
                permission_name=permission_name,
                granted_by=granted_by,
                granted_at=datetime.utcnow()
            )
            
            await self.role_permissions_collection.update_one(
                {
                    "role_name": role_name,
                    "permission_name": permission_name
                },
                {"$setOnInsert": role_permission.__dict__},
                upsert=True
            )
            
            # Invalidate cache
            self._invalidate_cache()
            
            logger.info(f"Permission {permission_name} granted to role {role_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to grant permission {permission_name} to role {role_name}: {e}")
            raise RBACError(f"Permission grant failed: {e}")
    
    async def revoke_permission(self, role_name: str, permission_name: str, revoked_by: str) -> bool:
        """Revoke permission from role"""
        try:
            result = await self.role_permissions_collection.delete_one({
                "role_name": role_name,
                "permission_name": permission_name
            })
            
            if result.deleted_count > 0:
                self._invalidate_cache()
                logger.info(f"Permission {permission_name} revoked from role {role_name}")
                return True
            else:
                logger.warning(f"Role {role_name} does not have permission {permission_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to revoke permission {permission_name} from role {role_name}: {e}")
            raise RBACError(f"Permission revocation failed: {e}")
    
    def _invalidate_cache(self):
        """Invalidate permission cache"""
        self.permissions_cache.clear()
        self.roles_cache.clear()
        self.last_cache_update = datetime.utcnow()
    
    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for user"""
        try:
            user_roles = await self.get_user_roles(user_id)
            permissions = set()
            
            for role_name in user_roles:
                role_permissions = await self._get_role_permissions(role_name)
                permissions.update(role_permissions)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get permissions for user {user_id}: {e}")
            return set()
    
    async def cleanup_expired_roles(self):
        """Clean up expired role assignments"""
        try:
            result = await self.user_roles_collection.delete_many({
                "expires_at": {"$lt": datetime.utcnow()}
            })
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} expired role assignments")
                self._invalidate_cache()
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired roles: {e}")
    
    async def close(self):
        """Close RBAC manager"""
        try:
            await self.cleanup_expired_roles()
            logger.info("RBAC manager closed")
        except Exception as e:
            logger.error(f"Error closing RBAC manager: {e}")


# Global RBAC manager instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get global RBAC manager instance"""
    global _rbac_manager
    if _rbac_manager is None:
        raise RBACError("RBAC manager not initialized")
    return _rbac_manager


def set_rbac_manager(manager: RBACManager):
    """Set global RBAC manager instance"""
    global _rbac_manager
    _rbac_manager = manager