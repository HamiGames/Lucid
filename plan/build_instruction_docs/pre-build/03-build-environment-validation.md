# Build Environment Validation

## Overview
Validate Windows 11 build host and Raspberry Pi target before starting builds to ensure all prerequisites are met.

## Script Location
`scripts/foundation/validate-build-environment.sh`

## Prerequisites Check

### 1. Windows 11 Build Host Validation

#### Docker Desktop Check
```bash
# Check Docker Desktop is running
docker --version
# Expected: Docker version 24.0.0 or higher

# Check Docker Compose v2
docker compose version
# Expected: Docker Compose version v2.20.0 or higher

# Check Docker BuildKit is enabled
docker buildx version
# Expected: BuildKit version 0.12.0 or higher
```

#### Docker Configuration Check
```bash
# Check Docker daemon is running
docker info
# Expected: Server information displayed

# Check available disk space
docker system df
# Expected: Sufficient space for builds (>20GB recommended)
```

### 2. Raspberry Pi Target Validation

#### SSH Connection Check
```bash
# Test SSH connection to Pi
ssh -o ConnectTimeout=10 pickme@192.168.0.75 "echo 'SSH connection successful'"
# Expected: Connection successful message
```

#### Pi System Information
```bash
# Check Pi architecture
ssh pickme@192.168.0.75 "uname -m"
# Expected: aarch64

# Check available disk space
ssh pickme@192.168.0.75 "df -h"
# Expected: >20GB free space

# Check Pi OS version
ssh pickme@192.168.0.75 "cat /etc/os-release"
# Expected: Raspberry Pi OS or compatible Linux
```

#### Docker on Pi Check
```bash
# Check Docker is installed on Pi
ssh pickme@192.168.0.75 "docker --version"
# Expected: Docker version 24.0.0 or higher

# Check Docker daemon is running on Pi
ssh pickme@192.168.0.75 "docker info"
# Expected: Server information displayed

# Check Docker Compose on Pi
ssh pickme@192.168.0.75 "docker compose version"
# Expected: Docker Compose version v2.20.0 or higher
```

### 3. Network Connectivity Check

#### Build Host to Pi Connectivity
```bash
# Test network connectivity
ping -c 4 192.168.0.75
# Expected: 4 packets transmitted, 4 received

# Test specific port connectivity
telnet 192.168.0.75 22
# Expected: Connection successful
```

#### Internet Connectivity Check
```bash
# Test Docker Hub connectivity
docker pull hello-world
# Expected: Image pulled successfully

# Test GitHub connectivity (for source code)
curl -I https://github.com
# Expected: HTTP 200 response
```

### 4. Required Base Images Check

#### Check Base Images Availability
```bash
# Check if required base images are available
docker images | grep -E "(python|node|debian|ubuntu|alpine)"
# Expected: Base images available locally or pullable

# Test pulling distroless base images
docker pull gcr.io/distroless/python3-debian12:arm64
docker pull gcr.io/distroless/base-debian12:arm64
# Expected: Images pulled successfully
```

## Script Implementation

```bash
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
if docker pull gcr.io/distroless/python3-debian12:arm64 &> /dev/null; then
    print_status 0 "Python distroless base image available"
else
    print_status 1 "Python distroless base image not available"
    exit 1
fi

if docker pull gcr.io/distroless/base-debian12:arm64 &> /dev/null; then
    print_status 0 "Base distroless image available"
else
    print_status 1 "Base distroless image not available"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ All build environment validation checks passed!${NC}"
echo "Build environment is ready for container builds."
```

## Validation Criteria
- All checks pass with exit code 0
- Docker Desktop running with BuildKit enabled
- Docker Compose v2 available
- SSH connection to Pi working
- Pi has >20GB free disk space
- Pi architecture is aarch64/arm64
- Network connectivity between build host and Pi
- Docker daemon running on Pi
- Required base images available

## Troubleshooting

### Docker Desktop Issues
```bash
# Restart Docker Desktop
# Check Docker Desktop is running in system tray
# Verify Docker Desktop settings allow buildx
```

### SSH Connection Issues
```bash
# Test SSH connection manually
ssh pickme@192.168.0.75

# Check SSH key authentication
ssh-add -l

# Test with verbose output
ssh -v pickme@192.168.0.75
```

### Pi Docker Issues
```bash
# Check Docker service on Pi
ssh pickme@192.168.0.75 "sudo systemctl status docker"

# Start Docker service if needed
ssh pickme@192.168.0.75 "sudo systemctl start docker"
```

### Network Issues
```bash
# Check Pi IP address
ping 192.168.0.75

# Check firewall rules
# Ensure port 22 is open for SSH
```

## Security Considerations
- SSH keys should be properly configured
- Pi should be on a secure network
- Docker daemon should be configured securely
- No unnecessary ports should be exposed

## Next Steps
After successful validation, proceed to distroless base image preparation.
