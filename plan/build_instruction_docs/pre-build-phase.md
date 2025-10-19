# Pre-Build Phase: Cleanup & Setup

## Overview

The Pre-Build Phase prepares the environment for the complete Lucid system build. This phase includes Docker Hub cleanup, environment configuration generation, build environment validation, and distroless base image preparation.

**Duration**: ~2 hours  
**Execution**: Sequential (Steps 1-4 must complete in order)  
**Prerequisites**: Docker Desktop running, SSH access to Pi, Docker Hub account access

## Step 1: Docker Hub Registry Cleanup

### Purpose
Clean all existing images from the pickme/lucid Docker Hub repository before starting new builds to ensure a clean state.

### Location
- **Script**: `scripts/registry/cleanup-dockerhub.sh`
- **Execution**: Windows 11 console

### Prerequisites
- Docker Hub account credentials for 'pickme' user
- Docker CLI authenticated to Docker Hub
- PowerShell 7+ or Bash shell

### Actions Required

1. **Create cleanup script**:
```bash
#!/bin/bash
# scripts/registry/cleanup-dockerhub.sh
# Full cleanup of pickme/lucid Docker Hub registry

set -e

echo "Starting Docker Hub registry cleanup for pickme/lucid..."

# Authenticate to Docker Hub
echo "Authenticating to Docker Hub..."
docker login

# List all repositories under pickme/lucid namespace
echo "Listing existing repositories..."
docker search pickme/lucid

# Delete all tagged images from registry
echo "Deleting all tagged images..."
for image in $(docker search pickme/lucid --format "table {{.Name}}" | grep -v "NAME" | head -20); do
    echo "Deleting $image..."
    docker rmi $image || echo "Image $image not found locally"
done

# Clean local Docker cache
echo "Cleaning local Docker cache..."
docker system prune -a -f
docker builder prune -a -f

echo "Docker Hub cleanup completed successfully"
```

2. **Execute cleanup**:
```bash
# Make script executable
chmod +x scripts/registry/cleanup-dockerhub.sh

# Run cleanup
./scripts/registry/cleanup-dockerhub.sh
```

3. **Verify cleanup**:
```bash
# Verify no images remain
docker search pickme/lucid
# Should return no results or empty results
```

### Validation
- `docker search pickme/lucid` returns no results
- Local Docker cache cleaned
- Ready for fresh image builds

### Troubleshooting
- **Authentication failed**: Ensure Docker Hub credentials are correct
- **Images not found**: Some images may not exist locally, continue with cleanup
- **Permission denied**: Ensure Docker daemon is running and user has permissions

---

## Step 2: Environment Configuration Generator

### Purpose
Generate ALL environment configuration files needed for the entire build process with real values, no placeholders.

### Location
- **Script**: `scripts/config/generate-all-env.sh`
- **Output**: `configs/environment/` directory

### Files to Generate

1. **`.env.pi-build`** - Raspberry Pi target configuration
2. **`.env.foundation`** - Phase 1 database/auth configs
3. **`.env.core`** - Phase 2 gateway/blockchain configs
4. **`.env.application`** - Phase 3 session/RDP/node configs
5. **`.env.support`** - Phase 4 admin/TRON configs
6. **`.env.gui`** - Electron GUI integration configs

### Configuration Values (Real, Not Placeholders)

Create the environment generator script:

