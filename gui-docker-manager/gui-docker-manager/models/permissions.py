"""
Permission and Role Data Models
File: gui-docker-manager/gui-docker-manager/models/permissions.py
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum


class PermissionType(str, Enum):
    """Permission types"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"


class Permission(BaseModel):
    """Individual permission"""
    resource: str = Field(..., description="Resource type")
    action: PermissionType = Field(..., description="Action type")
    allowed: bool = Field(..., description="Whether permission is allowed")


class Role(str, Enum):
    """User roles"""
    USER = "user"
    DEVELOPER = "developer"
    ADMIN = "admin"


class RolePermissions(BaseModel):
    """Role with its permissions"""
    role: Role = Field(..., description="Role name")
    permissions: Dict[str, bool] = Field(..., description="Permissions for this role")
    accessible_services: List[str] = Field(..., description="Service groups accessible to role")
    description: str = Field(..., description="Role description")
