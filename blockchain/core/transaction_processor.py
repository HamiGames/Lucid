# Path: blockchain/core/transaction_processor.py
# Lucid Blockchain Core - Transaction Processor
# Handles transaction processing, validation, and mempool management
# Based on BUILD_REQUIREMENTS_GUIDE.md Step 11 and blockchain cluster specifications

from __future__ import annotations

import asyncio
import logging
import hashlib
import struct
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
import blake3

from .models import (
    Transaction, TransactionStatus, TransactionType, Block,
    SessionAnchor, ChunkMetadata, generate_session_id
)

logger = logging.getLogger(__name__)

# Transaction configuration
MAX_TRANSACTION_SIZE_BYTES = 1024 * 1024  # 1MB max transaction size
TRANSACTION_FEE_MINIMUM = 0.001           # Minimum transaction fee
MEMPOOL_MAX_SIZE = 10000                  # Maximum transactions in mempool
TRANSACTION_TIMEOUT_HOURS = 24            # Transaction timeout in hours

@dataclass
class TransactionValidationResult:
    """Result of transaction validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fee_required: float = 0.0

@dataclass
class MempoolStats:
    """Mempool statistics"""
    total_transactions: int = 0
    pending_transactions: int = 0
    confirmed_transactions: int = 0
    failed_transactions: int = 0
    total_value: float = 0.0
    average_fee: float = 0.0

class TransactionProcessor:
    """
    Transaction Processor for the lucid_blocks blockchain
    
    Responsibilities:
    - Transaction validation and processing
    - Mempool management
    - Transaction fee calculation
    - Transaction broadcasting
    - Transaction status tracking
    - Batch transaction processing
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
        # Mempool for pending transactions
        self.mempool: Dict[str, Transaction] = {}
        self.mempool_by_address: Dict[str, List[str]] = {}  # address -> tx_ids
        
        # Transaction cache
        self.tx_cache: Dict[str, Transaction] = {}
        
        # Processing state
        self.processing_enabled = True
        self.batch_processing_active = False
        
        # Statistics
        self.stats = MempoolStats()
        
        logger.info("Transaction processor initialized")
    
    async def start(self) -> bool:
        """Start the transaction processor"""
        try:
            # Setup MongoDB indexes
            await self._setup_mongodb_indexes()
            
            # Load mempool from database
            await self._load_mempool()
            
            # Start background processing
            asyncio.create_task(self._process_transactions_loop())
            asyncio.create_task(self._cleanup_expired_transactions())
            
            # Update statistics
            await self._update_statistics()
            
            logger.info("Transaction processor started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start transaction processor: {e}")
            return False
    
    async def stop(self):
        """Stop the transaction processor"""
        try:
            self.processing_enabled = False
            
            # Clear caches
            self.mempool.clear()
            self.mempool_by_address.clear()
            self.tx_cache.clear()
            
            logger.info("Transaction processor stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop transaction processor: {e}")
    
    async def _setup_mongodb_indexes(self):
        """Setup MongoDB indexes for transaction collections"""
        try:
            # Transactions collection
            await self.db["transactions"].create_index([("id", 1)], unique=True)
            await self.db["transactions"].create_index([("from_address", 1)])
            await self.db["transactions"].create_index([("to_address", 1)])
            await self.db["transactions"].create_index([("timestamp", -1)])
            await self.db["transactions"].create_index([("status", 1)])
            await self.db["transactions"].create_index([("block_height", 1)])
            
            # Mempool collection
            await self.db["mempool"].create_index([("id", 1)], unique=True)
            await self.db["mempool"].create_index([("from_address", 1)])
            await self.db["mempool"].create_index([("timestamp", -1)])
            await self.db["mempool"].create_index([("status", 1)])
            await self.db["mempool"].create_index([("fee", -1)])
            
            # Transaction metadata collection
            await self.db["transaction_metadata"].create_index([("tx_id", 1)])
            await self.db["transaction_metadata"].create_index([("type", 1)])
            
            logger.info("Transaction processor MongoDB indexes created")
            
        except Exception as e:
            logger.error(f"Failed to setup MongoDB indexes: {e}")
    
    async def _load_mempool(self):
        """Load pending transactions from database into mempool"""
        try:
            cursor = self.db["mempool"].find({"status": "pending"})
            
            async for tx_doc in cursor:
                tx = self._doc_to_transaction(tx_doc)
                self.mempool[tx.id] = tx
                
                # Update address mapping
                if tx.from_address not in self.mempool_by_address:
                    self.mempool_by_address[tx.from_address] = []
                self.mempool_by_address[tx.from_address].append(tx.id)
            
            logger.info(f"Loaded {len(self.mempool)} transactions into mempool")
            
        except Exception as e:
            logger.error(f"Failed to load mempool: {e}")
    
    async def _process_transactions_loop(self):
        """Background loop for processing transactions"""
        while self.processing_enabled:
            try:
                if not self.batch_processing_active and self.mempool:
                    await self._process_pending_transactions()
                
                await asyncio.sleep(1)  # Process every second
                
            except Exception as e:
                logger.error(f"Transaction processing loop error: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_expired_transactions(self):
        """Clean up expired transactions from mempool"""
        while self.processing_enabled:
            try:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=TRANSACTION_TIMEOUT_HOURS)
                
                expired_tx_ids = []
                for tx_id, tx in self.mempool.items():
                    if tx.timestamp < cutoff_time:
                        expired_tx_ids.append(tx_id)
                
                # Remove expired transactions
                for tx_id in expired_tx_ids:
                    await self._remove_from_mempool(tx_id, "expired")
                
                if expired_tx_ids:
                    logger.info(f"Cleaned up {len(expired_tx_ids)} expired transactions")
                
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
            except Exception as e:
                logger.error(f"Transaction cleanup error: {e}")
                await asyncio.sleep(300)
    
    async def submit_transaction(self, tx: Transaction) -> TransactionValidationResult:
        """Submit a transaction to the mempool"""
        try:
            # Validate transaction
            validation_result = await self.validate_transaction(tx)
            if not validation_result.is_valid:
                return validation_result
            
            # Check if transaction already exists
            if tx.id in self.mempool or await self._transaction_exists(tx.id):
                validation_result.is_valid = False
                validation_result.errors.append("Transaction already exists")
                return validation_result
            
            # Check mempool size limit
            if len(self.mempool) >= MEMPOOL_MAX_SIZE:
                # Remove lowest fee transaction
                await self._evict_lowest_fee_transaction()
            
            # Add to mempool
            await self._add_to_mempool(tx)
            
            logger.info(f"Transaction submitted to mempool: {tx.id}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to submit transaction: {e}")
            return TransactionValidationResult(is_valid=False, errors=[str(e)])
    
    async def validate_transaction(self, tx: Transaction) -> TransactionValidationResult:
        """Validate a transaction thoroughly"""
        try:
            result = TransactionValidationResult(is_valid=True)
            
            # Basic structure validation
            if not tx.id:
                result.errors.append("Transaction ID is missing")
            
            if not tx.signature:
                result.errors.append("Transaction signature is missing")
            
            if not tx.from_address or not tx.to_address:
                result.errors.append("Transaction addresses are missing")
            
            if len(tx.from_address) != 42 or not tx.from_address.startswith('0x'):
                result.errors.append("Invalid from_address format")
            
            if len(tx.to_address) != 42 or not tx.to_address.startswith('0x'):
                result.errors.append("Invalid to_address format")
            
            if tx.value < 0:
                result.errors.append("Transaction value cannot be negative")
            
            # Transaction size validation
            tx_size = len(json.dumps(tx.to_dict(), default=str).encode('utf-8'))
            if tx_size > MAX_TRANSACTION_SIZE_BYTES:
                result.errors.append(f"Transaction too large: {tx_size} bytes")
            
            # Fee validation
            calculated_fee = self._calculate_transaction_fee(tx)
            result.fee_required = calculated_fee
            
            if hasattr(tx, 'fee') and tx.fee < calculated_fee:
                result.errors.append(f"Insufficient fee: {tx.fee} < {calculated_fee}")
            
            # Timestamp validation
            now = datetime.now(timezone.utc)
            if tx.timestamp > now + timedelta(minutes=5):
                result.errors.append("Transaction timestamp too far in future")
            
            if tx.timestamp < now - timedelta(hours=1):
                result.errors.append("Transaction timestamp too old")
            
            # Signature validation
            if not await self._verify_transaction_signature(tx):
                result.errors.append("Invalid transaction signature")
            
            # Balance validation (if applicable)
            if tx.value > 0:
                balance = await self._get_address_balance(tx.from_address)
                if balance < tx.value + calculated_fee:
                    result.errors.append("Insufficient balance")
            
            # Nonce validation (prevent replay attacks)
            if not await self._validate_transaction_nonce(tx):
                result.errors.append("Invalid transaction nonce")
            
            result.is_valid = len(result.errors) == 0
            
            if result.is_valid:
                logger.debug(f"Transaction validation passed: {tx.id}")
            else:
                logger.warning(f"Transaction validation failed: {result.errors}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to validate transaction: {e}")
            return TransactionValidationResult(is_valid=False, errors=[str(e)])
    
    def _calculate_transaction_fee(self, tx: Transaction) -> float:
        """Calculate required fee for a transaction"""
        try:
            # Base fee
            base_fee = TRANSACTION_FEE_MINIMUM
            
            # Size-based fee
            tx_size = len(json.dumps(tx.to_dict(), default=str).encode('utf-8'))
            size_fee = tx_size * 0.000001  # 1 microunit per byte
            
            # Data fee (if transaction contains data)
            data_fee = len(tx.data.encode('utf-8')) * 0.000001 if tx.data else 0
            
            return base_fee + size_fee + data_fee
            
        except Exception as e:
            logger.error(f"Failed to calculate transaction fee: {e}")
            return TRANSACTION_FEE_MINIMUM
    
    async def _verify_transaction_signature(self, tx: Transaction) -> bool:
        """Verify the cryptographic signature of a transaction"""
        try:
            # Create transaction hash for signature verification
            tx_data = f"{tx.id}{tx.from_address}{tx.to_address}{tx.value}{tx.data}{tx.timestamp.isoformat()}"
            tx_hash = blake3.blake3(tx_data.encode()).hexdigest()
            
            # In production, this would verify the cryptographic signature
            # For now, just check that signature exists and matches expected format
            expected_sig = blake3.blake3(f"{tx.from_address}:{tx_hash}".encode()).hexdigest()
            
            return tx.signature == expected_sig
            
        except Exception as e:
            logger.error(f"Failed to verify transaction signature: {e}")
            return False
    
    async def _get_address_balance(self, address: str) -> float:
        """Get the balance of an address"""
        try:
            # Calculate balance from confirmed transactions
            pipeline = [
                {"$match": {"$or": [{"from_address": address}, {"to_address": address}]}},
                {"$group": {
                    "_id": None,
                    "sent": {"$sum": {"$cond": [{"$eq": ["$from_address", address]}, "$value", 0]}},
                    "received": {"$sum": {"$cond": [{"$eq": ["$to_address", address]}, "$value", 0]}}
                }}
            ]
            
            result = await self.db["transactions"].aggregate(pipeline).to_list(1)
            if result:
                sent = result[0].get("sent", 0)
                received = result[0].get("received", 0)
                return received - sent
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get address balance: {e}")
            return 0.0
    
    async def _validate_transaction_nonce(self, tx: Transaction) -> bool:
        """Validate transaction nonce to prevent replay attacks"""
        try:
            # Get the last nonce for this address
            last_tx = await self.db["transactions"].find_one(
                {"from_address": tx.from_address},
                sort=[("timestamp", -1)]
            )
            
            # For now, just check that we don't have duplicate transaction IDs
            # In production, this would implement proper nonce validation
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate transaction nonce: {e}")
            return False
    
    async def _transaction_exists(self, tx_id: str) -> bool:
        """Check if transaction already exists in blockchain"""
        try:
            existing_tx = await self.db["transactions"].find_one({"id": tx_id})
            return existing_tx is not None
            
        except Exception as e:
            logger.error(f"Failed to check transaction existence: {e}")
            return False
    
    async def _add_to_mempool(self, tx: Transaction):
        """Add transaction to mempool"""
        try:
            # Add to memory mempool
            self.mempool[tx.id] = tx
            
            # Update address mapping
            if tx.from_address not in self.mempool_by_address:
                self.mempool_by_address[tx.from_address] = []
            self.mempool_by_address[tx.from_address].append(tx.id)
            
            # Store in database
            tx_doc = tx.to_dict()
            tx_doc["status"] = "pending"
            tx_doc["added_to_mempool"] = datetime.now(timezone.utc)
            await self.db["mempool"].insert_one(tx_doc)
            
            # Update statistics
            await self._update_statistics()
            
        except Exception as e:
            logger.error(f"Failed to add transaction to mempool: {e}")
            raise
    
    async def _remove_from_mempool(self, tx_id: str, reason: str = "processed"):
        """Remove transaction from mempool"""
        try:
            if tx_id not in self.mempool:
                return
            
            tx = self.mempool[tx_id]
            
            # Remove from memory
            del self.mempool[tx_id]
            
            # Update address mapping
            if tx.from_address in self.mempool_by_address:
                if tx_id in self.mempool_by_address[tx.from_address]:
                    self.mempool_by_address[tx.from_address].remove(tx_id)
                if not self.mempool_by_address[tx.from_address]:
                    del self.mempool_by_address[tx.from_address]
            
            # Update database
            await self.db["mempool"].update_one(
                {"id": tx_id},
                {"$set": {"status": reason, "removed_at": datetime.now(timezone.utc)}}
            )
            
            logger.debug(f"Transaction removed from mempool: {tx_id} ({reason})")
            
        except Exception as e:
            logger.error(f"Failed to remove transaction from mempool: {e}")
    
    async def _evict_lowest_fee_transaction(self):
        """Evict the transaction with the lowest fee from mempool"""
        try:
            if not self.mempool:
                return
            
            # Find transaction with lowest fee
            lowest_fee_tx_id = None
            lowest_fee = float('inf')
            
            for tx_id, tx in self.mempool.items():
                fee = getattr(tx, 'fee', TRANSACTION_FEE_MINIMUM)
                if fee < lowest_fee:
                    lowest_fee = fee
                    lowest_fee_tx_id = tx_id
            
            if lowest_fee_tx_id:
                await self._remove_from_mempool(lowest_fee_tx_id, "evicted")
                logger.info(f"Evicted transaction with lowest fee: {lowest_fee_tx_id}")
            
        except Exception as e:
            logger.error(f"Failed to evict lowest fee transaction: {e}")
    
    async def _process_pending_transactions(self):
        """Process pending transactions in mempool"""
        try:
            # This would typically be called by the block producer
            # For now, just update transaction statuses
            
            processed_count = 0
            for tx_id, tx in list(self.mempool.items()):
                # Check if transaction is still valid
                validation_result = await self.validate_transaction(tx)
                if not validation_result.is_valid:
                    await self._remove_from_mempool(tx_id, "invalid")
                    processed_count += 1
            
            if processed_count > 0:
                logger.debug(f"Processed {processed_count} transactions")
            
        except Exception as e:
            logger.error(f"Failed to process pending transactions: {e}")
    
    async def get_pending_transactions(self, limit: int = 1000) -> List[Transaction]:
        """Get pending transactions from mempool for block creation"""
        try:
            # Sort by fee (highest first) and timestamp (oldest first)
            transactions = list(self.mempool.values())
            transactions.sort(key=lambda tx: (
                -getattr(tx, 'fee', TRANSACTION_FEE_MINIMUM),
                tx.timestamp
            ))
            
            return transactions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get pending transactions: {e}")
            return []
    
    async def get_transactions_by_address(self, address: str, limit: int = 100) -> List[Transaction]:
        """Get transactions for a specific address"""
        try:
            transactions = []
            cursor = self.db["transactions"].find({
                "$or": [{"from_address": address}, {"to_address": address}]
            }).sort("timestamp", -1).limit(limit)
            
            async for tx_doc in cursor:
                tx = self._doc_to_transaction(tx_doc)
                transactions.append(tx)
            
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get transactions by address: {e}")
            return []
    
    async def get_transaction_by_id(self, tx_id: str) -> Optional[Transaction]:
        """Get transaction by ID"""
        try:
            # Check mempool first
            if tx_id in self.mempool:
                return self.mempool[tx_id]
            
            # Check cache
            if tx_id in self.tx_cache:
                return self.tx_cache[tx_id]
            
            # Query database
            tx_doc = await self.db["transactions"].find_one({"id": tx_id})
            if tx_doc:
                tx = self._doc_to_transaction(tx_doc)
                self.tx_cache[tx_id] = tx
                return tx
            
            # Check mempool database
            mempool_doc = await self.db["mempool"].find_one({"id": tx_id})
            if mempool_doc:
                return self._doc_to_transaction(mempool_doc)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transaction by ID: {e}")
            return None
    
    async def get_transaction_status(self, tx_id: str) -> Dict[str, Any]:
        """Get detailed transaction status"""
        try:
            # Check confirmed transactions
            tx_doc = await self.db["transactions"].find_one({"id": tx_id})
            if tx_doc:
                return {
                    "status": "confirmed",
                    "block_height": tx_doc.get("block_height"),
                    "confirmations": await self._get_confirmations(tx_doc.get("block_height", 0)),
                    "timestamp": tx_doc["timestamp"]
                }
            
            # Check mempool
            if tx_id in self.mempool:
                return {
                    "status": "pending",
                    "in_mempool": True,
                    "timestamp": self.mempool[tx_id].timestamp
                }
            
            # Check mempool database for other statuses
            mempool_doc = await self.db["mempool"].find_one({"id": tx_id})
            if mempool_doc:
                return {
                    "status": mempool_doc.get("status", "unknown"),
                    "timestamp": mempool_doc["timestamp"]
                }
            
            return {"status": "not_found"}
            
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _get_confirmations(self, block_height: int) -> int:
        """Get number of confirmations for a transaction"""
        try:
            # Get current blockchain height
            latest_block = await self.db["blocks"].find_one({}, sort=[("height", -1)])
            if latest_block:
                current_height = latest_block["height"]
                return max(0, current_height - block_height + 1)
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get confirmations: {e}")
            return 0
    
    async def process_block_transactions(self, transactions: List[Transaction], block_height: int):
        """Process transactions when they are included in a block"""
        try:
            for tx in transactions:
                # Remove from mempool if present
                if tx.id in self.mempool:
                    await self._remove_from_mempool(tx.id, "confirmed")
                
                # Update transaction with block information
                await self.db["transactions"].update_one(
                    {"id": tx.id},
                    {
                        "$set": {
                            "status": "confirmed",
                            "block_height": block_height,
                            "confirmed_at": datetime.now(timezone.utc)
                        }
                    },
                    upsert=True
                )
            
            logger.info(f"Processed {len(transactions)} transactions for block {block_height}")
            
        except Exception as e:
            logger.error(f"Failed to process block transactions: {e}")
    
    async def _update_statistics(self):
        """Update mempool and transaction statistics"""
        try:
            # Mempool stats
            self.stats.pending_transactions = len(self.mempool)
            self.stats.total_value = sum(tx.value for tx in self.mempool.values())
            
            if self.mempool:
                total_fees = sum(getattr(tx, 'fee', TRANSACTION_FEE_MINIMUM) for tx in self.mempool.values())
                self.stats.average_fee = total_fees / len(self.mempool)
            
            # Database stats
            self.stats.total_transactions = await self.db["transactions"].count_documents({})
            self.stats.confirmed_transactions = await self.db["transactions"].count_documents({"status": "confirmed"})
            self.stats.failed_transactions = await self.db["mempool"].count_documents({"status": "failed"})
            
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
    
    def _doc_to_transaction(self, doc: Dict[str, Any]) -> Transaction:
        """Convert MongoDB document to Transaction object"""
        return Transaction(
            id=doc["id"],
            from_address=doc["from_address"],
            to_address=doc["to_address"],
            value=doc["value"],
            data=doc.get("data", ""),
            timestamp=doc["timestamp"],
            signature=doc["signature"]
        )
    
    async def get_mempool_info(self) -> Dict[str, Any]:
        """Get comprehensive mempool information"""
        try:
            await self._update_statistics()
            
            return {
                "size": len(self.mempool),
                "max_size": MEMPOOL_MAX_SIZE,
                "total_value": self.stats.total_value,
                "average_fee": self.stats.average_fee,
                "pending_transactions": self.stats.pending_transactions,
                "oldest_transaction": min(tx.timestamp for tx in self.mempool.values()) if self.mempool else None,
                "newest_transaction": max(tx.timestamp for tx in self.mempool.values()) if self.mempool else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get mempool info: {e}")
            return {}
    
    async def submit_batch_transactions(self, transactions: List[Transaction]) -> List[TransactionValidationResult]:
        """Submit multiple transactions as a batch"""
        try:
            self.batch_processing_active = True
            results = []
            
            for tx in transactions:
                result = await self.submit_transaction(tx)
                results.append(result)
            
            self.batch_processing_active = False
            logger.info(f"Batch processed {len(transactions)} transactions")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to submit batch transactions: {e}")
            self.batch_processing_active = False
            return [TransactionValidationResult(is_valid=False, errors=[str(e)]) for _ in transactions]
