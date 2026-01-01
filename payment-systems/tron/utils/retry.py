"""
LUCID Payment Systems - TRON Client Retry Module
Retry logic with exponential backoff and jitter
Following architecture patterns from build/docs/
"""

import asyncio
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Callable, Any, Optional, Type, Tuple, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Retry configuration - defaults from environment variables"""
    max_retries: int = None
    initial_delay: float = None
    max_delay: float = None
    exponential_base: float = None
    jitter: bool = None
    jitter_range: Tuple[float, float] = None
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    retry_on_status_codes: Optional[List[int]] = None
    
    def __post_init__(self):
        """Initialize defaults from environment variables if not provided"""
        if self.max_retries is None:
            self.max_retries = int(os.getenv("RETRY_MAX_RETRIES", "3"))
        if self.initial_delay is None:
            self.initial_delay = float(os.getenv("RETRY_INITIAL_DELAY", "1.0"))
        if self.max_delay is None:
            self.max_delay = float(os.getenv("RETRY_MAX_DELAY", "60.0"))
        if self.exponential_base is None:
            self.exponential_base = float(os.getenv("RETRY_EXPONENTIAL_BASE", "2.0"))
        if self.jitter is None:
            self.jitter = os.getenv("RETRY_JITTER", "true").lower() == "true"
        if self.jitter_range is None:
            jitter_min = float(os.getenv("RETRY_JITTER_MIN", "0.0"))
            jitter_max = float(os.getenv("RETRY_JITTER_MAX", "0.1"))
            self.jitter_range = (jitter_min, jitter_max)


class RetryableError(Exception):
    """Error that can be retried"""
    pass


class MaxRetriesExceeded(Exception):
    """Maximum retries exceeded"""
    def __init__(self, last_exception: Exception, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(f"Max retries ({attempts}) exceeded: {str(last_exception)}")


def _calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for retry attempt"""
    # Exponential backoff
    delay = config.initial_delay * (config.exponential_base ** attempt)
    
    # Cap at max delay
    delay = min(delay, config.max_delay)
    
    # Add jitter if enabled
    if config.jitter:
        jitter_min, jitter_max = config.jitter_range
        jitter = random.uniform(jitter_min, jitter_max) * delay
        delay = delay + jitter
    
    return delay


def _is_retryable(exception: Exception, config: RetryConfig) -> bool:
    """Check if exception is retryable"""
    return isinstance(exception, config.retryable_exceptions)


async def retry_with_backoff(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Execute function with retry logic and exponential backoff
    
    Args:
        func: Async or sync function to execute
        *args: Function arguments
        config: Retry configuration (uses default if None)
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        MaxRetriesExceeded: If max retries exceeded
        Exception: Last exception if all retries failed
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success
            if attempt > 0:
                logger.info(f"Retry succeeded after {attempt} attempts")
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if retryable
            if not _is_retryable(e, config):
                logger.debug(f"Exception not retryable: {type(e).__name__}")
                raise e
            
            # Check if last attempt
            if attempt >= config.max_retries:
                logger.error(f"Max retries ({config.max_retries}) exceeded for {func.__name__}")
                raise MaxRetriesExceeded(e, attempt + 1)
            
            # Calculate delay
            delay = _calculate_delay(attempt, config)
            
            logger.warning(
                f"Retry attempt {attempt + 1}/{config.max_retries} for {func.__name__}: "
                f"{type(e).__name__}: {str(e)}. Retrying in {delay:.2f}s"
            )
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # Should not reach here, but handle just in case
    raise MaxRetriesExceeded(last_exception, config.max_retries + 1)


class RetryDecorator:
    """Decorator for retry logic"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def __call__(self, func: Callable) -> Callable:
        """Apply retry decorator to function"""
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(func, *args, config=self.config, **kwargs)
        
        return wrapper


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retry logic
    
    Usage:
        @retry(max_retries=3, initial_delay=1.0)
        async def my_function():
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions
    )
    
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(func, *args, config=config, **kwargs)
        return wrapper
    
    return decorator

