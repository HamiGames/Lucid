"""
Authentication Middleware for GUI API Bridge
File: gui-api-bridge/gui-api-bridge/middleware/auth.py
"""

import logging
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, JWTError

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication"""
    
    def __init__(self, app, config):
        """Initialize auth middleware"""
        super().__init__(app)
        self.config = config
    
    async def dispatch(self, request: Request, call_next):
        """Validate JWT token in request"""
        
        # Skip auth for health check and public endpoints
        skip_auth_paths = ["/health", "/", "/api/v1"]
        if request.url.path in skip_auth_paths or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)
        
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"Missing Authorization header for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Authorization header"},
            )
        
        try:
            # Extract token
            parts = auth_header.split()
            if len(parts) != 2 or parts[0] != "Bearer":
                logger.warning(f"Invalid Authorization header format for {request.url.path}")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid Authorization header format"},
                )
            
            token = parts[1]
            
            # Validate token
            try:
                payload = jwt.decode(
                    token,
                    self.config.JWT_SECRET_KEY,
                    algorithms=[self.config.JWT_ALGORITHM],
                )
                # Add user info to request state
                request.state.user = payload
                logger.debug(f"JWT validated for user {payload.get('sub')}")
            
            except JWTError as e:
                logger.warning(f"JWT validation failed: {e}")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid token"},
                )
        
        except Exception as e:
            logger.error(f"Auth middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Authentication error"},
            )
        
        return await call_next(request)
