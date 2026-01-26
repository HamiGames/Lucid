"""
Access Control Service
File: gui-docker-manager/gui-docker-manager/services/access_control_service.py
"""

import logging
from typing import Dict, List, Any
from enum import Enum

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """User roles for access control"""
    USER = "user"
    DEVELOPER = "developer"
    ADMIN = "admin"


# Role-based access control configuration
ROLE_PERMISSIONS = {
    UserRole.USER: {
        "read:container_status": True,
        "read:container_logs": True,
        "read:system_info": True,
        "start:container": False,
        "stop:container": False,
        "restart:container": False,
    },
    UserRole.DEVELOPER: {
        "read:container_status": True,
        "read:container_logs": True,
        "read:system_info": True,
        "start:container": True,
        "stop:container": True,
        "restart:container": True,
        "start:foundation_services": False,
        "stop:foundation_services": False,
        "start:core_services": True,
        "stop:core_services": True,
        "start:application_services": True,
        "stop:application_services": True,
    },
    UserRole.ADMIN: {
        "read:container_status": True,
        "read:container_logs": True,
        "read:system_info": True,
        "start:container": True,
        "stop:container": True,
        "restart:container": True,
        "start:foundation_services": True,
        "stop:foundation_services": True,
        "start:core_services": True,
        "stop:core_services": True,
        "start:application_services": True,
        "stop:application_services": True,
        "start:support_services": True,
        "stop:support_services": True,
    }
}

# Services accessible by role
ROLE_SERVICES = {
    UserRole.USER: [],
    UserRole.DEVELOPER: ["foundation", "core", "application"],
    UserRole.ADMIN: ["foundation", "core", "application", "support"],
}


class AccessControlService:
    """Business logic for role-based access control"""
    
    @staticmethod
    def check_permission(role: UserRole, permission: str) -> bool:
        """Check if role has permission"""
        if role not in ROLE_PERMISSIONS:
            logger.warning(f"Unknown role: {role}")
            return False
        
        return ROLE_PERMISSIONS[role].get(permission, False)
    
    @staticmethod
    def get_accessible_services(role: UserRole) -> List[str]:
        """Get list of services accessible to role"""
        return ROLE_SERVICES.get(role, [])
    
    @staticmethod
    def can_manage_service_group(role: UserRole, service_group: str) -> bool:
        """Check if role can manage a service group"""
        accessible = ROLE_SERVICES.get(role, [])
        return service_group in accessible
    
    @staticmethod
    def get_role_info(role: UserRole) -> Dict[str, Any]:
        """Get detailed information about a role"""
        return {
            "role": role,
            "permissions": ROLE_PERMISSIONS.get(role, {}),
            "services": ROLE_SERVICES.get(role, []),
        }
