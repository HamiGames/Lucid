#!/usr/bin/env python3
"""
Lucid Admin Interface - RBAC Middleware
Step 24: Admin Container & Integration

RBAC middleware for the Lucid admin interface.
Provides permission checking and role-based access control.
"""

import logging
from typing import List, Optional, Callable, Any
from functools import wraps
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .manager import get_rbac_manager, RBACManager
from .roles import get_role, role_exists
from .permissions import get_permission, permission_exists

logger = logging.getLogger(__name__)

security = HTTPBearer()


class RBACMiddleware:
    """RBAC middleware for FastAPI"""
    
    def __init__(self, rbac_manager: RBACManager):
        self.rbac_manager = rbac_manager
    
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has permission"""
        try:
            return await self.rbac_manager.check_permission(user_id, permission)
        except Exception as e:
            logger.error(f"Failed to check permission {permission} for user {user_id}: {e}")
            return False
    
    async def check_role(self, user_id: str, role: str) -> bool:
        """Check if user has role"""
        try:
            user_roles = await self.rbac_manager.get_user_roles(user_id)
            return role in user_roles
        except Exception as e:
            logger.error(f"Failed to check role {role} for user {user_id}: {e}")
            return False
    
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for user"""
        try:
            permissions = await self.rbac_manager.get_user_permissions(user_id)
            return list(permissions)
        except Exception as e:
            logger.error(f"Failed to get permissions for user {user_id}: {e}")
            return []
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get all roles for user"""
        try:
            return await self.rbac_manager.get_user_roles(user_id)
        except Exception as e:
            logger.error(f"Failed to get roles for user {user_id}: {e}")
            return []


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from context (would be implemented in real system)
            user_id = "current_user_id"  # This would come from authentication
            
            # Check permission
            rbac_manager = get_rbac_manager()
            has_permission = await rbac_manager.check_permission(user_id, permission)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """Decorator to require specific role"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from context (would be implemented in real system)
            user_id = "current_user_id"  # This would come from authentication
            
            # Check role
            rbac_manager = get_rbac_manager()
            user_roles = await rbac_manager.get_user_roles(user_id)
            
            if role not in user_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(permissions: List[str]):
    """Decorator to require any of the specified permissions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from context (would be implemented in real system)
            user_id = "current_user_id"  # This would come from authentication
            
            # Check permissions
            rbac_manager = get_rbac_manager()
            user_permissions = await rbac_manager.get_user_permissions(user_id)
            
            if not any(perm in user_permissions for perm in permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of the following permissions required: {', '.join(permissions)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(permissions: List[str]):
    """Decorator to require all of the specified permissions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from context (would be implemented in real system)
            user_id = "current_user_id"  # This would come from authentication
            
            # Check permissions
            rbac_manager = get_rbac_manager()
            user_permissions = await rbac_manager.get_user_permissions(user_id)
            
            if not all(perm in user_permissions for perm in permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"All of the following permissions required: {', '.join(permissions)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_role(roles: List[str]):
    """Decorator to require any of the specified roles"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from context (would be implemented in real system)
            user_id = "current_user_id"  # This would come from authentication
            
            # Check roles
            rbac_manager = get_rbac_manager()
            user_roles = await rbac_manager.get_user_roles(user_id)
            
            if not any(role in user_roles for role in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of the following roles required: {', '.join(roles)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_roles(roles: List[str]):
    """Decorator to require all of the specified roles"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from context (would be implemented in real system)
            user_id = "current_user_id"  # This would come from authentication
            
            # Check roles
            rbac_manager = get_rbac_manager()
            user_roles = await rbac_manager.get_user_roles(user_id)
            
            if not all(role in user_roles for role in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"All of the following roles required: {', '.join(roles)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# FastAPI dependency functions
async def check_permission_dependency(permission: str, user_id: str = "current_user_id") -> bool:
    """FastAPI dependency to check permission"""
    try:
        rbac_manager = get_rbac_manager()
        return await rbac_manager.check_permission(user_id, permission)
    except Exception as e:
        logger.error(f"Failed to check permission {permission}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Permission check failed"
        )


async def check_role_dependency(role: str, user_id: str = "current_user_id") -> bool:
    """FastAPI dependency to check role"""
    try:
        rbac_manager = get_rbac_manager()
        user_roles = await rbac_manager.get_user_roles(user_id)
        return role in user_roles
    except Exception as e:
        logger.error(f"Failed to check role {role}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role check failed"
        )


async def require_permission_dependency(permission: str, user_id: str = "current_user_id"):
    """FastAPI dependency that requires permission"""
    has_permission = await check_permission_dependency(permission, user_id)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {permission}"
        )
    return True


async def require_role_dependency(role: str, user_id: str = "current_user_id"):
    """FastAPI dependency that requires role"""
    has_role = await check_role_dependency(role, user_id)
    if not has_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role required: {role}"
        )
    return True


# Permission validation functions
def validate_permission(permission: str) -> bool:
    """Validate permission exists"""
    return permission_exists(permission)


def validate_role(role: str) -> bool:
    """Validate role exists"""
    return role_exists(role)


def get_permission_info(permission: str) -> Optional[dict]:
    """Get permission information"""
    perm = get_permission(permission)
    if perm:
        return {
            "name": perm.name,
            "display_name": perm.display_name,
            "description": perm.description,
            "type": perm.permission_type.value,
            "resource": perm.resource,
            "action": perm.action
        }
    return None


def get_role_info(role: str) -> Optional[dict]:
    """Get role information"""
    role_obj = get_role(role)
    if role_obj:
        return {
            "name": role_obj.name,
            "display_name": role_obj.display_name,
            "description": role_obj.description,
            "type": role_obj.role_type.value,
            "permissions": list(role_obj.permissions),
            "is_system": role_obj.is_system
        }
    return None
