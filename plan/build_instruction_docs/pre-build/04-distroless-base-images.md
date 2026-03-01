# Distroless Base Image Preparation

## Overview
Build foundation distroless base images for all service types to ensure consistent, secure, and minimal runtime environments. These images support multi-platform builds (AMD64 and ARM64) and are optimized for production deployment.

## Location
`infrastructure/containers/base/`

## Base Images to Build

### 1. Python Distroless Base
**File**: `infrastructure/containers/base/Dockerfile.python-base`

```dockerfile
# Lucid Python Base Distroless Image
# Ultra-minimal distroless base image for Lucid services
# Optimized for size and security

# syntax=docker/dockerfile:1.7
FROM python:3.11-slim-bookworm AS python-builder

# Set build environment
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install only the most essential Python packages
RUN pip install --no-cache-dir \
    requests \
    cryptography \
    fastapi \
    uvicorn \
    pydantic \
    motor \
    redis \
    psutil \
    python-dotenv \
    pyyaml \
    structlog \
    bcrypt \
    python-jose[cryptography] \
    passlib[bcrypt] \
    dnspython \
    python-multipart \
    python-dateutil \
    orjson

# Stage 2: Distroless runtime
FROM gcr.io/distroless/python3-debian12:latest

# Metadata for runtime container
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="Python base distroless runtime for Lucid services" \
      org.lucid.plane="infrastructure" \
      org.lucid.service="python-base" \
      org.lucid.stage="runtime"

# Set runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Copy Python packages from builder
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy essential system libraries
COPY --from=python-builder /lib/*-linux-*/libc.so.6 /lib/
COPY --from=python-builder /lib/*-linux-*/libssl.so.3 /lib/
COPY --from=python-builder /lib/*-linux-*/libcrypto.so.3 /lib/
COPY --from=python-builder /lib/*-linux-*/libz.so.1 /lib/
COPY --from=python-builder /lib/*-linux-*/libffi.so.8 /lib/
COPY --from=python-builder /lib*/ld-linux-*.so.2 /lib64/

# Copy CA certificates
COPY --from=python-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Create application directory
WORKDIR /app

# Set user to nonroot for security
USER nonroot:nonroot

# Expose common ports for Lucid services
EXPOSE 8000 8080 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import sys; sys.exit(0)"]

# Default command
CMD ["python", "-c", "print('Lucid Python Base Distroless Container Ready')"]
```

**Requirements File**: `infrastructure/containers/base/requirements.txt`
```txt
# Lucid Python Base Requirements for Distroless Images
# Core dependencies for all Lucid services
# Optimized for minimal attack surface and security

# Core Python packages
cryptography>=41.0.0
pynacl>=1.5.0
requests>=2.31.0
aiohttp>=3.8.0
fastapi>=0.103.0
uvicorn>=0.23.0
pydantic>=2.0.0

# Database packages
motor>=3.2.0
pymongo>=4.5.0
redis>=4.6.0

# Task processing
celery>=5.3.0

# System monitoring
psutil>=5.9.0

# File watching
watchdog>=3.0.0

# Configuration management
python-dotenv>=1.0.0
pyyaml>=5.4.1

# Logging and monitoring
structlog>=23.0.0
prometheus-client>=0.17.0

# Security
bcrypt>=4.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# Network utilities
dnspython>=2.4.0
python-multipart>=0.0.6

# Time utilities
python-dateutil>=2.8.0
pytz>=2023.3

# JSON handling
orjson>=3.9.0

# Compression
zstandard>=0.21.0

# Infrastructure specific packages (simplified)
docker>=6.1.0

# Monitoring and observability
grafana-api>=1.0.3
prometheus-api-client>=0.5.3
```

### 2. Java Distroless Base
**File**: `infrastructure/containers/base/Dockerfile.java-base`

