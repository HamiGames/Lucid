"""
Lucid Authentication Service - RBAC (Role-Based Access Control)
4 Roles: USER, NODE_OPERATOR, ADMIN, SUPER_ADMIN
"""

from enum import Enum
from typing import List, Dict, Set, Optional
from auth.models.permissions import Role, Permission
from auth.user_manager import UserManager
import logging

logger = logging.getLogger(__name__)


class RBACManager:
    """
    Role-Based Access Control Manager
    
    Roles:
    - USER: Basic session operations
    - NODE_OPERATOR: Node management, PoOT operations
    - ADMIN: System management, blockchain operations
    - SUPER_ADMIN: Full system access, TRON payout management
    """
    
    # Role hierarchy (higher number = more privileges)
    ROLE_HIERARCHY = {
        Role.USER: 1,
        Role.NODE_OPERATOR: 2,
        Role.ADMIN: 3,
        Role.SUPER_ADMIN: 4
    }
    
    # Role permissions mapping
    ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
        Role.USER: {
            Permission.CREATE_SESSION,
            Permission.VIEW_OWN_SESSIONS,
            Permission.DELETE_OWN_SESSIONS,
            Permission.VIEW_OWN_PROFILE,
            Permission.UPDATE_OWN_PROFILE,
            Permission.CONNECT_HARDWARE_WALLET
        },
        Role.NODE_OPERATOR: {
            # All USER permissions
            Permission.CREATE_SESSION,
            Permission.VIEW_OWN_SESSIONS,
            Permission.DELETE_OWN_SESSIONS,
            Permission.VIEW_OWN_PROFILE,
            Permission.UPDATE_OWN_PROFILE,
            Permission.CONNECT_HARDWARE_WALLET,
            # NODE_OPERATOR specific permissions
            Permission.REGISTER_NODE,
            Permission.MANAGE_OWN_NODES,
            Permission.VIEW_OWN_NODES,
            Permission.SUBMIT_POOT_VOTES,
            Permission.VIEW_OWN_PAYOUTS,
            Permission.REQUEST_PAYOUT,
            Permission.VIEW_POOL_INFO
        },
        Role.ADMIN: {
            # All NODE_OPERATOR permissions
            Permission.CREATE_SESSION,
            Permission.VIEW_OWN_SESSIONS,
            Permission.DELETE_OWN_SESSIONS,
            Permission.VIEW_OWN_PROFILE,
            Permission.UPDATE_OWN_PROFILE,
            Permission.CONNECT_HARDWARE_WALLET,
            Permission.REGISTER_NODE,
            Permission.MANAGE_OWN_NODES,
            Permission.VIEW_OWN_NODES,
            Permission.SUBMIT_POOT_VOTES,
            Permission.VIEW_OWN_PAYOUTS,
            Permission.REQUEST_PAYOUT,
            Permission.VIEW_POOL_INFO,
            # ADMIN specific permissions
            Permission.VIEW_ALL_USERS,
            Permission.MANAGE_USERS,
            Permission.VIEW_ALL_SESSIONS,
            Permission.DELETE_ANY_SESSION,
            Permission.VIEW_BLOCKCHAIN_INFO,
            Permission.VIEW_ALL_NODES,
            Permission.MANAGE_POOLS,
            Permission.VIEW_SYSTEM_METRICS,
            Permission.ACCESS_ADMIN_DASHBOARD,
            Permission.VIEW_AUDIT_LOGS,
            Permission.MANAGE_TRUST_POLICIES,
            # Service Orchestration permissions (ADMIN can spawn services)
            Permission.SPAWN_SERVICES,
            Permission.MANAGE_MONGODB_INSTANCES,
            Permission.CLONE_SERVICES,
            Permission.MANAGE_SERVICE_LIFECYCLE,
            Permission.VIEW_SPAWNED_SERVICES
        },
        Role.SUPER_ADMIN: set(Permission)  # All permissions
    }
    
    def __init__(self, user_manager: Optional[UserManager] = None):
        """Initialize RBAC manager"""
        self.user_manager = user_manager
        logger.info("RBAC Manager initialized with 4 roles")
    
    async def check_permission(self, user_id: str, permission: Permission) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            user_id: User ID
            permission: Permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            if not self.user_manager:
                logger.error("UserManager not initialized in RBACManager")
                return False
            
            user = await self.user_manager.get_user(user_id)
            if not user:
                logger.warning(f"User {user_id} not found for permission check")
                return False
            
            user_permissions = self.ROLE_PERMISSIONS.get(user.role, set())
            has_permission = permission in user_permissions
            
            logger.debug(f"Permission check: user {user_id} ({user.role.value}) - {permission.value}: {has_permission}")
            return has_permission
            
        except Exception as e:
            logger.error(f"Error checking permission for user {user_id}: {e}")
            return False
    
    async def check_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """
        Check if user has all specified permissions
        
        Args:
            user_id: User ID
            permissions: List of permissions to check
            
        Returns:
            True if user has all permissions, False otherwise
        """
        for permission in permissions:
            if not await self.check_permission(user_id, permission):
                return False
        return True
    
    async def check_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """
        Check if user has any of the specified permissions
        
        Args:
            user_id: User ID
            permissions: List of permissions to check
            
        Returns:
            True if user has at least one permission, False otherwise
        """
        for permission in permissions:
            if await self.check_permission(user_id, permission):
                return True
        return False
    
    async def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """
        Get all permissions for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Set of permissions
        """
        try:
            if not self.user_manager:
                return set()
            
            user = await self.user_manager.get_user(user_id)
            if not user:
                return set()
            
            return self.ROLE_PERMISSIONS.get(user.role, set())
            
        except Exception as e:
            logger.error(f"Error getting permissions for user {user_id}: {e}")
            return set()
    
    async def has_role(self, user_id: str, role: Role) -> bool:
        """
        Check if user has a specific role
        
        Args:
            user_id: User ID
            role: Role to check
            
        Returns:
            True if user has role, False otherwise
        """
        try:
            if not self.user_manager:
                return False
            
            user = await self.user_manager.get_user(user_id)
            if not user:
                return False
            
            return user.role == role
            
        except Exception as e:
            logger.error(f"Error checking role for user {user_id}: {e}")
            return False
    
    async def has_minimum_role(self, user_id: str, minimum_role: Role) -> bool:
        """
        Check if user has at least the specified role level
        
        Args:
            user_id: User ID
            minimum_role: Minimum role required
            
        Returns:
            True if user has minimum role level, False otherwise
        """
        try:
            if not self.user_manager:
                return False
            
            user = await self.user_manager.get_user(user_id)
            if not user:
                return False
            
            user_level = self.ROLE_HIERARCHY.get(user.role, 0)
            required_level = self.ROLE_HIERARCHY.get(minimum_role, 0)
            
            return user_level >= required_level
            
        except Exception as e:
            logger.error(f"Error checking minimum role for user {user_id}: {e}")
            return False
    
    async def assign_role(self, user_id: str, role: Role, assigned_by: str) -> bool:
        """
        Assign role to user
        
        Args:
            user_id: User ID
            role: Role to assign
            assigned_by: User ID of admin assigning role
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if assigner has permission
            if not await self.check_permission(assigned_by, Permission.MANAGE_USERS):
                logger.warning(f"User {assigned_by} lacks permission to assign roles")
                return False
            
            # Check role hierarchy - can't assign higher role than yours
            assigner = await self.user_manager.get_user(assigned_by)
            if not assigner:
                return False
            
            assigner_level = self.ROLE_HIERARCHY.get(assigner.role, 0)
            new_role_level = self.ROLE_HIERARCHY.get(role, 0)
            
            if new_role_level > assigner_level:
                logger.warning(f"User {assigned_by} cannot assign higher role than their own")
                return False
            
            # Assign role
            user = await self.user_manager.get_user(user_id)
            if not user:
                return False
            
            old_role = user.role
            user.role = role
            await self.user_manager.update_user(user)
            
            logger.info(f"Role changed for user {user_id}: {old_role.value} -> {role.value} (by {assigned_by})")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning role to user {user_id}: {e}")
            return False
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """
        Get all permissions for a role
        
        Args:
            role: Role
            
        Returns:
            Set of permissions
        """
        return self.ROLE_PERMISSIONS.get(role, set())
    
    def get_all_roles(self) -> List[Role]:
        """Get list of all roles"""
        return list(Role)
    
    def get_all_permissions(self) -> List[Permission]:
        """Get list of all permissions"""
        return list(Permission)
    
    def get_role_info(self, role: Role) -> Dict:
        """
        Get information about a role
        
        Args:
            role: Role
            
        Returns:
            Dict with role information
        """
        return {
            "role": role.value,
            "level": self.ROLE_HIERARCHY.get(role, 0),
            "permissions": [p.value for p in self.ROLE_PERMISSIONS.get(role, set())],
            "permission_count": len(self.ROLE_PERMISSIONS.get(role, set()))
        }
    
    def get_rbac_summary(self) -> Dict:
        """
        Get summary of RBAC configuration
        
        Returns:
            Dict with RBAC summary
        """
        return {
            "total_roles": len(Role),
            "total_permissions": len(Permission),
            "roles": [
                {
                    "role": role.value,
                    "level": self.ROLE_HIERARCHY.get(role, 0),
                    "permission_count": len(self.ROLE_PERMISSIONS.get(role, set()))
                }
                for role in Role
            ]
        }


# Decorator for permission checking
def require_permission(permission: Permission):
    """Decorator to require permission for endpoint"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user_id from request context
            # This will be implemented in the middleware
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: Role):
    """Decorator to require minimum role for endpoint"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user_id from request context
            # This will be implemented in the middleware
            return await func(*args, **kwargs)
        return wrapper
    return decorator

