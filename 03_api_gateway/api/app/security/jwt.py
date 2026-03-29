"""
File: /app/03_api_gateway/api/app/security/jwt.py
x-lucid-file-path: /app/03_api_gateway/api/app/security/jwt.py
x-lucid-file-type: python
"""

from __future__ import annotations

import jwt as JWT
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import uuid
import os
from pydantic import BaseModel, Field, field_validator
from api.app.config import get_settings

try:
    from api.app.utils.logging import get_logger, setup_logging
    logger = get_logger()
    settings = get_settings()
    setup_logging(settings)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    settings = get_settings()


class JWTConfig(BaseModel):
    """Pydantic model for JWT configuration - provides validation and flexibility"""
    
    secret_key: str = Field(env="JWT_SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, env="JWT_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="JWT_EXPIRE_DAYS")
    expire_hours: int = Field(default=1, env="JWT_EXPIRE_HOURS")
    expire_seconds: int = Field(default=0, env="JWT_EXPIRE_SECONDS")
    expire_milliseconds: int = Field(default=0, env="JWT_EXPIRE_MILLISECONDS")
    expire_microseconds: int = Field(default=0, env="JWT_EXPIRE_MICROSECONDS")
    expire_nanoseconds: int = Field(default=0, env="JWT_EXPIRE_NANOSECONDS")
    expire_timezone: str = Field(default="UTC", env="JWT_EXPIRE_TIMEZONE")
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        """Validate JWT secret key is strong enough"""
        if not v:
            raise ValueError('JWT_SECRET_KEY must be set')
        if len(v) < 32:
            raise ValueError('JWT_SECRET_KEY must be at least 32 characters long')
        return v
    
    @field_validator('algorithm')
    @classmethod
    def validate_algorithm(cls, v):
        """Validate JWT algorithm is supported"""
        supported = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
        if v not in supported:
            raise ValueError(f'JWT_ALGORITHM must be one of {supported}')
        return v
    
    class Config:
        env_file = ['.env.secrets', '.env.api-gateway']
        case_sensitive = False


# Initialize JWT config from settings
jwt_config = JWTConfig(
    secret_key=settings.JWT_SECRET_KEY,
    algorithm=settings.JWT_ALGORITHM,
    access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_token_expire_days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    expire_hours=settings.JWT_EXPIRE_HOURS,
    expire_seconds=settings.JWT_EXPIRE_SECONDS,
    expire_milliseconds=settings.JWT_EXPIRE_MILLISECONDS,
    expire_microseconds=settings.JWT_EXPIRE_MICROSECONDS,
    expire_nanoseconds=settings.JWT_EXPIRE_NANOSECONDS,
    expire_timezone=settings.JWT_EXPIRE_TIMEZONE,
)

# Runtime token blacklist
blacklisted_tokens: List[str] = []


def encode_jwt(payload: Dict[str, Any]) -> str:
    """Encode a JWT token"""
    try:
        payload = payload.copy()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=jwt_config.access_token_expire_minutes)
        payload["iat"] = datetime.now(timezone.utc)
        payload["jti"] = str(uuid.uuid4())
        payload["iss"] = "api-gateway"
        payload["aud"] = "lucid-blockchain"
        return JWT.encode(payload, jwt_config.secret_key, algorithm=jwt_config.algorithm)
    except Exception as e:
        logger.error(f"Error encoding JWT: {e}")
        raise


def decode_jwt(token: str) -> Dict[str, Any]:
    """Decode a JWT token"""
    try:
        return JWT.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
    except Exception as e:
        logger.error(f"Error decoding JWT: {e}")
        raise


def verify_jwt(token: str) -> bool:
    """Verify a JWT token"""
    try:
        JWT.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
        return True
    except Exception as e:
        logger.error(f"Error verifying JWT: {e}")
        return False


def extract_token_from_header(authorization: str) -> str:
    """Extract a JWT token from the authorization header"""
    try:
        token = authorization.split(" ")[1]
        JWT.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
        return token
    except Exception as e:
        logger.error(f"Error extracting token from header: {e}")
        raise


def create_token_payload(user_id: str, role: str) -> Dict[str, Any]:
    """Create a JWT token payload"""
    try:
        return {
            "sub": user_id,
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=jwt_config.access_token_expire_minutes),
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),
            "iss": "api-gateway",
            "aud": "lucid-blockchain"
        }
    except Exception as e:
        logger.error(f"Error creating token payload: {e}")
        raise


def is_token_expired(token: str) -> bool:
    """Check if a JWT token is expired"""
    try:
        payload = JWT.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
        return payload.get("exp", datetime.now(timezone.utc)) < datetime.now(timezone.utc)
    except Exception as e:
        logger.error(f"Error checking if token is expired: {e}")
        return True


def get_token_expiry(token: str) -> Optional[datetime]:
    """Get the expiry time of a JWT token"""
    try:
        payload = JWT.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
        return payload.get("exp") if "exp" in payload else None
    except Exception as e:
        logger.error(f"Error getting token expiry: {e}")
        raise


def get_token_payload(token: str) -> Dict[str, Any]:
    """Get the payload of a JWT token"""
    try:
        return JWT.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
    except Exception as e:
        logger.error(f"Error getting token payload: {e}")
        raise


def is_token_valid(token: str) -> bool:
    """Check if a JWT token is valid"""
    try:
        JWT.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
        return True
    except Exception as e:
        logger.error(f"Error checking if token is valid: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """Check if a JWT token is blacklisted"""
    try:
        payload = JWT.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
        return payload.get("jti") in blacklisted_tokens
    except Exception as e:
        logger.error(f"Error checking if token is blacklisted: {e}")
        return True


def blacklist_token(token: str) -> None:
    """Blacklist a JWT token"""
    try:
        payload = JWT.decode(token, jwt_config.secret_key, algorithms=[jwt_config.algorithm])
        jti = payload.get("jti")
        if jti and jti not in blacklisted_tokens:
            blacklisted_tokens.append(jti)
    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")
        raise


def cleanup_expired_tokens() -> None:
    """Cleanup expired tokens from blacklist"""
    global blacklisted_tokens
    try:
        blacklisted_tokens = [jti for jti in blacklisted_tokens if jti]  # Keep valid JTIs
    except Exception as e:
        logger.error(f"Error cleaning up expired tokens: {e}")


def get_blacklisted_tokens() -> List[str]:
    """Get the list of blacklisted tokens"""
    return blacklisted_tokens


def get_jwt_config() -> JWTConfig:
    """Get the JWT configuration object - allows external modules to access config"""
    return jwt_config
