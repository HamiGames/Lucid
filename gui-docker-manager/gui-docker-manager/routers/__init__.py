"""
Routers for Docker Manager API
File: gui-docker-manager/gui-docker-manager/routers/__init__.py
"""

from .containers import router as containers_router
from .services import router as services_router
from .compose import router as compose_router
from .health import router as health_router
from .networks import router as networks_router
from .volumes import router as volumes_router
from .events import router as events_router

__all__ = [
    "containers_router",
    "services_router",
    "compose_router",
    "health_router",
    "networks_router",
    "volumes_router",
    "events_router",
]
