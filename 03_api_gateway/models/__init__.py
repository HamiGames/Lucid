"""
Data Models Package

Contains all Pydantic models for request/response validation and serialization.

Model Categories:
- common: Shared models and base classes
- user: User-related models
- session: Session-related models
- auth: Authentication-related models

All models follow Pydantic V2 conventions and include:
- Type validation
- Field constraints
- JSON serialization
- Documentation strings
"""

__version__ = "1.0.0"

from ..models.common import ErrorResponse
from ..models.user import (
    UserCreateRequest, UserUpdateRequest, UserResponse, UserProfile, 
    UserListResponse, UserPreferences, UserActivity)
from ..models.session import( 
        SessionCreateRequest, SessionResponse, SessionDetail, SessionListResponse, 
        SessionTerminateRequest, ManifestCreateRequest, ManifestResponse, ManifestDetail,
        ChunkInfo, MerkleProof)
from ..models.auth import (
    LoginRequest, LoginResponse, VerifyRequest, AuthResponse, RefreshRequest,
    LogoutResponse, TokenPayload, HardwareWalletRequest, HardwareWalletResponse)
from 03_api_gateway.api..app.config import Settings
settings = Settings()
from 03_api_gateway.api..app.utils.logging import get_logger
logger = get_logger(__name__)


__all__ = [
    "ErrorResponse","UserResponse","UserProfile","UserListResponse","UserPreferences","UserActivity",
    "UserCreateRequest", "UserUpdateRequest", "SessionCreateRequest", "SessionResponse", "SessionDetail",
    "SessionListResponse", "SessionTerminateRequest", "ManifestCreateRequest", "ManifestResponse",
    "ManifestDetail", "ChunkInfo", "MerkleProof", "LoginRequest", "LoginResponse", "VerifyRequest",
    "AuthResponse", "RefreshRequest", "LogoutResponse", "TokenPayload", "HardwareWalletRequest",
    "HardwareWalletResponse", "logger", "settings", "Settings"
]

