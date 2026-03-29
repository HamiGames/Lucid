"""
    Routing Models
    File: /app/gui_api_bridge/gui_api_bridge/models/routing.py
    x-lucid-file-path: /app/gui_api_bridge/gui_api_bridge/models/routing.py
    x-lucid-file-type: python

"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class RouteInfo(BaseModel):
    """Route information model"""
    path: str
    method: str
    service: str
    roles: list


class ServiceInfo(BaseModel):
    """Service information model"""
    name: str
    url: str
    health_check: str
    status: Optional[str] = None
