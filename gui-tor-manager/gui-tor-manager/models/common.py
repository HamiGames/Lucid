"""
Common Pydantic models for GUI Tor Manager
Error responses, pagination, common data structures
"""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: Optional[str] = Field(default=None, description="Timestamp of error")


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: HealthStatus = Field(..., description="Overall service health status")
    timestamp: str = Field(..., description="Timestamp of health check")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    components: Dict[str, str] = Field(..., description="Status of individual components")


class ServiceInfo(BaseModel):
    """Service information model"""
    name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    status: str = Field(..., description="Service status")
    uptime_seconds: Optional[int] = Field(default=None, description="Service uptime in seconds")


class PaginationParams(BaseModel):
    """Pagination parameters model"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Sort field")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel):
    """Generic paginated response model"""
    data: List[Any] = Field(..., description="Response data")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class MessageResponse(BaseModel):
    """Simple message response model"""
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success flag")
