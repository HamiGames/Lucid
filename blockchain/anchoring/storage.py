"""
Anchoring Storage Module
Handles persistence of anchoring records in MongoDB

This module provides storage operations for session anchoring data.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

logger = logging.getLogger(__name__)


class AnchoringStorage:
    """
    Storage layer for anchoring records.
    
    Handles MongoDB operations for session anchoring data persistence.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize anchoring storage.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection: AsyncIOMotorCollection = db["session_anchorings"]
        logger.info("AnchoringStorage initialized")
    
    async def initialize(self):
        """Initialize storage indexes."""
        try:
            # Create indexes for efficient queries
            await self.collection.create_index("session_id", unique=True)
            await self.collection.create_index("status")
            await self.collection.create_index("transaction_id")
            await self.collection.create_index("submitted_at")
            await self.collection.create_index([("session_id", 1), ("status", 1)])
            
            logger.info("AnchoringStorage indexes created")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def store_anchoring_record(
        self,
        anchoring_id: str,
        session_id: str,
        anchor_txid: str,
        status: str,
        block_number: Optional[int] = None,
        merkle_root: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store anchoring record in database.
        
        Args:
            anchoring_id: Unique anchoring identifier
            session_id: Session identifier
            anchor_txid: Blockchain transaction ID
            status: Anchoring status (pending, confirmed, failed)
            block_number: Optional block number when confirmed
            merkle_root: Optional merkle root hash
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful
        """
        try:
            record = {
                "_id": anchoring_id,
                "session_id": session_id,
                "transaction_id": anchor_txid,
                "status": status,
                "block_number": block_number,
                "merkle_root": merkle_root,
                "submitted_at": datetime.now(timezone.utc),
                "confirmed_at": None,
                "metadata": metadata or {}
            }
            
            await self.collection.insert_one(record)
            logger.debug(f"Stored anchoring record: {anchoring_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store anchoring record: {e}")
            return False
    
    async def get_anchoring_record(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get anchoring record by session ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Anchoring record dictionary or None if not found
        """
        try:
            record = await self.collection.find_one({"session_id": session_id})
            if record:
                # Convert ObjectId to string for JSON serialization
                record["_id"] = str(record["_id"])
            return record
            
        except Exception as e:
            logger.error(f"Failed to get anchoring record for {session_id}: {e}")
            return None
    
    async def update_anchoring_status(
        self,
        session_id: str,
        status: str,
        block_number: Optional[int] = None
    ) -> bool:
        """
        Update anchoring status.
        
        Args:
            session_id: Session identifier
            status: New status (pending, confirmed, failed)
            block_number: Optional block number when confirmed
            
        Returns:
            True if successful
        """
        try:
            update_data = {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
            
            if block_number:
                update_data["$set"]["block_number"] = block_number
            
            if status == "confirmed":
                update_data["$set"]["confirmed_at"] = datetime.now(timezone.utc)
            
            result = await self.collection.update_one(
                {"session_id": session_id},
                update_data
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update anchoring status for {session_id}: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get anchoring statistics.
        
        Returns:
            Dictionary containing statistics
        """
        try:
            # Count by status
            pending = await self.collection.count_documents({"status": "pending"})
            processing = await self.collection.count_documents({"status": "processing"})
            confirmed = await self.collection.count_documents({"status": "confirmed"})
            failed = await self.collection.count_documents({"status": "failed"})
            total = await self.collection.count_documents({})
            
            # Count completed today
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            completed_today = await self.collection.count_documents({
                "status": "confirmed",
                "confirmed_at": {"$gte": today_start}
            })
            
            # Calculate average confirmation time from submitted_at to confirmed_at
            avg_confirmation_time = 0.0
            confirmed_records = await self.collection.find({
                "status": "confirmed",
                "submitted_at": {"$exists": True},
                "confirmed_at": {"$exists": True, "$ne": None}
            }).to_list(length=1000)
            
            if confirmed_records:
                total_seconds = 0.0
                valid_count = 0
                for record in confirmed_records:
                    submitted_at = record.get("submitted_at")
                    confirmed_at = record.get("confirmed_at")
                    if submitted_at and confirmed_at:
                        if isinstance(submitted_at, str):
                            try:
                                submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
                            except (ValueError, AttributeError):
                                continue
                        if isinstance(confirmed_at, str):
                            try:
                                confirmed_at = datetime.fromisoformat(confirmed_at.replace('Z', '+00:00'))
                            except (ValueError, AttributeError):
                                continue
                        if isinstance(submitted_at, datetime) and isinstance(confirmed_at, datetime):
                            delta = (confirmed_at - submitted_at).total_seconds()
                            if delta > 0:
                                total_seconds += delta
                                valid_count += 1
                
                if valid_count > 0:
                    avg_confirmation_time = total_seconds / valid_count
            
            return {
                "pending": pending,
                "processing": processing,
                "confirmed": confirmed,
                "failed": failed,
                "total": total,
                "completed_today": completed_today,
                "avg_confirmation_time": avg_confirmation_time
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "pending": 0,
                "processing": 0,
                "confirmed": 0,
                "failed": 0,
                "total": 0,
                "completed_today": 0,
                "avg_confirmation_time": 0.0
            }