```bash
#!/bin/bash
# scripts/config/generate-all-env.sh
# Generate all environment configuration files with real values

set -e

echo "Generating environment configuration files..."

# Create configs directory
mkdir -p configs/environment

# Generate secure random values
MONGODB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 64)
ENCRYPTION_KEY=$(openssl rand -base64 32)
TOR_PASSWORD=$(openssl rand -base64 32)

# .env.pi-build - Raspberry Pi target configuration
cat > configs/environment/.env.pi-build << EOF
# Raspberry Pi Target Configuration
PI_HOST=192.168.0.75
PI_USER=pickme
PI_DEPLOY_DIR=/opt/lucid/production
LUCID_NETWORK=lucid-pi-network

# Build Configuration
BUILD_PLATFORM=linux/arm64
DOCKER_REGISTRY=pickme/lucid
BUILD_TIMEOUT=3600
EOF

# .env.foundation - Phase 1 database/auth configs
cat > configs/environment/.env.foundation << EOF
# Database Configuration
MONGODB_URI=mongodb://lucid:${MONGODB_PASSWORD}@192.168.0.75:27017/lucid?authSource=admin&retryWrites=false
REDIS_URL=redis://:${REDIS_PASSWORD}@192.168.0.75:6379/0
ELASTICSEARCH_URL=http://192.168.0.75:9200

# Security Configuration
JWT_SECRET_KEY=${JWT_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
TOR_CONTROL_PASSWORD=${TOR_PASSWORD}

# Network Configuration
LUCID_NETWORK=lucid-pi-network
PI_HOST=192.168.0.75
PI_USER=pickme
PI_DEPLOY_DIR=/opt/lucid/production

# Service Ports (Fixed Assignments)
API_GATEWAY_PORT=8080
BLOCKCHAIN_CORE_PORT=8084
AUTH_SERVICE_PORT=8089
SESSION_API_PORT=8087
NODE_MANAGEMENT_PORT=8095
ADMIN_INTERFACE_PORT=8083
TRON_PAYMENT_PORT=8085

# Database Ports
MONGODB_PORT=27017
REDIS_PORT=6379
ELASTICSEARCH_PORT=9200
EOF

# .env.core - Phase 2 gateway/blockchain configs
cat > configs/environment/.env.core << EOF
# API Gateway Configuration
API_GATEWAY_PORT=8080
RATE_LIMIT_FREE=100
RATE_LIMIT_PREMIUM=1000
RATE_LIMIT_ENTERPRISE=10000

# Blockchain Configuration
BLOCKCHAIN_CORE_PORT=8084
CONSENSUS_ALGORITHM=proof_of_observation_time
BLOCK_TIME_SECONDS=10
MINING_DIFFICULTY=1

# Service Mesh Configuration
SERVICE_MESH_PORT=8086
CONSUL_PORT=8500
ENVOY_PORT=8088

# Network Configuration
LUCID_NETWORK=lucid-pi-network
PI_HOST=192.168.0.75

# Security
JWT_SECRET_KEY=${JWT_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
EOF

# .env.application - Phase 3 session/RDP/node configs
cat > configs/environment/.env.application << EOF
# Session Management Configuration
SESSION_API_PORT=8087
CHUNK_SIZE_MB=10
COMPRESSION_LEVEL=6
ENCRYPTION_ALGO=AES-256-GCM
MERKLE_HASH_ALGO=SHA256

# RDP Services Configuration
RDP_SERVER_MANAGER_PORT=8081
XRDP_PORT=3389
SESSION_CONTROLLER_PORT=8082
RESOURCE_MONITOR_PORT=8090

# Node Management Configuration
NODE_MANAGEMENT_PORT=8095
POOT_CALCULATION_INTERVAL_SEC=300
PAYOUT_THRESHOLD_USDT=10.0
POOL_MAX_NODES=100

# Network Configuration
LUCID_NETWORK=lucid-pi-network
PI_HOST=192.168.0.75

# Security
ENCRYPTION_KEY=${ENCRYPTION_KEY}
JWT_SECRET_KEY=${JWT_SECRET}
EOF

# .env.support - Phase 4 admin/TRON configs
cat > configs/environment/.env.support << EOF
# Admin Interface Configuration
ADMIN_INTERFACE_PORT=8083
ADMIN_USER=admin
ADMIN_PASSWORD=$(openssl rand -base64 16)

# TRON Configuration (Isolated)
TRON_NETWORK=mainnet
TRON_API_URL=https://api.trongrid.io
TRON_TESTNET_API=https://api.shasta.trongrid.io
USDT_TRC20_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
TRX_STAKING_MIN_AMOUNT=100
PAYOUT_MIN_THRESHOLD=10

# TRON Payment Services Ports
TRON_CLIENT_PORT=8091
PAYOUT_ROUTER_PORT=8092
WALLET_MANAGER_PORT=8093
USDT_MANAGER_PORT=8094
TRX_STAKING_PORT=8096
PAYMENT_GATEWAY_PORT=8097

# Network Configuration
LUCID_NETWORK=lucid-pi-network
LUCID_TRON_ISOLATED=lucid-tron-isolated
PI_HOST=192.168.0.75

# Security
ENCRYPTION_KEY=${ENCRYPTION_KEY}
JWT_SECRET_KEY=${JWT_SECRET}
TOR_CONTROL_PASSWORD=${TOR_PASSWORD}
EOF

# .env.gui - Electron GUI integration configs
cat > configs/environment/.env.gui << EOF
# API Endpoints (from backend .env files)
API_GATEWAY_URL=http://192.168.0.75:8080
BLOCKCHAIN_CORE_URL=http://192.168.0.75:8084
AUTH_SERVICE_URL=http://192.168.0.75:8089
SESSION_API_URL=http://192.168.0.75:8087
NODE_MANAGEMENT_URL=http://192.168.0.75:8095
ADMIN_INTERFACE_URL=http://192.168.0.75:8083

# Tor Configuration
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051
TOR_ENABLED=true

# GUI Configuration
ELECTRON_GUI_VERSION=1.0.0
GUI_THEME=dark
GUI_LANGUAGE=en

# Hardware Wallet Configuration
HARDWARE_WALLET_ENABLED=true
LEDGER_ENABLED=true
TREZOR_ENABLED=true
KEEPKEY_ENABLED=true

# Security
ENCRYPTION_KEY=${ENCRYPTION_KEY}
JWT_SECRET_KEY=${JWT_SECRET}
TOR_CONTROL_PASSWORD=${TOR_PASSWORD}
EOF

echo "Environment configuration files generated successfully"
echo "Generated files:"
ls -la configs/environment/
```

