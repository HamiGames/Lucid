# Error Response Schemas
# Standardized error responses for API endpoints

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ValidationError(BaseModel):
    """Validation error details"""
    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Invalid value that caused the error")


class ValidationErrorResponse(BaseModel):
    """Validation error response schema"""
    error_code: str = Field(default="validation_error", description="Error code")
    message: str = Field(..., description="Validation error message")
    errors: list[ValidationError] = Field(..., description="List of validation errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class NotFoundError(BaseModel):
    """Not found error response"""
    error_code: str = Field(default="not_found", description="Error code")
    message: str = Field(..., description="Resource not found message")
    resource_type: str = Field(..., description="Type of resource not found")
    resource_id: str = Field(..., description="Identifier of resource not found")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ConflictError(BaseModel):
    """Conflict error response"""
    error_code: str = Field(default="conflict", description="Error code")
    message: str = Field(..., description="Conflict error message")
    conflicting_resource: Optional[str] = Field(None, description="Conflicting resource identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class UnauthorizedError(BaseModel):
    """Unauthorized error response"""
    error_code: str = Field(default="unauthorized", description="Error code")
    message: str = Field(..., description="Unauthorized access message")
    required_permission: Optional[str] = Field(None, description="Required permission")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ForbiddenError(BaseModel):
    """Forbidden error response"""
    error_code: str = Field(default="forbidden", description="Error code")
    message: str = Field(..., description="Forbidden access message")
    required_role: Optional[str] = Field(None, description="Required role")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class RateLimitError(BaseModel):
    """Rate limit error response"""
    error_code: str = Field(default="rate_limit_exceeded", description="Error code")
    message: str = Field(..., description="Rate limit exceeded message")
    retry_after: int = Field(..., description="Seconds to wait before retry")
    limit: int = Field(..., description="Request limit per time window")
    window: str = Field(..., description="Time window description")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class InternalServerError(BaseModel):
    """Internal server error response"""
    error_code: str = Field(default="internal_server_error", description="Error code")
    message: str = Field(..., description="Internal server error message")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")