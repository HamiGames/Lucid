# Phase 2: Core Services Distroless Deployment Plan

## Overview

Deploy Core Services (Phase 2) with true distroless containers on Raspberry Pi 5 at 192.168.0.75. This phase includes API Gateway, Blockchain Engine, Service Mesh, Session Anchoring, Block Manager, and Data Chain services with proper volume management, environment configuration, and security hardening.

**PREREQUISITE:** Phase 1 Foundation Services must be deployed and healthy before proceeding.

## Prerequisites

- Phase 1 Foundation Services deployed and running healthy
- SSH access: `ssh pickme@192.168.0.75`
- Project root: `/mnt/myssd/Lucid/Lucid`
- Docker and Docker Compose installed on Pi
- Pre-built images on Docker Hub: `pickme/lucid-*:latest-arm64`
- Networks already created (from Phase 1)
- Foundation services running: MongoDB, Redis, Elasticsearch, Auth Service

## File Updates Required

### 1. Update Core Docker Compose with Volumes

**File:** `configs/docker/docker-compose.core.yml`

Add volume configurations and port mappings to all services:

**API Gateway volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/logs/api-gateway:/app/logs:rw
  - /mnt/myssd/Lucid/data/api-gateway/cache:/app/cache:rw
  - api-gateway-tmp:/tmp/api
ports:
  - "8080:8080"
```

**Blockchain Engine volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/blockchain:/app/data:rw
  - /mnt/myssd/Lucid/logs/blockchain-engine:/app/logs:rw
  - blockchain-cache:/tmp/blockchain
ports:
  - "8084:8084"
```

**Service Mesh volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/logs/service-mesh:/app/logs:rw
  - /mnt/myssd/Lucid/data/service-mesh/config:/app/config:rw
  - service-mesh-cache:/tmp/mesh
ports:
  - "8500:8500"
```

**Session Anchoring volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/session-anchoring:/app/data:rw
  - /mnt/myssd/Lucid/logs/session-anchoring:/app/logs:rw
  - session-anchoring-cache:/tmp/anchoring
```

**Block Manager volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/block-manager:/app/data:rw
  - /mnt/myssd/Lucid/logs/block-manager:/app/logs:rw
  - block-manager-cache:/tmp/blocks
```

**Data Chain volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/data-chain:/app/data:rw
  - /mnt/myssd/Lucid/logs/data-chain:/app/logs:rw
  - data-chain-cache:/tmp/chain
```

Add named volumes section at end:

```yaml
volumes:
  api-gateway-tmp:
    driver: local
    name: lucid-api-gateway-tmp
  blockchain-cache:
    driver: local
    name: lucid-blockchain-cache
  service-mesh-cache:
    driver: local
    name: lucid-service-mesh-cache
  session-anchoring-cache:
    driver: local
    name: lucid-session-anchoring-cache
  block-manager-cache:
    driver: local
    name: lucid-block-manager-cache
  data-chain-cache:
    driver: local
    name: lucid-data-chain-cache
```

### 2. Verify Environment Variable Consistency

**Files to check:**

- `configs/environment/env.core`
- `configs/environment/env.foundation` (for cross-references)

Ensure naming conventions match:

- Container names: `api-gateway`, `blockchain-engine`, `service-mesh`, `session-anchoring`, `block-manager`, `data-chain`
- Service hosts: Same as container names
- Network: `lucid-pi-network` (shared with Phase 1)
- User: `65532:65532` (distroless standard)
- Image names: `pickme/lucid-[service]:latest-arm64`
- Environment variable references from Phase 1: `${MONGODB_URL}`, `${REDIS_URL}`, `${AUTH_SERVICE_URL}`

### 3. Create/Verify Core Environment Generation Script

**File:** `scripts/config/generate-core-env.sh` (if missing)

Should follow same pattern as `generate-foundation-env.sh` and include Core service-specific variables.

## Deployment Steps (SSH to Pi)

### Phase 2A: Verify Phase 1 Services

```bash
# SSH to Pi
ssh pickme@192.168.0.75
cd /mnt/myssd/Lucid/Lucid

# Verify Phase 1 services are healthy
docker ps | grep -E "lucid-mongodb|lucid-redis|lucid-elasticsearch|lucid-auth-service"
docker ps --filter health=healthy | grep -E "lucid-mongodb|lucid-redis|lucid-auth-service"

# Test Phase 1 connectivity
docker exec lucid-mongodb mongosh --eval "db.adminCommand('ping')"
docker exec lucid-redis redis-cli ping
curl -f http://localhost:8089/health || echo "Auth service not ready"

# Verify networks exist
docker network ls | grep lucid-pi-network
docker network inspect lucid-pi-network | grep -E "Subnet|Gateway"
```

