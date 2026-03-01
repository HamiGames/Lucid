"""
Rate Limiting Middleware

This module contains rate limiting middleware for the Blockchain API.
Implements token bucket and sliding window rate limiting algorithms.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time
from collections import defaultdict
import logging

from ..rate_limiter import rate_limiter_manager

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for API requests."""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = rate_limiter_manager
    
    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiting middleware."""
        
        # Skip rate limiting for health checks
        if self._is_health_check(request.url.path):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Determine rate limit category
        category = self._get_rate_limit_category(request.url.path)
        
        # Check rate limit
        try:
            rate_limit_result = self.rate_limiter.check_rate_limit(category, client_id)
            
            if not rate_limit_result.allowed:
                logger.warning(f"Rate limit exceeded for {client_id} on {category}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {category}. Try again in {rate_limit_result.retry_after} seconds.",
                    headers={
                        "X-RateLimit-Limit": str(rate_limit_result.remaining + 1),
                        "X-RateLimit-Remaining": str(rate_limit_result.remaining),
                        "X-RateLimit-Reset": str(int(rate_limit_result.reset_time)),
                        "Retry-After": str(rate_limit_result.retry_after)
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(rate_limit_result.remaining + 1)
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_result.remaining)
            response.headers["X-RateLimit-Reset"] = str(int(rate_limit_result.reset_time))
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting if there's an error
            return await call_next(request)
    
    def _is_health_check(self, path: str) -> bool:
        """Check if request is a health check."""
        health_endpoints = [
            "/health",
            "/api/v1/health"
        ]
        
        return any(path.startswith(endpoint) for endpoint in health_endpoints)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try to get from X-Forwarded-For header first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to client IP
        return request.client.host
    
    def _get_rate_limit_category(self, path: str) -> str:
        """Determine rate limit category based on request path."""
        if path.startswith("/api/v1/chain/"):
            return "blockchain_queries"
        elif path.startswith("/api/v1/blocks"):
            return "blockchain_queries"
        elif path.startswith("/api/v1/transactions"):
            return "transaction_submission"
        elif path.startswith("/api/v1/anchoring"):
            return "session_anchoring"
        elif path.startswith("/api/v1/consensus"):
            return "consensus_operations"
        elif path.startswith("/api/v1/merkle"):
            return "merkle_operations"
        else:
            return "blockchain_queries"  # Default category