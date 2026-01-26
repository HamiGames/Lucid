"""
Tor operation models for GUI Tor Manager
Data models for Tor status, circuits, and operations
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class CircuitStatus(str, Enum):
    """Tor circuit status enumeration"""
    LAUNCHED = "launched"
    BUILT = "built"
    EXTENDED = "extended"
    FAILED = "failed"
    CLOSED = "closed"


class TorStatus(BaseModel):
    """Tor proxy status model"""
    running: bool = Field(..., description="Is Tor service running")
    version: Optional[str] = Field(default=None, description="Tor version")
    uptime_seconds: Optional[int] = Field(default=None, description="Uptime in seconds")
    process_id: Optional[int] = Field(default=None, description="Tor process ID")
    config_file: Optional[str] = Field(default=None, description="Configuration file path")
    data_dir: Optional[str] = Field(default=None, description="Data directory path")
    socks_listeners: List[str] = Field(default_factory=list, description="Active SOCKS listeners")
    control_listeners: List[str] = Field(default_factory=list, description="Active control listeners")


class Circuit(BaseModel):
    """Tor circuit model"""
    circuit_id: str = Field(..., description="Circuit identifier")
    status: CircuitStatus = Field(..., description="Circuit status")
    purpose: str = Field(..., description="Circuit purpose")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Nodes in circuit")
    creation_time: Optional[str] = Field(default=None, description="Circuit creation time")
    expiration_time: Optional[str] = Field(default=None, description="Circuit expiration time")


class CircuitList(BaseModel):
    """List of circuits model"""
    circuits: List[Circuit] = Field(..., description="List of active circuits")
    total: int = Field(..., description="Total circuit count")


class TorOperation(BaseModel):
    """Base model for Tor operations"""
    operation: str = Field(..., description="Operation type")
    timestamp: str = Field(..., description="Operation timestamp")
    success: bool = Field(..., description="Operation success")
    message: Optional[str] = Field(default=None, description="Operation message")
    error: Optional[str] = Field(default=None, description="Error details if operation failed")


class TorStatusRequest(BaseModel):
    """Request model for Tor status"""
    detailed: bool = Field(default=False, description="Include detailed information")


class TorStatusResponse(BaseModel):
    """Response model for Tor status"""
    tor_status: TorStatus = Field(..., description="Tor status information")
    timestamp: str = Field(..., description="Response timestamp")
