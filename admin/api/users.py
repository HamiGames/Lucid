#!/usr/bin/env python3
"""
Lucid Admin Interface - User Management API
Step 23: Admin Backend APIs Implementation

User management API endpoints for the Lucid admin interface.
Provides user creation, management, and role assignment functionality.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from pydantic import BaseModel, Field, EmailStr
import uuid

# Import admin modules
from admin.config import get_admin_config
from admin.system.admin_controller import AdminController, AdminAccount, AdminRole
from admin.rbac.manager import RBACManager
from admin.audit.logger import AuditLogger

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class UserCreateRequest(BaseModel):
    """User creation request"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=12, description="User password")
    role: str = Field(..., description="User role")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    is_active: bool = Field(True, description="User active status")


class UserUpdateRequest(BaseModel):
    """User update request"""
    email: Optional[EmailStr] = Field(None, description="User email address")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    is_active: Optional[bool] = Field(None, description="User active status")


class UserResponse(BaseModel):
    """User response model"""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="User role")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    is_active: bool = Field(..., description="User active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    sessions_count: int = Field(0, description="Active sessions count")


class UserListResponse(BaseModel):
    """User list response"""
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    limit: int = Field(..., description="Results limit")
    offset: int = Field(..., description="Results offset")


class UserRoleAssignment(BaseModel):
    """User role assignment"""
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., description="Role to assign")
    assigned_by: str = Field(..., description="Admin who assigned the role")
    assigned_at: datetime = Field(..., description="Assignment timestamp")


class UserSuspensionRequest(BaseModel):
    """User suspension request"""
    reason: str = Field(..., min_length=10, description="Suspension reason")
    duration_hours: Optional[int] = Field(None, description="Suspension duration in hours")
    notify_user: bool = Field(True, description="Whether to notify the user")


class UserActivationRequest(BaseModel):
    """User activation request"""
    reason: str = Field(..., min_length=10, description="Activation reason")
    notify_user: bool = Field(True, description="Whether to notify the user")


async def get_admin_controller() -> AdminController:
    """Get admin controller dependency"""
    from admin.main import admin_controller
    if not admin_controller:
        raise HTTPException(
            status_code=503,
            detail="Admin controller not available"
        )
    return admin_controller


async def get_rbac_manager() -> RBACManager:
    """Get RBAC manager dependency"""
    from admin.main import rbac_manager
    if not rbac_manager:
        raise HTTPException(
            status_code=503,
            detail="RBAC manager not available"
        )
    return rbac_manager


async def get_audit_logger() -> AuditLogger:
    """Get audit logger dependency"""
    from admin.main import audit_logger
    if not audit_logger:
        raise HTTPException(
            status_code=503,
            detail="Audit logger not available"
        )
    return audit_logger


@router.get("", response_model=UserListResponse)
async def list_users(
    status: Optional[str] = Query(None, description="Filter by user status"),
    role: Optional[str] = Query(None, description="Filter by user role"),
    search: Optional[str] = Query(None, description="Search by username or email"),
    limit: int = Query(50, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Results offset"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    List all users with optional filtering
    
    Parameters:
    - status: active, suspended, banned
    - role: Filter by role
    - search: Search by username or email
    - limit: Number of results (1-1000)
    - offset: Results offset
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "users:list")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: users:list"
            )
        
        # Log access
        await audit.log_access(
            admin.admin_id,
            "users_list",
            f"GET /admin/api/v1/users?status={status}&role={role}&search={search}"
        )
        
        # Get users from database
        users = await _get_users_from_database(
            status=status,
            role=role,
            search=search,
            limit=limit,
            offset=offset
        )
        
        # Get total count
        total = await _get_users_count(status=status, role=role, search=search)
        
        return UserListResponse(
            users=users,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve users"
        )


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreateRequest,
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Create new user
    
    Creates a new user account with specified role and permissions.
    Requires super-admin or admin role.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "users:create")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: users:create"
            )
        
        # Validate role
        valid_roles = [role.value for role in AdminRole]
        if user_data.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        # Check if username already exists
        existing_user = await _get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Username already exists"
            )
        
        # Check if email already exists
        existing_email = await _get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=409,
                detail="Email already exists"
            )
        
        # Create user
        user_id = await _create_user_in_database(user_data, admin.admin_id)
        
        # Log creation
        await audit.log_user_action(
            admin.admin_id,
            "user_created",
            user_id,
            {
                "username": user_data.username,
                "email": user_data.email,
                "role": user_data.role
            }
        )
        
        # Get created user
        created_user = await _get_user_by_id(user_id)
        if not created_user:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve created user"
            )
        
        return created_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create user"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str = Path(..., description="User ID"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Get user by ID
    
    Retrieves detailed information about a specific user.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "users:view")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: users:view"
            )
        
        # Log access
        await audit.log_access(
            admin.admin_id,
            "user_view",
            f"GET /admin/api/v1/users/{user_id}"
        )
        
        # Get user
        user = await _get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve user"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str = Path(..., description="User ID"),
    user_data: UserUpdateRequest = Body(..., description="User update data"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Update user information
    
    Updates user profile information. Cannot change username or role.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "users:update")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: users:update"
            )
        
        # Check if user exists
        existing_user = await _get_user_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Check email uniqueness if changing email
        if user_data.email and user_data.email != existing_user.email:
            existing_email = await _get_user_by_email(user_data.email)
            if existing_email:
                raise HTTPException(
                    status_code=409,
                    detail="Email already exists"
                )
        
        # Update user
        await _update_user_in_database(user_id, user_data, admin.admin_id)
        
        # Log update
        await audit.log_user_action(
            admin.admin_id,
            "user_updated",
            user_id,
            {
                "updated_fields": user_data.dict(exclude_unset=True)
            }
        )
        
        # Get updated user
        updated_user = await _get_user_by_id(user_id)
        if not updated_user:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve updated user"
            )
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update user"
        )


