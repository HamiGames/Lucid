"""
Container Data Models
File: gui-docker-manager/gui-docker-manager/models/container.py
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ContainerState(BaseModel):
    """Container state information"""
    status: str = Field(..., description="Container status (running, stopped, exited, etc)")
    exit_code: Optional[int] = Field(None, description="Exit code if stopped")
    started_at: Optional[datetime] = Field(None, description="When container was started")
    finished_at: Optional[datetime] = Field(None, description="When container finished")


class ContainerStats(BaseModel):
    """Container statistics"""
    cpu_percent: Optional[float] = Field(None, description="CPU percentage")
    memory_usage: Optional[str] = Field(None, description="Memory usage")
    net_io: Optional[str] = Field(None, description="Network I/O")
    block_io: Optional[str] = Field(None, description="Block I/O")


class ContainerInfo(BaseModel):
    """Container information"""
    id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Image name")
    state: ContainerState = Field(..., description="Container state")
    ports: Optional[Dict[str, Any]] = Field(None, description="Port mappings")
    labels: Optional[Dict[str, str]] = Field(None, description="Container labels")
    mounts: Optional[list] = Field(None, description="Volume mounts")
