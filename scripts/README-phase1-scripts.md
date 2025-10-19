# Phase 1 Foundation Services Scripts

This directory contains the build, deploy, and test scripts for Phase 1 Foundation Services of the Lucid RDP project as specified in the Docker Build Process Plan.

## Scripts Overview

### 1. `build-phase1-foundation.sh`
**Purpose**: Builds all Phase 1 Foundation Services containers for Raspberry Pi (linux/arm64)

**Components Built**:
- Base distroless images (Python & Java)
- Auth Service (`pickme/lucid-auth-service:latest-arm64`)
- Storage Database Service (`pickme/lucid-storage-database:latest-arm64`)
- MongoDB (`pickme/lucid-mongodb:latest-arm64`)
- Redis (`pickme/lucid-redis:latest-arm64`)
- Elasticsearch (`pickme/lucid-elasticsearch:latest-arm64`)

**Features**:
- Multi-stage distroless builds for security
- Docker BuildKit integration
- Automatic Docker Hub authentication
- Image verification
- ARM64 platform targeting

### 2. `deploy-phase1-pi.sh`
**Purpose**: Deploys Phase 1 services to Raspberry Pi via SSH

**Deployment Process**:
- SSH connectivity validation
- Docker network creation (`lucid-pi-network`)
- Environment configuration generation
- Docker Compose deployment
- Service health monitoring
- MongoDB replica set initialization
- Elasticsearch index creation

**Target Configuration**:
- Pi Host: `pickme@192.168.0.75:22`
- Deploy Path: `/opt/lucid/production`
- Network: `lucid-pi-network` (172.20.0.0/16)

### 3. `test-phase1-integration.sh`
**Purpose**: Comprehensive integration testing of Phase 1 services

**Test Coverage**:
- Infrastructure tests (SSH, Docker, networking)
- Database connectivity and performance
- Service endpoint validation
- Cross-service communication
- JWT token generation
- Session management
- Performance benchmarks
- Health checks

## Prerequisites

### Build Environment (Windows 11)
```bash
# Install Docker Desktop with BuildKit
docker --version
docker buildx version

# Login to Docker Hub as 'pickme'
docker login
```

### Target Environment (Raspberry Pi)
```bash
# Install Docker on Pi
sudo apt update
sudo apt install docker.io docker-compose
sudo usermod -aG docker pickme

# Verify Pi architecture
uname -m  # Should return 'aarch64'
```

### SSH Configuration
```bash
# Ensure SSH key authentication is set up
ssh-copy-id pickme@192.168.0.75

# Test SSH connectivity
ssh pickme@192.168.0.75 "echo 'SSH connection successful'"
```

## Usage Instructions

### Step 1: Build Phase 1 Services
```bash
# From project root
./scripts/build-phase1-foundation.sh
```

**Expected Output**:
- Base images before services
- All 5 service containers built and pushed to Docker Hub
- Image verification confirms ARM64 manifests exist

### Step 2: Deploy to Raspberry Pi
```bash
# From project root
./scripts/deploy-phase1-pi.sh
```

**Expected Output**:
- SSH connectivity established
- Docker network created
- Environment files generated and deployed
- All services started and healthy
- MongoDB replica set initialized
- Elasticsearch index created

### Step 3: Run Integration Tests
```bash
# From project root
./scripts/test-phase1-integration.sh
```

**Expected Output**:
- All infrastructure tests pass
- Database connectivity and performance verified
- Service endpoints responding correctly
- Cross-service communication working
- Test report generated in `tests/results/phase1/`

## Service Endpoints

After successful deployment, the following endpoints will be available:

| Service | Endpoint | Purpose |
|---------|----------|---------|
| MongoDB | `mongodb://lucid:****@192.168.0.75:27017/lucid` | Database operations |
| Redis | `redis://:****@192.168.0.75:6379` | Caching operations |
| Elasticsearch | `http://192.168.0.75:9200` | Search and indexing |
| Auth Service | `http://192.168.0.75:8089` | Authentication API |
| Storage Database | `http://192.168.0.75:8088` | Database management API |

## Configuration Files Generated

### Environment Configuration
- **File**: `configs/environment/.env.foundation`
- **Contains**: Secure passwords, JWT secrets, service ports, network config

### Docker Compose
- **File**: `configs/docker/docker-compose.foundation.yml`
- **Contains**: Service definitions, health checks, volume mounts, network config

## Troubleshooting

### Build Issues
```bash
# Check Docker BuildKit is enabled
docker buildx ls

# Verify platform support
docker buildx inspect --bootstrap

# Check Docker Hub authentication
docker info | grep Username
```

### Deployment Issues
```bash
# Check SSH connectivity
ssh pickme@192.168.0.75 "docker info"

# Check Pi disk space
ssh pickme@192.168.0.75 "df -h /"

# Check service logs
ssh pickme@192.168.0.75 "cd /opt/lucid/production && docker-compose logs"
```

### Test Issues
```bash
# Check service health
ssh pickme@192.168.0.75 "docker ps --filter 'health=healthy'"

# Check network connectivity
ssh pickme@192.168.0.75 "docker network ls | grep lucid"
```

## Security Features

### Distroless Containers
- All containers use distroless base images
- No shell or package managers in runtime
- Minimal attack surface

### Secure Configuration
- Auto-generated secure passwords (32-64 bytes)
- JWT secrets with proper expiration
- Encrypted communication between services

### Network Isolation
- Dedicated Docker network (`lucid-pi-network`)
- Internal service communication only
- External access through defined ports only

## Performance Targets

### Database Performance
- MongoDB queries: <10ms p95 latency
- Redis operations: <5ms p95 latency
- Elasticsearch indexing: <100ms per document

### Service Performance
- Auth Service response: <100ms
- Storage Database response: <50ms
- Health checks: <5s startup time

## Next Steps

After successful Phase 1 deployment and testing:

1. **Phase 2**: Deploy Core Services (API Gateway, Blockchain, Service Mesh)
2. **Phase 3**: Deploy Application Services (Sessions, RDP, Node Management)
3. **Phase 4**: Deploy Support Services (Admin Interface, TRON Payment Systems)

## Support

For issues or questions:
1. Check the test results in `tests/results/phase1/`
2. Review service logs: `ssh pickme@192.168.0.75 "docker-compose -f /opt/lucid/production/docker-compose.foundation.yml logs"`
3. Verify network connectivity and firewall settings
4. Ensure Pi has sufficient resources (RAM: 4GB+, Storage: 20GB+)