@router.post("/{user_id}/suspend", response_model=Dict[str, str])
async def suspend_user(
    user_id: str = Path(..., description="User ID"),
    suspension_data: UserSuspensionRequest = Body(..., description="Suspension details"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Suspend user account
    
    Suspends a user account with optional duration.
    Suspended users cannot log in or create sessions.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "users:suspend")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: users:suspend"
            )
        
        # Check if user exists
        existing_user = await _get_user_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Check if user is already suspended
        if not existing_user.is_active:
            raise HTTPException(
                status_code=409,
                detail="User is already suspended"
            )
        
        # Suspend user
        await _suspend_user_in_database(
            user_id,
            suspension_data.reason,
            suspension_data.duration_hours,
            admin.admin_id
        )
        
        # Log suspension
        await audit.log_user_action(
            admin.admin_id,
            "user_suspended",
            user_id,
            {
                "reason": suspension_data.reason,
                "duration_hours": suspension_data.duration_hours
            }
        )
        
        # Notify user if requested
        if suspension_data.notify_user:
            await _notify_user_suspension(user_id, suspension_data.reason)
        
        return {
            "status": "success",
            "message": f"User {user_id} suspended successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to suspend user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to suspend user"
        )


@router.post("/{user_id}/activate", response_model=Dict[str, str])
async def activate_user(
    user_id: str = Path(..., description="User ID"),
    activation_data: UserActivationRequest = Body(..., description="Activation details"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Activate user account
    
    Activates a suspended user account.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "users:activate")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: users:activate"
            )
        
        # Check if user exists
        existing_user = await _get_user_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Check if user is already active
        if existing_user.is_active:
            raise HTTPException(
                status_code=409,
                detail="User is already active"
            )
        
        # Activate user
        await _activate_user_in_database(
            user_id,
            activation_data.reason,
            admin.admin_id
        )
        
        # Log activation
        await audit.log_user_action(
            admin.admin_id,
            "user_activated",
            user_id,
            {
                "reason": activation_data.reason
            }
        )
        
        # Notify user if requested
        if activation_data.notify_user:
            await _notify_user_activation(user_id, activation_data.reason)
        
        return {
            "status": "success",
            "message": f"User {user_id} activated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to activate user"
        )


@router.post("/{user_id}/assign-role", response_model=UserRoleAssignment)
async def assign_user_role(
    user_id: str = Path(..., description="User ID"),
    role: str = Body(..., description="Role to assign"),
    admin: AdminAccount = Depends(get_admin_controller),
    rbac: RBACManager = Depends(get_rbac_manager),
    audit: AuditLogger = Depends(get_audit_logger)
):
    """
    Assign role to user
    
    Assigns a new role to a user. Requires super-admin permissions.
    """
    try:
        # Check permissions
        has_permission = await rbac.check_permission(admin.admin_id, "users:assign_role")
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Permission denied: users:assign_role"
            )
        
        # Validate role
        valid_roles = [role.value for role in AdminRole]
        if role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        # Check if user exists
        existing_user = await _get_user_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Assign role
        await _assign_role_to_user(user_id, role, admin.admin_id)
        
        # Log role assignment
        await audit.log_user_action(
            admin.admin_id,
            "user_role_assigned",
            user_id,
            {
                "new_role": role,
                "previous_role": existing_user.role
            }
        )
        
        return UserRoleAssignment(
            user_id=user_id,
            role=role,
            assigned_by=admin.admin_id,
            assigned_at=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign role: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to assign role"
        )


