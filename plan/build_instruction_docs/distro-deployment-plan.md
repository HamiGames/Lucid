# Distroless Deployment Plan for Raspberry Pi 5

## Overview

Deploy complete distroless infrastructure on Raspberry Pi 5 at 192.168.0.75. CRITICAL: Distroless base containers MUST be deployed BEFORE any Lucid service clusters, as all services depend on the distroless runtime environment.

**Deployment Order:**

1. Networks (6 networks)
2. Environment configuration (.env.distroless)
3. **Distroless base infrastructure (PREREQUISITE for all services)**
4. Lucid service clusters (Foundation, Core, Application, Support)

All deployment commands are manual (SSH to Pi console), except .env.distroless generation (bash script).

## Prerequisites

- SSH access: `ssh pickme@192.168.0.75`
- Project root: `/mnt/myssd/Lucid/Lucid`
- Docker and Docker Compose installed on Pi
- Pre-built images on Docker Hub: `pickme/lucid-base:latest-arm64` and `pickme/lucid-*:latest-arm64`

---

## Phase 1: Network Infrastructure Setup

### Create 6 Docker Networks

**Location:** Raspberry Pi console via SSH

**Commands (manual input):**

```bash
# 1. Main Network (Foundation + Core + Application + Blockchain)
docker network create lucid-pi-network \
  --driver bridge \
  --subnet 172.20.0.0/16 \
  --gateway 172.20.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=main" \
  --label "lucid.subnet=172.20.0.0/16"

# 2. TRON Isolated Network (Payment Services)
docker network create lucid-tron-isolated \
  --driver bridge \
  --subnet 172.21.0.0/16 \
  --gateway 172.21.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=tron-isolated" \
  --label "lucid.subnet=172.21.0.0/16"

# 3. GUI Network (Electron GUI Services)
docker network create lucid-gui-network \
  --driver bridge \
  --subnet 172.22.0.0/16 \
  --gateway 172.22.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=gui" \
  --label "lucid.subnet=172.22.0.0/16"

# 4. Distroless Production Network
docker network create lucid-distroless-production \
  --driver bridge \
  --subnet 172.23.0.0/16 \
  --gateway 172.23.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=distroless-production" \
  --label "lucid.subnet=172.23.0.0/16"

# 5. Distroless Development Network
docker network create lucid-distroless-dev \
  --driver bridge \
  --subnet 172.24.0.0/16 \
  --gateway 172.24.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=distroless-dev" \
  --label "lucid.subnet=172.24.0.0/16"

# 6. Multi-Stage Build Network
docker network create lucid-multi-stage-network \
  --driver bridge \
  --subnet 172.25.0.0/16 \
  --gateway 172.25.0.1 \
  --attachable \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.driver.mtu=1500 \
  --label "lucid.network=multi-stage" \
  --label "lucid.subnet=172.25.0.0/16"
```

**Verification:**

```bash
docker network ls | grep lucid
docker network inspect lucid-pi-network | grep -E "Subnet|Gateway"
docker network inspect lucid-distroless-production | grep -E "Subnet|Gateway"
```

---

## Phase 2: Environment Configuration

### Generate .env.distroless File

**Location:** Raspberry Pi console via SSH

**Directory:** `/mnt/myssd/Lucid/Lucid`

**Script-based generation (ONLY automated step):**

Create script `scripts/config/generate-distroless-env.sh` with content from plan, then execute:

```bash
cd /mnt/myssd/Lucid/Lucid
chmod +x scripts/config/generate-distroless-env.sh
bash scripts/config/generate-distroless-env.sh
```

**Verification:**

```bash
ls -la configs/environment/.env.distroless
grep -E "MONGODB_PASSWORD|JWT_SECRET_KEY|USER_ID" configs/environment/.env.distroless
```

---

## Phase 3: Base Distroless Infrastructure Deployment

**CRITICAL:** All distroless configurations depend on `pickme/lucid-base:latest-arm64`. Deploy these BEFORE any Lucid services.

### Step 3.0: Pull Base Distroless Image (PREREQUISITE)

```bash
docker pull pickme/lucid-base:latest-arm64
docker images | grep lucid-base
```

### Step 3.1: Deploy Distroless Config (Base Infrastructure)

**File:** `configs/docker/distroless/distroless-config.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-config.yml \
  up -d
```

**Services:** base, minimal-base, arm64-base

**Verification:** `docker ps | grep -E "base|minimal-base|arm64-base"`

### Step 3.2: Deploy Distroless Runtime Configuration

**File:** `configs/docker/distroless/distroless-runtime-config.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-runtime-config.yml \
  up -d
```

**Services:** distroless-runtime, minimal-runtime, arm64-runtime

**Verification:** `docker ps | grep runtime`

### Step 3.3: Deploy Distroless Build Configuration

**File:** `configs/docker/distroless/distroless-build-config.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-build-config.yml \
  up -d
```

**Services:** distroless-builder, security-scanner, layer-optimizer

**Verification:** `docker ps | grep -E "builder|scanner|optimizer"`

### Step 3.4: Deploy Base Docker Compose

**File:** `infrastructure/docker/distroless/base/docker-compose.base.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.distroless \
  -f infrastructure/docker/distroless/base/docker-compose.base.yml \
  up -d
```

**Services:** lucid-base-container, lucid-minimal-base-container, lucid-arm64-base-container

**Verification:** `docker ps | grep lucid-base`

### Step 3.5: Deploy Development Configuration (Optional)

**File:** `configs/docker/distroless/distroless-development-config.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-development-config.yml \
  up -d
```

**Services:** dev-distroless, dev-minimal, dev-tools

**Verification:** `docker ps | grep dev-`

### Step 3.6: Deploy Security Configuration (Production)

**File:** `configs/docker/distroless/distroless-security-config.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-security-config.yml \
  up -d
```

**Services:** secure-distroless, minimal-secure, security-monitor

**Verification:** `docker ps | grep secure`

### Step 3.7: Deploy Test Runtime (Validation)

**File:** `configs/docker/distroless/test-runtime-config.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/test-runtime-config.yml \
  up -d
```

**Services:** test-runtime

**Verification:** `docker logs test-runtime` (should show "Test runtime healthy")

### Step 3.8: Verify All Distroless Base Infrastructure

```bash
# Check all distroless containers
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep -E "base|runtime|distroless"

# Verify user is 65532:65532
docker exec base id
docker exec distroless-runtime id

# Verify no shell access (should fail)
docker exec base sh -c "echo test" 2>&1 | grep "executable file not found"

# Check health
docker ps --filter health=healthy | grep -E "base|runtime"
```

---

## Phase 4: Lucid Service Clusters Deployment

**PREREQUISITE:** Phase 3 distroless base infrastructure must be running.

### Cluster 1: Foundation Services (Phase 1)

**File:** `configs/docker/docker-compose.foundation.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.foundation \
  -f configs/docker/docker-compose.foundation.yml \
  up -d
```

**Services:** MongoDB, Redis, Elasticsearch, Auth Service

**Images:** pickme/lucid-mongodb, lucid-redis, lucid-elasticsearch, lucid-auth-service (all :latest-arm64)

**Verification:**

```bash
docker ps | grep -E "lucid-mongodb|lucid-redis|lucid-elasticsearch|lucid-auth-service"
curl http://localhost:8089/health
docker exec lucid-mongodb mongosh --eval "db.adminCommand('ping')"
docker exec lucid-redis redis-cli ping
```

### Cluster 2: Core Services (Phase 2)

**File:** `configs/docker/docker-compose.core.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.core \
  -f configs/docker/docker-compose.core.yml \
  up -d
```

**Services:** API Gateway, Blockchain Engine, Service Mesh, Session Anchoring, Block Manager, Data Chain

**Verification:**

```bash
docker ps | grep -E "api-gateway|blockchain-engine|service-mesh"
curl http://localhost:8080/health
curl http://localhost:8084/health
curl http://localhost:8500/health
```

### Cluster 3: Application Services (Phase 3)

**File:** `configs/docker/docker-compose.application.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.application \
  -f configs/docker/docker-compose.application.yml \
  up -d
```

**Services:** Session Pipeline, Session Recorder, Chunk Processor, Session Storage, Session API, RDP Services, Node Management

