"""
Middleware Package

File: 03_api_gateway/api/app/middleware/__init__.py
Purpose: Custom middleware for request processing
"""

from api.app.middleware.auth import AuthMiddleware
from api.app.middleware.rate_limit import RateLimitMiddleware
from api.app.middleware.logging import api.app.utils.logging as loggingMiddleware
from api.app.middleware.cors import CORSConfig
from api.app.utils.logging import get_logger
logger = get_logger(__name__)
__all__ = [
    "AuthMiddleware",
    "RateLimitMiddleware",
    "LoggingMiddleware",
    "CORSConfig",
    "logger",
]

