# Lucid Admin Interface - RBAC Package
# Step 24: Admin Container & Integration
#
# Role-Based Access Control system for the Lucid admin interface.
# Provides comprehensive permission management and role hierarchy.

from admin.rbac.manager import (
    RBACManager, get_rbac_manager, UserRole, RolePermission, set_rbac_manager)
from admin.rbac.roles import (
    Role, RoleType, get_role_hierarchy,
    get_all_roles, get_role, get_system_roles,
    get_custom_roles, role_exists, get_role_permissions,
    get_inherited_permissions, validate_role_hierarchy,
    get_role_dependencies, get_role_dependents
    )
from admin.rbac.permissions import( 
    Permission, PermissionType, get_permission_mapping,
    get_all_permissions, get_permissions_by_type, get_permissions_by_resource,
    get_permissions_by_action, permission_exists, get_permission_hierarchy,
    validate_permission_name, get_permission_dependencies, get_permission_dependents,
    get_permission_stats
    )
from admin.rbac.middleware import (
    RBACMiddleware, require_permission, require_role,
    require_any_permission, require_all_permissions,
    require_any_role, require_all_roles,
    check_permission_dependency, check_role_dependency,
    require_permission_dependency, require_role_dependency,
    validate_permission, validate_role,
    get_permission_info, get_role_info
    )
import admin.utils.logging as logging
logger = logging.get_logger(__name__)


__all__ = [
    "RBACManager", "get_rbac_manager", "UserRole", "RolePermission", "set_rbac_manager",
    "Role", "RoleType", "get_role_hierarchy", "get_all_roles", "get_role",
    "get_system_roles", "get_custom_roles", "role_exists", "get_role_permissions",
    "get_inherited_permissions", "validate_role_hierarchy", "get_role_dependencies",
    "get_role_dependents", "Permission", "PermissionType", "get_permission_mapping",
    "RBACMiddleware", "require_permission", "require_role", "require_any_permission",
    "require_all_permissions", "require_any_role", "require_all_roles",
    "check_permission_dependency", "check_role_dependency",
    "require_permission_dependency", "require_role_dependency",
    "validate_permission", "validate_role",
    "get_permission_info", "get_role_info", "logger", "logging",
    "get_all_permissions", "get_permissions_by_type", "get_permissions_by_resource",
    "get_permissions_by_action", "permission_exists", "get_permission_hierarchy",
    "validate_permission_name", "get_permission_dependencies", "get_permission_dependents",
    "get_permission_stats"
]
