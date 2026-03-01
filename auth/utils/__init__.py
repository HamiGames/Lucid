"""
Lucid Authentication Service - Utilities Package
"""

from .crypto import verify_tron_signature, hash_password, verify_password
from .validators import validate_tron_address, validate_email, validate_jwt_token
from .jwt_handler import decode_jwt, encode_jwt
from .exceptions import (
    AuthenticationError,
    TokenExpiredError,
    InvalidTokenError,
    SessionNotFoundError,
    MaxSessionsExceededError,
    HardwareWalletError
)

__all__ = [
    "verify_tron_signature",
    "hash_password",
    "verify_password",
    "validate_tron_address",
    "validate_email",
    "validate_jwt_token",
    "decode_jwt",
    "encode_jwt",
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidTokenError",
    "SessionNotFoundError",
    "MaxSessionsExceededError",
    "HardwareWalletError"
]