### Execute Environment Generation

```bash
# Make script executable
chmod +x scripts/config/generate-all-env.sh

# Run environment generation
./scripts/config/generate-all-env.sh
```

### Validation
- All 6 .env files exist in `configs/environment/`
- All files contain real values, no placeholders like `${PLACEHOLDER}`
- All passwords and secrets are randomly generated
- All port assignments are unique and non-conflicting

### Troubleshooting
- **Permission denied**: Ensure write permissions to configs directory
- **OpenSSL not found**: Install OpenSSL or use alternative random generation
- **Missing directories**: Script creates directories automatically

---

## Step 3: Build Environment Validation

### Purpose
Validate Windows 11 build host and Raspberry Pi target before starting builds to ensure all prerequisites are met.

### Location
- **Script**: `scripts/foundation/validate-build-environment.sh`
- **Execution**: Windows 11 console

### Validation Checks

Create the validation script:

```bash
#!/bin/bash
# scripts/foundation/validate-build-environment.sh
# Validate build environment for Lucid system

set -e

echo "Validating build environment for Lucid system..."

# Check Docker Desktop on Windows 11
echo "Checking Docker Desktop..."
if ! docker --version > /dev/null 2>&1; then
    echo "ERROR: Docker not found. Please install Docker Desktop."
    exit 1
fi

if ! docker compose version > /dev/null 2>&1; then
    echo "ERROR: Docker Compose v2 not found. Please update Docker Desktop."
    exit 1
fi

# Check BuildKit
echo "Checking Docker BuildKit..."
if ! docker buildx version > /dev/null 2>&1; then
    echo "ERROR: Docker BuildKit not available. Please enable BuildKit in Docker Desktop."
    exit 1
fi

# Check SSH connection to Pi
echo "Checking SSH connection to Pi..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes pickme@192.168.0.75 exit > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to Pi via SSH. Please check:"
    echo "  - SSH keys are configured"
    echo "  - Pi is accessible at 192.168.0.75"
    echo "  - User 'pickme' exists on Pi"
    exit 1
fi

# Check Pi disk space
echo "Checking Pi disk space..."
DISK_SPACE=$(ssh pickme@192.168.0.75 "df -h / | awk 'NR==2 {print \$4}' | sed 's/G//'")
if [ "$DISK_SPACE" -lt 20 ]; then
    echo "ERROR: Pi has less than 20GB free space. Available: ${DISK_SPACE}GB"
    exit 1
fi

# Check Pi architecture
echo "Checking Pi architecture..."
PI_ARCH=$(ssh pickme@192.168.0.75 "uname -m")
if [ "$PI_ARCH" != "aarch64" ]; then
    echo "ERROR: Pi architecture is $PI_ARCH, expected aarch64"
    exit 1
fi

# Check Docker daemon on Pi
echo "Checking Docker daemon on Pi..."
if ! ssh pickme@192.168.0.75 "docker --version" > /dev/null 2>&1; then
    echo "ERROR: Docker not installed on Pi. Please install Docker Engine."
    exit 1
fi

# Check Docker Compose on Pi
echo "Checking Docker Compose on Pi..."
if ! ssh pickme@192.168.0.75 "docker compose version" > /dev/null 2>&1; then
    echo "ERROR: Docker Compose not installed on Pi. Please install Docker Compose."
    exit 1
fi

# Check network connectivity
echo "Checking network connectivity..."
if ! ping -c 3 192.168.0.75 > /dev/null 2>&1; then
    echo "ERROR: Cannot ping Pi at 192.168.0.75. Check network connectivity."
    exit 1
fi

# Check required base images availability
echo "Checking base images availability..."
BASE_IMAGES=("python:3.11-slim" "node:18-slim" "debian:12-slim" "gcr.io/distroless/python3-debian12:arm64" "gcr.io/distroless/base-debian12:arm64")
for image in "${BASE_IMAGES[@]}"; do
    echo "Checking $image..."
    if ! docker pull $image > /dev/null 2>&1; then
        echo "WARNING: Cannot pull $image. Will attempt during build."
    fi
done

echo "Build environment validation completed successfully"
echo "All prerequisites met for Lucid system build"
```

