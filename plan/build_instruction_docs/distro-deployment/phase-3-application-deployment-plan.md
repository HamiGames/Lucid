# Phase 3: Application Services Distroless Deployment Plan

## Overview

Deploy Application Services (Phase 3) with true distroless containers on Raspberry Pi 5 at 192.168.0.75. This phase includes Session Management services (Pipeline, Recorder, Processor, Storage, API), RDP Services (Server Manager, XRDP, Controller, Monitor), and Node Management service with proper volume management, environment configuration, and security hardening.

**PREREQUISITES:** Phase 1 Foundation Services AND Phase 2 Core Services must be deployed and healthy before proceeding.

## Prerequisites

- Phase 1 Foundation Services deployed and running healthy
- Phase 2 Core Services deployed and running healthy
- SSH access: `ssh pickme@192.168.0.75`
- Project root: `/mnt/myssd/Lucid/Lucid`
- Docker and Docker Compose installed on Pi
- Pre-built images on Docker Hub: `pickme/lucid-*:latest-arm64`
- Networks already created (from Phase 1)
- Foundation services running: MongoDB, Redis, Elasticsearch, Auth Service
- Core services running: API Gateway, Blockchain Engine, Service Mesh, Session Anchoring, Block Manager, Data Chain

## File Updates Required

### 1. Update Application Docker Compose with Volumes

**File:** `configs/docker/docker-compose.application.yml`

Add volume configurations and port mappings to all services:

**Session Pipeline volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/session-pipeline:/app/data:rw
  - /mnt/myssd/Lucid/logs/session-pipeline:/app/logs:rw
  - session-pipeline-cache:/tmp/pipeline
ports:
  - "8083:8083"
```

**Session Recorder volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/session-recorder/recordings:/app/recordings:rw
  - /mnt/myssd/Lucid/data/session-recorder/chunks:/app/chunks:rw
  - /mnt/myssd/Lucid/logs/session-recorder:/app/logs:rw
  - session-recorder-cache:/tmp/recorder
ports:
  - "8084:8084"
```

**Session Processor volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/session-processor:/app/data:rw
  - /mnt/myssd/Lucid/logs/session-processor:/app/logs:rw
  - session-processor-cache:/tmp/processor
ports:
  - "8085:8085"
```

**Session Storage volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/session-storage:/app/data:rw
  - /mnt/myssd/Lucid/logs/session-storage:/app/logs:rw
  - session-storage-cache:/tmp/storage
ports:
  - "8086:8086"
```

**Session API volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/logs/session-api:/app/logs:rw
  - session-api-cache:/tmp/api
ports:
  - "8087:8087"
```

**RDP Server Manager volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/rdp-server-manager:/app/data:rw
  - /mnt/myssd/Lucid/logs/rdp-server-manager:/app/logs:rw
  - rdp-server-manager-cache:/tmp/rdp-manager
ports:
  - "8090:8090"
```

**RDP XRDP volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/rdp-xrdp/config:/app/config:rw
  - /mnt/myssd/Lucid/logs/rdp-xrdp:/app/logs:rw
  - rdp-xrdp-cache:/tmp/xrdp
ports:
  - "8091:8091"
  - "3389:3389"
```

**RDP Controller volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/rdp-controller:/app/data:rw
  - /mnt/myssd/Lucid/logs/rdp-controller:/app/logs:rw
  - rdp-controller-cache:/tmp/controller
ports:
  - "8092:8092"
```

**RDP Monitor volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/logs/rdp-monitor:/app/logs:rw
  - rdp-monitor-cache:/tmp/monitor
ports:
  - "8093:8093"
```

**Node Management volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/node-management:/app/data:rw
  - /mnt/myssd/Lucid/logs/node-management:/app/logs:rw
  - node-management-cache:/tmp/nodes
ports:
  - "8095:8095"
```

Add named volumes section at end:

```yaml
volumes:
  session-pipeline-cache:
    driver: local
    name: lucid-session-pipeline-cache
  session-recorder-cache:
    driver: local
    name: lucid-session-recorder-cache
  session-processor-cache:
    driver: local
    name: lucid-session-processor-cache
  session-storage-cache:
    driver: local
    name: lucid-session-storage-cache
  session-api-cache:
    driver: local
    name: lucid-session-api-cache
  rdp-server-manager-cache:
    driver: local
    name: lucid-rdp-server-manager-cache
  rdp-xrdp-cache:
    driver: local
    name: lucid-rdp-xrdp-cache
  rdp-controller-cache:
    driver: local
    name: lucid-rdp-controller-cache
  rdp-monitor-cache:
    driver: local
    name: lucid-rdp-monitor-cache
  node-management-cache:
    driver: local
    name: lucid-node-management-cache
```

