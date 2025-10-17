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
        try:
            # In production, validate against database
            # For now, use placeholder validation
            if api_key == "VALID_BLOCKCHAIN_API_TOKEN":
                return {
                    "user_id": "blockchain_user",
                    "username": "blockchain_user",
                    "permissions": ["read", "write", "admin"],
                    "auth_method": "api_key"
                }
            elif api_key == "VALID_API_KEY":
                return {
                    "user_id": "api_user",
                    "username": "api_user",
                    "permissions": ["read", "write"],
                    "auth_method": "api_key"
                }
            elif api_key == "READONLY_API_KEY":
                return {
                    "user_id": "readonly_user",
                    "username": "readonly_user",
                    "permissions": ["read"],
                    "auth_method": "api_key"
                }
        except Exception as e:
            logger.error(f"API key authentication failed: {e}")
        
        return None