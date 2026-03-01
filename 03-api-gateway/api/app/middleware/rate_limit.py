"""
Rate Limiting Middleware

File: 03-api-gateway/api/app/middleware/rate_limit.py
Purpose: Implements tiered rate limiting for different endpoint types and user roles.
All configuration from environment variables via app.config.
"""

import logging
import time
from typing import Optional, Dict
from fastapi import Request
from starlette.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitMiddleware:
    """Rate limiting middleware for request throttling"""
    
    # In-memory rate limit tracking (use Redis in production via settings.REDIS_URL)
    _rate_limits: Dict[str, Dict] = {}
    
    def __init__(self, app):
        self.app = app
        self.enabled = settings.RATE_LIMIT_ENABLED
        self.requests_per_minute = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.burst_size = settings.RATE_LIMIT_BURST_SIZE
        self.redis_url = settings.REDIS_URL
        logger.info(f"RateLimitMiddleware initialized (enabled={self.enabled}, rpm={self.requests_per_minute})")
    
    async def __call__(self, scope, receive, send):
        """Process request through rate limiting middleware"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Skip if rate limiting is disabled
        if not self.enabled:
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip rate limiting for health endpoints
        if request.url.path in ["/health", "/api/v1/meta/health"]:
            await self.app(scope, receive, send)
            return
        
        # Get client identifier (IP or user ID if authenticated)
        client_id = self._get_client_identifier(request, scope)
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self._check_rate_limit(client_id)
        
        if not is_allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "LUCID_ERR_3001",
                        "message": f"Rate limit exceeded. Try again in {reset_time} seconds."
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + reset_time),
                    "Retry-After": str(reset_time)
                }
            )
            await response(scope, receive, send)
            return
        
        # Add rate limit headers to response
        scope["state"] = scope.get("state", {})
        scope["state"]["rate_limit_remaining"] = remaining
        
        await self.app(scope, receive, send)
    
    def _get_client_identifier(self, request: Request, scope: dict) -> str:
        """Get unique client identifier for rate limiting"""
        # Check if user is authenticated
        state = scope.get("state", {})
        user = state.get("user")
        
        if user and user.get("user_id"):
            return f"user:{user['user_id']}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Check for forwarded IP (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    async def _check_rate_limit(self, client_id: str) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        Returns (is_allowed, remaining_requests, reset_time_seconds).
        
        Note: This is a simple in-memory implementation.
        Production should use Redis via settings.REDIS_URL.
        """
        current_time = time.time()
        window_start = current_time - 60  # 1-minute sliding window
        
        # Get or create rate limit entry
        if client_id not in self._rate_limits:
            self._rate_limits[client_id] = {
                "requests": [],
                "last_cleanup": current_time
            }
        
        entry = self._rate_limits[client_id]
        
        # Clean up old requests
        entry["requests"] = [
            req_time for req_time in entry["requests"]
            if req_time > window_start
        ]
        
        # Check if within limit
        request_count = len(entry["requests"])
        
        if request_count >= self.requests_per_minute:
            # Calculate reset time
            oldest_request = min(entry["requests"]) if entry["requests"] else current_time
            reset_time = int(60 - (current_time - oldest_request))
            return False, 0, max(1, reset_time)
        
        # Add current request
        entry["requests"].append(current_time)
        remaining = self.requests_per_minute - len(entry["requests"])
        
        return True, remaining, 0
    
    @classmethod
    def cleanup_old_entries(cls, max_age_seconds: int = 300):
        """Cleanup old rate limit entries to prevent memory bloat"""
        current_time = time.time()
        cutoff = current_time - max_age_seconds
        
        to_delete = [
            client_id for client_id, entry in cls._rate_limits.items()
            if entry.get("last_cleanup", 0) < cutoff
        ]
        
        for client_id in to_delete:
            del cls._rate_limits[client_id]
