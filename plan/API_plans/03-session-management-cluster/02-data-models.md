# 02. Data Models

## Overview

This document defines the data models, schemas, and validation rules for the Session Management Cluster. All models use Pydantic for validation and serialization, ensuring type safety and data integrity.

## Core Models

### Session Models

#### Session
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"

class RDPConfig(BaseModel):
    host: str = Field(..., min_length=1, max_length=255, description="RDP host address")
    port: int = Field(default=3389, ge=1, le=65535, description="RDP port")
    username: str = Field(..., min_length=1, max_length=255, description="RDP username")
    password: Optional[str] = Field(None, min_length=1, max_length=255, description="RDP password")
    domain: Optional[str] = Field(None, min_length=1, max_length=255, description="RDP domain")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    ignore_cert: bool = Field(default=False, description="Ignore certificate errors")
    
    @validator('host')
    def validate_host(cls, v):
        import re
        # Basic IP/hostname validation
        if not re.match(r'^[a-zA-Z0-9.-]+$', v):
            raise ValueError('Invalid host format')
        return v

class RecordingConfig(BaseModel):
    frame_rate: int = Field(default=30, ge=1, le=120, description="Recording frame rate")
    resolution: str = Field(default="1920x1080", description="Recording resolution")
    quality: str = Field(default="high", description="Recording quality")
    compression: str = Field(default="zstd", description="Compression algorithm")
    bitrate: Optional[int] = Field(None, ge=1000, le=50000000, description="Bitrate in kbps")
    audio_enabled: bool = Field(default=True, description="Enable audio recording")
    cursor_enabled: bool = Field(default=True, description="Record cursor movements")
    
    @validator('resolution')
    def validate_resolution(cls, v):
        import re
        if not re.match(r'^\d+x\d+$', v):
            raise ValueError('Resolution must be in format WIDTHxHEIGHT')
        width, height = map(int, v.split('x'))
        if width < 320 or width > 7680 or height < 240 or height > 4320:
            raise ValueError('Resolution must be between 320x240 and 7680x4320')
        return v
    
    @validator('quality')
    def validate_quality(cls, v):
        valid_qualities = ['low', 'medium', 'high', 'ultra']
        if v not in valid_qualities:
            raise ValueError(f'Quality must be one of: {valid_qualities}')
        return v
    
    @validator('compression')
    def validate_compression(cls, v):
        valid_compressions = ['none', 'zstd', 'lz4', 'gzip']
        if v not in valid_compressions:
            raise ValueError(f'Compression must be one of: {valid_compressions}')
        return v

class StorageConfig(BaseModel):
    retention_days: int = Field(default=30, ge=1, le=365, description="Retention period in days")
    max_size_gb: int = Field(default=10, ge=1, le=1000, description="Maximum size in GB")
    encryption_enabled: bool = Field(default=True, description="Enable encryption")
    compression_enabled: bool = Field(default=True, description="Enable compression")
    backup_enabled: bool = Field(default=False, description="Enable backup")
    archive_enabled: bool = Field(default=False, description="Enable archiving")

class SessionMetadata(BaseModel):
    project: Optional[str] = Field(None, max_length=100, description="Project name")
    environment: Optional[str] = Field(None, max_length=50, description="Environment")
    tags: List[str] = Field(default_factory=list, description="Session tags")
    description: Optional[str] = Field(None, max_length=500, description="Session description")
    owner: Optional[str] = Field(None, max_length=100, description="Session owner")
    priority: Optional[str] = Field(default="normal", description="Session priority")
    
    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        for tag in v:
            if len(tag) > 50:
                raise ValueError('Tag length cannot exceed 50 characters')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ['low', 'normal', 'high', 'critical']
        if v not in valid_priorities:
            raise ValueError(f'Priority must be one of: {valid_priorities}')
        return v

class SessionStatistics(BaseModel):
    duration_seconds: int = Field(default=0, ge=0, description="Total duration in seconds")
    chunks_count: int = Field(default=0, ge=0, description="Total number of chunks")
    size_bytes: int = Field(default=0, ge=0, description="Total size in bytes")
    frame_count: int = Field(default=0, ge=0, description="Total frame count")
    dropped_frames: int = Field(default=0, ge=0, description="Dropped frames count")
    error_count: int = Field(default=0, ge=0, description="Error count")
    average_fps: float = Field(default=0.0, ge=0.0, description="Average FPS")
    compression_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Compression ratio")

