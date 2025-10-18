"""
Block Repository
Handles database operations for blockchain blocks.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from ..connection import DatabaseConnection
from ...models.block import Block, BlockSummary

logger = logging.getLogger(__name__)


class BlockRepository:
    """Repository for block data access."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        self.collection_name = "blocks"
        
    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the blocks collection."""
        return self.db_connection.get_collection(self.collection_name)
        
    async def create_block(self, block: Block) -> str:
        """Create a new block in the database."""
        try:
            # Convert block to dictionary
            block_dict = block.dict()
            block_dict["_id"] = block.hash  # Use hash as MongoDB _id
            
            # Insert block
            await self.collection.insert_one(block_dict)
            
            logger.info(f"Created block {block.hash} at height {block.height}")
            return block.hash
            
        except DuplicateKeyError:
            logger.warning(f"Block {block.hash} already exists")
            raise ValueError(f"Block with hash {block.hash} already exists")
        except Exception as e:
            logger.error(f"Error creating block {block.hash}: {e}")
            raise
            
    async def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Get a block by its hash."""
        try:
            block_dict = await self.collection.find_one({"_id": block_hash})
            
            if not block_dict:
                return None
                
            # Remove MongoDB _id field and convert to Block
            block_dict.pop("_id", None)
            return Block(**block_dict)
            
        except Exception as e:
            logger.error(f"Error getting block by hash {block_hash}: {e}")
            return None
            
    async def get_block_by_height(self, height: int) -> Optional[Block]:
        """Get a block by its height."""
        try:
            block_dict = await self.collection.find_one({"height": height})
            
            if not block_dict:
                return None
                
            # Remove MongoDB _id field and convert to Block
            block_dict.pop("_id", None)
            return Block(**block_dict)
            
        except Exception as e:
            logger.error(f"Error getting block by height {height}: {e}")
            return None
            
    async def get_latest_block(self) -> Optional[Block]:
        """Get the latest block (highest height)."""
        try:
            block_dict = await self.collection.find_one(
                {},
                sort=[("height", DESCENDING)]
            )
            
            if not block_dict:
                return None
                
            # Remove MongoDB _id field and convert to Block
            block_dict.pop("_id", None)
            return Block(**block_dict)
            
        except Exception as e:
            logger.error(f"Error getting latest block: {e}")
            return None
            
    async def get_blocks_paginated(
        self,
        offset: int = 0,
        limit: int = 20,
        order_by: str = "height",
        order_direction: str = "desc"
    ) -> List[Block]:
        """Get blocks with pagination."""
        try:
            # Determine sort order
            sort_order = DESCENDING if order_direction.lower() == "desc" else ASCENDING
            
            # Query blocks
            cursor = self.collection.find({}).sort(order_by, sort_order).skip(offset).limit(limit)
            blocks = []
            
            async for block_dict in cursor:
                # Remove MongoDB _id field and convert to Block
                block_dict.pop("_id", None)
                blocks.append(Block(**block_dict))
                
            return blocks
            
        except Exception as e:
            logger.error(f"Error getting paginated blocks: {e}")
            return []
            
    async def get_blocks_by_height_range(
        self,
        start_height: int,
        end_height: int
    ) -> List[Block]:
        """Get blocks within a height range."""
        try:
            cursor = self.collection.find({
                "height": {
                    "$gte": start_height,
                    "$lte": end_height
                }
            }).sort("height", ASCENDING)
            
            blocks = []
            async for block_dict in cursor:
                # Remove MongoDB _id field and convert to Block
                block_dict.pop("_id", None)
                blocks.append(Block(**block_dict))
                
            return blocks
            
        except Exception as e:
            logger.error(f"Error getting blocks by height range {start_height}-{end_height}: {e}")
            return []
            
    async def search_blocks_by_hash_prefix(
        self,
        hash_prefix: str,
        limit: int = 10
    ) -> List[Block]:
        """Search blocks by hash prefix."""
        try:
            # Use regex for prefix search
            cursor = self.collection.find({
                "_id": {"$regex": f"^{hash_prefix}", "$options": "i"}
            }).limit(limit)
            
            blocks = []
            async for block_dict in cursor:
                # Remove MongoDB _id field and convert to Block
                block_dict.pop("_id", None)
                blocks.append(Block(**block_dict))
                
            return blocks
            
        except Exception as e:
            logger.error(f"Error searching blocks by hash prefix {hash_prefix}: {e}")
            return []
            
    async def get_total_blocks(self) -> int:
        """Get total number of blocks."""
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error getting total blocks count: {e}")
            return 0
            
    async def get_total_transactions(self) -> int:
        """Get total number of transactions across all blocks."""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_transactions": {
                            "$sum": {"$size": "$transactions"}
                        }
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            
            if result:
                return result[0]["total_transactions"]
            return 0
            
        except Exception as e:
            logger.error(f"Error getting total transactions count: {e}")
            return 0
            
    async def get_average_block_stats(self) -> Dict[str, float]:
        """Get average block statistics."""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "avg_size": {"$avg": "$size_bytes"},
                        "avg_tx_count": {"$avg": {"$size": "$transactions"}},
                        "avg_difficulty": {"$avg": "$difficulty"}
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            
            if result:
                return {
                    "avg_size": result[0].get("avg_size", 0),
                    "avg_tx_count": result[0].get("avg_tx_count", 0),
                    "avg_difficulty": result[0].get("avg_difficulty", 0)
                }
            return {"avg_size": 0, "avg_tx_count": 0, "avg_difficulty": 0}
            
        except Exception as e:
            logger.error(f"Error getting average block stats: {e}")
            return {"avg_size": 0, "avg_tx_count": 0, "avg_difficulty": 0}
            
    async def update_block_status(self, block_hash: str, status: str) -> bool:
        """Update block status."""
        try:
            result = await self.collection.update_one(
                {"_id": block_hash},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated block {block_hash} status to {status}")
                return True
            else:
                logger.warning(f"Block {block_hash} not found for status update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating block {block_hash} status: {e}")
            return False
            
    async def delete_block(self, block_hash: str) -> bool:
        """Delete a block (use with caution)."""
        try:
            result = await self.collection.delete_one({"_id": block_hash})
            
            if result.deleted_count > 0:
                logger.warning(f"Deleted block {block_hash}")
                return True
            else:
                logger.warning(f"Block {block_hash} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting block {block_hash}: {e}")
            return False
            
    async def get_blocks_by_timestamp_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Block]:
        """Get blocks within a timestamp range."""
        try:
            cursor = self.collection.find({
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("timestamp", ASCENDING)
            
            blocks = []
            async for block_dict in cursor:
                # Remove MongoDB _id field and convert to Block
                block_dict.pop("_id", None)
                blocks.append(Block(**block_dict))
                
            return blocks
            
        except Exception as e:
            logger.error(f"Error getting blocks by timestamp range: {e}")
            return []
            
    async def get_orphaned_blocks(self) -> List[Block]:
        """Get blocks that are not part of the main chain (orphaned)."""
        try:
            # This is a simplified implementation
            # In practice, you'd need more complex logic to identify orphaned blocks
            cursor = self.collection.find({
                "$or": [
                    {"is_orphaned": True},
                    {"status": "orphaned"}
                ]
            })
            
            blocks = []
            async for block_dict in cursor:
                # Remove MongoDB _id field and convert to Block
                block_dict.pop("_id", None)
                blocks.append(Block(**block_dict))
                
            return blocks
            
        except Exception as e:
            logger.error(f"Error getting orphaned blocks: {e}")
            return []
            
    async def health_check(self) -> bool:
        """Perform health check on block repository."""
        try:
            # Test basic operations
            await self.collection.find_one({})
            await self.get_total_blocks()
            return True
        except Exception as e:
            logger.error(f"Block repository health check failed: {e}")
            return False
            
    async def create_indexes(self):
        """Create additional indexes for performance."""
        try:
            # Compound indexes for common queries
            await self.collection.create_index([
                ("height", DESCENDING),
                ("timestamp", DESCENDING)
            ])
            
            await self.collection.create_index([
                ("timestamp", DESCENDING),
                ("height", DESCENDING)
            ])
            
            # Index for transaction count queries
            await self.collection.create_index("transactions")
            
            logger.info("Created additional block indexes")
            
        except Exception as e:
            logger.error(f"Error creating block indexes: {e}")
            raise
