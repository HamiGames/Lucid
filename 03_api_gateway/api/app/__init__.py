"""
API Gateway Application Package

File: 03_api_gateway/api/app/__init__.py
Purpose: Main application package initialization
"""

__version__ = "1.0.0"
__author__ = "Lucid Development Team"

from ..app.main import app
from ..app.config import get_settings, Settings
from ..app.deps import get_config
from ..app.middleware.auth import AuthMiddleware
from ..app.middleware.rate_limit import RateLimitMiddleware
from ..app.middleware.logging import LoggingMiddleware
from ..app.middleware.cors import CORSConfig
from ..app.routers import *
from ..app.schemas import *
from ..app.services import *
from ..app.utils import *
from ..app.database import *
from ..app.db import *
from ..app.scripts import *
from ..app.security import *
from ..app.routes import *
from ..app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

__all__ = [
    'logger',
    'app',
    'get_settings',
    'Settings',
    'get_config',
    'AuthMiddleware',
    'RateLimitMiddleware',
    'LoggingMiddleware',
    'CORSConfig',
    'routers',
    'schemas',
    'services',
    'utils',
    'database',
    'db',
    'scripts',
    'security',
    'get_logger', 'setup_logging'
    ]