```dockerfile
# Lucid Java Base Distroless Image
# Multi-stage build optimized for production deployment
# Supports ARM64 (Raspberry Pi) and AMD64 architectures
# LUCID-STRICT Mode: Enhanced security with minimal attack surface

# syntax=docker/dockerfile:1.7
FROM openjdk:17-jdk-slim-bookworm AS java-builder

# Build arguments for multi-platform support
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH

# Metadata for professional container management
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="Java base distroless image for Lucid services" \
      org.lucid.plane="infrastructure" \
      org.lucid.service="java-base" \
      org.lucid.stage="base"

# Set build environment
ENV DEBIAN_FRONTEND=noninteractive \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    MAVEN_HOME=/usr/share/maven \
    GRADLE_HOME=/usr/share/gradle \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    git \
    curl \
    ca-certificates \
    maven \
    gradle \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application directory
WORKDIR /app

# Copy Maven/Gradle files for dependency resolution
COPY ./pom.xml /app/
COPY ./build.gradle /app/
COPY ./gradle.properties /app/

# Download dependencies (if Maven/Gradle files exist)
RUN if [ -f pom.xml ]; then mvn dependency:go-offline -B; fi
RUN if [ -f build.gradle ]; then gradle dependencies --no-daemon; fi

# Stage 2: Distroless runtime
FROM gcr.io/distroless/java17-debian12:latest

# Metadata for runtime container
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="Java base distroless runtime for Lucid services" \
      org.lucid.plane="infrastructure" \
      org.lucid.service="java-base" \
      org.lucid.stage="runtime"

# Set runtime environment
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Copy essential system libraries (architecture-specific)
COPY --from=java-builder /lib/*-linux-*/libc.so.6 /lib/
COPY --from=java-builder /lib/*-linux-*/libssl.so.3 /lib/
COPY --from=java-builder /lib/*-linux-*/libcrypto.so.3 /lib/
COPY --from=java-builder /lib/*-linux-*/libz.so.1 /lib/
COPY --from=java-builder /lib/*-linux-*/liblzma.so.5 /lib/
COPY --from=java-builder /lib/*-linux-*/libzstd.so.1 /lib/
COPY --from=java-builder /lib/*-linux-*/libffi.so.8 /lib/
COPY --from=java-builder /lib*/ld-linux-*.so.2 /lib64/

# Copy CA certificates
COPY --from=java-builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Create application directory
WORKDIR /app

# Set user to nonroot for security
USER nonroot:nonroot

# Expose common ports for Lucid Java services
EXPOSE 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["java", "-version"]

# Default command
CMD ["java", "-version"]
```

## Build Commands

### Python Distroless Base
```bash
# Build Python distroless base image (Multi-platform)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/hamigames/lucid/python-base:latest \
  -t ghcr.io/hamigames/lucid/python-base:$(git rev-parse --short HEAD) \
  -t lucid-python-base:latest \
  -f infrastructure/containers/base/Dockerfile.python-base \
  --push \
  .
```

### Java Distroless Base
```bash
# Build Java distroless base image (Multi-platform)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/hamigames/lucid/java-base:latest \
  -t ghcr.io/hamigames/lucid/java-base:$(git rev-parse --short HEAD) \
  -t lucid-java-base:latest \
  -f infrastructure/containers/base/Dockerfile.java-base \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/foundation/build-distroless-base-images.sh`

The foundation build script provides automated building of distroless base images with multi-platform support and comprehensive error handling.

**Key Features:**
- Multi-platform builds (AMD64 and ARM64)
- GitHub Container Registry integration
- Comprehensive error handling and validation
- Image size optimization and verification
- Health check testing
- Build cache optimization

**Usage:**
```bash
# Run the foundation build script
./scripts/foundation/build-distroless-base-images.sh
```

**Alternative Build Script:**
**File**: `infrastructure/containers/base/build-base-images.sh`

This script is already implemented and provides the same functionality with enhanced features:

```bash
#!/bin/bash
# Lucid Base Images Build Script
# Builds distroless base images for Python and Java services
# Supports multi-platform builds for ARM64 (Pi) and AMD64

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="ghcr.io/hamigames/lucid"
PYTHON_IMAGE="python-base"
JAVA_IMAGE="java-base"
VERSION="latest"
PLATFORMS="linux/amd64,linux/arm64"

# Build arguments
BUILD_ARGS="--build-arg BUILDKIT_INLINE_CACHE=1 --build-arg BUILDKIT_PROGRESS=plain"

echo -e "${BLUE}🚀 Building Lucid Base Distroless Images${NC}"
echo -e "${BLUE}======================================${NC}"

# Check if Docker Buildx is available
if ! docker buildx version >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker Buildx not found. Please install Docker Buildx.${NC}"
    exit 1
fi

# Create buildx builder if it doesn't exist
if ! docker buildx ls | grep -q "lucid-builder"; then
    echo -e "${YELLOW}📦 Creating Docker Buildx builder...${NC}"
    docker buildx create --name lucid-builder --use --driver docker-container --driver-opt network=host
fi

# Set the builder
docker buildx use lucid-builder

echo -e "${YELLOW}🔧 Building Python Base Image...${NC}"
docker buildx build \
    --platform $PLATFORMS \
    --file Dockerfile.python-base \
    --tag $REGISTRY/$PYTHON_IMAGE:$VERSION \
    --tag $REGISTRY/$PYTHON_IMAGE:$(git rev-parse --short HEAD) \
    --tag lucid-python-base:latest \
    $BUILD_ARGS \
    --push \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python base image built successfully${NC}"
else
    echo -e "${RED}❌ Python base image build failed${NC}"
    exit 1
fi

echo -e "${YELLOW}🔧 Building Java Base Image...${NC}"
docker buildx build \
    --platform $PLATFORMS \
    --file Dockerfile.java-base \
    --tag $REGISTRY/$JAVA_IMAGE:$VERSION \
    --tag $REGISTRY/$JAVA_IMAGE:$(git rev-parse --short HEAD) \
    --tag lucid-java-base:latest \
    $BUILD_ARGS \
    --push \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Java base image built successfully${NC}"
else
    echo -e "${RED}❌ Java base image build failed${NC}"
    exit 1
fi

# Verify image sizes
echo -e "${YELLOW}📊 Verifying image sizes...${NC}"

PYTHON_SIZE=$(docker images lucid-python-base:latest --format "table {{.Size}}" | tail -n 1)
JAVA_SIZE=$(docker images lucid-java-base:latest --format "table {{.Size}}" | tail -n 1)

echo -e "${BLUE}Python Base Image Size: $PYTHON_SIZE${NC}"
echo -e "${BLUE}Java Base Image Size: $JAVA_SIZE${NC}"

# Test Python base image
echo -e "${YELLOW}🧪 Testing Python base image...${NC}"
docker run --rm lucid-python-base:latest python -c "print('Python base image test successful')"

# Test Java base image
echo -e "${YELLOW}🧪 Testing Java base image...${NC}"
docker run --rm lucid-java-base:latest java -version

echo -e "${GREEN}🎉 All base images built and tested successfully!${NC}"
echo -e "${BLUE}📋 Build Summary:${NC}"
echo -e "  • Python Base: $REGISTRY/$PYTHON_IMAGE:$VERSION"
echo -e "  • Java Base: $REGISTRY/$JAVA_IMAGE:$VERSION"
echo -e "  • Platforms: $PLATFORMS"
echo -e "  • Registry: $REGISTRY"
```

