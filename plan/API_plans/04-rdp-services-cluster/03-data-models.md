# RDP Services Cluster - Data Models

## Overview
This document defines the data models, schemas, and validation rules for the RDP Services Cluster. It includes Pydantic models for API requests/responses and MongoDB collection schemas for persistence.

## Pydantic Models

### RDP Server Models

#### RdpServerConfiguration
```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class DesktopEnvironment(str, Enum):
    XFCE = "xfce"
    GNOME = "gnome"
    KDE = "kde"
    LXDE = "lxde"

class ColorDepth(int, Enum):
    BIT_16 = 16
    BIT_24 = 24
    BIT_32 = 32

class RdpServerConfiguration(BaseModel):
    desktop_environment: DesktopEnvironment = Field(default=DesktopEnvironment.XFCE)
    resolution: str = Field(default="1920x1080", pattern=r"^\d{3,5}x\d{3,5}$")
    color_depth: ColorDepth = Field(default=ColorDepth.BIT_24)
    audio_enabled: bool = Field(default=True)
    clipboard_enabled: bool = Field(default=True)
    drive_redirection: bool = Field(default=False)
    printer_redirection: bool = Field(default=False)

    class Config:
        use_enum_values = True
```

#### RdpServerResources
```python
from pydantic import BaseModel, Field, validator

class RdpServerResources(BaseModel):
    cpu_limit: float = Field(..., ge=0.1, le=8.0, description="CPU cores limit")
    memory_limit: int = Field(..., ge=512, le=16384, description="Memory limit in MB")
    disk_limit: int = Field(..., ge=1024, le=102400, description="Disk limit in MB")
    network_bandwidth: int = Field(..., ge=100, le=10000, description="Network bandwidth in Mbps")

    @validator('cpu_limit')
    def validate_cpu_limit(cls, v):
        if v <= 0:
            raise ValueError('CPU limit must be positive')
        return round(v, 2)

    @validator('memory_limit', 'disk_limit')
    def validate_memory_disk(cls, v):
        if v % 256 != 0:
            raise ValueError('Memory and disk limits must be multiples of 256 MB')
        return v
```

#### RdpServerCreateRequest
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID

class RdpServerCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    user_id: UUID = Field(...)
    configuration: Optional[RdpServerConfiguration] = None
    resources: Optional[RdpServerResources] = None

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty or whitespace only')
        return v.strip()
```

#### RdpServerUpdateRequest
```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class RdpServerUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    configuration: Optional[RdpServerConfiguration] = None
    resources: Optional[RdpServerResources] = None

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty or whitespace only')
        return v.strip() if v else None
```

#### RdpServerResponse
```python
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class ServerStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class RdpServerResponse(BaseModel):
    server_id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    status: ServerStatus
    port: int = Field(..., ge=1024, le=65535)
    host: str
    configuration: RdpServerConfiguration
    resources: RdpServerResources
    created_at: datetime
    updated_at: datetime
    last_started_at: Optional[datetime]
    last_stopped_at: Optional[datetime]

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
```

### XRDP Models

#### XrdpGlobalSettings
```python
from pydantic import BaseModel, Field
from enum import Enum

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"

class XrdpGlobalSettings(BaseModel):
    port: int = Field(default=3389, ge=1024, le=65535)
    use_ssl: bool = Field(default=True)
    ssl_cert_path: str = Field(default="/etc/ssl/certs/xrdp.crt")
    ssl_key_path: str = Field(default="/etc/ssl/private/xrdp.key")
    log_level: LogLevel = Field(default=LogLevel.INFO)
    max_connections: int = Field(default=100, ge=1, le=1000)

    class Config:
        use_enum_values = True
```

#### XrdpSecuritySettings
```python
from pydantic import BaseModel, Field
from enum import Enum

class AuthMethod(str, Enum):
    PASSWORD = "password"
    CERTIFICATE = "certificate"
    BOTH = "both"

class EncryptionLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class XrdpSecuritySettings(BaseModel):
    authentication_method: AuthMethod = Field(default=AuthMethod.PASSWORD)
    session_timeout: int = Field(default=3600, ge=300, le=86400, description="Session timeout in seconds")
    idle_timeout: int = Field(default=1800, ge=60, le=7200, description="Idle timeout in seconds")
    encryption_level: EncryptionLevel = Field(default=EncryptionLevel.HIGH)

    class Config:
        use_enum_values = True
```

#### XrdpPerformanceSettings
```python
from pydantic import BaseModel, Field

class XrdpPerformanceSettings(BaseModel):
    compression: bool = Field(default=True)
    bitmap_cache: bool = Field(default=True)
    glyph_cache: bool = Field(default=True)
    max_bitmap_cache_size: int = Field(default=32000000, ge=1000000, le=100000000)
```

#### XrdpConfigUpdateRequest
```python
from pydantic import BaseModel
from typing import Optional

class XrdpConfigUpdateRequest(BaseModel):
    global_settings: Optional[XrdpGlobalSettings] = None
    security_settings: Optional[XrdpSecuritySettings] = None
    performance_settings: Optional[XrdpPerformanceSettings] = None
```

### Session Models

#### RdpClientInfo
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class RdpClientInfo(BaseModel):
    client_name: str = Field(..., max_length=255)
    client_version: str = Field(..., max_length=50)
    client_ip: str = Field(...)
    resolution: str = Field(..., pattern=r"^\d{3,5}x\d{3,5}$")
    color_depth: int = Field(..., ge=16, le=32)

    @validator('client_ip')
    def validate_ip(cls, v):
        # Basic IP validation
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, v):
            raise ValueError('Invalid IP address format')
        return v
```

#### RdpSessionCreateRequest
```python
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class RdpSessionCreateRequest(BaseModel):
    server_id: UUID = Field(...)
    user_id: UUID = Field(...)
    client_info: Optional[RdpClientInfo] = None
```

#### RdpSessionConnectionInfo
```python
from pydantic import BaseModel, Field

class RdpSessionConnectionInfo(BaseModel):
    client_ip: str
    client_port: int = Field(..., ge=1, le=65535)
    server_ip: str
    server_port: int = Field(..., ge=1, le=65535)
    protocol_version: str
    encryption_level: str
```

#### RdpSessionResponse
```python
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    TERMINATED = "terminated"

class RdpSessionResponse(BaseModel):
    session_id: UUID
    server_id: UUID
    user_id: UUID
    status: SessionStatus
    connection_info: Optional[RdpSessionConnectionInfo]
    created_at: datetime
    connected_at: Optional[datetime]
    last_activity: Optional[datetime]
    terminated_at: Optional[datetime]

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
```

### Resource Models

#### ResourceUsage
```python
from pydantic import BaseModel, Field

class ResourceUsage(BaseModel):
    cpu_percent: float = Field(..., ge=0, le=100)
    memory_percent: float = Field(..., ge=0, le=100)
    memory_used: int = Field(..., ge=0, description="Memory used in MB")
    memory_total: int = Field(..., ge=0, description="Total memory in MB")
    disk_usage_percent: float = Field(..., ge=0, le=100)
    disk_used: int = Field(..., ge=0, description="Disk used in MB")
    disk_total: int = Field(..., ge=0, description="Total disk in MB")
    network_in: int = Field(..., ge=0, description="Network input in KB/s")
    network_out: int = Field(..., ge=0, description="Network output in KB/s")
```

#### SessionResourceUsage
```python
from pydantic import BaseModel, Field
from uuid import UUID

class SessionResourceUsage(BaseModel):
    session_id: UUID
    cpu_percent: float = Field(..., ge=0, le=100)
    memory_percent: float = Field(..., ge=0, le=100)
    network_in: int = Field(..., ge=0, description="Network input in KB/s")
    network_out: int = Field(..., ge=0, description="Network output in KB/s")
```

#### ResourceAlert
```python
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ResourceType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"

class ResourceAlert(BaseModel):
    alert_id: UUID
    severity: AlertSeverity
    resource_type: ResourceType
    resource_id: str
    threshold: float
    current_value: float
    message: str
    created_at: datetime
    resolved_at: Optional[datetime]
    resolved: bool

    class Config:
        use_enum_values = True
```

