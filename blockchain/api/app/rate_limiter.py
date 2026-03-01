"""
Rate Limiter Module

This module contains rate limiting utilities for the Blockchain API.
Implements token bucket and sliding window rate limiting algorithms.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)

@dataclass
class RateLimit:
    """Rate limit configuration."""
    limit: int
    window: int  # in seconds
    burst: Optional[int] = None  # burst limit for token bucket

@dataclass
class RateLimitResult:
    """Rate limit check result."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[int] = None

class TokenBucketRateLimiter:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, limit: int, window: int, burst: Optional[int] = None):
        self.limit = limit
        self.window = window
        self.burst = burst or limit
        self.tokens = self.burst
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def refill_tokens(self):
        """Refill tokens based on elapsed time."""
        current_time = time.time()
        elapsed = current_time - self.last_refill
        
        # Calculate tokens to add
        tokens_to_add = (elapsed / self.window) * self.limit
        
        # Add tokens up to burst limit
        self.tokens = min(self.burst, self.tokens + tokens_to_add)
        self.last_refill = current_time
    
    def consume_token(self) -> RateLimitResult:
        """Consume a token and return rate limit result."""
        with self.lock:
            self.refill_tokens()
            
            if self.tokens >= 1:
                self.tokens -= 1
                return RateLimitResult(
                    allowed=True,
                    remaining=int(self.tokens),
                    reset_time=self.last_refill + self.window
                )
            else:
                # Calculate retry after time
                retry_after = int((1 - self.tokens) * self.window / self.limit)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=self.last_refill + self.window,
                    retry_after=retry_after
                )

class SlidingWindowRateLimiter:
    """Sliding window rate limiter implementation."""
    
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def clean_old_requests(self):
        """Remove requests outside the window."""
        current_time = time.time()
        cutoff_time = current_time - self.window
        
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
    
    def consume_request(self) -> RateLimitResult:
        """Consume a request and return rate limit result."""
        with self.lock:
            current_time = time.time()
            self.clean_old_requests()
            
            if len(self.requests) < self.limit:
                self.requests.append(current_time)
                return RateLimitResult(
                    allowed=True,
                    remaining=self.limit - len(self.requests),
                    reset_time=current_time + self.window
                )
            else:
                # Calculate retry after time
                oldest_request = self.requests[0]
                retry_after = int(oldest_request + self.window - current_time)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=oldest_request + self.window,
                    retry_after=max(0, retry_after)
                )

