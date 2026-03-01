"""
Authentication Middleware

File: 03-api-gateway/api/app/middleware/auth.py
Purpose: Handles JWT token validation and user authentication for protected endpoints.
All configuration from environment variables via app.config.
"""

import logging
from typing import Optional, List
from fastapi import Request
from starlette.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthMiddleware:
    """Authentication middleware for request processing"""
    
    # Public endpoints that don't require authentication (from config or defaults)
    PUBLIC_PATHS: List[str] = [
        "/health",
        "/api/v1/meta/info",
        "/api/v1/meta/health",
        "/api/v1/meta/version",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/verify",
        "/api/v1/auth/refresh",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    def __init__(self, app):
        self.app = app
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self.jwt_secret = settings.JWT_SECRET_KEY
        logger.info("AuthMiddleware initialized")
    
    async def __call__(self, scope, receive, send):
        """Process request through authentication middleware"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        path = request.url.path
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(path):
            await self.app(scope, receive, send)
            return
        
        # Extract and validate token
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            # No token provided - let the route handler decide if auth is required
            await self.app(scope, receive, send)
            return
        
        if not auth_header.startswith("Bearer "):
            response = JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "LUCID_ERR_2001",
                        "message": "Invalid authorization header format"
                    }
                }
            )
            await response(scope, receive, send)
            return
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate token (delegate to auth service or validate locally)
        is_valid, user_data = await self._validate_token(token)
        
        if not is_valid:
            response = JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "LUCID_ERR_2001",
                        "message": "Invalid or expired token"
                    }
                }
            )
            await response(scope, receive, send)
            return
        
        # Add user data to request state for downstream use
        if user_data:
            scope["state"] = scope.get("state", {})
            scope["state"]["user"] = user_data
        
        await self.app(scope, receive, send)
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no authentication required)"""
        return any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS)
    
    async def _validate_token(self, token: str) -> tuple[bool, Optional[dict]]:
        """
        Validate JWT token.
        Returns (is_valid, user_data) tuple.
        """
        try:
            # Import here to avoid circular imports
            from jose import jwt, JWTError
            
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            user_data = {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role", "USER"),
            }
            
            return True, user_data
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False, None