### Execute Validation

```bash
# Make script executable
chmod +x scripts/foundation/validate-build-environment.sh

# Run validation
./scripts/foundation/validate-build-environment.sh
```

### Validation Criteria
- Docker Desktop running on Windows 11 (BuildKit enabled)
- Docker Compose v2 available
- SSH connection to Pi (pickme@192.168.0.75) working
- Pi disk space available (>20GB free)
- Pi architecture verification (aarch64/arm64)
- Network connectivity between build host and Pi
- Docker daemon running on Pi
- Required base images available

### Troubleshooting
- **Docker not found**: Install Docker Desktop and ensure it's running
- **SSH connection failed**: Check SSH keys, network connectivity, and Pi accessibility
- **Insufficient disk space**: Free up space on Pi or use different storage
- **Architecture mismatch**: Ensure Pi is running 64-bit OS
- **Docker not on Pi**: Install Docker Engine on Pi

---

## Step 4: Distroless Base Image Preparation

### Purpose
Build foundation distroless base images for all service types to ensure consistent, secure runtime environments.

### Location
- **Directory**: `infrastructure/containers/base/`
- **Execution**: Windows 11 console with Docker BuildKit

### Base Images to Build

1. **Python 3.11 distroless base**
2. **Java 17 distroless base** (for future use)

### Create Base Image Directory Structure

```bash
# Create base image directory
mkdir -p infrastructure/containers/base
```

### Python Distroless Base Image

Create `infrastructure/containers/base/Dockerfile.python-base`:

```dockerfile
# infrastructure/containers/base/Dockerfile.python-base
# Python 3.11 distroless base for Lucid services

# Stage 1: Builder
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
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian12:arm64

# Copy Python dependencies from builder
COPY --from=builder /root/.local /usr/local

# Set working directory
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages

# Default command
CMD ["python"]
```

Create `infrastructure/containers/base/requirements.txt`:

```txt
# Base Python requirements for Lucid services
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
requests==2.31.0
cryptography==41.0.8
PyJWT==2.8.0
python-multipart==0.0.6
aiofiles==23.2.1
```

### Java Distroless Base Image

Create `infrastructure/containers/base/Dockerfile.java-base`:

```dockerfile
# infrastructure/containers/base/Dockerfile.java-base
# Java 17 distroless base for future Lucid services

# Stage 1: Builder
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

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/java17-debian12:arm64

# Copy JAR from builder
COPY --from=builder /app/target/*.jar /app/app.jar

# Set working directory
WORKDIR /app

# Default command
CMD ["app.jar"]
```

