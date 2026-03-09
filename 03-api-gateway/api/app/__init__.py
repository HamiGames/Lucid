"""
API Gateway Application Package

File: 03-api-gateway/api/app/__init__.py
Purpose: Main application package initialization
"""

__version__ = "1.0.0"
__author__ = "Lucid Development Team"

from app.main import app
from app.config import settings, get_settings
from app.deps import get_config
import app.middleware
import app.routes
import app.schemas
import app.services
import app.utils
import app.database
import app.db
import app.scripts
import app.security
import app.routes

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