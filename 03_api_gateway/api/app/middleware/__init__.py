"""
Middleware Package

File: 03_api_gateway/api/app/middleware/__init__.py
Purpose: Custom middleware for request processing
"""

from ..middleware.auth import AuthMiddleware
from ..middleware.rate_limit import RateLimitMiddleware
from ..middleware.logging import LoggingMiddleware
from ..middleware.cors import CORSConfig
from api.app.utils.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "AuthMiddleware",
    "RateLimitMiddleware",
    "LoggingMiddleware",
    "CORSConfig",
    "get_logger",
    "logger"
]

