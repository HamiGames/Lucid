# Session Pipeline Container Design and Build Documentation

**Service**: `lucid-session-pipeline`  
**Image**: `pickme/lucid-session-pipeline:latest-arm64`  
**Container Name**: `session-pipeline`  
**Port**: 8083  
**Document Version**: 1.0.0  
**Last Updated**: 2025-01-27

---

## Table of Contents

1. [Container Overview](#container-overview)
2. [Architecture and Design Decisions](#architecture-and-design-decisions)
3. [Module Structure and Components](#module-structure-and-components)
4. [Design Patterns](#design-patterns)
5. [Configuration Management](#configuration-management)
6. [State Machine Design](#state-machine-design)
7. [Integration Patterns](#integration-patterns)
8. [Build Specification](#build-specification)
9. [Dependencies and Requirements](#dependencies-and-requirements)
10. [Deployment and Runtime](#deployment-and-runtime)

---

## Container Overview

### Purpose

The session-pipeline container provides the Lucid Session Pipeline Manager service, orchestrating the complete session processing pipeline lifecycle:

- **Pipeline Orchestration**: Manages 6-stage session processing pipeline (recording → chunking → compression → encryption → merkle building → storage)
- **State Management**: Implements state machine for pipeline lifecycle control
- **Session Lifecycle**: Handles session creation, activation, pausing, stopping, and cleanup
- **Worker Management**: Manages concurrent workers for each pipeline stage
- **Integration Coordination**: Coordinates with external services (blockchain-engine, node-manager, API gateway, auth-service)
- **Error Handling**: Implements retry logic and error recovery mechanisms
- **Metrics and Monitoring**: Tracks pipeline performance metrics and health status

### Technology Stack

- **Base Image**: `gcr.io/distroless/python3-debian12:latest` (distroless, ARM64)
- **Python Version**: 3.11
- **Framework**: FastAPI + Uvicorn
- **Database**: MongoDB (via motor/pymongo), Redis (via aioredis)
- **Build Architecture**: Multi-stage build (builder + runtime)
- **User**: Non-root (UID/GID 65532:65532)
- **Security**: Distroless base (minimal attack surface), read-only filesystem, dropped capabilities

### Key Characteristics

- **Security**: Distroless base image with non-root user
- **Performance**: Async/await architecture for concurrent processing
- **Reliability**: State machine-based lifecycle management with error recovery
- **Scalability**: Configurable worker pools per pipeline stage
- **Observability**: Structured logging, metrics collection, health checks
- **Configuration**: Environment-driven configuration (no hardcoded values)

---

## Architecture and Design Decisions

### 1. Multi-Stage Build Pattern

**Decision**: Use multi-stage build with separate builder and runtime stages.

**Rationale**:
- Builder stage: Full Python image with build tools for compiling native extensions (zstd, cryptography, blake3)
- Runtime stage: Distroless image for minimal size and security
- Reduces final image size significantly while maintaining functionality

**Implementation**:
```dockerfile
FROM python:3.11-slim-bookworm AS builder
# Install build dependencies, compile packages

FROM gcr.io/distroless/python3-debian12:latest
# Copy only runtime artifacts (packages, source code)
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
- Health checks use Python socket/HTTP libraries
- Entrypoint uses Python interpreter directly
- Debugging requires exec into Python REPL

### 3. Modular Package Structure

**Decision**: Separate pipeline, core, and encryption modules.

**Rationale**:
- Clear separation of concerns
- Reusable core components (chunker, merkle_builder, logging)
- Encryption module shared with other session services
- Easier testing and maintenance

**Module Layout**:
```
/app/
├── pipeline/          # Pipeline-specific code
│   ├── main.py       # FastAPI application
│   ├── entrypoint.py # Container entrypoint
│   ├── config.py     # Configuration management
│   ├── pipeline_manager.py  # Main orchestration logic
│   ├── state_machine.py     # State management
│   └── integration/  # External service clients
├── core/             # Shared core components
│   ├── chunker.py    # Session chunking
│   ├── merkle_builder.py  # Merkle tree construction
│   ├── session_orchestrator.py  # Session orchestration
│   └── logging.py    # Logging utilities
└── encryption/       # Encryption module
    └── encryptor.py  # XChaCha20-Poly1305 encryption
```

### 4. State Machine Pattern

**Decision**: Implement explicit state machine for pipeline lifecycle.

**Rationale**:
- Enforces valid state transitions
- Prevents invalid operations
- Provides clear lifecycle management
- Enables state-based error recovery

**States**:
- `CREATED` → Initial state after pipeline creation
- `STARTING` → Pipeline initialization in progress
- `ACTIVE` → Pipeline processing data
- `PAUSING` → Pipeline pausing
- `PAUSED` → Pipeline paused (can resume)
- `STOPPING` → Pipeline stopping
- `STOPPED` → Pipeline stopped (cannot resume)
- `ERROR` → Error state (can recover)
- `CLEANUP` → Cleanup in progress
- `DESTROYED` → Final state

### 5. Worker Pool Pattern

**Decision**: Use configurable worker pools per pipeline stage.

**Rationale**:
- Allows independent scaling of each stage
- Prevents bottlenecks by parallelizing work
- Configurable per environment (dev/staging/prod)
- Resource isolation per stage

**Configuration**:
- Worker count per stage (e.g., RECORDER_WORKERS=2, ENCRYPTOR_WORKERS=4)
- Buffer size per stage (queue depth)
- Timeout per stage (error detection)
- Retry count per stage (resilience)

### 6. Integration Client Pattern

**Decision**: Centralized integration manager with lazy-initialized clients.

**Rationale**:
- Single point of configuration for external services
- Lazy initialization (only creates clients when needed)
- Consistent error handling and retry logic
- Easy to mock for testing

**Integration Services**:
- Blockchain Engine Client (for Merkle root anchoring)
- Node Manager Client (for node coordination)
- API Gateway Client (for routing)
- Auth Service Client (for authentication)

---

## Module Structure and Components

### Core Modules

#### 1. `pipeline/main.py`

**Purpose**: FastAPI application entry point and lifespan management.

**Responsibilities**:
- FastAPI app initialization
- Application lifespan management (startup/shutdown)
- Signal handling for graceful shutdown
- Route registration and middleware setup
- Global exception handling
- Health check endpoint

**Key Components**:
- `lifespan()`: Async context manager for app lifecycle
- `setup_signal_handlers()`: SIGINT/SIGTERM handling
- FastAPI app with CORS middleware
- Exception handlers for error responses

#### 2. `pipeline/entrypoint.py`

**Purpose**: Container entrypoint script.

**Responsibilities**:
- Parse environment variables (PORT, HOST)
- Import and run uvicorn server
- Handle invalid configuration gracefully
- UTF-8 encoding support

**Key Features**:
- Reads `SESSION_PIPELINE_PORT` from environment
- Binds to `0.0.0.0` (all interfaces)
- Runs `pipeline.main:app` via uvicorn

#### 3. `pipeline/config.py`

**Purpose**: Configuration management using Pydantic Settings.

**Responsibilities**:
- Define configuration schema (PipelineSettings)
- Validate environment variables
- Provide default values
- Override logic (e.g., PORT from SESSION_PIPELINE_PORT)

**Key Classes**:
- `WorkerConfig`: Worker pool configuration
- `StageConfig`: Pipeline stage configuration
- `PipelineSettings`: All pipeline settings (Pydantic BaseSettings)
- `PipelineConfig`: Main configuration manager

**Configuration Categories**:
- Service Configuration (name, version, debug, log level)
- Pipeline Configuration (max sessions, chunk size, compression level)
- Worker Configuration (counts per stage: recorder, chunk, compressor, encryptor, merkle, storage)
- Buffer Configuration (sizes per stage)
- Timeout Configuration (per stage)
- Retry Configuration (per stage)
- Memory Configuration (max MB per stage)
- Database Configuration (MongoDB, Redis, Elasticsearch URLs)
- Storage Configuration (paths for chunks, sessions, temp)
- Network Configuration (host, port, service URLs)
- Security Configuration (secret keys, encryption keys)
- Monitoring Configuration (metrics, health check interval)
- Integration Configuration (service URLs, timeouts, retries)
- Quality Configuration (default quality, frame rate, resolution)
- CORS Configuration (allowed origins)

**Validation**:
- Custom validators for chunk size, compression level, max sessions
- MongoDB/Redis URL validation (no localhost)
- Health check interval parser (handles '30s' format)

#### 4. `pipeline/pipeline_manager.py`

**Purpose**: Main pipeline orchestration logic.

**Responsibilities**:
- Pipeline creation and lifecycle management
- Worker pool management per stage
- Stage processing coordination
- Error handling and recovery
- Metrics collection
- Integration with external services

**Key Classes**:
- `PipelineMetrics`: Performance metrics dataclass
- `PipelineStage`: Stage configuration dataclass
- `SessionPipeline`: Pipeline instance dataclass
- `PipelineManager`: Main orchestration class

**Key Methods**:
- `create_pipeline()`: Create new pipeline for session
- `start_pipeline()`: Start pipeline processing
- `stop_pipeline()`: Stop pipeline gracefully
- `process_chunk()`: Process chunk through pipeline stages
- `_stage_worker()`: Worker function for stage processing
- `_generate_chunks()`: Chunk generation stage
- `_build_merkle_tree()`: Merkle tree building stage
- `_compress_chunk()`: Compression stage
- `_encrypt_chunk()`: Encryption stage

**Pipeline Stages (6-stage pipeline)**:
1. **Recording**: Record session data
2. **Chunk Generation**: Generate chunks from recorded data
3. **Compression**: Compress chunks (Zstd level 6)
4. **Encryption**: Encrypt chunks (XChaCha20-Poly1305)
5. **Merkle Building**: Build Merkle tree for integrity
6. **Storage**: Store processed chunks

#### 5. `pipeline/state_machine.py`

**Purpose**: State machine for pipeline lifecycle management.

**Responsibilities**:
- Define valid state transitions
- Enforce transition rules
- Track state history
- Validate transition requests

**Key Classes**:
- `PipelineState`: Enum of pipeline states
- `StateTransition`: Enum of transition triggers
- `StateTransitionRule`: Dataclass for transition rules
- `PipelineStateMachine`: State machine implementation

**State Transitions**:
- `CREATED` → `STARTING` (on START)
- `STARTING` → `ACTIVE` (on START_COMPLETE)
- `ACTIVE` → `PAUSING` (on PAUSE)
- `PAUSING` → `PAUSED` (on PAUSE_COMPLETE)
- `PAUSED` → `ACTIVE` (on RESUME)
- `ACTIVE` → `STOPPING` (on STOP)
- `STOPPING` → `STOPPED` (on STOP_COMPLETE)
- Any state → `ERROR` (on ERROR)
- `ERROR` → `ACTIVE` (on RECOVER)
- Any state → `CLEANUP` (on CLEANUP)
- `CLEANUP` → `DESTROYED` (on CLEANUP_COMPLETE)

#### 6. `pipeline/integration/`

**Purpose**: External service integration clients.

**Structure**:
- `integration_manager.py`: Centralized integration manager
- `service_base.py`: Base client class with retry logic
- `blockchain_engine_client.py`: Blockchain engine client
- `node_manager_client.py`: Node manager client
- `api_gateway_client.py`: API gateway client
- `auth_service_client.py`: Auth service client

**Pattern**: Base class (`ServiceClientBase`) provides:
- HTTP client with timeout
- Retry logic with exponential backoff
- Error handling (ServiceError, ServiceTimeoutError)
- Health check method
- Async context manager support

**Integration Manager**:
- Lazy initialization (clients created on first use)
- Centralized configuration
- Health check aggregation
- Error handling per client

### Core Module Dependencies

#### 7. `core/chunker.py`

**Purpose**: Session data chunking with Zstd compression.

**Key Features**:
- 8-16MB chunk size (configurable)
- Zstd compression (level 3 default)
- Chunk metadata generation
- Checksum calculation (SHA-256)
- Async chunk processing

**Classes**:
- `ChunkMetadata`: Chunk metadata dataclass
- `SessionChunker`: Chunking implementation

#### 8. `core/merkle_builder.py`

**Purpose**: Merkle tree construction for integrity verification.

**Key Features**:
- BLAKE3-based Merkle trees
- Proof generation
- Async tree building
- Root hash calculation

**Classes**:
- `MerkleNode`: Merkle tree node
- `MerkleRoot`: Root hash with proof capability
- `MerkleProof`: Proof structure
- `MerkleTreeBuilder`: Tree building implementation

#### 9. `core/session_orchestrator.py`

**Purpose**: High-level session orchestration (used by core, not directly by pipeline).

**Note**: Imported by `core/__init__.py` but not directly used by pipeline manager.

#### 10. `core/logging.py`

**Purpose**: Centralized logging utilities.

**Functions**:
- `setup_logging()`: Initialize logging configuration
- `get_logger()`: Get logger instance

#### 11. `encryption/encryptor.py`

**Purpose**: XChaCha20-Poly1305 encryption for chunks.

**Key Features**:
- Per-chunk encryption
- HKDF-BLAKE2b key derivation
- Nonce generation
- Tag verification

**Classes**:
- `EncryptedChunk`: Encrypted chunk structure
- `SessionEncryptor`: Encryption implementation

---

## Design Patterns

### 1. Dependency Injection

**Pattern**: Configuration injected via constructor.

**Example**:
```python
config = PipelineConfig()  # Reads from environment
pipeline_manager = PipelineManager(config)
```

**Benefits**:
- Testable (can inject mock config)
- Flexible (different configs per environment)
- Clear dependencies

### 2. Factory Pattern

**Pattern**: Pipeline creation via factory method.

**Example**:
```python
pipeline_id = await pipeline_manager.create_pipeline(session_id)
```

**Benefits**:
- Centralized creation logic
- Consistent initialization
- ID generation handled internally

### 3. Observer Pattern

**Pattern**: State machine tracks state changes.

**Example**:
```python
state_machine.transition(PipelineState.CREATED, StateTransition.START)
# State history automatically tracked
```

**Benefits**:
- Audit trail
- Debugging support
- State recovery

### 4. Strategy Pattern

**Pattern**: Different processing strategies per stage.

**Example**:
```python
if stage.stage_type == "compressor":
    result = await self._compress_chunk(data, stage)
elif stage.stage_type == "encryptor":
    result = await self._encrypt_chunk(data, stage)
```

**Benefits**:
- Extensible (add new stages easily)
- Isolated logic per stage
- Easy to test individual stages

### 5. Template Method Pattern

**Pattern**: Base class defines algorithm, subclasses implement steps.

**Example**: `ServiceClientBase` defines request flow, subclasses implement specific endpoints.

**Benefits**:
- Consistent error handling
- Shared retry logic
- Easy to add new clients

### 6. Singleton Pattern

**Pattern**: Single PipelineManager instance per container.

**Example**:
```python
pipeline_manager: Optional[PipelineManager] = None  # Global in main.py
```

**Benefits**:
- Resource efficiency
- Shared state (active pipelines)
- Centralized management

---

## Configuration Management

### Environment Variables

**Source**: docker-compose environment files:
- `.env.foundation` (database URLs, Redis, Elasticsearch)
- `.env.core` (service URLs, network config)
- `.env.application` (application-specific config)
- `.env.secrets` (secret keys, encryption keys)

### Configuration Loading

1. **Pydantic Settings**: `PipelineSettings` class reads from environment
2. **Validation**: Field validators ensure correct types and values
3. **Defaults**: Sensible defaults for all optional settings
4. **Overrides**: Special handling for PORT (from SESSION_PIPELINE_PORT)

### Configuration Categories

**Service Config**:
- `SERVICE_NAME`: Service identifier
- `DEBUG`: Debug mode flag
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

**Pipeline Config**:
- `MAX_CONCURRENT_SESSIONS`: Maximum active pipelines
- `CHUNK_SIZE_MB`: Target chunk size (8-16MB)
- `COMPRESSION_LEVEL`: Zstd compression level (1-9)

**Worker Config** (per stage):
- `{STAGE}_WORKERS`: Worker count (e.g., RECORDER_WORKERS=2)
- `{STAGE}_BUFFER_SIZE`: Queue depth
- `{STAGE}_TIMEOUT`: Operation timeout in seconds
- `{STAGE}_RETRY_COUNT`: Retry attempts
- `{STAGE}_MAX_MEMORY_MB`: Memory limit

**Database Config**:
- `MONGODB_URL`: MongoDB connection string (required, no localhost)
- `REDIS_URL`: Redis connection string (optional)
- `ELASTICSEARCH_URL`: Elasticsearch URL (optional)

**Storage Config**:
- `CHUNK_STORAGE_PATH`: Chunk storage directory (/app/data/chunks)
- `SESSION_STORAGE_PATH`: Session storage directory (/app/data/sessions)
- `TEMP_STORAGE_PATH`: Temporary storage (/tmp/pipeline)

**Network Config**:
- `SESSION_PIPELINE_HOST`: Service name (for URLs)
- `SESSION_PIPELINE_PORT`: Service port (8083)
- `BLOCKCHAIN_ENGINE_URL`: Blockchain engine service URL
- `NODE_MANAGEMENT_URL`: Node manager service URL
- `API_GATEWAY_URL`: API gateway service URL
- `AUTH_SERVICE_URL`: Auth service URL

**Security Config**:
- `SECRET_KEY`: Secret key for signing
- `ENCRYPTION_KEY`: Encryption key for chunks
- `JWT_SECRET_KEY`: JWT secret key

**Monitoring Config**:
- `METRICS_ENABLED`: Enable metrics collection
- `METRICS_PORT`: Metrics port (9093)
- `HEALTH_CHECK_INTERVAL`: Health check interval (30 seconds, accepts '30s' format)

**Integration Config**:
- `SERVICE_TIMEOUT_SECONDS`: Request timeout (30s default)
- `SERVICE_RETRY_COUNT`: Retry attempts (3 default)
- `SERVICE_RETRY_DELAY_SECONDS`: Retry delay (1.0s default)

---

## State Machine Design

### States

**Lifecycle States**:
- `CREATED`: Pipeline created but not started
- `STARTING`: Pipeline initialization in progress
- `ACTIVE`: Pipeline processing data
- `PAUSING`: Pipeline pausing (draining buffers)
- `PAUSED`: Pipeline paused (can resume)
- `STOPPING`: Pipeline stopping (graceful shutdown)
- `STOPPED`: Pipeline stopped (cannot resume)

**Error States**:
- `ERROR`: Error occurred (can recover)
- `CLEANUP`: Cleanup in progress
- `DESTROYED`: Final state (resources released)

### Transitions

**Valid Transitions**:

| From State | Trigger | To State | Description |
|------------|---------|----------|-------------|
| CREATED | START | STARTING | Begin initialization |
| STARTING | START_COMPLETE | ACTIVE | Initialization complete |
| ACTIVE | PAUSE | PAUSING | Begin pause |
| PAUSING | PAUSE_COMPLETE | PAUSED | Pause complete |
| PAUSED | RESUME | ACTIVE | Resume processing |
| ACTIVE | STOP | STOPPING | Begin stop |
| STOPPING | STOP_COMPLETE | STOPPED | Stop complete |
| Any | ERROR | ERROR | Error occurred |
| ERROR | RECOVER | ACTIVE | Recovery successful |
| Any | CLEANUP | CLEANUP | Begin cleanup |
| CLEANUP | CLEANUP_COMPLETE | DESTROYED | Cleanup complete |
| CREATED | DESTROY | DESTROYED | Immediate destroy |

**Invalid Transitions**: Raise `ValueError` with descriptive message.

### State History

**Tracking**:
- All state transitions logged
- Timestamp for each transition
- Transition trigger recorded
- Enables state recovery and debugging

---

## Integration Patterns

### Service Client Pattern

**Base Class**: `ServiceClientBase`

**Features**:
- Async HTTP client (httpx)
- Configurable timeout
- Retry logic with exponential backoff
- Error handling (ServiceError, ServiceTimeoutError)
- Health check method
- Async context manager support

**Implementation**:
```python
class BlockchainEngineClient(ServiceClientBase):
    async def anchor_merkle_root(self, root_hash: str) -> Dict[str, Any]:
        return await self._make_request('POST', '/anchor', json_data={'root': root_hash})
```

### Integration Manager

**Purpose**: Centralized management of all integration clients.

**Features**:
- Lazy initialization (clients created on first use)
- Configuration from PipelineConfig
- Health check aggregation
- Error isolation (one client failure doesn't affect others)

**Usage**:
```python
integration_manager = IntegrationManager(config)
await integration_manager.blockchain.anchor_merkle_root(root_hash)
health_status = await integration_manager.health_check_all()
```

### Retry Logic

**Pattern**: Exponential backoff with configurable attempts.

**Implementation**:
- Initial delay: `retry_delay` seconds
- Backoff: `delay * (attempt + 1)`
- Max attempts: `retry_count`
- No retry on 4xx errors (client errors)
- Retry on 5xx errors and timeouts

---

## Build Specification

### Dockerfile Structure

**Stage 1 - Builder**:
```dockerfile
FROM python:3.11-slim-bookworm AS builder
# Install build dependencies (gcc, g++, libffi-dev, libssl-dev)
# Install Python packages (pip install --user)
# Copy source code
```

**Stage 2 - Runtime**:
```dockerfile
FROM gcr.io/distroless/python3-debian12:latest
# Copy Python packages from builder
# Copy application source code
# Set environment variables
# Set user to 65532:65532
# Set entrypoint
```

### Build Arguments

- `BUILD_DATE`: Build timestamp
- `VCS_REF`: Git commit hash
- `VERSION`: Version number (1.0.0)
- `TARGETPLATFORM`: Target platform (linux/arm64)
- `BUILDPLATFORM`: Build platform (linux/amd64)
- `PYTHON_VERSION`: Python version (3.11)

### Build Process

1. **Builder Stage**:
   - Install build dependencies
   - Install Python packages to `/root/.local`
   - Copy source code to `/build`
   - Create marker files for verification

2. **Runtime Stage**:
   - Copy packages from builder
   - Copy source code from builder
   - Set ownership to 65532:65532
   - Verify package installation
   - Set entrypoint and CMD

### Source Code Structure

**Copied Modules**:
- `sessions/pipeline/` → `/app/pipeline/`
- `sessions/core/` → `/app/core/`
- `sessions/encryption/` → `/app/encryption/`
- `sessions/__init__.py` → `/app/__init__.py`

**PYTHONPATH**: `/app:/usr/local/lib/python3.11/site-packages`

---

## Dependencies and Requirements

### Python Dependencies

**Core Framework**:
- `fastapi>=0.111,<1.0`: Web framework
- `uvicorn[standard]>=0.30`: ASGI server
- `pydantic>=2.5.0`: Data validation
- `pydantic-settings>=2.1.0`: Settings management

**Async Support**:
- `asyncio-mqtt>=0.16.1`: MQTT client
- `aiofiles>=23.2.1`: Async file I/O
- `aioredis>=2.0.1`: Async Redis client

**Database**:
- `motor>=3.3.2`: Async MongoDB driver
- `pymongo>=4.6.0`: MongoDB driver

**HTTP Client**:
- `httpx>=0.25.2`: Async HTTP client
- `aiohttp>=3.9.1`: Alternative HTTP client

**Monitoring**:
- `structlog>=23.2.0`: Structured logging
- `prometheus-client>=0.19.0`: Metrics collection

**Cryptography**:
- `cryptography>=41.0.0`: Cryptographic primitives
- `blake3>=0.3.3`: BLAKE3 hashing

**Compression**:
- `zstd>=1.5.5`: Zstandard compression

**Utilities**:
- `python-multipart>=0.0.6`: Multipart form support
- `python-jose[cryptography]>=3.3.0`: JWT handling
- `passlib[bcrypt]>=1.7.4`: Password hashing

**Development**:
- `pytest>=7.4.3`: Testing framework
- `pytest-asyncio>=0.21.1`: Async test support
- `pytest-cov>=4.1.0`: Coverage reporting

### System Dependencies

**Build Dependencies** (builder stage only):
- `build-essential`: Compiler toolchain
- `gcc`, `g++`: C/C++ compilers
- `libffi-dev`: Foreign function interface
- `libssl-dev`: SSL/TLS library
- `pkg-config`: Package configuration
- `curl`: Download tool
- `ca-certificates`: CA certificates

**Runtime Dependencies**:
- None (provided by distroless base image)

---

## Deployment and Runtime

### Container Configuration

**User**: `65532:65532` (non-root)

**Working Directory**: `/app`

**Ports**:
- `8083`: HTTP API
- `9093`: Metrics (if enabled)

**Volumes**:
- `/mnt/myssd/Lucid/Lucid/data/session-pipeline:/app/data:rw` (data storage)
- `/mnt/myssd/Lucid/Lucid/logs/session-pipeline:/app/logs:rw` (logs)

**Environment**:
- `PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages`
- `PYTHONUNBUFFERED=1`
- `SESSION_PIPELINE_PORT=8083`
- `SESSION_PIPELINE_HOST=0.0.0.0`
- All configuration from docker-compose env files

**Security**:
- Read-only filesystem (`read_only: true`)
- Dropped capabilities (`cap_drop: ALL`)
- No new privileges (`no-new-privileges:true`)
- Tmpfs for /tmp (`tmpfs: /tmp:noexec,nosuid,size=200m`)

### Health Check

**Type**: Socket-based (no external dependencies)

**Command**:
```python
python3 -c "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8083)); s.close(); exit(0 if result == 0 else 1)"
```

**Configuration**:
- Interval: 30s
- Timeout: 10s
- Start period: 40s
- Retries: 3

### Startup Sequence

1. Container starts with `/usr/bin/python3.11 /app/pipeline/entrypoint.py`
2. Entrypoint reads `SESSION_PIPELINE_PORT` from environment
3. Uvicorn starts FastAPI app (`pipeline.main:app`)
4. `lifespan()` context manager runs:
   - Creates `PipelineConfig` instance
   - Validates configuration
   - Creates `PipelineManager` instance
   - Initializes integration manager
5. FastAPI app ready to accept requests

### Shutdown Sequence

1. Container receives SIGTERM/SIGINT
2. Signal handler triggers graceful shutdown
3. `lifespan()` cleanup runs:
   - Stops all active pipelines
   - Shuts down worker pools
   - Closes integration clients
   - Releases resources
4. Container exits

### API Endpoints

**Health Check**:
- `GET /health`: Service health status

**Pipeline Management**:
- `POST /pipelines`: Create new pipeline
- `POST /pipelines/{session_id}/start`: Start pipeline
- `POST /pipelines/{session_id}/stop`: Stop pipeline
- `GET /pipelines/{session_id}/status`: Get pipeline status
- `DELETE /pipelines/{session_id}`: Cleanup pipeline

**Chunk Processing**:
- `POST /pipelines/{session_id}/chunks`: Process chunk

**Configuration**:
- `GET /config`: Get pipeline configuration

**Metrics**:
- `GET /metrics`: Get pipeline metrics

**Status**:
- `GET /status`: Get service status

---

## Key Design Principles

### 1. Security First

- Distroless base image (minimal attack surface)
- Non-root user (65532:65532)
- Read-only filesystem
- Dropped capabilities
- No hardcoded secrets (all from environment)

### 2. Configuration Driven

- No hardcoded values
- All configuration from environment variables
- Validation via Pydantic
- Sensible defaults
- Clear error messages for missing required config

### 3. Async/Await Architecture

- All I/O operations are async
- Concurrent processing via worker pools
- Non-blocking service calls
- Efficient resource utilization

### 4. Error Resilience

- Retry logic with exponential backoff
- Error states in state machine
- Recovery mechanisms
- Graceful degradation
- Comprehensive error logging

### 5. Observability

- Structured logging (structlog)
- Metrics collection (prometheus-client)
- Health check endpoints
- State transition tracking
- Performance metrics

### 6. Testability

- Dependency injection
- Modular design
- Mockable integrations
- Clear interfaces
- Unit test support

### 7. Scalability

- Configurable worker pools
- Concurrent processing
- Buffer management
- Resource limits per stage
- Horizontal scaling support

---

## File Organization

### Source Files

```
sessions/pipeline/
├── __init__.py                 # Package exports
├── main.py                     # FastAPI application
├── entrypoint.py               # Container entrypoint
├── config.py                   # Configuration management
├── pipeline_manager.py         # Main orchestration
├── state_machine.py            # State management
├── chunk_processor.py          # Chunk processing utilities
├── merkle_tree_builder.py      # Merkle tree utilities
├── session_pipeline_manager.py # Alternative pipeline manager
├── test_step15_validation.py   # Validation tests
└── integration/
    ├── __init__.py
    ├── integration_manager.py  # Integration coordinator
    ├── service_base.py         # Base client class
    ├── blockchain_engine_client.py
    ├── node_manager_client.py
    ├── api_gateway_client.py
    └── auth_service_client.py
```

### Dependencies

```
sessions/
├── requirements.pipeline.txt   # Python dependencies
└── Dockerfile.pipeline         # Container build file
```

### Core Dependencies

```
sessions/core/
├── chunker.py                  # Session chunking
├── merkle_builder.py           # Merkle tree building
├── session_orchestrator.py     # Session orchestration
└── logging.py                  # Logging utilities

sessions/encryption/
└── encryptor.py                # Encryption module
```

---

## Summary

The session-pipeline container implements a robust, scalable, and secure session processing pipeline manager. Key characteristics:

- **Architecture**: Multi-stage build, distroless runtime, async/await
- **Design Patterns**: State machine, worker pools, integration clients, dependency injection
- **Configuration**: Environment-driven, Pydantic-validated, comprehensive defaults
- **Security**: Distroless base, non-root user, read-only filesystem, dropped capabilities
- **Observability**: Structured logging, metrics, health checks, state tracking
- **Resilience**: Retry logic, error recovery, graceful shutdown, resource limits

The container follows LUCID project standards and integrates seamlessly with other cluster services while maintaining isolation and security.

