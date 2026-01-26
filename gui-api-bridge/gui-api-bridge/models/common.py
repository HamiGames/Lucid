"""
Common Data Models
File: gui-api-bridge/gui-api-bridge/models/common.py
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
