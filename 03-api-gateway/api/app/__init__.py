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
import api.app.middleware
import api.app.routes
import api.app.schemas
import api.app.services
import api.app.utils
import api.app.database
import api.app.db
import api.app.scripts
import api.app.security
import api.app.routes

__all__ = [
    'app',
    'settings',
    'get_settings',
    'get_config',
    'app.middleware',
    'app.routes',
    'app.schemas',
    'app.services',
    'app.utils',
    'app.database',
    'app.db',
    'app.scripts',
    'app.security',
    'app.routes',
    'app.schemas',
    'app.services',
    'app.utils',
    'app.database',
    'app.db',
    'app.scripts',
    'app.security',
    'app.routes'
    ]