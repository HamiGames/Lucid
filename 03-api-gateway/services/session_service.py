"""
Lucid API Gateway - Session Service
Handles session management operations.

File: 03-api-gateway/services/session_service.py
Lines: ~280
Purpose: Session management service
Dependencies: aiohttp, models
"""

import aiohttp
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from ..models.session import Session, SessionCreate, SessionStatus
from ..config import settings
from ..database.connection import get_database

logger = logging.getLogger(__name__)


class SessionServiceError(Exception):
    """Base exception for session service errors."""
    pass


class SessionNotFoundError(SessionServiceError):
    """Session not found."""
    pass


class SessionService:
    """
    Session management service.
    
    Handles:
    - Session creation and lifecycle
    - Session queries
    - Session status updates
    """
    
    def __init__(self):
        self.db = None
        self.session_management_url = settings.SESSION_SERVICE_URL
        self.http_session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize database and HTTP connections."""
        if not self.db:
            self.db = await get_database()
            
        if not self.http_session:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=100)
            self.http_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
            
    async def close(self):
        """Close HTTP session."""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            
    async def create_session(
        self, 
        user_id: str, 
        session_create: SessionCreate
    ) -> Session:
        """
        Create new session.
        
        Args:
            user_id: User identifier
            session_create: Session creation data
            
        Returns:
            Created Session object
        """
        await self.initialize()
        
        try:
            # Create session document
            session_data = session_create.dict()
            session_data["user_id"] = user_id
            session_data["status"] = SessionStatus.INITIALIZING.value
            session_data["created_at"] = datetime.utcnow()
            session_data["updated_at"] = datetime.utcnow()
            
            # Insert into database
            result = await self.db.sessions.insert_one(session_data)
            session_data["_id"] = str(result.inserted_id)
            
            # Notify Session Management cluster
            await self._notify_session_management(
                "create",
                session_data
            )
            
            logger.info(f"Created session {session_data['session_id']} for user {user_id}")
            return Session(**session_data)
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise SessionServiceError(f"Failed to create session: {e}")
            
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object or None if not found
        """
        await self.initialize()
        
        try:
            session_data = await self.db.sessions.find_one(
                {"session_id": session_id}
            )
            if session_data:
                return Session(**session_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise SessionServiceError(f"Failed to get session: {e}")
            
    async def update_session_status(
        self, 
        session_id: str, 
        status: SessionStatus
    ) -> Optional[Session]:
        """
        Update session status.
        
        Args:
            session_id: Session identifier
            status: New session status
            
        Returns:
            Updated Session object or None if not found
        """
        await self.initialize()
        
        try:
            result = await self.db.sessions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": status.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated session {session_id} status to {status.value}")
                return await self.get_session(session_id)
            else:
                logger.warning(f"Session {session_id} not found for status update")
                return None
                
        except Exception as e:
            logger.error(f"Error updating session status: {e}")
            raise SessionServiceError(f"Failed to update session status: {e}")
            
    async def list_user_sessions(
        self, 
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Session]:
        """
        List sessions for a user.
        
        Args:
            user_id: User identifier
            skip: Number of sessions to skip
            limit: Maximum number of sessions to return
            
        Returns:
            List of Session objects
        """
        await self.initialize()
        
        try:
            cursor = self.db.sessions.find(
                {"user_id": user_id}
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            sessions = []
            async for session_data in cursor:
                sessions.append(Session(**session_data))
                
            return sessions
            
        except Exception as e:
            logger.error(f"Error listing sessions for user {user_id}: {e}")
            raise SessionServiceError(f"Failed to list sessions: {e}")
            
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted successfully
        """
        await self.initialize()
        
        try:
            # Update status to terminated
            result = await self.db.sessions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": SessionStatus.TERMINATED.value,
                        "terminated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Notify Session Management cluster
                await self._notify_session_management(
                    "terminate",
                    {"session_id": session_id}
                )
                
                logger.info(f"Terminated session {session_id}")
                return True
            else:
                logger.warning(f"Session {session_id} not found for termination")
                return False
                
        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {e}")
            raise SessionServiceError(f"Failed to terminate session: {e}")
            
    async def _notify_session_management(
        self, 
        action: str, 
        data: Dict[str, Any]
    ) -> bool:
        """
        Notify Session Management cluster of session events.
        
        Args:
            action: Action type (create, terminate, etc.)
            data: Session data
            
        Returns:
            True if notification successful
        """
        await self.initialize()
        
        try:
            async with self.http_session.post(
                f"{self.session_management_url}/sessions/{action}",
                json=data
            ) as response:
                if response.status == 200:
                    return True
                else:
                    logger.warning(
                        f"Session management notification failed: {response.status}"
                    )
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(f"Session management notification error: {e}")
            return False


# Global session service instance
session_service = SessionService()