**Verification:**

```bash
docker ps | grep -E "session|rdp|node-management"
curl http://localhost:8087/health
curl http://localhost:8095/health
```

### Cluster 4: Support Services (Phase 4)

**File:** `configs/docker/docker-compose.support.yml`

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.support \
  -f configs/docker/docker-compose.support.yml \
  up -d
```

**Services:** Admin Interface, TRON Payment Services (6 services on isolated network)

**Verification:**

```bash
docker ps | grep -E "admin-interface|tron"
curl http://localhost:8083/health
curl http://localhost:8091/health
docker network inspect lucid-tron-isolated | grep tron
```

---

## Phase 5: Post-Deployment Verification

### System-Wide Health Check

```bash
# All containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health status
docker ps --filter health=healthy
docker ps --filter health=unhealthy

# Networks
docker network ls | grep lucid

# Resource usage
docker stats --no-stream

# Logs
docker-compose -f configs/docker/docker-compose.foundation.yml logs --tail=50
```

### Distroless Compliance Verification

```bash
# Verify non-root user (65532:65532)
docker exec lucid-auth-service id
docker exec distroless-runtime id

# Verify no shell
docker exec lucid-auth-service sh -c "echo test" 2>&1 | grep "executable file not found"

# Verify distroless base
docker inspect pickme/lucid-auth-service:latest-arm64 | grep "gcr.io/distroless"

# Verify security options
docker inspect lucid-auth-service | grep -E "SecurityOpt|CapDrop|ReadonlyRootfs"
```

---

## Deployment Order Summary

1. **Networks** (6 networks) - Phase 1
2. **Environment** (.env.distroless generation) - Phase 2
3. **Distroless Base Infrastructure** (CRITICAL PREREQUISITE) - Phase 3

   - distroless-config.yml
   - distroless-runtime-config.yml
   - distroless-build-config.yml
   - docker-compose.base.yml
   - distroless-development-config.yml (optional)
   - distroless-security-config.yml (production)
   - test-runtime-config.yml (validation)

4. **Foundation Cluster** (MongoDB, Redis, Elasticsearch, Auth) - Phase 4.1
5. **Core Cluster** (API Gateway, Blockchain, Service Mesh) - Phase 4.2
6. **Application Cluster** (Sessions, RDP, Node Management) - Phase 4.3
7. **Support Cluster** (Admin, TRON Payments) - Phase 4.4
8. **Verification** (Health checks, compliance tests) - Phase 5

---

## Key Distroless Requirements Met

Per project_build_prog documentation:

- **Base Image:** gcr.io/distroless/python3-debian12 (all services)
- **Non-root User:** UID 65532:65532 (distroless standard)
- **No Shell:** No shell access in runtime containers
- **Multi-stage Build:** All Dockerfiles use builder + distroless runtime
- **Security Labels:** Applied to all containers
- **Health Checks:** Python-based (no shell commands)
- **Network Isolation:** Proper network segmentation
- **Resource Limits:** Memory and CPU limits configured
- **Read-only Filesystem:** Where applicable
- **Capability Dropping:** All capabilities dropped, only necessary ones added

---

## Configuration Files Reference

- **Networks:** plan/build_instruction_docs/env_files/network-configs.md
- **Environment:** plan/build_instruction_docs/env_files/env-file-pi.md
- **Distroless Config:** configs/docker/distroless/distroless-config.yml
- **Runtime Config:** configs/docker/distroless/distroless-runtime-config.yml
- **Build Config:** configs/docker/distroless/distroless-build-config.yml
- **Dev Config:** configs/docker/distroless/distroless-development-config.yml
- **Security Config:** configs/docker/distroless/distroless-security-config.yml
- **Test Config:** configs/docker/distroless/test-runtime-config.yml
- **Base Compose:** infrastructure/docker/distroless/base/docker-compose.base.yml
- **Distroless Env:** configs/docker/distroless/distroless.env
- **Foundation:** configs/docker/docker-compose.foundation.yml
- **Core:** configs/docker/docker-compose.core.yml
- **Application:** configs/docker/docker-compose.application.yml
- **Support:** configs/docker/docker-compose.support.yml