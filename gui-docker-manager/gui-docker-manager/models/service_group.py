"""
Service Group Data Models
File: gui-docker-manager/gui-docker-manager/models/service_group.py
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ServiceGroupConfig(BaseModel):
    """Service group configuration"""
    name: str = Field(..., description="Service group name")
    description: str = Field(..., description="Service group description")
    services: List[str] = Field(..., description="List of services in group")
    dependencies: Optional[List[str]] = Field(None, description="Dependent service groups")
    startup_order: int = Field(..., description="Startup order priority")


class ServiceGroup(BaseModel):
    """Service group with status"""
    name: str = Field(..., description="Group name")
    config: ServiceGroupConfig = Field(..., description="Group configuration")
    status: str = Field(..., description="Group status")
    running_services: int = Field(..., description="Number of running services")
    total_services: int = Field(..., description="Total services in group")
