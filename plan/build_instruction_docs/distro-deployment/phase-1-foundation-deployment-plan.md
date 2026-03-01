# Phase 1: Foundation Services Distroless Deployment Plan

## Overview

Deploy Foundation Services (Phase 1) with true distroless containers on Raspberry Pi 5 at 192.168.0.75. This includes distroless base infrastructure (prerequisite), then Foundation cluster services with proper volume management, environment configuration, and security hardening.

## Prerequisites

- SSH access: `ssh pickme@192.168.0.75`
- Project root: `/mnt/myssd/Lucid/Lucid`
- Docker and Docker Compose installed on Pi
- Pre-built images on Docker Hub: `pickme/lucid-*:latest-arm64`
- Windows 11 console for local operations

## File Updates Required

### 1. Update Foundation Docker Compose with Volumes

**File:** `configs/docker/docker-compose.foundation.yml`

Add volume configurations to all services:

**MongoDB volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/mongodb:/data/db:rw
  - /mnt/myssd/Lucid/logs/mongodb:/var/log/mongodb:rw
  - mongodb-cache:/var/cache/mongodb
```

**Redis volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/redis:/data:rw
  - /mnt/myssd/Lucid/logs/redis:/var/log/redis:rw
  - redis-cache:/var/cache/redis
```

**Elasticsearch volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/data/elasticsearch:/usr/share/elasticsearch/data:rw
  - /mnt/myssd/Lucid/logs/elasticsearch:/usr/share/elasticsearch/logs:rw
  - elasticsearch-cache:/tmp/elasticsearch
```

**Auth Service volumes:**

```yaml
volumes:
  - /mnt/myssd/Lucid/logs/auth-service:/app/logs:rw
  - auth-cache:/tmp/auth
```

Add named volumes section at end:

```yaml
volumes:
  mongodb-cache:
    driver: local
    name: lucid-mongodb-cache
  redis-cache:
    driver: local
    name: lucid-redis-cache
  elasticsearch-cache:
    driver: local
    name: lucid-elasticsearch-cache
  auth-cache:
    driver: local
    name: lucid-auth-cache
```

### 2. Update Distroless Runtime Config with Volumes

**File:** `configs/docker/distroless/distroless-runtime-config.yml`

Add volumes to `distroless-runtime` service:

```yaml
volumes:
  - /mnt/myssd/Lucid/logs/distroless-runtime:/app/logs:rw
  - distroless-runtime-cache:/tmp/runtime
```

Add volumes to `minimal-runtime` service:

```yaml
volumes:
  - /mnt/myssd/Lucid/logs/minimal-runtime:/app/logs:rw
  - minimal-runtime-cache:/tmp/runtime
```

Add volumes to `arm64-runtime` service:

```yaml
volumes:
  - /mnt/myssd/Lucid/logs/arm64-runtime:/app/logs:rw
  - arm64-runtime-cache:/tmp/runtime
```

Add named volumes section:

```yaml
volumes:
  distroless-runtime-cache:
    driver: local
    name: lucid-distroless-runtime-cache
  minimal-runtime-cache:
    driver: local
    name: lucid-minimal-runtime-cache
  arm64-runtime-cache:
    driver: local
    name: lucid-arm64-runtime-cache
```

### 3. Update Distroless Config with Volumes

**File:** `configs/docker/distroless/distroless-config.yml`

Add volumes to each service (base, minimal-base, arm64-base):

```yaml
volumes:
  - /mnt/myssd/Lucid/logs/[service-name]:/app/logs:rw
  - [service-name]-cache:/tmp/cache
```

Add named volumes section with all three cache volumes.

### 4. Update Base Docker Compose with Volumes

**File:** `infrastructure/docker/distroless/base/docker-compose.base.yml`

Add volumes to all three services following same pattern as distroless-config.yml.

### 5. Verify Environment Variable Consistency

**Files to check:**

- `configs/environment/.env.foundation`
- `configs/environment/env.core`
- `scripts/config/generate-distroless-env.sh`

Ensure all naming conventions match across files:

- Container names: `lucid-[service]` (e.g., `lucid-mongodb`, `lucid-redis`)
- Service hosts: Same as container names
- Network names: `lucid-pi-network`, `lucid-distroless-production`
- User: `65532:65532` (distroless standard)
- Image names: `pickme/lucid-[service]:latest-arm64`

## Deployment Steps (SSH to Pi)

### Phase 1A: Network Infrastructure

```bash
# SSH to Pi
ssh pickme@192.168.0.75
cd /mnt/myssd/Lucid/Lucid