### Phase 2B: Directory Structure

```bash
# Create Phase 2 data directories
sudo mkdir -p /mnt/myssd/Lucid/data/{api-gateway/cache,blockchain,service-mesh/config,session-anchoring,block-manager,data-chain}
sudo mkdir -p /mnt/myssd/Lucid/logs/{api-gateway,blockchain-engine,service-mesh,session-anchoring,block-manager,data-chain}

# Set ownership
sudo chown -R pickme:pickme /mnt/myssd/Lucid/data
sudo chown -R pickme:pickme /mnt/myssd/Lucid/logs

# Verify directories
ls -la /mnt/myssd/Lucid/data/
ls -la /mnt/myssd/Lucid/logs/
```

### Phase 2C: Environment Configuration

**Option 1: If not already generated**

```bash
# Generate core environment (requires Phase 1 env.foundation)
cd /mnt/myssd/Lucid/Lucid
chmod +x scripts/config/generate-core-env.sh
bash scripts/config/generate-core-env.sh

# Verify
ls -la configs/environment/env.core
grep -E "API_GATEWAY_URL|BLOCKCHAIN_ENGINE_URL|MONGODB_URL" configs/environment/env.core
```

**Option 2: If already configured**

```bash
# Verify file exists and has required variables
ls -la configs/environment/env.core
grep -E "API_GATEWAY_HOST|BLOCKCHAIN_ENGINE_HOST" configs/environment/env.core
```

### Phase 2D: Pull Docker Images

```bash
# Pull core service images
docker pull pickme/lucid-api-gateway:latest-arm64
docker pull pickme/lucid-blockchain-engine:latest-arm64
docker pull pickme/lucid-service-mesh:latest-arm64
docker pull pickme/lucid-session-anchoring:latest-arm64
docker pull pickme/lucid-block-manager:latest-arm64
docker pull pickme/lucid-data-chain:latest-arm64

# Verify all images
docker images | grep pickme/lucid | grep -E "api-gateway|blockchain|service-mesh|session|block|data-chain"
```

### Phase 2E: Deploy Core Services

```bash
cd /mnt/myssd/Lucid/Lucid

# Deploy Core Services using both env files (Foundation + Core)
docker-compose \
  --env-file configs/environment/env.foundation \
  --env-file configs/environment/env.core \
  -f configs/docker/docker-compose.core.yml \
  up -d

# Verify services starting
docker ps | grep -E "api-gateway|blockchain-engine|service-mesh|session-anchoring|block-manager|data-chain"
```

### Phase 2F: Verification & Health Checks

```bash
# Wait for services to initialize (90 seconds for blockchain services)
sleep 90

# Check all Phase 2 containers running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "api-gateway|blockchain|service-mesh|session|block|data-chain"

# Check health status
docker ps --filter health=healthy | grep -E "api-gateway|blockchain-engine|service-mesh"

# Verify API Gateway
curl http://localhost:8080/health
curl -f http://localhost:8080/health || echo "API Gateway not ready"

# Verify Blockchain Engine
curl http://localhost:8084/health
curl -f http://localhost:8084/health || echo "Blockchain Engine not ready"

# Verify Service Mesh
curl http://localhost:8500/health
curl -f http://localhost:8500/health || echo "Service Mesh not ready"

# Check logs for errors
docker logs api-gateway --tail 50
docker logs blockchain-engine --tail 50
docker logs service-mesh --tail 50
docker logs session-anchoring --tail 50
docker logs block-manager --tail 50
docker logs data-chain --tail 50

# Verify distroless compliance for all services
for service in api-gateway blockchain-engine service-mesh session-anchoring block-manager data-chain; do
  echo "Checking $service..."
  docker exec $service id
  docker exec $service sh -c "echo test" 2>&1 | grep "executable file not found"
done

# Verify volumes mounted
docker inspect api-gateway | grep -A 10 "Mounts"
docker inspect blockchain-engine | grep -A 10 "Mounts"
docker inspect service-mesh | grep -A 10 "Mounts"

# Check disk usage
df -h /mnt/myssd/Lucid/data/
du -sh /mnt/myssd/Lucid/data/*
du -sh /mnt/myssd/Lucid/logs/*
```

