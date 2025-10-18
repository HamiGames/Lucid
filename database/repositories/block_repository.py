"""
Block Repository

Repository pattern implementation for blockchain block data access.
Handles all database operations related to blocks (lucid_blocks).

Database Collection: blocks
Phase: Phase 1 - Foundation
Blockchain: lucid_blocks (on-chain)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging

from ..models.block import (
    Block, BlockCreate, BlockInDB, BlockSummary,
    BlockStatus, BlockStatistics, SessionAnchor,
    ConsensusInfo
)

logger = logging.getLogger(__name__)


class BlockRepository:
    """Repository for block data access"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Initialize block repository
        
        Args:
            database: MongoDB database instance
        """
        self.db = database
        self.collection: AsyncIOMotorCollection = database.blocks
    
    async def create(self, block_create: BlockCreate) -> BlockInDB:
        """
        Create a new block
        
        Args:
            block_create: Block creation data
            
        Returns:
            Created block with database ID
            
        Raises:
            ValueError: If block at height already exists
        """
        # Check if block at this height already exists
        existing_block = await self.collection.find_one({"height": block_create.height})
        if existing_block:
            raise ValueError(f"Block at height {block_create.height} already exists")
        
        # Prepare block document
        block_dict = block_create.dict(exclude_unset=True)
        block_dict["created_at"] = datetime.utcnow()
        block_dict["confirmed_at"] = datetime.utcnow()
        block_dict["block_id"] = None  # Will be set to block hash
        block_dict["status"] = BlockStatus.CONFIRMED.value
        block_dict["confirmations"] = 0
        block_dict["finalized"] = False
        block_dict["timestamp"] = datetime.utcnow()
        
        # Calculate transaction count
        block_dict["transaction_count"] = len(block_dict.get("transactions", []))
        block_dict["session_anchor_count"] = len(block_dict.get("session_anchors", []))
        
        # Insert into database
        result = await self.collection.insert_one(block_dict)
        
        # Retrieve created block
        created_block = await self.collection.find_one({"_id": result.inserted_id})
        
        # Convert to BlockInDB model
        created_block["block_id"] = str(created_block.pop("_id"))
        return BlockInDB(**created_block)
    
    async def get_by_id(self, block_id: str) -> Optional[BlockInDB]:
        """
        Get block by ID (block hash)
        
        Args:
            block_id: Block identifier (hash)
            
        Returns:
            Block if found, None otherwise
        """
        from bson import ObjectId
        
        # Try as ObjectId first
        try:
            block_doc = await self.collection.find_one({"_id": ObjectId(block_id)})
        except Exception:
            # Try as block hash
            block_doc = await self.collection.find_one({"block_id": block_id})
        
        if not block_doc:
            return None
        
        block_doc["block_id"] = str(block_doc.pop("_id"))
        return BlockInDB(**block_doc)
    
    async def get_by_height(self, height: int) -> Optional[BlockInDB]:
        """
        Get block by height
        
        Args:
            height: Block height
            
        Returns:
            Block if found, None otherwise
        """
        block_doc = await self.collection.find_one({"height": height})
        
        if not block_doc:
            return None
        
        block_doc["block_id"] = str(block_doc.pop("_id"))
        return BlockInDB(**block_doc)
    
    async def get_latest_block(self) -> Optional[BlockInDB]:
        """
        Get the latest block in the chain
        
        Returns:
            Latest block if exists, None otherwise
        """
        block_doc = await self.collection.find_one(
            sort=[("height", -1)]
        )
        
        if not block_doc:
            return None
        
        block_doc["block_id"] = str(block_doc.pop("_id"))
        return BlockInDB(**block_doc)
    
    async def get_block_range(
        self,
        start_height: int,
        end_height: int
    ) -> List[Block]:
        """
        Get blocks in a height range
        
        Args:
            start_height: Start height (inclusive)
            end_height: End height (inclusive)
            
        Returns:
            List of blocks in range
        """
        query = {
            "height": {"$gte": start_height, "$lte": end_height}
        }
        
        cursor = self.collection.find(query).sort("height", 1)
        blocks = []
        
        async for block_doc in cursor:
            block_doc["block_id"] = str(block_doc.pop("_id"))
            block_dict = {k: v for k, v in block_doc.items() if k in Block.__fields__}
            blocks.append(Block(**block_dict))
        
        return blocks
    
    async def update_confirmations(self, block_id: str, confirmations: int) -> bool:
        """
        Update block confirmations
        
        Args:
            block_id: Block identifier
            confirmations: Number of confirmations
            
        Returns:
            True if updated, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(block_id)},
                {"$set": {"confirmations": confirmations}}
            )
        except Exception as e:
            logger.error(f"Error updating confirmations: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def finalize_block(self, block_id: str) -> bool:
        """
        Mark a block as finalized
        
        Args:
            block_id: Block identifier
            
        Returns:
            True if finalized, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(block_id)},
                {
                    "$set": {
                        "finalized": True,
                        "finalized_at": datetime.utcnow(),
                        "status": BlockStatus.FINALIZED.value
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error finalizing block: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def mark_orphaned(self, block_id: str) -> bool:
        """
        Mark a block as orphaned
        
        Args:
            block_id: Block identifier
            
        Returns:
            True if marked, False otherwise
        """
        from bson import ObjectId
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(block_id)},
                {"$set": {"status": BlockStatus.ORPHANED.value}}
            )
        except Exception as e:
            logger.error(f"Error marking block as orphaned: {str(e)}")
            return False
        
        return result.matched_count > 0
    
    async def list_blocks(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[BlockStatus] = None
    ) -> List[BlockSummary]:
        """
        List blocks with optional filters
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            
        Returns:
            List of block summaries
        """
        query = {}
        
        if status:
            query["status"] = status.value
        
        cursor = self.collection.find(query).sort("height", -1).skip(skip).limit(limit)
        blocks = []
        
        async for block_doc in cursor:
            block_doc["block_id"] = str(block_doc.pop("_id"))
            summary = BlockSummary(
                block_id=block_doc["block_id"],
                height=block_doc["height"],
                timestamp=block_doc["timestamp"],
                transaction_count=block_doc.get("transaction_count", 0),
                session_anchor_count=block_doc.get("session_anchor_count", 0),
                confirmations=block_doc.get("confirmations", 0),
                status=block_doc.get("status", BlockStatus.CONFIRMED.value)
            )
            blocks.append(summary)
        
        return blocks
    
    async def count_blocks(self, status: Optional[BlockStatus] = None) -> int:
        """
        Count blocks with optional filters
        
        Args:
            status: Optional status filter
            
        Returns:
            Number of blocks matching criteria
        """
        query = {}
        
        if status:
            query["status"] = status.value
        
        return await self.collection.count_documents(query)
    
    async def get_chain_height(self) -> int:
        """
        Get current blockchain height
        
        Returns:
            Current height (0 if no blocks)
        """
        latest_block = await self.get_latest_block()
        return latest_block.height if latest_block else 0
    
    async def get_blocks_by_session(self, session_id: str) -> List[Block]:
        """
        Get blocks that contain anchors for a specific session
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of blocks containing session anchors
        """
        query = {"session_anchors.session_id": session_id}
        
        cursor = self.collection.find(query).sort("height", 1)
        blocks = []
        
        async for block_doc in cursor:
            block_doc["block_id"] = str(block_doc.pop("_id"))
            block_dict = {k: v for k, v in block_doc.items() if k in Block.__fields__}
            blocks.append(Block(**block_dict))
        
        return blocks
    
    async def get_block_statistics(self, block_id: str) -> Optional[BlockStatistics]:
        """
        Get block statistics
        
        Args:
            block_id: Block identifier
            
        Returns:
            Block statistics if found, None otherwise
        """
        block = await self.get_by_id(block_id)
        if not block:
            return None
        
        # Get previous block for time calculation
        prev_block = None
        if block.height > 0:
            prev_block = await self.get_by_height(block.height - 1)
        
        time_since_previous = None
        if prev_block:
            time_diff = (block.timestamp - prev_block.timestamp).total_seconds()
            time_since_previous = int(time_diff)
        
        stats = BlockStatistics(
            block_id=block.block_id,
            height=block.height,
            size_bytes=block.size_bytes or 0,
            header_size_bytes=0,  # Would need calculation
            transactions_size_bytes=0,  # Would need calculation
            transaction_count=block.transaction_count,
            session_anchor_count=block.session_anchor_count,
            timestamp=block.timestamp,
            time_since_previous_seconds=time_since_previous,
            processing_time_ms=block.processing_time_ms or 0,
            propagation_time_ms=block.propagation_time_ms,
            validator_count=block.consensus_info.validator_count if block.consensus_info else 0,
            consensus_time_ms=None,
            confirmations=block.confirmations,
            confirmation_time_seconds=None
        )
        
        return stats
    
    async def search_blocks(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[BlockSummary]:
        """
        Search blocks by block ID or hash
        
        Args:
            query: Search query
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching blocks
        """
        search_query = {
            "$or": [
                {"block_id": query},
                {"merkle_root": query}
            ]
        }
        
        cursor = self.collection.find(search_query).sort("height", -1).skip(skip).limit(limit)
        blocks = []
        
        async for block_doc in cursor:
            block_doc["block_id"] = str(block_doc.pop("_id"))
            summary = BlockSummary(
                block_id=block_doc["block_id"],
                height=block_doc["height"],
                timestamp=block_doc["timestamp"],
                transaction_count=block_doc.get("transaction_count", 0),
                session_anchor_count=block_doc.get("session_anchor_count", 0),
                confirmations=block_doc.get("confirmations", 0),
                status=block_doc.get("status", BlockStatus.CONFIRMED.value)
            )
            blocks.append(summary)
        
        return blocks
    
    async def get_recent_blocks(self, limit: int = 10) -> List[BlockSummary]:
        """
        Get most recent blocks
        
        Args:
            limit: Number of blocks to return
            
        Returns:
            List of recent block summaries
        """
        return await self.list_blocks(skip=0, limit=limit)
    
    async def get_blocks_in_time_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Block]:
        """
        Get blocks created within a time range
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            
        Returns:
            List of blocks in time range
        """
        query = {
            "timestamp": {"$gte": start_time, "$lte": end_time}
        }
        
        cursor = self.collection.find(query).sort("timestamp", 1)
        blocks = []
        
        async for block_doc in cursor:
            block_doc["block_id"] = str(block_doc.pop("_id"))
            block_dict = {k: v for k, v in block_doc.items() if k in Block.__fields__}
            blocks.append(Block(**block_dict))
        
        return blocks

