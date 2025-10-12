# Session Service Layer
# Business logic integration between API routes and session pipeline

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.schemas.sessions import (
    SessionCreate, SessionResponse, SessionDetail, SessionList, 
    SessionState, SessionStateUpdate
)
from app.db.models.session import RDPSession
from app.config import Settings, get_settings

# Import session pipeline components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../sessions'))

from pipeline.pipeline_manager import SessionPipelineManager, SessionState as PipelineSessionState
from core.session_generator import SessionIdGenerator

logger = logging.getLogger(__name__)


class SessionService:
    """
    Business logic layer for session management.
    
    Integrates with:
    - SessionPipelineManager for lifecycle management
    - SessionIdGenerator for unique ID creation
    - MongoDB for persistence
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.pipeline_manager: Optional[SessionPipelineManager] = None
        
    async def _get_mongo_client(self) -> AsyncIOMotorClient:
        """Get MongoDB client connection"""
        if not self.mongo_client:
            self.mongo_client = AsyncIOMotorClient(self.settings.MONGO_URL)
            self.db = self.mongo_client.get_default_database()
        return self.mongo_client
    
    async def _get_pipeline_manager(self) -> SessionPipelineManager:
        """Get session pipeline manager instance"""
        if not self.pipeline_manager:
            self.pipeline_manager = SessionPipelineManager()
        return self.pipeline_manager
    
    def _map_pipeline_state(self, pipeline_state: str) -> SessionState:
        """Map pipeline session state to API session state"""
        mapping = {
            PipelineSessionState.INITIALIZING.value: SessionState.INITIALIZING,
            PipelineSessionState.RECORDING.value: SessionState.RECORDING,
            PipelineSessionState.FINALIZING.value: SessionState.FINALIZING,
            PipelineSessionState.ANCHORING.value: SessionState.ANCHORING,
            PipelineSessionState.COMPLETED.value: SessionState.COMPLETED,
            PipelineSessionState.FAILED.value: SessionState.FAILED,
        }
        return mapping.get(pipeline_state, SessionState.FAILED)
    
    async def create_session(
        self, 
        user_id: str, 
        owner_address: str, 
        node_id: str, 
        policy_hash: Optional[str] = None
    ) -> SessionResponse:
        """
        Create a new session with unique ID generation and pipeline initialization.
        
        Args:
            user_id: User identifier
            owner_address: TRON wallet address
            node_id: Node identifier for hosting
            policy_hash: Optional trust policy hash
            
        Returns:
            SessionResponse with session details
        """
        try:
            # Generate unique session ID
            session_id = SessionIdGenerator.generate()
            
            # Get MongoDB connection
            await self._get_mongo_client()
            pipeline_manager = await self._get_pipeline_manager()
            
            # Initialize session in pipeline
            session_metadata = await pipeline_manager.initialize_session(
                session_id=session_id,
                owner_address=owner_address,
                node_id=node_id
            )
            
            # Create session document
            session_doc = RDPSession(
                id=session_id,
                user_id=user_id,
                owner_address=owner_address,
                node_id=node_id,
                host="localhost",  # Default host, will be updated by RDP service
                port=3389,  # Default RDP port
                state=SessionState.INITIALIZING,
                policy_hash=policy_hash,
                started_at=datetime.utcnow()
            )
            
            # Insert into MongoDB
            result = await self.db.sessions.insert_one(session_doc.dict(by_alias=True))
            
            logger.info(f"Session created: {session_id} for user {user_id}")
            
            return SessionResponse(
                session_id=session_id,
                user_id=user_id,
                owner_address=owner_address,
                node_id=node_id,
                state=SessionState.INITIALIZING,
                created_at=session_doc.started_at,
                policy_hash=policy_hash
            )
            
        except DuplicateKeyError:
            logger.error(f"Session ID collision: {session_id}")
            raise ValueError("Session ID collision detected")
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def list_sessions(
        self, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 20,
        state: Optional[SessionState] = None
    ) -> SessionList:
        """
        List sessions for a user with pagination and optional state filtering.
        
        Args:
            user_id: User identifier
            page: Page number (1-based)
            page_size: Items per page
            state: Optional state filter
            
        Returns:
            SessionList with paginated results
        """
        try:
            await self._get_mongo_client()
            
            # Build query
            query = {"user_id": user_id}
            if state:
                query["state"] = state.value
            
            # Calculate skip
            skip = (page - 1) * page_size
            
            # Get total count
            total = await self.db.sessions.count_documents(query)
            
            # Get paginated results
            cursor = self.db.sessions.find(query).sort("started_at", -1).skip(skip).limit(page_size)
            sessions = []
            
            async for doc in cursor:
                session = SessionResponse(
                    session_id=doc["_id"],
                    user_id=doc["user_id"],
                    owner_address=doc["owner_address"],
                    node_id=doc["node_id"],
                    state=SessionState(doc["state"]),
                    created_at=doc["started_at"],
                    started_at=doc.get("recording_started_at"),
                    ended_at=doc.get("ended_at"),
                    policy_hash=doc.get("policy_hash")
                )
                sessions.append(session)
            
            return SessionList(
                items=sessions,
                total=total,
                page=page,
                page_size=page_size,
                has_next=skip + page_size < total
            )
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise
    
    async def get_session_detail(self, session_id: str) -> Optional[SessionDetail]:
        """
        Get detailed session information including blockchain metadata.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionDetail or None if not found
        """
        try:
            await self._get_mongo_client()
            
            doc = await self.db.sessions.find_one({"_id": session_id})
            if not doc:
                return None
            
            return SessionDetail(
                session_id=doc["_id"],
                user_id=doc["user_id"],
                owner_address=doc["owner_address"],
                node_id=doc["node_id"],
                state=SessionState(doc["state"]),
                created_at=doc["started_at"],
                started_at=doc.get("recording_started_at"),
                ended_at=doc.get("ended_at"),
                policy_hash=doc.get("policy_hash"),
                manifest_hash=doc.get("manifest_hash"),
                merkle_root=doc.get("merkle_root"),
                anchor_txid=doc.get("anchor_txid"),
                total_chunks=doc.get("total_chunks"),
                total_size=doc.get("total_size")
            )
            
        except Exception as e:
            logger.error(f"Failed to get session detail: {e}")
            raise
    
    async def start_session_recording(self, session_id: str) -> SessionResponse:
        """
        Start session recording.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionResponse with updated state
        """
        try:
            await self._get_mongo_client()
            
            # Check current session state
            doc = await self.db.sessions.find_one({"_id": session_id})
            if not doc:
                raise ValueError(f"Session {session_id} not found")
            
            current_state = SessionState(doc["state"])
            if current_state != SessionState.INITIALIZING:
                raise ValueError(f"Cannot start session in state: {current_state}")
            
            # Update session state
            now = datetime.utcnow()
            await self.db.sessions.update_one(
                {"_id": session_id},
                {
                    "$set": {
                        "state": SessionState.RECORDING.value,
                        "recording_started_at": now
                    }
                }
            )
            
            # Get updated session
            updated_doc = await self.db.sessions.find_one({"_id": session_id})
            
            return SessionResponse(
                session_id=updated_doc["_id"],
                user_id=updated_doc["user_id"],
                owner_address=updated_doc["owner_address"],
                node_id=updated_doc["node_id"],
                state=SessionState(updated_doc["state"]),
                created_at=updated_doc["started_at"],
                started_at=updated_doc.get("recording_started_at"),
                ended_at=updated_doc.get("ended_at"),
                policy_hash=updated_doc.get("policy_hash")
            )
            
        except Exception as e:
            logger.error(f"Failed to start session recording: {e}")
            raise
    
    async def finalize_session(self, session_id: str) -> SessionDetail:
        """
        Finalize session and trigger blockchain anchoring.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionDetail with anchor metadata
        """
        try:
            await self._get_mongo_client()
            pipeline_manager = await self._get_pipeline_manager()
            
            # Check current session state
            doc = await self.db.sessions.find_one({"_id": session_id})
            if not doc:
                raise ValueError(f"Session {session_id} not found")
            
            current_state = SessionState(doc["state"])
            if current_state != SessionState.RECORDING:
                raise ValueError(f"Cannot finalize session in state: {current_state}")
            
            # Trigger pipeline finalization (this will handle anchoring)
            success = await pipeline_manager.finalize_session(session_id)
            
            if not success:
                raise ValueError("Session finalization failed")
            
            # Get updated session with anchor metadata
            updated_doc = await self.db.sessions.find_one({"_id": session_id})
            
            return SessionDetail(
                session_id=updated_doc["_id"],
                user_id=updated_doc["user_id"],
                owner_address=updated_doc["owner_address"],
                node_id=updated_doc["node_id"],
                state=SessionState(updated_doc["state"]),
                created_at=updated_doc["started_at"],
                started_at=updated_doc.get("recording_started_at"),
                ended_at=updated_doc.get("ended_at"),
                policy_hash=updated_doc.get("policy_hash"),
                manifest_hash=updated_doc.get("manifest_hash"),
                merkle_root=updated_doc.get("merkle_root"),
                anchor_txid=updated_doc.get("anchor_txid"),
                total_chunks=updated_doc.get("total_chunks"),
                total_size=updated_doc.get("total_size")
            )
            
        except Exception as e:
            logger.error(f"Failed to finalize session: {e}")
            raise
    
    async def cancel_session(self, session_id: str) -> bool:
        """
        Cancel session before recording starts.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if cancelled successfully
        """
        try:
            await self._get_mongo_client()
            
            # Check current session state
            doc = await self.db.sessions.find_one({"_id": session_id})
            if not doc:
                return False
            
            current_state = SessionState(doc["state"])
            if current_state != SessionState.INITIALIZING:
                return False  # Cannot cancel in this state
            
            # Update session state to failed
            await self.db.sessions.update_one(
                {"_id": session_id},
                {
                    "$set": {
                        "state": SessionState.FAILED.value,
                        "ended_at": datetime.utcnow()
                    }
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel session: {e}")
            raise
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time session state information.
        
        Args:
            session_id: Session identifier
            
        Returns:
            State information dict or None if not found
        """
        try:
            await self._get_mongo_client()
            
            doc = await self.db.sessions.find_one({"_id": session_id})
            if not doc:
                return None
            
            return {
                "session_id": session_id,
                "state": doc["state"],
                "created_at": doc["started_at"].isoformat(),
                "recording_started_at": doc.get("recording_started_at").isoformat() if doc.get("recording_started_at") else None,
                "ended_at": doc.get("ended_at").isoformat() if doc.get("ended_at") else None,
                "manifest_hash": doc.get("manifest_hash"),
                "merkle_root": doc.get("merkle_root"),
                "anchor_txid": doc.get("anchor_txid"),
                "total_chunks": doc.get("total_chunks"),
                "total_size": doc.get("total_size")
            }
            
        except Exception as e:
            logger.error(f"Failed to get session state: {e}")
            raise
