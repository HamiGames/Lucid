"""
Database Connection Management

File: 03-api-gateway/api/app/database/connection.py
Purpose: MongoDB and Redis connection initialization and management
"""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import redis.asyncio as redis
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global database clients
_mongodb_client: Optional[AsyncIOMotorClient] = None
_redis_client: Optional[redis.Redis] = None


async def init_database() -> None:
    """Initialize database connections"""
    global _mongodb_client, _redis_client
    
    try:
        # Initialize MongoDB
        logger.info(f"Connecting to MongoDB: {settings.MONGODB_URI}")
        _mongodb_client = AsyncIOMotorClient(settings.MONGODB_URI)
        
        # Verify MongoDB connection
        await _mongodb_client.admin.command('ping')
        logger.info("MongoDB connection established")
        
        # Initialize Redis
        logger.info(f"Connecting to Redis: {settings.REDIS_URL}")
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Verify Redis connection
        await _redis_client.ping()
        logger.info("Redis connection established")
        
        # Create indexes
        await _create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to initialize database connections: {e}")
        raise


async def _create_indexes() -> None:
    """Create database indexes"""
    try:
        db = get_database()
        
        # Users collection indexes
        await db.users.create_index("email", unique=True)
        await db.users.create_index("username", unique=True)
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("role")
        await db.users.create_index("created_at")
        
        # Sessions collection indexes
        await db.sessions.create_index("session_id", unique=True)
        await db.sessions.create_index("user_id")
        await db.sessions.create_index("status")
        await db.sessions.create_index([("user_id", 1), ("created_at", -1)])
        
        # Auth tokens collection indexes
        await db.auth_tokens.create_index("token_id", unique=True)
        await db.auth_tokens.create_index("token_hash", unique=True)
        await db.auth_tokens.create_index("user_id")
        await db.auth_tokens.create_index("expires_at")
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"Failed to create some indexes: {e}")


def get_database() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance"""
    if _mongodb_client is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _mongodb_client[settings.MONGODB_DATABASE]


def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_database() first.")
    return _redis_client


async def close_database() -> None:
    """Close database connections"""
    global _mongodb_client, _redis_client
    
    if _mongodb_client:
        _mongodb_client.close()
        logger.info("MongoDB connection closed")
    
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")

