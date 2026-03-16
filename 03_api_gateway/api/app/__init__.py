"""
API Gateway Application Package
File: 03_api_gateway/api/app/__init__.py
Purpose: Main application package initialization
"""
from .utils.logging import get_logger

__version__ = "1.0.0"
__author__ = "Lucid Development Team"

__all__ = [
    "get_logger"
]