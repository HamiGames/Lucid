"""
Network Data Models
File: gui-docker-manager/gui-docker-manager/models/network.py

Models for Docker network management and information.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class NetworkIPAM(BaseModel):
    """Network IPAM configuration"""
    driver: Optional[str] = Field(None, description="IPAM driver")
    configs: Optional[List[Dict[str, Any]]] = Field(None, description="IPAM configurations")


class NetworkConnectedContainer(BaseModel):
    """Container connected to network"""
    container_id: str = Field(..., description="Container ID")
    container_name: Optional[str] = Field(None, description="Container name")
    ip_address: str = Field(..., description="IP address on this network")
    gateway: Optional[str] = Field(None, description="Gateway IP")


class NetworkInfo(BaseModel):
    """Network information"""
    id: str = Field(..., description="Network ID")
    name: str = Field(..., description="Network name")
    driver: str = Field(..., description="Network driver (bridge/overlay/host/macvlan)")
    scope: str = Field(..., description="Network scope (local/swarm/global)")
    created: datetime = Field(..., description="Creation timestamp")
    subnet: Optional[str] = Field(None, description="Network subnet")
    gateway: Optional[str] = Field(None, description="Network gateway")
    containers: List[NetworkConnectedContainer] = Field(default_factory=list, description="Connected containers")
    labels: Dict[str, str] = Field(default_factory=dict, description="Network labels")
    options: Dict[str, str] = Field(default_factory=dict, description="Network options")
    ipam: Optional[NetworkIPAM] = Field(None, description="IPAM configuration")
    connected_container_count: int = Field(default=0, description="Number of connected containers")


class NetworkCreateRequest(BaseModel):
    """Request to create a network"""
    name: str = Field(..., description="Network name")
    driver: str = Field(default="bridge", description="Network driver")
    labels: Optional[Dict[str, str]] = Field(None, description="Labels for network")
    subnet: Optional[str] = Field(None, description="Subnet for network (if using custom IPAM)")


class NetworkConnectRequest(BaseModel):
    """Request to connect container to network"""
    container_id: str = Field(..., description="Container ID to connect")
    ip_address: Optional[str] = Field(None, description="Optional IP address for container on network")


class NetworkDisconnectRequest(BaseModel):
    """Request to disconnect container from network"""
    container_id: str = Field(..., description="Container ID to disconnect")
    force: bool = Field(default=False, description="Force disconnection")
