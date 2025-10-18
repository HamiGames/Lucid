"""
MongoDB Service for Lucid Database Infrastructure
Provides MongoDB operations, connection management, and database administration.

This service implements the MongoDB operations layer for the Lucid blockchain system,
handling database connections, CRUD operations, replica set management, and sharding.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import MongoClient
from pymongo.errors import (
    ConnectionFailure, 
    ServerSelectionTimeoutError, 
    OperationFailure,
    DuplicateKeyError,
    BulkWriteError
)
from bson import ObjectId
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDBService:
    """
    MongoDB Service for Lucid Database Infrastructure
    
    Provides comprehensive MongoDB operations including:
    - Connection management and pooling
    - CRUD operations with validation
    - Replica set management
    - Sharding operations
    - Index management
    - Health monitoring
    """
    
    def __init__(self, uri: str, database_name: str = "lucid"):
        """
        Initialize MongoDB service
        
        Args:
            uri: MongoDB connection URI
            database_name: Target database name
        """
        self.uri = uri
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.sync_client: Optional[MongoClient] = None
        self._connection_pool_size = 100
        self._max_idle_time_ms = 30000
        
    async def connect(self) -> bool:
        """
        Establish connection to MongoDB
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Async client for regular operations
            self.client = AsyncIOMotorClient(
                self.uri,
                maxPoolSize=self._connection_pool_size,
                maxIdleTimeMS=self._max_idle_time_ms,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
                retryWrites=True,
                w="majority",
                readPreference="primaryPreferred"
            )
            
            # Sync client for admin operations
            self.sync_client = MongoClient(self.uri)
            
            self.db = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB: {self.database_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    async def disconnect(self):
        """Close MongoDB connections"""
        if self.client:
            self.client.close()
        if self.sync_client:
            self.sync_client.close()
        logger.info("MongoDB connections closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Dict containing health status and metrics
        """
        try:
            if not self.client:
                return {"status": "unhealthy", "error": "No connection"}
            
            # Test basic connectivity
            await self.client.admin.command('ping')
            
            # Get server status
            server_status = await self.client.admin.command('serverStatus')
            
            # Get replica set status if applicable
            replica_status = None
            try:
                replica_status = await self.client.admin.command('replSetGetStatus')
            except OperationFailure:
                # Not a replica set
                pass
            
            # Get database stats
            db_stats = await self.db.command('dbStats')
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "server_info": {
                    "version": server_status.get("version"),
                    "uptime": server_status.get("uptime"),
                    "connections": server_status.get("connections", {})
                },
                "database_stats": {
                    "collections": db_stats.get("collections"),
                    "dataSize": db_stats.get("dataSize"),
                    "indexSize": db_stats.get("indexSize"),
                    "storageSize": db_stats.get("storageSize")
                },
                "replica_set": replica_status.get("set") if replica_status else None
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def create_indexes(self) -> bool:
        """
        Create all required indexes for Lucid collections
        
        Returns:
            bool: True if successful
        """
        try:
            # Users collection indexes
            await self.db.users.create_index([("user_id", 1)], unique=True)
            await self.db.users.create_index([("email", 1)], unique=True)
            await self.db.users.create_index([("tron_address", 1)], unique=True, sparse=True)
            await self.db.users.create_index([("roles", 1)])
            await self.db.users.create_index([("status", 1)])
            await self.db.users.create_index([("created_at", -1)])
            
            # Sessions collection indexes
            await self.db.sessions.create_index([("_id", 1)], unique=True)
            await self.db.sessions.create_index([("owner_address", 1)])
            await self.db.sessions.create_index([("status", 1)])
            await self.db.sessions.create_index([("started_at", -1)])
            await self.db.sessions.create_index([("completed_at", -1)], sparse=True)
            await self.db.sessions.create_index([("merkle_root", 1)], unique=True, sparse=True)
            await self.db.sessions.create_index([("anchor_txid", 1)], unique=True, sparse=True)
            
            # Blocks collection indexes
            await self.db.blocks.create_index([("block_height", 1)], unique=True)
            await self.db.blocks.create_index([("block_hash", 1)], unique=True)
            await self.db.blocks.create_index([("previous_hash", 1)])
            await self.db.blocks.create_index([("timestamp", -1)])
            await self.db.blocks.create_index([("miner_id", 1)], sparse=True)
            
            # Transactions collection indexes
            await self.db.transactions.create_index([("tx_id", 1)], unique=True)
            await self.db.transactions.create_index([("tx_type", 1)])
            await self.db.transactions.create_index([("sender", 1)])
            await self.db.transactions.create_index([("status", 1)])
            await self.db.transactions.create_index([("timestamp", -1)])
            await self.db.transactions.create_index([("block_height", 1)], sparse=True)
            
            # Trust policies collection indexes
            await self.db.trust_policies.create_index([("policy_id", 1)], unique=True)
            await self.db.trust_policies.create_index([("creator_id", 1)])
            await self.db.trust_policies.create_index([("status", 1)])
            await self.db.trust_policies.create_index([("created_at", -1)])
            
            # Authentication collection indexes
            await self.db.authentication.create_index([("user_id", 1)], unique=True)
            await self.db.authentication.create_index([("session_token", 1)], unique=True, sparse=True)
            await self.db.authentication.create_index([("expires_at", 1)])
            await self.db.authentication.create_index([("last_activity", -1)])
            
            # Encryption keys collection indexes
            await self.db.encryption_keys.create_index([("_id", 1)], unique=True)
            await self.db.encryption_keys.create_index([("session_id", 1)])
            await self.db.encryption_keys.create_index([("key_id", 1)], unique=True)
            await self.db.encryption_keys.create_index([("created_at", -1)])
            await self.db.encryption_keys.create_index([("expires_at", 1)])
            
            logger.info("All indexes created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dict containing collection statistics
        """
        try:
            stats = await self.db.command("collStats", collection_name)
            return {
                "collection": collection_name,
                "count": stats.get("count", 0),
                "size": stats.get("size", 0),
                "avgObjSize": stats.get("avgObjSize", 0),
                "storageSize": stats.get("storageSize", 0),
                "totalIndexSize": stats.get("totalIndexSize", 0),
                "indexSizes": stats.get("indexSizes", {}),
                "ok": stats.get("ok", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get stats for collection {collection_name}: {e}")
            return {"error": str(e)}
    
    async def list_collections(self) -> List[str]:
        """
        List all collections in the database
        
        Returns:
            List of collection names
        """
        try:
            collections = await self.db.list_collection_names()
            return collections
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    async def create_collection_with_validation(self, collection_name: str, validator: Dict) -> bool:
        """
        Create a collection with JSON schema validation
        
        Args:
            collection_name: Name of the collection to create
            validator: JSON schema validator
            
        Returns:
            bool: True if successful
        """
        try:
            await self.db.create_collection(
                collection_name,
                validator=validator,
                validationLevel="strict",
                validationAction="error"
            )
            logger.info(f"Collection {collection_name} created with validation")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False
    
    async def insert_document(self, collection_name: str, document: Dict) -> Optional[str]:
        """
        Insert a document into a collection
        
        Args:
            collection_name: Target collection
            document: Document to insert
            
        Returns:
            Inserted document ID or None if failed
        """
        try:
            collection = self.db[collection_name]
            result = await collection.insert_one(document)
            logger.debug(f"Document inserted into {collection_name}: {result.inserted_id}")
            return str(result.inserted_id)
        except DuplicateKeyError as e:
            logger.warning(f"Duplicate key error in {collection_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to insert document into {collection_name}: {e}")
            return None
    
    async def find_documents(self, collection_name: str, filter_dict: Dict, 
                           limit: int = 100, skip: int = 0, sort: List = None) -> List[Dict]:
        """
        Find documents in a collection
        
        Args:
            collection_name: Target collection
            filter_dict: Query filter
            limit: Maximum number of documents to return
            skip: Number of documents to skip
            sort: Sort specification
            
        Returns:
            List of matching documents
        """
        try:
            collection = self.db[collection_name]
            cursor = collection.find(filter_dict).limit(limit).skip(skip)
            
            if sort:
                cursor = cursor.sort(sort)
            
            documents = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string for JSON serialization
            for doc in documents:
                if '_id' in doc and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
            
            return documents
        except Exception as e:
            logger.error(f"Failed to find documents in {collection_name}: {e}")
            return []
    
    async def update_document(self, collection_name: str, filter_dict: Dict, 
                            update_dict: Dict, upsert: bool = False) -> bool:
        """
        Update a document in a collection
        
        Args:
            collection_name: Target collection
            filter_dict: Query filter
            update_dict: Update operations
            upsert: Whether to insert if document doesn't exist
            
        Returns:
            bool: True if successful
        """
        try:
            collection = self.db[collection_name]
            result = await collection.update_one(filter_dict, update_dict, upsert=upsert)
            
            if result.modified_count > 0 or (upsert and result.upserted_id):
                logger.debug(f"Document updated in {collection_name}")
                return True
            else:
                logger.warning(f"No document updated in {collection_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update document in {collection_name}: {e}")
            return False
    
    async def delete_document(self, collection_name: str, filter_dict: Dict) -> bool:
        """
        Delete a document from a collection
        
        Args:
            collection_name: Target collection
            filter_dict: Query filter
            
        Returns:
            bool: True if successful
        """
        try:
            collection = self.db[collection_name]
            result = await collection.delete_one(filter_dict)
            
            if result.deleted_count > 0:
                logger.debug(f"Document deleted from {collection_name}")
                return True
            else:
                logger.warning(f"No document deleted from {collection_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete document from {collection_name}: {e}")
            return False
    
    async def aggregate(self, collection_name: str, pipeline: List[Dict]) -> List[Dict]:
        """
        Run aggregation pipeline on a collection
        
        Args:
            collection_name: Target collection
            pipeline: Aggregation pipeline
            
        Returns:
            List of aggregation results
        """
        try:
            collection = self.db[collection_name]
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            # Convert ObjectId to string for JSON serialization
            for result in results:
                if '_id' in result and isinstance(result['_id'], ObjectId):
                    result['_id'] = str(result['_id'])
            
            return results
        except Exception as e:
            logger.error(f"Failed to run aggregation on {collection_name}: {e}")
            return []
    
    async def get_replica_set_status(self) -> Optional[Dict]:
        """
        Get replica set status
        
        Returns:
            Replica set status or None if not a replica set
        """
        try:
            status = await self.client.admin.command('replSetGetStatus')
            return status
        except OperationFailure:
            logger.info("Not running as replica set")
            return None
        except Exception as e:
            logger.error(f"Failed to get replica set status: {e}")
            return None
    
    async def enable_sharding(self, database_name: str = None) -> bool:
        """
        Enable sharding for the database
        
        Args:
            database_name: Database name (uses default if None)
            
        Returns:
            bool: True if successful
        """
        try:
            db_name = database_name or self.database_name
            await self.client.admin.command('enableSharding', db_name)
            logger.info(f"Sharding enabled for database: {db_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable sharding: {e}")
            return False
    
    async def shard_collection(self, collection_name: str, shard_key: Dict) -> bool:
        """
        Shard a collection
        
        Args:
            collection_name: Collection to shard
            shard_key: Shard key specification
            
        Returns:
            bool: True if successful
        """
        try:
            full_collection_name = f"{self.database_name}.{collection_name}"
            await self.client.admin.command('shardCollection', full_collection_name, key=shard_key)
            logger.info(f"Collection {collection_name} sharded with key: {shard_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to shard collection {collection_name}: {e}")
            return False
    
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """
        Get a collection object for direct operations
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            AsyncIOMotorCollection object
        """
        return self.db[collection_name]
    
    async def cleanup_expired_documents(self, collection_name: str, 
                                      expire_field: str, expire_hours: int = 24) -> int:
        """
        Clean up expired documents from a collection
        
        Args:
            collection_name: Target collection
            expire_field: Field containing expiration timestamp
            expire_hours: Hours after which documents expire
            
        Returns:
            Number of documents deleted
        """
        try:
            expire_time = datetime.utcnow() - timedelta(hours=expire_hours)
            collection = self.db[collection_name]
            
            result = await collection.delete_many({
                expire_field: {"$lt": expire_time}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} expired documents from {collection_name}")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired documents from {collection_name}: {e}")
            return 0

# Global MongoDB service instance
mongodb_service = None

async def get_mongodb_service(uri: str = None, database_name: str = "lucid") -> MongoDBService:
    """
    Get or create MongoDB service instance
    
    Args:
        uri: MongoDB connection URI
        database_name: Database name
        
    Returns:
        MongoDBService instance
    """
    global mongodb_service
    
    if mongodb_service is None:
        if uri is None:
            raise ValueError("MongoDB URI is required for first initialization")
        
        mongodb_service = MongoDBService(uri, database_name)
        await mongodb_service.connect()
    
    return mongodb_service

async def close_mongodb_service():
    """Close the global MongoDB service"""
    global mongodb_service
    if mongodb_service:
        await mongodb_service.disconnect()
        mongodb_service = None
