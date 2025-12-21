#!/usr/bin/env python3
"""
Auth Service Integration Client
Handles interaction with lucid-auth-service for authentication and authorization
"""

import logging
import os
from typing import Dict, Any, Optional

from .service_base import ServiceClientBase, ServiceError
from core.logging import get_logger

logger = get_logger(__name__)


class AuthServiceClient(ServiceClientBase):
    """
    Client for interacting with lucid-auth-service
    Handles user authentication, token validation, and permission checks
    """
    
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """
        Initialize Auth Service client
        
        Args:
            base_url: Base URL for auth-service (from AUTH_SERVICE_URL env var if not provided)
            **kwargs: Additional arguments passed to ServiceClientBase
        """
        url = base_url or os.getenv('AUTH_SERVICE_URL', '')
        if not url:
            raise ValueError("AUTH_SERVICE_URL environment variable is required")
        
        super().__init__(base_url=url, **kwargs)
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Token validation result with user information
        """
        try:
            payload = {
                "token": token
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/auth/validate',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to validate token: {str(e)}")
            raise ServiceError(f"Token validation failed: {str(e)}")
    
    async def get_user_permissions(
        self,
        user_id: str,
        resource: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user permissions
        
        Args:
            user_id: User identifier
            resource: Optional resource identifier for specific permissions
            
        Returns:
            User permissions information
        """
        try:
            params = {}
            if resource:
                params['resource'] = resource
            
            response = await self._make_request(
                method='GET',
                endpoint=f'/api/v1/auth/users/{user_id}/permissions',
                params=params
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get permissions for user {user_id}: {str(e)}")
            raise ServiceError(f"Failed to get user permissions: {str(e)}")
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        resource: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if user has specific permission
        
        Args:
            user_id: User identifier
            permission: Permission name to check
            resource: Optional resource identifier
            
        Returns:
            Permission check result
        """
        try:
            payload = {
                "user_id": user_id,
                "permission": permission,
                "resource": resource
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/auth/permissions/check',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to check permission for user {user_id}: {str(e)}")
            raise ServiceError(f"Permission check failed: {str(e)}")
    
    async def authenticate_user(
        self,
        credentials: Dict[str, Any],
        auth_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user with credentials
        
        Args:
            credentials: Authentication credentials (varies by method)
            auth_method: Optional authentication method (jwt, magic_link, hardware_wallet, etc.)
            
        Returns:
            Authentication result with token if successful
        """
        try:
            payload = {
                "credentials": credentials,
                "auth_method": auth_method or "jwt"
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/auth/authenticate',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to authenticate user: {str(e)}")
            raise ServiceError(f"Authentication failed: {str(e)}")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            New access token
        """
        try:
            payload = {
                "refresh_token": refresh_token
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/auth/refresh',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            raise ServiceError(f"Token refresh failed: {str(e)}")
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information
        
        Args:
            user_id: User identifier
            
        Returns:
            User information
        """
        try:
            response = await self._make_request(
                method='GET',
                endpoint=f'/api/v1/auth/users/{user_id}'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {str(e)}")
            raise ServiceError(f"Failed to get user info: {str(e)}")
    
    async def logout_user(self, user_id: str, token: Optional[str] = None) -> Dict[str, Any]:
        """
        Logout user and invalidate tokens
        
        Args:
            user_id: User identifier
            token: Optional token to invalidate
            
        Returns:
            Logout confirmation
        """
        try:
            payload = {
                "user_id": user_id,
                "token": token
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/auth/logout',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to logout user {user_id}: {str(e)}")
            raise ServiceError(f"Logout failed: {str(e)}")

