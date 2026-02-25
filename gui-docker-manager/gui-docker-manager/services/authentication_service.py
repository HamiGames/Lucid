"""
Authentication Service - JWT Token Validation and User Authentication
File: gui-docker-manager/gui-docker-manager/services/authentication_service.py

Provides JWT token validation, user extraction, and role-based access control.
Integrates with FastAPI dependency injection for easy reuse across routes.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """User roles for access control"""
    USER = "user"
    DEVELOPER = "developer"
    ADMIN = "admin"


class TokenPayload(BaseModel):
    """JWT token payload structure"""
    sub: str  # Subject (user ID)
    role: UserRole  # User role
    exp: Optional[datetime] = None  # Expiration time
    iat: Optional[datetime] = None  # Issued at time
    aud: str = "gui-docker-manager"  # Audience


class AuthenticatedUser(BaseModel):
    """Authenticated user information"""
    user_id: str
    role: UserRole
    token_valid: bool
    permissions: Dict[str, bool]


class AuthenticationService:
    """Service for JWT token validation and user authentication"""

    def __init__(self, secret_key: str):
        """
        Initialize authentication service

        Args:
            secret_key: JWT secret key for token validation
        """
        self.secret_key = secret_key
        self.algorithm = "HS256"

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        """
        Decode and validate JWT token

        Args:
            token: JWT token string (with or without "Bearer " prefix)

        Returns:
            TokenPayload if valid, None if invalid or expired
        """
        try:
            # Remove "Bearer " prefix if present
            if token.startswith("Bearer "):
                token = token[7:]

            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="gui-docker-manager"
            )

            # Extract and validate required fields
            user_id = payload.get("sub")
            role_str = payload.get("role", "user")

            if not user_id:
                logger.warning("Token missing subject claim")
                return None

            # Validate role is one of allowed roles
            try:
                role = UserRole(role_str)
            except ValueError:
                logger.warning(f"Token contains invalid role: {role_str}")
                return None

            return TokenPayload(
                sub=user_id,
                role=role,
                exp=datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None,
                iat=datetime.fromtimestamp(payload.get("iat")) if payload.get("iat") else None,
                aud=payload.get("aud", "gui-docker-manager")
            )

        except JWTError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            return None

    def create_token(
        self,
        user_id: str,
        role: UserRole,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT token

        Args:
            user_id: User identifier
            role: User role
            expires_delta: Token expiration time delta

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=24)

        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": user_id,
            "role": role.value,
            "exp": expire,
            "iat": datetime.utcnow(),
            "aud": "gui-docker-manager"
        }

        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )

        return token

    def validate_token_and_extract_user(self, token: str) -> Optional[AuthenticatedUser]:
        """
        Validate token and extract user information

        Args:
            token: JWT token

        Returns:
            AuthenticatedUser if valid, None otherwise
        """
        payload = self.decode_token(token)

        if payload is None:
            return None

        # Check if token is expired
        if payload.exp and payload.exp < datetime.utcnow():
            logger.warning(f"Token expired for user {payload.sub}")
            return None

        return AuthenticatedUser(
            user_id=payload.sub,
            role=payload.role,
            token_valid=True,
            permissions=self._get_role_permissions(payload.role)
        )

    @staticmethod
    def _get_role_permissions(role: UserRole) -> Dict[str, bool]:
        """
        Get permissions for a given role

        Args:
            role: User role

        Returns:
            Dictionary of permissions
        """
        permissions_map = {
            UserRole.USER: {
                "read:containers": True,
                "read:services": True,
                "read:logs": True,
                "read:stats": True,
                "read:health": True,
                "write:containers": False,
                "write:services": False,
                "admin:operations": False,
            },
            UserRole.DEVELOPER: {
                "read:containers": True,
                "read:services": True,
                "read:logs": True,
                "read:stats": True,
                "read:health": True,
                "write:containers": True,
                "write:services": True,
                "write:foundation_services": False,
                "write:core_services": True,
                "write:application_services": True,
                "admin:operations": False,
            },
            UserRole.ADMIN: {
                "read:containers": True,
                "read:services": True,
                "read:logs": True,
                "read:stats": True,
                "read:health": True,
                "write:containers": True,
                "write:services": True,
                "write:foundation_services": True,
                "write:core_services": True,
                "write:application_services": True,
                "write:support_services": True,
                "admin:operations": True,
                "admin:compose_management": True,
            }
        }

        return permissions_map.get(role, {})

    def has_permission(self, user: AuthenticatedUser, permission: str) -> bool:
        """
        Check if user has specific permission

        Args:
            user: Authenticated user
            permission: Permission string to check

        Returns:
            True if user has permission, False otherwise
        """
        return user.permissions.get(permission, False)

    def can_manage_service_group(self, user: AuthenticatedUser, service_group: str) -> bool:
        """
        Check if user can manage a specific service group

        Args:
            user: Authenticated user
            service_group: Service group name (foundation, core, application, support)

        Returns:
            True if user can manage the group, False otherwise
        """
        service_permissions = {
            "foundation": f"write:foundation_services",
            "core": f"write:core_services",
            "application": f"write:application_services",
            "support": f"write:support_services",
        }

        permission = service_permissions.get(service_group)
        if not permission:
            logger.warning(f"Unknown service group: {service_group}")
            return False

        return self.has_permission(user, permission)

    def get_user_info(self, user: AuthenticatedUser) -> Dict[str, Any]:
        """
        Get comprehensive user information

        Args:
            user: Authenticated user

        Returns:
            Dictionary with user details and permissions
        """
        return {
            "user_id": user.user_id,
            "role": user.role.value,
            "permissions": user.permissions,
            "can_manage_services": any(
                perm.startswith("write:") and perm != "write:containers"
                for perm, allowed in user.permissions.items()
                if allowed
            )
        }