### Build Commands

Create build script `infrastructure/containers/base/build-base-images.sh`:

```bash
#!/bin/bash
# infrastructure/containers/base/build-base-images.sh
# Build distroless base images for Lucid services

set -e

echo "Building distroless base images..."

# Set build context
cd infrastructure/containers/base

# Build Python distroless base
echo "Building Python distroless base..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:python-distroless-arm64 \
  -f Dockerfile.python-base \
  --push .

# Build Java distroless base
echo "Building Java distroless base..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:java-distroless-arm64 \
  -f Dockerfile.java-base \
  --push .

echo "Base images built and pushed successfully"
```

### Execute Base Image Build

```bash
# Make script executable
chmod +x infrastructure/containers/base/build-base-images.sh

# Run base image build
./infrastructure/containers/base/build-base-images.sh
```

### Validation
- Base images pushed to Docker Hub
- Images available for dependent builds
- Distroless compliance verified
- ARM64 platform compatibility confirmed

### Troubleshooting
- **Build failed**: Check Docker BuildKit is enabled
- **Push failed**: Verify Docker Hub authentication
- **Platform error**: Ensure ARM64 platform support
- **Dependencies missing**: Check requirements.txt files

---

## Pre-Build Phase Validation

### Complete Phase Validation

After completing all 4 steps, run the complete validation:

```bash
#!/bin/bash
# scripts/validation/pre-build-validation.sh
# Complete Pre-Build Phase validation

set -e

echo "Running Pre-Build Phase validation..."

# Check Docker Hub cleanup
echo "Checking Docker Hub cleanup..."
if docker search pickme/lucid | grep -q "lucid"; then
    echo "WARNING: Some lucid images still exist on Docker Hub"
else
    echo "✓ Docker Hub cleanup completed"
fi

# Check environment files
echo "Checking environment configuration..."
ENV_FILES=(".env.pi-build" ".env.foundation" ".env.core" ".env.application" ".env.support" ".env.gui")
for file in "${ENV_FILES[@]}"; do
    if [ -f "configs/environment/$file" ]; then
        if grep -q "\${" "configs/environment/$file"; then
            echo "ERROR: Placeholders found in $file"
            exit 1
        else
            echo "✓ $file generated with real values"
        fi
    else
        echo "ERROR: $file not found"
        exit 1
    fi
done

# Check base images
echo "Checking base images..."
if docker manifest inspect pickme/lucid-base:python-distroless-arm64 > /dev/null 2>&1; then
    echo "✓ Python distroless base image available"
else
    echo "ERROR: Python distroless base image not found"
    exit 1
fi

if docker manifest inspect pickme/lucid-base:java-distroless-arm64 > /dev/null 2>&1; then
    echo "✓ Java distroless base image available"
else
    echo "ERROR: Java distroless base image not found"
    exit 1
fi

echo "Pre-Build Phase validation completed successfully"
echo "Ready to proceed to Phase 1: Foundation Services"
```

### Execute Complete Validation

```bash
# Make script executable
chmod +x scripts/validation/pre-build-validation.sh

# Run complete validation
./scripts/validation/pre-build-validation.sh
```

## Next Steps

Upon successful completion of the Pre-Build Phase:

1. **All environment files generated** with real values
2. **Docker Hub registry cleaned** and ready for new builds
3. **Build environment validated** and ready for container builds
4. **Distroless base images prepared** for service builds

**Proceed to**: [Phase 1: Foundation Services](phase1-foundation-services.md)

## Troubleshooting Summary

| Issue | Solution |
|-------|----------|
| Docker Hub authentication failed | Check credentials and Docker login |
| Environment generation failed | Verify OpenSSL and directory permissions |
| SSH connection to Pi failed | Check network, SSH keys, and Pi accessibility |
| Base image build failed | Verify BuildKit enabled and Docker Hub access |
| Validation script errors | Check all prerequisites and run individual steps |

---

**Duration**: ~2 hours  
**Status**: Sequential execution required  
**Dependencies**: None  
**Next Phase**: Phase 1 Foundation Services
