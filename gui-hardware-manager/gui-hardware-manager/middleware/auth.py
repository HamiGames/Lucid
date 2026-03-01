"""
Authentication middleware for JWT validation
"""

import logging
import re
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware"""
    
    # Paths that don't require authentication
    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/"
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication"""
        
        # Skip auth for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            logger.warning(f"Missing authorization header for {request.url.path}")
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        try:
            # Validate Bearer token format
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                raise HTTPException(status_code=401, detail="Invalid authorization header format")
            
            token = parts[1]
            
            # TODO: Implement JWT validation logic
            # For now, just accept any token
            
            # Add user info to request state
            request.state.user = {"token": token}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return await call_next(request)
