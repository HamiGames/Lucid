"""
Lucid Authentication Service - Authentication Middleware
JWT token validation middleware
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional
from datetime import datetime
import logging

from ..session_manager import SessionManager
from ..models.session import TokenType
from ..utils.exceptions import TokenExpiredError, InvalidTokenError

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for JWT token validation
    
    Validates JWT tokens on protected endpoints and injects user context
    into request state.
    """
    
    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = [
        "/health",
        "/meta/info",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/register",
        "/auth/login",
        "/auth/refresh"
    ]
    
    def __init__(self, app, session_manager: Optional[SessionManager] = None):
        super().__init__(app)
        self.session_manager = session_manager or SessionManager()
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate authentication"""
        
        # Skip authentication for public endpoints
        if self.is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Extract token from header
        token = self.extract_token(request)
        
        if not token:
            return self.unauthorized_response(
                "Missing authentication token",
                "LUCID_ERR_2001"
            )
        
        # Validate token
        try:
            payload = await self.session_manager.validate_token(token, TokenType.ACCESS)
            
            # Inject user context into request state
            request.state.user_id = payload.user_id
            request.state.role = payload.role
            request.state.token_jti = payload.jti
            request.state.authenticated = True
            
            logger.debug(f"Authenticated user {payload.user_id} with role {payload.role}")
            
            # Process request
            response = await call_next(request)
            return response
            
        except TokenExpiredError as e:
            return self.unauthorized_response(
                str(e),
                "LUCID_ERR_2002",
                401
            )
        except InvalidTokenError as e:
            return self.unauthorized_response(
                str(e),
                "LUCID_ERR_2003",
                401
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return self.error_response(
                "Authentication failed",
                "LUCID_ERR_2000",
                500
            )
    
    def is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (doesn't require authentication)"""
        for endpoint in self.PUBLIC_ENDPOINTS:
            if path.startswith(endpoint):
                return True
        return False
    
    def extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request header
        
        Supports:
        - Authorization: Bearer <token>
        - X-Auth-Token: <token>
        """
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1]
        
        # Try X-Auth-Token header
        token_header = request.headers.get("X-Auth-Token")
        if token_header:
            return token_header
        
        return None
    
    def unauthorized_response(self, message: str, error_code: str, status_code: int = 401) -> JSONResponse:
        """Generate unauthorized response"""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": message,
                    "service": "auth-service",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    def error_response(self, message: str, error_code: str, status_code: int = 500) -> JSONResponse:
        """Generate error response"""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": message,
                    "service": "auth-service",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )

