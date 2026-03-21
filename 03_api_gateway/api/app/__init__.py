"""
API Gateway Application Package
File: 03_api_gateway/api/app/__init__.py
Purpose: Main application package initialization
"""
from api.app.middleware.auth import AuthMiddleware
from api.app.utils.logging import get_logger, setup_logging
from api.app.config import CONFIG, SETTINGS
from api.app.deps import get_config
from api.app.main import app
from api.app.routers import (
    meta,
    auth,
    users,
    sessions,
    manifests,
    trust,
    chain,
    wallets,
    gui,
    gui_docker,
    gui_tor,
    gui_hardware,
    tron_support
)
from api.app.database.connection import init_database
from api.app.models.common import ErrorResponse, ErrorDetail
__all__ = [
    'AuthMiddleware', 'get_logger', 'setup_logging', 'CONFIG', 
    'SETTINGS', 'get_config', 'app', 'meta', 'auth', 'users', 
    'sessions', 'manifests', 'trust', 'chain', 'wallets', 'gui', 
    'gui_docker', 'gui_tor', 'gui_hardware', 'tron_support', 'init_database', 'ErrorResponse', 'ErrorDetail'
]