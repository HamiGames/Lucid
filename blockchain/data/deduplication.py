"""
Deduplication Manager
Handles data deduplication for data chunks

This module manages data deduplication, identifying and reusing
duplicate chunks to save storage space.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from ..config.config import get_blockchain_config

logger = logging.getLogger(__name__)

# Environment variable configuration (required, no hardcoded defaults)
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL or MONGODB_URL environment variable not set")

# Deduplication configuration from environment
DEDUPLICATION_ENABLED = os.getenv("DATA_CHAIN_DEDUPLICATION_ENABLED", "true").lower() in ("true", "1", "yes")
DEDUPLICATION_METHOD = os.getenv("DATA_CHAIN_DEDUPLICATION_METHOD", os.getenv("DEDUPLICATION_METHOD", "content_hash")).lower()
DEDUPLICATION_HASH_ALGORITHM = os.getenv("DATA_CHAIN_DEDUPLICATION_HASH_ALGORITHM", os.getenv("ANCHORING_HASH_ALGORITHM", "BLAKE3")).upper()
GC_ENABLED = os.getenv("DATA_CHAIN_GC_ENABLED", "true").lower() in ("true", "1", "yes")
GC_INTERVAL_HOURS = int(os.getenv("DATA_CHAIN_GC_INTERVAL_HOURS", os.getenv("GC_INTERVAL_HOURS", "24")))


class DeduplicationManager:
    """
    Manages data deduplication.
    
    Identifies duplicate chunks by content hash and manages
    reference counting for garbage collection.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize deduplication manager.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.deduplication_collection = db.chunk_deduplication
        
        # Get configuration
        config = get_blockchain_config()
        data_chain_config = config.get_data_chain_config()
        dedup_config = data_chain_config.get("deduplication", {})
        
        # Override with environment variables if provided
        self.enabled = DEDUPLICATION_ENABLED and dedup_config.get("enabled", True)
        self.method = DEDUPLICATION_METHOD or dedup_config.get("method", "content_hash")
        self.reference_counting = os.getenv("DATA_CHAIN_REFERENCE_COUNTING", str(dedup_config.get("reference_counting", True))).lower() in ("true", "1", "yes")
        self.store_references = os.getenv("DATA_CHAIN_STORE_REFERENCES", str(dedup_config.get("store_references", True))).lower() in ("true", "1", "yes")
        
        logger.info(f"DeduplicationManager initialized: enabled={self.enabled}, method={self.method}")
    
    async def register_chunk(self, chunk_id: str, hash_value: str, size_bytes: int) -> bool:
        """
        Register a chunk for deduplication tracking.
        
        Args:
            chunk_id: Chunk identifier
            hash_value: Content hash of chunk
            size_bytes: Size of chunk in bytes
            
        Returns:
            True if registered, False otherwise
        """
        if not self.enabled:
            return True
        
        try:
            # Check if hash already exists
            existing = await self.deduplication_collection.find_one({"hash": hash_value})
            
            if existing:
                # Increment reference count
                if self.reference_counting:
                    await self.deduplication_collection.update_one(
                        {"hash": hash_value},
                        {
                            "$inc": {"reference_count": 1},
                            "$addToSet": {"chunk_ids": chunk_id}
                        }
                    )
                else:
                    # Just add chunk_id to list
                    await self.deduplication_collection.update_one(
                        {"hash": hash_value},
                        {"$addToSet": {"chunk_ids": chunk_id}}
                    )
            else:
                # Create new entry
                doc = {
                    "hash": hash_value,
                    "primary_chunk_id": chunk_id,
                    "chunk_ids": [chunk_id],
                    "size_bytes": size_bytes,
                    "reference_count": 1,
                    "created_at": datetime.now(timezone.utc),
                    "last_accessed_at": datetime.now(timezone.utc)
                }
                await self.deduplication_collection.insert_one(doc)
            
            logger.debug(f"Registered chunk {chunk_id} with hash {hash_value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register chunk {chunk_id} for deduplication: {e}")
            return False
    
    async def unregister_chunk(self, chunk_id: str, hash_value: Optional[str] = None) -> bool:
        """
        Unregister a chunk from deduplication tracking.
        
        Args:
            chunk_id: Chunk identifier
            hash_value: Optional content hash (will be looked up if not provided)
            
        Returns:
            True if unregistered, False otherwise
        """
        if not self.enabled:
            return True
        
        try:
            # Look up hash if not provided
            if not hash_value:
                doc = await self.deduplication_collection.find_one({"chunk_ids": chunk_id})
                if doc:
                    hash_value = doc.get("hash")
                else:
                    return False
            
            # Decrement reference count
            if self.reference_counting:
                result = await self.deduplication_collection.update_one(
                    {"hash": hash_value},
                    {
                        "$inc": {"reference_count": -1},
                        "$pull": {"chunk_ids": chunk_id}
                    }
                )
            else:
                result = await self.deduplication_collection.update_one(
                    {"hash": hash_value},
                    {"$pull": {"chunk_ids": chunk_id}}
                )
            
            # If reference count reaches 0, mark for garbage collection
            doc = await self.deduplication_collection.find_one({"hash": hash_value})
            if doc and doc.get("reference_count", 0) <= 0:
                await self.deduplication_collection.update_one(
                    {"hash": hash_value},
                    {"$set": {"gc_eligible": True, "gc_eligible_at": datetime.now(timezone.utc)}}
                )
            
            logger.debug(f"Unregistered chunk {chunk_id} with hash {hash_value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister chunk {chunk_id} for deduplication: {e}")
            return False
    
    async def find_duplicate(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """
        Find duplicate chunk by hash.
        
        Args:
            hash_value: Content hash to search for
            
        Returns:
            Duplicate chunk information or None if not found
        """
        if not self.enabled:
            return None
        
        try:
            doc = await self.deduplication_collection.find_one({"hash": hash_value})
            if doc:
                # Update last accessed time
                await self.deduplication_collection.update_one(
                    {"hash": hash_value},
                    {"$set": {"last_accessed_at": datetime.now(timezone.utc)}}
                )
                
                return {
                    "chunk_id": doc.get("primary_chunk_id"),
                    "hash": hash_value,
                    "reference_count": doc.get("reference_count", 0),
                    "size_bytes": doc.get("size_bytes", 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find duplicate for hash {hash_value}: {e}")
            return None
    
    async def get_deduplication_stats(self) -> Dict[str, Any]:
        """
        Get deduplication statistics.
        
        Returns:
            Dictionary with deduplication statistics
        """
        if not self.enabled:
            return {
                "enabled": False,
                "total_unique_chunks": 0,
                "total_references": 0,
                "deduplication_ratio": 0.0
            }
        
        try:
            # Count unique chunks
            unique_count = await self.deduplication_collection.count_documents({})
            
            # Sum reference counts
            pipeline = [
                {"$group": {
                    "_id": None,
                    "total_references": {"$sum": "$reference_count"},
                    "total_size": {"$sum": "$size_bytes"}
                }}
            ]
            result = await self.deduplication_collection.aggregate(pipeline).to_list(length=1)
            
            total_references = result[0].get("total_references", 0) if result else 0
            total_size = result[0].get("total_size", 0) if result else 0
            
            # Calculate deduplication ratio
            dedup_ratio = (total_references - unique_count) / total_references if total_references > 0 else 0.0
            
            return {
                "enabled": True,
                "total_unique_chunks": unique_count,
                "total_references": total_references,
                "total_size_bytes": total_size,
                "deduplication_ratio": dedup_ratio,
                "space_saved_bytes": total_size * (total_references - unique_count) if total_references > unique_count else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get deduplication stats: {e}")
            return {
                "enabled": True,
                "error": str(e)
            }
    
    async def run_garbage_collection(self) -> Dict[str, Any]:
        """
        Run garbage collection to remove unreferenced chunks.
        
        Returns:
            Dictionary with GC results
        """
        if not self.enabled or not GC_ENABLED:
            return {"enabled": False, "chunks_removed": 0}
        
        try:
            # Find chunks eligible for GC
            eligible_chunks = await self.deduplication_collection.find({
                "gc_eligible": True,
                "reference_count": {"$lte": 0}
            }).to_list(length=None)
            
            removed_count = 0
            for chunk_doc in eligible_chunks:
                chunk_id = chunk_doc.get("primary_chunk_id")
                hash_value = chunk_doc.get("hash")
                
                # Remove from deduplication collection
                await self.deduplication_collection.delete_one({"hash": hash_value})
                removed_count += 1
            
            logger.info(f"Garbage collection removed {removed_count} unreferenced chunks")
            return {
                "enabled": True,
                "chunks_removed": removed_count,
                "chunks_checked": len(eligible_chunks)
            }
            
        except Exception as e:
            logger.error(f"Failed to run garbage collection: {e}")
            return {
                "enabled": True,
                "error": str(e),
                "chunks_removed": 0
            }

