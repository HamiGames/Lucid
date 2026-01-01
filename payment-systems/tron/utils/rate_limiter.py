"""
LUCID Payment Systems - TRON Client Rate Limiter Module
Rate limiting implementation using token bucket algorithm
Following architecture patterns from build/docs/
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 100
    burst_size: int = 200
    window_seconds: int = 60
    enabled: bool = True


class RateLimitExceeded(Exception):
    """Rate limit exceeded"""
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after:.2f} seconds")


class RateLimiter:
    """
    Token bucket rate limiter implementation
    
    Algorithm:
    - Tokens are added at a constant rate (requests_per_minute / window_seconds)
    - Each request consumes one token
    - Burst size limits maximum tokens
    - If no tokens available, request is rejected
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = float(config.burst_size)
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    def _add_tokens(self):
        """Add tokens based on elapsed time"""
        if not self.config.enabled:
            return
        
        now = time.time()
        elapsed = now - self.last_update
        
        # Calculate tokens to add (rate per second)
        tokens_per_second = self.config.requests_per_minute / self.config.window_seconds
        tokens_to_add = elapsed * tokens_per_second
        
        # Add tokens, but cap at burst size
        self.tokens = min(self.config.burst_size, self.tokens + tokens_to_add)
        self.last_update = now
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens
        
        Args:
            tokens: Number of tokens to acquire (default: 1)
            
        Returns:
            True if tokens acquired, False if rate limit exceeded
        """
        if not self.config.enabled:
            return True
        
        async with self._lock:
            self._add_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                # Calculate retry after
                tokens_needed = tokens - self.tokens
                tokens_per_second = self.config.requests_per_minute / self.config.window_seconds
                retry_after = tokens_needed / tokens_per_second
                
                logger.warning(
                    f"Rate limit exceeded. Tokens available: {self.tokens:.2f}, "
                    f"Requested: {tokens}. Retry after {retry_after:.2f}s"
                )
                return False
    
    async def wait(self, tokens: int = 1) -> float:
        """
        Wait until tokens are available
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds (0 if immediate)
        """
        if not self.config.enabled:
            return 0.0
        
        async with self._lock:
            self._add_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            
            # Calculate wait time
            tokens_needed = tokens - self.tokens
            tokens_per_second = self.config.requests_per_minute / self.config.window_seconds
            wait_time = tokens_needed / tokens_per_second
            
            # Wait
            await asyncio.sleep(wait_time)
            
            # Acquire tokens after wait
            self._add_tokens()
            self.tokens -= tokens
            
            return wait_time
    
    def get_stats(self) -> Dict[str, float]:
        """Get rate limiter statistics"""
        self._add_tokens()
        return {
            "tokens_available": self.tokens,
            "tokens_max": self.config.burst_size,
            "requests_per_minute": self.config.requests_per_minute,
            "window_seconds": self.config.window_seconds,
        }


class RateLimiterManager:
    """Manager for multiple rate limiters"""
    
    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = asyncio.Lock()
    
    async def get_limiter(
        self,
        name: str,
        config: Optional[RateLimitConfig] = None
    ) -> RateLimiter:
        """Get or create rate limiter"""
        async with self._lock:
            if name not in self._limiters:
                if config is None:
                    config = RateLimitConfig()
                self._limiters[name] = RateLimiter(config)
            return self._limiters[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all rate limiters"""
        return {name: limiter.get_stats() for name, limiter in self._limiters.items()}


# Global rate limiter manager
_limiter_manager: Optional[RateLimiterManager] = None


def get_rate_limiter_manager() -> RateLimiterManager:
    """Get or create global rate limiter manager"""
    global _limiter_manager
    if _limiter_manager is None:
        _limiter_manager = RateLimiterManager()
    return _limiter_manager

