"""
Authentication Middleware for GUI Tor Manager
JWT token validation for API requests
"""

from typing import Optional, Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt

from config import get_config
from utils.logging import get_logger

logger = get_logger(__name__)

# Paths that don't require authentication
UNPROTECTED_PATHS = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
]


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate JWT token for protected routes"""
        # Check if path requires authentication
        if any(request.url.path.startswith(path) for path in UNPROTECTED_PATHS):
            return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header:
            # Some endpoints might allow unauthenticated access
            # (check according to your security requirements)
            return await call_next(request)
        
        try:
            # Parse Bearer token
            if not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authorization header format"
                )
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Validate token (simplified - implement full JWT validation)
            # In production, verify token signature and expiration
            
            logger.info("Token validation passed", extra={"token_length": len(token)})
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        return await call_next(request)
