"""
Database Connection Management

File: 03-api-gateway/api/app/database/connection.py
Purpose: MongoDB and Redis connection initialization and management
Includes tor-proxy bootstrap wait sequence before attempting connections
"""

import logging
import asyncio
import socket
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import redis.asyncio as redis  # pyright: ignore[reportMissingImports]
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global database clients
_mongodb_client: Optional[AsyncIOMotorClient] = None
_redis_client: Optional[redis.Redis] = None


async def _wait_for_tor_proxy(host: str = "tor-proxy", port: int = 9051, timeout: int = 180, retry_interval: int = 5) -> None:
    """Wait for tor-proxy to bootstrap and be ready
    
    Args:
        host: Tor proxy hostname
        port: Tor control port
        timeout: Maximum time to wait in seconds
        retry_interval: Time between connection attempts in seconds
    """
    logger.info(f"Waiting for tor-proxy bootstrap at {host}:{port} (timeout: {timeout}s)")
    start_time = asyncio.get_event_loop().time()
    
    while True:
        try:
            # Try to connect to tor control port
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5
            )
            writer.close()
            await writer.wait_closed()
            logger.info(f"✓ tor-proxy is ready at {host}:{port}")
            return
            
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError) as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.error(f"✗ Timeout waiting for tor-proxy after {elapsed:.1f}s")
                raise RuntimeError(f"tor-proxy failed to start within {timeout}s: {e}")
            
            remaining = timeout - elapsed
            logger.warning(f"tor-proxy not ready yet ({elapsed:.1f}s elapsed, {remaining:.1f}s remaining): {e}")
            await asyncio.sleep(retry_interval)


async def _wait_for_mongodb(mongodb_uri: str, timeout: int = 120, retry_interval: int = 5) -> AsyncIOMotorClient:
    """Wait for MongoDB to be ready with retry logic
    
    Args:
        mongodb_uri: MongoDB connection string
        timeout: Maximum time to wait in seconds
        retry_interval: Time between connection attempts in seconds
        
    Returns:
        Connected AsyncIOMotorClient
    """
    logger.info(f"Waiting for MongoDB to be ready (timeout: {timeout}s)")
    start_time = asyncio.get_event_loop().time()
    last_error = None
    
    while True:
        try:
            client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            await client.admin.command('ping')
            logger.info("✓ MongoDB connection established and healthy")
            return client
            
        except Exception as e:
            last_error = e
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.error(f"✗ Timeout waiting for MongoDB after {elapsed:.1f}s: {last_error}")
                raise RuntimeError(f"MongoDB failed to connect within {timeout}s: {last_error}")
            
            remaining = timeout - elapsed
            logger.warning(f"MongoDB not ready yet ({elapsed:.1f}s elapsed, {remaining:.1f}s remaining): {last_error}")
            await asyncio.sleep(retry_interval)


async def _wait_for_redis(redis_url: str, timeout: int = 120, retry_interval: int = 5) -> redis.Redis:
    """Wait for Redis to be ready with retry logic
    
    Args:
        redis_url: Redis connection URL
        timeout: Maximum time to wait in seconds
        retry_interval: Time between connection attempts in seconds
        
    Returns:
        Connected Redis client
    """
    logger.info(f"Waiting for Redis to be ready (timeout: {timeout}s)")
    start_time = asyncio.get_event_loop().time()
    last_error = None
    
    while True:
        try:
            client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=5)
            await client.ping()
            logger.info("✓ Redis connection established and healthy")
            return client
            
        except Exception as e:
            last_error = e
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.error(f"✗ Timeout waiting for Redis after {elapsed:.1f}s: {last_error}")
                raise RuntimeError(f"Redis failed to connect within {timeout}s: {last_error}")
            
            remaining = timeout - elapsed
            logger.warning(f"Redis not ready yet ({elapsed:.1f}s elapsed, {remaining:.1f}s remaining): {last_error}")
            await asyncio.sleep(retry_interval)


async def init_database() -> None:
    """Initialize database connections with tor-proxy bootstrap wait sequence"""
    global _mongodb_client, _redis_client
    
    try:
        # Step 1: Wait for tor-proxy to bootstrap first
        logger.info("=== PHASE 1: Waiting for tor-proxy bootstrap ===")
        await _wait_for_tor_proxy(host="tor-proxy", port=9051, timeout=180, retry_interval=5)
        
        # Step 2: Wait for MongoDB
        logger.info("=== PHASE 2: Waiting for MongoDB ===")
        mongodb_uri = settings.mongodb_connection_string
        if not mongodb_uri:
            raise RuntimeError("No MongoDB connection string configured (set MONGODB_URL or MONGODB_URI)")
        logger.info(f"MongoDB URI: {mongodb_uri[:50]}...")
        _mongodb_client = await _wait_for_mongodb(mongodb_uri, timeout=120, retry_interval=5)
        
        # Step 3: Wait for Redis
        logger.info("=== PHASE 3: Waiting for Redis ===")
        if not settings.REDIS_URL:
            raise RuntimeError("No Redis URL configured (set REDIS_URL)")
        logger.info(f"Redis URL: {settings.REDIS_URL[:50]}...")
        _redis_client = await _wait_for_redis(settings.REDIS_URL, timeout=120, retry_interval=5)
        
        # Step 4: Create indexes
        logger.info("=== PHASE 4: Creating database indexes ===")
        await _create_indexes()
        
        logger.info("✓ All database connections initialized successfully")
        
    except Exception as e:
        logger.error(f"✗ Failed to initialize database connections: {e}")
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

