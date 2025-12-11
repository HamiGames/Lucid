"""
Block Storage Module
Handles persistence of blocks in MongoDB and file system

This module provides storage operations for block data.
"""

from __future__ import annotations

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from ..core.models import Transaction

logger = logging.getLogger(__name__)


class BlockStorage:
    """
    Storage layer for blocks.
    
    Handles MongoDB operations and file system storage for block data.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, storage_path: Path):
        """
        Initialize block storage.
        
        Args:
            db: MongoDB database instance
            storage_path: Path for file system storage
        """
        self.db = db
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.collection: AsyncIOMotorCollection = db["blocks"]
        logger.info(f"BlockStorage initialized with path: {storage_path}")
    
    async def initialize(self):
        """Initialize storage indexes."""
        try:
            # Create indexes for efficient queries
            await self.collection.create_index("height", unique=True)
            await self.collection.create_index("hash", unique=True)
            await self.collection.create_index("timestamp")
            await self.collection.create_index("producer")
            await self.collection.create_index("previous_hash")
            await self.collection.create_index([("height", -1), ("timestamp", -1)])
            
            logger.info("BlockStorage indexes created")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def store_block(self, block) -> bool:
        """
        Store block in database and file system.
        
        Args:
            block: Block object to store
            
        Returns:
            True if successful
        """
        try:
            # Convert block to document
            block_doc = self._block_to_document(block)
            
            # Store in MongoDB
            await self.collection.replace_one(
                {"hash": block.hash},
                block_doc,
                upsert=True
            )
            
            # Store in file system (backup)
            block_file = self.storage_path / f"{block.height:010d}_{block.hash[:16]}.json"
            with open(block_file, 'w') as f:
                json.dump(block_doc, f, indent=2, default=str)
            
            logger.debug(f"Stored block: height {block.height}, hash {block.hash}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store block {block.hash}: {e}")
            return False
    
    async def get_block_by_hash(self, block_hash: str):
        """
        Get block by hash.
        
        Args:
            block_hash: Block hash
            
        Returns:
            Block object or None if not found
        """
        try:
            block_doc = await self.collection.find_one({"hash": block_hash})
            if not block_doc:
                return None
            
            return self._document_to_block(block_doc)
            
        except Exception as e:
            logger.error(f"Failed to get block by hash {block_hash}: {e}")
            return None
    
    async def get_block_by_height(self, height: int):
        """
        Get block by height.
        
        Args:
            height: Block height
            
        Returns:
            Block object or None if not found
        """
        try:
            block_doc = await self.collection.find_one({"height": height})
            if not block_doc:
                return None
            
            return self._document_to_block(block_doc)
            
        except Exception as e:
            logger.error(f"Failed to get block by height {height}: {e}")
            return None
    
    async def get_latest_block(self):
        """
        Get the latest block (highest height).
        
        Returns:
            Block object or None if no blocks exist
        """
        try:
            block_doc = await self.collection.find_one(
                {},
                sort=[("height", -1)]
            )
            if not block_doc:
                return None
            
            return self._document_to_block(block_doc)
            
        except Exception as e:
            logger.error(f"Failed to get latest block: {e}")
            return None
    
    async def list_blocks(
        self,
        page: int = 1,
        limit: int = 20,
        height_from: Optional[int] = None,
        height_to: Optional[int] = None,
        sort_field: str = "height",
        sort_direction: int = -1
    ) -> List:
        """
        List blocks with pagination and filtering.
        
        Args:
            page: Page number (1-indexed)
            limit: Number of blocks per page
            height_from: Minimum block height
            height_to: Maximum block height
            sort_field: Field to sort by
            sort_direction: Sort direction (1 for asc, -1 for desc)
            
        Returns:
            List of Block objects
        """
        try:
            # Build query
            query: Dict[str, Any] = {}
            if height_from is not None or height_to is not None:
                height_query: Dict[str, Any] = {}
                if height_from is not None:
                    height_query["$gte"] = height_from
                if height_to is not None:
                    height_query["$lte"] = height_to
                query["height"] = height_query
            
            # Calculate skip
            skip = (page - 1) * limit
            
            # Query blocks
            cursor = self.collection.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
            
            blocks = []
            async for block_doc in cursor:
                blocks.append(self._document_to_block(block_doc))
            
            return blocks
            
        except Exception as e:
            logger.error(f"Failed to list blocks: {e}")
            return []
    
    async def get_total_blocks(self) -> int:
        """
        Get total number of blocks.
        
        Returns:
            Total block count
        """
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Failed to get total blocks: {e}")
            return 0
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary containing statistics
        """
        try:
            total_blocks = await self.get_total_blocks()
            
            # Get latest block
            latest = await self.get_latest_block()
            latest_height = latest.height if latest else 0
            
            # Count file system blocks
            file_count = len(list(self.storage_path.glob("*.json"))) if self.storage_path.exists() else 0
            
            return {
                "total_blocks": total_blocks,
                "latest_height": latest_height,
                "file_system_blocks": file_count,
                "storage_path": str(self.storage_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "total_blocks": 0,
                "latest_height": 0,
                "file_system_blocks": 0,
                "storage_path": str(self.storage_path)
            }
    
    def _block_to_document(self, block) -> Dict[str, Any]:
        """Convert Block object to MongoDB document."""
        return {
            "_id": block.hash,
            "hash": block.hash,
            "height": block.height,
            "previous_hash": block.previous_hash,
            "merkle_root": block.merkle_root,
            "timestamp": block.timestamp,
            "producer": block.producer,
            "signature": block.signature,
            "transactions": [
                {
                    "id": tx.id,
                    "from_address": getattr(tx, 'from_address', ''),
                    "to_address": getattr(tx, 'to_address', ''),
                    "value": getattr(tx, 'value', 0),
                    "data": getattr(tx, 'data', ''),
                    "timestamp": tx.timestamp,
                    "signature": getattr(tx, 'signature', '')
                }
                for tx in block.transactions
            ],
            "size_bytes": getattr(block, 'size_bytes', 0),
            "created_at": datetime.now(timezone.utc)
        }
    
    def _document_to_block(self, doc: Dict[str, Any]):
        """Convert MongoDB document to Block object."""
        # Use the same structure as block_manager._doc_to_block
        # Block is created with these fields based on block_manager usage
        transactions = []
        for tx_doc in doc.get("transactions", []):
            tx = Transaction(
                id=tx_doc.get("id", ""),
                from_address=tx_doc.get("from_address", ""),
                to_address=tx_doc.get("to_address", ""),
                value=tx_doc.get("value", 0),
                data=tx_doc.get("data", ""),
                timestamp=tx_doc.get("timestamp"),
                signature=tx_doc.get("signature", "")
            )
            transactions.append(tx)
        
        # Create a simple Block-like object (matches block_manager structure)
        # Block has: height, hash, previous_hash, timestamp, transactions, merkle_root, producer, signature
        from types import SimpleNamespace
        block = SimpleNamespace()
        block.height = doc["height"]
        block.hash = doc["hash"]
        block.previous_hash = doc["previous_hash"]
        block.timestamp = doc["timestamp"]
        block.transactions = transactions
        block.merkle_root = doc["merkle_root"]
        block.producer = doc["producer"]
        block.signature = doc["signature"]
        block.size_bytes = doc.get("size_bytes", 0)
        
        return block

