# TRON Payment System API - Distroless Dockerfile

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-DOCKER-06A |
| Version | 1.0.0 |
| Status | IN PROGRESS |
| Last Updated | 2025-10-12 |
| Owner | Lucid RDP Development Team |

---

## Overview

This document provides a complete multi-stage Dockerfile for building distroless containers for the TRON Payment System API. The implementation follows SPEC-1B-v2 requirements for minimal attack surface and security hardening.

### Key Principles

- **Multi-stage Build**: Separate builder and runtime stages
- **Distroless Base**: Use `gcr.io/distroless/python3-debian12:nonroot`
- **Security Hardening**: Non-root user, read-only filesystem
- **Minimal Dependencies**: Only essential runtime components
- **Optimized Layers**: Efficient caching and minimal image size

---

## Complete Dockerfile Implementation

### Multi-Stage Dockerfile

```dockerfile
# ==============================================================================
# TRON Payment System API - Multi-Stage Distroless Dockerfile
# ==============================================================================
# 
# Build Command:
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     --target distroless \
#     --tag pickme/lucid:tron-payment-service:latest \
#     --file Dockerfile \
#     --push .
#
# Security Features:
#   - Distroless base image (no shell, no package managers)
#   - Non-root user (UID 65532)
#   - Read-only root filesystem
#   - Minimal attack surface
#   - Multi-platform support (AMD64/ARM64)
#
# SPEC-1B-v2 Compliance:
#   - Wallet plane isolation
#   - Payment-only operations
#   - No blockchain consensus operations
# ==============================================================================

# ==============================================================================
# Stage 1: Builder - Install dependencies and build application
# ==============================================================================
FROM python:3.12-slim-bookworm AS builder

# Build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION=3.12

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-prod.txt ./

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy application source
COPY payment-systems/tron-payment-service/ .

# Install application in development mode (will be copied to final stage)
RUN pip install --no-cache-dir -e .

# ==============================================================================
# Stage 2: Runtime - Distroless container with application
# ==============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS distroless

# Metadata labels
LABEL maintainer="Lucid RDP Development Team <dev@lucid-rdp.onion>"
LABEL org.opencontainers.image.title="TRON Payment System API"
LABEL org.opencontainers.image.description="Isolated TRON payment system for USDT-TRC20 payouts"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="Lucid RDP"
LABEL org.opencontainers.image.licenses="Proprietary"
LABEL org.opencontainers.image.url="https://lucid-rdp.onion"
LABEL org.opencontainers.image.source="https://github.com/HamiGames/Lucid"
LABEL org.opencontainers.image.documentation="https://lucid-rdp.onion/docs"

# Security labels
LABEL security.distroless="true"
LABEL security.nonroot="true"
LABEL security.readonly="true"
LABEL security.plane="wallet"
LABEL security.isolation="payment-only"

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV SERVICE_NAME=tron-payment-service
ENV SERVICE_PORT=8090
ENV LUCID_ENV=production

# Create application directory with proper permissions
USER nonroot:nonroot
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=nonroot:nonroot /opt/venv /opt/venv

# Copy application source with proper ownership
COPY --from=builder --chown=nonroot:nonroot /app /app

# Copy configuration files
COPY --chown=nonroot:nonroot configs/ /app/configs/

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/tmp /app/secrets && \
    chmod 755 /app/logs /app/tmp && \
    chmod 700 /app/secrets

# Set Python path to use virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Health check (HTTP-based, no shell required)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8090/health').read()"]

# Expose service port
EXPOSE 8090

# Switch to non-root user (redundant but explicit)
USER 65532:65532

# Default command
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "1"]

# ==============================================================================
# Stage 3: Development - Full development environment (optional)
# ==============================================================================
FROM python:3.12-slim-bookworm AS development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt requirements-dev.txt ./

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# Copy application source
COPY payment-systems/tron-payment-service/ .

# Install in development mode
RUN pip install --no-cache-dir -e .

# Expose ports
EXPOSE 8090 8091

# Development command with hot reload
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--reload", "--log-level", "debug"]
```

---

## Security Hardening Steps

### 1. User Configuration

```dockerfile
# Explicit non-root user configuration
USER 65532:65532

# Verify user permissions
RUN id && whoami
```

### 2. Filesystem Permissions

```dockerfile
# Create directories with minimal permissions
RUN mkdir -p /app/logs /app/tmp /app/secrets && \
    chmod 755 /app/logs /app/tmp && \
    chmod 700 /app/secrets

# Ensure proper ownership
COPY --chown=nonroot:nonroot /app /app
```

### 3. Read-Only Configuration

```dockerfile
# Runtime with read-only root filesystem
FROM gcr.io/distroless/python3-debian12:nonroot

# Mount writable directories as volumes
VOLUME ["/app/logs", "/app/tmp", "/app/secrets"]
```

---

## Build Instructions

### Local Development Build

```bash
# Build development image
docker buildx build \
  --target development \
  --tag tron-payment-service:dev \
  --file Dockerfile \
  .

# Run development container
docker run -it --rm \
  -p 8090:8090 \
  -v $(pwd)/configs:/app/configs:ro \
  -v $(pwd)/logs:/app/logs \
  tron-payment-service:dev
```

### Production Build

```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --target distroless \
  --tag pickme/lucid:tron-payment-service:latest \
  --tag pickme/lucid:tron-payment-service:v1.0.0 \
  --file Dockerfile \
  --push \
  .

# Build for specific platform (AMD64)
docker buildx build \
  --platform linux/amd64 \
  --target distroless \
  --tag pickme/lucid:tron-payment-service:latest-amd64 \
  --file Dockerfile \
  --push \
  .
```

