"""
RDP Common Models - Shared Data Models

This module contains shared data models used across RDP services.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

class SessionStatus(str, Enum):
    """RDP session status enumeration"""
    CREATING = "creating"
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    ERROR = "error"

class ConnectionStatus(str, Enum):
    """RDP connection status enumeration"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

class RdpSession(BaseModel):
    """RDP session model"""
    session_id: UUID
    user_id: str
    server_id: UUID
    connection_id: Optional[UUID] = None
    status: SessionStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": str(self.session_id),
            "user_id": self.user_id,
            "server_id": str(self.server_id),
            "connection_id": str(self.connection_id) if self.connection_id else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "config": self.config,
            "metadata": self.metadata
        }

class SessionMetrics(BaseModel):
    """Session metrics model"""
    session_id: UUID
    start_time: datetime
    last_updated: Optional[datetime] = None
    cpu_percent: float = 0.0
    memory_usage: int = 0
    memory_percent: float = 0.0
    disk_usage: int = 0
    disk_percent: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    network_packets_sent: int = 0
    network_packets_recv: int = 0
    active_connections: int = 0
    process_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "session_id": str(self.session_id),
            "start_time": self.start_time.isoformat(),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "cpu_percent": self.cpu_percent,
            "memory_usage": self.memory_usage,
            "memory_percent": self.memory_percent,
            "disk_usage": self.disk_usage,
            "disk_percent": self.disk_percent,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "network_packets_sent": self.network_packets_sent,
            "network_packets_recv": self.network_packets_recv,
            "active_connections": self.active_connections,
            "process_count": self.process_count
        }
    
    def update_from_dict(self, data: Dict[str, Any]):
        """Update metrics from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.last_updated = datetime.utcnow()

class RdpServer(BaseModel):
    """RDP server model"""
    server_id: UUID
    name: str
    host: str
    port: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert server to dictionary"""
        return {
            "server_id": str(self.server_id),
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "config": self.config,
            "metadata": self.metadata
        }

class RdpConnection(BaseModel):
    """RDP connection model"""
    connection_id: UUID
    session_id: UUID
    server_id: UUID
    status: ConnectionStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert connection to dictionary"""
        return {
            "connection_id": str(self.connection_id),
            "session_id": str(self.session_id),
            "server_id": str(self.server_id),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "config": self.config,
            "metrics": self.metrics
        }

class ResourceAlert(BaseModel):
    """Resource alert model"""
    alert_id: UUID
    session_id: UUID
    alert_type: str
    severity: str
    message: str
    threshold: float
    current_value: float
    created_at: datetime
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "alert_id": str(self.alert_id),
            "session_id": str(self.session_id),
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "threshold": self.threshold,
            "current_value": self.current_value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata
        }

class SessionConfig(BaseModel):
    """Session configuration model"""
    user_id: str
    server_id: UUID
    display_resolution: str = "1920x1080"
    color_depth: int = 24
    audio_enabled: bool = True
    clipboard_enabled: bool = True
    file_transfer_enabled: bool = True
    session_timeout: int = 3600  # seconds
    idle_timeout: int = 1800  # seconds
    max_connections: int = 1
    encryption_enabled: bool = True
    compression_enabled: bool = True
    bandwidth_limit: Optional[int] = None  # KB/s
    custom_settings: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "user_id": self.user_id,
            "server_id": str(self.server_id),
            "display_resolution": self.display_resolution,
            "color_depth": self.color_depth,
            "audio_enabled": self.audio_enabled,
            "clipboard_enabled": self.clipboard_enabled,
            "file_transfer_enabled": self.file_transfer_enabled,
            "session_timeout": self.session_timeout,
            "idle_timeout": self.idle_timeout,
            "max_connections": self.max_connections,
            "encryption_enabled": self.encryption_enabled,
            "compression_enabled": self.compression_enabled,
            "bandwidth_limit": self.bandwidth_limit,
            "custom_settings": self.custom_settings
        }