### 2. Verify Environment Variable Consistency

**Files to check:**

- `configs/environment/env.foundation` (for cross-references)
- `configs/environment/env.core` (for cross-references)
- Create `configs/environment/env.application` if missing

Ensure naming conventions match:

- Container names: `session-pipeline`, `session-recorder`, `session-processor`, `session-storage`, `session-api`, `rdp-server-manager`, `rdp-xrdp`, `rdp-controller`, `rdp-monitor`, `node-management`
- Service hosts: Same as container names
- Network: `lucid-pi-network` (shared with Phase 1 and 2)
- User: `65532:65532` (distroless standard)
- Image names: `pickme/lucid-[service]:latest-arm64`
- Environment variable references from Phase 1 & 2: `${MONGODB_URL}`, `${REDIS_URL}`, `${API_GATEWAY_URL}`, `${BLOCKCHAIN_ENGINE_URL}`

### 3. Create/Verify Application Environment Generation Script

**File:** `scripts/config/generate-application-env.sh` (if missing)

Should follow same pattern as `generate-foundation-env.sh` and `generate-core-env.sh` and include Application service-specific variables.

## Deployment Steps (SSH to Pi)

### Phase 3A: Verify Phase 1 & 2 Services

```bash
# SSH to Pi
ssh pickme@192.168.0.75
cd /mnt/myssd/Lucid/Lucid

# Verify Phase 1 services are healthy
docker ps | grep -E "lucid-mongodb|lucid-redis|lucid-elasticsearch|lucid-auth-service"
docker ps --filter health=healthy | grep -E "lucid-mongodb|lucid-redis|lucid-auth-service"

# Verify Phase 2 services are healthy
docker ps | grep -E "api-gateway|blockchain-engine|service-mesh|session-anchoring|block-manager|data-chain"
docker ps --filter health=healthy | grep -E "api-gateway|blockchain-engine|service-mesh"

# Test Phase 1 connectivity
docker exec lucid-mongodb mongosh --eval "db.adminCommand('ping')"
docker exec lucid-redis redis-cli ping
curl -f http://localhost:8089/health || echo "Auth service not ready"

# Test Phase 2 connectivity
curl -f http://localhost:8080/health || echo "API Gateway not ready"
curl -f http://localhost:8084/health || echo "Blockchain Engine not ready"
curl -f http://localhost:8500/health || echo "Service Mesh not ready"

# Verify networks exist
docker network ls | grep lucid-pi-network
docker network inspect lucid-pi-network | grep -E "Subnet|Gateway"
```

### Phase 3B: Directory Structure

```bash
# Create Phase 3 data directories
sudo mkdir -p /mnt/myssd/Lucid/data/{session-pipeline,session-recorder/{recordings,chunks},session-processor,session-storage}
sudo mkdir -p /mnt/myssd/Lucid/data/{rdp-server-manager,rdp-xrdp/config,rdp-controller,node-management}
sudo mkdir -p /mnt/myssd/Lucid/logs/{session-pipeline,session-recorder,session-processor,session-storage,session-api}
sudo mkdir -p /mnt/myssd/Lucid/logs/{rdp-server-manager,rdp-xrdp,rdp-controller,rdp-monitor,node-management}

# Set ownership
sudo chown -R pickme:pickme /mnt/myssd/Lucid/data
sudo chown -R pickme:pickme /mnt/myssd/Lucid/logs

# Verify directories
ls -la /mnt/myssd/Lucid/data/
ls -la /mnt/myssd/Lucid/logs/
du -sh /mnt/myssd/Lucid/data/*
```

### Phase 3C: Environment Configuration

**Option 1: If not already generated**

```bash
# Generate application environment (requires Phase 1 & 2 env files)
cd /mnt/myssd/Lucid/Lucid
chmod +x scripts/config/generate-application-env.sh
bash scripts/config/generate-application-env.sh

# Verify
ls -la configs/environment/env.application
grep -E "SESSION_PIPELINE_HOST|RDP_SERVER_MANAGER_HOST|NODE_MANAGEMENT_HOST" configs/environment/env.application
```

**Option 2: If already configured**

```bash
# Verify file exists and has required variables
ls -la configs/environment/env.application
grep -E "SESSION_API_HOST|RDP_SERVER_MANAGER_PORT|NODE_MANAGEMENT_PORT" configs/environment/env.application
```

### Phase 3D: Pull Docker Images

