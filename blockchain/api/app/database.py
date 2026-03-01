"""
Database Module

This module contains database connection and operation utilities
for the Blockchain API. Handles MongoDB connections and common operations.
"""

import logging
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import asyncio

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection manager for MongoDB."""
    
    def __init__(self, database_url: str, database_name: str):
        self.database_url = database_url
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> bool:
        """Connect to MongoDB database."""
        try:
            self.client = AsyncIOMotorClient(self.database_url)
            self.database = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB database: {self.database_name}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MongoDB database."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if not self.client:
                return False
            
            await self.client.admin.command('ping')
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_collection(self, collection_name: str):
        """Get a collection from the database."""
        if not self.database:
            raise RuntimeError("Database not connected")
        return self.database[collection_name]

# Global database manager instance
db_manager: Optional[DatabaseManager] = None

async def init_database(database_url: str, database_name: str) -> bool:
    """Initialize database connection."""
    global db_manager
    
    db_manager = DatabaseManager(database_url, database_name)
    return await db_manager.connect()

async def close_database():
    """Close database connection."""
    global db_manager
    
    if db_manager:
        await db_manager.disconnect()
        db_manager = None

def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    if not db_manager or not db_manager.database:
        raise RuntimeError("Database not initialized")
    return db_manager.database

def get_collection(collection_name: str):
    """Get a collection from the database."""
    return db_manager.get_collection(collection_name)

# Collection names
class Collections:
    """Database collection names."""
    BLOCKS = "blocks"
    TRANSACTIONS = "transactions"
    SESSION_ANCHORINGS = "session_anchorings"
    CONSENSUS_VOTES = "consensus_votes"
    MERKLE_TREES = "merkle_trees"
    NETWORK_PEERS = "network_peers"
    SYSTEM_METRICS = "system_metrics"

# Database operations
class DatabaseOperations:
    """Common database operations."""
    
    @staticmethod
    async def insert_document(collection_name: str, document: Dict[str, Any]) -> str:
        """Insert a document into a collection."""
        collection = get_collection(collection_name)
        result = await collection.insert_one(document)
        return str(result.inserted_id)
    
    @staticmethod
    async def find_document(
        collection_name: str,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Find a single document in a collection."""
        collection = get_collection(collection_name)
        return await collection.find_one(query, projection)
    
    @staticmethod
    async def find_documents(
        collection_name: str,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        sort: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple documents in a collection."""
        collection = get_collection(collection_name)
        cursor = collection.find(query, projection)
        
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        
        return await cursor.to_list(length=limit)
    
    @staticmethod
    async def update_document(
        collection_name: str,
        query: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False
    ) -> bool:
        """Update a document in a collection."""
        collection = get_collection(collection_name)
        result = await collection.update_one(query, update, upsert=upsert)
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    async def delete_document(collection_name: str, query: Dict[str, Any]) -> bool:
        """Delete a document from a collection."""
        collection = get_collection(collection_name)
        result = await collection.delete_one(query)
        return result.deleted_count > 0
    
    @staticmethod
    async def count_documents(collection_name: str, query: Dict[str, Any]) -> int:
        """Count documents in a collection."""
        collection = get_collection(collection_name)
        return await collection.count_documents(query)
    
    @staticmethod
    async def create_index(
        collection_name: str,
        index_spec: List[tuple],
        unique: bool = False
    ) -> str:
        """Create an index on a collection."""
        collection = get_collection(collection_name)
        return await collection.create_index(index_spec, unique=unique)
    
    @staticmethod
    async def aggregate(
        collection_name: str,
        pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Perform aggregation on a collection."""
        collection = get_collection(collection_name)
        cursor = collection.aggregate(pipeline)
        return await cursor.to_list(length=None)

# Database initialization
async def setup_database_indexes():
    """Set up database indexes for optimal performance."""
    try:
        # Blocks collection indexes
        await DatabaseOperations.create_index(
            Collections.BLOCKS,
            [("height", 1)],
            unique=True
        )
        await DatabaseOperations.create_index(
            Collections.BLOCKS,
            [("hash", 1)],
            unique=True
        )
        await DatabaseOperations.create_index(
            Collections.BLOCKS,
            [("timestamp", -1)]
        )
        
        # Transactions collection indexes
        await DatabaseOperations.create_index(
            Collections.TRANSACTIONS,
            [("tx_id", 1)],
            unique=True
        )
        await DatabaseOperations.create_index(
            Collections.TRANSACTIONS,
            [("block_height", 1)]
        )
        await DatabaseOperations.create_index(
            Collections.TRANSACTIONS,
            [("status", 1)]
        )
        await DatabaseOperations.create_index(
            Collections.TRANSACTIONS,
            [("timestamp", -1)]
        )
        
        # Session anchorings collection indexes
        await DatabaseOperations.create_index(
            Collections.SESSION_ANCHORINGS,
            [("session_id", 1)],
            unique=True
        )
        await DatabaseOperations.create_index(
            Collections.SESSION_ANCHORINGS,
            [("anchoring_id", 1)],
            unique=True
        )
        await DatabaseOperations.create_index(
            Collections.SESSION_ANCHORINGS,
            [("status", 1)]
        )
        
        # Consensus votes collection indexes
        await DatabaseOperations.create_index(
            Collections.CONSENSUS_VOTES,
            [("vote_id", 1)],
            unique=True
        )
        await DatabaseOperations.create_index(
            Collections.CONSENSUS_VOTES,
            [("block_height", 1)]
        )
        await DatabaseOperations.create_index(
            Collections.CONSENSUS_VOTES,
            [("node_id", 1)]
        )
        
        # Merkle trees collection indexes
        await DatabaseOperations.create_index(
            Collections.MERKLE_TREES,
            [("root_hash", 1)],
            unique=True
        )
        await DatabaseOperations.create_index(
            Collections.MERKLE_TREES,
            [("session_id", 1)]
        )
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create database indexes: {e}")
        raise
