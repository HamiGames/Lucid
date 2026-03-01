"""
Lucid Authentication Service - Session Model
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TokenType(str, Enum):
    """JWT token types"""
    ACCESS = "access"
    REFRESH = "refresh"


class Session(BaseModel):
    """Session model"""
    
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User ID")
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    
    # Session metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    
    # Device information
    user_agent: Optional[str] = Field(None, description="User agent string")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    device_type: Optional[str] = Field(None, description="Device type")
    location: Optional[str] = Field(None, description="Geographic location")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiry time")
    last_activity_at: datetime = Field(default_factory=datetime.utcnow, description="Last activity time")
    
    # Status
    is_active: bool = Field(default=True, description="Session active status")
    revoked: bool = Field(default=False, description="Session revoked status")
    revoked_at: Optional[datetime] = Field(None, description="Revocation time")
    revoked_reason: Optional[str] = Field(None, description="Revocation reason")
    
    def dict(self, *args, **kwargs):
        """Override dict to handle datetime serialization"""
        d = super().dict(*args, **kwargs)
        # Convert datetimes to ISO format strings
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
        return d
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_1234567890abcdef",
                "user_id": "usr_1234567890abcdef",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "metadata": {
                    "login_method": "tron_signature"
                },
                "user_agent": "Mozilla/5.0...",
                "ip_address": "192.168.1.1",
                "device_type": "desktop",
                "created_at": "2025-01-01T00:00:00Z",
                "expires_at": "2025-01-08T00:00:00Z",
                "is_active": True
            }
        }


class TokenPayload(BaseModel):
    """JWT token payload"""
    
    user_id: str = Field(..., description="User ID")
    role: Optional[str] = Field(None, description="User role")
    type: str = Field(..., description="Token type (access/refresh)")
    jti: str = Field(..., description="JWT ID (unique token identifier)")
    iat: Optional[datetime] = Field(None, description="Issued at")
    exp: Optional[datetime] = Field(None, description="Expiration time")
    nbf: Optional[datetime] = Field(None, description="Not before")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "usr_1234567890abcdef",
                "role": "USER",
                "type": "access",
                "jti": "jwt_1234567890abcdef",
                "iat": "2025-01-01T00:00:00Z",
                "exp": "2025-01-01T00:15:00Z"
            }
        }


class SessionResponse(BaseModel):
    """Session response (public data only)"""
    
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_activity_at: datetime
    is_active: bool
    revoked: bool = Field(default=False, description="Session revoked status")
    device_type: Optional[str] = None
    location: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_1234567890abcdef",
                "user_id": "usr_1234567890abcdef",
                "created_at": "2025-01-01T00:00:00Z",
                "expires_at": "2025-01-08T00:00:00Z",
                "last_activity_at": "2025-01-01T00:00:00Z",
                "is_active": True,
                "revoked": False,
                "device_type": "desktop",
                "metadata": {
                    "login_method": "tron_signature"
                }
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    
    refresh_token: str = Field(..., description="Refresh token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RefreshTokenResponse(BaseModel):
    """Refresh token response"""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900
            }
        }