```bash
# Pull session management service images
docker pull pickme/lucid-session-pipeline:latest-arm64
docker pull pickme/lucid-session-recorder:latest-arm64
docker pull pickme/lucid-session-processor:latest-arm64
docker pull pickme/lucid-session-storage:latest-arm64
docker pull pickme/lucid-session-api:latest-arm64

# Pull RDP service images
docker pull pickme/lucid-rdp-server-manager:latest-arm64
docker pull pickme/lucid-rdp-xrdp:latest-arm64
docker pull pickme/lucid-rdp-controller:latest-arm64
docker pull pickme/lucid-rdp-monitor:latest-arm64

# Pull node management image
docker pull pickme/lucid-node-management:latest-arm64

# Verify all images
docker images | grep pickme/lucid | grep -E "session|rdp|node"
```

### Phase 3E: Deploy Application Services

```bash
cd /mnt/myssd/Lucid/Lucid

# Deploy Application Services using all env files (Foundation + Core + Application)
docker-compose \
  --env-file configs/environment/env.foundation \
  --env-file configs/environment/env.core \
  --env-file configs/environment/env.application \
  -f configs/docker/docker-compose.application.yml \
  up -d

# Verify services starting
docker ps | grep -E "session-pipeline|session-recorder|session-processor|session-storage|session-api"
docker ps | grep -E "rdp-server-manager|rdp-xrdp|rdp-controller|rdp-monitor"
docker ps | grep node-management
```

### Phase 3F: Verification & Health Checks

```bash
# Wait for services to initialize (120 seconds for session services)
sleep 120

# Check all Phase 3 containers running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "session|rdp|node"

# Check health status
docker ps --filter health=healthy | grep -E "session-api|rdp-server-manager|node-management"

# Verify Session Management Services
curl http://localhost:8083/health || echo "Session Pipeline not ready"
curl http://localhost:8084/health || echo "Session Recorder not ready"
curl http://localhost:8085/health || echo "Session Processor not ready"
curl http://localhost:8086/health || echo "Session Storage not ready"
curl http://localhost:8087/health || echo "Session API not ready"

# Verify RDP Services
curl http://localhost:8090/health || echo "RDP Server Manager not ready"
curl http://localhost:8091/health || echo "RDP XRDP not ready"
curl http://localhost:8092/health || echo "RDP Controller not ready"
curl http://localhost:8093/health || echo "RDP Monitor not ready"

# Verify Node Management
curl http://localhost:8095/health || echo "Node Management not ready"

# Check logs for errors
docker logs session-pipeline --tail 50
docker logs session-recorder --tail 50
docker logs session-api --tail 50
docker logs rdp-server-manager --tail 50
docker logs node-management --tail 50

# Verify distroless compliance for all services
for service in session-pipeline session-recorder session-processor session-storage session-api rdp-server-manager rdp-xrdp rdp-controller rdp-monitor node-management; do
  echo "Checking $service..."
  docker exec $service id
  docker exec $service sh -c "echo test" 2>&1 | grep "executable file not found"
done

# Verify volumes mounted
docker inspect session-pipeline | grep -A 10 "Mounts"
docker inspect session-recorder | grep -A 10 "Mounts"
docker inspect rdp-server-manager | grep -A 10 "Mounts"
docker inspect node-management | grep -A 10 "Mounts"

# Check disk usage
df -h /mnt/myssd/Lucid/data/
du -sh /mnt/myssd/Lucid/data/*
du -sh /mnt/myssd/Lucid/logs/*
```

### Phase 3G: Integration Testing

```bash
# Verify network connectivity between Phase 3 and Phase 1/2 services
# Test from Session API to Phase 1 services
docker exec session-api python3 -c "import socket; socket.create_connection(('lucid-mongodb', 27017), timeout=5); print('MongoDB connection OK')"
docker exec session-api python3 -c "import socket; socket.create_connection(('lucid-redis', 6379), timeout=5); print('Redis connection OK')"

# Test from Session API to Phase 2 services
docker exec session-api python3 -c "import socket; socket.create_connection(('api-gateway', 8080), timeout=5); print('API Gateway connection OK')"
docker exec session-api python3 -c "import socket; socket.create_connection(('blockchain-engine', 8084), timeout=5); print('Blockchain Engine connection OK')"

# Test Session Management API endpoints
curl -X GET http://localhost:8087/api/v1/sessions/status
curl -X GET http://localhost:8087/health

# Test session recording capabilities
curl -X POST http://localhost:8084/api/v1/recording/start -H "Content-Type: application/json" -d '{"session_id":"test-001"}'

# Test RDP Server Manager
curl -X GET http://localhost:8090/api/v1/rdp/servers/status
curl -X GET http://localhost:8090/health

# Test Node Management
curl -X GET http://localhost:8095/api/v1/nodes/status
curl -X GET http://localhost:8095/api/v1/nodes/pools
curl -X GET http://localhost:8095/health

# Verify service registration in Service Mesh
curl -X GET http://localhost:8500/v1/catalog/service/session-api
curl -X GET http://localhost:8500/v1/catalog/service/rdp-server-manager
curl -X GET http://localhost:8500/v1/catalog/service/node-management
```

