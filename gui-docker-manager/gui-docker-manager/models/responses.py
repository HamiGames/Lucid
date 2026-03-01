"""
Response Models for API Responses
File: gui-docker-manager/gui-docker-manager/models/responses.py

Pydantic models for standardized API responses across all endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class StatusResponse(BaseModel):
    """Generic status response"""
    status: str = Field(..., description="Operation status (success/error/pending)")
    message: Optional[str] = Field(None, description="Status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ServiceStatusResponse(BaseModel):
    """Service group status response"""
    service_group: str = Field(..., description="Service group name")
    services: List[str] = Field(..., description="List of services in group")
    status: str = Field(..., description="Group overall status (running/stopped/partial/unhealthy)")
    running_services: int = Field(..., description="Number of running services")
    total_services: int = Field(..., description="Total services in group")
    details: Dict[str, Any] = Field(default_factory=dict, description="Per-service status details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ContainerEventResponse(BaseModel):
    """Container event for real-time streaming"""
    timestamp: datetime = Field(..., description="Event timestamp")
    container_id: str = Field(..., description="Container ID")
    container_name: str = Field(..., description="Container name")
    event_type: str = Field(..., description="Event type (start/stop/create/destroy/pause/unpause)")
    status: str = Field(..., description="Current container status")
    exit_code: Optional[int] = Field(None, description="Exit code if applicable")
    error: Optional[str] = Field(None, description="Error message if applicable")


class OperationResultResponse(BaseModel):
    """Result of a container/service operation"""
    success: bool = Field(..., description="Whether operation succeeded")
    operation: str = Field(..., description="Operation type (start/stop/restart/pause/unpause/remove)")
    target_id: str = Field(..., description="Target container/service ID")
    message: str = Field(..., description="Operation result message")
    error: Optional[str] = Field(None, description="Error details if operation failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BatchOperationResponse(BaseModel):
    """Result of batch operations on multiple containers/services"""
    operation: str = Field(..., description="Operation type")
    total: int = Field(..., description="Total items operated on")
    succeeded: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    results: List[Dict[str, Any]] = Field(..., description="Individual operation results")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall status (healthy/unhealthy/degraded)")
    service: str = Field(..., description="Service name")
    docker_daemon: Dict[str, Any] = Field(..., description="Docker daemon health")
    database_connectivity: Dict[str, bool] = Field(..., description="Database connectivity status")
    message: str = Field(..., description="Health status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MetricsResponse(BaseModel):
    """Metrics response"""
    containers_total: int = Field(..., description="Total number of containers")
    containers_running: int = Field(..., description="Number of running containers")
    containers_stopped: int = Field(..., description="Number of stopped containers")
    services_healthy: int = Field(..., description="Number of healthy services")
    services_unhealthy: int = Field(..., description="Number of unhealthy services")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response"""
    error: Dict[str, Any] = Field(..., description="Error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "LUCID_ERR_5000",
                    "message": "Internal server error",
                    "details": {"exception": "Error message"}
                }
            }
        }
