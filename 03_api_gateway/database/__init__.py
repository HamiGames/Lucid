"""
Lucid API Gateway - Database Package
Path: ..database
file: 03_api_gateway/database/__init__.py
the database calls the api gateway database
Database connection and utilities.
"""

from .connection import get_database, close_database
from api.app.utils.logging import get_logger

__all__ = [
    "get_database",
    "close_database",
    "get_logger"
]