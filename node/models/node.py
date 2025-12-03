# Path: node/models/node.py
# Lucid Node Management Models - Node Data Models
# Based on LUCID-STRICT requirements per Spec-1c

"""
Node data models for Lucid system.

This module provides Pydantic models for:
- Node lifecycle management
- Hardware information
- Resource monitoring
- PoOT validation
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from enum import Enum
import re

class NodeStatus(str, Enum):
    """Node operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"

class NodeType(str, Enum):
    """Node type classification"""
    WORKER = "worker"
    VALIDATOR = "validator"
    STORAGE = "storage"
    COMPUTE = "compute"

class HardwareInfo(BaseModel):
    """Hardware information for a node"""
    cpu: Dict[str, Any] = Field(..., description="CPU information")
    memory: Dict[str, Any] = Field(..., description="Memory information")
    storage: Dict[str, Any] = Field(..., description="Storage information")
    gpu: Optional[Dict[str, Any]] = Field(None, description="GPU information")
    network: List[Dict[str, Any]] = Field(default_factory=list, description="Network interfaces")
    
    @field_validator('cpu')
    @classmethod
    def validate_cpu(cls, v):
        required_fields = ['cores', 'frequency_mhz', 'architecture']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"CPU {field} is required")
        return v
    
    @field_validator('memory')
    @classmethod
    def validate_memory(cls, v):
        required_fields = ['total_bytes', 'type']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Memory {field} is required")
        return v
    
    @field_validator('storage')
    @classmethod
    def validate_storage(cls, v):
        required_fields = ['total_bytes', 'type', 'interface']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Storage {field} is required")
        return v

class NodeLocation(BaseModel):
    """Geographic location information"""
    country: str = Field(..., description="Country code")
    region: str = Field(..., description="Region/state")
    city: str = Field(..., description="City name")
    timezone: str = Field(..., description="Timezone")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Latitude and longitude")
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v):
        if len(v) != 2:
            raise ValueError("Country must be 2-character ISO code")
        return v.upper()

class ResourceLimits(BaseModel):
    """Resource limits for a node"""
    cpu_percent: float = Field(..., ge=0, le=100, description="CPU usage limit percentage")
    memory_bytes: int = Field(..., ge=0, description="Memory limit in bytes")
    disk_bytes: int = Field(..., ge=0, description="Disk limit in bytes")
    network_mbps: float = Field(..., ge=0, description="Network bandwidth limit in Mbps")
    
    @field_validator('cpu_percent')
    @classmethod
    def validate_cpu_percent(cls, v):
        if v < 1 or v > 100:
            raise ValueError("CPU percent must be between 1 and 100")
        return v

