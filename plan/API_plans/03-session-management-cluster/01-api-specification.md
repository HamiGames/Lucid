# 01. API Specification

## Overview

The Session Management API provides comprehensive REST endpoints for managing RDP sessions, including creation, recording, processing, and retrieval operations. All endpoints follow RESTful conventions and return JSON responses.

## Base URL

```
https://api-sessions.lucid.example/api/v1/sessions
```

## Authentication

All API endpoints require authentication using JWT Bearer tokens:

```http
Authorization: Bearer <jwt-token>
```

## Rate Limiting

| Endpoint Type | Rate Limit | Window |
|---------------|------------|---------|
| Session Creation | 10 requests | 1 minute |
| Session Status | 100 requests | 1 minute |
| Chunk Operations | 1000 requests | 1 minute |
| Bulk Operations | 5 requests | 1 minute |

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": "LUCID_ERR_3001",
    "message": "Session not found",
    "details": {
      "session_id": "sess-12345"
    },
    "request_id": "req-uuid-here",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## Endpoints

### 1. Session Management

#### Create Session
```http
POST /api/v1/sessions
```

**Request Body:**
```json
{
  "name": "Development Session",
  "description": "Development environment session",
  "rdp_config": {
    "host": "192.168.1.100",
    "port": 3389,
    "username": "developer",
    "domain": "WORKGROUP"
  },
  "recording_config": {
    "frame_rate": 30,
    "resolution": "1920x1080",
    "quality": "high",
    "compression": "zstd"
  },
  "storage_config": {
    "retention_days": 30,
    "max_size_gb": 10,
    "encryption_enabled": true
  },
  "metadata": {
    "project": "lucid-rdp",
    "environment": "development",
    "tags": ["dev", "testing"]
  }
}
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "status": "created",
  "created_at": "2024-01-01T00:00:00Z",
  "rdp_config": {
    "host": "192.168.1.100",
    "port": 3389,
    "username": "developer",
    "domain": "WORKGROUP"
  },
  "recording_config": {
    "frame_rate": 30,
    "resolution": "1920x1080",
    "quality": "high",
    "compression": "zstd"
  },
  "storage_config": {
    "retention_days": 30,
    "max_size_gb": 10,
    "encryption_enabled": true
  },
  "metadata": {
    "project": "lucid-rdp",
    "environment": "development",
    "tags": ["dev", "testing"]
  }
}
```

#### Get Session
```http
GET /api/v1/sessions/{session_id}
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "status": "recording",
  "created_at": "2024-01-01T00:00:00Z",
  "started_at": "2024-01-01T00:01:00Z",
  "rdp_config": {
    "host": "192.168.1.100",
    "port": 3389,
    "username": "developer",
    "domain": "WORKGROUP"
  },
  "recording_config": {
    "frame_rate": 30,
    "resolution": "1920x1080",
    "quality": "high",
    "compression": "zstd"
  },
  "storage_config": {
    "retention_days": 30,
    "max_size_gb": 10,
    "encryption_enabled": true
  },
  "metadata": {
    "project": "lucid-rdp",
    "environment": "development",
    "tags": ["dev", "testing"]
  },
  "statistics": {
    "duration_seconds": 3600,
    "chunks_count": 108000,
    "size_bytes": 1073741824,
    "frame_count": 108000
  }
}
```

#### List Sessions
```http
GET /api/v1/sessions
```

