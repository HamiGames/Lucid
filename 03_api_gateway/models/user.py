"""
User Data Models

Models for user management operations including:
- User profiles
- User creation and updates
- User preferences
- User activity tracking

All user models include validation and documentation.
"""

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserRole(str, Enum):
    """User roles for RBAC"""
    USER = "user"
    NODE_OPERATOR = "node_operator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserCreateRequest(BaseModel):
    """
    Request model for creating a new user.
    
    Attributes:
        email: User email address (required)
        tron_address: TRON blockchain address (optional)
        display_name: User display name (optional)
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "tron_address": "TXyz123...",
            "display_name": "John Doe"
        }
    })
    
    email: EmailStr = Field(..., description="User email address")
    tron_address: Optional[str] = Field(None, description="TRON blockchain address")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")


class UserUpdateRequest(BaseModel):
    """
    Request model for updating user information.
    
    All fields are optional - only provided fields will be updated.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "display_name": "John Doe Updated",
            "bio": "Updated bio",
            "avatar_url": "https://example.com/avatar.jpg"
        }
    })
    
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserResponse(BaseModel):
    """
    Standard user response model.
    
    Attributes:
        user_id: Unique user identifier
        email: User email address
        tron_address: TRON blockchain address
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        status: User account status
        roles: List of user roles
        profile: User profile information
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "user-123",
            "email": "user@example.com",
            "tron_address": "TXyz123...",
            "created_at": "2025-10-14T12:00:00Z",
            "updated_at": "2025-10-14T12:00:00Z",
            "status": "active",
            "roles": ["user"],
            "profile": {
                "display_name": "John Doe",
                "bio": "",
                "avatar_url": None
            }
        }
    })
    
    user_id: str = Field(..., description="User identifier")
    email: EmailStr = Field(..., description="Email address")
    tron_address: Optional[str] = Field(None, description="TRON address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    status: str = Field(..., description="Account status")
    roles: List[str] = Field(..., description="User roles")
    profile: Dict[str, Any] = Field(..., description="Profile information")


class UserProfile(BaseModel):
    """
    Detailed user profile model.
    
    Includes complete user information and statistics.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "user-123",
            "email": "user@example.com",
            "tron_address": "TXyz123...",
            "display_name": "John Doe",
            "bio": "Lucid blockchain user",
            "avatar_url": None,
            "created_at": "2025-10-14T12:00:00Z",
            "updated_at": "2025-10-14T12:00:00Z",
            "last_login": "2025-10-14T12:00:00Z",
            "status": "active",
            "roles": ["user"],
            "preferences": {},
            "statistics": {
                "sessions_created": 10,
                "total_observation_time": 3600
            }
        }
    })
    
    user_id: str = Field(..., description="User identifier")
    email: EmailStr = Field(..., description="Email address")
    tron_address: Optional[str] = Field(None, description="TRON address")
    display_name: str = Field(..., description="Display name")
    bio: Optional[str] = Field(None, description="User bio")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    status: str = Field(..., description="Account status")
    roles: List[str] = Field(..., description="User roles")
    preferences: Dict[str, Any] = Field(..., description="User preferences")
    statistics: Dict[str, Any] = Field(..., description="User statistics")


class UserListResponse(BaseModel):
    """
    Paginated list of users response.
    
    Attributes:
        users: List of user responses
        total: Total number of users matching criteria
        skip: Number of records skipped
        limit: Maximum records returned
        has_more: Whether more records are available
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "users": [],
            "total": 100,
            "skip": 0,
            "limit": 100,
            "has_more": False
        }
    })
    
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total user count")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Maximum records")
    has_more: bool = Field(..., description="More records available")


class UserPreferences(BaseModel):
    """
    User preferences and settings.
    
    Attributes:
        user_id: User identifier
        notifications_enabled: Enable notifications
        email_notifications: Enable email notifications
        theme: UI theme preference
        language: Language preference
        timezone: Timezone preference
        date_format: Date format preference
        time_format: Time format preference
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "user-123",
            "notifications_enabled": True,
            "email_notifications": True,
            "theme": "dark",
            "language": "en",
            "timezone": "UTC",
            "date_format": "YYYY-MM-DD",
            "time_format": "24h"
        }
    })
    
    user_id: str = Field(..., description="User identifier")
    notifications_enabled: bool = Field(True, description="Notifications enabled")
    email_notifications: bool = Field(True, description="Email notifications enabled")
    theme: str = Field("dark", description="UI theme")
    language: str = Field("en", description="Language code")
    timezone: str = Field("UTC", description="Timezone")
    date_format: str = Field("YYYY-MM-DD", description="Date format")
    time_format: str = Field("24h", description="Time format")


class UserActivity(BaseModel):
    """
    User activity log entry.
    
    Attributes:
        activity_id: Activity identifier
        user_id: User identifier
        action: Action performed
        resource_type: Type of resource affected
        resource_id: Identifier of affected resource
        timestamp: Activity timestamp
        ip_address: User IP address
        user_agent: User agent string
        metadata: Additional activity metadata
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "activity_id": "activity-123",
            "user_id": "user-123",
            "action": "login",
            "resource_type": "session",
            "resource_id": None,
            "timestamp": "2025-10-14T12:00:00Z",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
            "metadata": {}
        }
    })
    
    activity_id: str = Field(..., description="Activity identifier")
    user_id: str = Field(..., description="User identifier")
    action: str = Field(..., description="Action performed")
    resource_type: Optional[str] = Field(None, description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    timestamp: datetime = Field(..., description="Activity timestamp")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Activity metadata")

