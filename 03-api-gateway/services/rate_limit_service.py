"""
Lucid API Gateway - Rate Limiting Service
Handles rate limiting with Redis backend.

File: 03-api-gateway/services/rate_limit_service.py
Lines: ~200
Purpose: Rate limiting service
Dependencies: Redis
"""

import redis.asyncio as redis
import logging
from typing import Optional, Tuple
from datetime import datetime
from enum import Enum

from ..config import settings

logger = logging.getLogger(__name__)


class RateLimitTier(Enum):
    """Rate limit tiers based on user authentication."""
    PUBLIC = "public"            # 100 req/min
    AUTHENTICATED = "authenticated"  # 1000 req/min
    ADMIN = "admin"              # 10000 req/min


class RateLimitExceeded(Exception):
    """Rate limit exceeded exception."""
    pass


class RateLimitService:
    """
    Rate limiting service with Redis backend.
    
    Implements:
    - Tiered rate limiting (100/1000/10000 req/min)
    - Sliding window algorithm
    - Per-user and per-IP tracking
    """
    
    # Rate limits per tier (requests per minute)
    RATE_LIMITS = {
        RateLimitTier.PUBLIC: 100,
        RateLimitTier.AUTHENTICATED: 1000,
        RateLimitTier.ADMIN: 10000,
    }
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.redis_uri = settings.REDIS_URI
        
    async def initialize(self):
        """Initialize Redis connection."""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_uri,
                encoding="utf-8",
                decode_responses=True
            )
            
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            
    async def check_rate_limit(
        self, 
        identifier: str, 
        tier: RateLimitTier = RateLimitTier.PUBLIC
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Client identifier (IP or user_id)
            tier: Rate limit tier
            
        Returns:
            Tuple of (allowed, remaining, reset_time)
            
        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        await self.initialize()
        
        try:
            # Get rate limit for tier
            limit = self.RATE_LIMITS[tier]
            window = 60  # 1 minute window
            
            # Redis key for rate limiting
            key = f"rate_limit:{tier.value}:{identifier}"
            
            # Get current timestamp
            now = datetime.utcnow().timestamp()
            window_start = now - window
            
            # Remove old entries outside the window
            await self.redis_client.zremrangebyscore(
                key, 
                0, 
                window_start
            )
            
            # Count requests in current window
            request_count = await self.redis_client.zcard(key)
            
            # Check if limit exceeded
            if request_count >= limit:
                # Calculate reset time
                oldest = await self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = int(oldest[0][1] + window)
                else:
                    reset_time = int(now + window)
                    
                logger.warning(
                    f"Rate limit exceeded for {identifier} "
                    f"(tier: {tier.value}, limit: {limit})"
                )
                return False, 0, reset_time
                
            # Add current request
            await self.redis_client.zadd(key, {str(now): now})
            
            # Set expiration on key
            await self.redis_client.expire(key, window)
            
            # Calculate remaining requests
            remaining = limit - request_count - 1
            reset_time = int(now + window)
            
            return True, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow the request (fail open)
            return True, 0, 0
            
    async def get_rate_limit_info(
        self, 
        identifier: str, 
        tier: RateLimitTier
    ) -> dict:
        """
        Get rate limit information for identifier.
        
        Args:
            identifier: Client identifier
            tier: Rate limit tier
            
        Returns:
            Dictionary with rate limit info
        """
        await self.initialize()
        
        try:
            limit = self.RATE_LIMITS[tier]
            window = 60
            
            key = f"rate_limit:{tier.value}:{identifier}"
            
            now = datetime.utcnow().timestamp()
            window_start = now - window
            
            # Clean old entries
            await self.redis_client.zremrangebyscore(
                key, 
                0, 
                window_start
            )
            
            # Get current count
            request_count = await self.redis_client.zcard(key)
            
            # Calculate remaining
            remaining = max(0, limit - request_count)
            
            # Get oldest entry for reset time
            oldest = await self.redis_client.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset_time = int(oldest[0][1] + window)
            else:
                reset_time = int(now + window)
                
            return {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "tier": tier.value
            }
            
        except Exception as e:
            logger.error(f"Get rate limit info error: {e}")
            return {
                "limit": 0,
                "remaining": 0,
                "reset": 0,
                "tier": tier.value
            }
            
    async def reset_rate_limit(self, identifier: str, tier: RateLimitTier):
        """
        Reset rate limit for identifier (admin function).
        
        Args:
            identifier: Client identifier
            tier: Rate limit tier
        """
        await self.initialize()
        
        try:
            key = f"rate_limit:{tier.value}:{identifier}"
            await self.redis_client.delete(key)
            logger.info(f"Reset rate limit for {identifier} (tier: {tier.value})")
            
        except Exception as e:
            logger.error(f"Reset rate limit error: {e}")


# Global rate limit service instance
rate_limit_service = RateLimitService()

