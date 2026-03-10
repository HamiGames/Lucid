"""
API Gateway Application Package

File: 03_api_gateway/api/app/__init__.py
Purpose: Main application package initialization
"""

__version__ = "1.0.0"
__author__ = "Lucid Development Team"

from api.app.main import app
from api.app.config import get_settings, Settings
from api.app.deps import get_config
from api.app.middleware.auth import AuthMiddleware
from api.app.middleware.rate_limit import RateLimitMiddleware
from api.app.middleware.logging import api.app.utils.logging as loggingMiddleware
from api.app.middleware.cors import CORSConfig
import api.app.routers as routers
import api.app.schemas as schemas
import api.app.services as services
import api.app.utils as utils
import api.app.database as database
import api.app.db as db
import api.app.scripts as scripts
import api.app.security as security
import api.app.routes as routes
from api.app.utils.logging import get_logger, setup_logging

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
    'routes',
    'schemas',
    'services',
    'utils',
    'database',
    'db',
    'scripts',
    'security', 'routers',
    'get_logger', 'setup_logging'
    ]