"""
Authentication Middleware

File: 03-api-gateway/api/app/middleware/auth.py
Purpose: Handles JWT token validation and user authentication for protected endpoints
"""

import logging
from typing import Optional
from fastapi import Request

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Authentication middleware for request processing"""
    
    def __init__(self, app):
        self.app = app
        logger.info("AuthMiddleware initialized")
    
    async def __call__(self, scope, receive, send):
        """Process request through authentication middleware"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            await self.app(scope, receive, send)
            return
        
        # TODO: Implement full JWT token validation
        # For now, allow all requests to pass through
        await self.app(scope, receive, send)
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no authentication required)"""
        public_paths = [
            "/api/v1/meta/info",
            "/api/v1/meta/health",
            "/api/v1/meta/version",
            "/api/v1/auth/login",
            "/api/v1/auth/verify",
            "/api/v1/users",  # User registration
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)
