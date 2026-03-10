"""
Database Package

File: 03_api_gateway/api/app/database/__init__.py
Purpose: Database connection and repository layer
"""

# Database imports will be added as they are implemented
# from .connection import init_database, get_database, get_redis
from api.app.database.connection import (
    init_database, get_database, get_redis, close_database, close_redis, 
    _wait_for_tor_proxy, _wait_for_mongodb, _wait_for_redis, _create_indexes
    )
from api.app.utils.logging import get_logger
logger = get_logger(__name__)
__all__ = [
    'init_database',
    'get_database',
    'get_redis',
    'close_database',
    'close_redis',
    '_wait_for_tor_proxy',
    '_wait_for_mongodb',
    '_wait_for_redis',
    'logger', '_create_indexes'
]