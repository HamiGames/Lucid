"""
User Data Models

Pydantic models for user entities in the Lucid system.
Handles user accounts, profiles, authentication, and permissions.

Database Collection: users
Phase: Phase 1 - Foundation
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    USER = "user"
    NODE_OPERATOR = "node_operator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"


class HardwareWalletInfo(BaseModel):
    """Hardware wallet information"""
    type: str = Field(..., description="Hardware wallet type (ledger, trezor, keepkey)")
    model: Optional[str] = Field(None, description="Hardware wallet model")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    connected_at: Optional[datetime] = Field(None, description="Connection timestamp")
    public_key: Optional[str] = Field(None, description="Public key")
    
    class Config:
        use_enum_values = True


class UserBase(BaseModel):
    """Base user model with common fields"""
    email: EmailStr = Field(..., description="User email address")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")
    tron_address: str = Field(..., description="TRON wallet address")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="User account status")
    
    @validator('tron_address')
    def validate_tron_address(cls, v):
        """Validate TRON address format"""
        if not v.startswith('T') or len(v) != 34:
            raise ValueError('Invalid TRON address format')
        return v
    
    class Config:
        use_enum_values = True


class UserCreate(UserBase):
    """Model for creating a new user"""
    password: Optional[str] = Field(None, min_length=8, description="User password (optional for TRON auth)")
    hardware_wallet: Optional[HardwareWalletInfo] = Field(None, description="Hardware wallet info")
    referral_code: Optional[str] = Field(None, description="Referral code")


class UserUpdate(BaseModel):
    """Model for updating user information"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    profile: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class User(UserBase):
    """User model for API responses"""
    user_id: str = Field(..., description="Unique user identifier")
    profile: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User profile data")
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User preferences")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    email_verified: bool = Field(default=False, description="Email verification status")
    tron_verified: bool = Field(default=False, description="TRON address verification status")
    
    # Statistics
    total_sessions: int = Field(default=0, description="Total number of sessions")
    total_chunks_uploaded: int = Field(default=0, description="Total chunks uploaded")
    total_storage_used: int = Field(default=0, description="Total storage used (bytes)")
    
    # Node operator specific (if applicable)
    is_node_operator: bool = Field(default=False, description="Whether user operates nodes")
    node_count: Optional[int] = Field(None, description="Number of nodes operated")
    total_poot_score: Optional[float] = Field(None, description="Total PoOT score")
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UserInDB(User):
    """User model as stored in database (includes sensitive fields)"""
    password_hash: Optional[str] = Field(None, description="Hashed password")
    salt: Optional[str] = Field(None, description="Password salt")
    tron_signature: Optional[str] = Field(None, description="TRON signature for verification")
    api_keys: List[str] = Field(default_factory=list, description="API keys")
    hardware_wallet: Optional[HardwareWalletInfo] = Field(None, description="Hardware wallet info")
    
    # Security fields
    failed_login_attempts: int = Field(default=0, description="Failed login attempt count")
    last_failed_login: Optional[datetime] = Field(None, description="Last failed login timestamp")
    account_locked_until: Optional[datetime] = Field(None, description="Account lock expiration")
    
    # Audit fields
    created_by: Optional[str] = Field(None, description="User ID that created this account")
    updated_by: Optional[str] = Field(None, description="User ID that last updated this account")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UserProfile(BaseModel):
    """User profile information"""
    display_name: Optional[str] = Field(None, description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    location: Optional[str] = Field(None, description="User location")
    website: Optional[str] = Field(None, description="User website")
    social_links: Optional[Dict[str, str]] = Field(None, description="Social media links")


class UserPreferences(BaseModel):
    """User preferences and settings"""
    language: str = Field(default="en", description="Preferred language")
    timezone: str = Field(default="UTC", description="User timezone")
    email_notifications: bool = Field(default=True, description="Enable email notifications")
    session_notifications: bool = Field(default=True, description="Enable session notifications")
    payout_notifications: bool = Field(default=True, description="Enable payout notifications")
    theme: str = Field(default="dark", description="UI theme preference")
    auto_anchor_sessions: bool = Field(default=True, description="Automatically anchor sessions to blockchain")


class UserStatistics(BaseModel):
    """User statistics and metrics"""
    user_id: str = Field(..., description="User identifier")
    total_sessions: int = Field(default=0, description="Total sessions created")
    active_sessions: int = Field(default=0, description="Currently active sessions")
    completed_sessions: int = Field(default=0, description="Completed sessions")
    total_chunks: int = Field(default=0, description="Total chunks uploaded")
    total_storage_bytes: int = Field(default=0, description="Total storage used")
    total_bandwidth_bytes: int = Field(default=0, description="Total bandwidth used")
    avg_session_duration_seconds: Optional[float] = Field(None, description="Average session duration")
    
    # Node operator statistics (if applicable)
    nodes_operated: Optional[int] = Field(None, description="Number of nodes operated")
    total_poot_score: Optional[float] = Field(None, description="Total PoOT score")
    total_earnings_usdt: Optional[float] = Field(None, description="Total earnings in USDT")
    last_payout: Optional[datetime] = Field(None, description="Last payout timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

