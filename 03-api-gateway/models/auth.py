"""
Authentication Data Models

Models for authentication and authorization operations including:
- Login and verification
- JWT tokens
- Hardware wallet authentication
- Session management

All auth models integrate with Cluster 09 (Authentication Service).
"""

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum


class TokenType(str, Enum):
    """JWT token types"""
    ACCESS = "access"
    REFRESH = "refresh"


class LoginRequest(BaseModel):
    """
    Request model for initiating login.
    
    Attributes:
        email: User email address for magic link
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com"
        }
    })
    
    email: EmailStr = Field(..., description="User email address")


class LoginResponse(BaseModel):
    """
    Response model for login initiation.
    
    Attributes:
        message: Confirmation message
        email: Email address where link was sent
        expires_in: Magic link expiration time in seconds
        request_id: Request identifier for tracking
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "Magic link sent to your email",
            "email": "user@example.com",
            "expires_in": 900,
            "request_id": "req-123"
        }
    })
    
    message: str = Field(..., description="Confirmation message")
    email: EmailStr = Field(..., description="Email address")
    expires_in: int = Field(..., description="Expiration time in seconds")
    request_id: str = Field(..., description="Request identifier")


class VerifyRequest(BaseModel):
    """
    Request model for TOTP verification.
    
    Attributes:
        email: User email address
        code: TOTP verification code
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "user@example.com",
            "code": "123456"
        }
    })
    
    email: EmailStr = Field(..., description="User email address")
    code: str = Field(..., min_length=6, max_length=6, description="TOTP code")


class AuthResponse(BaseModel):
    """
    Standard authentication response model.
    
    Attributes:
        access_token: JWT access token
        refresh_token: JWT refresh token
        token_type: Token type (always "Bearer")
        expires_in: Access token expiration time in seconds
        user_id: Authenticated user identifier
        email: User email address
        roles: List of user roles
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJ...",
            "refresh_token": "eyJ...",
            "token_type": "Bearer",
            "expires_in": 900,
            "user_id": "user-123",
            "email": "user@example.com",
            "roles": ["user"]
        }
    })
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Expiration time in seconds")
    user_id: str = Field(..., description="User identifier")
    email: EmailStr = Field(..., description="User email")
    roles: List[str] = Field(..., description="User roles")


class RefreshRequest(BaseModel):
    """
    Request model for token refresh.
    
    Attributes:
        refresh_token: Valid refresh token
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "refresh_token": "eyJ..."
        }
    })
    
    refresh_token: str = Field(..., description="Refresh token")


class LogoutResponse(BaseModel):
    """
    Response model for logout.
    
    Attributes:
        message: Confirmation message
        timestamp: Logout timestamp
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "Logout successful",
            "timestamp": "2025-10-14T12:00:00Z"
        }
    })
    
    message: str = Field(..., description="Confirmation message")
    timestamp: datetime = Field(..., description="Logout timestamp")


class TokenPayload(BaseModel):
    """
    JWT token payload model.
    
    Attributes:
        user_id: User identifier
        email: User email
        roles: User roles
        exp: Expiration timestamp
        iat: Issued at timestamp
        token_type: Token type
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "user-123",
            "email": "user@example.com",
            "roles": ["user"],
            "exp": 1729000000,
            "iat": 1728999100,
            "token_type": "access"
        }
    })
    
    user_id: str = Field(..., description="User identifier")
    email: EmailStr = Field(..., description="User email")
    roles: List[str] = Field(..., description="User roles")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    token_type: str = Field(..., description="Token type")


class HardwareWalletRequest(BaseModel):
    """
    Request model for hardware wallet connection.
    
    Attributes:
        wallet_type: Type of hardware wallet (ledger/trezor/keepkey)
        derivation_path: BIP-44 derivation path
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "wallet_type": "ledger",
            "derivation_path": "m/44'/195'/0'/0/0"
        }
    })
    
    wallet_type: str = Field(..., description="Wallet type")
    derivation_path: Optional[str] = Field(
        None,
        description="BIP-44 derivation path"
    )


class HardwareWalletResponse(BaseModel):
    """
    Response model for hardware wallet connection.
    
    Attributes:
        connected: Whether wallet is connected
        wallet_type: Type of hardware wallet
        address: Wallet address
        message: Status message
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "connected": True,
            "wallet_type": "ledger",
            "address": "0x1234...",
            "message": "Hardware wallet connected successfully"
        }
    })
    
    connected: bool = Field(..., description="Connection status")
    wallet_type: str = Field(..., description="Wallet type")
    address: str = Field(..., description="Wallet address")
    message: str = Field(..., description="Status message")


class TronSignatureRequest(BaseModel):
    """
    Request model for TRON signature authentication.
    
    Attributes:
        tron_address: TRON blockchain address
        message: Message that was signed
        signature: TRON signature
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tron_address": "TXyz123...",
            "message": "Sign in to Lucid",
            "signature": "0x..."
        }
    })
    
    tron_address: str = Field(..., description="TRON address")
    message: str = Field(..., description="Signed message")
    signature: str = Field(..., description="TRON signature")


class TronSignatureResponse(BaseModel):
    """
    Response model for TRON signature verification.
    
    Attributes:
        verified: Whether signature is valid
        tron_address: TRON address
        user_id: Associated user identifier (if exists)
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "verified": True,
            "tron_address": "TXyz123...",
            "user_id": "user-123"
        }
    })
    
    verified: bool = Field(..., description="Verification status")
    tron_address: str = Field(..., description="TRON address")
    user_id: Optional[str] = Field(None, description="User identifier")

