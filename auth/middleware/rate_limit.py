"""
Lucid Authentication Service - Rate Limiting Middleware
Tiered rate limiting based on authentication status
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime
import redis.asyncio as redis
from typing import Optional
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with tiered limits
    
    Tiers:
    - Public (unauthenticated): 100 requests/minute
    - Authenticated: 1000 requests/minute
    - Admin: 10000 requests/minute
    """
    
    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        self.redis_client = redis_client
        self.enabled = settings.RATE_LIMIT_ENABLED
        
        # Rate limits (requests per minute)
        self.limits = {
            "public": settings.RATE_LIMIT_PUBLIC,
            "authenticated": settings.RATE_LIMIT_AUTHENTICATED,
            "admin": settings.RATE_LIMIT_ADMIN
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        if not self.enabled:
            return await call_next(request)
        
        # Initialize Redis client if needed
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URI,
                    decode_responses=True
                )
            except Exception as e:
                logger.error(f"Failed to initialize Redis for rate limiting: {e}")
                # Continue without rate limiting if Redis unavailable
                return await call_next(request)
        
        # Determine client identifier
        client_id = self.get_client_identifier(request)
        
        # Determine rate limit tier
        limit = self.get_rate_limit(request)
        
        # Check rate limit
        try:
            is_allowed, current_count, reset_time = await self.check_rate_limit(
                client_id,
                limit
            )
            
            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for {client_id}: {current_count}/{limit} requests"
                )
                return self.rate_limit_response(
                    limit,
                    current_count,
                    reset_time
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(limit - current_count)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}", exc_info=True)
            # Continue without rate limiting on error
            return await call_next(request)
    
    def get_client_identifier(self, request: Request) -> str:
        """
        Get client identifier for rate limiting
        
        Uses user_id if authenticated, otherwise uses IP address
        """
        # Check if user is authenticated (set by AuthMiddleware)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Use IP address for unauthenticated requests
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def get_rate_limit(self, request: Request) -> int:
        """Determine rate limit based on authentication status and role"""
        
        # Check if user is authenticated
        if not hasattr(request.state, "authenticated") or not request.state.authenticated:
            return self.limits["public"]
        
        # Check user role
        role = getattr(request.state, "role", None)
        if role in ["ADMIN", "SUPER_ADMIN"]:
            return self.limits["admin"]
        
        return self.limits["authenticated"]
    
    async def check_rate_limit(self, client_id: str, limit: int) -> tuple:
        """
        Check if client has exceeded rate limit
        
        Returns:
            (is_allowed, current_count, reset_time)
        """
        # Use sliding window rate limiting
        now = datetime.utcnow()
        current_minute = now.strftime("%Y-%m-%d %H:%M")
        key = f"ratelimit:{client_id}:{current_minute}"
        
        # Increment counter
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)  # Expire after 1 minute
        results = await pipe.execute()
        
        current_count = results[0]
        
        # Calculate reset time (end of current minute)
        reset_time = int(now.timestamp()) + (60 - now.second)
        
        is_allowed = current_count <= limit
        
        return is_allowed, current_count, reset_time
    
    def rate_limit_response(self, limit: int, current_count: int, reset_time: int) -> JSONResponse:
        """Generate rate limit exceeded response"""
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "LUCID_ERR_3001",
                    "message": f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
                    "details": {
                        "limit": limit,
                        "current": current_count,
                        "reset_at": reset_time
                    },
                    "service": "auth-service",
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(reset_time - int(datetime.utcnow().timestamp()))
            }
        )

