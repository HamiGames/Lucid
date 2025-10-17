"""
Session Repository

Repository pattern implementation for session data access.
Handles all database operations related to sessions.

Database Collection: sessions
Phase: Phase 1 - Foundation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging

from ..models.session import (
    Session, SessionCreate, SessionUpdate, SessionInDB,
    SessionStatus, ChunkInfo, MerkleTreeInfo, BlockchainAnchor,
    SessionStatistics, SessionManifest
)

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for session data access"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Initialize session repository
        
        Args:
            database: MongoDB database instance
        """
        self.db = database
        self.collection: AsyncIOMotorCollection = database.sessions
    
    async def create(self, session_create: SessionCreate) -> SessionInDB:
        """
        Create a new session
        
        Args:
            session_create: Session creation data
            
        Returns:
            Created session with database ID
        """
        # Prepare session document
        session_dict = session_create.dict(exclude_unset=True)
        session_dict["created_at"] = datetime.utcnow()
        session_dict["updated_at"] = datetime.utcnow()
        session_dict["session_id"] = None  # Will be set by MongoDB _id conversion
        session_dict["total_chunks"] = 0
        session_dict["chunks_uploaded"] = 0
        session_dict["chunks_processed"] = 0
        session_dict["chunks_encrypted"] = 0
        session_dict["chunks"] = []
        session_dict["metadata"] = session_dict.get("initial_metadata", {})
        
        # Insert into database
        result = await self.collection.insert_one(session_dict)
        
        # Retrieve created session
        created_session = await self.collection.find_one({"_id": result.inserted_id})
        
        # Convert to SessionInDB model
        created_session["session_id"] = str(created_session.pop("_id"))
        return SessionInDB(**created_session)
    
    async def get_by_id(self, session_id: str) -> Optional[SessionInDB]:
        """
        Get session by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session if found, None otherwise
        """
        from bson import ObjectId
        
        try:
            session_doc = await self.collection.find_one({"_id": ObjectId(session_id)})
        except Exception:
            return None
        
        if not session_doc:
            return None
        
        session_doc["session_id"] = str(session_doc.pop("_id"))
        return SessionInDB(**session_doc)
    
    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[SessionStatus] = None
    ) -> List[Session]:
        """
        Get sessions for a user
        
        Args:
            user_id: User identifier
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            
        Returns:
            List of sessions
        """
        query = {"user_id": user_id, "deleted_at": {"$exists": False}}
        
        if status:
            query["status"] = status.value
        
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        sessions = []
        
        async for session_doc in cursor:
            session_doc["session_id"] = str(session_doc.pop("_id"))
            session_dict = {k: v for k, v in session_doc.items() if k in Session.__fields__}
            sessions.append(Session(**session_dict))
        
        return sessions
    
    async def update(self, session_id: str, session_update: SessionUpdate) -> Optional[SessionInDB]:
        """
        Update session information
        
        Args:
            session_id: Session identifier
            session_update: Update data
            
        Returns:
            Updated session if found, None otherwise
        """
        from bson import ObjectId
        
        update_dict = session_update.dict(exclude_unset=True, exclude_none=True)
        if not update_dict:
            return await self.get_by_id(session_id)
        
        update_dict["updated_at"] = datetime.utcnow()
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": update_dict}
            )
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            return None
        
        if result.matched_count == 0:
            return None
        
        return await self.get_by_id(session_id)
    
    async def update_status(self, session_id: str, status: SessionStatus) -> bool:
        """
        Update session status
        
        Args:
            session_id: Session identifier
            status: New status
            
        Returns:
            True if updated, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {
                        "status": status.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error updating session status: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def add_chunk(self, session_id: str, chunk_info: ChunkInfo) -> bool:
        """
        Add a chunk to the session
        
        Args:
            session_id: Session identifier
            chunk_info: Chunk information
            
        Returns:
            True if added, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$push": {"chunks": chunk_info.dict()},
                    "$inc": {
                        "total_chunks": 1,
                        "chunks_uploaded": 1 if chunk_info.status == "uploaded" else 0
                    },
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
        except Exception as e:
            logger.error(f"Error adding chunk: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def update_chunk_status(
        self,
        session_id: str,
        chunk_id: str,
        status: str
    ) -> bool:
        """
        Update status of a specific chunk
        
        Args:
            session_id: Session identifier
            chunk_id: Chunk identifier
            status: New chunk status
            
        Returns:
            True if updated, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {
                    "_id": ObjectId(session_id),
                    "chunks.chunk_id": chunk_id
                },
                {
                    "$set": {
                        "chunks.$.status": status,
                        "chunks.$.processed_at": datetime.utcnow() if status == "stored" else None,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error updating chunk status: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def set_merkle_tree(self, session_id: str, merkle_tree: MerkleTreeInfo) -> bool:
        """
        Set Merkle tree information for the session
        
        Args:
            session_id: Session identifier
            merkle_tree: Merkle tree information
            
        Returns:
            True if set, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {
                        "merkle_tree": merkle_tree.dict(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error setting merkle tree: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def set_blockchain_anchor(
        self,
        session_id: str,
        anchor: BlockchainAnchor
    ) -> bool:
        """
        Set blockchain anchoring information
        
        Args:
            session_id: Session identifier
            anchor: Blockchain anchor information
            
        Returns:
            True if set, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {
                        "blockchain_anchor": anchor.dict(),
                        "status": SessionStatus.COMPLETED.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error setting blockchain anchor: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def delete(self, session_id: str) -> bool:
        """
        Delete session (soft delete)
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"deleted_at": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def list_sessions(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[SessionStatus] = None,
        user_id: Optional[str] = None
    ) -> List[Session]:
        """
        List sessions with optional filters
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            user_id: Optional user filter
            
        Returns:
            List of sessions
        """
        query = {"deleted_at": {"$exists": False}}
        
        if status:
            query["status"] = status.value
        if user_id:
            query["user_id"] = user_id
        
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        sessions = []
        
        async for session_doc in cursor:
            session_doc["session_id"] = str(session_doc.pop("_id"))
            session_dict = {k: v for k, v in session_doc.items() if k in Session.__fields__}
            sessions.append(Session(**session_dict))
        
        return sessions
    
    async def count_sessions(
        self,
        status: Optional[SessionStatus] = None,
        user_id: Optional[str] = None
    ) -> int:
        """
        Count sessions with optional filters
        
        Args:
            status: Optional status filter
            user_id: Optional user filter
            
        Returns:
            Number of sessions matching criteria
        """
        query = {"deleted_at": {"$exists": False}}
        
        if status:
            query["status"] = status.value
        if user_id:
            query["user_id"] = user_id
        
        return await self.collection.count_documents(query)
    
    async def get_session_statistics(self, session_id: str) -> Optional[SessionStatistics]:
        """
        Get session statistics
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session statistics if found, None otherwise
        """
        session = await self.get_by_id(session_id)
        if not session:
            return None
        
        # Calculate statistics
        chunk_sizes = [chunk.size_bytes for chunk in session.chunks]
        
        stats = SessionStatistics(
            session_id=session.session_id,
            user_id=session.user_id,
            total_size_bytes=session.recorded_size_bytes or sum(chunk_sizes),
            compressed_size_bytes=session.compressed_size_bytes or 0,
            compression_ratio=session.compression_ratio or 0.0,
            total_chunks=session.total_chunks,
            chunk_size_avg_bytes=sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
            chunk_size_min_bytes=min(chunk_sizes) if chunk_sizes else 0,
            chunk_size_max_bytes=max(chunk_sizes) if chunk_sizes else 0,
            duration_seconds=session.duration_seconds or 0,
            processing_time_seconds=session.processing_time_seconds or 0,
            upload_time_seconds=0,  # Would need additional tracking
            upload_speed_mbps=session.upload_bandwidth_mbps or 0.0,
            processing_speed_mbps=0.0,  # Calculate from processing time
            anchored=session.blockchain_anchor is not None,
            anchor_confirmations=session.blockchain_anchor.confirmation_count if session.blockchain_anchor else 0
        )
        
        return stats
    
    async def get_session_manifest(self, session_id: str) -> Optional[SessionManifest]:
        """
        Get session manifest for blockchain anchoring
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session manifest if ready, None otherwise
        """
        session = await self.get_by_id(session_id)
        if not session or not session.merkle_tree:
            return None
        
        # Build manifest
        chunk_hashes = [chunk.hash for chunk in session.chunks]
        
        manifest = SessionManifest(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            total_chunks=session.total_chunks,
            total_size_bytes=session.recorded_size_bytes or 0,
            merkle_root=session.merkle_tree.root_hash,
            chunk_hashes=chunk_hashes,
            metadata=session.metadata
        )
        
        return manifest
    
    async def search_sessions(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Session]:
        """
        Search sessions by name or session ID
        
        Args:
            query: Search query
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching sessions
        """
        search_query = {
            "$or": [
                {"session_name": {"$regex": query, "$options": "i"}},
                {"session_id": query}
            ],
            "deleted_at": {"$exists": False}
        }
        
        cursor = self.collection.find(search_query).sort("created_at", -1).skip(skip).limit(limit)
        sessions = []
        
        async for session_doc in cursor:
            session_doc["session_id"] = str(session_doc.pop("_id"))
            session_dict = {k: v for k, v in session_doc.items() if k in Session.__fields__}
            sessions.append(Session(**session_dict))
        
        return sessions

