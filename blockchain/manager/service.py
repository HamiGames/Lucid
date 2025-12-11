"""
Block Manager Service
Core service for block management operations

This service integrates with the blockchain core to provide
block management functionality for the Lucid RDP system.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..core.block_manager import BlockManager, BlockValidationResult, BlockStats
from ..core.models import Transaction
from .storage import BlockStorage
from .validation import BlockValidator
from .synchronization import ChainSynchronizer

logger = logging.getLogger(__name__)

# Environment variable configuration (required, no hardcoded defaults)
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL or MONGODB_URL environment variable not set")

BLOCK_STORAGE_PATH = os.getenv("BLOCK_STORAGE_PATH", "/data/blocks")
BLOCKCHAIN_ENGINE_URL = os.getenv("BLOCKCHAIN_ENGINE_URL")
if not BLOCKCHAIN_ENGINE_URL:
    raise RuntimeError("BLOCKCHAIN_ENGINE_URL environment variable not set")


class BlockManagerService:
    """
    Main block manager service.
    
    Handles block operations including creation, storage, retrieval, and validation.
    Integrates with MongoDB for persistence and blockchain engine for operations.
    """
    
    def __init__(self, mongo_client: Optional[AsyncIOMotorClient] = None):
        """
        Initialize block manager service.
        
        Args:
            mongo_client: Optional MongoDB client. If not provided, creates new client.
        """
        if mongo_client:
            self.mongo_client = mongo_client
        else:
            self.mongo_client = AsyncIOMotorClient(MONGO_URL)
        
        self.db: AsyncIOMotorDatabase = self.mongo_client.get_database("lucid")
        
        # Initialize core block manager
        storage_path = Path(BLOCK_STORAGE_PATH)
        self.block_manager = BlockManager(self.db, storage_path)
        
        # Initialize storage
        self.storage = BlockStorage(self.db, storage_path)
        
        # Initialize validator
        self.validator = BlockValidator(self.block_manager)
        
        # Initialize synchronizer
        self.synchronizer = ChainSynchronizer(
            self.block_manager,
            self.storage,
            BLOCKCHAIN_ENGINE_URL
        )
        
        logger.info("BlockManagerService initialized")
    
    async def start(self) -> bool:
        """
        Start the block manager service.
        
        Returns:
            True if started successfully
        """
        try:
            # Start core block manager
            await self.block_manager.start()
            
            # Initialize storage
            await self.storage.initialize()
            
            logger.info("BlockManagerService started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start BlockManagerService: {e}", exc_info=True)
            return False
    
    async def stop(self):
        """Stop the block manager service."""
        try:
            await self.block_manager.stop()
            logger.info("BlockManagerService stopped")
        except Exception as e:
            logger.error(f"Failed to stop BlockManagerService: {e}")
    
    async def create_block(
        self,
        transactions: List[Transaction],
        producer: str
    ) -> Dict[str, Any]:
        """
        Create a new block with the given transactions.
        
        Args:
            transactions: List of transactions to include in block
            producer: Block producer identifier
            
        Returns:
            Dictionary containing block information
        """
        try:
            logger.info(f"Creating block with {len(transactions)} transactions, producer: {producer}")
            
            # Create block using core block manager
            block = await self.block_manager.create_block(transactions, producer)
            
            # Store block
            await self.storage.store_block(block)
            
            # Calculate hash if not set
            if not hasattr(block, 'hash') or not block.hash:
                block.hash = self.block_manager._calculate_block_hash(block)
            
            logger.info(f"Block created: height {block.height}, hash {block.hash}")
            
            return {
                "block_id": block.hash,
                "height": block.height,
                "hash": block.hash,
                "previous_hash": block.previous_hash,
                "merkle_root": block.merkle_root,
                "timestamp": block.timestamp.isoformat() if hasattr(block.timestamp, 'isoformat') else str(block.timestamp),
                "transaction_count": len(block.transactions),
                "producer": block.producer,
                "signature": block.signature
            }
            
        except Exception as e:
            logger.error(f"Failed to create block: {e}", exc_info=True)
            raise
    
    async def get_block_by_id(self, block_id: str) -> Optional[Dict[str, Any]]:
        """
        Get block by ID (hash or height).
        
        Args:
            block_id: Block hash or height string
            
        Returns:
            Dictionary containing block information or None if not found
        """
        try:
            logger.info(f"Fetching block by ID: {block_id}")
            
            # Try as hash first
            block = await self.storage.get_block_by_hash(block_id)
            
            # If not found, try as height
            if not block:
                try:
                    height = int(block_id)
                    block = await self.storage.get_block_by_height(height)
                except ValueError:
                    pass
            
            if not block:
                return None
            
            return self._block_to_dict(block)
            
        except Exception as e:
            logger.error(f"Failed to get block by ID {block_id}: {e}", exc_info=True)
            return None
    
    async def get_block_by_height(self, height: int) -> Optional[Dict[str, Any]]:
        """
        Get block by height.
        
        Args:
            height: Block height
            
        Returns:
            Dictionary containing block information or None if not found
        """
        try:
            block = await self.storage.get_block_by_height(height)
            if not block:
                return None
            
            return self._block_to_dict(block)
            
        except Exception as e:
            logger.error(f"Failed to get block by height {height}: {e}")
            return None
    
    async def get_latest_block(self) -> Dict[str, Any]:
        """
        Get the latest block.
        
        Returns:
            Dictionary containing latest block information
        """
        try:
            block = await self.storage.get_latest_block()
            if not block:
                # Return genesis block info if no blocks exist
                return {
                    "block_id": "genesis",
                    "height": 0,
                    "hash": "",
                    "message": "No blocks found"
                }
            
            return self._block_to_dict(block)
            
        except Exception as e:
            logger.error(f"Failed to get latest block: {e}")
            raise
    
    async def list_blocks(
        self,
        page: int = 1,
        limit: int = 20,
        height_from: Optional[int] = None,
        height_to: Optional[int] = None,
        sort: str = "height_desc"
    ) -> Dict[str, Any]:
        """
        List blocks with pagination and filtering.
        
        Args:
            page: Page number (1-indexed)
            limit: Number of blocks per page
            height_from: Minimum block height
            height_to: Maximum block height
            sort: Sort order (height_asc, height_desc, timestamp_asc, timestamp_desc)
            
        Returns:
            Dictionary containing blocks and pagination info
        """
        try:
            logger.info(f"Listing blocks: page={page}, limit={limit}, height_from={height_from}, height_to={height_to}, sort={sort}")
            
            # Parse sort
            sort_field = "height"
            sort_direction = -1  # DESC
            
            if sort == "height_asc":
                sort_field = "height"
                sort_direction = 1
            elif sort == "height_desc":
                sort_field = "height"
                sort_direction = -1
            elif sort == "timestamp_asc":
                sort_field = "timestamp"
                sort_direction = 1
            elif sort == "timestamp_desc":
                sort_field = "timestamp"
                sort_direction = -1
            
            # Get blocks
            blocks = await self.storage.list_blocks(
                page=page,
                limit=limit,
                height_from=height_from,
                height_to=height_to,
                sort_field=sort_field,
                sort_direction=sort_direction
            )
            
            # Get total count
            total = await self.storage.get_total_blocks()
            
            return {
                "blocks": [self._block_to_dict(block) for block in blocks],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit if limit > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to list blocks: {e}", exc_info=True)
            raise
    
    async def validate_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate block structure and integrity.
        
        Args:
            block_data: Block data dictionary
            
        Returns:
            Dictionary containing validation results
        """
        try:
            logger.info("Validating block structure")
            
            # Convert dict to Block object if needed
            if isinstance(block_data, dict):
                # Basic validation first
                validation_result = await self.validator.validate_block_structure(block_data)
                
                if not validation_result["valid"]:
                    return validation_result
                
                # If structure is valid, try to create Block object for full validation
                try:
                    block = await self.validator.block_from_dict(block_data)
                    full_validation = await self.validator.validate_block(block)
                    
                    return {
                        "valid": full_validation.is_valid,
                        "validation_results": {
                            "structure_valid": validation_result["valid"],
                            "integrity_valid": full_validation.is_valid,
                            "signature_valid": len([e for e in full_validation.errors if "signature" in e.lower()]) == 0,
                            "merkle_root_valid": len([e for e in full_validation.errors if "merkle" in e.lower()]) == 0,
                            "timestamp_valid": len([e for e in full_validation.errors if "timestamp" in e.lower()]) == 0,
                            "transactions_valid": len([e for e in full_validation.errors if "transaction" in e.lower()]) == 0
                        },
                        "errors": full_validation.errors,
                        "warnings": full_validation.warnings
                    }
                except Exception as e:
                    return {
                        "valid": False,
                        "validation_results": {
                            "structure_valid": validation_result["valid"],
                            "integrity_valid": False
                        },
                        "errors": validation_result.get("errors", []) + [f"Failed to parse block: {str(e)}"],
                        "warnings": validation_result.get("warnings", [])
                    }
            else:
                return {
                    "valid": False,
                    "errors": ["Invalid block data format"],
                    "warnings": []
                }
                
        except Exception as e:
            logger.error(f"Failed to validate block: {e}", exc_info=True)
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get current status of block manager service.
        
        Returns:
            Dictionary containing service status metrics
        """
        try:
            # Get statistics from block manager
            stats: BlockStats = self.block_manager.stats
            
            # Get storage statistics
            storage_stats = await self.storage.get_statistics()
            
            return {
                "status": "healthy",
                "chain_height": stats.chain_height,
                "total_blocks": stats.total_blocks,
                "total_transactions": stats.total_transactions,
                "average_block_time": stats.average_block_time,
                "average_block_size": stats.average_block_size,
                "last_block_hash": stats.last_block_hash,
                "storage": storage_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}", exc_info=True)
            return {
                "status": "degraded",
                "error": str(e)
            }
    
    async def synchronize_chain(self) -> Dict[str, Any]:
        """
        Synchronize chain with blockchain engine.
        
        Returns:
            Dictionary containing synchronization results
        """
        try:
            logger.info("Starting chain synchronization")
            result = await self.synchronizer.synchronize()
            return result
            
        except Exception as e:
            logger.error(f"Failed to synchronize chain: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _block_to_dict(self, block) -> Dict[str, Any]:
        """Convert Block object to dictionary."""
        return {
            "block_id": block.hash,
            "height": block.height,
            "hash": block.hash,
            "previous_hash": block.previous_hash,
            "merkle_root": block.merkle_root,
            "timestamp": block.timestamp.isoformat() if hasattr(block.timestamp, 'isoformat') else str(block.timestamp),
            "transaction_count": len(block.transactions),
            "transactions": [
                {
                    "tx_id": tx.id,
                    "type": getattr(tx, 'type', 'unknown'),
                    "from_address": getattr(tx, 'from_address', ''),
                    "to_address": getattr(tx, 'to_address', ''),
                    "value": getattr(tx, 'value', 0),
                    "timestamp": tx.timestamp.isoformat() if hasattr(tx.timestamp, 'isoformat') else str(tx.timestamp)
                }
                for tx in block.transactions
            ],
            "producer": block.producer,
            "signature": block.signature,
            "size_bytes": getattr(block, 'size_bytes', 0)
        }
    
    async def close(self):
        """Close service and cleanup resources."""
        try:
            await self.stop()
            self.mongo_client.close()
            logger.info("BlockManagerService closed")
        except Exception as e:
            logger.error(f"Error closing BlockManagerService: {e}")