# Create 6 networks
docker network create lucid-pi-network --driver bridge --subnet 172.20.0.0/16 --gateway 172.20.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 --opt com.docker.network.driver.mtu=1500 --label "lucid.network=main" --label "lucid.subnet=172.20.0.0/16"

docker network create lucid-tron-isolated --driver bridge --subnet 172.21.0.0/16 --gateway 172.21.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 --opt com.docker.network.driver.mtu=1500 --label "lucid.network=tron-isolated" --label "lucid.subnet=172.21.0.0/16"

docker network create lucid-gui-network --driver bridge --subnet 172.22.0.0/16 --gateway 172.22.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.bridge.host_binding_ipv4=0.0.0.0 --opt com.docker.network.driver.mtu=1500 --label "lucid.network=gui" --label "lucid.subnet=172.22.0.0/16"

docker network create lucid-distroless-production --driver bridge --subnet 172.23.0.0/16 --gateway 172.23.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.driver.mtu=1500 --label "lucid.network=distroless-production" --label "lucid.subnet=172.23.0.0/16"

docker network create lucid-distroless-dev --driver bridge --subnet 172.24.0.0/16 --gateway 172.24.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.driver.mtu=1500 --label "lucid.network=distroless-dev" --label "lucid.subnet=172.24.0.0/16"

docker network create lucid-multi-stage-network --driver bridge --subnet 172.25.0.0/16 --gateway 172.25.0.1 --attachable --opt com.docker.network.bridge.enable_icc=true --opt com.docker.network.bridge.enable_ip_masquerade=true --opt com.docker.network.driver.mtu=1500 --label "lucid.network=multi-stage" --label "lucid.subnet=172.25.0.0/16"

# Verify networks
docker network ls | grep lucid
docker network inspect lucid-pi-network | grep -E "Subnet|Gateway"
docker network inspect lucid-distroless-production | grep -E "Subnet|Gateway"
```

### Phase 1B: Directory Structure

```bash
# Create data directories
sudo mkdir -p /mnt/myssd/Lucid/data/{mongodb,redis,elasticsearch}
sudo mkdir -p /mnt/myssd/Lucid/logs/{mongodb,redis,elasticsearch,auth-service,distroless-runtime,minimal-runtime,arm64-runtime,base,minimal-base,arm64-base}

# Set ownership
sudo chown -R pickme:pickme /mnt/myssd/Lucid/data
sudo chown -R pickme:pickme /mnt/myssd/Lucid/logs

# Verify
ls -la /mnt/myssd/Lucid/data/
ls -la /mnt/myssd/Lucid/logs/
```

### Phase 1C: Environment Configuration

**Option 1: If not already generated**

```bash
# Generate secure keys first
cd /mnt/myssd/Lucid/Lucid
chmod +x scripts/config/generate-secure-keys.sh
bash scripts/config/generate-secure-keys.sh

# Generate foundation environment
chmod +x scripts/config/generate-foundation-env.sh
bash scripts/config/generate-foundation-env.sh

# Verify
ls -la configs/environment/.env.foundation
grep -E "MONGODB_PASSWORD|JWT_SECRET_KEY|USER_ID" configs/environment/.env.foundation
```

**Option 2: If already configured**

```bash
# Just verify files exist
ls -la configs/environment/.env.foundation
grep -E "MONGODB_PASSWORD|JWT_SECRET_KEY" configs/environment/.env.foundation
```

### Phase 1D: Pull Docker Images

```bash
# Pull distroless base image (prerequisite)
docker pull pickme/lucid-base:latest-arm64
docker images | grep lucid-base

# Pull foundation service images
docker pull pickme/lucid-mongodb:latest-arm64
docker pull pickme/lucid-redis:latest-arm64
docker pull pickme/lucid-elasticsearch:latest-arm64
docker pull pickme/lucid-auth-service:latest-arm64

# Verify all images
docker images | grep pickme/lucid
```

### Phase 1E: Deploy Distroless Base Infrastructure (PREREQUISITE)

**Step 1: Deploy Distroless Config**

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.foundation \
  -f configs/docker/distroless/distroless-config.yml \
  up -d

# Verify
docker ps | grep -E "lucid-base|lucid-minimal-base|lucid-arm64-base"
```

**Step 2: Deploy Distroless Runtime Config**

```bash
docker-compose \
  --env-file configs/environment/.env.foundation \
  -f configs/docker/distroless/distroless-runtime-config.yml \
  up -d

# Verify
docker ps | grep -E "distroless-runtime|minimal-runtime|arm64-runtime"
```

**Step 3: Deploy Base Docker Compose**

