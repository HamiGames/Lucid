"""
Database Connection Management
Handles MongoDB connections for blockchain API.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import os

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages MongoDB connection for blockchain API."""
    
    def __init__(self, connection_string: str, database_name: str):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._connected = False
        
    async def connect(self) -> bool:
        """Establish connection to MongoDB."""
        try:
            logger.info(f"Connecting to MongoDB database: {self.database_name}")
            
            # Create client with connection options
            self.client = AsyncIOMotorClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,         # 10 second connection timeout
                socketTimeoutMS=20000,          # 20 second socket timeout
                maxPoolSize=50,                 # Maximum connection pool size
                minPoolSize=5,                  # Minimum connection pool size
                maxIdleTimeMS=30000,           # 30 second max idle time
                retryWrites=True,              # Enable retryable writes
                retryReads=True                # Enable retryable reads
            )
            
            # Get database reference
            self.database = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            
            self._connected = True
            logger.info("Successfully connected to MongoDB")
            
            # Ensure indexes exist
            await self._ensure_indexes()
            
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            self._connected = False
            return False
            
    async def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            logger.info("Disconnecting from MongoDB")
            self.client.close()
            self.client = None
            self.database = None
            self._connected = False
            
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on database connection."""
        try:
            if not self._connected or not self.client:
                return {
                    "healthy": False,
                    "error": "Not connected to database"
                }
                
            # Test connection with ping
            await self.client.admin.command('ping')
            
            # Get server info
            server_info = await self.client.server_info()
            
            # Get database stats
            db_stats = await self.database.command('dbStats')
            
            return {
                "healthy": True,
                "server_version": server_info.get("version"),
                "database_name": self.database_name,
                "collections": db_stats.get("collections", 0),
                "data_size_bytes": db_stats.get("dataSize", 0),
                "storage_size_bytes": db_stats.get("storageSize", 0),
                "indexes": db_stats.get("indexes", 0)
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e)
            }
            
    async def _ensure_indexes(self):
        """Ensure required indexes exist."""
        try:
            logger.info("Ensuring database indexes exist")
            
            # Blocks collection indexes
            blocks_collection = self.database.blocks
            await blocks_collection.create_index("hash", unique=True)
            await blocks_collection.create_index("height", unique=True)
            await blocks_collection.create_index("timestamp")
            await blocks_collection.create_index("previous_hash")
            
            # Transactions collection indexes
            transactions_collection = self.database.transactions
            await transactions_collection.create_index("hash", unique=True)
            await transactions_collection.create_index("block_hash")
            await transactions_collection.create_index("from_address")
            await transactions_collection.create_index("to_address")
            await transactions_collection.create_index("timestamp")
            await transactions_collection.create_index("status")
            
            # Session anchors collection indexes
            anchors_collection = self.database.session_anchors
            await anchors_collection.create_index("session_id", unique=True)
            await anchors_collection.create_index("merkle_root")
            await anchors_collection.create_index("block_hash")
            await anchors_collection.create_index("status")
            await anchors_collection.create_index("created_at")
            
            # Consensus rounds collection indexes
            consensus_collection = self.database.consensus_rounds
            await consensus_collection.create_index("round_id", unique=True)
            await consensus_collection.create_index("block_hash")
            await consensus_collection.create_index("state")
            await consensus_collection.create_index("started_at")
            
            # Consensus votes collection indexes
            votes_collection = self.database.consensus_votes
            await votes_collection.create_index("vote_id", unique=True)
            await votes_collection.create_index("round_id")
            await votes_collection.create_index("voter_id")
            await votes_collection.create_index("block_hash")
            
            logger.info("Database indexes ensured successfully")
            
        except Exception as e:
            logger.error(f"Error ensuring database indexes: {e}")
            raise
            
    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected and self.client is not None
        
    def get_collection(self, collection_name: str):
        """Get a collection from the database."""
        if not self.database:
            raise RuntimeError("Database not connected")
        return self.database[collection_name]


# Global database connection instance
_db_connection: Optional[DatabaseConnection] = None


async def get_database_connection() -> DatabaseConnection:
    """Get the global database connection instance."""
    global _db_connection
    
    if _db_connection is None:
        # Get connection details from environment
        connection_string = os.getenv(
            "MONGODB_URI", 
            "mongodb://localhost:27017"
        )
        database_name = os.getenv(
            "BLOCKCHAIN_DB_NAME", 
            "lucid_blocks"
        )
        
        _db_connection = DatabaseConnection(connection_string, database_name)
        
        # Connect to database
        connected = await _db_connection.connect()
        if not connected:
            raise RuntimeError("Failed to connect to database")
            
    return _db_connection


async def close_database_connection():
    """Close the global database connection."""
    global _db_connection
    
    if _db_connection:
        await _db_connection.disconnect()
        _db_connection = None


# Context manager for database operations
class DatabaseSession:
    """Context manager for database operations."""
    
    def __init__(self):
        self.connection: Optional[DatabaseConnection] = None
        
    async def __aenter__(self) -> DatabaseConnection:
        self.connection = await get_database_connection()
        return self.connection
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Connection is managed globally, don't close here
        pass


# Utility functions for common database operations
async def ensure_database_connection() -> DatabaseConnection:
    """Ensure database connection is established."""
    connection = await get_database_connection()
    if not connection.is_connected:
        connected = await connection.connect()
        if not connected:
            raise RuntimeError("Unable to establish database connection")
    return connection


async def test_database_connection() -> bool:
    """Test database connection."""
    try:
        connection = await get_database_connection()
        health = await connection.health_check()
        return health.get("healthy", False)
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
