# Master Docker Design - Shared Design Factors

## Overview

This document consolidates **all common and shared design factors** found across all Lucid container design documents. It serves as the single source of truth for universal patterns, practices, and standards that apply to all Python distroless containers in the Lucid project.

**Purpose**: Reference document for creating new containers and ensuring consistency across all services.

**Scope**: Only includes patterns, practices, and standards that are **universally shared** across all design documents.

---

## Table of Contents

1. [Architecture Foundation](#architecture-foundation)
2. [Build Arguments](#build-arguments)
3. [Builder Stage Pattern](#builder-stage-pattern)
4. [Runtime Stage Pattern](#runtime-stage-pattern)
5. [Security Practices](#security-practices)
6. [Environment Variables](#environment-variables)
7. [Package Management](#package-management)
8. [Verification Strategy](#verification-strategy)
9. [Health Check Pattern](#health-check-pattern)
10. [Entrypoint Pattern](#entrypoint-pattern)
11. [Module Organization](#module-organization)
12. [Configuration Philosophy](#configuration-philosophy)
13. [Error Handling](#error-handling)
14. [Integration Patterns](#integration-patterns)
15. [Best Practices](#best-practices)

---

## Architecture Foundation

### Multi-Stage Build Pattern

**Universal Pattern**: All containers use a two-stage build architecture.

**Stage 1 - Builder**:
- Base: `python:3.11-slim-bookworm`
- Purpose: Install build dependencies, compile Python packages
- Working Directory: `/build`

**Stage 2 - Runtime**:
- Base: `gcr.io/distroless/python3-debian12:latest`
- Purpose: Minimal runtime with only required artifacts
- Working Directory: `/app`

**Rationale**:
- Minimal attack surface (distroless base)
- Smaller image size (~60% reduction)
- Better security posture
- ARM64-first (Raspberry Pi compatible)

---

## Build Arguments

**Universal Build Arguments** (all containers):

```dockerfile
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11
```

**Usage**:
- `BUILD_DATE`: Build timestamp for metadata
- `VCS_REF`: Git commit hash
- `VERSION`: Service version number
- `TARGETPLATFORM`: Target architecture (ARM64)
- `BUILDPLATFORM`: Build host architecture
- `PYTHON_VERSION`: Python version (3.11)

---

## Builder Stage Pattern

### Base Image & Environment

```dockerfile
FROM --platform=$TARGETPLATFORM python:3.11-slim-bookworm AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    DEBIAN_FRONTEND=noninteractive
```

### System Packages Installation

**Universal Pattern**: Single `apt-get` block with Docker cache mounts.

```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        pkg-config \
        curl \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

**Required Build Dependencies**:
- `build-essential`: Compiler toolchain
- `gcc`, `g++`: C/C++ compilers
- `libffi-dev`: Foreign function interface
- `libssl-dev`: SSL/TLS library
- `pkg-config`: Package configuration
- `curl`: Download tool
- `ca-certificates`: CA certificates

### System Directory Markers

**Universal Pattern**: Create contentful marker files for system directories.

```dockerfile
WORKDIR /build

# Ensures /var/run and /var/lib exist with real content (COPY won't be silent)
RUN echo "LUCID_<SERVICE>_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_<SERVICE>_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib
```

**Purpose**: Prevent silent COPY failures in distroless runtime stage.

### Python Package Installation

**Universal Pattern**: Install packages to user directory with cache mounts.

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

COPY <service>/requirements.txt ./requirements.txt

RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --prefer-binary -r requirements.txt
```

**Key Points**:
- Install to `/root/.local/lib/python3.11/site-packages`
- Use `--user` flag for user installation
- Use `--no-cache-dir` to reduce image size
- Use `--prefer-binary` for faster installs
- Cache pip downloads with Docker cache mounts

### Marker Files Pattern

**Universal Pattern**: Create contentful marker files after package installation.

```dockerfile
RUN echo "LUCID_<SERVICE>_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_<SERVICE>_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local
```

**Purpose**: 
- Ensure directory structure is "locked in"
- Prevent silent COPY failures
- Verify package installation succeeded

**Requirements**:
- Marker files must have **actual content** (not empty)
- Include timestamp for uniqueness
- Set ownership to `65532:65532` (non-root user)

### Builder-Stage Verification

**Universal Pattern**: Verify critical packages in builder stage.

```dockerfile
RUN python3 -c "import fastapi, uvicorn, pydantic; print('✅ critical packages installed')" && \
    python3 -c "import uvicorn; print('uvicorn location:', uvicorn.__file__)" && \
    test -d /root/.local/lib/python3.11/site-packages && \
    test -f /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    test -s /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "✅ Marker file verified in builder (non-empty)"
```

**Key Points**:
- Import critical packages to verify installation
- Verify directory exists
- Verify marker file exists and is non-empty
- Adjust import list per service requirements

---

## Runtime Stage Pattern

### Base Image & Labels

```dockerfile
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid <Service>" \
      org.opencontainers.image.description="Distroless <service> for Lucid project" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="<service-id>" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="core" \
      com.lucid.security="distroless"
```

**Label Standards**:
- OCI image labels for metadata
- Lucid-specific labels for service identification
- Version and build information

### System Directories & Certificates

```dockerfile
# Copy system directories with proper ownership
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib

# Copy CA certificates for TLS verification
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
```

**Key Points**:
- Copy system directories from builder
- Set ownership to `65532:65532`
- Copy CA certificates for HTTPS/TLS connections

### Python Package Copy

```dockerfile
# Copy Python packages from builder to runtime
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin
```

**Key Points**:
- Copy from `/root/.local/lib/python3.11/site-packages` (builder)
- Copy to `/usr/local/lib/python3.11/site-packages` (runtime)
- Set ownership to `65532:65532`
- Copy binaries to `/usr/local/bin`

### Runtime Verification

**Universal Pattern**: Verify packages in runtime stage before application copy.

```dockerfile
RUN ["/usr/bin/python3.11", "-c", "import sys; import os; \
site_packages = '/usr/local/lib/python3.11/site-packages'; \
sys.path.insert(0, site_packages); \
assert os.path.exists(site_packages), site_packages + ' does not exist'; \
# Verify critical packages exist \
assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; \
assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; \
# Verify marker file \
marker_path = os.path.join(site_packages, '.lucid-marker'); \
assert os.path.exists(marker_path), 'marker file not found'; \
assert os.path.getsize(marker_path) > 0, 'marker file is empty'; \
# Actually import packages \
import uvicorn; assert uvicorn, 'uvicorn import failed'; \
import fastapi; assert fastapi, 'fastapi import failed'; \
print('✅ All packages verified in runtime stage')"]
```

**Verification Requirements**:
- Verify site-packages directory exists
- Verify critical packages exist
- Verify marker file exists and is non-empty
- Actually import packages to verify functionality
- Extend assertions per service requirements

---

## Security Practices

### Universal Security Standards

**All containers must implement**:

1. **Distroless Base Image**
   - No shell, package manager, or unnecessary binaries
   - Minimal attack surface
   - Reduced CVE exposure

2. **Non-Root User**
   - User: `65532:65532`
   - Set with `USER 65532:65532`
   - All files owned by non-root user

3. **No Hardcoded Secrets**
   - All secrets from environment variables
   - No credentials in code or Dockerfile
   - Use `.env` files or secrets management

4. **Read-Only Filesystem** (where applicable)
   - Use `read_only: true` in docker-compose
   - Mount writable volumes for data directories
   - Prevents unauthorized file modifications

5. **Dropped Capabilities** (where applicable)
   - Use `cap_drop: ALL` in docker-compose
   - Remove unnecessary Linux capabilities
   - Follow principle of least privilege

### Security Implementation

```dockerfile
# Runtime stage
USER 65532:65532

# All COPY operations use --chown=65532:65532
COPY --chown=65532:65532 --from=builder ...
```

**Docker Compose Security**:
```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
read_only: true
tmpfs:
  - /tmp:noexec,nosuid,size=200m
```

---

## Environment Variables

### Universal Environment Variables

**All containers set these environment variables**:

```dockerfile
ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    <SERVICE>_PORT=<PORT> \
    <SERVICE>_HOST=0.0.0.0
```

**Environment Variable Standards**:

| Variable | Purpose | Value |
|----------|---------|-------|
| `PYTHONUNBUFFERED` | Disable Python output buffering | `1` |
| `PYTHONDONTWRITEBYTECODE` | Don't write `.pyc` files | `1` |
| `PYTHONPATH` | Python module search path | `/app:/usr/local/lib/python3.11/site-packages` |
| `PYTHONIOENCODING` | I/O encoding | `utf-8` |
| `LANG` | Locale | `C.UTF-8` |
| `LC_ALL` | Locale | `C.UTF-8` |
| `<SERVICE>_HOST` | Bind address | `0.0.0.0` (always) |
| `<SERVICE>_PORT` | Service port | Service-specific |

**Important**: `HOST` must always be `0.0.0.0` (bind to all interfaces), not a hostname.

---

## Package Management

### Requirements File Pattern

**Universal Pattern**: Service-specific requirements files.

**Location**: `<service>/requirements.txt` or `sessions/requirements.<service>.txt`

**Installation Pattern**:
```dockerfile
COPY <service>/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --prefer-binary -r requirements.txt
```

**Best Practices**:
- Pin versions for production (`package>=x.y.z,<x+1.0.0`)
- Use service-specific requirements files
- Only include packages actually used
- Group packages by category (core, database, monitoring, etc.)

### Package Verification

**Universal Pattern**: Verify packages in both builder and runtime stages.

**Builder Stage**:
- Import critical packages
- Verify marker file exists and is non-empty

**Runtime Stage**:
- Verify site-packages directory exists
- Verify critical packages exist
- Verify marker file exists and is non-empty
- Actually import packages

---

## Verification Strategy

### Universal Verification Requirements

**All containers must verify**:

1. **Builder Stage**:
   - Critical packages import successfully
   - Marker files exist and are non-empty
   - Directory structure is correct

2. **Runtime Stage**:
   - Site-packages directory exists
   - Critical packages exist
   - Marker files exist and are non-empty
   - Packages can be imported
   - Application source files copied correctly
   - Entrypoint exists and is executable

### Verification Pattern

```dockerfile
# Builder verification
RUN python3 -c "import <critical_packages>; print('✅ packages installed')" && \
    test -f /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    test -s /root/.local/lib/python3.11/site-packages/.lucid-marker

# Runtime verification
RUN ["/usr/bin/python3.11", "-c", "import os; \
assert os.path.exists('/usr/local/lib/python3.11/site-packages'), 'site-packages missing'; \
assert os.path.exists('/usr/local/lib/python3.11/site-packages/.lucid-marker'), 'marker missing'; \
assert os.path.getsize('/usr/local/lib/python3.11/site-packages/.lucid-marker') > 0, 'marker empty'; \
import uvicorn; import fastapi; \
print('✅ Verification complete')"]
```

---

## Health Check Pattern

### Universal Health Check

**All containers use socket-based health checks**:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', <PORT>)); s.close(); exit(0 if result == 0 else 1)"]
```

**Health Check Standards**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `interval` | `30s` | Check interval |
| `timeout` | `10s` | Check timeout |
| `start-period` | `40s` | Grace period for startup |
| `retries` | `3` | Consecutive failures before unhealthy |

**Key Points**:
- Use Python socket module (no external tools)
- Connect to `127.0.0.1` (localhost)
- Use service-specific port
- Exit code 0 = healthy, 1 = unhealthy

**Rationale**:
- Works in distroless images (no shell/curl needed)
- Fast and reliable
- No external dependencies
- Standard across all services

---

## Entrypoint Pattern

### Universal Entrypoint Pattern

**All containers follow this pattern**:

```dockerfile
# Clear base ENTRYPOINT so CMD works as expected
ENTRYPOINT []

# Use JSON-form CMD with explicit Python path
CMD ["/usr/bin/python3.11", "/app/<service-path>/entrypoint.py"]
```

**Entrypoint Script Pattern**:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service Entrypoint
UTF-8 encoded entrypoint script for distroless container
"""

import os
import sys

# Ensure site-packages is in Python path
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

if __name__ == "__main__":
    # Get configuration from environment variables
    port_str = os.getenv('<SERVICE>_PORT', '<default_port>')
    host = '0.0.0.0'  # Always bind to all interfaces
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid <SERVICE>_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
    except ImportError as e:
        print(f"ERROR: Failed to import uvicorn: {e}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run('<module.path>.main:app', host=host, port=port)
```

**Key Points**:
- Clear `ENTRYPOINT []` to avoid base image interference
- Use explicit Python path: `/usr/bin/python3.11`
- Read port from environment variable
- Always bind to `0.0.0.0` (all interfaces)
- Handle errors gracefully
- UTF-8 encoding support

---

## Module Organization

### Universal Module Structure

**All containers follow this module organization**:

```
/app/
├── <service>/              # Service-specific modules
│   ├── __init__.py
│   ├── main.py            # FastAPI application
│   ├── entrypoint.py      # Container entrypoint
│   ├── config.py          # Configuration management
│   └── integration/       # Service integration clients
│       ├── __init__.py
│       ├── integration_manager.py
│       └── service_base.py
├── core/                  # Shared core modules (if applicable)
│   ├── __init__.py
│   ├── logging.py
│   └── ...
└── /usr/local/lib/python3.11/site-packages/  # Python packages
```

**Core Module Standards**:

1. **`main.py`**: FastAPI application with lifespan management
2. **`entrypoint.py`**: Container entrypoint script
3. **`config.py`**: Configuration management (Pydantic/YAML)
4. **`integration/`**: Service-to-service communication clients

**Module Organization Principles**:
- Clear separation of concerns
- Reusable core components
- Service-specific modules isolated
- Integration clients centralized

---

## Configuration Philosophy

### Universal Configuration Standards

**All containers follow these configuration principles**:

1. **No Hardcoded Values**
   - All configuration from environment variables
   - YAML files optional (with env var fallbacks)
   - No secrets in code

2. **Environment Variable Driven**
   - Primary configuration source
   - Override YAML file values
   - Required for secrets and URLs

3. **Validation on Startup**
   - Validate all configuration
   - Fail fast with clear error messages
   - Sensible defaults for optional settings

4. **Configuration Loading Pattern**:
   ```python
   # Load from YAML (optional)
   config_dict = load_yaml_config() if yaml_exists else {}
   
   # Override with environment variables
   config_dict['database']['mongodb_url'] = os.getenv('MONGODB_URL', '')
   
   # Validate and create config object
   config = ConfigClass(**config_dict)
   config.validate()
   ```

5. **Error Handling**:
   - Clear error messages for missing required config
   - Log configuration loading
   - Fallback to defaults when appropriate

---

## Error Handling

### Universal Error Handling Patterns

**All containers implement**:

1. **Graceful Degradation**
   - Services start even if optional integrations fail
   - Log warnings for non-critical failures
   - Continue operation with reduced functionality

2. **Clear Error Messages**
   - Include actionable information
   - Specify what failed and why
   - Provide resolution suggestions

3. **Structured Logging**
   - Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
   - Include context in log messages
   - Structured format for parsing

4. **Try/Except for Optional Imports**:
   ```python
   try:
       from core.logging import get_logger
   except ImportError:
       import logging
       logger = logging.getLogger(__name__)
       def get_logger(name):
           return logging.getLogger(name)
   ```

5. **Signal Handlers**:
   ```python
   def setup_signal_handlers():
       def signal_handler(signum, frame):
           logger.info(f"Received signal {signum}, initiating graceful shutdown...")
           sys.exit(0)
       
       signal.signal(signal.SIGINT, signal_handler)
       signal.signal(signal.SIGTERM, signal_handler)
   ```

---

## Integration Patterns

### Universal Integration Patterns

**All containers use**:

1. **Lazy Initialization**
   - Clients created only when needed
   - Reduces startup time
   - Handles missing services gracefully

2. **Centralized Integration Manager**
   - Single point of configuration
   - Consistent error handling
   - Health check aggregation

3. **Retry Logic with Exponential Backoff**
   - Configurable retry count
   - Exponential backoff delay
   - No retry on 4xx errors (client errors)
   - Retry on 5xx errors and timeouts

4. **Service Client Base Pattern**:
   ```python
   class ServiceClientBase:
       def __init__(self, base_url, timeout, retry_count, retry_delay):
           self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
           self.retry_count = retry_count
           self.retry_delay = retry_delay
       
       async def _make_request(self, method, endpoint, **kwargs):
           # Retry logic with exponential backoff
           pass
   ```

5. **Health Check Methods**
   - Each client implements `health_check()`
   - Integration manager aggregates health status
   - Used for service discovery and monitoring

---

## Best Practices

### Universal Best Practices

**All containers must follow**:

1. **Import Management**
   - Use absolute imports for cross-package imports
   - Use try/except for optional imports
   - Avoid relative imports that can fail in containers

2. **Configuration Management**
   - Never hardcode values
   - YAML files optional, env vars required
   - Validate configuration on startup
   - Log configuration loading

3. **Error Handling**
   - Graceful degradation for optional features
   - Clear error messages with actionable information
   - Proper logging with appropriate levels

4. **Security**
   - Non-root user (65532:65532)
   - Distroless base image
   - No secrets in code
   - Input validation

5. **Performance**
   - Lazy initialization of clients
   - Connection pooling for HTTP clients
   - Async operations for I/O
   - Resource cleanup on shutdown

6. **Testing**
   - Health check endpoint (`/health`)
   - Integration tests for service interactions
   - Error scenario testing
   - Container verification in Dockerfile

7. **Documentation**
   - Document all environment variables
   - Document API endpoints
   - Document error codes and messages
   - Include troubleshooting guides

---

## Design Rules Summary

### Always Use

- `python:3.11-slim-bookworm` for builder
- `gcr.io/distroless/python3-debian12:latest` for runtime
- Install packages to `/root/.local` in builder
- Copy to `/usr/local/lib/python3.11/site-packages` in runtime
- Create contentful marker files after `pip install`
- Verify packages in both builder and runtime stages
- Use `COPY --chown=65532:65532` for all files
- Run as `USER 65532:65532`
- Clear `ENTRYPOINT []` and use JSON-form `CMD`
- Socket-based health checks
- Environment variable configuration
- Explicit Python path: `/usr/bin/python3.11`

### Never Use

- Shells (`/bin/sh`, `bash`) in runtime stage
- External tools (`curl`, `wget`) in health checks
- System linkers/runtimes from builder in runtime
- Empty `touch`/`> file` placeholders
- Hardcoded secrets or credentials
- Relative imports that can fail in containers
- Hostnames for bind addresses (use `0.0.0.0`)

---

## Related Documents

- `dockerfile-design.md` - Detailed Dockerfile patterns
- `session-recorder-design.md` - Service template example
- `session-pipeline-design.md` - Complex service example
- `data-chain-design.md` - Error resolution examples
- `service-mesh-design.md` - Service-specific patterns

---

## Version History

- **v1.0.0** (2025-01-27): Initial master design document consolidating all shared patterns

---

## Notes

- This document represents **universal patterns only**
- Service-specific patterns are documented in individual design documents
- All containers must comply with these shared standards
- Deviations require justification and documentation