### Common Models

#### PaginationInfo
```python
from pydantic import BaseModel, Field

class PaginationInfo(BaseModel):
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    pages: int = Field(..., ge=0)
```

#### ErrorResponse
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Error code (e.g., LUCID_ERR_2001)")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: UUID = Field(..., description="Request ID for tracking")
    timestamp: datetime = Field(..., description="Error timestamp")
    service: str = Field(..., description="Service that generated the error")
    version: str = Field(default="v1", description="API version")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

## MongoDB Collection Schemas

### RDP Servers Collection

**Collection Name**: `rdp_servers`

**Schema**:
```json
{
  "_id": "ObjectId",
  "server_id": "UUID (indexed, unique)",
  "user_id": "UUID (indexed)",
  "name": "String (1-255 chars)",
  "description": "String (max 1000 chars, nullable)",
  "status": "Enum (running, stopped, error, maintenance)",
  "port": "Integer (1024-65535)",
  "host": "String",
  "configuration": {
    "desktop_environment": "Enum (xfce, gnome, kde, lxde)",
    "resolution": "String (e.g., 1920x1080)",
    "color_depth": "Integer (16, 24, 32)",
    "audio_enabled": "Boolean",
    "clipboard_enabled": "Boolean",
    "drive_redirection": "Boolean",
    "printer_redirection": "Boolean"
  },
  "resources": {
    "cpu_limit": "Float (0.1-8.0)",
    "memory_limit": "Integer (512-16384 MB)",
    "disk_limit": "Integer (1024-102400 MB)",
    "network_bandwidth": "Integer (100-10000 Mbps)"
  },
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "last_started_at": "ISODate (nullable)",
  "last_stopped_at": "ISODate (nullable)"
}
```

**Indexes**:
```javascript
db.rdp_servers.createIndex({ "server_id": 1 }, { unique: true });
db.rdp_servers.createIndex({ "user_id": 1 });
db.rdp_servers.createIndex({ "status": 1 });
db.rdp_servers.createIndex({ "created_at": -1 });
```

### RDP Sessions Collection

**Collection Name**: `rdp_sessions`

**Schema**:
```json
{
  "_id": "ObjectId",
  "session_id": "UUID (indexed, unique)",
  "server_id": "UUID (indexed)",
  "user_id": "UUID (indexed)",
  "status": "Enum (active, disconnected, terminated)",
  "connection_info": {
    "client_ip": "String",
    "client_port": "Integer",
    "server_ip": "String",
    "server_port": "Integer",
    "protocol_version": "String",
    "encryption_level": "String"
  },
  "client_info": {
    "client_name": "String",
    "client_version": "String",
    "client_ip": "String",
    "resolution": "String",
    "color_depth": "Integer"
  },
  "created_at": "ISODate",
  "connected_at": "ISODate (nullable)",
  "last_activity": "ISODate (nullable)",
  "terminated_at": "ISODate (nullable)"
}
```

**Indexes**:
```javascript
db.rdp_sessions.createIndex({ "session_id": 1 }, { unique: true });
db.rdp_sessions.createIndex({ "server_id": 1 });
db.rdp_sessions.createIndex({ "user_id": 1 });
db.rdp_sessions.createIndex({ "status": 1 });
db.rdp_sessions.createIndex({ "created_at": -1 });
db.rdp_sessions.createIndex({ "last_activity": -1 });
```

### XRDP Configuration Collection

**Collection Name**: `xrdp_configs`

**Schema**:
```json
{
  "_id": "ObjectId",
  "config_version": "String",
  "global_settings": {
    "port": "Integer",
    "use_ssl": "Boolean",
    "ssl_cert_path": "String",
    "ssl_key_path": "String",
    "log_level": "Enum (DEBUG, INFO, WARN, ERROR)",
    "max_connections": "Integer"
  },
  "security_settings": {
    "authentication_method": "Enum (password, certificate, both)",
    "session_timeout": "Integer",
    "idle_timeout": "Integer",
    "encryption_level": "Enum (low, medium, high)"
  },
  "performance_settings": {
    "compression": "Boolean",
    "bitmap_cache": "Boolean",
    "glyph_cache": "Boolean",
    "max_bitmap_cache_size": "Integer"
  },
  "last_updated": "ISODate",
  "updated_by": "UUID"
}
```