class NodeConfiguration(BaseModel):
    """Node configuration settings"""
    max_sessions: int = Field(default=10, ge=1, le=1000, description="Maximum concurrent sessions")
    resource_limits: ResourceLimits = Field(..., description="Resource limits")
    auto_scaling: bool = Field(default=False, description="Enable auto-scaling")
    maintenance_window: Optional[Dict[str, int]] = Field(None, description="Maintenance window settings")
    
    @field_validator('max_sessions')
    @classmethod
    def validate_max_sessions(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Max sessions must be between 1 and 1000")
        return v

class Node(BaseModel):
    """Node model"""
    node_id: str = Field(..., description="Unique node identifier", regex="^node_[a-zA-Z0-9_-]+$")
    name: str = Field(..., min_length=3, max_length=100, description="Human-readable node name")
    status: NodeStatus = Field(..., description="Current node status")
    node_type: NodeType = Field(..., description="Type of node")
    pool_id: Optional[str] = Field(None, description="Pool this node belongs to", regex="^pool_[a-zA-Z0-9_-]+$")
    hardware_info: HardwareInfo = Field(..., description="Hardware information")
    location: NodeLocation = Field(..., description="Geographic location")
    configuration: NodeConfiguration = Field(..., description="Node configuration")
    poot_score: Optional[float] = Field(None, ge=0, le=100, description="Current PoOT score")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    
    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if not re.match(r'^node_[a-zA-Z0-9_-]+$', v):
            raise ValueError("Node ID must match pattern: ^node_[a-zA-Z0-9_-]+$")
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Node name must contain only alphanumeric characters, hyphens, and underscores")
        return v
    
    @field_validator('poot_score')
    @classmethod
    def validate_poot_score(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("PoOT score must be between 0 and 100")
        return v

class NodeCreateRequest(BaseModel):
    """Request model for creating a new node"""
    name: str = Field(..., min_length=3, max_length=100, description="Node name")
    node_type: NodeType = Field(..., description="Type of node")
    hardware_info: HardwareInfo = Field(..., description="Hardware information")
    location: NodeLocation = Field(..., description="Geographic location")
    initial_pool_id: Optional[str] = Field(None, description="Initial pool assignment", regex="^pool_[a-zA-Z0-9_-]+$")
    configuration: Optional[NodeConfiguration] = Field(None, description="Node configuration")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Node name must contain only alphanumeric characters, hyphens, and underscores")
        return v

class NodeUpdateRequest(BaseModel):
    """Request model for updating a node"""
    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Node name")
    node_type: Optional[NodeType] = Field(None, description="Type of node")
    pool_id: Optional[str] = Field(None, description="Pool assignment", regex="^pool_[a-zA-Z0-9_-]+$")
    status: Optional[NodeStatus] = Field(None, description="Node status")
    configuration: Optional[NodeConfiguration] = Field(None, description="Node configuration")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Node name must contain only alphanumeric characters, hyphens, and underscores")
        return v

# Resource monitoring models
class CPUMetrics(BaseModel):
    """CPU metrics"""
    usage_percent: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    cores: int = Field(..., ge=1, description="Number of CPU cores")
    frequency_mhz: float = Field(..., ge=0, description="CPU frequency in MHz")
    load_average: List[float] = Field(..., max_items=3, description="1min, 5min, 15min load averages")
    temperature_celsius: Optional[float] = Field(None, description="CPU temperature")

class MemoryMetrics(BaseModel):
    """Memory metrics"""
    total_bytes: int = Field(..., ge=0, description="Total memory in bytes")
    used_bytes: int = Field(..., ge=0, description="Used memory in bytes")
    free_bytes: int = Field(..., ge=0, description="Free memory in bytes")
    cached_bytes: int = Field(..., ge=0, description="Cached memory in bytes")
    swap_total_bytes: int = Field(..., ge=0, description="Total swap in bytes")
    swap_used_bytes: int = Field(..., ge=0, description="Used swap in bytes")

class DiskMetrics(BaseModel):
    """Disk metrics"""
    total_bytes: int = Field(..., ge=0, description="Total disk space in bytes")
    used_bytes: int = Field(..., ge=0, description="Used disk space in bytes")
    free_bytes: int = Field(..., ge=0, description="Free disk space in bytes")
    read_iops: int = Field(..., ge=0, description="Read operations per second")
    write_iops: int = Field(..., ge=0, description="Write operations per second")
    read_throughput_mbps: float = Field(..., ge=0, description="Read throughput in MB/s")
    write_throughput_mbps: float = Field(..., ge=0, description="Write throughput in MB/s")

class NetworkInterface(BaseModel):
    """Network interface information"""
    name: str = Field(..., description="Interface name")
    ip: str = Field(..., description="IP address")
    mac: str = Field(..., description="MAC address")
    status: str = Field(..., description="Interface status")
    bytes_in: int = Field(..., ge=0, description="Bytes received")
    bytes_out: int = Field(..., ge=0, description="Bytes sent")

class NetworkMetrics(BaseModel):
    """Network metrics"""
    interfaces: List[NetworkInterface] = Field(..., description="Network interfaces")
    total_bytes_in: int = Field(..., ge=0, description="Total bytes received")
    total_bytes_out: int = Field(..., ge=0, description="Total bytes sent")
    packets_in: int = Field(..., ge=0, description="Total packets received")
    packets_out: int = Field(..., ge=0, description="Total packets sent")
    errors_in: int = Field(..., ge=0, description="Receive errors")
    errors_out: int = Field(..., ge=0, description="Transmit errors")

class GPUMetrics(BaseModel):
    """GPU metrics"""
    usage_percent: float = Field(..., ge=0, le=100, description="GPU usage percentage")
    memory_used_bytes: int = Field(..., ge=0, description="Used GPU memory in bytes")
    memory_total_bytes: int = Field(..., ge=0, description="Total GPU memory in bytes")
    temperature_celsius: Optional[float] = Field(None, description="GPU temperature")

class NodeResources(BaseModel):
    """Node resource utilization"""
    node_id: str = Field(..., description="Node ID")
    timestamp: datetime = Field(..., description="Metrics timestamp")
    cpu: CPUMetrics = Field(..., description="CPU metrics")
    memory: MemoryMetrics = Field(..., description="Memory metrics")
    disk: DiskMetrics = Field(..., description="Disk metrics")
    network: NetworkMetrics = Field(..., description="Network metrics")
    gpu: Optional[GPUMetrics] = Field(None, description="GPU metrics")

class ResourceMetrics(BaseModel):
    """Resource metrics with time series data"""
    node_id: str = Field(..., description="Node ID")
    metric_type: Optional[str] = Field(None, description="Type of metrics")
    granularity: str = Field(..., description="Data granularity")
    start_time: datetime = Field(..., description="Start time")
    end_time: datetime = Field(..., description="End time")
    data_points: List[Dict[str, Any]] = Field(..., description="Time series data points")

# PoOT models
class PoOTScore(BaseModel):
    """PoOT score model"""
    node_id: str = Field(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$")
    score: float = Field(..., ge=0, le=100, description="PoOT score (0-100)")
    calculated_at: datetime = Field(..., description="Calculation timestamp")
    output_hash: str = Field(..., description="Hash of the output data")
    validation_status: str = Field(..., description="Validation status")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level of the score")

class PoOTValidation(BaseModel):
    """PoOT validation result"""
    node_id: str = Field(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$")
    validation_id: str = Field(..., description="Validation ID")
    is_valid: bool = Field(..., description="Whether PoOT is valid")
    score: float = Field(..., ge=0, le=100, description="PoOT score")
    confidence: float = Field(..., ge=0, le=1, description="Validation confidence")
    output_hash: str = Field(..., description="SHA-256 hash of output data")
    timestamp: datetime = Field(..., description="Validation timestamp")
    validation_time_ms: int = Field(..., ge=0, description="Validation time in milliseconds")
    errors: List[str] = Field(default_factory=list, description="Validation errors if any")

class PoOTValidationRequest(BaseModel):
    """PoOT validation request"""
    node_id: str = Field(..., description="Node ID", regex="^node_[a-zA-Z0-9_-]+$")
    output_data: str = Field(..., description="Base64 encoded output data")
    timestamp: datetime = Field(..., description="Output timestamp")
    nonce: str = Field(..., description="Nonce for validation")
    
    @field_validator('output_data')
    @classmethod
    def validate_output_data(cls, v):
        try:
            import base64
            decoded = base64.b64decode(v)
            if len(decoded) > 1024 * 1024:  # 1MB limit
                raise ValueError("Output data too large (max 1MB)")
        except Exception:
            raise ValueError("Invalid base64 encoded output data")
        return v
