"""
Rate limiting middleware
"""

import logging
import time
from typing import Dict, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for API endpoints"""
    
    def __init__(self, app, requests_per_minute: int = 100, burst_size: int = 200):
        """Initialize rate limiting middleware"""
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        # Track requests per client IP
        self.client_requests: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting"""
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Initialize tracking for client if needed
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []
        
        # Get current time
        current_time = time.time()
        
        # Clean up old requests (older than 1 minute)
        self.client_requests[client_ip] = [
            req_time for req_time in self.client_requests[client_ip]
            if current_time - req_time < 60
        ]
        
        # Check rate limit
        requests_in_window = len(self.client_requests[client_ip])
        
        if requests_in_window >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Record this request
        self.client_requests[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        return response
