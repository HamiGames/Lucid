"""
Redis Service for Lucid Database Infrastructure
Provides Redis operations, caching, session management, and pub/sub functionality.

This service implements the Redis operations layer for the Lucid blockchain system,
handling caching, session storage, rate limiting, and real-time messaging.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Set
import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import (
    ConnectionError,
    TimeoutError,
    RedisError,
    ResponseError
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisService:
    """
    Redis Service for Lucid Database Infrastructure
    
    Provides comprehensive Redis operations including:
    - Connection management and pooling
    - Caching operations with TTL
    - Session management
    - Rate limiting
    - Pub/Sub messaging
    - Distributed locking
    - Health monitoring
    """
    
    def __init__(self, uri: str, max_connections: int = 100):
        """
        Initialize Redis service
        
        Args:
            uri: Redis connection URI
            max_connections: Maximum connections in pool
        """
        self.uri = uri
        self.max_connections = max_connections
        self.client: Optional[Redis] = None
        self.connection_pool: Optional[ConnectionPool] = None
        self._pubsub_client: Optional[Redis] = None
        
    async def connect(self) -> bool:
        """
        Establish connection to Redis
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Create connection pool
            self.connection_pool = ConnectionPool.from_url(
                self.uri,
                max_connections=self.max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Create Redis client
            self.client = Redis(
                connection_pool=self.connection_pool,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Create separate client for pub/sub
            self._pubsub_client = Redis(
                connection_pool=self.connection_pool,
                decode_responses=True
            )
            
            # Test connection
            await self.client.ping()
            logger.info("Successfully connected to Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Close Redis connections"""
        if self.client:
            await self.client.close()
        if self._pubsub_client:
            await self._pubsub_client.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()
        logger.info("Redis connections closed")
    
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
            ping_result = await self.client.ping()
            
            # Get Redis info
            info = await self.client.info()
            
            # Get memory usage
            memory_info = await self.client.info("memory")
            
            # Get connection info
            clients_info = await self.client.info("clients")
            
            # Get stats info
            stats_info = await self.client.info("stats")
            
            return {
                "status": "healthy" if ping_result else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "server_info": {
                    "version": info.get("redis_version"),
                    "uptime": info.get("uptime_in_seconds"),
                    "role": info.get("role")
                },
                "memory": {
                    "used_memory": memory_info.get("used_memory"),
                    "used_memory_human": memory_info.get("used_memory_human"),
                    "used_memory_peak": memory_info.get("used_memory_peak"),
                    "used_memory_peak_human": memory_info.get("used_memory_peak_human"),
                    "maxmemory": memory_info.get("maxmemory"),
                    "maxmemory_human": memory_info.get("maxmemory_human")
                },
                "connections": {
                    "connected_clients": clients_info.get("connected_clients"),
                    "blocked_clients": clients_info.get("blocked_clients"),
                    "rejected_connections": clients_info.get("rejected_connections")
                },
                "stats": {
                    "total_commands_processed": stats_info.get("total_commands_processed"),
                    "instantaneous_ops_per_sec": stats_info.get("instantaneous_ops_per_sec"),
                    "keyspace_hits": stats_info.get("keyspace_hits"),
                    "keyspace_misses": stats_info.get("keyspace_misses"),
                    "hit_rate": self._calculate_hit_rate(
                        stats_info.get("keyspace_hits", 0),
                        stats_info.get("keyspace_misses", 0)
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0
    
    # Cache Operations
    async def cache_set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set a cache value with TTL
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)
            
            result = await self.client.setex(key, ttl, value)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return result
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    async def cache_get(self, key: str, parse_json: bool = False) -> Optional[Any]:
        """
        Get a cache value
        
        Args:
            key: Cache key
            parse_json: Whether to parse value as JSON
            
        Returns:
            Cached value or None if not found
        """
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            if parse_json:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON for key {key}")
                    return value
            
            return value
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    async def cache_delete(self, key: str) -> bool:
        """
        Delete a cache key
        
        Args:
            key: Cache key to delete
            
        Returns:
            bool: True if key was deleted
        """
        try:
            result = await self.client.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    async def cache_exists(self, key: str) -> bool:
        """
        Check if cache key exists
        
        Args:
            key: Cache key to check
            
        Returns:
            bool: True if key exists
        """
        try:
            result = await self.client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to check cache key {key}: {e}")
            return False
    
    async def cache_expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for a key
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            result = await self.client.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {e}")
            return False
    
    async def cache_ttl(self, key: str) -> int:
        """
        Get time to live for a key
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds (-1 if no expiration, -2 if key doesn't exist)
        """
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Failed to get TTL for key {key}: {e}")
            return -2
    
    # Session Management
    async def create_session(self, session_id: str, user_id: str, 
                           session_data: Dict, ttl: int = 86400) -> bool:
        """
        Create a user session
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            session_data: Session data to store
            ttl: Session TTL in seconds (default 24 hours)
            
        Returns:
            bool: True if successful
        """
        try:
            session_key = f"session:{session_id}"
            user_sessions_key = f"user_sessions:{user_id}"
            
            # Store session data
            session_info = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                **session_data
            }
            
            # Use pipeline for atomic operations
            async with self.client.pipeline() as pipe:
                pipe.setex(session_key, ttl, json.dumps(session_info))
                pipe.sadd(user_sessions_key, session_id)
                pipe.expire(user_sessions_key, ttl)
                await pipe.execute()
            
            logger.debug(f"Session created: {session_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        try:
            session_key = f"session:{session_id}"
            session_data = await self.client.get(session_key)
            
            if session_data:
                return json.loads(session_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def update_session_activity(self, session_id: str) -> bool:
        """
        Update session last activity timestamp
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if successful
        """
        try:
            session_key = f"session:{session_id}"
            session_data = await self.get_session(session_id)
            
            if session_data:
                session_data["last_activity"] = datetime.utcnow().isoformat()
                ttl = await self.client.ttl(session_key)
                if ttl > 0:
                    await self.client.setex(session_key, ttl, json.dumps(session_data))
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update session activity {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if successful
        """
        try:
            session_key = f"session:{session_id}"
            
            # Get session to find user_id
            session_data = await self.get_session(session_id)
            if session_data:
                user_id = session_data.get("user_id")
                user_sessions_key = f"user_sessions:{user_id}"
                
                # Remove from both session and user sessions
                async with self.client.pipeline() as pipe:
                    pipe.delete(session_key)
                    pipe.srem(user_sessions_key, session_id)
                    await pipe.execute()
            else:
                await self.client.delete(session_key)
            
            logger.debug(f"Session deleted: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all sessions for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of session IDs
        """
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            sessions = await self.client.smembers(user_sessions_key)
            return list(sessions)
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    # Rate Limiting
    async def check_rate_limit(self, identifier: str, limit: int, 
                             window_seconds: int = 60) -> Dict[str, Any]:
        """
        Check and update rate limit for an identifier
        
        Args:
            identifier: Rate limit identifier (IP, user ID, etc.)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Dict with rate limit status
        """
        try:
            key = f"rate_limit:{identifier}"
            current_time = int(datetime.utcnow().timestamp())
            window_start = current_time - window_seconds
            
            # Use sliding window log approach
            async with self.client.pipeline() as pipe:
                # Remove expired entries
                pipe.zremrangebyscore(key, 0, window_start)
                # Count current requests
                pipe.zcard(key)
                # Add current request
                pipe.zadd(key, {str(current_time): current_time})
                # Set expiration
                pipe.expire(key, window_seconds)
                
                results = await pipe.execute()
                current_count = results[1]
            
            remaining = max(0, limit - current_count - 1)
            reset_time = current_time + window_seconds
            
            return {
                "allowed": current_count < limit,
                "limit": limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "current_count": current_count + 1
            }
            
        except Exception as e:
            logger.error(f"Failed to check rate limit for {identifier}: {e}")
            return {
                "allowed": True,  # Fail open
                "limit": limit,
                "remaining": limit - 1,
                "reset_time": int(datetime.utcnow().timestamp()) + window_seconds,
                "current_count": 1
            }
    
    # Distributed Locking
    async def acquire_lock(self, lock_name: str, timeout: int = 10, 
                          blocking_timeout: int = 5) -> Optional[str]:
        """
        Acquire a distributed lock
        
        Args:
            lock_name: Name of the lock
            timeout: Lock timeout in seconds
            blocking_timeout: How long to wait for lock
            
        Returns:
            Lock identifier if acquired, None otherwise
        """
        try:
            lock_key = f"lock:{lock_name}"
            lock_value = f"{datetime.utcnow().timestamp()}:{id(self)}"
            
            # Try to acquire lock with timeout
            result = await self.client.set(
                lock_key, 
                lock_value, 
                nx=True, 
                ex=timeout
            )
            
            if result:
                logger.debug(f"Lock acquired: {lock_name}")
                return lock_value
            
            # If blocking_timeout specified, wait for lock
            if blocking_timeout > 0:
                end_time = datetime.utcnow() + timedelta(seconds=blocking_timeout)
                while datetime.utcnow() < end_time:
                    await asyncio.sleep(0.1)
                    result = await self.client.set(
                        lock_key, 
                        lock_value, 
                        nx=True, 
                        ex=timeout
                    )
                    if result:
                        logger.debug(f"Lock acquired after waiting: {lock_name}")
                        return lock_value
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to acquire lock {lock_name}: {e}")
            return None
    
    async def release_lock(self, lock_name: str, lock_value: str) -> bool:
        """
        Release a distributed lock
        
        Args:
            lock_name: Name of the lock
            lock_value: Lock identifier returned by acquire_lock
            
        Returns:
            bool: True if lock was released
        """
        try:
            lock_key = f"lock:{lock_name}"
            
            # Lua script to atomically check and delete lock
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.client.eval(lua_script, 1, lock_key, lock_value)
            
            if result:
                logger.debug(f"Lock released: {lock_name}")
                return True
            else:
                logger.warning(f"Failed to release lock {lock_name}: not owner or expired")
                return False
                
        except Exception as e:
            logger.error(f"Failed to release lock {lock_name}: {e}")
            return False
    
    # Pub/Sub Operations
    async def publish_message(self, channel: str, message: Any) -> int:
        """
        Publish a message to a channel
        
        Args:
            channel: Channel name
            message: Message to publish
            
        Returns:
            Number of subscribers that received the message
        """
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            elif not isinstance(message, str):
                message = str(message)
            
            result = await self.client.publish(channel, message)
            logger.debug(f"Message published to {channel}: {result} subscribers")
            return result
            
        except Exception as e:
            logger.error(f"Failed to publish message to {channel}: {e}")
            return 0
    
    async def subscribe_to_channels(self, channels: List[str], 
                                  message_handler=None) -> Optional[Any]:
        """
        Subscribe to channels
        
        Args:
            channels: List of channel names
            message_handler: Async function to handle messages
            
        Returns:
            PubSub object for manual message handling
        """
        try:
            pubsub = self._pubsub_client.pubsub()
            await pubsub.subscribe(*channels)
            
            if message_handler:
                # Start message handling task
                asyncio.create_task(
                    self._handle_pubsub_messages(pubsub, message_handler)
                )
            
            logger.info(f"Subscribed to channels: {channels}")
            return pubsub
            
        except Exception as e:
            logger.error(f"Failed to subscribe to channels {channels}: {e}")
            return None
    
    async def _handle_pubsub_messages(self, pubsub, message_handler):
        """Handle pub/sub messages"""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Try to parse as JSON
                        data = json.loads(message["data"])
                    except json.JSONDecodeError:
                        data = message["data"]
                    
                    await message_handler(message["channel"], data)
        except Exception as e:
            logger.error(f"Error in pub/sub message handler: {e}")
    
    # Utility Operations
    async def get_keys_pattern(self, pattern: str) -> List[str]:
        """
        Get keys matching a pattern
        
        Args:
            pattern: Key pattern (e.g., "session:*")
            
        Returns:
            List of matching keys
        """
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            return keys
        except Exception as e:
            logger.error(f"Failed to get keys for pattern {pattern}: {e}")
            return []
    
    async def flush_database(self, database: int = None) -> bool:
        """
        Flush database (USE WITH CAUTION)
        
        Args:
            database: Database number (None for current)
            
        Returns:
            bool: True if successful
        """
        try:
            if database is not None:
                await self.client.select(database)
            
            await self.client.flushdb()
            logger.warning("Database flushed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to flush database: {e}")
            return False

# Global Redis service instance
redis_service = None

async def get_redis_service(uri: str = None, max_connections: int = 100) -> RedisService:
    """
    Get or create Redis service instance
    
    Args:
        uri: Redis connection URI
        max_connections: Maximum connections in pool
        
    Returns:
        RedisService instance
    """
    global redis_service
    
    if redis_service is None:
        if uri is None:
            raise ValueError("Redis URI is required for first initialization")
        
        redis_service = RedisService(uri, max_connections)
        await redis_service.connect()
    
    return redis_service

async def close_redis_service():
    """Close the global Redis service"""
    global redis_service
    if redis_service:
        await redis_service.disconnect()
        redis_service = None
