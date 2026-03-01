"""
Lucid API Gateway - Database Package
Database connection and utilities.
"""

from .connection import get_database, close_database

__all__ = [
    'get_database',
    'close_database',
]

