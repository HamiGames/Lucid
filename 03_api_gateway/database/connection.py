"""
Lucid API Gateway - Database Connection
MongoDB connection with connection pooling.

File: 03_api_gateway/database/connection.py
Lines: ~100
Purpose: MongoDB connection
Dependencies: motor (async MongoDB)
"""


from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

import os
from api.app.config import get_settings

try:
    from api.app.utils.logging import get_logger, setup_logging
    logger = get_logger("LOG_LEVEL", "INFO")
    settings = get_settings()
    setup_logging(settings) 
    import logging
    logger = logging.getLogger("LOG_LEVEL")
    settings = get_settings()
    
# Global database client and database
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def get_database() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance with connection pooling.
    
    Returns:
        AsyncIOMotorDatabase instance
    """
    global _client, _database
    
    if _database is not None:
        return _database
        
    try:
        # Create MongoDB client with connection pooling
        _client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=100,
            minPoolSize=10,
            maxIdleTimeMS=45000,
            serverSelectionTimeoutMS=5000,
        )
        
        # Get database
        db_name = settings.MONGODB_URI.split('/')[-1].split('?')[0]
        if not db_name:
            db_name = "lucid"
            
        _database = _client[db_name]
        
        # Test connection
        await _client.admin.command('ping')
        logger.info(f"Connected to MongoDB database: {db_name}")
        
        return _database
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_database():
    """Close MongoDB connection."""
    global _client, _database
    
    if _client:
        _client.close()
        _client = None
        _database = None
        logger.info("Closed MongoDB connection")

