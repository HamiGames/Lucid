"""
Lucid API Gateway - Authentication Service Client
Handles communication with Authentication Cluster (Cluster 09).

File: 03-api-gateway/services/auth_service.py
Lines: ~300
Purpose: Authentication service integration
Dependencies: aiohttp, PyJWT
"""

import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt

from ..models.auth import LoginRequest, TokenResponse, TokenPayload
from ..config import settings

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass


class TokenExpiredError(AuthenticationError):
    """Token has expired."""
    pass


class InvalidTokenError(AuthenticationError):
    """Token is invalid."""
    pass


class AuthService:
    """
    Authentication service client for Cluster 09 integration.
    
    Handles:
    - User login/logout
    - JWT token validation
    - Token refresh
    - Hardware wallet authentication
    """
    
    def __init__(self):
        self.auth_service_url = settings.AUTH_SERVICE_URL
        self.jwt_secret_key = settings.JWT_SECRET_KEY
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self.token_expire_minutes = settings.TOKEN_EXPIRE_MINUTES
        
        # Connection pooling for auth service
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize aiohttp session with connection pooling."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
            
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def login(
        self, 
        tron_address: str, 
        signature: str,
        message: str
    ) -> TokenResponse:
        """
        Authenticate user with TRON signature.
        
        Args:
            tron_address: User's TRON wallet address
            signature: Signed message signature
            message: Original message that was signed
            
        Returns:
            TokenResponse with access_token and refresh_token
            
        Raises:
            AuthenticationError: If authentication fails
        """
        await self.initialize()
        
        try:
            async with self.session.post(
                f"{self.auth_service_url}/auth/login",
                json={
                    "tron_address": tron_address,
                    "signature": signature,
                    "message": message
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return TokenResponse(**data)
                elif response.status == 401:
                    error_data = await response.json()
                    raise AuthenticationError(
                        error_data.get("error", {}).get("message", "Authentication failed")
                    )
                else:
                    raise AuthenticationError(f"Login failed with status {response.status}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Auth service connection error: {e}")
            raise AuthenticationError("Authentication service unavailable")
            
    async def verify_token(self, token: str) -> TokenPayload:
        """
        Verify JWT token validity.
        
        Args:
            token: JWT access token
            
        Returns:
            TokenPayload with decoded token data
            
        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is invalid
        """
        try:
            # First, try local JWT verification (faster)
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm]
            )
            
            # Validate token type
            if payload.get("type") != "access":
                raise InvalidTokenError("Invalid token type")
                
            return TokenPayload(**payload)
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise TokenExpiredError("Token has expired")
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise InvalidTokenError("Invalid token")
            
    async def verify_token_remote(self, token: str) -> TokenPayload:
        """
        Verify token with authentication service (fallback).
        
        Args:
            token: JWT access token
            
        Returns:
            TokenPayload with decoded token data
        """
        await self.initialize()
        
        try:
            async with self.session.post(
                f"{self.auth_service_url}/auth/verify",
                json={"token": token}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return TokenPayload(**data)
                else:
                    raise InvalidTokenError("Token verification failed")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Token verification error: {e}")
            raise AuthenticationError("Token verification service unavailable")
            
    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            TokenResponse with new access_token
            
        Raises:
            AuthenticationError: If refresh fails
        """
        await self.initialize()
        
        try:
            async with self.session.post(
                f"{self.auth_service_url}/auth/refresh",
                json={"refresh_token": refresh_token}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return TokenResponse(**data)
                else:
                    raise AuthenticationError("Token refresh failed")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Token refresh error: {e}")
            raise AuthenticationError("Token refresh service unavailable")
            
    async def logout(self, user_id: str) -> bool:
        """
        Logout user and invalidate tokens.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if logout successful
        """
        await self.initialize()
        
        try:
            async with self.session.post(
                f"{self.auth_service_url}/auth/logout",
                json={"user_id": user_id}
            ) as response:
                return response.status == 200
                
        except aiohttp.ClientError as e:
            logger.error(f"Logout error: {e}")
            return False
            
    async def get_user_permissions(self, user_id: str) -> list:
        """
        Get user permissions from auth service.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of permission strings
        """
        await self.initialize()
        
        try:
            async with self.session.get(
                f"{self.auth_service_url}/auth/permissions/{user_id}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("permissions", [])
                else:
                    logger.warning(f"Failed to get permissions for user {user_id}")
                    return []
                    
        except aiohttp.ClientError as e:
            logger.error(f"Get permissions error: {e}")
            return []


# Global auth service instance
auth_service = AuthService()

