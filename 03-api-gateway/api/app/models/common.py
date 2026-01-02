
"""
Common Models

File: 03-api-gateway/api/app/models/common.py
Purpose: Shared data models used across the application
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class ErrorDetail(BaseModel):
    """Error detail information"""
    code: str = Field(..., examples=["LUCID_ERR_1001"])
    message: str = Field(..., examples=["Invalid request data"])
    details: Optional[Dict[str, Any]] = Field(None)
    request_id: str = Field(...)
    timestamp: datetime = Field(...)
    service: str = Field(..., examples=["api-gateway"])
    version: str = Field(..., examples=["v1"])
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }


class ErrorResponse(BaseModel):
    """Error response wrapper"""
    error: ErrorDetail = Field(...)


class PaginationInfo(BaseModel):
    """Pagination information"""
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    pages: int = Field(..., ge=0)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ServiceInfo(BaseModel):
    """Service information response"""
    service_name: str = Field(..., examples=["api-gateway"])
    version: str = Field(..., examples=["1.0.0"])
    build_date: datetime = Field(...)
    environment: str = Field(..., examples=["production"])
    features: list = Field(..., examples=[["authentication", "rate_limiting", "ssl_termination"]])
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthStatus(BaseModel):
    """Health status response"""
    status: str = Field(..., pattern="^(healthy|unhealthy|degraded)$")
    timestamp: datetime = Field(...)
    service: str = Field(..., examples=["api-gateway"])
    version: str = Field(..., examples=["1.0.0"])
    dependencies: Dict[str, str] = Field(..., description="Dependency health status")
    uptime: int = Field(..., description="Uptime in seconds")
    response_time: float = Field(..., description="Average response time in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
