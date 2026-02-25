"""
Authentication Middleware
File: gui-docker-manager/gui-docker-manager/middleware/auth.py

Validates JWT tokens from Authorization header and validates user permissions.
Adds authenticated user to request state for downstream access.
"""

import logging
from fastapi import Request, HTTPException
from typing import Callable, Optional
from ..services.authentication_service import AuthenticationService, AuthenticatedUser

logger = logging.getLogger(__name__)


class AuthenticationMiddleware:
    """JWT Authentication middleware for FastAPI"""

    def __init__(self, auth_service: AuthenticationService, exclude_paths: Optional[list] = None):
        """
        Initialize authentication middleware

        Args:
            auth_service: Authentication service instance
            exclude_paths: Paths that don't require authentication
        """
        self.auth_service = auth_service
        self.exclude_paths = exclude_paths or [
            "/health",
            "/ready",
            "/live",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/"
        ]

    async def __call__(self, request: Request, call_next: Callable):
        """
        Process request authentication

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from next handler
        """
        # Check if path is excluded
        if request.url.path in self.exclude_paths or request.url.path.startswith("/docs"):
            response = await call_next(request)
            return response

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning(f"Missing Authorization header for {request.method} {request.url.path}")
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Validate token
        try:
            authenticated_user = self.auth_service.validate_token_and_extract_user(auth_header)

            if not authenticated_user:
                logger.warning(f"Invalid token for {request.method} {request.url.path}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            # Add user to request state for downstream access
            request.state.user = authenticated_user
            logger.info(f"Authenticated user {authenticated_user.user_id} ({authenticated_user.role.value})")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication failed")

        # Call next handler
        response = await call_next(request)
        return response


async def get_authenticated_user(request: Request) -> AuthenticatedUser:
    """
    FastAPI dependency to get authenticated user from request state

    Args:
        request: FastAPI request

    Returns:
        AuthenticatedUser from request state

    Raises:
        HTTPException: If user not authenticated
    """
    user = getattr(request.state, "user", None)

    if user is None:
        logger.warning("Request missing authenticated user in state")
        raise HTTPException(status_code=401, detail="User not authenticated")

    return user


async def require_permission(permission: str):
    """
    Factory for creating permission check middleware

    Args:
        permission: Permission string to require

    Returns:
        Async dependency function for FastAPI
    """
    async def permission_checker(request: Request):
        """Check if user has required permission"""
        user = getattr(request.state, "user", None)

        if not user:
            logger.warning(f"Permission check failed: user not authenticated")
            raise HTTPException(status_code=401, detail="User not authenticated")

        if not user.permissions.get(permission):
            logger.warning(f"User {user.user_id} denied permission: {permission}")
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions for {permission}"
            )

        return user

    return permission_checker
