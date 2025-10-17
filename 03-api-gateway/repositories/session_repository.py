"""
Lucid API Gateway - Session Repository
Data access layer for session operations.

File: 03-api-gateway/repositories/session_repository.py
Lines: ~120
Purpose: Session data access
Dependencies: motor
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class SessionRepository:
    """
    Session data access repository.
    
    Provides CRUD operations for session data.
    """
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.collection = self.db.sessions
        
    async def find_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Find session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session document or None
        """
        try:
            return await self.collection.find_one({"session_id": session_id})
        except Exception as e:
            logger.error(f"Error finding session by ID: {e}")
            return None
            
    async def find_by_user(
        self, 
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find sessions by user ID.
        
        Args:
            user_id: User identifier
            skip: Number of sessions to skip
            limit: Maximum number of sessions
            
        Returns:
            List of session documents
        """
        try:
            cursor = self.collection.find(
                {"user_id": user_id}
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error finding sessions by user: {e}")
            return []
            
    async def create(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new session.
        
        Args:
            session_data: Session data dictionary
            
        Returns:
            Created session document
        """
        try:
            session_data["created_at"] = datetime.utcnow()
            session_data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.insert_one(session_data)
            session_data["_id"] = str(result.inserted_id)
            
            return session_data
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
            
    async def update(
        self, 
        session_id: str, 
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update session.
        
        Args:
            session_id: Session identifier
            update_data: Update data dictionary
            
        Returns:
            True if updated successfully
        """
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"session_id": session_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return False
            
    async def update_status(
        self, 
        session_id: str, 
        status: str
    ) -> bool:
        """
        Update session status.
        
        Args:
            session_id: Session identifier
            status: New status
            
        Returns:
            True if updated successfully
        """
        return await self.update(session_id, {"status": status})
        
    async def delete(self, session_id: str) -> bool:
        """
        Delete session (mark as terminated).
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            result = await self.collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": "terminated",
                        "terminated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

