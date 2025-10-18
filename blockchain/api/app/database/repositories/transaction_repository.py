"""
Transaction Repository
Handles database operations for blockchain transactions.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from ..connection import DatabaseConnection
from ...models.transaction import Transaction, TransactionStatus

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Repository for transaction data access."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        self.collection_name = "transactions"
        
    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the transactions collection."""
        return self.db_connection.get_collection(self.collection_name)
        
    async def create_transaction(self, transaction: Transaction) -> str:
        """Create a new transaction in the database."""
        try:
            # Convert transaction to dictionary
            tx_dict = transaction.dict()
            tx_dict["_id"] = transaction.hash  # Use hash as MongoDB _id
            
            # Insert transaction
            await self.collection.insert_one(tx_dict)
            
            logger.info(f"Created transaction {transaction.hash}")
            return transaction.hash
            
        except DuplicateKeyError:
            logger.warning(f"Transaction {transaction.hash} already exists")
            raise ValueError(f"Transaction with hash {transaction.hash} already exists")
        except Exception as e:
            logger.error(f"Error creating transaction {transaction.hash}: {e}")
            raise
            
    async def get_transaction_by_hash(self, tx_hash: str) -> Optional[Transaction]:
        """Get a transaction by its hash."""
        try:
            tx_dict = await self.collection.find_one({"_id": tx_hash})
            
            if not tx_dict:
                return None
                
            # Remove MongoDB _id field and convert to Transaction
            tx_dict.pop("_id", None)
            return Transaction(**tx_dict)
            
        except Exception as e:
            logger.error(f"Error getting transaction by hash {tx_hash}: {e}")
            return None
            
    async def get_transactions_by_block(self, block_hash: str) -> List[Transaction]:
        """Get all transactions in a specific block."""
        try:
            cursor = self.collection.find({"block_hash": block_hash}).sort("transaction_index", ASCENDING)
            
            transactions = []
            async for tx_dict in cursor:
                # Remove MongoDB _id field and convert to Transaction
                tx_dict.pop("_id", None)
                transactions.append(Transaction(**tx_dict))
                
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions for block {block_hash}: {e}")
            return []
            
    async def get_transactions_by_address(
        self,
        address: str,
        offset: int = 0,
        limit: int = 20,
        order_by: str = "timestamp",
        order_direction: str = "desc"
    ) -> List[Transaction]:
        """Get transactions involving a specific address."""
        try:
            # Determine sort order
            sort_order = DESCENDING if order_direction.lower() == "desc" else ASCENDING
            
            # Query transactions where address is sender or recipient
            cursor = self.collection.find({
                "$or": [
                    {"from_address": address},
                    {"to_address": address}
                ]
            }).sort(order_by, sort_order).skip(offset).limit(limit)
            
            transactions = []
            async for tx_dict in cursor:
                # Remove MongoDB _id field and convert to Transaction
                tx_dict.pop("_id", None)
                transactions.append(Transaction(**tx_dict))
                
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions for address {address}: {e}")
            return []
            
    async def get_transaction_count_by_address(self, address: str) -> int:
        """Get count of transactions involving a specific address."""
        try:
            return await self.collection.count_documents({
                "$or": [
                    {"from_address": address},
                    {"to_address": address}
                ]
            })
        except Exception as e:
            logger.error(f"Error getting transaction count for address {address}: {e}")
            return 0
            
    async def get_transactions_by_status(
        self,
        status: TransactionStatus,
        limit: int = 100
    ) -> List[Transaction]:
        """Get transactions by status."""
        try:
            cursor = self.collection.find({"status": status.value}).limit(limit)
            
            transactions = []
            async for tx_dict in cursor:
                # Remove MongoDB _id field and convert to Transaction
                tx_dict.pop("_id", None)
                transactions.append(Transaction(**tx_dict))
                
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions by status {status}: {e}")
            return []
            
    async def get_transaction_count_by_status(self, status: TransactionStatus) -> int:
        """Get count of transactions by status."""
        try:
            return await self.collection.count_documents({"status": status.value})
        except Exception as e:
            logger.error(f"Error getting transaction count for status {status}: {e}")
            return 0
            
    async def update_transaction_status(
        self,
        tx_hash: str,
        status: TransactionStatus
    ) -> bool:
        """Update transaction status."""
        try:
            result = await self.collection.update_one(
                {"_id": tx_hash},
                {
                    "$set": {
                        "status": status.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated transaction {tx_hash} status to {status.value}")
                return True
            else:
                logger.warning(f"Transaction {tx_hash} not found for status update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating transaction {tx_hash} status: {e}")
            return False
            
    async def update_transaction_block_info(
        self,
        tx_hash: str,
        block_hash: str,
        block_height: int,
        transaction_index: int
    ) -> bool:
        """Update transaction with block information."""
        try:
            result = await self.collection.update_one(
                {"_id": tx_hash},
                {
                    "$set": {
                        "block_hash": block_hash,
                        "block_height": block_height,
                        "transaction_index": transaction_index,
                        "status": TransactionStatus.CONFIRMED.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated transaction {tx_hash} with block info")
                return True
            else:
                logger.warning(f"Transaction {tx_hash} not found for block info update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating transaction {tx_hash} block info: {e}")
            return False
            
    async def search_transactions_by_hash_prefix(
        self,
        hash_prefix: str,
        limit: int = 10
    ) -> List[Transaction]:
        """Search transactions by hash prefix."""
        try:
            # Use regex for prefix search
            cursor = self.collection.find({
                "_id": {"$regex": f"^{hash_prefix}", "$options": "i"}
            }).limit(limit)
            
            transactions = []
            async for tx_dict in cursor:
                # Remove MongoDB _id field and convert to Transaction
                tx_dict.pop("_id", None)
                transactions.append(Transaction(**tx_dict))
                
            return transactions
            
        except Exception as e:
            logger.error(f"Error searching transactions by hash prefix {hash_prefix}: {e}")
            return []
            
    async def search_transactions_by_address(
        self,
        address: str,
        limit: int = 10
    ) -> List[Transaction]:
        """Search transactions by address (partial match)."""
        try:
            # Use regex for partial address search
            cursor = self.collection.find({
                "$or": [
                    {"from_address": {"$regex": address, "$options": "i"}},
                    {"to_address": {"$regex": address, "$options": "i"}}
                ]
            }).limit(limit)
            
            transactions = []
            async for tx_dict in cursor:
                # Remove MongoDB _id field and convert to Transaction
                tx_dict.pop("_id", None)
                transactions.append(Transaction(**tx_dict))
                
            return transactions
            
        except Exception as e:
            logger.error(f"Error searching transactions by address {address}: {e}")
            return []
            
    async def get_total_transactions(self) -> int:
        """Get total number of transactions."""
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error getting total transactions count: {e}")
            return 0
            
    async def get_average_transaction_stats(self) -> Dict[str, float]:
        """Get average transaction statistics."""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "avg_fee": {"$avg": "$fee"},
                        "avg_amount": {"$avg": "$amount"},
                        "avg_gas_used": {"$avg": "$gas_used"}
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            
            if result:
                return {
                    "avg_fee": result[0].get("avg_fee", 0),
                    "avg_amount": result[0].get("avg_amount", 0),
                    "avg_gas_used": result[0].get("avg_gas_used", 0)
                }
            return {"avg_fee": 0, "avg_amount": 0, "avg_gas_used": 0}
            
        except Exception as e:
            logger.error(f"Error getting average transaction stats: {e}")
            return {"avg_fee": 0, "avg_amount": 0, "avg_gas_used": 0}
            
    async def get_transactions_by_timestamp_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Transaction]:
        """Get transactions within a timestamp range."""
        try:
            cursor = self.collection.find({
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("timestamp", ASCENDING)
            
            transactions = []
            async for tx_dict in cursor:
                # Remove MongoDB _id field and convert to Transaction
                tx_dict.pop("_id", None)
                transactions.append(Transaction(**tx_dict))
                
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions by timestamp range: {e}")
            return []
            
    async def get_failed_transactions(self, limit: int = 100) -> List[Transaction]:
        """Get failed transactions."""
        try:
            cursor = self.collection.find({
                "status": {"$in": [TransactionStatus.FAILED.value, TransactionStatus.REJECTED.value]}
            }).sort("timestamp", DESCENDING).limit(limit)
            
            transactions = []
            async for tx_dict in cursor:
                # Remove MongoDB _id field and convert to Transaction
                tx_dict.pop("_id", None)
                transactions.append(Transaction(**tx_dict))
                
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting failed transactions: {e}")
            return []
            
    async def delete_transaction(self, tx_hash: str) -> bool:
        """Delete a transaction (use with caution)."""
        try:
            result = await self.collection.delete_one({"_id": tx_hash})
            
            if result.deleted_count > 0:
                logger.warning(f"Deleted transaction {tx_hash}")
                return True
            else:
                logger.warning(f"Transaction {tx_hash} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting transaction {tx_hash}: {e}")
            return False
            
    async def get_transaction_volume_by_period(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get transaction volume statistics for a time period."""
        try:
            pipeline = [
                {
                    "$match": {
                        "timestamp": {
                            "$gte": start_time,
                            "$lte": end_time
                        }
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_transactions": {"$sum": 1},
                        "total_volume": {"$sum": "$amount"},
                        "total_fees": {"$sum": "$fee"},
                        "avg_amount": {"$avg": "$amount"},
                        "avg_fee": {"$avg": "$fee"}
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            
            if result:
                return result[0]
            return {
                "total_transactions": 0,
                "total_volume": 0,
                "total_fees": 0,
                "avg_amount": 0,
                "avg_fee": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction volume stats: {e}")
            return {
                "total_transactions": 0,
                "total_volume": 0,
                "total_fees": 0,
                "avg_amount": 0,
                "avg_fee": 0
            }
            
    async def health_check(self) -> bool:
        """Perform health check on transaction repository."""
        try:
            # Test basic operations
            await self.collection.find_one({})
            await self.get_total_transactions()
            return True
        except Exception as e:
            logger.error(f"Transaction repository health check failed: {e}")
            return False
            
    async def create_indexes(self):
        """Create additional indexes for performance."""
        try:
            # Compound indexes for common queries
            await self.collection.create_index([
                ("from_address", ASCENDING),
                ("timestamp", DESCENDING)
            ])
            
            await self.collection.create_index([
                ("to_address", ASCENDING),
                ("timestamp", DESCENDING)
            ])
            
            await self.collection.create_index([
                ("status", ASCENDING),
                ("timestamp", DESCENDING)
            ])
            
            await self.collection.create_index([
                ("block_hash", ASCENDING),
                ("transaction_index", ASCENDING)
            ])
            
            # Index for amount range queries
            await self.collection.create_index("amount")
            
            logger.info("Created additional transaction indexes")
            
        except Exception as e:
            logger.error(f"Error creating transaction indexes: {e}")
            raise
