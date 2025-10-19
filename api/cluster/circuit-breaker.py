#!/usr/bin/env python3
"""
LUCID Circuit Breaker - SPEC-1B Implementation
Circuit breaker pattern for service resilience
"""

import asyncio
import logging
import time
from typing import Dict, Any, Callable, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3
    timeout: int = 30

@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    last_success_time: Optional[datetime]
    total_requests: int
    total_failures: int

class CircuitBreaker:
    """Circuit breaker implementation"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.total_requests = 0
        self.total_failures = 0
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        async with self._lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")
            
            # Execute function
            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
                
            except Exception as e:
                await self._on_failure()
                raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if self.last_failure_time is None:
            return True
        
        return datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.config.recovery_timeout)
    
    async def _on_success(self):
        """Handle successful call"""
        self.total_requests += 1
        self.last_success_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker {self.name} closed after successful calls")
        else:
            # Reset failure count on success
            self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed call"""
        self.total_requests += 1
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            # If we're in half-open state and get a failure, go back to open
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} opened again after failure in half-open state")
        elif self.failure_count >= self.config.failure_threshold:
            # Open the circuit
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} opened after {self.failure_count} failures")
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics"""
        return CircuitBreakerStats(
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            last_failure_time=self.last_failure_time,
            last_success_time=self.last_success_time,
            total_requests=self.total_requests,
            total_failures=self.total_failures
        )
    
    def reset(self):
        """Reset circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        logger.info(f"Circuit breaker {self.name} manually reset")

class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class CircuitBreakerManager:
    """Manager for multiple circuit breakers"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.default_config = CircuitBreakerConfig()
    
    def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create circuit breaker"""
        if name not in self.breakers:
            if config is None:
                config = self.default_config
            self.breakers[name] = CircuitBreaker(name, config)
        
        return self.breakers[name]
    
    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers"""
        return {name: breaker.get_stats() for name, breaker in self.breakers.items()}
    
    def reset_breaker(self, name: str):
        """Reset specific circuit breaker"""
        if name in self.breakers:
            self.breakers[name].reset()
    
    def reset_all_breakers(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()

# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()

# Decorator for easy use
def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator for circuit breaker protection"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            breaker = circuit_breaker_manager.get_breaker(name, config)
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator

# Example usage
if __name__ == "__main__":
    # Example circuit breaker usage
    async def example_service_call():
        """Example service call that might fail"""
        # Simulate service call
        await asyncio.sleep(1)
        
        # Simulate random failure
        import random
        if random.random() < 0.3:  # 30% failure rate
            raise Exception("Service call failed")
        
        return "Success"
    
    async def test_circuit_breaker():
        """Test circuit breaker functionality"""
        breaker = circuit_breaker_manager.get_breaker(
            "example_service",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=10,
                success_threshold=2
            )
        )
        
        # Test successful calls
        for i in range(5):
            try:
                result = await breaker.call(example_service_call)
                print(f"Call {i+1}: {result}")
            except Exception as e:
                print(f"Call {i+1}: {e}")
            
            # Print stats
            stats = breaker.get_stats()
            print(f"Stats: {stats.state.value}, failures: {stats.failure_count}, successes: {stats.success_count}")
            
            await asyncio.sleep(1)
    
    # Run test
    asyncio.run(test_circuit_breaker())
