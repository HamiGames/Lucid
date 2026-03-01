"""
Lucid API Gateway - User Repository
Data access layer for user operations.

File: 03-api-gateway/repositories/user_repository.py
Lines: ~150
Purpose: User data access
Dependencies: motor
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class UserRepository:
    """
    User data access repository.
    
    Provides CRUD operations for user data.
    """
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.collection = self.db.users
        
    async def find_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Find user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User document or None
        """
        try:
            return await self.collection.find_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error finding user by ID: {e}")
            return None
            
    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find user by email.
        
        Args:
            email: User email address
            
        Returns:
            User document or None
        """
        try:
            return await self.collection.find_one({"email": email})
        except Exception as e:
            logger.error(f"Error finding user by email: {e}")
            return None
            
    async def find_by_tron_address(
        self, 
        tron_address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find user by TRON address.
        
        Args:
            tron_address: TRON wallet address
            
        Returns:
            User document or None
        """
        try:
            return await self.collection.find_one({"tron_address": tron_address})
        except Exception as e:
            logger.error(f"Error finding user by TRON address: {e}")
            return None
            
    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new user.
        
        Args:
            user_data: User data dictionary
            
        Returns:
            Created user document
        """
        try:
            user_data["created_at"] = datetime.utcnow()
            user_data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.insert_one(user_data)
            user_data["_id"] = str(result.inserted_id)
            
            return user_data
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
            
    async def update(
        self, 
        user_id: str, 
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update user.
        
        Args:
            user_id: User identifier
            update_data: Update data dictionary
            
        Returns:
            True if updated successfully
        """
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
            
    async def delete(self, user_id: str) -> bool:
        """
        Delete user (soft delete).
        
        Args:
            user_id: User identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "deleted": True,
                        "deleted_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
            
    async def list_users(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List users with pagination.
        
        Args:
            skip: Number of users to skip
            limit: Maximum number of users
            
        Returns:
            List of user documents
        """
        try:
            cursor = self.collection.find(
                {"deleted": {"$ne": True}}
            ).skip(skip).limit(limit)
            
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []

