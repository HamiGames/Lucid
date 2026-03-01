"""
Wallet Repository - MongoDB persistence layer for wallet management
Follows Lucid architecture patterns for database repositories
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId

logger = logging.getLogger(__name__)


class WalletRepository:
    """Repository for wallet management operations with MongoDB persistence"""
    
    def __init__(self, mongo_url: str, database_name: str = "lucid_payments"):
        """Initialize wallet repository"""
        self.mongo_url = mongo_url
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.wallets_collection: Optional[AsyncIOMotorCollection] = None
        self.transactions_collection: Optional[AsyncIOMotorCollection] = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            # Get connection pool settings from environment
            server_selection_timeout_ms = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"))
            connect_timeout_ms = int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "10000"))
            socket_timeout_ms = int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "20000"))
            max_pool_size = int(os.getenv("MONGODB_MAX_POOL_SIZE", "50"))
            min_pool_size = int(os.getenv("MONGODB_MIN_POOL_SIZE", "5"))
            max_idle_time_ms = int(os.getenv("MONGODB_MAX_IDLE_TIME_MS", "30000"))
            retry_writes = os.getenv("MONGODB_RETRY_WRITES", "true").lower() in ("true", "1", "yes")
            retry_reads = os.getenv("MONGODB_RETRY_READS", "true").lower() in ("true", "1", "yes")
            
            self.client = AsyncIOMotorClient(
                self.mongo_url,
                serverSelectionTimeoutMS=server_selection_timeout_ms,
                connectTimeoutMS=connect_timeout_ms,
                socketTimeoutMS=socket_timeout_ms,
                maxPoolSize=max_pool_size,
                minPoolSize=min_pool_size,
                maxIdleTimeMS=max_idle_time_ms,
                retryWrites=retry_writes,
                retryReads=retry_reads
            )
            
            self.db = self.client[self.database_name]
            self.wallets_collection = self.db["wallets"]
            self.transactions_collection = self.db["wallet_transactions"]
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Create indexes
            await self._create_indexes()
            
            logger.info(f"Connected to MongoDB database: {self.database_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes for efficient queries"""
        try:
            # Wallet indexes
            await self.wallets_collection.create_index("wallet_id", unique=True)
            await self.wallets_collection.create_index("address", unique=True)
            await self.wallets_collection.create_index("user_id")
            await self.wallets_collection.create_index("status")
            await self.wallets_collection.create_index("wallet_type")
            await self.wallets_collection.create_index("created_at")
            await self.wallets_collection.create_index([("user_id", 1), ("status", 1)])
            await self.wallets_collection.create_index([("created_at", -1)])
            
            # Transaction indexes
            await self.transactions_collection.create_index("transaction_id", unique=True)
            await self.transactions_collection.create_index("wallet_id")
            await self.transactions_collection.create_index("from_address")
            await self.transactions_collection.create_index("to_address")
            await self.transactions_collection.create_index("status")
            await self.transactions_collection.create_index("created_at")
            await self.transactions_collection.create_index([("wallet_id", 1), ("created_at", -1)])
            await self.transactions_collection.create_index([("from_address", 1), ("status", 1)])
            
            logger.info("Wallet repository indexes created")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def create_wallet(self, wallet_data: Dict[str, Any]) -> str:
        """Create a new wallet"""
        try:
            wallet_data["created_at"] = datetime.now(timezone.utc)
            wallet_data["updated_at"] = datetime.now(timezone.utc)
            result = await self.wallets_collection.insert_one(wallet_data)
            logger.info(f"Created wallet: {wallet_data.get('wallet_id')}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create wallet: {e}")
            raise
    
    async def get_wallet(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet by ID"""
        try:
            wallet = await self.wallets_collection.find_one({"wallet_id": wallet_id})
            if wallet and "_id" in wallet:
                wallet["_id"] = str(wallet["_id"])
            return wallet
        except Exception as e:
            logger.error(f"Failed to get wallet {wallet_id}: {e}")
            raise
    
    async def get_wallet_by_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Get wallet by address"""
        try:
            wallet = await self.wallets_collection.find_one({"address": address})
            if wallet and "_id" in wallet:
                wallet["_id"] = str(wallet["_id"])
            return wallet
        except Exception as e:
            logger.error(f"Failed to get wallet by address {address}: {e}")
            raise
    
    async def update_wallet(self, wallet_id: str, update_data: Dict[str, Any]) -> bool:
        """Update wallet"""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = await self.wallets_collection.update_one(
                {"wallet_id": wallet_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update wallet {wallet_id}: {e}")
            raise
    
    async def delete_wallet(self, wallet_id: str) -> bool:
        """Delete wallet (soft delete by setting status)"""
        try:
            result = await self.wallets_collection.update_one(
                {"wallet_id": wallet_id},
                {"$set": {"status": "deleted", "deleted_at": datetime.now(timezone.utc)}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to delete wallet {wallet_id}: {e}")
            raise
    
    async def list_wallets(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        wallet_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List wallets with filters"""
        try:
            query = {}
            if user_id:
                query["user_id"] = user_id
            if status:
                query["status"] = status
            if wallet_type:
                query["wallet_type"] = wallet_type
            
            cursor = self.wallets_collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
            wallets = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string
            for wallet in wallets:
                if "_id" in wallet:
                    wallet["_id"] = str(wallet["_id"])
            
            return wallets
        except Exception as e:
            logger.error(f"Failed to list wallets: {e}")
            raise
    
    async def count_wallets(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """Count wallets matching criteria"""
        try:
            query = {}
            if user_id:
                query["user_id"] = user_id
            if status:
                query["status"] = status
            return await self.wallets_collection.count_documents(query)
        except Exception as e:
            logger.error(f"Failed to count wallets: {e}")
            raise
    
    async def create_transaction(self, transaction_data: Dict[str, Any]) -> str:
        """Create a transaction record"""
        try:
            transaction_data["created_at"] = datetime.now(timezone.utc)
            result = await self.transactions_collection.insert_one(transaction_data)
            logger.info(f"Created transaction: {transaction_data.get('transaction_id')}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create transaction: {e}")
            raise
    
    async def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction by ID"""
        try:
            transaction = await self.transactions_collection.find_one({"transaction_id": transaction_id})
            if transaction and "_id" in transaction:
                transaction["_id"] = str(transaction["_id"])
            return transaction
        except Exception as e:
            logger.error(f"Failed to get transaction {transaction_id}: {e}")
            raise
    
    async def list_transactions(
        self,
        wallet_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List transactions with filters"""
        try:
            query = {}
            if wallet_id:
                query["wallet_id"] = wallet_id
            if status:
                query["status"] = status
            
            cursor = self.transactions_collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
            transactions = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string
            for transaction in transactions:
                if "_id" in transaction:
                    transaction["_id"] = str(transaction["_id"])
            
            return transactions
        except Exception as e:
            logger.error(f"Failed to list transactions: {e}")
            raise
    
    async def update_transaction(self, transaction_id: str, update_data: Dict[str, Any]) -> bool:
        """Update transaction"""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            result = await self.transactions_collection.update_one(
                {"transaction_id": transaction_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update transaction {transaction_id}: {e}")
            raise

