"""
Database Cache Management API

Provides endpoints for Redis cache operations:
- Cache statistics
- Cache operations (get, set, delete)
- Cache clearing and flushing
- Session cache management
- Rate limit cache management

Port: 8088 (Storage-Database Cluster)
Phase: Phase 1 - Foundation
"""

from fastapi import APIRouter, HTTPException, Query, Body, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..services.redis_service import RedisService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/database/cache",
    tags=["database-cache"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Service instance
redis_service: RedisService = None


def init_service(redis: RedisService):
    """Initialize Redis service instance"""
    global redis_service
    redis_service = redis


# Request/Response Models
class CacheSetRequest(BaseModel):
    """Request model for setting cache value"""
    key: str = Field(..., description="Cache key")
    value: str = Field(..., description="Cache value")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")


class CacheDeleteRequest(BaseModel):
    """Request model for deleting cache keys"""
    keys: List[str] = Field(..., description="List of keys to delete")


@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_stats():
    """
    Get Redis cache statistics
    
    Returns:
        Cache statistics including memory usage, hit/miss ratio, keys count
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        info = await redis_service.get_info()
        
        stats = {
            "connected": True,
            "version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
            "total_keys": await redis_service.get_total_keys(),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": calculate_hit_rate(
                info.get("keyspace_hits", 0),
                info.get("keyspace_misses", 0)
            ),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@router.get("/keys", response_model=List[str])
async def list_cache_keys(
    pattern: str = Query("*", description="Key pattern (supports wildcards)"),
    limit: int = Query(100, ge=1, le=10000, description="Maximum number of keys to return")
):
    """
    List cache keys matching a pattern
    
    Args:
        pattern: Key pattern (supports * and ? wildcards)
        limit: Maximum number of keys to return
        
    Returns:
        List of matching keys
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        keys = await redis_service.scan_keys(pattern, limit)
        
        return keys
        
    except Exception as e:
        logger.error(f"Error listing cache keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cache keys: {str(e)}"
        )


@router.get("/keys/{key}", response_model=Dict[str, Any])
async def get_cache_value(key: str):
    """
    Get value for a cache key
    
    Args:
        key: Cache key
        
    Returns:
        Cache value and metadata
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        # Check if key exists
        exists = await redis_service.exists(key)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Key '{key}' not found"
            )
        
        # Get value
        value = await redis_service.get(key)
        
        # Get TTL
        ttl = await redis_service.get_ttl(key)
        
        return {
            "key": key,
            "value": value,
            "ttl": ttl,
            "exists": True,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache value: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache value: {str(e)}"
        )


@router.post("/keys", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def set_cache_value(request: CacheSetRequest):
    """
    Set a cache value
    
    Args:
        request: Cache set request
        
    Returns:
        Success message
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        # Set value
        result = await redis_service.set(request.key, request.value, request.ttl)
        
        return {
            "success": True,
            "message": f"Cache key '{request.key}' set successfully",
            "key": request.key,
            "ttl": request.ttl,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error setting cache value: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set cache value: {str(e)}"
        )


@router.delete("/keys", response_model=Dict[str, Any])
async def delete_cache_keys(request: CacheDeleteRequest):
    """
    Delete cache keys
    
    Args:
        request: Delete keys request
        
    Returns:
        Number of keys deleted
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        # Delete keys
        deleted_count = await redis_service.delete_keys(request.keys)
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} cache keys",
            "keys_requested": len(request.keys),
            "keys_deleted": deleted_count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error deleting cache keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cache keys: {str(e)}"
        )


@router.post("/flush", response_model=Dict[str, Any])
async def flush_cache(
    pattern: Optional[str] = Query(None, description="Pattern for keys to flush (default: all)")
):
    """
    Flush cache keys
    
    Args:
        pattern: Optional pattern for keys to flush (default: flush all)
        
    Warning:
        This operation will delete cache data. Use with caution.
        
    Returns:
        Number of keys flushed
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        if pattern:
            # Flush keys matching pattern
            keys = await redis_service.scan_keys(pattern, limit=10000)
            deleted_count = await redis_service.delete_keys(keys)
        else:
            # Flush entire cache
            deleted_count = await redis_service.flushdb()
        
        return {
            "success": True,
            "message": f"Cache flushed successfully",
            "pattern": pattern or "all",
            "keys_deleted": deleted_count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error flushing cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to flush cache: {str(e)}"
        )


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def list_cached_sessions(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of sessions to return")
):
    """
    List cached session data
    
    Args:
        limit: Maximum number of sessions to return
        
    Returns:
        List of cached session metadata
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        # Get session keys (lucid:session:*)
        session_keys = await redis_service.scan_keys("lucid:session:*", limit)
        
        sessions = []
        for key in session_keys:
            ttl = await redis_service.get_ttl(key)
            sessions.append({
                "key": key,
                "session_id": key.split(":")[-1],
                "ttl": ttl
            })
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error listing cached sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cached sessions: {str(e)}"
        )


@router.get("/rate-limits", response_model=List[Dict[str, Any]])
async def list_rate_limits(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of rate limits to return")
):
    """
    List cached rate limit data
    
    Args:
        limit: Maximum number of rate limits to return
        
    Returns:
        List of cached rate limit metadata
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        # Get rate limit keys (lucid:ratelimit:*)
        ratelimit_keys = await redis_service.scan_keys("lucid:ratelimit:*", limit)
        
        rate_limits = []
        for key in ratelimit_keys:
            ttl = await redis_service.get_ttl(key)
            value = await redis_service.get(key)
            rate_limits.append({
                "key": key,
                "identifier": key.split(":")[-1],
                "count": int(value) if value else 0,
                "ttl": ttl
            })
        
        return rate_limits
        
    except Exception as e:
        logger.error(f"Error listing rate limits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list rate limits: {str(e)}"
        )


@router.post("/clear-sessions", response_model=Dict[str, Any])
async def clear_session_cache():
    """
    Clear all cached session data
    
    Returns:
        Number of sessions cleared
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        # Get all session keys
        session_keys = await redis_service.scan_keys("lucid:session:*", limit=10000)
        
        # Delete session keys
        deleted_count = await redis_service.delete_keys(session_keys)
        
        return {
            "success": True,
            "message": f"Cleared {deleted_count} cached sessions",
            "sessions_cleared": deleted_count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error clearing session cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear session cache: {str(e)}"
        )


@router.post("/clear-rate-limits", response_model=Dict[str, Any])
async def clear_rate_limit_cache():
    """
    Clear all rate limit cache data
    
    Returns:
        Number of rate limits cleared
    """
    try:
        if not redis_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        # Get all rate limit keys
        ratelimit_keys = await redis_service.scan_keys("lucid:ratelimit:*", limit=10000)
        
        # Delete rate limit keys
        deleted_count = await redis_service.delete_keys(ratelimit_keys)
        
        return {
            "success": True,
            "message": f"Cleared {deleted_count} rate limits",
            "rate_limits_cleared": deleted_count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error clearing rate limit cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear rate limit cache: {str(e)}"
        )


# Helper functions
def calculate_hit_rate(hits: int, misses: int) -> float:
    """Calculate cache hit rate percentage"""
    total = hits + misses
    if total == 0:
        return 0.0
    return round((hits / total) * 100, 2)

