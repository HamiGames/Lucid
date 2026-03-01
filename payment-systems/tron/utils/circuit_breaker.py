"""
LUCID Payment Systems - TRON Client Circuit Breaker Module
Circuit breaker pattern implementation for resilient service calls
Following architecture patterns from build/docs/
"""

import asyncio
import logging
import os
import time
from enum import Enum
from dataclasses import dataclass
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration - defaults from environment variables"""
    failure_threshold: int = None
    recovery_timeout: int = None
    success_threshold: int = None
    half_open_max_calls: int = None
    name: str = "default"
    
    def __post_init__(self):
        """Initialize defaults from environment variables if not provided"""
        if self.failure_threshold is None:
            self.failure_threshold = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
        if self.recovery_timeout is None:
            self.recovery_timeout = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))
        if self.success_threshold is None:
            self.success_threshold = int(os.getenv("CIRCUIT_BREAKER_SUCCESS_THRESHOLD", "2"))
        if self.half_open_max_calls is None:
            self.half_open_max_calls = int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS", "3"))


class CircuitBreakerError(Exception):
    """Circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting service calls
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing fast, requests rejected immediately
    - HALF_OPEN: Testing recovery, limited requests allowed
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        self.total_requests = 0
        self.total_failures = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            self.total_requests += 1
            
            # Check if circuit is open
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker {self.config.name}: Attempting recovery (HALF_OPEN)")
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    self.half_open_calls = 0
                else:
                    self.total_failures += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker {self.config.name} is OPEN. "
                        f"Last failure: {self.last_failure_time}"
                    )
            
            # Check half-open state limits
            if self.state == CircuitBreakerState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    logger.warning(f"Circuit breaker {self.config.name}: HALF_OPEN limit reached, opening")
                    self.state = CircuitBreakerState.OPEN
                    self.last_failure_time = datetime.now()
                    self.total_failures += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker {self.config.name} HALF_OPEN limit exceeded"
                    )
                self.half_open_calls += 1
            
            # Execute function
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                await self._on_success()
                return result
                
            except Exception as e:
                await self._on_failure()
                raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout
    
    async def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker {self.config.name}: Recovery successful, closing")
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.half_open_calls = 0
                self.last_failure_time = None
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Failure in half-open state, open circuit
            logger.warning(f"Circuit breaker {self.config.name}: Failure in HALF_OPEN, opening")
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            self.half_open_calls = 0
        elif self.state == CircuitBreakerState.CLOSED:
            # Check if threshold reached
            if self.failure_count >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit breaker {self.config.name}: Failure threshold ({self.config.failure_threshold}) "
                    f"reached, opening circuit"
                )
                self.state = CircuitBreakerState.OPEN
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "half_open_calls": self.half_open_calls,
        }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        logger.info(f"Circuit breaker {self.config.name}: Manual reset")
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        self.last_failure_time = None


class CircuitBreakerManager:
    """Manager for multiple circuit breakers"""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create circuit breaker"""
        async with self._lock:
            if name not in self._breakers:
                if config is None:
                    config = CircuitBreakerConfig(name=name)
                else:
                    config.name = name
                self._breakers[name] = CircuitBreaker(config)
            return self._breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}


# Global circuit breaker manager
_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get or create global circuit breaker manager"""
    global _breaker_manager
    if _breaker_manager is None:
        _breaker_manager = CircuitBreakerManager()
    return _breaker_manager