### Build with BuildKit

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build with cache optimization
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --target distroless \
  --tag pickme/lucid:tron-payment-service:latest \
  --cache-from type=gha,scope=tron-payment \
  --cache-to type=gha,mode=max,scope=tron-payment \
  --file Dockerfile \
  --push \
  .
```

---

## Dependency Management

### Requirements Files Structure

```
payment-systems/tron-payment-service/
├── requirements.txt          # Core dependencies
├── requirements-prod.txt     # Production-only dependencies
└── requirements-dev.txt      # Development dependencies
```

### Core Dependencies (requirements.txt)

```txt
# FastAPI and ASGI server
fastapi==0.104.1
uvicorn[standard]==0.24.0

# TRON blockchain integration
tronpy==0.4.0

# Database
pymongo==4.6.0
motor==3.3.2

# HTTP client
httpx==0.25.2

# Configuration and validation
pydantic==2.5.0
pydantic-settings==2.1.0

# Security
cryptography==41.0.8
python-jose[cryptography]==3.3.0

# Monitoring and metrics
prometheus-client==0.19.0

# Utilities
python-multipart==0.0.6
python-dotenv==1.0.0
```

### Production Dependencies (requirements-prod.txt)

```txt
# Production-specific optimizations
gunicorn==21.2.0

# Monitoring
structlog==23.2.0

# Health checks
psutil==5.9.6
```

### Development Dependencies (requirements-dev.txt)

```txt
# Development tools
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0

# Code quality
black==23.11.0
ruff==0.1.6
mypy==1.7.1

# Testing utilities
httpx==0.25.2
factory-boy==3.3.0
```

---

## COPY Instructions with Proper Ownership

### Application Files

```dockerfile
# Copy application with proper ownership
COPY --from=builder --chown=nonroot:nonroot /app /app

# Copy configuration files
COPY --chown=nonroot:nonroot configs/ /app/configs/

# Copy secrets (read-only)
COPY --chown=nonroot:nonroot secrets/ /app/secrets:ro
```

### Static Assets

```dockerfile
# Copy static files with minimal permissions
COPY --chown=nonroot:nonroot static/ /app/static/
RUN chmod -R 644 /app/static/
```

---

## USER and WORKDIR Setup

### User Configuration

```dockerfile
# Explicit non-root user
USER 65532:65532

# Verify user context
RUN id && whoami && pwd
```

### Working Directory

```dockerfile
# Set working directory
WORKDIR /app

# Ensure directory exists and has proper permissions
RUN mkdir -p /app && chown nonroot:nonroot /app
```

---

## CMD and Health Check Setup

### Application Command

```dockerfile
# Production command with single worker
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "1"]

# Alternative with gunicorn for production
# CMD ["gunicorn", "main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8090"]
```

### Health Check Implementation

```dockerfile
# HTTP-based health check (no shell required)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8090/health').read()"]

# Alternative health check using curl (if available)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD ["curl", "-f", "http://localhost:8090/health"]
```

---

## Multi-Platform Support

### Build for Multiple Architectures

```bash
# Create builder instance
docker buildx create --name multiarch --use

# Build for AMD64 and ARM64
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --target distroless \
  --tag pickme/lucid:tron-payment-service:latest \
  --file Dockerfile \
  --push \
  .
```

### Platform-Specific Optimizations

```dockerfile
# Platform-specific build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Conditional installations based on platform
RUN case ${TARGETPLATFORM} in \
    "linux/amd64") echo "Building for AMD64" ;; \
    "linux/arm64") echo "Building for ARM64" ;; \
    *) echo "Unknown platform: ${TARGETPLATFORM}" ;; \
    esac
```

---

## Build Validation

### Image Verification Script

```bash
#!/bin/bash
# verify-distroless.sh

set -e

IMAGE_NAME="pickme/lucid:tron-payment-service:latest"

echo "Verifying distroless image: $IMAGE_NAME"

# Check if image exists
if ! docker image inspect $IMAGE_NAME >/dev/null 2>&1; then
    echo "❌ Image $IMAGE_NAME not found"
    exit 1
fi

# Check if image is distroless (no shell)
if docker run --rm $IMAGE_NAME /bin/sh -c "echo 'Shell available'" 2>/dev/null; then
    echo "❌ Image has shell access (not distroless)"
    exit 1
else
    echo "✅ Image is properly distroless"
fi

# Check if image runs as non-root
USER_ID=$(docker run --rm $IMAGE_NAME python3 -c "import os; print(os.getuid())")
if [ "$USER_ID" = "65532" ]; then
    echo "✅ Image runs as non-root user (UID 65532)"
else
    echo "❌ Image does not run as non-root user (UID: $USER_ID)"
    exit 1
fi

# Check if application starts
if docker run --rm -d --name test-container -p 8090:8090 $IMAGE_NAME; then
    echo "✅ Application starts successfully"
    sleep 5
    
    # Check health endpoint
    if curl -f http://localhost:8090/health >/dev/null 2>&1; then
        echo "✅ Health endpoint responds"
    else
        echo "❌ Health endpoint not responding"
    fi
    
    docker stop test-container >/dev/null
else
    echo "❌ Application failed to start"
    exit 1
fi

echo "✅ All validation checks passed"
```

---

## References

- [Distroless Images](https://github.com/GoogleContainerTools/distroless) - Official distroless documentation
- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/) - Multi-stage build guide
- [SPEC-1B-v2-DISTROLESS.md](../../../docs/build-docs/Build_guide_docs/SPEC-1B-v2-DISTROLESS.md) - Architecture requirements
- [07_SECURITY_COMPLIANCE.md](07_SECURITY_COMPLIANCE.md) - Security implementation details

---

**Document Status**: [IN PROGRESS]  
**Last Review**: 2025-10-12  
**Next Review**: 2025-11-12