**Indexes**:
```javascript
db.xrdp_configs.createIndex({ "config_version": 1 });
db.xrdp_configs.createIndex({ "last_updated": -1 });
```

### Resource Monitoring Collection

**Collection Name**: `resource_metrics`

**Schema**:
```json
{
  "_id": "ObjectId",
  "metric_id": "UUID (indexed)",
  "server_id": "UUID (indexed, nullable)",
  "session_id": "UUID (indexed, nullable)",
  "metric_type": "Enum (server, session, system)",
  "timestamp": "ISODate (indexed)",
  "cpu_percent": "Float",
  "memory_percent": "Float",
  "memory_used": "Integer (MB)",
  "memory_total": "Integer (MB)",
  "disk_usage_percent": "Float (nullable)",
  "disk_used": "Integer (MB, nullable)",
  "disk_total": "Integer (MB, nullable)",
  "network_in": "Integer (KB/s)",
  "network_out": "Integer (KB/s)"
}
```

**Indexes**:
```javascript
db.resource_metrics.createIndex({ "metric_id": 1 });
db.resource_metrics.createIndex({ "server_id": 1, "timestamp": -1 });
db.resource_metrics.createIndex({ "session_id": 1, "timestamp": -1 });
db.resource_metrics.createIndex({ "timestamp": -1 });
// TTL index - auto-delete metrics older than 7 days
db.resource_metrics.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 604800 });
```

### Resource Alerts Collection

**Collection Name**: `resource_alerts`

**Schema**:
```json
{
  "_id": "ObjectId",
  "alert_id": "UUID (indexed, unique)",
  "severity": "Enum (low, medium, high, critical)",
  "resource_type": "Enum (cpu, memory, disk, network)",
  "resource_id": "String (server_id or session_id)",
  "threshold": "Float",
  "current_value": "Float",
  "message": "String",
  "created_at": "ISODate (indexed)",
  "resolved_at": "ISODate (nullable)",
  "resolved": "Boolean (indexed)",
  "resolved_by": "UUID (nullable)"
}
```

**Indexes**:
```javascript
db.resource_alerts.createIndex({ "alert_id": 1 }, { unique: true });
db.resource_alerts.createIndex({ "severity": 1, "resolved": 1 });
db.resource_alerts.createIndex({ "resource_id": 1 });
db.resource_alerts.createIndex({ "created_at": -1 });
db.resource_alerts.createIndex({ "resolved": 1 });
```

## Validation Rules

### Global Validation Rules

1. **UUID Validation**: All UUID fields must be valid UUID v4 format
2. **Timestamp Validation**: All timestamps must be ISO 8601 format
3. **String Trimming**: All string fields are trimmed before validation
4. **Null Handling**: Optional fields can be null but not empty strings

### RDP Server Validation

1. **Name**: 
   - Required, 1-255 characters
   - Cannot be only whitespace
   - Trimmed before storage

2. **Port Allocation**:
   - Range: 33890-33999 for dynamic RDP instances
   - Must not conflict with existing allocations
   - Standard RDP port 3389 managed separately

3. **Resource Limits**:
   - CPU: 0.1-8.0 cores, rounded to 2 decimal places
   - Memory: 512-16384 MB, must be multiples of 256
   - Disk: 1024-102400 MB, must be multiples of 256
   - Network: 100-10000 Mbps

4. **Resolution Format**:
   - Pattern: `^\d{3,5}x\d{3,5}$`
   - Examples: "1920x1080", "1280x720", "3840x2160"

### Session Validation

1. **Session Timeout**:
   - Default: 3600 seconds (1 hour)
   - Range: 300-86400 seconds