## Verification Checklist

- [ ] Phase 1 Foundation Services healthy and running
- [ ] Phase 2 Core Services healthy and running
- [ ] Phase 3 data directories created with correct permissions
- [ ] Phase 3 log directories created with correct permissions
- [ ] Application environment file generated/verified
- [ ] All Phase 3 images pulled successfully
- [ ] Session Pipeline container running and healthy
- [ ] Session Recorder container running and healthy
- [ ] Session Processor container running and healthy
- [ ] Session Storage container running and healthy
- [ ] Session API container running and healthy
- [ ] RDP Server Manager container running and healthy
- [ ] RDP XRDP container running and healthy
- [ ] RDP Controller container running and healthy
- [ ] RDP Monitor container running and healthy
- [ ] Node Management container running and healthy
- [ ] All services using user 65532:65532
- [ ] No shell access verified on all containers
- [ ] Health checks passing on all services
- [ ] Volumes correctly mounted on all services
- [ ] Network connectivity verified between Phase 1, 2, and 3 services
- [ ] Session Management API responding
- [ ] RDP services responding
- [ ] Node Management API responding
- [ ] Integration tests passing

## Rollback Procedure

```bash
# Stop and remove Application services only (keeps Phase 1 and 2 running)
docker-compose -f configs/docker/docker-compose.application.yml down

# Remove named volumes (optional, keeps data)
docker volume ls | grep -E "session|rdp|node"
docker volume rm lucid-session-pipeline-cache lucid-session-recorder-cache lucid-session-processor-cache lucid-session-storage-cache lucid-session-api-cache lucid-rdp-server-manager-cache lucid-rdp-xrdp-cache lucid-rdp-controller-cache lucid-rdp-monitor-cache lucid-node-management-cache

# Data remains in /mnt/myssd/Lucid/data/ for recovery
# Phase 1 and Phase 2 services continue running unaffected
```

## Key Files Modified

1. `configs/docker/docker-compose.application.yml` - Add volumes and ports
2. `configs/environment/env.application` - Verify consistency with foundation and core
3. Create `scripts/config/generate-application-env.sh` if missing

## Naming Convention Standards

All naming follows these patterns:

- **Images**: `pickme/lucid-[service]:latest-arm64`
- **Containers**: `[service-name]` (e.g., `session-pipeline`, `rdp-server-manager`, `node-management`)
- **Networks**: `lucid-pi-network` (shared with Phase 1 and 2)
- **Volumes (named)**: `lucid-[service]-cache`
- **Volumes (host)**: `/mnt/myssd/Lucid/[type]/[service]`
- **User**: `65532:65532` (distroless standard)
- **Environment variables**: `[SERVICE]_[PROPERTY]` (e.g., `SESSION_API_HOST`, `RDP_SERVER_MANAGER_PORT`)
- **Service URLs**: `http://[container-name]:[port]` (e.g., `http://session-api:8087`)

## Service Dependencies

Phase 3 services depend on Phase 1 and Phase 2:

**Session Management Services:**

- **Session Pipeline** → MongoDB, Redis, Elasticsearch
- **Session Recorder** → MongoDB, Redis, Session Pipeline
- **Session Processor** → MongoDB, Redis, Session Pipeline
- **Session Storage** → MongoDB, Redis, Blockchain Engine
- **Session API** → MongoDB, Redis, API Gateway, All Session Services

**RDP Services:**

- **RDP Server Manager** → MongoDB, Redis, API Gateway, Auth Service
- **RDP XRDP** → MongoDB, Redis, RDP Server Manager
- **RDP Controller** → MongoDB, Redis, Session API, RDP Server Manager
- **RDP Monitor** → MongoDB, Redis, RDP Server Manager

**Node Management:**

- **Node Management** → MongoDB, Redis, API Gateway, Blockchain Engine

## Port Mapping

Phase 3 exposed ports:

**Session Management:**

- **8083**: Session Pipeline (internal)
- **8084**: Session Recorder (internal)
- **8085**: Session Processor (internal)
- **8086**: Session Storage (internal)
- **8087**: Session API (external access)

**RDP Services:**

- **8090**: RDP Server Manager (external access)
- **8091**: RDP XRDP (external access)
- **8092**: RDP Controller (external access)
- **8093**: RDP Monitor (external access)
- **3389**: XRDP Protocol (external access)

**Node Management:**

- **8095**: Node Management API (external access)
