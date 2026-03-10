"""
Common Data Models

Shared models used across multiple endpoint categories including:
- Error responses
- Pagination
- Service metadata
- Health status
- Metrics

These models provide standardized response formats across the API.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes"""
    VALIDATION_ERROR = "LUCID_ERR_1000"
    AUTHENTICATION_ERROR = "LUCID_ERR_2000"
    AUTHORIZATION_ERROR = "LUCID_ERR_2001"
    RATE_LIMIT_ERROR = "LUCID_ERR_3000"
    BUSINESS_LOGIC_ERROR = "LUCID_ERR_4000"
    SYSTEM_ERROR = "LUCID_ERR_5000"
    SERVICE_UNAVAILABLE = "LUCID_ERR_5001"


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    
    Attributes:
        code: Error code from ErrorCode enum
        message: Human-readable error message
        details: Optional additional error details
        request_id: Unique request identifier for tracking
        timestamp: ISO 8601 timestamp of the error
        service: Service name that generated the error
        version: API version
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "code": "LUCID_ERR_1000",
            "message": "Validation error",
            "details": {"field": "email", "constraint": "required"},
            "request_id": "req-123456",
            "timestamp": "2025-10-14T12:00:00Z",
            "service": "api-gateway",
            "version": "v1"
        }
    })
    
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: str = Field(..., description="Request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    service: str = Field(default="api-gateway", description="Service name")
    version: str = Field(default="v1", description="API version")


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.
    
    Attributes:
        skip: Number of records to skip
        limit: Maximum number of records to return
    """
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum records to return")


class ServiceInfo(BaseModel):
    """
    Service information response.
    
    Attributes:
        service_name: Name of the service
        version: Service version
        environment: Deployment environment
        description: Service description
        maintainer: Service maintainer
        docs_url: API documentation URL
        openapi_url: OpenAPI specification URL
        supported_versions: List of supported API versions
        capabilities: List of service capabilities
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "service_name": "lucid-api-gateway",
            "version": "1.0.0",
            "environment": "production",
            "description": "Primary entry point for all Lucid blockchain system APIs",
            "maintainer": "Lucid Development Team",
            "docs_url": "/docs",
            "openapi_url": "/openapi.json",
            "supported_versions": ["v1"],
            "capabilities": ["authentication", "rate_limiting", "proxy"]
        }
    })
    
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment (dev/staging/production)")
    description: str = Field(..., description="Service description")
    maintainer: str = Field(..., description="Service maintainer")
    docs_url: str = Field(..., description="API documentation URL")
    openapi_url: str = Field(..., description="OpenAPI specification URL")
    supported_versions: List[str] = Field(..., description="Supported API versions")
    capabilities: List[str] = Field(..., description="Service capabilities")


class HealthStatus(BaseModel):
    """
    Health check response.
    
    Attributes:
        status: Overall health status (healthy/degraded/unhealthy)
        timestamp: Health check timestamp
        uptime_seconds: Service uptime in seconds
        dependencies: Status of service dependencies
        version: Service version
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "healthy",
            "timestamp": "2025-10-14T12:00:00Z",
            "uptime_seconds": 86400,
            "dependencies": {
                "mongodb": "healthy",
                "redis": "healthy",
                "auth_service": "healthy"
            },
            "version": "1.0.0"
        }
    })
    
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    uptime_seconds: int = Field(..., description="Service uptime")
    dependencies: Dict[str, str] = Field(..., description="Dependency statuses")
    version: str = Field(..., description="Service version")


class VersionInfo(BaseModel):
    """
    Version information response.
    
    Attributes:
        service_version: Service version
        api_version: Current API version
        supported_api_versions: List of supported API versions
        build_date: Build date
        git_commit: Git commit hash
        python_version: Python version
        dependencies: Key dependency versions
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "service_version": "1.0.0",
            "api_version": "v1",
            "supported_api_versions": ["v1"],
            "build_date": "2025-10-14",
            "git_commit": "abc123",
            "python_version": "3.11.0",
            "dependencies": {"fastapi": "0.104.1", "pydantic": "2.5.0"}
        }
    })
    
    service_version: str = Field(..., description="Service version")
    api_version: str = Field(..., description="Current API version")
    supported_api_versions: List[str] = Field(..., description="Supported API versions")
    build_date: str = Field(..., description="Build date")
    git_commit: str = Field(..., description="Git commit hash")
    python_version: str = Field(..., description="Python version")
    dependencies: Dict[str, str] = Field(..., description="Dependency versions")


class MetricsResponse(BaseModel):
    """
    Service metrics response.
    
    Attributes:
        timestamp: Metrics timestamp
        uptime_seconds: Service uptime
        request_count: Total request count
        error_count: Total error count
        average_response_time_ms: Average response time
        requests_per_second: Current requests per second
        system_metrics: System resource metrics
        endpoint_metrics: Per-endpoint metrics
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "timestamp": "2025-10-14T12:00:00Z",
            "uptime_seconds": 86400,
            "request_count": 10000,
            "error_count": 50,
            "average_response_time_ms": 45.5,
            "requests_per_second": 10.5,
            "system_metrics": {
                "cpu_percent": 25.5,
                "memory_percent": 45.2,
                "disk_percent": 60.0
            },
            "endpoint_metrics": {}
        }
    })
    
    timestamp: datetime = Field(..., description="Metrics timestamp")
    uptime_seconds: int = Field(..., description="Service uptime")
    request_count: int = Field(..., description="Total requests")
    error_count: int = Field(..., description="Total errors")
    average_response_time_ms: float = Field(..., description="Average response time")
    requests_per_second: float = Field(..., description="Requests per second")
    system_metrics: Dict[str, float] = Field(..., description="System metrics")
    endpoint_metrics: Dict[str, Any] = Field(..., description="Endpoint metrics")

