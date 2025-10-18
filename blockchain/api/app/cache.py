"""
Cache Module

This module contains caching utilities for the Blockchain API.
Handles Redis connections and common caching operations.
"""

import logging
import json
from typing import Optional, Dict, Any, List, Union
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError
import asyncio

logger = logging.getLogger(__name__)

class CacheManager:
    """Cache manager for Redis operations."""
    
    def __init__(self, redis_url: str, redis_host: str, redis_port: int, redis_db: int):
        self.redis_url = redis_url
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.client: Optional[redis.Redis] = None
    
    async def connect(self) -> bool:
        """Connect to Redis server."""
        try:
            if self.redis_url:
                self.client = redis.from_url(self.redis_url)
            else:
                self.client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    db=self.redis_db,
                    decode_responses=True
                )
            
            # Test connection
            await self.client.ping()
            logger.info("Connected to Redis server")
            return True
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis server."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            if not self.client:
                return False
            
            await self.client.ping()
            return True
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

# Global cache manager instance
cache_manager: Optional[CacheManager] = None

async def init_cache(redis_url: str, redis_host: str, redis_port: int, redis_db: int) -> bool:
    """Initialize cache connection."""
    global cache_manager
    
    cache_manager = CacheManager(redis_url, redis_host, redis_port, redis_db)
    return await cache_manager.connect()

async def close_cache():
    """Close cache connection."""
    global cache_manager
    
    if cache_manager:
        await cache_manager.disconnect()
        cache_manager = None

def get_cache() -> redis.Redis:
    """Get cache client instance."""
    if not cache_manager or not cache_manager.client:
        raise RuntimeError("Cache not initialized")
    return cache_manager.client