class Session(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, description="Unique session ID")
    name: str = Field(..., min_length=1, max_length=255, description="Session name")
    status: SessionStatus = Field(default=SessionStatus.CREATED, description="Session status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    stopped_at: Optional[datetime] = Field(None, description="Stop timestamp")
    rdp_config: RDPConfig = Field(..., description="RDP configuration")
    recording_config: RecordingConfig = Field(..., description="Recording configuration")
    storage_config: StorageConfig = Field(..., description="Storage configuration")
    metadata: SessionMetadata = Field(default_factory=SessionMetadata, description="Session metadata")
    statistics: SessionStatistics = Field(default_factory=SessionStatistics, description="Session statistics")
    
    @validator('session_id')
    def validate_session_id(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError('Session ID must contain only alphanumeric characters, hyphens, and underscores')
        return v
```

### Chunk Models

#### Chunk
```python
class ChunkStatus(str, Enum):
    RECORDED = "recorded"
    PROCESSING = "processing"
    COMPRESSED = "compressed"
    ENCRYPTED = "encrypted"
    STORED = "stored"
    FAILED = "failed"
    DELETED = "deleted"

class Chunk(BaseModel):
    chunk_id: str = Field(..., min_length=1, max_length=100, description="Unique chunk ID")
    session_id: str = Field(..., min_length=1, max_length=100, description="Parent session ID")
    sequence_number: int = Field(..., ge=1, description="Chunk sequence number")
    timestamp: datetime = Field(..., description="Chunk timestamp")
    status: ChunkStatus = Field(default=ChunkStatus.RECORDED, description="Chunk status")
    size_bytes: int = Field(..., ge=0, description="Chunk size in bytes")
    duration_seconds: float = Field(..., ge=0.0, description="Chunk duration in seconds")
    frame_count: int = Field(..., ge=0, description="Number of frames in chunk")
    merkle_hash: Optional[str] = Field(None, min_length=64, max_length=64, description="Merkle tree hash")
    storage_path: Optional[str] = Field(None, description="Storage path")
    compression_ratio: Optional[float] = Field(None, ge=0.0, le=1.0, description="Compression ratio")
    quality_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Quality score")
    encryption_key_id: Optional[str] = Field(None, description="Encryption key ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    
    @validator('chunk_id')
    def validate_chunk_id(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError('Chunk ID must contain only alphanumeric characters, hyphens, and underscores')
        return v
    
    @validator('merkle_hash')
    def validate_merkle_hash(cls, v):
        if v is not None:
            import re
            if not re.match(r'^[a-fA-F0-9]{64}$', v):
                raise ValueError('Merkle hash must be a 64-character hexadecimal string')
        return v
```

### Pipeline Models

#### Pipeline Stage
```python
class StageStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"

class StageMetrics(BaseModel):
    items_processed: int = Field(default=0, ge=0, description="Items processed")
    errors_count: int = Field(default=0, ge=0, description="Error count")
    processing_time_ms: float = Field(default=0.0, ge=0.0, description="Processing time in ms")
    throughput_per_second: float = Field(default=0.0, ge=0.0, description="Throughput per second")
    memory_usage_bytes: int = Field(default=0, ge=0, description="Memory usage in bytes")
    cpu_usage_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="CPU usage percentage")

class PipelineStage(BaseModel):
    stage_name: str = Field(..., min_length=1, max_length=50, description="Stage name")
    status: StageStatus = Field(default=StageStatus.INACTIVE, description="Stage status")
    last_processed: Optional[datetime] = Field(None, description="Last processed timestamp")
    metrics: StageMetrics = Field(default_factory=StageMetrics, description="Stage metrics")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, ge=0, description="Retry count")
    max_retries: int = Field(default=3, ge=0, description="Maximum retries")

class PipelineStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"

class OverallMetrics(BaseModel):
    total_processing_time_ms: float = Field(default=0.0, ge=0.0, description="Total processing time")
    throughput_fps: float = Field(default=0.0, ge=0.0, description="Throughput in FPS")
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Error rate")
    memory_usage_bytes: int = Field(default=0, ge=0, description="Total memory usage")
    cpu_usage_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Total CPU usage")

class Pipeline(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, description="Session ID")
    pipeline_status: PipelineStatus = Field(default=PipelineStatus.INACTIVE, description="Pipeline status")
    stages: List[PipelineStage] = Field(default_factory=list, description="Pipeline stages")
    overall_metrics: OverallMetrics = Field(default_factory=OverallMetrics, description="Overall metrics")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
```

### Request/Response Models

#### Create Session Request
```python
class CreateSessionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Session name")
    description: Optional[str] = Field(None, max_length=500, description="Session description")
    rdp_config: RDPConfig = Field(..., description="RDP configuration")
    recording_config: RecordingConfig = Field(default_factory=RecordingConfig, description="Recording configuration")
    storage_config: StorageConfig = Field(default_factory=StorageConfig, description="Storage configuration")
    metadata: SessionMetadata = Field(default_factory=SessionMetadata, description="Session metadata")
```

#### Update Session Request
```python
class UpdateSessionRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Session name")
    description: Optional[str] = Field(None, max_length=500, description="Session description")
    recording_config: Optional[RecordingConfig] = Field(None, description="Recording configuration")
    storage_config: Optional[StorageConfig] = Field(None, description="Storage configuration")
    metadata: Optional[SessionMetadata] = Field(None, description="Session metadata")
```

#### Session Response
```python
class SessionResponse(BaseModel):
    session_id: str = Field(..., description="Session ID")
    status: SessionStatus = Field(..., description="Session status")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    stopped_at: Optional[datetime] = Field(None, description="Stop timestamp")
    rdp_config: RDPConfig = Field(..., description="RDP configuration")
    recording_config: RecordingConfig = Field(..., description="Recording configuration")
    storage_config: StorageConfig = Field(..., description="Storage configuration")
    metadata: SessionMetadata = Field(..., description="Session metadata")
    statistics: SessionStatistics = Field(..., description="Session statistics")
```

#### Session List Response
```python
class SessionListResponse(BaseModel):
    sessions: List[SessionResponse] = Field(..., description="List of sessions")
    pagination: PaginationInfo = Field(..., description="Pagination information")

class PaginationInfo(BaseModel):
    total: int = Field(..., ge=0, description="Total number of items")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    offset: int = Field(..., ge=0, description="Offset")
    has_next: bool = Field(..., description="Has next page")
    has_previous: bool = Field(..., description="Has previous page")
```

#### Chunk List Response
```python
class ChunkResponse(BaseModel):
    chunk_id: str = Field(..., description="Chunk ID")
    session_id: str = Field(..., description="Session ID")
    sequence_number: int = Field(..., description="Sequence number")
    timestamp: datetime = Field(..., description="Timestamp")
    status: ChunkStatus = Field(..., description="Status")
    size_bytes: int = Field(..., description="Size in bytes")
    duration_seconds: float = Field(..., description="Duration in seconds")
    frame_count: int = Field(..., description="Frame count")
    merkle_hash: Optional[str] = Field(None, description="Merkle hash")
    storage_path: Optional[str] = Field(None, description="Storage path")
    processing_info: Optional[ProcessingInfo] = Field(None, description="Processing information")

class ProcessingInfo(BaseModel):
    compression_ratio: Optional[float] = Field(None, description="Compression ratio")
    encryption_enabled: bool = Field(default=False, description="Encryption enabled")
    quality_score: Optional[float] = Field(None, description="Quality score")

class ChunkListResponse(BaseModel):
    chunks: List[ChunkResponse] = Field(..., description="List of chunks")
    pagination: PaginationInfo = Field(..., description="Pagination information")
```

#### Pipeline Response
```python
class PipelineResponse(BaseModel):
    session_id: str = Field(..., description="Session ID")
    pipeline_status: PipelineStatus = Field(..., description="Pipeline status")
    stages: List[PipelineStage] = Field(..., description="Pipeline stages")
    overall_metrics: OverallMetrics = Field(..., description="Overall metrics")
```

#### Statistics Response
```python
class SessionStatisticsResponse(BaseModel):
    session_id: str = Field(..., description="Session ID")
    time_range: TimeRange = Field(..., description="Time range")
    recording_stats: RecordingStats = Field(..., description="Recording statistics")
    storage_stats: StorageStats = Field(..., description="Storage statistics")
    quality_stats: QualityStats = Field(..., description="Quality statistics")
    performance_stats: PerformanceStats = Field(..., description="Performance statistics")

class TimeRange(BaseModel):
    start: datetime = Field(..., description="Start time")
    end: datetime = Field(..., description="End time")

class RecordingStats(BaseModel):
    total_duration_seconds: int = Field(..., ge=0, description="Total duration")
    active_duration_seconds: int = Field(..., ge=0, description="Active duration")
    paused_duration_seconds: int = Field(..., ge=0, description="Paused duration")
    total_frames: int = Field(..., ge=0, description="Total frames")
    dropped_frames: int = Field(..., ge=0, description="Dropped frames")
    average_fps: float = Field(..., ge=0.0, description="Average FPS")

class StorageStats(BaseModel):
    total_size_bytes: int = Field(..., ge=0, description="Total size")
    compressed_size_bytes: int = Field(..., ge=0, description="Compressed size")
    compression_ratio: float = Field(..., ge=0.0, le=1.0, description="Compression ratio")
    chunks_count: int = Field(..., ge=0, description="Chunks count")
    average_chunk_size_bytes: int = Field(..., ge=0, description="Average chunk size")

class QualityStats(BaseModel):
    average_quality_score: float = Field(..., ge=0.0, le=100.0, description="Average quality score")
    min_quality_score: float = Field(..., ge=0.0, le=100.0, description="Minimum quality score")
    max_quality_score: float = Field(..., ge=0.0, le=100.0, description="Maximum quality score")
    quality_distribution: QualityDistribution = Field(..., description="Quality distribution")

class QualityDistribution(BaseModel):
    excellent: float = Field(..., ge=0.0, le=1.0, description="Excellent quality ratio")
    good: float = Field(..., ge=0.0, le=1.0, description="Good quality ratio")
    fair: float = Field(..., ge=0.0, le=1.0, description="Fair quality ratio")
    poor: float = Field(..., ge=0.0, le=1.0, description="Poor quality ratio")
    
    @validator('*')
    def validate_distribution(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Quality distribution values must be between 0.0 and 1.0')
        return v

class PerformanceStats(BaseModel):
    average_processing_time_ms: float = Field(..., ge=0.0, description="Average processing time")
    max_processing_time_ms: float = Field(..., ge=0.0, description="Maximum processing time")
    min_processing_time_ms: float = Field(..., ge=0.0, description="Minimum processing time")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Error rate")

class SystemStatisticsResponse(BaseModel):
    system_stats: SystemStats = Field(..., description="System statistics")
    performance_stats: PerformanceStats = Field(..., description="Performance statistics")
    storage_stats: SystemStorageStats = Field(..., description="Storage statistics")

class SystemStats(BaseModel):
    total_sessions: int = Field(..., ge=0, description="Total sessions")
    active_sessions: int = Field(..., ge=0, description="Active sessions")
    total_storage_bytes: int = Field(..., ge=0, description="Total storage bytes")
    average_session_duration_seconds: int = Field(..., ge=0, description="Average session duration")

class SystemStorageStats(BaseModel):
    total_capacity_bytes: int = Field(..., ge=0, description="Total capacity")
    used_capacity_bytes: int = Field(..., ge=0, description="Used capacity")
    available_capacity_bytes: int = Field(..., ge=0, description="Available capacity")
```

#### Error Response
```python
class ErrorResponse(BaseModel):
    error: ErrorInfo = Field(..., description="Error information")

class ErrorInfo(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Error code")
    message: str = Field(..., min_length=1, max_length=500, description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    request_id: str = Field(..., min_length=1, max_length=100, description="Request ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
```

#### Health Response
```python
class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"

class ServiceHealth(BaseModel):
    status: HealthStatus = Field(..., description="Service status")
    last_check: datetime = Field(..., description="Last health check")
    response_time_ms: Optional[float] = Field(None, ge=0.0, description="Response time")
    error_message: Optional[str] = Field(None, description="Error message")

class HealthResponse(BaseModel):
    status: HealthStatus = Field(..., description="Overall status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    services: Dict[str, ServiceHealth] = Field(..., description="Service health status")
    database: Dict[str, ServiceHealth] = Field(..., description="Database health status")
    storage: Dict[str, ServiceHealth] = Field(..., description="Storage health status")
```

## MongoDB Collections

### Sessions Collection
```javascript
// sessions collection schema
{
  _id: ObjectId,
  session_id: String, // unique index
  name: String,
  status: String, // enum: created, recording, paused, stopped, etc.
  created_at: Date,
  started_at: Date,
  stopped_at: Date,
  rdp_config: {
    host: String,
    port: Number,
    username: String,
    domain: String,
    use_tls: Boolean,
    ignore_cert: Boolean
  },
  recording_config: {
    frame_rate: Number,
    resolution: String,
    quality: String,
    compression: String,
    bitrate: Number,
    audio_enabled: Boolean,
    cursor_enabled: Boolean
  },
  storage_config: {
    retention_days: Number,
    max_size_gb: Number,
    encryption_enabled: Boolean,
    compression_enabled: Boolean,
    backup_enabled: Boolean,
    archive_enabled: Boolean
  },
  metadata: {
    project: String,
    environment: String,
    tags: [String],
    description: String,
    owner: String,
    priority: String
  },
  statistics: {
    duration_seconds: Number,
    chunks_count: Number,
    size_bytes: Number,
    frame_count: Number,
    dropped_frames: Number,
    error_count: Number,
    average_fps: Number,
    compression_ratio: Number
  },
  updated_at: Date
}

// Indexes
db.sessions.createIndex({ "session_id": 1 }, { unique: true })
db.sessions.createIndex({ "status": 1 })
db.sessions.createIndex({ "created_at": -1 })
db.sessions.createIndex({ "metadata.project": 1 })
db.sessions.createIndex({ "metadata.environment": 1 })
db.sessions.createIndex({ "metadata.tags": 1 })
```

### Chunks Collection
```javascript
// chunks collection schema
{
  _id: ObjectId,
  chunk_id: String, // unique index
  session_id: String, // foreign key to sessions
  sequence_number: Number,
  timestamp: Date,
  status: String, // enum: recorded, processing, stored, etc.
  size_bytes: Number,
  duration_seconds: Number,
  frame_count: Number,
  merkle_hash: String,
  storage_path: String,
  compression_ratio: Number,
  quality_score: Number,
  encryption_key_id: String,
  created_at: Date,
  processed_at: Date,
  updated_at: Date
}

// Indexes
db.chunks.createIndex({ "chunk_id": 1 }, { unique: true })
db.chunks.createIndex({ "session_id": 1, "sequence_number": 1 })
db.chunks.createIndex({ "session_id": 1, "timestamp": 1 })
db.chunks.createIndex({ "status": 1 })
db.chunks.createIndex({ "merkle_hash": 1 })
db.chunks.createIndex({ "created_at": -1 })
```

### Pipeline Collection
```javascript
// pipeline collection schema
{
  _id: ObjectId,
  session_id: String, // foreign key to sessions
  pipeline_status: String, // enum: inactive, active, paused, error
  stages: [{
    stage_name: String,
    status: String,
    last_processed: Date,
    metrics: {
      items_processed: Number,
      errors_count: Number,
      processing_time_ms: Number,
      throughput_per_second: Number,
      memory_usage_bytes: Number,
      cpu_usage_percent: Number
    },
    error_message: String,
    retry_count: Number,
    max_retries: Number
  }],
  overall_metrics: {
    total_processing_time_ms: Number,
    throughput_fps: Number,
    error_rate: Number,
    memory_usage_bytes: Number,
    cpu_usage_percent: Number
  },
  created_at: Date,
  updated_at: Date
}

// Indexes
db.pipeline.createIndex({ "session_id": 1 }, { unique: true })
db.pipeline.createIndex({ "pipeline_status": 1 })
db.pipeline.createIndex({ "updated_at": -1 })
```

## Validation Rules

### Session Validation
- Session ID must be unique across all sessions
- RDP host must be a valid IP address or hostname
- RDP port must be between 1 and 65535
- Frame rate must be between 1 and 120 FPS
- Resolution must be in format WIDTHxHEIGHT with valid dimensions
- Quality must be one of: low, medium, high, ultra
- Compression must be one of: none, zstd, lz4, gzip
- Retention days must be between 1 and 365
- Maximum size must be between 1 and 1000 GB
- Tags list cannot exceed 10 tags
- Each tag cannot exceed 50 characters

### Chunk Validation
- Chunk ID must be unique across all chunks
- Sequence number must be positive and unique within session
- Size must be non-negative
- Duration must be non-negative
- Frame count must be non-negative
- Merkle hash must be 64-character hexadecimal string
- Compression ratio must be between 0.0 and 1.0
- Quality score must be between 0.0 and 100.0

### Pipeline Validation
- Session ID must exist in sessions collection
- Pipeline status must be valid enum value
- Stage names must be unique within pipeline
- Metrics values must be non-negative
- Error rates must be between 0.0 and 1.0
- CPU and memory usage must be between 0.0 and 100.0

## Data Relationships

### Primary Relationships
- **Session → Chunks**: One-to-many relationship
- **Session → Pipeline**: One-to-one relationship
- **Session → Statistics**: One-to-one relationship

### Foreign Key Constraints
- Chunk.session_id must reference Session.session_id
- Pipeline.session_id must reference Session.session_id
- All foreign keys must exist before insertion

### Cascade Operations
- Deleting a session should delete all associated chunks
- Deleting a session should delete the associated pipeline
- Updating session status should update pipeline status

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-XX  
**Next Review**: 2024-04-XX
