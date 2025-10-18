"""
User Repository

Repository pattern implementation for user data access.
Handles all database operations related to users.

Database Collection: users
Phase: Phase 1 - Foundation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging

from ..models.user import (
    User, UserCreate, UserUpdate, UserInDB,
    UserRole, UserStatus, UserStatistics
)

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user data access"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Initialize user repository
        
        Args:
            database: MongoDB database instance
        """
        self.db = database
        self.collection: AsyncIOMotorCollection = database.users
    
    async def create(self, user_create: UserCreate) -> UserInDB:
        """
        Create a new user
        
        Args:
            user_create: User creation data
            
        Returns:
            Created user with database ID
            
        Raises:
            ValueError: If user with email or TRON address already exists
        """
        # Check if user with email already exists
        existing_user = await self.collection.find_one({"email": user_create.email})
        if existing_user:
            raise ValueError(f"User with email '{user_create.email}' already exists")
        
        # Check if user with TRON address already exists
        existing_tron = await self.collection.find_one({"tron_address": user_create.tron_address})
        if existing_tron:
            raise ValueError(f"User with TRON address '{user_create.tron_address}' already exists")
        
        # Prepare user document
        user_dict = user_create.dict(exclude_unset=True)
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        user_dict["user_id"] = None  # Will be set by MongoDB _id conversion
        
        # Insert into database
        result = await self.collection.insert_one(user_dict)
        
        # Retrieve created user
        created_user = await self.collection.find_one({"_id": result.inserted_id})
        
        # Convert to UserInDB model
        created_user["user_id"] = str(created_user.pop("_id"))
        return UserInDB(**created_user)
    
    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        Get user by ID
        
        Args:
            user_id: User identifier
            
        Returns:
            User if found, None otherwise
        """
        from bson import ObjectId
        
        try:
            user_doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            # Invalid ObjectId format
            return None
        
        if not user_doc:
            return None
        
        # Convert to UserInDB model
        user_doc["user_id"] = str(user_doc.pop("_id"))
        return UserInDB(**user_doc)
    
    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        """
        Get user by email address
        
        Args:
            email: Email address
            
        Returns:
            User if found, None otherwise
        """
        user_doc = await self.collection.find_one({"email": email})
        
        if not user_doc:
            return None
        
        user_doc["user_id"] = str(user_doc.pop("_id"))
        return UserInDB(**user_doc)
    
    async def get_by_tron_address(self, tron_address: str) -> Optional[UserInDB]:
        """
        Get user by TRON address
        
        Args:
            tron_address: TRON wallet address
            
        Returns:
            User if found, None otherwise
        """
        user_doc = await self.collection.find_one({"tron_address": tron_address})
        
        if not user_doc:
            return None
        
        user_doc["user_id"] = str(user_doc.pop("_id"))
        return UserInDB(**user_doc)
    
    async def get_by_username(self, username: str) -> Optional[UserInDB]:
        """
        Get user by username
        
        Args:
            username: Username
            
        Returns:
            User if found, None otherwise
        """
        user_doc = await self.collection.find_one({"username": username})
        
        if not user_doc:
            return None
        
        user_doc["user_id"] = str(user_doc.pop("_id"))
        return UserInDB(**user_doc)
    
    async def update(self, user_id: str, user_update: UserUpdate) -> Optional[UserInDB]:
        """
        Update user information
        
        Args:
            user_id: User identifier
            user_update: Update data
            
        Returns:
            Updated user if found, None otherwise
        """
        from bson import ObjectId
        
        update_dict = user_update.dict(exclude_unset=True, exclude_none=True)
        if not update_dict:
            return await self.get_by_id(user_id)
        
        update_dict["updated_at"] = datetime.utcnow()
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_dict}
            )
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return None
        
        if result.matched_count == 0:
            return None
        
        return await self.get_by_id(user_id)
    
    async def delete(self, user_id: str) -> bool:
        """
        Delete user (soft delete)
        
        Args:
            user_id: User identifier
            
        Returns:
            True if deleted, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "deleted_at": datetime.utcnow(),
                        "status": UserStatus.INACTIVE.value
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None
    ) -> List[User]:
        """
        List users with optional filters
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            role: Optional role filter
            status: Optional status filter
            
        Returns:
            List of users
        """
        query = {"deleted_at": {"$exists": False}}
        
        if role:
            query["role"] = role.value
        if status:
            query["status"] = status.value
        
        cursor = self.collection.find(query).skip(skip).limit(limit)
        users = []
        
        async for user_doc in cursor:
            user_doc["user_id"] = str(user_doc.pop("_id"))
            # Convert to User (not UserInDB to avoid exposing sensitive fields)
            user_dict = {k: v for k, v in user_doc.items() if k in User.__fields__}
            users.append(User(**user_dict))
        
        return users
    
    async def count_users(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None
    ) -> int:
        """
        Count users with optional filters
        
        Args:
            role: Optional role filter
            status: Optional status filter
            
        Returns:
            Number of users matching criteria
        """
        query = {"deleted_at": {"$exists": False}}
        
        if role:
            query["role"] = role.value
        if status:
            query["status"] = status.value
        
        return await self.collection.count_documents(query)
    
    async def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            user_id: User identifier
            
        Returns:
            True if updated, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_login": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error updating last login: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def increment_session_count(self, user_id: str) -> bool:
        """
        Increment user's session count
        
        Args:
            user_id: User identifier
            
        Returns:
            True if updated, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"total_sessions": 1}}
            )
        except Exception as e:
            logger.error(f"Error incrementing session count: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def update_storage_used(self, user_id: str, bytes_delta: int) -> bool:
        """
        Update user's storage usage
        
        Args:
            user_id: User identifier
            bytes_delta: Change in storage (positive or negative)
            
        Returns:
            True if updated, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$inc": {
                        "total_storage_used": bytes_delta,
                        "total_chunks_uploaded": 1 if bytes_delta > 0 else 0
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error updating storage used: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def get_user_statistics(self, user_id: str) -> Optional[UserStatistics]:
        """
        Get user statistics
        
        Args:
            user_id: User identifier
            
        Returns:
            User statistics if found, None otherwise
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Build statistics from user data
        stats = UserStatistics(
            user_id=user.user_id,
            total_sessions=user.total_sessions,
            active_sessions=0,  # Would need to query sessions collection
            completed_sessions=0,  # Would need to query sessions collection
            total_chunks=user.total_chunks_uploaded,
            total_storage_bytes=user.total_storage_used,
            total_bandwidth_bytes=0,  # Would need additional tracking
            nodes_operated=user.node_count,
            total_poot_score=user.total_poot_score,
            total_earnings_usdt=None,  # Would need to query payouts
            last_payout=None  # Would need to query payouts
        )
        
        return stats
    
    async def search_users(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Search users by email, username, or TRON address
        
        Args:
            query: Search query
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching users
        """
        search_query = {
            "$or": [
                {"email": {"$regex": query, "$options": "i"}},
                {"username": {"$regex": query, "$options": "i"}},
                {"tron_address": {"$regex": query, "$options": "i"}}
            ],
            "deleted_at": {"$exists": False}
        }
        
        cursor = self.collection.find(search_query).skip(skip).limit(limit)
        users = []
        
        async for user_doc in cursor:
            user_doc["user_id"] = str(user_doc.pop("_id"))
            user_dict = {k: v for k, v in user_doc.items() if k in User.__fields__}
            users.append(User(**user_dict))
        
        return users

