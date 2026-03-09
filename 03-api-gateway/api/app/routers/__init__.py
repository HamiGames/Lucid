"""
Routers Package

File: 03-api-gateway/api/app/routers/__init__.py
Purpose: API route handlers
"""

from .meta import meta_router, auth_router, users_router, sessions_router, manifests_router, trust_router, chain_router, wallets_router, gui_router
from .gui import gui_router, gui_docker_router, gui_tor_router, gui_hardware_router, tron_support_router
from .gui_docker import gui_docker_router, gui_docker_manager_router, gui_docker_manager_service_router
from .gui_tor import gui_tor_router, gui_tor_manager_router, gui_tor_manager_service_router
from .gui_hardware import gui_hardware_router, gui_hardware_manager_router, gui_hardware_manager_service_router
from .tron_support import tron_support_router, tron_support_service_router
from .auth import auth_router, auth_service_router
from .users import users_router, users_service_router
from .sessions import sessions_router, sessions_service_router
from .manifests import manifests_router, manifests_service_router
from .trust import trust_router, trust_service_router
from .chain import chain_router, chain_service_router
from .wallets import wallets_router, wallets_service_router

__all__ = [
    "meta_router", "gui_router", "gui_docker_router", "gui_tor_router", "gui_hardware_router",
    "tron_support_router", "auth_router", "users_router", "sessions_router", "manifests_router",
    "trust_router", "chain_router", "wallets_router","gui_docker_manager_router", 
    "gui_tor_manager_router", "gui_hardware_manager_router", "tron_support_service_router",
    "auth_service_router", "users_service_router", "sessions_service_router",
    "manifests_service_router", "trust_service_router", "chain_service_router",
    "wallets_service_router", "gui_bridge_service_router", "gui_docker_manager_service_router",
    "gui_tor_manager_service_router", "gui_hardware_manager_service_router", 
    "tron_support_service_router","auth_service_router", "users_service_router",
    "sessions_service_router", "manifests_service_router", "trust_service_router", 
    "chain_service_router", "wallets_service_router"
]

