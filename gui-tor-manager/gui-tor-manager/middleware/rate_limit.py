"""
Rate Limiting Middleware for GUI Tor Manager
Implements basic rate limiting to prevent abuse
"""

from typing import Callable, Dict
import time
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Simple in-memory rate limiter (in production, use Redis)
# Format: {client_ip: [timestamp1, timestamp2, ...]}
_rate_limit_store: Dict[str, list] = {}

# Rate limit configuration
REQUESTS_PER_MINUTE = 100
CLEANUP_INTERVAL = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for basic rate limiting"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests"""
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for health check endpoint
        if request.url.path == "/health":
            return await call_next(request)
        
        current_time = time.time()
        
        # Initialize client record if not exists
        if client_ip not in _rate_limit_store:
            _rate_limit_store[client_ip] = []
        
        # Clean old timestamps (older than 1 minute)
        _rate_limit_store[client_ip] = [
            ts for ts in _rate_limit_store[client_ip]
            if current_time - ts < CLEANUP_INTERVAL
        ]
        
        # Check rate limit
        if len(_rate_limit_store[client_ip]) >= REQUESTS_PER_MINUTE:
            logger.warning(
                f"Rate limit exceeded for {client_ip}",
                extra={"client_ip": client_ip, "request_count": len(_rate_limit_store[client_ip])}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )
        
        # Add current request timestamp
        _rate_limit_store[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = REQUESTS_PER_MINUTE - len(_rate_limit_store[client_ip])
        response.headers["X-RateLimit-Limit"] = str(REQUESTS_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + CLEANUP_INTERVAL))
        
        return response
