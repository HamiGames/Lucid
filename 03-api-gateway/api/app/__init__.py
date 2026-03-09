"""
API Gateway Application Package

File: 03-api-gateway/api/app/__init__.py
Purpose: Main application package initialization
"""

__version__ = "1.0.0"
__author__ = "Lucid Development Team"

from api.app.main import app
from api.app.config import settings, get_settings
from api.app.deps import get_config
import api.app.middleware as middleware
import api.app.routers as routers
import api.app.schemas as schemas
import api.app.services as services
import api.app.utils as utils
import api.app.database as database
import api.app.db as db
import api.app.scripts as scripts
import api.app.security as security
import api.app.routes as routes

__all__ = [
    'app',
    'settings',
    'get_settings',
    'get_config',
    'middleware',
    'routes',
    'schemas',
    'services',
    'utils',
    'database',
    'db',
    'scripts',
    'security', 'routers'
    
    ]