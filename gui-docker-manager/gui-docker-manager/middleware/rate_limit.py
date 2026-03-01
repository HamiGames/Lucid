"""
Rate Limiting Middleware
File: gui-docker-manager/gui-docker-manager/middleware/rate_limit.py
"""

import logging
import time
from fastapi import Request, HTTPException
from typing import Callable, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if client can make request"""
        now = time.time()
        minute_ago = now - 60
        
        # Remove old requests
        self.requests[client_id] = [t for t in self.requests[client_id] if t > minute_ago]
        
        # Check limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False
        
        # Add new request
        self.requests[client_id].append(now)
        return True


rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next: Callable) -> any:
    """Rate limiting middleware"""
    client_id = request.client.host if request.client else "unknown"
    
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    response = await call_next(request)
    return response
