"""
Onion service models for GUI Tor Manager
Data models for onion service management
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class OnionServiceType(str, Enum):
    """Onion service type enumeration"""
    RSA1024 = "RSA1024"
    ED25519 = "ED25519"


class OnionServiceStatus(str, Enum):
    """Onion service status enumeration"""
    LAUNCHED = "launched"
    ACTIVE = "active"
    FAILED = "failed"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class OnionService(BaseModel):
    """Onion service model"""
    service_id: str = Field(..., description="Unique service identifier")
    address: str = Field(..., description="Onion address (.onion)")
    service_type: OnionServiceType = Field(..., description="Type of onion service")
    ports: List[int] = Field(default_factory=list, description="Listen ports")
    targets: List[Dict[str, Any]] = Field(default_factory=list, description="Target mappings")
    status: OnionServiceStatus = Field(..., description="Current status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    is_persistent: bool = Field(default=True, description="Whether service is persistent")
    version: str = Field(default="2", description="Onion address version (2 or 3)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class OnionServiceList(BaseModel):
    """List of onion services model"""
    services: List[OnionService] = Field(..., description="List of onion services")
    total: int = Field(..., description="Total service count")


class CreateOnionServiceRequest(BaseModel):
    """Request model for creating onion service"""
    name: Optional[str] = Field(default=None, description="Service name")
    service_type: OnionServiceType = Field(default=OnionServiceType.ED25519, description="Service type")
    ports: List[int] = Field(..., description="Listen ports")
    targets: List[Dict[str, str]] = Field(..., description="Target port mappings")
    persistent: bool = Field(default=True, description="Make service persistent")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class CreateOnionServiceResponse(BaseModel):
    """Response model for creating onion service"""
    service_id: str = Field(..., description="Created service identifier")
    address: str = Field(..., description="Onion address")
    status: OnionServiceStatus = Field(..., description="Initial status")
    created_at: str = Field(..., description="Creation timestamp")


class DeleteOnionServiceRequest(BaseModel):
    """Request model for deleting onion service"""
    service_id: str = Field(..., description="Service identifier to delete")
    force: bool = Field(default=False, description="Force deletion")


class DeleteOnionServiceResponse(BaseModel):
    """Response model for deleting onion service"""
    service_id: str = Field(..., description="Deleted service identifier")
    address: str = Field(..., description="Deleted onion address")
    deleted_at: str = Field(..., description="Deletion timestamp")


class OnionServiceStatusRequest(BaseModel):
    """Request model for onion service status"""
    service_id: str = Field(..., description="Service identifier")


class OnionServiceStatusResponse(BaseModel):
    """Response model for onion service status"""
    service_id: str = Field(..., description="Service identifier")
    address: str = Field(..., description="Onion address")
    status: OnionServiceStatus = Field(..., description="Current status")
    message: Optional[str] = Field(default=None, description="Status message")
