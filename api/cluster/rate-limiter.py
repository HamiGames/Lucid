#!/usr/bin/env python3
"""
LUCID Rate Limiter - SPEC-1B Implementation
Rate limiting for API endpoints and services
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import redis
from fastapi import FastAPI, HTTPException, Request
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int = 10
    window_size: int = 60  # seconds

@dataclass
class RateLimitInfo:
    """Rate limit information"""
    limit: int
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None

class RateLimiter:
    """Rate limiter implementation"""
    
    def __init__(self):
        self.app = FastAPI(
            title="LUCID Rate Limiter",
            description="Rate limiting service for Lucid RDP APIs",
            version="1.0.0"
        )
        
        # Redis connection
        self.redis_client = None
        
        # Rate limit configurations
        self.configs: Dict[str, RateLimitConfig] = {
            'public': RateLimitConfig(
                requests_per_minute=100,
                requests_per_hour=1000,
                requests_per_day=10000,
                burst_limit=10
            ),
            'authenticated': RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=10000,
                requests_per_day=100000,
                burst_limit=50
            ),
            'admin': RateLimitConfig(
                requests_per_minute=10000,
                requests_per_hour=100000,
                requests_per_day=1000000,
                burst_limit=100
            ),
            'session_upload': RateLimitConfig(
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=1000,
                burst_limit=5
            ),
            'blockchain_query': RateLimitConfig(
                requests_per_minute=500,
                requests_per_hour=5000,
                requests_per_day=50000,
                burst_limit=25
            )
        }
        
        # Setup routes
        self.setup_routes()
        
        # Initialize connections
        asyncio.create_task(self.initialize_connections())
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "rate_limit_configs": len(self.configs)
            }
        
        @self.app.post("/api/v1/rate-limit/check")
        async def check_rate_limit(request: Request):
            """Check rate limit for a request"""
            try:
                data = await request.json()
                
                # Required fields
                client_id = data.get('client_id')
                endpoint = data.get('endpoint')
                tier = data.get('tier', 'public')
                
                if not client_id or not endpoint:
                    raise HTTPException(status_code=400, detail="Missing required fields")
                
                # Get rate limit config
                if tier not in self.configs:
                    raise HTTPException(status_code=400, detail="Invalid tier")
                
                config = self.configs[tier]
                
                # Check rate limit
                rate_limit_info = await self.check_rate_limit_internal(
                    client_id, endpoint, config
                )
                
                if rate_limit_info.remaining < 0:
                    return {
                        "status": "rate_limited",
                        "limit": rate_limit_info.limit,
                        "remaining": 0,
                        "reset_time": rate_limit_info.reset_time.isoformat(),
                        "retry_after": rate_limit_info.retry_after
                    }
                
                return {
                    "status": "allowed",
                    "limit": rate_limit_info.limit,
                    "remaining": rate_limit_info.remaining,
                    "reset_time": rate_limit_info.reset_time.isoformat()
                }
                
            except Exception as e:
                logger.error(f"Rate limit check error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/api/v1/rate-limit/increment")
        async def increment_rate_limit(request: Request):
            """Increment rate limit counter"""
            try:
                data = await request.json()
                
                client_id = data.get('client_id')
                endpoint = data.get('endpoint')
                tier = data.get('tier', 'public')
                
                if not client_id or not endpoint:
                    raise HTTPException(status_code=400, detail="Missing required fields")
                
                # Get rate limit config
                if tier not in self.configs:
                    raise HTTPException(status_code=400, detail="Invalid tier")
                
                config = self.configs[tier]
                
                # Increment counter
                await self.increment_rate_limit_internal(client_id, endpoint, config)
                
                return {
                    "status": "success",
                    "message": "Rate limit counter incremented"
                }
                
            except Exception as e:
                logger.error(f"Increment rate limit error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/rate-limit/stats/{client_id}")
        async def get_rate_limit_stats(client_id: str):
            """Get rate limit statistics for a client"""
            try:
                stats = await self.get_rate_limit_stats_internal(client_id)
                
                return {
                    "status": "success",
                    "client_id": client_id,
                    "stats": stats
                }
                
            except Exception as e:
                logger.error(f"Get rate limit stats error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/api/v1/rate-limit/reset/{client_id}")
        async def reset_rate_limit(client_id: str):
            """Reset rate limit for a client"""
            try:
                await self.reset_rate_limit_internal(client_id)
                
                return {
                    "status": "success",
                    "message": f"Rate limit reset for client {client_id}"
                }
                
            except Exception as e:
                logger.error(f"Reset rate limit error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    
    async def initialize_connections(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url('redis://localhost:6379')
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
    
    async def check_rate_limit_internal(
        self, 
        client_id: str, 
        endpoint: str, 
        config: RateLimitConfig
    ) -> RateLimitInfo:
        """Internal rate limit check"""
        try:
            current_time = int(time.time())
            window_start = current_time - config.window_size
            
            # Create key for this client/endpoint combination
            key = f"rate_limit:{client_id}:{endpoint}"
            
            # Get current count
            count = await self.redis_client.get(key)
            if count is None:
                count = 0
            else:
                count = int(count)
            
            # Check if limit exceeded
            if count >= config.requests_per_minute:
                # Calculate reset time
                reset_time = datetime.utcnow() + timedelta(seconds=config.window_size)
                retry_after = config.window_size - (current_time - window_start)
                
                return RateLimitInfo(
                    limit=config.requests_per_minute,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=retry_after
                )
            
            # Calculate remaining requests
            remaining = config.requests_per_minute - count - 1
            reset_time = datetime.utcnow() + timedelta(seconds=config.window_size)
            
            return RateLimitInfo(
                limit=config.requests_per_minute,
                remaining=remaining,
                reset_time=reset_time
            )
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Allow request if rate limiting fails
            return RateLimitInfo(
                limit=config.requests_per_minute,
                remaining=config.requests_per_minute,
                reset_time=datetime.utcnow() + timedelta(seconds=config.window_size)
            )
    
    async def increment_rate_limit_internal(
        self, 
        client_id: str, 
        endpoint: str, 
        config: RateLimitConfig
    ):
        """Internal rate limit increment"""
        try:
            current_time = int(time.time())
            window_start = current_time - config.window_size
            
            # Create key for this client/endpoint combination
            key = f"rate_limit:{client_id}:{endpoint}"
            
            # Increment counter
            await self.redis_client.incr(key)
            
            # Set expiration
            await self.redis_client.expire(key, config.window_size)
            
            # Also track hourly and daily limits
            await self._track_hourly_limit(client_id, endpoint, config)
            await self._track_daily_limit(client_id, endpoint, config)
            
        except Exception as e:
            logger.error(f"Rate limit increment error: {e}")
    
    async def _track_hourly_limit(
        self, 
        client_id: str, 
        endpoint: str, 
        config: RateLimitConfig
    ):
        """Track hourly rate limit"""
        try:
            current_time = int(time.time())
            hour_start = current_time - (current_time % 3600)  # Start of current hour
            
            key = f"rate_limit_hourly:{client_id}:{endpoint}:{hour_start}"
            
            await self.redis_client.incr(key)
            await self.redis_client.expire(key, 3600)  # Expire in 1 hour
            
        except Exception as e:
            logger.error(f"Hourly rate limit tracking error: {e}")
    
    async def _track_daily_limit(
        self, 
        client_id: str, 
        endpoint: str, 
        config: RateLimitConfig
    ):
        """Track daily rate limit"""
        try:
            current_time = int(time.time())
            day_start = current_time - (current_time % 86400)  # Start of current day
            
            key = f"rate_limit_daily:{client_id}:{endpoint}:{day_start}"
            
            await self.redis_client.incr(key)
            await self.redis_client.expire(key, 86400)  # Expire in 1 day
            
        except Exception as e:
            logger.error(f"Daily rate limit tracking error: {e}")
    
    async def get_rate_limit_stats_internal(self, client_id: str) -> Dict[str, Any]:
        """Get rate limit statistics for a client"""
        try:
            # Get all keys for this client
            pattern = f"rate_limit:{client_id}:*"
            keys = await self.redis_client.keys(pattern)
            
            stats = {
                "client_id": client_id,
                "endpoints": {},
                "total_requests": 0
            }
            
            for key in keys:
                # Extract endpoint from key
                key_parts = key.decode().split(':')
                if len(key_parts) >= 3:
                    endpoint = key_parts[2]
                    
                    # Get current count
                    count = await self.redis_client.get(key)
                    if count is not None:
                        count = int(count)
                        stats["endpoints"][endpoint] = count
                        stats["total_requests"] += count
            
            return stats
            
        except Exception as e:
            logger.error(f"Get rate limit stats error: {e}")
            return {"client_id": client_id, "endpoints": {}, "total_requests": 0}
    
    async def reset_rate_limit_internal(self, client_id: str):
        """Reset rate limit for a client"""
        try:
            # Get all keys for this client
            pattern = f"rate_limit:{client_id}:*"
            keys = await self.redis_client.keys(pattern)
            
            # Delete all rate limit keys
            if keys:
                await self.redis_client.delete(*keys)
            
            logger.info(f"Rate limit reset for client {client_id}")
            
        except Exception as e:
            logger.error(f"Reset rate limit error: {e}")
            raise

# Initialize rate limiter
rate_limiter = RateLimiter()

if __name__ == "__main__":
    uvicorn.run(
        "rate-limiter:rate_limiter.app",
        host="0.0.0.0",
        port=8083,
        reload=True,
        log_level="info"
    )
