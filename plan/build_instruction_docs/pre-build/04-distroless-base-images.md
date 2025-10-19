# Distroless Base Image Preparation

## Overview
Build foundation distroless base images for all service types to ensure consistent, secure, and minimal runtime environments.

## Location
`infrastructure/containers/base/`

## Base Images to Build

### 1. Python Distroless Base
**File**: `infrastructure/containers/base/Dockerfile.python-base`

```dockerfile
# Multi-stage build for Python distroless base
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt

# Remove unnecessary files
RUN find /app/deps -name "*.pyc" -delete && \
    find /app/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /app/deps -name "*.dist-info" -type d -exec rm -rf {} +

# Final distroless stage
FROM gcr.io/distroless/python3-debian12:arm64

# Copy Python dependencies
COPY --from=builder /app/deps /app/deps

# Set Python path
ENV PYTHONPATH=/app/deps

# Set working directory
WORKDIR /app

# Set non-root user
USER 65532:65532

# Default command
CMD ["python", "main.py"]
```

**Requirements File**: `infrastructure/containers/base/requirements.txt`
```txt
# Core Python dependencies for Lucid services
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.8
pymongo==4.6.0
redis==5.0.1
elasticsearch==8.11.0
pytest==7.4.3
pytest-asyncio==0.21.1
```

### 2. Java Distroless Base (Future Use)
**File**: `infrastructure/containers/base/Dockerfile.java-base`

```dockerfile
# Multi-stage build for Java distroless base
FROM openjdk:17-jdk-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    maven \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy Maven files
COPY pom.xml .
COPY src ./src

# Build application
RUN mvn clean package -DskipTests

# Final distroless stage
FROM gcr.io/distroless/java17-debian12:arm64

# Copy JAR file
COPY --from=builder /app/target/*.jar /app/app.jar

# Set working directory
WORKDIR /app

# Set non-root user
USER 65532:65532

# Default command
CMD ["java", "-jar", "app.jar"]
```

## Build Commands

### Python Distroless Base
```bash
# Build Python distroless base image
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:python-distroless-arm64 \
  -f infrastructure/containers/base/Dockerfile.python-base \
  --push \
  .
```

### Java Distroless Base
```bash
# Build Java distroless base image
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:java-distroless-arm64 \
  -f infrastructure/containers/base/Dockerfile.java-base \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/foundation/build-distroless-base-images.sh`

```bash
#!/bin/bash
# scripts/foundation/build-distroless-base-images.sh
# Build distroless base images for all service types

set -e

echo "Building distroless base images..."

# Create base images directory
mkdir -p infrastructure/containers/base

# Create Python requirements file
cat > infrastructure/containers/base/requirements.txt << 'EOF'
# Core Python dependencies for Lucid services
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.8
pymongo==4.6.0
redis==5.0.1
elasticsearch==8.11.0
pytest==7.4.3
pytest-asyncio==0.21.1
EOF

# Create Python distroless Dockerfile
cat > infrastructure/containers/base/Dockerfile.python-base << 'EOF'
# Multi-stage build for Python distroless base
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt

# Remove unnecessary files
RUN find /app/deps -name "*.pyc" -delete && \
    find /app/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /app/deps -name "*.dist-info" -type d -exec rm -rf {} +

# Final distroless stage
FROM gcr.io/distroless/python3-debian12:arm64

# Copy Python dependencies
COPY --from=builder /app/deps /app/deps

# Set Python path
ENV PYTHONPATH=/app/deps

# Set working directory
WORKDIR /app

# Set non-root user
USER 65532:65532

# Default command
CMD ["python", "main.py"]
EOF

# Create Java distroless Dockerfile
cat > infrastructure/containers/base/Dockerfile.java-base << 'EOF'
# Multi-stage build for Java distroless base
FROM openjdk:17-jdk-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    maven \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy Maven files
COPY pom.xml .
COPY src ./src

# Build application
RUN mvn clean package -DskipTests

# Final distroless stage
FROM gcr.io/distroless/java17-debian12:arm64

# Copy JAR file
COPY --from=builder /app/target/*.jar /app/app.jar

# Set working directory
WORKDIR /app

# Set non-root user
USER 65532:65532

# Default command
CMD ["java", "-jar", "app.jar"]
EOF

# Build Python distroless base image
echo "Building Python distroless base image..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:python-distroless-arm64 \
  -f infrastructure/containers/base/Dockerfile.python-base \
  --push \
  .

# Build Java distroless base image
echo "Building Java distroless base image..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:java-distroless-arm64 \
  -f infrastructure/containers/base/Dockerfile.java-base \
  --push \
  .

echo "Distroless base images built and pushed successfully!"
echo "Available base images:"
echo "- pickme/lucid-base:python-distroless-arm64"
echo "- pickme/lucid-base:java-distroless-arm64"
```

## Validation Criteria
- Base images pushed to Docker Hub successfully
- Images are available for dependent builds
- Python base image includes all required dependencies
- Java base image is ready for future Java services
- All images use distroless runtime
- Images are optimized for arm64 platform

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
USER 65532:65532

# Remove unnecessary files
RUN find /app/deps -name "*.pyc" -delete && \
    find /app/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /app/deps -name "*.dist-info" -type d -exec rm -rf {} +
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
docker images pickme/lucid-base

# Expected sizes:
# python-distroless-arm64: ~150MB
# java-distroless-arm64: ~200MB
```

## Troubleshooting

### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain \
  --platform linux/arm64 \
  -t pickme/lucid-base:python-distroless-arm64 \
  -f infrastructure/containers/base/Dockerfile.python-base \
  .
```

### Push Failures
```bash
# Check Docker Hub authentication
docker login --username pickme

# Check network connectivity
docker pull hello-world
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
- Docker Hub authentication
- Network connectivity to Docker Hub

### Base Image Requirements
- `gcr.io/distroless/python3-debian12:arm64`
- `gcr.io/distroless/java17-debian12:arm64`
- `gcr.io/distroless/base-debian12:arm64`

## Next Steps
After successful base image builds, proceed to Phase 1 foundation services build.
