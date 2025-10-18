"""
Lucid Authentication Service - User Model
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from .permissions import Role


class User(BaseModel):
    """User model"""
    
    user_id: str = Field(..., description="Unique user identifier")
    tron_address: str = Field(..., description="TRON wallet address")
    email: Optional[str] = Field(None, description="User email (optional)")
    role: Role = Field(default=Role.USER, description="User role")
    
    # Hardware wallet info
    hardware_wallet_type: Optional[str] = Field(None, description="Hardware wallet type")
    hardware_wallet_path: Optional[str] = Field(None, description="Hardware wallet derivation path")
    
    # Profile information
    display_name: Optional[str] = Field(None, description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    
    # Account status
    is_active: bool = Field(default=True, description="Account active status")
    is_verified: bool = Field(default=False, description="Email verification status")
    kyc_verified: bool = Field(default=False, description="KYC verification status")
    
    # Security
    mfa_enabled: bool = Field(default=False, description="Multi-factor authentication enabled")
    login_attempts: int = Field(default=0, description="Failed login attempts")
    locked_until: Optional[datetime] = Field(None, description="Account lock expiry")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    @validator("tron_address")
    def validate_tron_address(cls, v):
        """Validate TRON address format"""
        if not v:
            raise ValueError("TRON address is required")
        if not v.startswith("T"):
            raise ValueError("TRON address must start with 'T'")
        if len(v) != 34:
            raise ValueError("TRON address must be 34 characters")
        return v
    
    @validator("email")
    def validate_email(cls, v):
        """Validate email format"""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "usr_1234567890abcdef",
                "tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v",
                "email": "user@example.com",
                "role": "USER",
                "display_name": "John Doe",
                "is_active": True,
                "is_verified": False,
                "kyc_verified": False,
                "mfa_enabled": False,
                "created_at": "2025-01-01T00:00:00Z"
            }
        }


class UserCreate(BaseModel):
    """User creation request"""
    
    tron_address: str = Field(..., description="TRON wallet address")
    signature: str = Field(..., description="TRON signature for verification")
    message: str = Field(..., description="Signed message")
    email: Optional[str] = Field(None, description="User email (optional)")
    display_name: Optional[str] = Field(None, description="Display name")
    hardware_wallet_type: Optional[str] = Field(None, description="Hardware wallet type")
    
    @validator("tron_address")
    def validate_tron_address(cls, v):
        """Validate TRON address format"""
        if not v or not v.startswith("T") or len(v) != 34:
            raise ValueError("Invalid TRON address")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v",
                "signature": "0x1234567890abcdef...",
                "message": "Sign this message to authenticate with Lucid: 2025-01-01T00:00:00Z",
                "email": "user@example.com",
                "display_name": "John Doe"
            }
        }


class UserUpdate(BaseModel):
    """User update request"""
    
    email: Optional[str] = Field(None, description="User email")
    display_name: Optional[str] = Field(None, description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "newemail@example.com",
                "display_name": "Jane Doe",
                "avatar_url": "https://example.com/avatar.jpg"
            }
        }


class UserResponse(BaseModel):
    """User response (public data only)"""
    
    user_id: str
    tron_address: str
    email: Optional[str] = None
    role: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    kyc_verified: bool
    hardware_wallet_type: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "usr_1234567890abcdef",
                "tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v",
                "email": "user@example.com",
                "role": "USER",
                "display_name": "John Doe",
                "is_active": True,
                "is_verified": False,
                "kyc_verified": False,
                "hardware_wallet_type": "ledger",
                "created_at": "2025-01-01T00:00:00Z"
            }
        }


class LoginRequest(BaseModel):
    """Login request"""
    
    tron_address: str = Field(..., description="TRON wallet address")
    signature: str = Field(..., description="TRON signature")
    message: str = Field(..., description="Signed message")
    hardware_wallet: bool = Field(default=False, description="Using hardware wallet")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v",
                "signature": "0x1234567890abcdef...",
                "message": "Sign this message to authenticate with Lucid: 2025-01-01T00:00:00Z",
                "hardware_wallet": False
            }
        }


class LoginResponse(BaseModel):
    """Login response"""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")
    user: UserResponse
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900,
                "user": {
                    "user_id": "usr_1234567890abcdef",
                    "tron_address": "TXYZPvGUMN8cXPFQtPqrQjBBVSFQwgFQ1v",
                    "role": "USER"
                }
            }
        }

