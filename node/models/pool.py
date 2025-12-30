# Path: node/models/pool.py
# Lucid Node Management Models - Pool Data Models
# Based on LUCID-STRICT requirements per Spec-1c

"""
Pool data models for Lucid system.

This module provides Pydantic models for:
- Pool lifecycle management
- Node assignment and scaling
- Resource allocation
- Auto-scaling configuration
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import re

class ScalingPolicy(BaseModel):
    """Auto-scaling policy configuration"""
    scale_up_threshold: float = Field(..., ge=0, le=100, description="CPU percentage threshold for scaling up")
    scale_down_threshold: float = Field(..., ge=0, le=100, description="CPU percentage threshold for scaling down")
    min_nodes: int = Field(..., ge=1, description="Minimum number of nodes")
    max_nodes: int = Field(..., ge=1, description="Maximum number of nodes")
    cooldown_minutes: int = Field(..., ge=1, description="Cooldown period in minutes")
    
    @field_validator('scale_up_threshold')
    @classmethod
    def validate_scale_up_threshold(cls, v):
        if v < 50 or v > 95:
            raise ValueError("Scale up threshold must be between 50 and 95")
        return v
    
    @field_validator('scale_down_threshold')
    @classmethod
    def validate_scale_down_threshold(cls, v):
        if v < 10 or v > 50:
            raise ValueError("Scale down threshold must be between 10 and 50")
        return v
    
    @field_validator('max_nodes')
    @classmethod
    def validate_max_nodes(cls, v, info):
        if hasattr(info, 'data') and 'min_nodes' in info.data and v < info.data['min_nodes']:
            raise ValueError("Max nodes must be greater than or equal to min nodes")
        return v

class AutoScalingConfig(BaseModel):
    """Auto-scaling configuration"""
    enabled: bool = Field(default=False, description="Enable auto-scaling")
    policy: Optional[ScalingPolicy] = Field(None, description="Scaling policy")
    target_cpu_percent: float = Field(default=70.0, ge=0, le=100, description="Target CPU utilization")
    scale_up_cooldown: int = Field(default=5, ge=1, description="Scale up cooldown in minutes")
    scale_down_cooldown: int = Field(default=10, ge=1, description="Scale down cooldown in minutes")
    
    @field_validator('target_cpu_percent')
    @classmethod
    def validate_target_cpu_percent(cls, v):
        if v < 30 or v > 90:
            raise ValueError("Target CPU percent must be between 30 and 90")
        return v

class NodePool(BaseModel):
    """Node pool model"""
    pool_id: str = Field(..., description="Unique pool identifier", pattern="^pool_[a-zA-Z0-9_-]+$")
    name: str = Field(..., min_length=3, max_length=100, description="Human-readable pool name")
    description: Optional[str] = Field(None, max_length=500, description="Pool description")
    node_count: int = Field(default=0, ge=0, description="Current number of nodes in pool")
    max_nodes: int = Field(..., ge=1, le=1000, description="Maximum nodes allowed in pool")
    resource_limits: Optional[Dict[str, Any]] = Field(None, description="Resource limits for the pool")
    auto_scaling: AutoScalingConfig = Field(default_factory=AutoScalingConfig, description="Auto-scaling configuration")
    pricing: Optional[Dict[str, Any]] = Field(None, description="Pricing information")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    
    @field_validator('pool_id')
    @classmethod
    def validate_pool_id(cls, v):
        if not re.match(r'^pool_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Pool ID must match pattern: ^pool_[a-zA-Z0-9_-]+$")
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Pool name must contain only alphanumeric characters, hyphens, and underscores")
        return v
    
    @field_validator('max_nodes')
    @classmethod
    def validate_max_nodes(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Max nodes must be between 1 and 1000")
        return v
    
    @field_validator('node_count')
    @classmethod
    def validate_node_count(cls, v, info):
        if hasattr(info, 'data') and 'max_nodes' in info.data and v > info.data['max_nodes']:
            raise ValueError("Node count cannot exceed max nodes")
        return v

class NodePoolCreateRequest(BaseModel):
    """Request model for creating a new pool"""
    name: str = Field(..., min_length=3, max_length=100, description="Pool name")
    description: Optional[str] = Field(None, max_length=500, description="Pool description")
    max_nodes: int = Field(default=100, ge=1, le=1000, description="Maximum nodes allowed in pool")
    resource_limits: Optional[Dict[str, Any]] = Field(None, description="Resource limits for the pool")
    auto_scaling: Optional[AutoScalingConfig] = Field(None, description="Auto-scaling configuration")
    pricing: Optional[Dict[str, Any]] = Field(None, description="Pricing information")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Pool name must contain only alphanumeric characters, hyphens, and underscores")
        return v
    
    @field_validator('max_nodes')
    @classmethod
    def validate_max_nodes(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Max nodes must be between 1 and 1000")
        return v

class NodePoolUpdateRequest(BaseModel):
    """Request model for updating a pool"""
    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Pool name")
    description: Optional[str] = Field(None, max_length=500, description="Pool description")
    max_nodes: Optional[int] = Field(None, ge=1, le=1000, description="Maximum nodes allowed in pool")
    resource_limits: Optional[Dict[str, Any]] = Field(None, description="Resource limits for the pool")
    auto_scaling: Optional[AutoScalingConfig] = Field(None, description="Auto-scaling configuration")
    pricing: Optional[Dict[str, Any]] = Field(None, description="Pricing information")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Pool name must contain only alphanumeric characters, hyphens, and underscores")
        return v
    
    @field_validator('max_nodes')
    @classmethod
    def validate_max_nodes(cls, v):
        if v is not None and (v < 1 or v > 1000):
            raise ValueError("Max nodes must be between 1 and 1000")
        return v

class PoolNode(BaseModel):
    """Node assignment in a pool"""
    node_id: str = Field(..., description="Node ID", pattern="^node_[a-zA-Z0-9_-]+$")
    pool_id: str = Field(..., description="Pool ID", pattern="^pool_[a-zA-Z0-9_-]+$")
    priority: int = Field(default=50, ge=1, le=100, description="Node priority in pool")
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Assignment timestamp")
    status: str = Field(default="active", description="Node status in pool")
    
    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if not re.match(r'^node_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Node ID must match pattern: ^node_[a-zA-Z0-9_-]+$")
        return v
    
    @field_validator('pool_id')
    @classmethod
    def validate_pool_id(cls, v):
        if not re.match(r'^pool_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Pool ID must match pattern: ^pool_[a-zA-Z0-9_-]+$")
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v < 1 or v > 100:
            raise ValueError("Priority must be between 1 and 100")
        return v

class PoolScalingEvent(BaseModel):
    """Pool scaling event"""
    event_id: str = Field(..., description="Event ID")
    pool_id: str = Field(..., description="Pool ID", pattern="^pool_[a-zA-Z0-9_-]+$")
    event_type: str = Field(..., description="Event type (scale_up, scale_down)")
    target_nodes: int = Field(..., ge=0, description="Target number of nodes")
    current_nodes: int = Field(..., ge=0, description="Current number of nodes")
    trigger_reason: str = Field(..., description="Reason for scaling")
    triggered_at: datetime = Field(..., description="Event timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    status: str = Field(default="pending", description="Event status")
    
    @field_validator('pool_id')
    @classmethod
    def validate_pool_id(cls, v):
        if not re.match(r'^pool_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Pool ID must match pattern: ^pool_[a-zA-Z0-9_-]+$")
        return v
    
    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v):
        if v not in ['scale_up', 'scale_down']:
            raise ValueError("Event type must be 'scale_up' or 'scale_down'")
        return v

class PoolMetrics(BaseModel):
    """Pool performance metrics"""
    pool_id: str = Field(..., description="Pool ID", pattern="^pool_[a-zA-Z0-9_-]+$")
    timestamp: datetime = Field(..., description="Metrics timestamp")
    total_nodes: int = Field(..., ge=0, description="Total nodes in pool")
    active_nodes: int = Field(..., ge=0, description="Active nodes")
    average_cpu_percent: float = Field(..., ge=0, le=100, description="Average CPU utilization")
    average_memory_percent: float = Field(..., ge=0, le=100, description="Average memory utilization")
    total_sessions: int = Field(..., ge=0, description="Total active sessions")
    throughput_mbps: float = Field(..., ge=0, description="Network throughput in Mbps")
    
    @field_validator('pool_id')
    @classmethod
    def validate_pool_id(cls, v):
        if not re.match(r'^pool_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Pool ID must match pattern: ^pool_[a-zA-Z0-9_-]+$")
        return v
    
    @field_validator('active_nodes')
    @classmethod
    def validate_active_nodes(cls, v, info):
        if hasattr(info, 'data') and 'total_nodes' in info.data and v > info.data['total_nodes']:
            raise ValueError("Active nodes cannot exceed total nodes")
        return v
