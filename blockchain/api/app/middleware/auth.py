"""
Authentication Middleware

This module contains authentication middleware for the Blockchain API.
Handles JWT token verification, API key validation, and user authentication.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from typing import Optional

from ..security import SecurityManager
from ..config import settings

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for API requests."""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_manager = SecurityManager(settings.SECRET_KEY, settings.ALGORITHM)
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication middleware."""
        
        # Skip authentication for health checks and public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Extract authentication information
        auth_header = request.headers.get("Authorization")
        api_key = request.headers.get("X-API-Key")
        
        # Try JWT token authentication first
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user = await self._authenticate_jwt_token(token)
            if user:
                request.state.user = user
                return await call_next(request)
        
        # Try API key authentication
        if api_key:
            user = await self._authenticate_api_key(api_key)
            if user:
                request.state.user = user
                return await call_next(request)
        
        # Authentication failed
        logger.warning(f"Authentication failed for {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public and doesn't require authentication."""
        public_endpoints = [
            "/health",
            "/api/v1/health",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json"
        ]
        
        return any(path.startswith(endpoint) for endpoint in public_endpoints)
    
    async def _authenticate_jwt_token(self, token: str) -> Optional[dict]:
        """Authenticate JWT token."""
        try:
            payload = self.security_manager.verify_token(token)
            if payload:
                return {
                    "user_id": payload.get("user_id"),
                    "username": payload.get("username"),
                    "permissions": payload.get("permissions", []),
                    "auth_method": "jwt"
                }
        except Exception as e:
            logger.error(f"JWT token authentication failed: {e}")
        
        return None
    
    async def _authenticate_api_key(self, api_key: str) -> Optional[dict]:
        """Authenticate API key."""
        import os
        try:
            # Get API keys from environment variables
            # Format: API_KEY_<name>=<key_value> or API_KEY_<name>_USER=<user_id>
            # Example: API_KEY_BLOCKCHAIN=your-key-here, API_KEY_BLOCKCHAIN_USER=blockchain_user
            
            # Check environment for API key mappings
            # In production, this should query a database or use a proper API key service
            valid_api_keys = {}
            
            # Load API keys from environment (optional - can be overridden by database)
            env_api_keys = {
                os.getenv("API_KEY_BLOCKCHAIN", ""): {
                    "user_id": os.getenv("API_KEY_BLOCKCHAIN_USER", "blockchain_user"),
                    "username": os.getenv("API_KEY_BLOCKCHAIN_USERNAME", "blockchain_user"),
                    "permissions": os.getenv("API_KEY_BLOCKCHAIN_PERMISSIONS", "read,write,admin").split(",")
                },
                os.getenv("API_KEY_READONLY", ""): {
                    "user_id": os.getenv("API_KEY_READONLY_USER", "readonly_user"),
                    "username": os.getenv("API_KEY_READONLY_USERNAME", "readonly_user"),
                    "permissions": os.getenv("API_KEY_READONLY_PERMISSIONS", "read").split(",")
                }
            }
            
            # Remove empty keys
            valid_api_keys = {k: v for k, v in env_api_keys.items() if k}
            
            # Check if API key is valid
            if api_key in valid_api_keys:
                user_info = valid_api_keys[api_key]
                return {
                    "user_id": user_info["user_id"],
                    "username": user_info["username"],
                    "permissions": user_info["permissions"],
                    "auth_method": "api_key"
                }
            
            # TODO: In production, query database for API key validation
            # This is a placeholder - should be replaced with database lookup
            logger.warning(f"API key authentication attempted but key not found in environment")
            
        except Exception as e:
            logger.error(f"API key authentication failed: {e}")
        
        return None