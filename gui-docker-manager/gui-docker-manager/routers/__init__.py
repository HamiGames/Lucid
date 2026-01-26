"""
Routers for Docker Manager API
File: gui-docker-manager/gui-docker-manager/routers/__init__.py
"""

from .containers import router as containers_router
from .services import router as services_router
from .compose import router as compose_router
from .health import router as health_router

__all__ = [
    "containers_router",
    "services_router",
    "compose_router",
    "health_router",
]
