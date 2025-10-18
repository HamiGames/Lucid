"""
API Routes Package for Lucid
Centralized route definitions for the Lucid API gateway
"""

from .auth import router as auth_router
from .blockchain import router as blockchain_router
from .health import router as health_router
from .meta import router as meta_router
from .users import router as users_router
from .wallets import router as wallets_router

__all__ = [
    "auth_router",
    "blockchain_router", 
    "health_router",
    "meta_router",
    "users_router",
    "wallets_router"
]