## Validation Criteria
- Base images pushed to GitHub Container Registry successfully
- Images are available for dependent builds
- Python base image includes all required dependencies
- Java base image is ready for future Java services
- All images use distroless runtime
- Images are optimized for multi-platform (AMD64 and ARM64)
- Images pass health checks and basic functionality tests
- Image sizes are optimized (Python: ~150MB, Java: ~200MB)
- Security scanning passes (non-root user, minimal attack surface)

## Security Features

### Distroless Benefits
- **Minimal Attack Surface**: No shell, package manager, or unnecessary binaries
- **Non-root User**: All containers run as non-root user (65532:65532)
- **No Package Manager**: Cannot install additional packages at runtime
- **Immutable**: Runtime environment cannot be modified
- **Minimal Dependencies**: Only required runtime libraries included

### Security Hardening
```dockerfile
# Set non-root user
USER nonroot:nonroot

# Remove unnecessary files and optimize
RUN find /app/deps -name "*.pyc" -delete && \
    find /app/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /app/deps -name "*.dist-info" -type d -exec rm -rf {} +

# Copy only essential system libraries
COPY --from=builder /lib/*-linux-*/libc.so.6 /lib/
COPY --from=builder /lib/*-linux-*/libssl.so.3 /lib/
COPY --from=builder /lib/*-linux-*/libcrypto.so.3 /lib/
```

## Performance Optimizations

### Multi-stage Build Benefits
- **Smaller Final Image**: Only runtime dependencies in final image
- **Faster Builds**: Build dependencies not included in final image
- **Layer Caching**: Build stages can be cached independently
- **Security**: Build tools not available in production image

### Image Size Optimization
```bash
# Check image sizes
docker images ghcr.io/hamigames/lucid

# Expected sizes:
# python-base:latest: ~150MB
# java-base:latest: ~200MB

# Check local images
docker images lucid-python-base lucid-java-base
```

## Troubleshooting

### Build Failures
```bash
# Check build logs with detailed output
docker buildx build --progress=plain \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/hamigames/lucid/python-base:latest \
  -f infrastructure/containers/base/Dockerfile.python-base \
  .

# Check buildx builder status
docker buildx ls
docker buildx inspect lucid-builder
```

### Push Failures
```bash
# Check GitHub Container Registry authentication
docker login ghcr.io --username hamigames

# Check network connectivity
docker pull hello-world

# Verify registry access
docker pull ghcr.io/hamigames/lucid/python-base:latest
```

### Platform Issues
```bash
# Check buildx platform support
docker buildx ls

# Create new builder if needed
docker buildx create --name lucid-builder --use
```

## Dependencies

### Required Tools
- Docker BuildKit enabled
- Docker buildx plugin
- GitHub Container Registry authentication
- Network connectivity to GitHub Container Registry
- Git repository access for version tagging

### Base Image Requirements
- `gcr.io/distroless/python3-debian12:latest`
- `gcr.io/distroless/java17-debian12:latest`
- `gcr.io/distroless/base-debian12:latest`

## Next Steps
After successful base image builds, proceed to Phase 1 foundation services build.
