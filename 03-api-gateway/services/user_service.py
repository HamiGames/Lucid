"""
Lucid API Gateway - User Service
Handles user management operations.

File: 03-api-gateway/services/user_service.py
Lines: ~250
Purpose: User management service
Dependencies: aiohttp, models
"""

import aiohttp
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models.user import User, UserCreate, UserUpdate
from ..config import settings
from ..database.connection import get_database

logger = logging.getLogger(__name__)


class UserServiceError(Exception):
    """Base exception for user service errors."""
    pass


class UserNotFoundError(UserServiceError):
    """User not found."""
    pass


class UserService:
    """
    User management service.
    
    Handles:
    - User creation and updates
    - User queries
    - User profile management
    """
    
    def __init__(self):
        self.db = None
        
    async def initialize(self):
        """Initialize database connection."""
        if not self.db:
            self.db = await get_database()
            
    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User object or None if not found
        """
        await self.initialize()
        
        try:
            user_data = await self.db.users.find_one({"user_id": user_id})
            if user_data:
                return User(**user_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise UserServiceError(f"Failed to get user: {e}")
            
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User object or None if not found
        """
        await self.initialize()
        
        try:
            user_data = await self.db.users.find_one({"email": email})
            if user_data:
                return User(**user_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise UserServiceError(f"Failed to get user: {e}")
            
    async def get_user_by_tron_address(self, tron_address: str) -> Optional[User]:
        """
        Get user by TRON wallet address.
        
        Args:
            tron_address: TRON wallet address
            
        Returns:
            User object or None if not found
        """
        await self.initialize()
        
        try:
            user_data = await self.db.users.find_one({"tron_address": tron_address})
            if user_data:
                return User(**user_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by TRON address: {e}")
            raise UserServiceError(f"Failed to get user: {e}")
            
    async def create_user(self, user_create: UserCreate) -> User:
        """
        Create new user.
        
        Args:
            user_create: User creation data
            
        Returns:
            Created User object
        """
        await self.initialize()
        
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_tron_address(
                user_create.tron_address
            )
            if existing_user:
                logger.info(f"User with TRON address {user_create.tron_address} already exists")
                return existing_user
                
            # Create user document
            user_data = user_create.dict()
            user_data["created_at"] = datetime.utcnow()
            user_data["updated_at"] = datetime.utcnow()
            
            result = await self.db.users.insert_one(user_data)
            user_data["_id"] = str(result.inserted_id)
            
            logger.info(f"Created user {user_data['user_id']}")
            return User(**user_data)
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise UserServiceError(f"Failed to create user: {e}")
            
    async def update_user(
        self, 
        user_id: str, 
        user_update: UserUpdate
    ) -> Optional[User]:
        """
        Update user information.
        
        Args:
            user_id: User identifier
            user_update: User update data
            
        Returns:
            Updated User object or None if not found
        """
        await self.initialize()
        
        try:
            # Get existing user
            existing_user = await self.get_user(user_id)
            if not existing_user:
                raise UserNotFoundError(f"User {user_id} not found")
                
            # Prepare update data
            update_data = user_update.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()
            
            # Update user
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            
            # Return updated user
            return await self.get_user(user_id)
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise UserServiceError(f"Failed to update user: {e}")
            
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user (soft delete).
        
        Args:
            user_id: User identifier
            
        Returns:
            True if deleted successfully
        """
        await self.initialize()
        
        try:
            result = await self.db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "deleted": True,
                        "deleted_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Deleted user {user_id}")
                return True
            else:
                logger.warning(f"User {user_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise UserServiceError(f"Failed to delete user: {e}")
            
    async def list_users(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """
        List users with pagination.
        
        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return
            
        Returns:
            List of User objects
        """
        await self.initialize()
        
        try:
            cursor = self.db.users.find(
                {"deleted": {"$ne": True}}
            ).skip(skip).limit(limit)
            
            users = []
            async for user_data in cursor:
                users.append(User(**user_data))
                
            return users
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise UserServiceError(f"Failed to list users: {e}")


# Global user service instance
user_service = UserService()

