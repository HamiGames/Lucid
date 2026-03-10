"""
Lucid API Gateway - Database Package
Database connection and utilities.
"""

from .connection import get_database, close_database
from 03_api_gateway.api..app.config import Settings

from 03_api_gateway.api..app.utils.logging import get_logger

settings = Settings()
logger = get_logger(__name__)
__all__ = [
    'get_database',
    'close_database',
    'logger',
    'settings', 
    'Settings'
    
]

