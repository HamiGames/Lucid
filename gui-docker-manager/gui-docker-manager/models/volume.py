"""
Volume Data Models
File: gui-docker-manager/gui-docker-manager/models/volume.py

Models for Docker volume management and information.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class VolumeUsage(BaseModel):
    """Volume usage information"""
    size_bytes: Optional[int] = Field(None, description="Volume size in bytes")
    ref_count: int = Field(default=0, description="Reference count")


class VolumeContainer(BaseModel):
    """Container using volume"""
    container_id: str = Field(..., description="Container ID")
    container_name: Optional[str] = Field(None, description="Container name")
    mount_path: str = Field(..., description="Mount path inside container")
    read_only: bool = Field(default=False, description="Whether mount is read-only")


class VolumeInfo(BaseModel):
    """Docker volume information"""
    name: str = Field(..., description="Volume name")
    driver: str = Field(..., description="Volume driver")
    driver_options: Dict[str, str] = Field(default_factory=dict, description="Driver options")
    mountpoint: str = Field(..., description="Actual mountpoint on host")
    labels: Dict[str, str] = Field(default_factory=dict, description="Volume labels")
    scope: str = Field(default="local", description="Volume scope")
    created: datetime = Field(..., description="Creation timestamp")
    containers: List[VolumeContainer] = Field(default_factory=list, description="Containers using volume")
    usage: Optional[VolumeUsage] = Field(None, description="Volume usage stats")
    backup_enabled: Optional[bool] = Field(None, description="Whether volume has backups")
    last_backup_time: Optional[datetime] = Field(None, description="Last backup timestamp")


class VolumeCreateRequest(BaseModel):
    """Request to create a volume"""
    name: str = Field(..., description="Volume name")
    driver: str = Field(default="local", description="Volume driver")
    driver_options: Optional[Dict[str, str]] = Field(None, description="Driver options")
    labels: Optional[Dict[str, str]] = Field(None, description="Volume labels")


class VolumeRemoveRequest(BaseModel):
    """Request to remove a volume"""
    name: str = Field(..., description="Volume name")
    force: bool = Field(default=False, description="Force removal even if in use")


class VolumeBackupRequest(BaseModel):
    """Request to backup a volume"""
    volume_name: str = Field(..., description="Volume name to backup")
    backup_name: Optional[str] = Field(None, description="Optional backup name")
    destination: Optional[str] = Field(None, description="Optional backup destination")


class VolumeRestoreRequest(BaseModel):
    """Request to restore a volume from backup"""
    volume_name: str = Field(..., description="Volume name to restore to")
    backup_name: str = Field(..., description="Backup name to restore from")
