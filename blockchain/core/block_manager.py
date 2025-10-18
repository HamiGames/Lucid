# Path: blockchain/core/block_manager.py
# Lucid Blockchain Core - Block Manager
# Handles block creation, validation, storage and retrieval
# Based on BUILD_REQUIREMENTS_GUIDE.md Step 11 and blockchain cluster specifications

from __future__ import annotations

import asyncio
import logging
import hashlib
import struct
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
import json
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
import blake3

from .models import (
    Block, Transaction, BlockHeader, BlockStatus, ChainType,
    SessionAnchor, ChunkMetadata, generate_session_id
)

logger = logging.getLogger(__name__)

# Block configuration from BUILD_REQUIREMENTS_GUIDE.md
BLOCK_TIME_SECONDS = 10          # Target block time
BLOCK_SIZE_LIMIT_MB = 1          # Maximum block size
MAX_TRANSACTIONS_PER_BLOCK = 1000  # Maximum transactions per block
GENESIS_BLOCK_HEIGHT = 0         # Genesis block height

@dataclass
class BlockValidationResult:
    """Result of block validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class BlockStats:
    """Block statistics"""
    total_blocks: int = 0
    total_transactions: int = 0
    average_block_time: float = 0.0
    average_block_size: float = 0.0
    chain_height: int = 0
    last_block_hash: str = ""

class BlockManager:
    """
    Block Manager for the lucid_blocks blockchain
    
    Responsibilities:
    - Block creation and validation
    - Block storage and retrieval
    - Block height management
    - Blockchain state management
    - Genesis block creation
    - Block integrity verification
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, storage_path: Optional[Path] = None):
        self.db = db
        self.storage_path = storage_path or Path("/data/blocks")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Block cache for recent blocks
        self.block_cache: Dict[str, Block] = {}
        self.height_cache: Dict[int, str] = {}  # height -> block_hash
        
        # Chain state
        self.current_height = 0
        self.latest_block_hash = ""
        self.genesis_block: Optional[Block] = None
        
        # Statistics
        self.stats = BlockStats()
        
        logger.info(f"Block manager initialized with storage: {self.storage_path}")
    
    async def start(self) -> bool:
        """Start the block manager"""
        try:
            # Setup MongoDB indexes
            await self._setup_mongodb_indexes()
            
            # Initialize chain state
            await self._initialize_chain_state()
            
            # Create genesis block if needed
            if self.current_height == 0:
                await self._create_genesis_block()
            
            # Load recent blocks into cache
            await self._load_block_cache()
            
            # Update statistics
            await self._update_statistics()
            
            logger.info(f"Block manager started - Height: {self.current_height}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start block manager: {e}")
            return False
    
    async def stop(self):
        """Stop the block manager"""
        try:
            # Clear caches
            self.block_cache.clear()
            self.height_cache.clear()
            
            logger.info("Block manager stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop block manager: {e}")
    
    async def _setup_mongodb_indexes(self):
        """Setup MongoDB indexes for block collections"""
        try:
            # Blocks collection
            await self.db["blocks"].create_index([("height", 1)], unique=True)
            await self.db["blocks"].create_index([("hash", 1)], unique=True)
            await self.db["blocks"].create_index([("timestamp", -1)])
            await self.db["blocks"].create_index([("producer", 1)])
            await self.db["blocks"].create_index([("previous_hash", 1)])
            
            # Block headers collection (for light clients)
            await self.db["block_headers"].create_index([("height", 1)], unique=True)
            await self.db["block_headers"].create_index([("hash", 1)], unique=True)
            
            # Block metadata collection
            await self.db["block_metadata"].create_index([("block_hash", 1)])
            await self.db["block_metadata"].create_index([("status", 1)])
            
            logger.info("Block manager MongoDB indexes created")
            
        except Exception as e:
            logger.error(f"Failed to setup MongoDB indexes: {e}")
    
    async def _initialize_chain_state(self):
        """Initialize blockchain state from database"""
        try:
            # Get latest block
            latest_block_doc = await self.db["blocks"].find_one({}, sort=[("height", -1)])
            
            if latest_block_doc:
                self.current_height = latest_block_doc["height"]
                self.latest_block_hash = latest_block_doc["hash"]
                
                # Load genesis block
                genesis_doc = await self.db["blocks"].find_one({"height": 0})
                if genesis_doc:
                    self.genesis_block = self._doc_to_block(genesis_doc)
            else:
                self.current_height = 0
                self.latest_block_hash = ""
            
            logger.info(f"Chain state initialized - Height: {self.current_height}")
            
        except Exception as e:
            logger.error(f"Failed to initialize chain state: {e}")
    
    async def _create_genesis_block(self):
        """Create the genesis block (height = 0)"""
        try:
            # Check if genesis block already exists
            existing_genesis = await self.db["blocks"].find_one({"height": 0})
            if existing_genesis:
                self.genesis_block = self._doc_to_block(existing_genesis)
                logger.info("Genesis block already exists")
                return
            
            # Create genesis block
            genesis_timestamp = datetime.now(timezone.utc)
            
            # Genesis transaction (system initialization)
            genesis_tx = Transaction(
                id=f"genesis_{int(genesis_timestamp.timestamp())}",
                from_address="0x0000000000000000000000000000000000000000",
                to_address="0x0000000000000000000000000000000000000000",
                value=0,
                data=json.dumps({
                    "type": "genesis",
                    "network": "lucid_blocks",
                    "version": "1.0.0",
                    "consensus": "PoOT",
                    "created_at": genesis_timestamp.isoformat()
                }),
                timestamp=genesis_timestamp,
                signature="genesis_signature"
            )
            
            # Create genesis block
            self.genesis_block = Block(
                height=0,
                previous_hash="0" * 64,  # Genesis has no previous block
                timestamp=genesis_timestamp,
                transactions=[genesis_tx],
                merkle_root=self._calculate_merkle_root([genesis_tx]),
                producer="genesis",
                signature="genesis_signature"
            )
            
            # Calculate genesis block hash
            self.genesis_block.hash = self._calculate_block_hash(self.genesis_block)
            
            # Store genesis block
            await self._store_block(self.genesis_block)
            
            # Update chain state
            self.current_height = 0
            self.latest_block_hash = self.genesis_block.hash
            
            logger.info(f"Genesis block created: {self.genesis_block.hash}")
            
        except Exception as e:
            logger.error(f"Failed to create genesis block: {e}")
            raise
    
    async def _load_block_cache(self):
        """Load recent blocks into cache"""
        try:
            # Load last 100 blocks into cache
            cursor = self.db["blocks"].find({}).sort("height", -1).limit(100)
            
            async for block_doc in cursor:
                block = self._doc_to_block(block_doc)
                self.block_cache[block.hash] = block
                self.height_cache[block.height] = block.hash
            
            logger.info(f"Loaded {len(self.block_cache)} blocks into cache")
            
        except Exception as e:
            logger.error(f"Failed to load block cache: {e}")
    
    async def _update_statistics(self):
        """Update blockchain statistics"""
        try:
            # Count total blocks
            self.stats.total_blocks = await self.db["blocks"].count_documents({})
            
            # Count total transactions
            pipeline = [
                {"$group": {"_id": None, "total": {"$sum": {"$size": "$transactions"}}}}
            ]
            result = await self.db["blocks"].aggregate(pipeline).to_list(1)
            self.stats.total_transactions = result[0]["total"] if result else 0
            
            # Calculate average block time
            if self.stats.total_blocks > 1:
                pipeline = [
                    {"$sort": {"height": 1}},
                    {"$group": {
                        "_id": None,
                        "timestamps": {"$push": "$timestamp"}
                    }}
                ]
                result = await self.db["blocks"].aggregate(pipeline).to_list(1)
                if result and len(result[0]["timestamps"]) > 1:
                    timestamps = result[0]["timestamps"]
                    total_time = (timestamps[-1] - timestamps[0]).total_seconds()
                    self.stats.average_block_time = total_time / (len(timestamps) - 1)
            
            # Update current state
            self.stats.chain_height = self.current_height
            self.stats.last_block_hash = self.latest_block_hash
            
            logger.debug(f"Statistics updated: {self.stats.total_blocks} blocks, {self.stats.total_transactions} transactions")
            
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
    
    async def create_block(self, transactions: List[Transaction], producer: str) -> Block:
        """Create a new block with the given transactions"""
        try:
            # Validate inputs
            if len(transactions) > MAX_TRANSACTIONS_PER_BLOCK:
                raise ValueError(f"Too many transactions: {len(transactions)} > {MAX_TRANSACTIONS_PER_BLOCK}")
            
            # Get previous block
            prev_block = await self.get_block_by_height(self.current_height)
            if not prev_block and self.current_height > 0:
                raise ValueError("Cannot find previous block")
            
            # Calculate new height
            new_height = self.current_height + 1
            prev_hash = prev_block.hash if prev_block else "0" * 64
            
            # Create new block
            block = Block(
                height=new_height,
                previous_hash=prev_hash,
                timestamp=datetime.now(timezone.utc),
                transactions=transactions,
                merkle_root=self._calculate_merkle_root(transactions),
                producer=producer,
                signature=""  # Will be set by caller
            )
            
            logger.info(f"Block created: height {new_height}, {len(transactions)} transactions")
            return block
            
        except Exception as e:
            logger.error(f"Failed to create block: {e}")
            raise
    
    async def validate_block(self, block: Block) -> BlockValidationResult:
        """Validate a block thoroughly"""
        try:
            result = BlockValidationResult(is_valid=True)
            
            # Basic structure validation
            if not block.hash:
                result.errors.append("Block hash is missing")
            
            if not block.signature:
                result.errors.append("Block signature is missing")
            
            if block.height < 0:
                result.errors.append("Invalid block height")
            
            # Height sequence validation
            if block.height == 0:
                # Genesis block validation
                if block.previous_hash != "0" * 64:
                    result.errors.append("Genesis block must have zero previous hash")
            else:
                # Regular block validation
                prev_block = await self.get_block_by_height(block.height - 1)
                if not prev_block:
                    result.errors.append(f"Previous block not found for height {block.height - 1}")
                elif block.previous_hash != prev_block.hash:
                    result.errors.append("Previous hash mismatch")
            
            # Transaction validation
            if len(block.transactions) > MAX_TRANSACTIONS_PER_BLOCK:
                result.errors.append(f"Too many transactions: {len(block.transactions)}")
            
            # Validate each transaction
            for i, tx in enumerate(block.transactions):
                tx_validation = await self._validate_transaction(tx)
                if not tx_validation.is_valid:
                    result.errors.extend([f"Transaction {i}: {error}" for error in tx_validation.errors])
            
            # Merkle root validation
            calculated_root = self._calculate_merkle_root(block.transactions)
            if block.merkle_root != calculated_root:
                result.errors.append("Merkle root mismatch")
            
            # Block hash validation
            calculated_hash = self._calculate_block_hash(block)
            if block.hash != calculated_hash:
                result.errors.append("Block hash mismatch")
            
            # Timestamp validation
            now = datetime.now(timezone.utc)
            if block.timestamp > now + timedelta(minutes=5):
                result.errors.append("Block timestamp too far in future")
            
            # Block size validation
            block_size = self._calculate_block_size(block)
            if block_size > BLOCK_SIZE_LIMIT_MB * 1024 * 1024:
                result.errors.append(f"Block too large: {block_size} bytes")
            
            # Set final validation result
            result.is_valid = len(result.errors) == 0
            
            if result.is_valid:
                logger.debug(f"Block validation passed: {block.hash}")
            else:
                logger.warning(f"Block validation failed: {result.errors}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to validate block: {e}")
            return BlockValidationResult(is_valid=False, errors=[str(e)])
    
    async def _validate_transaction(self, tx: Transaction) -> BlockValidationResult:
        """Validate a single transaction"""
        try:
            result = BlockValidationResult(is_valid=True)
            
            # Basic validation
            if not tx.id:
                result.errors.append("Transaction ID is missing")
            
            if not tx.signature:
                result.errors.append("Transaction signature is missing")
            
            if not tx.from_address or not tx.to_address:
                result.errors.append("Transaction addresses are missing")
            
            if tx.value < 0:
                result.errors.append("Transaction value cannot be negative")
            
            # Check for duplicate transaction
            existing_tx = await self.db["transactions"].find_one({"id": tx.id})
            if existing_tx:
                result.errors.append("Duplicate transaction ID")
            
            result.is_valid = len(result.errors) == 0
            return result
            
        except Exception as e:
            logger.error(f"Failed to validate transaction: {e}")
            return BlockValidationResult(is_valid=False, errors=[str(e)])
    
    async def add_block(self, block: Block) -> bool:
        """Add a validated block to the blockchain"""
        try:
            # Validate block first
            validation_result = await self.validate_block(block)
            if not validation_result.is_valid:
                logger.error(f"Cannot add invalid block: {validation_result.errors}")
                return False
            
            # Check if block already exists
            existing_block = await self.get_block_by_hash(block.hash)
            if existing_block:
                logger.warning(f"Block already exists: {block.hash}")
                return True
            
            # Store block
            await self._store_block(block)
            
            # Update chain state
            if block.height > self.current_height:
                self.current_height = block.height
                self.latest_block_hash = block.hash
            
            # Update cache
            self.block_cache[block.hash] = block
            self.height_cache[block.height] = block.hash
            
            # Update statistics
            await self._update_statistics()
            
            logger.info(f"Block added to blockchain: height {block.height}, hash {block.hash}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add block: {e}")
            return False
    
    async def _store_block(self, block: Block):
        """Store block in database and filesystem"""
        try:
            # Store in MongoDB
            await self.db["blocks"].insert_one(block.to_dict())
            
            # Store block header separately for light clients
            header = BlockHeader(
                height=block.height,
                hash=block.hash,
                previous_hash=block.previous_hash,
                timestamp=block.timestamp,
                merkle_root=block.merkle_root,
                producer=block.producer,
                transaction_count=len(block.transactions)
            )
            await self.db["block_headers"].insert_one(header.to_dict())
            
            # Store transactions separately
            for tx in block.transactions:
                await self.db["transactions"].insert_one(tx.to_dict())
            
            # Store block metadata
            metadata = {
                "block_hash": block.hash,
                "height": block.height,
                "status": BlockStatus.CONFIRMED.value,
                "size_bytes": self._calculate_block_size(block),
                "transaction_count": len(block.transactions),
                "created_at": datetime.now(timezone.utc)
            }
            await self.db["block_metadata"].insert_one(metadata)
            
            # Store block file on disk (optional)
            if self.storage_path:
                block_file = self.storage_path / f"block_{block.height:010d}.json"
                with open(block_file, 'w') as f:
                    json.dump(block.to_dict(), f, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Failed to store block: {e}")
            raise
    
    async def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Get block by hash"""
        try:
            # Check cache first
            if block_hash in self.block_cache:
                return self.block_cache[block_hash]
            
            # Query database
            block_doc = await self.db["blocks"].find_one({"hash": block_hash})
            if block_doc:
                block = self._doc_to_block(block_doc)
                # Add to cache
                self.block_cache[block_hash] = block
                return block
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get block by hash: {e}")
            return None
    
    async def get_block_by_height(self, height: int) -> Optional[Block]:
        """Get block by height"""
        try:
            # Check cache first
            if height in self.height_cache:
                block_hash = self.height_cache[height]
                return await self.get_block_by_hash(block_hash)
            
            # Query database
            block_doc = await self.db["blocks"].find_one({"height": height})
            if block_doc:
                block = self._doc_to_block(block_doc)
                # Add to cache
                self.block_cache[block.hash] = block
                self.height_cache[height] = block.hash
                return block
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get block by height: {e}")
            return None
    
    async def get_latest_block(self) -> Optional[Block]:
        """Get the latest block"""
        try:
            if self.latest_block_hash:
                return await self.get_block_by_hash(self.latest_block_hash)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest block: {e}")
            return None
    
    async def get_blocks(self, start_height: int = 0, limit: int = 100) -> List[Block]:
        """Get multiple blocks starting from height"""
        try:
            blocks = []
            cursor = self.db["blocks"].find({
                "height": {"$gte": start_height}
            }).sort("height", 1).limit(limit)
            
            async for block_doc in cursor:
                block = self._doc_to_block(block_doc)
                blocks.append(block)
            
            return blocks
            
        except Exception as e:
            logger.error(f"Failed to get blocks: {e}")
            return []
    
    async def get_block_headers(self, start_height: int = 0, limit: int = 100) -> List[BlockHeader]:
        """Get block headers for light clients"""
        try:
            headers = []
            cursor = self.db["block_headers"].find({
                "height": {"$gte": start_height}
            }).sort("height", 1).limit(limit)
            
            async for header_doc in cursor:
                header = BlockHeader(
                    height=header_doc["height"],
                    hash=header_doc["hash"],
                    previous_hash=header_doc["previous_hash"],
                    timestamp=header_doc["timestamp"],
                    merkle_root=header_doc["merkle_root"],
                    producer=header_doc["producer"],
                    transaction_count=header_doc["transaction_count"]
                )
                headers.append(header)
            
            return headers
            
        except Exception as e:
            logger.error(f"Failed to get block headers: {e}")
            return []
    
    def _calculate_merkle_root(self, transactions: List[Transaction]) -> str:
        """Calculate Merkle root for transactions"""
        if not transactions:
            return "0" * 64
        
        # Create leaf hashes
        leaves = [blake3.blake3(tx.id.encode()).hexdigest() for tx in transactions]
        
        # Build Merkle tree
        while len(leaves) > 1:
            next_level = []
            for i in range(0, len(leaves), 2):
                left = leaves[i]
                right = leaves[i + 1] if i + 1 < len(leaves) else left
                combined = blake3.blake3((left + right).encode()).hexdigest()
                next_level.append(combined)
            leaves = next_level
        
        return leaves[0] if leaves else "0" * 64
    
    def _calculate_block_hash(self, block: Block) -> str:
        """Calculate the hash of a block"""
        # Create block header data for hashing
        header_data = (
            f"{block.height}"
            f"{block.previous_hash}"
            f"{block.timestamp.isoformat()}"
            f"{block.merkle_root}"
            f"{block.producer}"
            f"{len(block.transactions)}"
        )
        
        return blake3.blake3(header_data.encode()).hexdigest()
    
    def _calculate_block_size(self, block: Block) -> int:
        """Calculate the size of a block in bytes"""
        try:
            block_json = json.dumps(block.to_dict(), default=str)
            return len(block_json.encode('utf-8'))
        except Exception:
            return 0
    
    def _doc_to_block(self, doc: Dict[str, Any]) -> Block:
        """Convert MongoDB document to Block object"""
        transactions = []
        for tx_doc in doc.get("transactions", []):
            tx = Transaction(
                id=tx_doc["id"],
                from_address=tx_doc["from_address"],
                to_address=tx_doc["to_address"],
                value=tx_doc["value"],
                data=tx_doc.get("data", ""),
                timestamp=tx_doc["timestamp"],
                signature=tx_doc["signature"]
            )
            transactions.append(tx)
        
        return Block(
            height=doc["height"],
            hash=doc["hash"],
            previous_hash=doc["previous_hash"],
            timestamp=doc["timestamp"],
            transactions=transactions,
            merkle_root=doc["merkle_root"],
            producer=doc["producer"],
            signature=doc["signature"]
        )
    
    async def get_blockchain_info(self) -> Dict[str, Any]:
        """Get comprehensive blockchain information"""
        try:
            await self._update_statistics()
            
            return {
                "network": "lucid_blocks",
                "version": "1.0.0",
                "consensus": "PoOT",
                "current_height": self.current_height,
                "latest_block_hash": self.latest_block_hash,
                "genesis_block_hash": self.genesis_block.hash if self.genesis_block else None,
                "total_blocks": self.stats.total_blocks,
                "total_transactions": self.stats.total_transactions,
                "average_block_time": self.stats.average_block_time,
                "block_size_limit_mb": BLOCK_SIZE_LIMIT_MB,
                "max_transactions_per_block": MAX_TRANSACTIONS_PER_BLOCK,
                "target_block_time": BLOCK_TIME_SECONDS
            }
            
        except Exception as e:
            logger.error(f"Failed to get blockchain info: {e}")
            return {}
    
    async def get_blockchain_status(self) -> Dict[str, Any]:
        """Get current blockchain status"""
        try:
            latest_block = await self.get_latest_block()
            
            # Calculate sync status
            now = datetime.now(timezone.utc)
            last_block_time = latest_block.timestamp if latest_block else now
            time_since_last_block = (now - last_block_time).total_seconds()
            
            is_synced = time_since_last_block < BLOCK_TIME_SECONDS * 3  # Within 3 block times
            
            return {
                "is_synced": is_synced,
                "current_height": self.current_height,
                "latest_block_hash": self.latest_block_hash,
                "last_block_time": last_block_time.isoformat() if latest_block else None,
                "time_since_last_block": time_since_last_block,
                "cache_size": len(self.block_cache),
                "status": "healthy" if is_synced else "syncing"
            }
            
        except Exception as e:
            logger.error(f"Failed to get blockchain status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def verify_chain_integrity(self, start_height: int = 0, end_height: Optional[int] = None) -> Dict[str, Any]:
        """Verify the integrity of the blockchain"""
        try:
            if end_height is None:
                end_height = self.current_height
            
            errors = []
            warnings = []
            blocks_checked = 0
            
            for height in range(start_height, end_height + 1):
                block = await self.get_block_by_height(height)
                if not block:
                    errors.append(f"Missing block at height {height}")
                    continue
                
                # Validate block
                validation_result = await self.validate_block(block)
                if not validation_result.is_valid:
                    errors.extend([f"Height {height}: {error}" for error in validation_result.errors])
                
                warnings.extend([f"Height {height}: {warning}" for warning in validation_result.warnings])
                blocks_checked += 1
            
            return {
                "is_valid": len(errors) == 0,
                "blocks_checked": blocks_checked,
                "errors": errors,
                "warnings": warnings,
                "start_height": start_height,
                "end_height": end_height
            }
            
        except Exception as e:
            logger.error(f"Failed to verify chain integrity: {e}")
            return {"is_valid": False, "error": str(e)}
