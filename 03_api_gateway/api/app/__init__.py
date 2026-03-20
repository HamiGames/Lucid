"""
API Gateway Application Package
File: 03_api_gateway/api/app/__init__.py
Purpose: Main application package initialization
"""
from api.app.middleware.auth import AuthMiddleware
from api.app.utils.logging import get_logger, setup_logging

__all__ = [
    'AuthMiddleware', 'get_logger', 'setup_logging'
]