```bash
docker-compose \
  --env-file configs/environment/.env.foundation \
  -f infrastructure/docker/distroless/base/docker-compose.base.yml \
  up -d

# Verify
docker ps | grep lucid-base-container
```

**Step 4: Verify Distroless Base Infrastructure**

```bash
# Check all distroless containers running
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep -E "base|runtime|distroless"

# Verify user is 65532:65532
docker exec lucid-base id
docker exec distroless-runtime id

# Verify no shell (should fail)
docker exec lucid-base sh -c "echo test" 2>&1 | grep "executable file not found"

# Check health
docker ps --filter health=healthy | grep -E "base|runtime"
```

### Phase 1F: Deploy Foundation Services

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.foundation \
  -f configs/docker/docker-compose.foundation.yml \
  up -d

# Verify services starting
docker ps | grep -E "lucid-mongodb|lucid-redis|lucid-elasticsearch|lucid-auth-service"
```

### Phase 1G: Verification & Health Checks

```bash
# Wait for services to initialize (60 seconds)
sleep 60

# Check all containers running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check health status
docker ps --filter health=healthy

# Verify MongoDB
docker exec lucid-mongodb mongosh --eval "db.adminCommand('ping')"

# Verify Redis
docker exec lucid-redis redis-cli ping

# Verify Elasticsearch
curl http://localhost:9200/_cluster/health

# Verify Auth Service
curl http://localhost:8089/health

# Check logs for errors
docker logs lucid-mongodb --tail 50
docker logs lucid-redis --tail 50
docker logs lucid-elasticsearch --tail 50
docker logs lucid-auth-service --tail 50

# Verify distroless compliance
docker exec lucid-auth-service id
docker exec lucid-auth-service sh -c "echo test" 2>&1 | grep "executable file not found"

# Verify volumes mounted
docker inspect lucid-mongodb | grep -A 10 "Mounts"
docker inspect lucid-redis | grep -A 10 "Mounts"
docker inspect lucid-elasticsearch | grep -A 10 "Mounts"

# Check disk usage
df -h /mnt/myssd/Lucid/data/
du -sh /mnt/myssd/Lucid/data/*
```

## Verification Checklist

- [ ] 6 Docker networks created and verified
- [ ] Data directories created with correct permissions
- [ ] Log directories created with correct permissions
- [ ] Environment files generated/verified
- [ ] All images pulled successfully
- [ ] Distroless base infrastructure deployed (3 services)
- [ ] Distroless runtime infrastructure deployed (3 services)
- [ ] Base containers deployed (3 services)
- [ ] MongoDB container running and healthy
- [ ] Redis container running and healthy
- [ ] Elasticsearch container running and healthy
- [ ] Auth Service container running and healthy
- [ ] All services using user 65532:65532
- [ ] No shell access verified on all containers
- [ ] Health checks passing on all services
- [ ] Volumes correctly mounted on all services
- [ ] Network connectivity between services verified

## Rollback Procedure

```bash
# Stop and remove Foundation services
docker-compose -f configs/docker/docker-compose.foundation.yml down

# Stop and remove distroless infrastructure
docker-compose -f configs/docker/distroless/distroless-config.yml down
docker-compose -f configs/docker/distroless/distroless-runtime-config.yml down
docker-compose -f infrastructure/docker/distroless/base/docker-compose.base.yml down

# Remove named volumes (optional, keeps data)
docker volume ls | grep lucid-mongodb-cache
docker volume rm lucid-mongodb-cache lucid-redis-cache lucid-elasticsearch-cache lucid-auth-cache

# Data remains in /mnt/myssd/Lucid/data/ for recovery
```

## Key Files Modified

1. `configs/docker/docker-compose.foundation.yml` - Add volumes
2. `configs/docker/distroless/distroless-runtime-config.yml` - Add volumes
3. `configs/docker/distroless/distroless-config.yml` - Add volumes
4. `infrastructure/docker/distroless/base/docker-compose.base.yml` - Add volumes
5. Verify consistency in `configs/environment/.env.foundation`

## Naming Convention Standards

All naming follows these patterns:

- **Images**: `pickme/lucid-[service]:latest-arm64`
- **Containers**: `lucid-[service]` (e.g., `lucid-mongodb`)
- **Networks**: `lucid-[network-type]` (e.g., `lucid-pi-network`)
- **Volumes (named)**: `lucid-[service]-cache`
- **Volumes (host)**: `/mnt/myssd/Lucid/[type]/[service]`
- **User**: `65532:65532` (distroless standard)
- **Environment variables**: `[SERVICE]_[PROPERTY]` (e.g., `MONGODB_HOST`)