# Cache operations
class CacheOperations:
    """Common cache operations."""
    
    @staticmethod
    async def set(
        key: str,
        value: Union[str, Dict[str, Any], List[Any]],
        expire: Optional[int] = None
    ) -> bool:
        """Set a value in cache."""
        try:
            cache = get_cache()
            
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if expire:
                await cache.setex(key, expire, value)
            else:
                await cache.set(key, value)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    @staticmethod
    async def get(key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        try:
            cache = get_cache()
            value = await cache.get(key)
            
            if value is None:
                return default
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return default
    
    @staticmethod
    async def delete(key: str) -> bool:
        """Delete a key from cache."""
        try:
            cache = get_cache()
            result = await cache.delete(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    @staticmethod
    async def exists(key: str) -> bool:
        """Check if a key exists in cache."""
        try:
            cache = get_cache()
            result = await cache.exists(key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to check cache key {key}: {e}")
            return False
    
    @staticmethod
    async def expire(key: str, seconds: int) -> bool:
        """Set expiration for a key."""
        try:
            cache = get_cache()
            result = await cache.expire(key, seconds)
            return result
            
        except Exception as e:
            logger.error(f"Failed to set expiration for cache key {key}: {e}")
            return False
    
    @staticmethod
    async def ttl(key: str) -> int:
        """Get time to live for a key."""
        try:
            cache = get_cache()
            return await cache.ttl(key)
            
        except Exception as e:
            logger.error(f"Failed to get TTL for cache key {key}: {e}")
            return -1
    
    @staticmethod
    async def increment(key: str, amount: int = 1) -> int:
        """Increment a numeric value in cache."""
        try:
            cache = get_cache()
            return await cache.incrby(key, amount)
            
        except Exception as e:
            logger.error(f"Failed to increment cache key {key}: {e}")
            return 0
    
    @staticmethod
    async def decrement(key: str, amount: int = 1) -> int:
        """Decrement a numeric value in cache."""
        try:
            cache = get_cache()
            return await cache.decrby(key, amount)
            
        except Exception as e:
            logger.error(f"Failed to decrement cache key {key}: {e}")
            return 0
    
    @staticmethod
    async def set_hash(key: str, field: str, value: Union[str, Dict[str, Any]]) -> bool:
        """Set a field in a hash."""
        try:
            cache = get_cache()
            
            if isinstance(value, dict):
                value = json.dumps(value)
            
            result = await cache.hset(key, field, value)
            return result >= 0
            
        except Exception as e:
            logger.error(f"Failed to set hash field {field} in key {key}: {e}")
            return False
    
    @staticmethod
    async def get_hash(key: str, field: str, default: Any = None) -> Any:
        """Get a field from a hash."""
        try:
            cache = get_cache()
            value = await cache.hget(key, field)
            
            if value is None:
                return default
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Failed to get hash field {field} from key {key}: {e}")
            return default
    
    @staticmethod
    async def get_all_hash(key: str) -> Dict[str, Any]:
        """Get all fields from a hash."""
        try:
            cache = get_cache()
            hash_data = await cache.hgetall(key)
            
            # Parse JSON values
            for field, value in hash_data.items():
                try:
                    hash_data[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string
            
            return hash_data
            
        except Exception as e:
            logger.error(f"Failed to get all hash fields from key {key}: {e}")
            return {}
    
    @staticmethod
    async def delete_hash_field(key: str, field: str) -> bool:
        """Delete a field from a hash."""
        try:
            cache = get_cache()
            result = await cache.hdel(key, field)
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete hash field {field} from key {key}: {e}")
            return False
    
    @staticmethod
    async def list_push(key: str, *values: Union[str, Dict[str, Any]]) -> int:
        """Push values to a list."""
        try:
            cache = get_cache()
            
            # Convert dicts to JSON strings
            json_values = []
            for value in values:
                if isinstance(value, dict):
                    json_values.append(json.dumps(value))
                else:
                    json_values.append(str(value))
            
            result = await cache.lpush(key, *json_values)
            return result
            
        except Exception as e:
            logger.error(f"Failed to push to list {key}: {e}")
            return 0
    
    @staticmethod
    async def list_pop(key: str) -> Any:
        """Pop a value from a list."""
        try:
            cache = get_cache()
            value = await cache.rpop(key)
            
            if value is None:
                return None
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Failed to pop from list {key}: {e}")
            return None
    
    @staticmethod
    async def list_range(key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get a range of values from a list."""
        try:
            cache = get_cache()
            values = await cache.lrange(key, start, end)
            
            # Parse JSON values
            parsed_values = []
            for value in values:
                try:
                    parsed_values.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    parsed_values.append(value)
            
            return parsed_values
            
        except Exception as e:
            logger.error(f"Failed to get range from list {key}: {e}")
            return []
    
    @staticmethod
    async def list_length(key: str) -> int:
        """Get the length of a list."""
        try:
            cache = get_cache()
            return await cache.llen(key)
            
        except Exception as e:
            logger.error(f"Failed to get length of list {key}: {e}")
            return 0

# Cache key patterns
class CacheKeys:
    """Cache key patterns for different data types."""
    
    BLOCK_INFO = "block:info:{block_id}"
    BLOCK_HEIGHT = "block:height:{height}"
    BLOCK_LATEST = "block:latest"
    BLOCK_LIST = "blocks:list:{page}:{limit}:{sort}"
    
    TRANSACTION_INFO = "transaction:info:{tx_id}"
    TRANSACTION_PENDING = "transactions:pending"
    TRANSACTION_BATCH = "transaction:batch:{batch_id}"
    
    SESSION_ANCHORING = "session:anchoring:{session_id}"
    ANCHORING_STATUS = "anchoring:status:{session_id}"
    
    CONSENSUS_STATUS = "consensus:status"
    CONSENSUS_PARTICIPANTS = "consensus:participants"
    CONSENSUS_HISTORY = "consensus:history:{limit}:{offset}"
    
    MERKLE_TREE = "merkle:tree:{root_hash}"
    MERKLE_VALIDATION = "merkle:validation:{session_id}"
    
    NETWORK_INFO = "network:info"
    NETWORK_PEERS = "network:peers"
    
    SYSTEM_METRICS = "system:metrics"
    HEALTH_CHECK = "health:check"
