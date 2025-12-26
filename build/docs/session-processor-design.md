# Session Processor Container Design and Build Documentation

**Service**: `lucid-chunk-processor`  
**Image**: `pickme/lucid-chunk-processor:latest-arm64`  
**Container Name**: `session-processor`  
**Port**: 8091  
**Document Version**: 1.0.0  
**Last Updated**: 2025-01-27

---

## Table of Contents

1. [Container Overview](#container-overview)
2. [Architecture and Design Decisions](#architecture-and-design-decisions)
3. [Module Structure and Components](#module-structure-and-components)
4. [Design Patterns](#design-patterns)
5. [Configuration Management](#configuration-management)
6. [Processing Pipeline](#processing-pipeline)
7. [Integration Patterns](#integration-patterns)
8. [Build Specification](#build-specification)
9. [Dependencies and Requirements](#dependencies-and-requirements)
10. [Deployment and Runtime](#deployment-and-runtime)
11. [Alignment Criteria](#alignment-criteria)

---

## Container Overview

### Purpose

The session-processor container provides the Lucid Chunk Processor service, handling concurrent processing of session data chunks with compression, encryption, and Merkle tree building:

- **Chunk Processing**: Concurrent processing of session data chunks using configurable worker pools
- **Compression**: Multi-algorithm compression support (Zstd, LZ4, Brotli) with configurable compression levels
- **Encryption**: AES-256-GCM encryption with key rotation and secure key management
- **Merkle Tree Building**: Constructs Merkle trees for blockchain anchoring and integrity verification
- **Storage Integration**: Sends processed chunks to session-storage service
- **Pipeline Integration**: Coordinates with session-pipeline for workflow orchestration
- **Performance Metrics**: Tracks processing metrics, compression ratios, and performance statistics
- **Error Handling**: Implements retry logic and error recovery mechanisms

### Technology Stack

- **Base Image**: `gcr.io/distroless/python3-debian12:latest` (distroless, ARM64)
- **Python Version**: 3.11
- **Framework**: FastAPI + Uvicorn
- **Database**: MongoDB (via motor/pymongo), Redis (via aioredis)
- **Compression**: zstandard, zstd, lz4, brotli
- **Cryptography**: cryptography (AES-256-GCM), blake3
- **Build Architecture**: Multi-stage build (builder + runtime)
- **User**: Non-root (UID/GID 65532:65532)
- **Security**: Distroless base (minimal attack surface), read-only filesystem, dropped capabilities

### Key Characteristics

- **Security**: Distroless base image with non-root user, encrypted data at rest
- **Performance**: Concurrent processing with configurable worker pools, async/await architecture
- **Reliability**: Retry logic, error recovery, comprehensive error handling
- **Scalability**: Configurable worker pools, batch processing support
- **Observability**: Structured logging, metrics collection, health checks
- **Configuration**: Environment-driven configuration (no hardcoded values)

---

## Architecture and Design Decisions

### 1. Multi-Stage Build Pattern

**Decision**: Use multi-stage build with separate builder and runtime stages.

**Rationale**:
- Builder stage: Full Python image with build tools for compiling native extensions (zstandard, lz4, cryptography, blake3)
- Runtime stage: Distroless image for minimal size and security
- Reduces final image size significantly while maintaining functionality
- Native extension libraries (libzstd.so.1, liblz4.so.1) copied from builder to runtime

**Implementation**:
```dockerfile
FROM python:3.11-slim-bookworm AS builder
# Install build dependencies, compile packages

FROM gcr.io/distroless/python3-debian12:latest
# Copy only runtime artifacts (packages, source code, dynamic libraries)
```

### 2. Distroless Base Image

**Decision**: Use `gcr.io/distroless/python3-debian12:latest` as runtime base.

**Rationale**:
- No shell, package manager, or unnecessary binaries
- Minimal attack surface (reduced CVE exposure)
- Smaller image size
- Better security posture for production

**Implications**:
- All runtime commands must use Python (no shell scripts)
- Health checks use Python socket libraries
- Entrypoint uses Python interpreter directly
- Dynamic libraries must be explicitly copied (libzstd.so.1, liblz4.so.1)

### 3. Entrypoint Pattern

**Decision**: Use dedicated `entrypoint.py` script instead of `-m` flag.

**Rationale**:
- Ensures `sys.path` is configured before any imports
- Prevents module resolution issues with distroless containers
- Matches pattern used by other session services (storage, api, recorder, pipeline)
- Provides clear error messages for configuration issues

**Implementation**:
```python
# entrypoint.py sets up sys.path BEFORE imports
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

# Then imports uvicorn and starts the app
uvicorn.run('sessions.processor.main:app', host='0.0.0.0', port=port)
```

### 4. Modular Package Structure

**Decision**: Separate processor, core, encryption, and integration modules.

**Rationale**:
- Clear separation of concerns
- Reusable core components (chunker, merkle_builder, logging)
- Encryption module shared with other session services
- Integration clients for service-to-service communication
- Easier testing and maintenance

**Module Layout**:
```
/app/
├── sessions/
│   ├── processor/          # Processor-specific code
│   │   ├── main.py          # FastAPI application
│   │   ├── entrypoint.py    # Container entrypoint
│   │   ├── config.py        # Configuration management
│   │   ├── chunk_processor.py  # Main processing logic
│   │   ├── compressor.py    # Compression engine
│   │   ├── encryption.py    # Encryption manager
│   │   ├── merkle_builder.py  # Merkle tree construction
│   │   ├── session_manifest.py  # Manifest generation
│   │   ├── config.yaml      # YAML configuration
│   │   └── integration/     # External service clients
│   ├── core/                # Shared core components
│   ├── pipeline/            # Pipeline integration
│   └── __init__.py
└── /usr/local/lib/python3.11/site-packages/  # Python packages
```

### 5. Concurrent Processing Pattern

**Decision**: Use ThreadPoolExecutor for concurrent chunk processing.

**Rationale**:
- Configurable worker pool size (default: 10 workers)
- Efficient CPU utilization for I/O-bound operations
- Thread-safe operations for compression and encryption
- Metrics tracking per worker

**Implementation**:
- Worker pool managed by `ChunkProcessorService`
- Each worker processes chunks independently
- Results aggregated and sent to storage service
- Error handling per worker with retry logic

---

## Module Structure and Components

### Core Modules

#### 1. Main Application Module (`main.py`)

**Purpose**: FastAPI application entry point with lifespan management

**Key Components**:
- FastAPI app initialization with metadata
- Lifespan context manager (startup/shutdown)
- Global service instances (chunk_processor_service, encryption_manager, merkle_tree_manager)
- Signal handlers for graceful shutdown
- Health check endpoints (`/health`, `/ready`)
- API route definitions for chunk processing
- Metrics endpoints
- Error handling middleware

**Key Features**:
- Async/await architecture
- Request/response models with Pydantic validation
- Background task support
- Comprehensive error handling

#### 2. Entrypoint Module (`entrypoint.py`)

**Purpose**: Container entrypoint script for distroless containers

**Key Components**:
- `sys.path` configuration before imports
- Environment variable reading (SESSION_PROCESSOR_PORT)
- Uvicorn server startup
- Error handling for invalid configuration

**Critical Pattern**:
```python
# MUST set sys.path BEFORE any imports
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
```

#### 3. Configuration Module (`config.py`)

**Purpose**: Configuration management with environment variable support

**Key Components**:
- `ChunkProcessorConfig` class (Pydantic BaseSettings)
- YAML configuration file loading (optional)
- Environment variable validation
- Configuration validation methods
- Default value management

**Configuration Sources** (priority order):
1. Environment variables (highest priority)
2. YAML configuration file (`config.yaml`)
3. Pydantic field defaults (lowest priority)

**Required Environment Variables**:
- `MONGODB_URL` (required)
- `REDIS_URL` (required)
- `SESSION_PROCESSOR_PORT` (optional, defaults to 8091)

**Optional Environment Variables**:
- `LUCID_COMPRESSION_PATH` (defaults to `/app/data/compression`)
- `LUCID_MANIFEST_PATH` (defaults to `/app/data/manifests`)
- Integration service URLs (SESSION_PIPELINE_URL, SESSION_STORAGE_URL, etc.)

#### 4. Chunk Processor Module (`chunk_processor.py`)

**Purpose**: Core chunk processing logic with concurrent execution

**Key Components**:
- `ChunkProcessor` class: Main processing engine
- `ChunkProcessorService` class: Service wrapper with async support
- `ChunkMetadata` dataclass: Processing metadata
- `ProcessingResult` dataclass: Processing outcome
- Worker pool management (ThreadPoolExecutor)
- Batch processing support
- Metrics tracking

**Processing Flow**:
1. Receive chunk data (base64-encoded)
2. Decode and validate chunk
3. Compress chunk (if enabled)
4. Encrypt chunk (AES-256-GCM)
5. Build Merkle tree node
6. Send to storage service
7. Return processing result with metadata

#### 5. Compression Module (`compressor.py`)

**Purpose**: Multi-algorithm compression engine

**Key Components**:
- `SessionCompressor` class: Main compression engine
- `CompressionAlgorithm` enum: Supported algorithms (ZSTD, LZ4, BROTLI)
- `CompressionResult` dataclass: Compression outcome
- Algorithm-specific compression methods
- Compression ratio calculation
- File-based compression support

**Supported Algorithms**:
- **Zstd** (default): High compression ratio, fast decompression
- **LZ4**: Fast compression, lower ratio
- **Brotli**: Good balance, web-optimized

**Configuration**:
- `LUCID_COMPRESSION_PATH`: Compression output directory (default: `/app/data/compression`)
- `LUCID_DEFAULT_COMPRESSION_LEVEL`: Default compression level (default: 3)
- `LUCID_MAX_CHUNK_SIZE`: Maximum chunk size (default: 1MB)

#### 6. Encryption Module (`encryption.py`)

**Purpose**: AES-256-GCM encryption with key management

**Key Components**:
- `EncryptionManager` class: Main encryption manager
- `ChunkEncryptor` class: Chunk-specific encryption
- Key generation and rotation
- Salt and nonce management
- Authentication tag generation

**Encryption Details**:
- Algorithm: AES-256-GCM
- Key size: 32 bytes (256 bits)
- Nonce size: 12 bytes (96 bits)
- Tag size: 16 bytes (128 bits)
- Salt size: 32 bytes (256 bits)
- PBKDF2 iterations: 100,000

#### 7. Merkle Tree Module (`merkle_builder.py`)

**Purpose**: Merkle tree construction for blockchain anchoring

**Key Components**:
- `MerkleTreeBuilder` class: Tree construction
- `MerkleTreeManager` class: Multi-session tree management
- `MerkleNode` dataclass: Tree node structure
- `MerkleProof` dataclass: Proof generation
- `MerkleTreeMetadata` dataclass: Tree metadata

**Features**:
- Incremental tree building
- Proof generation for integrity verification
- Tree serialization/deserialization
- Multi-session tree management

#### 8. Session Manifest Module (`session_manifest.py`)

**Purpose**: Session manifest generation with blockchain anchoring

**Key Components**:
- `SessionManifest` class: Manifest structure
- `ManifestStatus` enum: Manifest generation status
- `ManifestType` enum: Manifest types
- Manifest signing (Ed25519)
- JSON manifest file generation

**Manifest Features**:
- Session metadata capture
- Chunk integrity verification
- Blockchain transaction anchoring
- Digital signatures
- JSON file output

**Configuration**:
- `LUCID_MANIFEST_PATH`: Manifest output directory (default: `/app/data/manifests`)
- `LUCID_MANIFEST_SIGNATURE_ALGORITHM`: Signature algorithm (default: Ed25519)
- `LUCID_MANIFEST_HASH_ALGORITHM`: Hash algorithm (default: BLAKE3)

#### 9. Integration Module (`integration/`)

**Purpose**: Service-to-service communication clients

**Key Components**:
- `IntegrationManager` class: Centralized integration management
- `ServiceClientBase` class: Base client with retry logic
- `SessionPipelineClient` class: Pipeline service client
- `SessionStorageClient` class: Storage service client

**Integration Features**:
- Retry logic with exponential backoff
- Health check methods
- Timeout configuration
- Error handling and recovery
- Service discovery support

---

## Design Patterns

### 1. Configuration Pattern

**Pattern**: Environment-first configuration with YAML fallback

**Implementation**:
```python
class ChunkProcessorConfig(BaseSettings):
    # Environment variables override YAML, which override defaults
    mongodb_url: str = ""  # Required from environment
    
    model_config = {
        "env_file": None,  # Don't read .env directly
        "case_sensitive": True,
        "env_prefix": ""  # No prefix - use standard names
    }
```

**Priority Order**:
1. Environment variables (from docker-compose)
2. YAML configuration file (`config.yaml`)
3. Pydantic field defaults

### 2. Error Handling Pattern

**Pattern**: Graceful degradation with clear error messages

**Implementation**:
- Try/except blocks around critical operations
- Structured error logging
- Error recovery mechanisms
- Retry logic for transient failures
- Clear error messages with actionable information

**Example**:
```python
try:
    result = await process_chunk(...)
except CompressionError as e:
    logger.error(f"Compression failed: {e}")
    # Fallback or retry logic
except EncryptionError as e:
    logger.error(f"Encryption failed: {e}")
    # Error recovery
```

### 3. Integration Pattern

**Pattern**: Lazy initialization with centralized management

**Implementation**:
- Integration clients created only when needed
- Centralized `IntegrationManager` for coordination
- Health check aggregation
- Consistent error handling across clients
- Retry logic with exponential backoff

### 4. Processing Pattern

**Pattern**: Concurrent processing with worker pools

**Implementation**:
- ThreadPoolExecutor for concurrent chunk processing
- Configurable worker count (default: 10)
- Queue-based task distribution
- Metrics tracking per worker
- Error isolation (one worker failure doesn't affect others)

### 5. Storage Pattern

**Pattern**: Volume-mounted writable directories

**Implementation**:
- All data written to `/app/data/` (volume mount)
- Compression data: `/app/data/compression`
- Manifest data: `/app/data/manifests`
- Chunk storage: `/app/data/chunks`
- Logs: `/app/logs` (volume mount)

---

## Configuration Management

### Environment Variables

**Required Variables**:
- `MONGODB_URL`: MongoDB connection string (required)
- `REDIS_URL`: Redis connection string (required)

**Service Configuration**:
- `SESSION_PROCESSOR_PORT`: Service port (default: 8091)
- `SESSION_PROCESSOR_HOST`: Service hostname (for identification, not binding)
- `SESSION_PROCESSOR_URL`: Service URL (for other services)

**Path Configuration**:
- `LUCID_COMPRESSION_PATH`: Compression output path (default: `/app/data/compression`)
- `LUCID_MANIFEST_PATH`: Manifest output path (default: `/app/data/manifests`)

**Integration Service URLs**:
- `SESSION_PIPELINE_URL`: Pipeline service URL
- `SESSION_STORAGE_URL`: Storage service URL
- `SESSION_RECORDER_URL`: Recorder service URL
- `SESSION_API_URL`: API service URL
- `BLOCKCHAIN_ENGINE_URL`: Blockchain engine URL
- `NODE_MANAGEMENT_URL`: Node management URL
- `API_GATEWAY_URL`: API gateway URL
- `AUTH_SERVICE_URL`: Auth service URL

**Compression Configuration**:
- `LUCID_DEFAULT_COMPRESSION_LEVEL`: Default compression level (default: 3)
- `LUCID_MAX_CHUNK_SIZE`: Maximum chunk size in bytes (default: 1048576)
- `LUCID_COMPRESSION_THRESHOLD`: Minimum size to compress (default: 1024)

**Manifest Configuration**:
- `LUCID_MANIFEST_SIGNATURE_ALGORITHM`: Signature algorithm (default: Ed25519)
- `LUCID_MANIFEST_HASH_ALGORITHM`: Hash algorithm (default: BLAKE3)
- `LUCID_MANIFEST_CHUNK_SIZE`: Manifest chunk size (default: 1048576)

### YAML Configuration File

**Location**: `/app/sessions/processor/config.yaml`

**Purpose**: Optional configuration file for non-sensitive settings

**Structure**:
```yaml
service_name: "chunk-processor"
service_version: "1.0.0"
host: "0.0.0.0"
port: 8091

# Worker configuration
max_workers: 10
queue_size: 1000
worker_timeout: 30

# Compression configuration
compression_enabled: true
compression_level: 6

# Storage configuration
storage_path: "/app/data/chunks"
max_chunk_size: 10485760  # 10MB
```

**Note**: Environment variables always override YAML values.

---

## Processing Pipeline

### Chunk Processing Flow

1. **Receive Request**: FastAPI endpoint receives chunk processing request
2. **Decode Data**: Base64 decode chunk data
3. **Validate Chunk**: Validate chunk size and format
4. **Compress** (optional): Apply compression algorithm (Zstd, LZ4, or Brotli)
5. **Encrypt**: Apply AES-256-GCM encryption
6. **Build Merkle Node**: Add chunk to Merkle tree
7. **Store Chunk**: Send encrypted chunk to storage service
8. **Return Result**: Return processing result with metadata

### Batch Processing

**Support**: Multiple chunks processed concurrently

**Implementation**:
- Worker pool processes chunks in parallel
- Results aggregated and returned
- Error handling per chunk (one failure doesn't stop others)
- Metrics tracked per chunk

### Compression Pipeline

**Algorithms Supported**:
- **Zstd** (default): Best compression ratio, fast decompression
- **LZ4**: Fastest compression, lower ratio
- **Brotli**: Good balance, web-optimized

**Compression Flow**:
1. Check chunk size against threshold
2. Apply selected compression algorithm
3. Calculate compression ratio
4. Store compressed data
5. Return compression metadata

### Encryption Pipeline

**Encryption Flow**:
1. Generate or retrieve encryption key
2. Generate salt and nonce
3. Apply AES-256-GCM encryption
4. Generate authentication tag
5. Combine salt + nonce + ciphertext + tag
6. Return encrypted data with metadata

### Merkle Tree Pipeline

**Tree Building Flow**:
1. Create Merkle tree for session
2. Add chunks as leaf nodes incrementally
3. Build tree structure bottom-up
4. Generate root hash
5. Generate proofs for integrity verification
6. Anchor root hash to blockchain (via integration)

---

## Integration Patterns

### Service Client Pattern

**Base Pattern**: `ServiceClientBase` with retry logic

**Features**:
- HTTP client with timeout configuration
- Retry logic with exponential backoff
- Health check methods
- Error handling and recovery
- Service discovery support

**Implementation**:
```python
class ServiceClientBase:
    def __init__(self, base_url, timeout, retry_count, retry_delay):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self.retry_count = retry_count
        self.retry_delay = retry_delay
    
    async def _make_request(self, method, endpoint, **kwargs):
        # Retry logic with exponential backoff
        for attempt in range(self.retry_count):
            try:
                response = await self.client.request(method, endpoint, **kwargs)
                if response.status_code < 500:
                    return response
            except Exception as e:
                if attempt == self.retry_count - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
```

### Integration Manager Pattern

**Purpose**: Centralized integration management

**Features**:
- Lazy initialization of clients
- Health check aggregation
- Service discovery
- Error isolation
- Configuration management

### Storage Integration

**Client**: `SessionStorageClient`

**Methods**:
- `store_chunk()`: Store processed chunk
- `get_chunk()`: Retrieve chunk by ID
- `list_chunks()`: List chunks for session
- `health_check()`: Check storage service health

### Pipeline Integration

**Client**: `SessionPipelineClient`

**Methods**:
- `create_pipeline()`: Create new processing pipeline
- `update_pipeline_status()`: Update pipeline status
- `send_chunk()`: Send chunk to pipeline
- `health_check()`: Check pipeline service health

---

## Build Specification

### Dockerfile Structure

**Alignment**: Follows `master-docker-design.md` and `dockerfile-design.md`

**Key Components**:

1. **Build Arguments**:
   - `BUILD_DATE`: Build timestamp
   - `VCS_REF`: Git commit hash
   - `VERSION`: Service version (default: 1.0.0)
   - `TARGETPLATFORM`: Target architecture (linux/arm64)
   - `BUILDPLATFORM`: Build host architecture
   - `PYTHON_VERSION`: Python version (3.11)

2. **Builder Stage**:
   - Base: `python:3.11-slim-bookworm`
   - System packages: build-essential, gcc, g++, libffi-dev, libssl-dev, libzstd-dev, liblz4-dev
   - Python packages: Installed to `/root/.local/lib/python3.11/site-packages`
   - Marker files: Created after package installation
   - Verification: Critical packages imported and verified

3. **Runtime Stage**:
   - Base: `gcr.io/distroless/python3-debian12:latest`
   - System directories: `/var/run`, `/var/lib` (with marker files)
   - CA certificates: Copied from builder
   - Dynamic libraries: `libzstd.so.1`, `liblz4.so.1` (required for compression)
   - Python packages: Copied to `/usr/local/lib/python3.11/site-packages`
   - Application code: Copied to `/app/sessions/processor`
   - Verification: Packages and files verified before completion
   - Health check: Socket-based check on port 8091
   - User: Non-root (65532:65532)

### Build Process

**Steps**:
1. Install system build dependencies
2. Create system directory markers
3. Install Python packages
4. Create package marker files
5. Verify packages in builder stage
6. Copy application source code
7. Copy packages to runtime stage
8. Copy dynamic libraries
9. Verify packages in runtime stage
10. Copy application code
11. Verify application files
12. Set health check
13. Set user and entrypoint

### Critical Build Dependencies

**System Packages**:
- `libzstd-dev`, `libzstd1`: Required for zstandard Python package
- `liblz4-dev`, `liblz4-1`: Required for lz4 Python package
- `build-essential`, `gcc`, `g++`: Required for compiling native extensions

**Python Packages** (from `requirements.processor.txt`):
- Core: fastapi, uvicorn, pydantic, pydantic-settings
- Cryptography: cryptography, blake3
- Database: motor, pymongo, redis, async-timeout
- Compression: zstandard, zstd, lz4, brotli
- Async: aiofiles, aiohttp, httpx
- Data: numpy, PyYAML
- Monitoring: prometheus-client, structlog

### Dynamic Library Requirements

**Critical**: Native compression libraries must be copied to runtime

**Libraries Copied**:
- `/lib/*/libzstd.so.1` → `/lib/`
- `/lib/*/liblz4.so.1` → `/lib/`

**Rationale**: Distroless base doesn't include these libraries, but zstandard and lz4 Python packages require them at runtime.

---

## Dependencies and Requirements

### Python Dependencies

**Core Framework**:
- `fastapi>=0.111,<1.0`: Web framework
- `uvicorn[standard]>=0.30`: ASGI server
- `pydantic==2.5.0`: Data validation
- `pydantic-settings==2.1.0`: Settings management

**Cryptography**:
- `cryptography==41.0.7`: AES-256-GCM encryption
- `blake3>=0.3.3`: Fast hashing

**Database**:
- `motor==3.3.2`: Async MongoDB driver
- `pymongo==4.6.0`: MongoDB driver
- `redis==5.0.1`: Redis client
- `async-timeout>=4.0.2`: Timeout support

**Compression**:
- `zstandard>=0.21.0`: **REQUIRED** - Primary compression algorithm
- `zstd>=1.5.5`: Direct zstd API
- `lz4>=4.3.2`: LZ4 compression
- `brotli>=1.1.0`: Brotli compression

**Async/Concurrency**:
- `aiofiles==23.2.1`: Async file I/O
- `aiohttp==3.9.1`: Async HTTP client
- `httpx==0.25.2`: Modern HTTP client

**Data Processing**:
- `numpy==1.24.4`: Numerical operations
- `PyYAML==6.0.1`: YAML parsing

**Monitoring**:
- `prometheus-client==0.19.0`: Metrics collection
- `structlog==23.2.0`: Structured logging

### System Dependencies

**Build Dependencies** (builder stage only):
- `build-essential`: Compiler toolchain
- `gcc`, `g++`: C/C++ compilers
- `libffi-dev`: Foreign function interface
- `libssl-dev`: SSL/TLS library
- `pkg-config`: Package configuration
- `libzstd-dev`, `libzstd1`: Zstd library (build + runtime)
- `liblz4-dev`, `liblz4-1`: LZ4 library (build + runtime)
- `curl`: Download tool
- `ca-certificates`: CA certificates

**Runtime Dependencies** (copied to runtime):
- `libzstd.so.1`: Zstd runtime library
- `liblz4.so.1`: LZ4 runtime library
- CA certificates for TLS verification

---

## Deployment and Runtime

### Container Configuration

**Docker Compose** (`configs/docker/docker-compose.application.yml`):

```yaml
session-processor:
  image: pickme/lucid-chunk-processor:latest-arm64
  container_name: session-processor
  restart: unless-stopped
  ports:
    - "8091:8091"
  volumes:
    - /mnt/myssd/Lucid/Lucid/data/session-processor:/app/data:rw
    - /mnt/myssd/Lucid/Lucid/logs/session-processor:/app/logs:rw
  environment:
    - SESSION_PROCESSOR_PORT=8091
    - MONGODB_URL=${MONGODB_URL}
    - REDIS_URL=${REDIS_URL}
    - LUCID_COMPRESSION_PATH=/app/data/compression
    - LUCID_MANIFEST_PATH=/app/data/manifests
    # Integration service URLs...
  user: "65532:65532"
  read_only: true
  tmpfs:
    - /tmp:noexec,nosuid,size=200m
```

### Volume Mounts

**Data Volume**: `/mnt/myssd/Lucid/Lucid/data/session-processor:/app/data:rw`
- Compression data: `/app/data/compression`
- Manifest data: `/app/data/manifests`
- Chunk storage: `/app/data/chunks`

**Logs Volume**: `/mnt/myssd/Lucid/Lucid/logs/session-processor:/app/logs:rw`
- Application logs: `/app/logs/`

**Temporary Files**: `/tmp` (tmpfs, 200MB)
- Temporary compression files
- Temporary processing files

### Security Configuration

**Security Settings**:
- `read_only: true`: Read-only root filesystem
- `user: "65532:65532"`: Non-root user
- `cap_drop: ALL`: Drop all capabilities
- `security_opt: no-new-privileges:true`: Prevent privilege escalation
- `tmpfs: /tmp`: Temporary filesystem for writable temp directory

### Health Check

**Implementation**: Socket-based health check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8091)); s.close(); exit(0 if result == 0 else 1)"]
```

**Health Check Endpoints**:
- `/health`: Basic health check
- `/ready`: Readiness check (checks dependencies)

### Startup Sequence

1. Container starts with entrypoint script
2. Entrypoint sets up `sys.path` for distroless
3. Entrypoint reads `SESSION_PROCESSOR_PORT` from environment
4. Entrypoint starts uvicorn server
5. Uvicorn imports `sessions.processor.main:app`
6. FastAPI app initializes with lifespan manager
7. Lifespan startup:
   - Load configuration
   - Initialize logging
   - Initialize encryption manager
   - Initialize Merkle tree manager
   - Initialize chunk processor service
   - Initialize integration manager
   - Connect to MongoDB and Redis
8. Service ready to accept requests

### Shutdown Sequence

1. Signal received (SIGTERM or SIGINT)
2. Signal handler initiates graceful shutdown
3. Lifespan shutdown:
   - Stop accepting new requests
   - Complete in-flight requests
   - Close integration clients
   - Close database connections
   - Clean up resources
4. Container exits

---

## Alignment Criteria

### Design Document Alignment

**Master Design Compliance**:
- ✅ Multi-stage build pattern (builder + runtime)
- ✅ Distroless base image
- ✅ Non-root user (65532:65532)
- ✅ Marker files pattern
- ✅ Runtime verification pattern
- ✅ Socket-based health check
- ✅ Entrypoint pattern (dedicated entrypoint.py)
- ✅ Environment variable configuration
- ✅ Security practices (read-only, dropped capabilities)

**Dockerfile Design Compliance**:
- ✅ Builder stage pattern
- ✅ Runtime stage pattern
- ✅ Package installation pattern
- ✅ Verification strategy
- ✅ COPY pattern (entire directories)

### Code Organization Alignment

**Module Structure**:
- ✅ Clear separation of concerns
- ✅ Reusable core components
- ✅ Service-specific modules isolated
- ✅ Integration clients centralized
- ✅ Configuration management centralized

**Import Patterns**:
- ✅ Absolute imports for cross-package imports
- ✅ Try/except for optional imports
- ✅ No relative imports that fail in containers

### Configuration Alignment

**Configuration Philosophy**:
- ✅ No hardcoded values
- ✅ Environment variable driven
- ✅ YAML file optional (with env var fallbacks)
- ✅ Validation on startup
- ✅ Sensible defaults for optional settings

### Error Handling Alignment

**Error Handling Patterns**:
- ✅ Graceful degradation
- ✅ Clear error messages
- ✅ Structured logging
- ✅ Try/except for optional imports
- ✅ Signal handlers for graceful shutdown

### Integration Alignment

**Integration Patterns**:
- ✅ Lazy initialization
- ✅ Centralized integration manager
- ✅ Retry logic with exponential backoff
- ✅ Health check methods
- ✅ Service client base pattern

### Build Alignment

**Build Process**:
- ✅ Multi-stage build
- ✅ Package verification in builder
- ✅ Package verification in runtime
- ✅ Application file verification
- ✅ Marker file verification
- ✅ Dynamic library copying

### Security Alignment

**Security Practices**:
- ✅ Distroless base image
- ✅ Non-root user
- ✅ No hardcoded secrets
- ✅ Read-only filesystem
- ✅ Dropped capabilities
- ✅ Security options configured

### Performance Alignment

**Performance Practices**:
- ✅ Lazy initialization of clients
- ✅ Connection pooling for HTTP clients
- ✅ Async operations for I/O
- ✅ Resource cleanup on shutdown
- ✅ Concurrent processing with worker pools

### Observability Alignment

**Observability Practices**:
- ✅ Health check endpoint (`/health`)
- ✅ Readiness endpoint (`/ready`)
- ✅ Metrics collection
- ✅ Structured logging
- ✅ Error scenario handling

---

## Design Principles Summary

### 1. Security First

- Distroless base image (minimal attack surface)
- Non-root user execution
- Read-only filesystem
- Dropped capabilities
- No hardcoded secrets
- Encrypted data at rest

### 2. Configuration Driven

- All configuration from environment variables
- YAML files optional (with env var overrides)
- No hardcoded values
- Validation on startup
- Sensible defaults

### 3. Robust Error Handling

- Graceful degradation
- Clear error messages
- Retry logic for transient failures
- Error isolation
- Comprehensive logging

### 4. Performance Optimized

- Concurrent processing with worker pools
- Async/await architecture
- Connection pooling
- Efficient compression algorithms
- Resource cleanup

### 5. Observability Built-In

- Health checks
- Metrics collection
- Structured logging
- Error tracking
- Performance monitoring

### 6. Integration Ready

- Service client pattern
- Retry logic
- Health check aggregation
- Service discovery support
- Error isolation

### 7. Build Verification

- Package verification in builder
- Package verification in runtime
- File verification
- Marker file verification
- Import verification

---

## Version History

- **v1.0.0** (2025-01-27): Initial design document for session-processor container

---

## Related Documents

- `master-docker-design.md` - Universal design patterns for all containers
- `dockerfile-design.md` - Dockerfile-specific patterns
- `session-recorder-design.md` - Similar service design reference
- `session-pipeline-design.md` - Pipeline orchestration design
- `data-chain-design.md` - Error resolution examples

---

## Notes

- This document represents the design principles and alignment criteria for the session-processor container
- All design decisions align with the master design document
- Deviations from master design are documented with justification
- Container must comply with all shared standards from master design
- Service-specific patterns are documented here