**Query Parameters:**
- `status` (optional): Filter by session status
- `project` (optional): Filter by project name
- `environment` (optional): Filter by environment
- `limit` (optional): Number of results per page (default: 50, max: 100)
- `offset` (optional): Number of results to skip (default: 0)

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "sess-12345",
      "name": "Development Session",
      "status": "recording",
      "created_at": "2024-01-01T00:00:00Z",
      "metadata": {
        "project": "lucid-rdp",
        "environment": "development"
      },
      "statistics": {
        "duration_seconds": 3600,
        "chunks_count": 108000,
        "size_bytes": 1073741824
      }
    }
  ],
  "pagination": {
    "total": 100,
    "limit": 50,
    "offset": 0,
    "has_next": true
  }
}
```

#### Update Session
```http
PUT /api/v1/sessions/{session_id}
```

**Request Body:**
```json
{
  "name": "Updated Session Name",
  "description": "Updated description",
  "recording_config": {
    "frame_rate": 60,
    "quality": "ultra"
  },
  "metadata": {
    "project": "lucid-rdp",
    "environment": "production",
    "tags": ["prod", "critical"]
  }
}
```

#### Delete Session
```http
DELETE /api/v1/sessions/{session_id}
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "status": "deleted",
  "deleted_at": "2024-01-01T00:00:00Z"
}
```

### 2. Session Control

#### Start Recording
```http
POST /api/v1/sessions/{session_id}/start
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "status": "recording",
  "started_at": "2024-01-01T00:01:00Z",
  "recording_url": "rtsp://recorder:8084/sessions/sess-12345"
}
```

#### Stop Recording
```http
POST /api/v1/sessions/{session_id}/stop
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "status": "stopped",
  "stopped_at": "2024-01-01T00:30:00Z",
  "final_statistics": {
    "duration_seconds": 1740,
    "chunks_count": 52200,
    "size_bytes": 536870912,
    "frame_count": 52200
  }
}
```

#### Pause Recording
```http
POST /api/v1/sessions/{session_id}/pause
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "status": "paused",
  "paused_at": "2024-01-01T00:15:00Z"
}
```

#### Resume Recording
```http
POST /api/v1/sessions/{session_id}/resume
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "status": "recording",
  "resumed_at": "2024-01-01T00:16:00Z"
}
```

### 3. Chunk Management

#### List Chunks
```http
GET /api/v1/sessions/{session_id}/chunks
```

**Query Parameters:**
- `limit` (optional): Number of results per page (default: 100, max: 1000)
- `offset` (optional): Number of results to skip (default: 0)
- `status` (optional): Filter by chunk status
- `start_time` (optional): Filter chunks after timestamp
- `end_time` (optional): Filter chunks before timestamp

**Response:**
```json
{
  "chunks": [
    {
      "chunk_id": "chunk-12345",
      "session_id": "sess-12345",
      "sequence_number": 1,
      "timestamp": "2024-01-01T00:01:00Z",
      "status": "processed",
      "size_bytes": 1048576,
      "duration_seconds": 1,
      "frame_count": 30,
      "merkle_hash": "abc123...",
      "storage_path": "/storage/chunks/chunk-12345.zstd"
    }
  ],
  "pagination": {
    "total": 108000,
    "limit": 100,
    "offset": 0,
    "has_next": true
  }
}
```

#### Get Chunk
```http
GET /api/v1/sessions/{session_id}/chunks/{chunk_id}
```

**Response:**
```json
{
  "chunk_id": "chunk-12345",
  "session_id": "sess-12345",
  "sequence_number": 1,
  "timestamp": "2024-01-01T00:01:00Z",
  "status": "processed",
  "size_bytes": 1048576,
  "duration_seconds": 1,
  "frame_count": 30,
  "merkle_hash": "abc123...",
  "storage_path": "/storage/chunks/chunk-12345.zstd",
  "processing_info": {
    "compression_ratio": 0.75,
    "encryption_enabled": true,
    "quality_score": 95.5
  }
}
```

#### Download Chunk
```http
GET /api/v1/sessions/{session_id}/chunks/{chunk_id}/download
```

**Response:** Binary chunk data with appropriate headers:
```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="chunk-12345.zstd"
Content-Length: 1048576
```

### 4. Pipeline Management

#### Get Pipeline Status
```http
GET /api/v1/sessions/{session_id}/pipeline
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "pipeline_status": "active",
  "stages": [
    {
      "stage_name": "recording",
      "status": "active",
      "last_processed": "2024-01-01T00:01:00Z",
      "metrics": {
        "frames_processed": 1800,
        "errors_count": 0,
        "processing_time_ms": 33
      }
    },
    {
      "stage_name": "compression",
      "status": "active",
      "last_processed": "2024-01-01T00:01:00Z",
      "metrics": {
        "chunks_processed": 60,
        "compression_ratio": 0.75,
        "processing_time_ms": 15
      }
    },
    {
      "stage_name": "encryption",
      "status": "active",
      "last_processed": "2024-01-01T00:01:00Z",
      "metrics": {
        "chunks_encrypted": 60,
        "encryption_time_ms": 8
      }
    },
    {
      "stage_name": "storage",
      "status": "active",
      "last_processed": "2024-01-01T00:01:00Z",
      "metrics": {
        "chunks_stored": 60,
        "storage_time_ms": 5
      }
    }
  ],
  "overall_metrics": {
    "total_processing_time_ms": 61,
    "throughput_fps": 30,
    "error_rate": 0.0
  }
}
```

#### Pause Pipeline
```http
POST /api/v1/sessions/{session_id}/pipeline/pause
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "pipeline_status": "paused",
  "paused_at": "2024-01-01T00:15:00Z"
}
```

#### Resume Pipeline
```http
POST /api/v1/sessions/{session_id}/pipeline/resume
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "pipeline_status": "active",
  "resumed_at": "2024-01-01T00:16:00Z"
}
```

### 5. Statistics and Analytics

#### Get Session Statistics
```http
GET /api/v1/sessions/{session_id}/statistics
```

**Response:**
```json
{
  "session_id": "sess-12345",
  "time_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-01T01:00:00Z"
  },
  "recording_stats": {
    "total_duration_seconds": 3600,
    "active_duration_seconds": 3540,
    "paused_duration_seconds": 60,
    "total_frames": 108000,
    "dropped_frames": 120,
    "average_fps": 29.97
  },
  "storage_stats": {
    "total_size_bytes": 1073741824,
    "compressed_size_bytes": 805306368,
    "compression_ratio": 0.75,
    "chunks_count": 108000,
    "average_chunk_size_bytes": 9951
  },
  "quality_stats": {
    "average_quality_score": 95.5,
    "min_quality_score": 85.0,
    "max_quality_score": 100.0,
    "quality_distribution": {
      "excellent": 0.85,
      "good": 0.12,
      "fair": 0.03,
      "poor": 0.00
    }
  },
  "performance_stats": {
    "average_processing_time_ms": 33,
    "max_processing_time_ms": 50,
    "min_processing_time_ms": 20,
    "error_rate": 0.001
  }
}
```

#### Get System Statistics
```http
GET /api/v1/sessions/statistics
```

**Response:**
```json
{
  "system_stats": {
    "total_sessions": 150,
    "active_sessions": 25,
    "total_storage_bytes": 16106127360,
    "average_session_duration_seconds": 7200
  },
  "performance_stats": {
    "average_processing_time_ms": 35,
    "system_throughput_fps": 750,
    "error_rate": 0.002
  },
  "storage_stats": {
    "total_capacity_bytes": 1099511627776,
    "used_capacity_bytes": 16106127360,
    "available_capacity_bytes": 108340540416
  }
}
```

### 6. Health and Monitoring

#### Health Check
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "pipeline_manager": "healthy",
    "session_recorder": "healthy",
    "chunk_processor": "healthy",
    "session_storage": "healthy",
    "session_api": "healthy"
  },
  "database": {
    "mongodb": "healthy",
    "redis": "healthy"
  },
  "storage": {
    "local_storage": "healthy",
    "available_space_bytes": 108340540416
  }
}
```

