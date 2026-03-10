"""
Routers Package

File: 03_api_gateway/api/app/routers/__init__.py
Purpose: API route handlers
"""

from api.app.routers.meta import router as meta_router
from api.app.routers.gui import router as gui_router
from api.app.routers.gui_docker import router as gui_docker_router
from api.app.routers.gui_tor import router as gui_tor_router
from api.app.routers.gui_hardware import router as gui_hardware_router
from api.app.routers.tron_support import router as tron_support_router
from api.app.routers.auth import router as auth_router
from api.app.routers.users import router as users_router
from api.app.routers.sessions import router as sessions_router
from api.app.routers.manifests import router as manifests_router
from api.app.routers.trust import router as trust_router
from api.app.routers.chain import router as chain_router
from api.app.routers.wallets import router as wallets_router

from api.app.utils.logging import get_logger
logger = get_logger(__name__)
__all__ = [
    "meta_router", "gui_router", "gui_docker_router", "gui_tor_router", "gui_hardware_router",
    "tron_support_router", "auth_router", "users_router", "sessions_router", "manifests_router",
    "trust_router", "chain_router", "wallets_router", "logger"
    
]