2. **Idle Timeout**:
   - Default: 1800 seconds (30 minutes)
   - Range: 60-7200 seconds
   - Must be less than session_timeout

3. **Client IP**:
   - Must be valid IPv4 address
   - Format: `^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$`

### Resource Validation

1. **Percentage Values**:
   - Range: 0-100
   - Rounded to 2 decimal places

2. **Memory/Disk Values**:
   - Must be non-negative integers
   - Represented in MB

3. **Network Values**:
   - Must be non-negative integers
   - Represented in KB/s

## Data Transformation Patterns

### UUID Handling
```python
from uuid import UUID

def serialize_uuid(uuid_obj: UUID) -> str:
    """Convert UUID to string for JSON serialization"""
    return str(uuid_obj)

def deserialize_uuid(uuid_str: str) -> UUID:
    """Convert string to UUID for processing"""
    return UUID(uuid_str)
```

### Datetime Handling
```python
from datetime import datetime

def serialize_datetime(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string"""
    return dt.isoformat()

def deserialize_datetime(dt_str: str) -> datetime:
    """Convert ISO 8601 string to datetime"""
    return datetime.fromisoformat(dt_str)
```

### Enum Handling
```python
from enum import Enum

def serialize_enum(enum_obj: Enum) -> str:
    """Convert enum to string value"""
    return enum_obj.value

def deserialize_enum(enum_str: str, enum_class: type) -> Enum:
    """Convert string to enum instance"""
    return enum_class(enum_str)
```

### Resource Conversion
```python
def mb_to_bytes(mb: int) -> int:
    """Convert megabytes to bytes"""
    return mb * 1024 * 1024

def bytes_to_mb(bytes_val: int) -> int:
    """Convert bytes to megabytes"""
    return bytes_val // (1024 * 1024)

def kbps_to_bps(kbps: int) -> int:
    """Convert KB/s to bytes/s"""
    return kbps * 1024

def bps_to_kbps(bps: int) -> int:
    """Convert bytes/s to KB/s"""
    return bps // 1024
```

## Error Code Mapping

All error responses follow the standardized error format:

```python
ERROR_CODES = {
    # RDP Server Errors (LUCID_ERR_20XX)
    "LUCID_ERR_2001": "RDP server not found",
    "LUCID_ERR_2002": "RDP server creation failed",
    "LUCID_ERR_2003": "RDP server start failed",
    "LUCID_ERR_2004": "RDP server stop failed",
    "LUCID_ERR_2005": "RDP server restart failed",
    "LUCID_ERR_2006": "RDP server configuration invalid",
    "LUCID_ERR_2007": "RDP server port allocation failed",
    "LUCID_ERR_2008": "RDP server resource limit exceeded",
    
    # XRDP Errors (LUCID_ERR_21XX)
    "LUCID_ERR_2101": "XRDP service not available",
    "LUCID_ERR_2102": "XRDP configuration invalid",
    "LUCID_ERR_2103": "XRDP service start failed",
    "LUCID_ERR_2104": "XRDP service stop failed",
    "LUCID_ERR_2105": "XRDP service restart failed",
    "LUCID_ERR_2106": "XRDP SSL configuration error",
    
    # Session Errors (LUCID_ERR_22XX)
    "LUCID_ERR_2201": "RDP session not found",
    "LUCID_ERR_2202": "RDP session creation failed",
    "LUCID_ERR_2203": "RDP session connection failed",
    "LUCID_ERR_2204": "RDP session termination failed",
    "LUCID_ERR_2205": "RDP session already connected",
    "LUCID_ERR_2206": "RDP session timeout",
    "LUCID_ERR_2207": "RDP session authentication failed",
    
    # Resource Errors (LUCID_ERR_23XX)
    "LUCID_ERR_2301": "Resource limit exceeded",
    "LUCID_ERR_2302": "Resource monitoring failed",
    "LUCID_ERR_2303": "Resource allocation failed",
    "LUCID_ERR_2304": "Resource cleanup failed",
    "LUCID_ERR_2305": "Resource alert creation failed",
}
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10

