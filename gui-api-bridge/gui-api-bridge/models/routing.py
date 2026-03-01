"""
Routing Models
File: gui-api-bridge/gui-api-bridge/models/routing.py
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
