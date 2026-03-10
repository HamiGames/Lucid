"""
API Gateway Endpoints Package

This package contains all endpoint implementations for the Lucid API Gateway.
Each module corresponds to a specific endpoint category as defined in the
API specification.

Endpoint Categories:
- meta: Service metadata, health checks, version info
- auth: Authentication and authorization endpoints
- users: User management operations
- sessions: Session lifecycle management  
- manifests: Session manifest operations
- trust: Trust policy management
- chain: Blockchain proxy endpoints

All endpoints follow RESTful conventions and return standardized responses.
"""
from ..models.auth import LoginRequest, LoginResponse, VerifyRequest, AuthResponse, RefreshRequest, LogoutResponse, TokenPayload, HardwareWalletRequest, HardwareWalletResponse
from ..models.common import ErrorResponse
from ..models.user import UserCreateRequest, UserUpdateRequest, UserResponse, UserProfile, UserListResponse, UserPreferences, UserActivity
from ..models.session import SessionCreateRequest, SessionResponse, SessionDetail, SessionListResponse, SessionTerminateRequest, ManifestCreateRequest, ManifestResponse, ManifestDetail, ChunkInfo, MerkleProof
from 03_api_gateway.api..app.utils.logging import get_logger
from 03_api_gateway.api..app.config import Settings

settings = Settings()

logger = get_logger(__name__)
__version__ = "1.0.0"
__all__ = [
    "meta",
    "auth",
    "users",
    "sessions",
    "manifests",
    "trust",
    "chain",
    "logger",
    "settings",
    "Settings",
    "ErrorResponse",
    "LoginRequest",
    "LoginResponse",
    "VerifyRequest",
    "AuthResponse",
    "RefreshRequest",
    "LogoutResponse",
    "TokenPayload",
    "HardwareWalletRequest",
    "HardwareWalletResponse"
]

