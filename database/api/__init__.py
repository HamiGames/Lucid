"""
Database API Layer Package

This package provides RESTful API endpoints for database operations including:
- Health checks and monitoring
- Statistics and metrics collection
- Collection management
- Index management
- Backup operations
- Cache management
- Volume management
- Search operations

All endpoints follow the Lucid API architecture standards.
"""

from .database_health import router as health_router
from .database_stats import router as stats_router
from .collections import router as collections_router
from .indexes import router as indexes_router
from .backups import router as backups_router
from .cache import router as cache_router
from .volumes import router as volumes_router
from .search import router as search_router

__all__ = [
    'health_router',
    'stats_router',
    'collections_router',
    'indexes_router',
    'backups_router',
    'cache_router',
    'volumes_router',
    'search_router',
]

__version__ = '1.0.0'