### Phase 2G: Integration Testing

```bash
# Verify network connectivity between Phase 1 and Phase 2 services
# Test from API Gateway to Phase 1 services
docker exec api-gateway python3 -c "import socket; socket.create_connection(('lucid-mongodb', 27017), timeout=5); print('MongoDB connection OK')"
docker exec api-gateway python3 -c "import socket; socket.create_connection(('lucid-redis', 6379), timeout=5); print('Redis connection OK')"
docker exec api-gateway python3 -c "import socket; socket.create_connection(('lucid-auth-service', 8089), timeout=5); print('Auth Service connection OK')"

# Test API Gateway routing
curl -X GET http://localhost:8080/api/v1/status
curl -X GET http://localhost:8080/health

# Test blockchain operations
curl -X GET http://localhost:8084/blockchain/status
curl -X GET http://localhost:8084/blockchain/blocks/latest

# Test service mesh discovery
curl -X GET http://localhost:8500/v1/catalog/services

# Verify service registration in mesh
curl -X GET http://localhost:8500/v1/catalog/service/api-gateway
curl -X GET http://localhost:8500/v1/catalog/service/blockchain-engine
```

## Verification Checklist

- [ ] Phase 1 Foundation Services healthy and running
- [ ] Phase 2 data directories created with correct permissions
- [ ] Phase 2 log directories created with correct permissions
- [ ] Core environment file generated/verified
- [ ] All Phase 2 images pulled successfully
- [ ] API Gateway container running and healthy
- [ ] Blockchain Engine container running and healthy
- [ ] Service Mesh container running and healthy
- [ ] Session Anchoring container running and healthy
- [ ] Block Manager container running and healthy
- [ ] Data Chain container running and healthy
- [ ] All services using user 65532:65532
- [ ] No shell access verified on all containers
- [ ] Health checks passing on all services
- [ ] Volumes correctly mounted on all services
- [ ] Network connectivity verified between Phase 1 and Phase 2 services
- [ ] API Gateway routing working
- [ ] Blockchain operations responding
- [ ] Service Mesh discovery working
- [ ] Integration tests passing

## Rollback Procedure

```bash
# Stop and remove Core services only (keeps Phase 1 running)
docker-compose -f configs/docker/docker-compose.core.yml down

# Remove named volumes (optional, keeps data)
docker volume ls | grep -E "api-gateway|blockchain|service-mesh|session|block|data-chain"
docker volume rm lucid-api-gateway-tmp lucid-blockchain-cache lucid-service-mesh-cache lucid-session-anchoring-cache lucid-block-manager-cache lucid-data-chain-cache

# Data remains in /mnt/myssd/Lucid/data/ for recovery
# Phase 1 services continue running unaffected
```

## Key Files Modified

1. `configs/docker/docker-compose.core.yml` - Add volumes and ports
2. `configs/environment/env.core` - Verify consistency with foundation
3. Create `scripts/config/generate-core-env.sh` if missing

## Naming Convention Standards

All naming follows these patterns:

- **Images**: `pickme/lucid-[service]:latest-arm64`
- **Containers**: `[service-name]` (e.g., `api-gateway`, `blockchain-engine`)
- **Networks**: `lucid-pi-network` (shared with Phase 1)
- **Volumes (named)**: `lucid-[service]-cache` or `lucid-[service]-tmp`
- **Volumes (host)**: `/mnt/myssd/Lucid/[type]/[service]`
- **User**: `65532:65532` (distroless standard)
- **Environment variables**: `[SERVICE]_[PROPERTY]` (e.g., `API_GATEWAY_HOST`)
- **Service URLs**: `http://[container-name]:[port]` (e.g., `http://api-gateway:8080`)

## Service Dependencies

Phase 2 services depend on Phase 1:

- **API Gateway** → MongoDB, Redis, Auth Service
- **Blockchain Engine** → MongoDB, Redis
- **Service Mesh** → MongoDB, Redis
- **Session Anchoring** → MongoDB, Redis, Blockchain Engine
- **Block Manager** → MongoDB, Redis, Blockchain Engine
- **Data Chain** → MongoDB, Redis, Blockchain Engine

## Port Mapping

Phase 2 exposed ports:

- **8080**: API Gateway (external access)
- **8084**: Blockchain Engine (external access)
- **8500**: Service Mesh (external access)