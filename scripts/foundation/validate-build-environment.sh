#!/bin/bash
# scripts/foundation/validate-build-environment.sh
# Validate Windows 11 build host and Raspberry Pi target

set -e

echo "Starting build environment validation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to check command availability
check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

echo "=== Windows 11 Build Host Validation ==="

# Check Docker Desktop
echo "Checking Docker Desktop..."
if check_command docker; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    echo "Docker version: $DOCKER_VERSION"
    print_status 0 "Docker Desktop is installed"
else
    print_status 1 "Docker Desktop is not installed"
    exit 1
fi

# Check Docker Compose v2
echo "Checking Docker Compose v2..."
if check_command docker; then
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version | cut -d' ' -f4)
        echo "Docker Compose version: $COMPOSE_VERSION"
        print_status 0 "Docker Compose v2 is available"
    else
        print_status 1 "Docker Compose v2 is not available"
        exit 1
    fi
else
    print_status 1 "Docker Compose v2 is not available"
    exit 1
fi

# Check Docker BuildKit
echo "Checking Docker BuildKit..."
if docker buildx version &> /dev/null; then
    print_status 0 "Docker BuildKit is available"
else
    print_status 1 "Docker BuildKit is not available"
    exit 1
fi

# Check Docker daemon
echo "Checking Docker daemon..."
if docker info &> /dev/null; then
    print_status 0 "Docker daemon is running"
else
    print_status 1 "Docker daemon is not running"
    exit 1
fi

# Check disk space
echo "Checking disk space..."
DISK_SPACE=$(docker system df --format "table {{.Size}}" | tail -n +2 | head -1)
echo "Available disk space: $DISK_SPACE"
if docker system df | grep -q "GB"; then
    print_status 0 "Sufficient disk space available"
else
    print_status 1 "Insufficient disk space"
    exit 1
fi

echo ""
echo "=== Raspberry Pi Target Validation ==="

# Check SSH connection
echo "Checking SSH connection to Pi..."
if ssh -o ConnectTimeout=10 -o BatchMode=yes pickme@192.168.0.75 "echo 'SSH connection successful'" &> /dev/null; then
    print_status 0 "SSH connection to Pi successful"
else
    print_status 1 "SSH connection to Pi failed"
    echo "Please ensure:"
    echo "1. Pi is powered on and accessible at 192.168.0.75"
    echo "2. SSH is enabled on Pi"
    echo "3. SSH key authentication is configured"
    exit 1
fi

# Check Pi architecture
echo "Checking Pi architecture..."
PI_ARCH=$(ssh pickme@192.168.0.75 "uname -m")
echo "Pi architecture: $PI_ARCH"
if [ "$PI_ARCH" = "aarch64" ]; then
    print_status 0 "Pi architecture is aarch64 (arm64)"
else
    print_status 1 "Pi architecture is not aarch64"
    exit 1
fi

# Check Pi disk space
echo "Checking Pi disk space..."
PI_DISK_SPACE=$(ssh pickme@192.168.0.75 "df -h / | tail -1 | awk '{print \$4}'")
echo "Pi available disk space: $PI_DISK_SPACE"
if ssh pickme@192.168.0.75 "df -h / | tail -1 | awk '{print \$4}' | grep -q 'G'"; then
    print_status 0 "Pi has sufficient disk space"
else
    print_status 1 "Pi has insufficient disk space"
    exit 1
fi

# Check Docker on Pi
echo "Checking Docker on Pi..."
if ssh pickme@192.168.0.75 "docker --version" &> /dev/null; then
    PI_DOCKER_VERSION=$(ssh pickme@192.168.0.75 "docker --version" | cut -d' ' -f3 | cut -d',' -f1)
    echo "Pi Docker version: $PI_DOCKER_VERSION"
    print_status 0 "Docker is installed on Pi"
else
    print_status 1 "Docker is not installed on Pi"
    exit 1
fi

# Check Docker daemon on Pi
echo "Checking Docker daemon on Pi..."
if ssh pickme@192.168.0.75 "docker info" &> /dev/null; then
    print_status 0 "Docker daemon is running on Pi"
else
    print_status 1 "Docker daemon is not running on Pi"
    exit 1
fi

# Check Docker Compose on Pi
echo "Checking Docker Compose on Pi..."
if ssh pickme@192.168.0.75 "docker compose version" &> /dev/null; then
    PI_COMPOSE_VERSION=$(ssh pickme@192.168.0.75 "docker compose version" | cut -d' ' -f4)
    echo "Pi Docker Compose version: $PI_COMPOSE_VERSION"
    print_status 0 "Docker Compose is available on Pi"
else
    print_status 1 "Docker Compose is not available on Pi"
    exit 1
fi

echo ""
echo "=== Network Connectivity Check ==="

# Check network connectivity to Pi
echo "Checking network connectivity to Pi..."
if ping -c 4 192.168.0.75 &> /dev/null; then
    print_status 0 "Network connectivity to Pi is working"
else
    print_status 1 "Network connectivity to Pi failed"
    exit 1
fi

# Check internet connectivity
echo "Checking internet connectivity..."
if curl -I https://github.com &> /dev/null; then
    print_status 0 "Internet connectivity is working"
else
    print_status 1 "Internet connectivity failed"
    exit 1
fi

# Check Docker Hub connectivity
echo "Checking Docker Hub connectivity..."
if docker pull hello-world &> /dev/null; then
    print_status 0 "Docker Hub connectivity is working"
    docker rmi hello-world &> /dev/null
else
    print_status 1 "Docker Hub connectivity failed"
    exit 1
fi

echo ""
echo "=== Base Images Check ==="

# Check distroless base images
echo "Checking distroless base images..."
if docker pull gcr.io/distroless/python3-debian12:latest &> /dev/null; then
    print_status 0 "Python distroless base image available"
else
    print_status 1 "Python distroless base image not available"
    exit 1
fi

if docker pull gcr.io/distroless/base-debian12:latest &> /dev/null; then
    print_status 0 "Base distroless image available"
else
    print_status 1 "Base distroless image not available"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ All build environment validation checks passed!${NC}"
echo "Build environment is ready for container builds."