#### Metrics
```http
GET /api/v1/metrics
```

**Response:** Prometheus-formatted metrics
```
# HELP sessions_total Total number of sessions
# TYPE sessions_total counter
sessions_total{status="active"} 25
sessions_total{status="completed"} 125

# HELP chunks_processed_total Total number of chunks processed
# TYPE chunks_processed_total counter
chunks_processed_total{status="success"} 1080000
chunks_processed_total{status="error"} 120

# HELP processing_duration_seconds Processing duration in seconds
# TYPE processing_duration_seconds histogram
processing_duration_seconds_bucket{le="0.01"} 1000
processing_duration_seconds_bucket{le="0.05"} 5000
processing_duration_seconds_bucket{le="0.1"} 10000
processing_duration_seconds_count 1080000
processing_duration_seconds_sum 32400
```

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| LUCID_ERR_3001 | Session not found | The specified session does not exist |
| LUCID_ERR_3002 | Invalid session configuration | Session configuration is invalid |
| LUCID_ERR_3003 | Session already exists | Session with same ID already exists |
| LUCID_ERR_3004 | Recording not started | Cannot perform operation on non-recording session |
| LUCID_ERR_3005 | Chunk not found | The specified chunk does not exist |
| LUCID_ERR_3006 | Pipeline error | Pipeline processing error |
| LUCID_ERR_3007 | Storage error | Storage operation failed |
| LUCID_ERR_3008 | Compression error | Chunk compression failed |
| LUCID_ERR_3009 | Encryption error | Chunk encryption failed |
| LUCID_ERR_3010 | Rate limit exceeded | API rate limit exceeded |

## Request/Response Examples

### Create Session with Validation
```bash
curl -X POST "https://api-sessions.lucid.example/api/v1/sessions" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Session",
    "description": "Production environment monitoring",
    "rdp_config": {
      "host": "prod-server.lucid.example",
      "port": 3389,
      "username": "monitor",
      "domain": "LUCID"
    },
    "recording_config": {
      "frame_rate": 60,
      "resolution": "2560x1440",
      "quality": "ultra",
      "compression": "zstd"
    },
    "storage_config": {
      "retention_days": 90,
      "max_size_gb": 50,
      "encryption_enabled": true
    },
    "metadata": {
      "project": "lucid-rdp",
      "environment": "production",
      "tags": ["prod", "monitoring", "critical"]
    }
  }'
```

### Start Recording with Error Handling
```bash
curl -X POST "https://api-sessions.lucid.example/api/v1/sessions/sess-12345/start" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json"
```

### Get Session Statistics with Time Range
```bash
curl -X GET "https://api-sessions.lucid.example/api/v1/sessions/sess-12345/statistics" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-XX  
**Next Review**: 2024-04-XX
