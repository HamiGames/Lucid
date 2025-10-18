"""
Anchoring Repository
Handles database operations for session anchoring records.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
import uuid

from ..connection import DatabaseConnection
from ...models.anchoring import SessionAnchor, AnchorStatus

logger = logging.getLogger(__name__)


class AnchoringRepository:
    """Repository for session anchoring data access."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        self.collection_name = "session_anchors"
        
    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the session anchors collection."""
        return self.db_connection.get_collection(self.collection_name)
        
    async def create_anchor(self, anchor: SessionAnchor) -> str:
        """Create a new session anchor in the database."""
        try:
            # Generate anchor ID if not provided
            if not anchor.anchor_id:
                anchor.anchor_id = str(uuid.uuid4())
                
            # Convert anchor to dictionary
            anchor_dict = anchor.dict()
            anchor_dict["_id"] = anchor.anchor_id  # Use anchor_id as MongoDB _id
            
            # Insert anchor
            await self.collection.insert_one(anchor_dict)
            
            logger.info(f"Created anchor {anchor.anchor_id} for session {anchor.session_id}")
            return anchor.anchor_id
            
        except DuplicateKeyError:
            logger.warning(f"Anchor {anchor.anchor_id} already exists")
            raise ValueError(f"Anchor with ID {anchor.anchor_id} already exists")
        except Exception as e:
            logger.error(f"Error creating anchor for session {anchor.session_id}: {e}")
            raise
            
    async def get_anchor_by_id(self, anchor_id: str) -> Optional[SessionAnchor]:
        """Get an anchor by its ID."""
        try:
            anchor_dict = await self.collection.find_one({"_id": anchor_id})
            
            if not anchor_dict:
                return None
                
            # Remove MongoDB _id field and convert to SessionAnchor
            anchor_dict.pop("_id", None)
            return SessionAnchor(**anchor_dict)
            
        except Exception as e:
            logger.error(f"Error getting anchor by ID {anchor_id}: {e}")
            return None
            
    async def get_anchor_by_session_id(self, session_id: str) -> Optional[SessionAnchor]:
        """Get an anchor by session ID."""
        try:
            anchor_dict = await self.collection.find_one({"session_id": session_id})
            
            if not anchor_dict:
                return None
                
            # Remove MongoDB _id field and convert to SessionAnchor
            anchor_dict.pop("_id", None)
            return SessionAnchor(**anchor_dict)
            
        except Exception as e:
            logger.error(f"Error getting anchor by session ID {session_id}: {e}")
            return None
            
    async def get_anchors_by_status(
        self,
        status: AnchorStatus,
        limit: int = 100
    ) -> List[SessionAnchor]:
        """Get anchors by status."""
        try:
            cursor = self.collection.find({"status": status.value}).limit(limit)
            
            anchors = []
            async for anchor_dict in cursor:
                # Remove MongoDB _id field and convert to SessionAnchor
                anchor_dict.pop("_id", None)
                anchors.append(SessionAnchor(**anchor_dict))
                
            return anchors
            
        except Exception as e:
            logger.error(f"Error getting anchors by status {status}: {e}")
            return []
            
    async def get_anchor_count_by_status(self, status: AnchorStatus) -> int:
        """Get count of anchors by status."""
        try:
            return await self.collection.count_documents({"status": status.value})
        except Exception as e:
            logger.error(f"Error getting anchor count for status {status}: {e}")
            return 0
            
    async def update_anchor(self, anchor: SessionAnchor) -> bool:
        """Update an existing anchor."""
        try:
            if not anchor.anchor_id:
                raise ValueError("Anchor ID is required for update")
                
            # Convert anchor to dictionary and remove _id
            anchor_dict = anchor.dict()
            anchor_dict.pop("anchor_id", None)  # Don't update the ID field
            anchor_dict["updated_at"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"_id": anchor.anchor_id},
                {"$set": anchor_dict}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated anchor {anchor.anchor_id}")
                return True
            else:
                logger.warning(f"Anchor {anchor.anchor_id} not found for update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating anchor {anchor.anchor_id}: {e}")
            return False
            
    async def update_anchor_status(
        self,
        anchor_id: str,
        status: AnchorStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """Update anchor status."""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }
            
            if status == AnchorStatus.CONFIRMED:
                update_data["confirmed_at"] = datetime.utcnow()
            elif status == AnchorStatus.FAILED and error_message:
                update_data["error_message"] = error_message
                
            result = await self.collection.update_one(
                {"_id": anchor_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated anchor {anchor_id} status to {status.value}")
                return True
            else:
                logger.warning(f"Anchor {anchor_id} not found for status update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating anchor {anchor_id} status: {e}")
            return False
            
    async def get_anchors_by_block(self, block_hash: str) -> List[SessionAnchor]:
        """Get all anchors in a specific block."""
        try:
            cursor = self.collection.find({"block_hash": block_hash})
            
            anchors = []
            async for anchor_dict in cursor:
                # Remove MongoDB _id field and convert to SessionAnchor
                anchor_dict.pop("_id", None)
                anchors.append(SessionAnchor(**anchor_dict))
                
            return anchors
            
        except Exception as e:
            logger.error(f"Error getting anchors for block {block_hash}: {e}")
            return []
            
    async def get_anchors_by_merkle_root(self, merkle_root: str) -> List[SessionAnchor]:
        """Get anchors by Merkle root."""
        try:
            cursor = self.collection.find({"merkle_root": merkle_root})
            
            anchors = []
            async for anchor_dict in cursor:
                # Remove MongoDB _id field and convert to SessionAnchor
                anchor_dict.pop("_id", None)
                anchors.append(SessionAnchor(**anchor_dict))
                
            return anchors
            
        except Exception as e:
            logger.error(f"Error getting anchors by Merkle root {merkle_root}: {e}")
            return []
            
    async def get_anchors_paginated(
        self,
        offset: int = 0,
        limit: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> List[SessionAnchor]:
        """Get anchors with pagination."""
        try:
            # Determine sort order
            sort_order = DESCENDING if order_direction.lower() == "desc" else ASCENDING
            
            # Query anchors
            cursor = self.collection.find({}).sort(order_by, sort_order).skip(offset).limit(limit)
            
            anchors = []
            async for anchor_dict in cursor:
                # Remove MongoDB _id field and convert to SessionAnchor
                anchor_dict.pop("_id", None)
                anchors.append(SessionAnchor(**anchor_dict))
                
            return anchors
            
        except Exception as e:
            logger.error(f"Error getting paginated anchors: {e}")
            return []
            
    async def get_total_anchors(self) -> int:
        """Get total number of anchors."""
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error getting total anchors count: {e}")
            return 0
            
    async def get_anchors_by_timestamp_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[SessionAnchor]:
        """Get anchors within a timestamp range."""
        try:
            cursor = self.collection.find({
                "created_at": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("created_at", ASCENDING)
            
            anchors = []
            async for anchor_dict in cursor:
                # Remove MongoDB _id field and convert to SessionAnchor
                anchor_dict.pop("_id", None)
                anchors.append(SessionAnchor(**anchor_dict))
                
            return anchors
            
        except Exception as e:
            logger.error(f"Error getting anchors by timestamp range: {e}")
            return []
            
    async def get_pending_anchors(self, older_than_minutes: int = 30) -> List[SessionAnchor]:
        """Get anchors that have been pending for too long."""
        try:
            cutoff_time = datetime.utcnow() - datetime.timedelta(minutes=older_than_minutes)
            
            cursor = self.collection.find({
                "status": AnchorStatus.PENDING.value,
                "created_at": {"$lt": cutoff_time}
            })
            
            anchors = []
            async for anchor_dict in cursor:
                # Remove MongoDB _id field and convert to SessionAnchor
                anchor_dict.pop("_id", None)
                anchors.append(SessionAnchor(**anchor_dict))
                
            return anchors
            
        except Exception as e:
            logger.error(f"Error getting pending anchors: {e}")
            return []
            
    async def get_failed_anchors(self, limit: int = 100) -> List[SessionAnchor]:
        """Get failed anchors."""
        try:
            cursor = self.collection.find({
                "status": AnchorStatus.FAILED.value
            }).sort("created_at", DESCENDING).limit(limit)
            
            anchors = []
            async for anchor_dict in cursor:
                # Remove MongoDB _id field and convert to SessionAnchor
                anchor_dict.pop("_id", None)
                anchors.append(SessionAnchor(**anchor_dict))
                
            return anchors
            
        except Exception as e:
            logger.error(f"Error getting failed anchors: {e}")
            return []
            
    async def increment_retry_count(self, anchor_id: str) -> bool:
        """Increment retry count for an anchor."""
        try:
            result = await self.collection.update_one(
                {"_id": anchor_id},
                {
                    "$inc": {"retry_count": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Incremented retry count for anchor {anchor_id}")
                return True
            else:
                logger.warning(f"Anchor {anchor_id} not found for retry count increment")
                return False
                
        except Exception as e:
            logger.error(f"Error incrementing retry count for anchor {anchor_id}: {e}")
            return False
            
    async def delete_anchor(self, anchor_id: str) -> bool:
        """Delete an anchor (use with caution)."""
        try:
            result = await self.collection.delete_one({"_id": anchor_id})
            
            if result.deleted_count > 0:
                logger.warning(f"Deleted anchor {anchor_id}")
                return True
            else:
                logger.warning(f"Anchor {anchor_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting anchor {anchor_id}: {e}")
            return False
            
    async def get_anchoring_stats(self) -> Dict[str, Any]:
        """Get anchoring statistics."""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "total_chunks": {"$sum": "$chunk_count"}
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(None)
            
            stats = {
                "total_anchors": 0,
                "confirmed_anchors": 0,
                "pending_anchors": 0,
                "failed_anchors": 0,
                "total_chunks_anchored": 0
            }
            
            for item in result:
                status = item["_id"]
                count = item["count"]
                chunks = item["total_chunks"]
                
                stats["total_anchors"] += count
                
                if status == AnchorStatus.CONFIRMED.value:
                    stats["confirmed_anchors"] = count
                    stats["total_chunks_anchored"] += chunks
                elif status == AnchorStatus.PENDING.value:
                    stats["pending_anchors"] = count
                elif status == AnchorStatus.FAILED.value:
                    stats["failed_anchors"] = count
                    
            return stats
            
        except Exception as e:
            logger.error(f"Error getting anchoring stats: {e}")
            return {
                "total_anchors": 0,
                "confirmed_anchors": 0,
                "pending_anchors": 0,
                "failed_anchors": 0,
                "total_chunks_anchored": 0
            }
            
    async def get_average_confirmation_time(self) -> float:
        """Get average confirmation time for anchors."""
        try:
            pipeline = [
                {
                    "$match": {
                        "status": AnchorStatus.CONFIRMED.value,
                        "confirmed_at": {"$exists": True},
                        "created_at": {"$exists": True}
                    }
                },
                {
                    "$project": {
                        "confirmation_time": {
                            "$subtract": ["$confirmed_at", "$created_at"]
                        }
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_confirmation_time_ms": {"$avg": "$confirmation_time"}
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            
            if result:
                # Convert milliseconds to seconds
                return result[0]["avg_confirmation_time_ms"] / 1000.0
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting average confirmation time: {e}")
            return 0.0
            
    async def health_check(self) -> bool:
        """Perform health check on anchoring repository."""
        try:
            # Test basic operations
            await self.collection.find_one({})
            await self.get_total_anchors()
            return True
        except Exception as e:
            logger.error(f"Anchoring repository health check failed: {e}")
            return False
            
    async def create_indexes(self):
        """Create additional indexes for performance."""
        try:
            # Compound indexes for common queries
            await self.collection.create_index([
                ("status", ASCENDING),
                ("created_at", DESCENDING)
            ])
            
            await self.collection.create_index([
                ("block_hash", ASCENDING),
                ("block_height", ASCENDING)
            ])
            
            await self.collection.create_index([
                ("merkle_root", ASCENDING),
                ("status", ASCENDING)
            ])
            
            # Index for retry operations
            await self.collection.create_index([
                ("status", ASCENDING),
                ("retry_count", ASCENDING),
                ("created_at", ASCENDING)
            ])
            
            logger.info("Created additional anchoring indexes")
            
        except Exception as e:
            logger.error(f"Error creating anchoring indexes: {e}")
            raise
