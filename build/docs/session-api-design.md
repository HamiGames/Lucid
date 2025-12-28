# Session API Container Design Document

**Version:** 1.0.0  
**Last Updated:** 2025-12-28  
**Service:** `lucid-session-api`  
**Container Name:** `session-api`  
**Purpose:** REST API service for session management operations in the Lucid RDP system

This document provides a comprehensive design reference for the `session-api` container, documenting its architecture, configuration, implementation patterns, and operational requirements.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Docker Compose Configuration](#3-docker-compose-configuration)
4. [Directory Structure](#4-directory-structure)
5. [Module Organization](#5-module-organization)
6. [Configuration Management](#6-configuration-management)
7. [API Endpoints](#7-api-endpoints)
8. [Dependencies](#8-dependencies)
9. [Volume Mounts and Permissions](#9-volume-mounts-and-permissions)
10. [Security Configuration](#10-security-configuration)
11. [Build Process](#11-build-process)
12. [Health Checks](#12-health-checks)
13. [Error Handling](#13-error-handling)
14. [Integration Patterns](#14-integration-patterns)

---

## 1. Overview

### 1.1 Purpose

The `session-api` service provides a REST API for managing RDP sessions in the Lucid system. It handles:

- Session lifecycle management (create, read, update, delete)
- Recording control (start, stop, pause, resume)
- Chunk retrieval and download
- Pipeline status monitoring
- Session statistics and metrics

### 1.2 Service Identity

- **Service Name:** `lucid-session-api`
- **Container Name:** `session-api`
- **Image:** `pickme/lucid-session-api:latest-arm64`
- **Port:** `8113` (HTTP)
- **Protocol:** REST API (FastAPI)
- **Version:** `1.0.0`

### 1.3 Key Features

- **Distroless Container:** Minimal attack surface using `gcr.io/distroless/python3-debian12`
- **FastAPI Framework:** Modern async Python web framework
- **Configuration Management:** Pydantic Settings with YAML/JSON file support and environment variable overrides
- **Storage Integration:** Uses `SessionStorage` and `ChunkStore` from `sessions.storage` module
- **Pipeline Integration:** Integrates with `SessionPipeline` from `sessions.core` module
- **MongoDB & Redis:** Primary data stores for session metadata and caching
- **Graceful Degradation:** Handles missing optional modules (e.g., recorder) gracefully

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    session-api Container                     │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   main.py    │  │   routes.py  │  │ session_api  │      │
│  │  (FastAPI)   │──│  (Router)    │──│   (Logic)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   config.py  │  │ entrypoint.py│  │   __init__   │      │
│  │  (Settings)  │  │  (Startup)   │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Shared Modules (from /app/sessions/)         │   │
│  │  • sessions.storage (SessionStorage, ChunkStore)     │   │
│  │  • sessions.core (SessionPipeline)                   │   │
│  │  • sessions.encryption (SessionEncryptor)            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │  External Services                  │
        │  • MongoDB (lucid-mongodb)          │
        │  • Redis (lucid-redis)              │
        │  • Elasticsearch (optional)         │
        └─────────────────────────────────────┘
```

### 2.2 Request Flow

1. **Request Reception:** FastAPI receives HTTP request
2. **Routing:** `routes.py` routes request to appropriate handler
3. **Dependency Injection:** `get_session_api()` provides `SessionAPI` instance
4. **Business Logic:** `SessionAPI` processes request using `SessionStorage` and `ChunkStore`
5. **Data Access:** Storage modules interact with MongoDB/Redis
6. **Response:** FastAPI returns JSON response

### 2.3 Component Responsibilities

- **`main.py`:** FastAPI application setup, lifespan management, middleware configuration
- **`routes.py`:** API endpoint definitions and request/response models
- **`session_api.py`:** Business logic for session management operations
- **`config.py`:** Configuration loading and validation (Pydantic Settings)
- **`entrypoint.py`:** Container entrypoint script (Python-based for distroless)

---

## 3. Docker Compose Configuration

### 3.1 Service Definition

```yaml
session-api:
  image: pickme/lucid-session-api:latest-arm64
  container_name: session-api
  restart: unless-stopped
  env_file:
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.application
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.session-api
  networks:
    - lucid-pi-network
  ports:
    - "8113:8113"
  volumes:
    - /mnt/myssd/Lucid/Lucid/data/session-api:/app/data:rw
    - /mnt/myssd/Lucid/Lucid/logs/session-api:/app/logs:rw
    - session-api-cache:/tmp/api
  environment:
    - LUCID_ENV=production
    - LUCID_PLATFORM=arm64
    - SESSION_API_HOST=session-api
    - SESSION_API_PORT=8113
    - SESSION_API_URL=http://session-api:8113
    - MONGODB_URL=${MONGODB_URL:?MONGODB_URL not set}
    - REDIS_URL=${REDIS_URL}
    - ELASTICSEARCH_URL=${ELASTICSEARCH_URL}
    - API_GATEWAY_URL=${API_GATEWAY_URL}
    - BLOCKCHAIN_ENGINE_URL=${BLOCKCHAIN_ENGINE_URL}
  user: "65532:65532"
  security_opt:
    - no-new-privileges:true
    - seccomp:unconfined
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE
  read_only: true
  tmpfs:
    - /tmp:noexec,nosuid,size=100m
  healthcheck:
    test: ["CMD", "/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8113)); s.close(); exit(0 if result == 0 else 1)"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  labels:
    - "lucid.service=session-api"
    - "lucid.type=distroless"
    - "lucid.platform=arm64"
    - "lucid.security=hardened"
    - "lucid.cluster=application"
  depends_on:
    tor-proxy:
      condition: service_started
    lucid-mongodb:
      condition: service_healthy
    lucid-redis:
      condition: service_healthy
```

### 3.2 Environment Files

Configuration is loaded from multiple environment files in priority order:

1. `.env.foundation` - Foundation service URLs
2. `.env.core` - Core service configuration
3. `.env.application` - Application-level settings
4. `.env.secrets` - Sensitive credentials
5. `.env.session-api` - Service-specific overrides

### 3.3 Volume Configuration

```yaml
volumes:
  session-api-cache:
    driver: local
    name: lucid-session-api-cache
    external: false
```

---

## 4. Directory Structure

### 4.1 Container Internal Structure

```
/app/
├── sessions/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app and lifespan
│   │   ├── config.py            # Configuration management
│   │   ├── entrypoint.py        # Container entrypoint
│   │   ├── routes.py            # API route definitions
│   │   ├── session_api.py       # Business logic
│   │   ├── config.yaml          # Default configuration
│   │   ├── openapi.yaml         # OpenAPI schema
│   │   ├── health-schema.json   # Health check schema
│   │   ├── metrics-schema.json  # Metrics schema
│   │   └── config/
│   │       └── env.session-api.template
│   ├── storage/                 # Shared storage module
│   │   ├── session_storage.py
│   │   ├── chunk_store.py
│   │   └── config.py
│   ├── core/                    # Shared core module
│   │   └── session_orchestrator.py
│   └── encryption/              # Shared encryption module
│       └── encryptor.py
├── data/                        # Volume mount: /app/data
│   ├── sessions/                # Session data
│   └── chunks/                  # Chunk data
└── logs/                        # Volume mount: /app/logs
```

### 4.2 Host Volume Mounts

- **Data:** `/mnt/myssd/Lucid/Lucid/data/session-api` → `/app/data:rw`
- **Logs:** `/mnt/myssd/Lucid/Lucid/logs/session-api` → `/app/logs:rw`
- **Cache:** `session-api-cache` → `/tmp/api:rw`

---

## 5. Module Organization

### 5.1 main.py

**Purpose:** FastAPI application setup and lifespan management

**Key Components:**
- FastAPI app instance creation
- Lifespan context manager (startup/shutdown)
- CORS middleware configuration
- Global exception handler
- Root and health endpoints

**Lifespan Events:**
- **Startup:** Initialize `SessionAPIConfig`, create `SessionAPI` instance
- **Shutdown:** Close `SessionAPI` connections gracefully

**Code Pattern:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global session_api, api_config
    
    # Startup
    api_config = SessionAPIConfig()
    session_api = SessionAPI(
        api_config.settings.MONGODB_URL,
        api_config.settings.REDIS_URL
    )
    
    yield
    
    # Shutdown
    if session_api:
        await session_api.close()
```

### 5.2 config.py

**Purpose:** Configuration management using Pydantic Settings

**Key Classes:**
- `SessionAPISettings`: Pydantic BaseSettings with validation
- `SessionAPIConfig`: Configuration manager wrapper
- `load_config()`: YAML/JSON file loader with environment variable overrides

**Configuration Priority:**
1. Environment variables (highest)
2. YAML/JSON configuration file
3. Pydantic field defaults (lowest)

**Validation:**
- MongoDB URL validation (must not use localhost)
- Redis URL validation (must not use localhost)
- Port number validation (1-65535)

### 5.3 entrypoint.py

**Purpose:** Container entrypoint script (Python-based for distroless)

**Key Functions:**
- Python path setup (`/usr/local/lib/python3.11/site-packages`, `/app`)
- Environment variable reading (`SESSION_API_PORT`)
- Uvicorn server startup
- Error handling with detailed diagnostics

**Bind Address:**
- Always binds to `0.0.0.0` (all interfaces) within container
- `SESSION_API_HOST` is used for service discovery, not binding

### 5.4 routes.py

**Purpose:** FastAPI route definitions and request/response models

**Router Configuration:**
```python
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
```

**Dependency Injection:**
```python
def get_session_api() -> SessionAPI:
    """Dependency to get session API instance"""
    global session_api
    if session_api is None:
        # Initialize from environment
        session_api = SessionAPI(mongo_url, redis_url)
    return session_api
```

**Route Categories:**
- Session management (CRUD)
- Recording control (start, stop, pause, resume)
- Chunk operations (list, get, download)
- Pipeline management (status, pause, resume)
- Statistics and metrics

### 5.5 session_api.py

**Purpose:** Business logic for session management operations

**Key Classes:**
- `SessionAPI`: Main service class
- Request/Response models (Pydantic BaseModel)
- Enums (`SessionStatus`, etc.)

**Dependencies:**
- `SessionStorage`: From `sessions.storage.session_storage`
- `ChunkStore`: From `sessions.storage.chunk_store`
- `StorageConfigManager`: From `sessions.storage.config`
- `SessionPipeline`: From `sessions.core.session_orchestrator`

**Initialization Pattern:**
```python
def __init__(self, mongo_url: str = None, redis_url: str = None):
    # Initialize storage configuration using StorageConfigManager
    storage_config_manager = StorageConfigManager()
    
    # Get configuration dictionaries
    storage_config_dict = storage_config_manager.get_storage_config_dict()
    chunk_config_dict = storage_config_manager.get_chunk_store_config_dict()
    
    # Create dataclass configs
    from ..storage.session_storage import StorageConfig as StorageConfigDataclass
    storage_config = StorageConfigDataclass(**storage_config_dict)
    chunk_config = ChunkStoreConfig(**chunk_config_dict)
    
    # Initialize services
    self.session_storage = SessionStorage(storage_config, mongo_url, redis_url)
    self.chunk_store = ChunkStore(chunk_config)
```

---

## 6. Configuration Management

### 6.1 Configuration Sources

**Priority Order (highest to lowest):**
1. Environment variables (from `.env.*` files)
2. YAML configuration file (`config.yaml`)
3. Pydantic field defaults

### 6.2 Required Environment Variables

```bash
# Database Connections (Required)
MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0

# Service Configuration
SESSION_API_HOST=session-api
SESSION_API_PORT=8113
SESSION_API_URL=http://session-api:8113
```

### 6.3 Optional Environment Variables

```bash
# Integration URLs (Optional)
ELASTICSEARCH_URL=http://lucid-elasticsearch:9200
API_GATEWAY_URL=http://api-gateway:8080
BLOCKCHAIN_ENGINE_URL=http://blockchain-engine:8084
AUTH_SERVICE_URL=http://lucid-auth-service:8089

# Storage Paths
LUCID_STORAGE_PATH=/app/data/sessions
LUCID_CHUNK_STORE_PATH=/app/data/chunks

# CORS Configuration
CORS_ORIGINS=*

# Logging
LOG_LEVEL=INFO
```

### 6.4 Configuration File (config.yaml)

Location: `/app/sessions/api/config.yaml` (baked into image)

Example structure:
```yaml
service_name: lucid-session-api
service_version: "1.0.0"
debug: false
log_level: INFO

network:
  host: "0.0.0.0"
  port: 8113
  url: ""

database:
  mongodb_url: ""  # Must be set via environment variable
  redis_url: ""    # Must be set via environment variable
  elasticsearch_url: ""

storage:
  session_storage_path: /app/data/sessions
  chunk_storage_path: /app/data/chunks
  temp_storage_path: /tmp/api

cors:
  origins: "*"
```

### 6.5 Configuration Validation

**Pydantic Validators:**
- `validate_mongodb_url()`: Ensures MongoDB URL is set and doesn't use localhost
- `validate_redis_url()`: Ensures Redis URL is set and doesn't use localhost
- `validate_port()`: Ensures port is in valid range (1-65535)

---

## 7. API Endpoints

### 7.1 Base Path

All endpoints are prefixed with `/api/v1/sessions`

### 7.2 Session Management Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| POST | `` | Create new session | `SessionResponse` |
| GET | `/{session_id}` | Get session by ID | `SessionResponse` |
| GET | `` | List sessions (with filters) | `SessionListResponse` |
| PUT | `/{session_id}` | Update session | `SessionResponse` |
| DELETE | `/{session_id}` | Delete session | `{}` |

### 7.3 Recording Control Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| POST | `/{session_id}/start` | Start recording | `{}` |
| POST | `/{session_id}/stop` | Stop recording | `{}` |
| POST | `/{session_id}/pause` | Pause recording | `{}` |
| POST | `/{session_id}/resume` | Resume recording | `{}` |

### 7.4 Chunk Management Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/{session_id}/chunks` | List chunks for session | `ChunkListResponse` |
| GET | `/{session_id}/chunks/{chunk_id}` | Get chunk details | `ChunkResponse` |
| GET | `/{session_id}/chunks/{chunk_id}/download` | Download chunk file | `StreamingResponse` |

### 7.5 Pipeline Management Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/{session_id}/pipeline` | Get pipeline status | `PipelineResponse` |
| POST | `/{session_id}/pipeline/pause` | Pause pipeline | `{}` |
| POST | `/{session_id}/pipeline/resume` | Resume pipeline | `{}` |

### 7.6 Statistics and Monitoring Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/{session_id}/statistics` | Get session statistics | `StatisticsResponse` |
| GET | `/statistics` | Get system-wide statistics | `{}` |
| GET | `/health` | Health check | `{}` |
| GET | `/metrics` | Prometheus metrics | `{}` |

### 7.7 Request/Response Models

**Key Models (Pydantic BaseModel):**
- `CreateSessionRequest`
- `UpdateSessionRequest`
- `SessionResponse`
- `SessionListResponse`
- `ChunkResponse`
- `ChunkListResponse`
- `PipelineResponse`
- `StatisticsResponse`
- `RDPConfig`
- `RecordingConfig`
- `StorageConfig` (API model, different from dataclass)
- `SessionMetadata`

---

## 8. Dependencies

### 8.1 External Services

**Required:**
- **MongoDB** (`lucid-mongodb:27017`): Session metadata storage
- **Redis** (`lucid-redis:6379`): Caching and session state

**Optional:**
- **Elasticsearch** (`lucid-elasticsearch:9200`): Search and indexing
- **API Gateway** (`api-gateway:8080`): Request routing
- **Blockchain Engine** (`blockchain-engine:8084`): Blockchain operations
- **Auth Service** (`lucid-auth-service:8089`): Authentication

### 8.2 Python Dependencies

**Core Framework:**
- `fastapi>=0.104.0`: Web framework
- `uvicorn>=0.24.0`: ASGI server
- `pydantic>=2.0.0`: Data validation
- `pydantic-settings>=2.1.0`: Settings management

**Database:**
- `motor>=3.3.0`: Async MongoDB driver
- `pymongo>=4.6.0`: MongoDB driver
- `redis>=5.0.0`: Redis client
- `async-timeout>=4.0.0`: Required by redis.asyncio

**Storage & Compression:**
- `zstandard>=0.21.0`: Zstd compression
- `lz4>=4.3.0`: LZ4 compression
- `aiofiles>=23.0.0`: Async file operations

**Cryptography:**
- `cryptography>=41.0.0`: Encryption support
- `blake3>=0.3.3`: BLAKE3 hashing (for Merkle trees)

**HTTP:**
- `httpx>=0.25.0`: HTTP client

**Configuration:**
- `pyyaml>=6.0.0`: YAML file support

### 8.3 Internal Module Dependencies

**From `sessions.storage`:**
- `SessionStorage`: Session storage operations
- `ChunkStore`: Chunk storage operations
- `StorageConfigManager`: Storage configuration management

**From `sessions.core`:**
- `SessionPipeline`: Pipeline orchestration
- `PipelineStage`: Pipeline stage definitions

**From `sessions.encryption`:**
- `SessionEncryptor`: Encryption operations (optional, graceful degradation)

**Optional (graceful degradation):**
- `sessions.recorder`: Recorder module (optional, fails gracefully if missing)

---

## 9. Volume Mounts and Permissions

### 9.1 Volume Mounts

| Host Path | Container Path | Permissions | Purpose |
|-----------|---------------|-------------|---------|
| `/mnt/myssd/Lucid/Lucid/data/session-api` | `/app/data` | `rw` | Session and chunk data storage |
| `/mnt/myssd/Lucid/Lucid/logs/session-api` | `/app/logs` | `rw` | Application logs |
| `session-api-cache` | `/tmp/api` | `rw` | Temporary cache files |

### 9.2 Permission Requirements

**Container User:** `65532:65532` (non-root)

**Host Directory Setup:**
```bash
# Create directories
sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/session-api
sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/session-api

# Set ownership (container user: 65532:65532)
sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/session-api
sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/logs/session-api

# Set permissions
sudo chmod -R 755 /mnt/myssd/Lucid/Lucid/data/session-api
sudo chmod -R 755 /mnt/myssd/Lucid/Lucid/logs/session-api
```

### 9.3 Directory Creation Logic

**Storage Paths:**
- Base path: `/app/data/sessions` (from `LUCID_STORAGE_PATH`)
- Chunk path: `/app/data/chunks` (from `LUCID_CHUNK_STORE_PATH`)

**Initialization:**
1. Check if parent directory (`/app/data`) exists (from volume mount)
2. Create subdirectories if they don't exist
3. Handle permission errors with clear error messages

**Error Handling:**
- If parent directory doesn't exist: Raise `OSError` with volume mount instructions
- If permission denied: Raise `PermissionError` with `chown`/`chmod` instructions

---

## 10. Security Configuration

### 10.1 Container Security

**Security Options:**
```yaml
user: "65532:65532"  # Non-root user
security_opt:
  - no-new-privileges:true
  - seccomp:unconfined
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # Required for binding to port 8113
read_only: true  # Read-only root filesystem
tmpfs:
  - /tmp:noexec,nosuid,size=100m  # Writable tmpfs for temporary files
```

### 10.2 Network Security

- **Internal Network:** `lucid-pi-network` (private Docker network)
- **Port Binding:** `8113:8113` (host:container)
- **Service Discovery:** Uses container names (not IP addresses)

### 10.3 CORS Configuration

**Configuration:**
- Controlled via `CORS_ORIGINS` environment variable
- Default: `*` (allow all origins)
- Can be set to comma-separated list: `"https://example.com,https://app.example.com"`

**Middleware:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # From CORS_ORIGINS env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 10.4 Data Security

- **Encryption:** Supported via `sessions.encryption` module
- **Compression:** Zstd/LZ4 compression for data storage
- **Secrets:** Stored in `.env.secrets` (not in code or config files)

---

## 11. Build Process

### 11.1 Dockerfile Location

` sessions/Dockerfile.api`

### 11.2 Build Command

```bash
docker build \
  --platform linux/arm64 \
  -t pickme/lucid-session-api:latest-arm64 \
  -f sessions/Dockerfile.api \
  .
```

### 11.3 Build Stages

**Stage 1: Builder**
- Base: `python:3.11-slim-bookworm`
- Purpose: Install Python packages and build application
- Output: Packages in `/root/.local/lib/python3.11/site-packages`
- Output: Application source in `/build/sessions`

**Stage 2: Runtime**
- Base: `gcr.io/distroless/python3-debian12:latest`
- Purpose: Minimal runtime environment
- Copies: Packages and application from builder stage
- User: `65532:65532` (non-root)

### 11.4 Build Verification

**Package Verification:**
- Verifies critical packages exist and are importable
- Checks marker files for COPY verification
- Fails build if packages are missing

**Source Verification:**
- Verifies application source files were copied
- Checks for required modules (`api`, `core`, `storage`, `encryption`)
- Validates critical files exist

### 11.5 Multi-Stage Build Benefits

- **Smaller Image:** Only runtime dependencies in final image
- **Security:** No build tools in production image
- **Reproducibility:** Consistent build environment

---

## 12. Health Checks

### 12.1 Health Check Configuration

```yaml
healthcheck:
  test: ["CMD", "/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8113)); s.close(); exit(0 if result == 0 else 1)"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Type:** Socket-based (connects to TCP port 8113)

**Why Socket-Based:**
- Distroless containers don't have shell utilities
- Python socket module is available in distroless
- More reliable than HTTP health checks for basic connectivity

### 12.2 Health Check Endpoint

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "session-api",
  "timestamp": "2025-12-28T12:00:00Z"
}
```

**Checks:**
- Service is initialized (`session_api is not None`)
- MongoDB connection (if available)
- Redis connection (if available)

### 12.3 Metrics Endpoint

**Endpoint:** `GET /metrics`

**Format:** Prometheus-compatible metrics

**Metrics:**
- Session counts (total, by status)
- Chunk counts
- Pipeline status counts
- Request counters (if implemented)

---

## 13. Error Handling

### 13.1 Global Exception Handler

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )
```

### 13.2 HTTP Exception Handling

**Standard HTTP Exceptions:**
- `404 Not Found`: Session/chunk not found
- `400 Bad Request`: Invalid request data
- `500 Internal Server Error`: Unexpected errors
- `503 Service Unavailable`: Service not initialized

### 13.3 Storage Error Handling

**Permission Errors:**
- Clear error messages with fix instructions
- Suggests `chown` and `chmod` commands
- Identifies missing volume mounts

**Example:**
```python
except PermissionError as e:
    raise PermissionError(
        f"Permission denied creating directory: {path}. "
        f"The container runs as user 65532:65532 and needs write access. "
        f"On the host, run: sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/session-api"
    )
```

### 13.4 Graceful Degradation

**Optional Modules:**
- `sessions.recorder`: Logs warning if missing, continues operation
- `sessions.encryption`: Handled via try/except in storage modules

**Pattern:**
```python
try:
    from ..recorder.session_recorder import ChunkMetadata
except (ImportError, OSError) as e:
    logger.warning(f"Failed to import recorder module (will use graceful degradation): {e}")
    ChunkMetadata = None
```

---

## 14. Integration Patterns

### 14.1 Session Storage Integration

**Usage Pattern:**
```python
# Initialize via StorageConfigManager
storage_config_manager = StorageConfigManager()
storage_config_dict = storage_config_manager.get_storage_config_dict()
storage_config = StorageConfigDataclass(**storage_config_dict)

# Create SessionStorage instance
session_storage = SessionStorage(storage_config, mongo_url, redis_url)
```

**Shared Configuration:**
- Uses same `StorageConfigManager` as `session-storage` service
- Ensures consistent configuration across services
- Environment variables override YAML defaults

### 14.2 MongoDB Integration

**Connection:**
- Uses `Motor` (async) for async operations
- Uses `pymongo` (sync) for sync operations
- Connection URL from `MONGODB_URL` environment variable

**Collections:**
- `sessions`: Session metadata
- `chunks`: Chunk metadata
- `pipeline`: Pipeline state

### 14.3 Redis Integration

**Usage:**
- Caching session state
- Temporary data storage
- Connection URL from `REDIS_URL` environment variable

**Pattern:**
```python
import redis.asyncio as redis
redis_client = await redis.from_url(redis_url)
```

### 14.4 Pipeline Integration

**SessionPipeline Usage:**
```python
from ..core.session_orchestrator import SessionPipeline, PipelineStage

pipeline = SessionPipeline(session_id, mongo_url, redis_url)
await pipeline.update_stage(PipelineStage.RECORDING)
```

### 14.5 Service Discovery

**Pattern:**
- Uses container names (not IP addresses)
- URLs like `http://session-api:8113`
- Configured via environment variables

**Example:**
```yaml
environment:
  - SESSION_API_URL=http://session-api:8113
  - MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid
  - REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
```

---

## 15. Operational Considerations

### 15.1 Startup Sequence

1. **Entrypoint:** `entrypoint.py` sets up Python path
2. **Uvicorn:** Starts FastAPI application
3. **Lifespan Startup:** Initializes configuration and services
4. **Service Ready:** Health check passes

### 15.2 Shutdown Sequence

1. **Signal Received:** SIGTERM or SIGINT
2. **Lifespan Shutdown:** Closes `SessionAPI` connections
3. **Cleanup:** MongoDB and Redis connections closed
4. **Exit:** Container exits gracefully

### 15.3 Logging

**Log Format:**
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**Log Levels:**
- Controlled via `LOG_LEVEL` environment variable
- Default: `INFO`
- Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Log Destination:**
- Volume mount: `/app/logs`
- Host path: `/mnt/myssd/Lucid/Lucid/logs/session-api`

### 15.4 Monitoring

**Health Checks:**
- Docker healthcheck (socket-based)
- HTTP `/health` endpoint
- HTTP `/metrics` endpoint (Prometheus)

**Key Metrics:**
- Session counts by status
- Chunk counts
- Pipeline stage counts
- Request latencies (if implemented)

---

## 16. Troubleshooting

### 16.1 Common Issues

**Permission Denied Errors:**
- **Symptom:** `PermissionError: [Errno 13] Permission denied`
- **Cause:** Volume mount doesn't have correct ownership
- **Fix:** Run `sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/session-api`

**Module Not Found Errors:**
- **Symptom:** `ModuleNotFoundError: No module named 'sessions.encryption'`
- **Cause:** Module not copied into container
- **Fix:** Ensure `sessions/encryption/` is copied in Dockerfile

**Connection Errors:**
- **Symptom:** Cannot connect to MongoDB/Redis
- **Cause:** Service names incorrect or services not running
- **Fix:** Verify service names match docker-compose, check service health

### 16.2 Debugging

**View Logs:**
```bash
docker logs session-api
docker logs --tail 100 -f session-api
```

**Check Container Status:**
```bash
docker ps | grep session-api
docker inspect session-api
```

**Test Health Check:**
```bash
docker exec session-api python3 -c "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8113)); s.close(); exit(0 if result == 0 else 1)"
```

**Test API Endpoint:**
```bash
curl http://localhost:8113/health
curl http://localhost:8113/api/v1/sessions
```

---

## 17. Related Documentation

- `build/docs/mod-design-template.md` - General module design template
- `build/docs/master-docker-design.md` - Master Docker design principles
- `build/docs/dockerfile-design.md` - Dockerfile patterns
- `plan/constants/Dockerfile-copy-pattern.md` - COPY command patterns
- `docs/architecture/DISTROLESS-CONTAINER-SPEC.md` - Distroless container requirements

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-12-28 | Initial design document creation | System |

---

**Last Updated:** 2025-12-28  
**Status:** ACTIVE  
**Maintained By:** Lucid Development Team

