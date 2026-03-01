"""
API Dependencies

This module contains FastAPI dependencies for authentication, authorization,
and other common functionality used across the Blockchain API.

Dependencies:
- get_current_user: Get current authenticated user
- verify_api_key: Verify API key for authentication
- get_database: Get database connection
- get_redis_client: Get Redis client for caching and rate limiting
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Placeholder for user model
class User:
    """Placeholder user model."""
    def __init__(self, user_id: str, username: str, permissions: list):
        self.user_id = user_id
        self.username = username
        self.permissions = permissions

# Placeholder for database connection
class Database:
    """Placeholder database connection."""
    pass

# Placeholder for Redis client
class RedisClient:
    """Placeholder Redis client."""
    pass

# In-memory storage for demo purposes
# In production, use proper database and Redis connections
# NOTE: These are placeholders - should be loaded from environment or database
import os

def _load_users_from_env():
    """Load users from environment variables."""
    users = {}
    
    # Load users from environment (optional - can be overridden by database)
    blockchain_user_id = os.getenv("USER_BLOCKCHAIN_ID", "user_001")
    blockchain_username = os.getenv("USER_BLOCKCHAIN_USERNAME", "blockchain_user")
    blockchain_perms = os.getenv("USER_BLOCKCHAIN_PERMISSIONS", "read,write,admin").split(",")
    users["blockchain_user"] = User(blockchain_user_id, blockchain_username, blockchain_perms)
    
    api_user_id = os.getenv("USER_API_ID", "user_002")
    api_username = os.getenv("USER_API_USERNAME", "api_user")
    api_perms = os.getenv("USER_API_PERMISSIONS", "read,write").split(",")
    users["api_user"] = User(api_user_id, api_username, api_perms)
    
    readonly_user_id = os.getenv("USER_READONLY_ID", "user_003")
    readonly_username = os.getenv("USER_READONLY_USERNAME", "readonly_user")
    readonly_perms = os.getenv("USER_READONLY_PERMISSIONS", "read").split(",")
    users["readonly_user"] = User(readonly_user_id, readonly_username, readonly_perms)
    
    return users

def _load_api_keys_from_env():
    """Load API keys from environment variables."""
    api_keys = {}
    
    # Load API keys from environment
    # Format: API_KEY_<name>=<key_value> maps to user_id
    blockchain_key = os.getenv("API_KEY_BLOCKCHAIN", "")
    if blockchain_key:
        api_keys[blockchain_key] = os.getenv("API_KEY_BLOCKCHAIN_USER", "blockchain_user")
    
    api_key = os.getenv("API_KEY_API", "")
    if api_key:
        api_keys[api_key] = os.getenv("API_KEY_API_USER", "api_user")
    
    readonly_key = os.getenv("API_KEY_READONLY", "")
    if readonly_key:
        api_keys[readonly_key] = os.getenv("API_KEY_READONLY_USER", "readonly_user")
    
    return api_keys

USERS_DB = _load_users_from_env()
API_KEYS = _load_api_keys_from_env()

def get_database() -> Database:
    """Get database connection."""
    # In production, return actual database connection
    return Database()

def get_redis_client() -> RedisClient:
    """Get Redis client for caching and rate limiting."""
    # In production, return actual Redis client
    return RedisClient()

def verify_api_key(api_key: str = Header(None)) -> str:
    """Verify API key and return user ID."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return API_KEYS[api_key]

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    api_key: str = Header(None)
) -> User:
    """Get current authenticated user from JWT token or API key."""
    
    # Try API key first
    if api_key and api_key in API_KEYS:
        user_id = API_KEYS[api_key]
        if user_id in USERS_DB:
            return USERS_DB[user_id]
    
    # Try JWT token
    if credentials:
        token = credentials.credentials
        # In production, validate JWT token using SecurityManager
        # This is a placeholder - should use proper JWT validation
        from ..security import SecurityManager
        from ..config import settings
        
        try:
            security_manager = SecurityManager(settings.SECRET_KEY, settings.ALGORITHM)
            payload = security_manager.verify_token(token)
            if payload:
                user_id = payload.get("user_id")
                if user_id and user_id in USERS_DB:
                    return USERS_DB[user_id]
        except Exception as e:
            logger.debug(f"JWT token validation failed: {e}")
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )

def require_permission(permission: str):
    """Dependency factory for requiring specific permissions."""
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return user
    return permission_checker

def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin permissions."""
    if "admin" not in user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    return user

def require_read_permission(user: User = Depends(get_current_user)) -> User:
    """Require read permissions."""
    if "read" not in user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read permissions required"
        )
    return user

def require_write_permission(user: User = Depends(get_current_user)) -> User:
    """Require write permissions."""
    if "write" not in user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write permissions required"
        )
    return user
