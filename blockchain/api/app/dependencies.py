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
USERS_DB = {
    "blockchain_user": User("user_001", "blockchain_user", ["read", "write", "admin"]),
    "api_user": User("user_002", "api_user", ["read", "write"]),
    "readonly_user": User("user_003", "readonly_user", ["read"])
}

API_KEYS = {
    "VALID_BLOCKCHAIN_API_TOKEN": "blockchain_user",
    "VALID_API_KEY": "api_user",
    "READONLY_API_KEY": "readonly_user"
}

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
        # In production, validate JWT token
        if token == "VALID_BLOCKCHAIN_API_TOKEN":
            return USERS_DB["blockchain_user"]
        elif token == "VALID_JWT_TOKEN":
            return USERS_DB["api_user"]
    
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
