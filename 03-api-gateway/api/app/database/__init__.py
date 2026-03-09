"""
Database Package

File: 03-api-gateway/api/app/database/__init__.py
Purpose: Database connection and repository layer
"""

# Database imports will be added as they are implemented
# from .connection import init_database, get_database, get_redis
from app.database.connection import (
    init_database,
    get_database,
    get_redis,
    close_database,
    close_redis,
)

__all__ = [
    'init_database',
    'get_database',
    'get_redis',
    'close_database',
    'close_redis',
]

