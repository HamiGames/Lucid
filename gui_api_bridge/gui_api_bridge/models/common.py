"""
Common Data Models
File: /app/gui_api_bridge/gui_api_bridge/models/common.py
x-lucid-file-path: /app/gui_api_bridge/gui_api_bridge/models/common.py
x-lucid-file-type: python
x-lucid-file-size: 100
x-lucid-file-hash: 1234567890
x-lucid-file-created: 2021-01-01
x-lucid-file-modified: 2021-01-01
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class ErrorResponse(BaseModel):
    """Standard error response model"""
    status: str = "error"
    message: str
    details: Optional[Dict[str, Any]] = None
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response model"""
    status: str = "success"
    data: Dict[str, Any]
    message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    version: str
    timestamp: str
    uptime_seconds: float
    backend_services: list