# Helper functions
async def _get_users_from_database(
    status: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[UserResponse]:
    """Get users from database with filtering"""
    try:
        # This would query the actual database
        # For now, return sample data
        users = []
        
        # Sample user data
        sample_users = [
            {
                "id": "user-1",
                "username": "john_doe",
                "email": "john@example.com",
                "role": "user",
                "first_name": "John",
                "last_name": "Doe",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "last_login": datetime.now(timezone.utc),
                "sessions_count": 2
            },
            {
                "id": "user-2",
                "username": "jane_smith",
                "email": "jane@example.com",
                "role": "operator",
                "first_name": "Jane",
                "last_name": "Smith",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "last_login": datetime.now(timezone.utc),
                "sessions_count": 1
            }
        ]
        
        for user_data in sample_users:
            # Apply filters
            if status and status == "active" and not user_data["is_active"]:
                continue
            if status and status == "suspended" and user_data["is_active"]:
                continue
            if role and user_data["role"] != role:
                continue
            if search and search.lower() not in user_data["username"].lower() and search.lower() not in user_data["email"].lower():
                continue
            
            users.append(UserResponse(**user_data))
        
        return users[offset:offset + limit]
        
    except Exception as e:
        logger.error(f"Failed to get users from database: {e}")
        return []


async def _get_users_count(
    status: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None
) -> int:
    """Get total count of users with filtering"""
    try:
        # This would query the actual database
        # For now, return sample count
        return 2
        
    except Exception as e:
        logger.error(f"Failed to get users count: {e}")
        return 0


async def _get_user_by_id(user_id: str) -> Optional[UserResponse]:
    """Get user by ID"""
    try:
        # This would query the actual database
        # For now, return sample data
        if user_id == "user-1":
            return UserResponse(
                id="user-1",
                username="john_doe",
                email="john@example.com",
                role="user",
                first_name="John",
                last_name="Doe",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc),
                sessions_count=2
            )
        return None
        
    except Exception as e:
        logger.error(f"Failed to get user by ID: {e}")
        return None


async def _get_user_by_username(username: str) -> Optional[UserResponse]:
    """Get user by username"""
    try:
        # This would query the actual database
        # For now, return None (no existing user)
        return None
        
    except Exception as e:
        logger.error(f"Failed to get user by username: {e}")
        return None


async def _get_user_by_email(email: str) -> Optional[UserResponse]:
    """Get user by email"""
    try:
        # This would query the actual database
        # For now, return None (no existing user)
        return None
        
    except Exception as e:
        logger.error(f"Failed to get user by email: {e}")
        return None


async def _create_user_in_database(user_data: UserCreateRequest, admin_id: str) -> str:
    """Create user in database"""
    try:
        # This would create the user in the actual database
        # For now, return a sample user ID
        user_id = str(uuid.uuid4())
        
        # Log creation
        logger.info(f"User created: {user_id} by admin: {admin_id}")
        
        return user_id
        
    except Exception as e:
        logger.error(f"Failed to create user in database: {e}")
        raise


async def _update_user_in_database(user_id: str, user_data: UserUpdateRequest, admin_id: str):
    """Update user in database"""
    try:
        # This would update the user in the actual database
        logger.info(f"User updated: {user_id} by admin: {admin_id}")
        
    except Exception as e:
        logger.error(f"Failed to update user in database: {e}")
        raise


async def _suspend_user_in_database(user_id: str, reason: str, duration_hours: Optional[int], admin_id: str):
    """Suspend user in database"""
    try:
        # This would suspend the user in the actual database
        logger.info(f"User suspended: {user_id} by admin: {admin_id}, reason: {reason}")
        
    except Exception as e:
        logger.error(f"Failed to suspend user in database: {e}")
        raise


async def _activate_user_in_database(user_id: str, reason: str, admin_id: str):
    """Activate user in database"""
    try:
        # This would activate the user in the actual database
        logger.info(f"User activated: {user_id} by admin: {admin_id}, reason: {reason}")
        
    except Exception as e:
        logger.error(f"Failed to activate user in database: {e}")
        raise


async def _assign_role_to_user(user_id: str, role: str, admin_id: str):
    """Assign role to user in database"""
    try:
        # This would assign the role in the actual database
        logger.info(f"Role assigned: {role} to user: {user_id} by admin: {admin_id}")
        
    except Exception as e:
        logger.error(f"Failed to assign role to user: {e}")
        raise


async def _notify_user_suspension(user_id: str, reason: str):
    """Notify user of suspension"""
    try:
        # This would send notification to the user
        logger.info(f"User notification sent: suspension to user: {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to notify user suspension: {e}")


async def _notify_user_activation(user_id: str, reason: str):
    """Notify user of activation"""
    try:
        # This would send notification to the user
        logger.info(f"User notification sent: activation to user: {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to notify user activation: {e}")