class RateLimiterManager:
    """Rate limiter manager for different endpoint categories."""
    
    def __init__(self):
        import os
        # Load rate limit configurations from environment variables
        self.limiters: Dict[str, Dict[str, Any]] = {
            "blockchain_queries": {
                "limit": int(os.getenv("RATE_LIMIT_BLOCKCHAIN_QUERIES", "500")),
                "window": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
                "type": os.getenv("RATE_LIMIT_TYPE", "sliding_window")
            },
            "transaction_submission": {
                "limit": int(os.getenv("RATE_LIMIT_TRANSACTION_SUBMISSION", "100")),
                "window": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
                "type": os.getenv("RATE_LIMIT_TYPE", "sliding_window")
            },
            "session_anchoring": {
                "limit": int(os.getenv("RATE_LIMIT_SESSION_ANCHORING", "50")),
                "window": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
                "type": os.getenv("RATE_LIMIT_TYPE", "sliding_window")
            },
            "consensus_operations": {
                "limit": int(os.getenv("RATE_LIMIT_CONSENSUS_OPERATIONS", "200")),
                "window": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
                "type": os.getenv("RATE_LIMIT_TYPE", "sliding_window")
            },
            "merkle_operations": {
                "limit": int(os.getenv("RATE_LIMIT_MERKLE_OPERATIONS", "300")),
                "window": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
                "type": os.getenv("RATE_LIMIT_TYPE", "sliding_window")
            }
        }
        
        # Client-specific rate limiters
        self.client_limiters: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.lock = threading.Lock()
    
    def get_limiter_for_category(self, category: str, client_id: str) -> Any:
        """Get rate limiter for a specific category and client."""
        with self.lock:
            if client_id not in self.client_limiters:
                self.client_limiters[client_id] = {}
            
            if category not in self.client_limiters[client_id]:
                import os
                config = self.limiters.get(category, {
                    "limit": int(os.getenv("RATE_LIMIT_DEFAULT", "100")),
                    "window": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
                    "type": os.getenv("RATE_LIMIT_TYPE", "sliding_window")
                })
                
                if config["type"] == "token_bucket":
                    limiter = TokenBucketRateLimiter(
                        config["limit"],
                        config["window"],
                        config.get("burst")
                    )
                else:
                    limiter = SlidingWindowRateLimiter(
                        config["limit"],
                        config["window"]
                    )
                
                self.client_limiters[client_id][category] = limiter
            
            return self.client_limiters[client_id][category]
    
    def check_rate_limit(self, category: str, client_id: str) -> RateLimitResult:
        """Check rate limit for a client and category."""
        limiter = self.get_limiter_for_category(category, client_id)
        
        if isinstance(limiter, TokenBucketRateLimiter):
            return limiter.consume_token()
        else:
            return limiter.consume_request()
    
    def get_rate_limit_status(self, category: str, client_id: str) -> Dict[str, Any]:
        """Get current rate limit status for a client and category."""
        limiter = self.get_limiter_for_category(category, client_id)
        config = self.limiters.get(category, {})
        
        if isinstance(limiter, TokenBucketRateLimiter):
            with limiter.lock:
                limiter.refill_tokens()
                return {
                    "category": category,
                    "client_id": client_id,
                    "limit": config.get("limit", 100),
                    "window": config.get("window", 60),
                    "tokens_remaining": int(limiter.tokens),
                    "burst_limit": limiter.burst,
                    "type": "token_bucket"
                }
        else:
            with limiter.lock:
                limiter.clean_old_requests()
                return {
                    "category": category,
                    "client_id": client_id,
                    "limit": config.get("limit", 100),
                    "window": config.get("window", 60),
                    "requests_remaining": config.get("limit", 100) - len(limiter.requests),
                    "type": "sliding_window"
                }
    
    def update_rate_limit_config(self, category: str, config: Dict[str, Any]):
        """Update rate limit configuration for a category."""
        with self.lock:
            self.limiters[category] = config
            
            # Clear existing limiters for this category
            for client_id in self.client_limiters:
                if category in self.client_limiters[client_id]:
                    del self.client_limiters[client_id][category]
    
    def get_all_rate_limit_status(self) -> Dict[str, Any]:
        """Get rate limit status for all categories and clients."""
        with self.lock:
            result = {
                "categories": {},
                "clients": {}
            }
            
            # Category configurations
            for category, config in self.limiters.items():
                result["categories"][category] = config
            
            # Client statuses
            for client_id, categories in self.client_limiters.items():
                result["clients"][client_id] = {}
                for category in categories:
                    result["clients"][client_id][category] = self.get_rate_limit_status(category, client_id)
            
            return result
    
    def cleanup_old_clients(self, max_age: int = 3600):
        """Clean up rate limiters for old clients."""
        current_time = time.time()
        
        with self.lock:
            clients_to_remove = []
            
            for client_id, categories in self.client_limiters.items():
                # Check if client has been active recently
                last_activity = 0
                for category, limiter in categories.items():
                    if isinstance(limiter, SlidingWindowRateLimiter):
                        if limiter.requests:
                            last_activity = max(last_activity, limiter.requests[-1])
                    elif isinstance(limiter, TokenBucketRateLimiter):
                        last_activity = max(last_activity, limiter.last_refill)
                
                if current_time - last_activity > max_age:
                    clients_to_remove.append(client_id)
            
            for client_id in clients_to_remove:
                del self.client_limiters[client_id]

# Global rate limiter manager
rate_limiter_manager = RateLimiterManager()

class RateLimitMiddleware:
    """Rate limiting middleware for FastAPI."""
    
    def __init__(self, rate_limiter_manager: RateLimiterManager):
        self.rate_limiter_manager = rate_limiter_manager
    
    def get_client_id(self, request) -> str:
        """Get client identifier from request."""
        # Try to get from X-Forwarded-For header first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to client IP
        return request.client.host
    
    def get_rate_limit_category(self, path: str) -> str:
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
    
    async def check_rate_limit(self, request) -> RateLimitResult:
        """Check rate limit for a request."""
        client_id = self.get_client_id(request)
        category = self.get_rate_limit_category(request.url.path)
        
        return self.rate_limiter_manager.check_rate_limit(category, client_id)
    
    def get_rate_limit_headers(self, result: RateLimitResult) -> Dict[str, str]:
        """Get rate limit headers for response."""
        headers = {
            "X-RateLimit-Limit": str(result.remaining + (1 if result.allowed else 0)),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(int(result.reset_time))
        }
        
        if result.retry_after is not None:
            headers["Retry-After"] = str(result.retry_after)
        
        return headers
