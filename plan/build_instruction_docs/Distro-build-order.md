# Distroless Build Order and Deployment Commands

## Overview

This document provides a comprehensive guide for deploying the Lucid project using distroless containers on Raspberry Pi 5. All commands are designed for production, testing, and development environments with proper distroless compliance.

## Prerequisites

- **Target Host**: Raspberry Pi 5 (192.168.0.75)
- **SSH Access**: `ssh pickme@192.168.0.75`
- **Project Root**: `/mnt/myssd/Lucid/Lucid`
- **Architecture**: ARM64 (linux/arm64)
- **Registry**: Docker Hub (pickme/lucid namespace)

## Phase 1: Network Infrastructure Setup

### Create 6 Docker Networks

```bash
# SSH to Pi
ssh pickme@192.168.0.75
cd /mnt/myssd/Lucid/Lucid

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

# Verify networks
docker network ls | grep lucid
```

## Phase 2: Environment Configuration

### Generate Environment Files

```bash
# Generate all environment files
bash scripts/config/generate-all-env-complete.sh

# Verify files exist
ls -la configs/environment/.env.*
```

### Create Distroless Environment File

```bash
# Create distroless-specific environment
cp configs/docker/distroless/production.env configs/environment/.env.distroless

# Update with secure values from foundation
source configs/environment/.env.foundation
sed -i "s|mongodb://lucid:lucid@|mongodb://lucid:${MONGODB_PASSWORD}@|g" configs/environment/.env.distroless
sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${ENCRYPTION_KEY}|g" configs/environment/.env.distroless
sed -i "s|JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|g" configs/environment/.env.distroless
```

## Phase 3: Distroless Base Infrastructure (CRITICAL PREREQUISITE)

**⚠️ IMPORTANT**: All distroless base infrastructure must be deployed BEFORE any Lucid services.

### Step 3.1: Deploy Distroless Config

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-config.yml \
  up -d

# Verify
docker ps | grep -E "base|minimal-base|arm64-base"
```

### Step 3.2: Deploy Distroless Runtime Configuration

```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-runtime-config.yml \
  up -d

# Verify
docker ps | grep runtime
```

### Step 3.3: Deploy Distroless Build Configuration

```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-build-config.yml \
  up -d

# Verify
docker ps | grep -E "builder|scanner|optimizer"
```

### Step 3.4: Deploy Base Docker Compose

```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  -f infrastructure/docker/distroless/base/docker-compose.base.yml \
  up -d

# Verify
docker ps | grep lucid-base
```

### Step 3.5: Deploy Development Configuration (Optional)

```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-development-config.yml \
  up -d

# Verify
docker ps | grep dev-
```

### Step 3.6: Deploy Security Configuration (Production)

```bash
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-security-config.yml \
  up -d

# Verify
docker ps | grep secure
```

### Step 3.7: Verify All Distroless Base Infrastructure

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

## Phase 4: Lucid Service Clusters Deployment

### Cluster 1: Foundation Services (Phase 1)

```bash
cd /mnt/myssd/Lucid/Lucid

docker-compose \
  --env-file configs/environment/.env.foundation \
  -f configs/docker/docker-compose.foundation.yml \
  up -d

# Verify
docker ps | grep -E "lucid-mongodb|lucid-redis|lucid-elasticsearch|lucid-auth-service"
curl http://localhost:8089/health
docker exec lucid-mongodb mongosh --eval "db.adminCommand('ping')"
docker exec lucid-redis redis-cli ping
```

### Cluster 2: Core Services (Phase 2)

```bash
docker-compose \
  --env-file configs/environment/.env.core \
  -f configs/docker/docker-compose.core.yml \
  up -d

# Verify
docker ps | grep -E "api-gateway|blockchain-engine|service-mesh"
curl http://localhost:8080/health
curl http://localhost:8084/health
curl http://localhost:8500/health
```

### Cluster 3: Application Services (Phase 3)

```bash
docker-compose \
  --env-file configs/environment/.env.application \
  -f configs/docker/docker-compose.application.yml \
  up -d

# Verify
docker ps | grep -E "session|rdp|node-management"
curl http://localhost:8087/health
curl http://localhost:8095/health
```

### Cluster 4: Support Services (Phase 4)

```bash
docker-compose \
  --env-file configs/environment/.env.support \
  -f configs/docker/docker-compose.support.yml \
  up -d

# Verify
docker ps | grep -E "admin-interface|tron"
curl http://localhost:8083/health
curl http://localhost:8091/health
docker network inspect lucid-tron-isolated | grep tron
```

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

## Individual Docker Compose Deployments

### Production Environment

```bash
# Foundation Services
docker-compose \
  --env-file configs/environment/.env.foundation \
  -f configs/docker/docker-compose.foundation.yml \
  up -d

# Core Services
docker-compose \
  --env-file configs/environment/.env.core \
  -f configs/docker/docker-compose.core.yml \
  up -d

# Application Services
docker-compose \
  --env-file configs/environment/.env.application \
  -f configs/docker/docker-compose.application.yml \
  up -d

# Support Services
docker-compose \
  --env-file configs/environment/.env.support \
  -f configs/docker/docker-compose.support.yml \
  up -d
```

### Development Environment

```bash
# Development distroless configuration
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/distroless-development-config.yml \
  up -d

# Development services with debug mode
docker-compose \
  --env-file configs/environment/.env.foundation \
  -f configs/docker/docker-compose.foundation.yml \
  up -d
```

### Testing Environment

```bash
# Test runtime configuration
docker-compose \
  --env-file configs/environment/.env.distroless \
  --env-file configs/docker/distroless/distroless.env \
  -f configs/docker/distroless/test-runtime-config.yml \
  up -d

# Run integration tests
bash tests/integration/run-all-tests.sh
```

## Distroless Configuration Files

### Core Distroless Files:
- `configs/docker/distroless/distroless-config.yml`
- `configs/docker/distroless/distroless-runtime-config.yml`
- `configs/docker/distroless/distroless-build-config.yml`
- `configs/docker/distroless/distroless-development-config.yml`
- `configs/docker/distroless/distroless-security-config.yml`
- `configs/docker/distroless/test-runtime-config.yml`
- `infrastructure/docker/distroless/base/docker-compose.base.yml`

### Service Cluster Files:
- `configs/docker/docker-compose.foundation.yml`
- `configs/docker/docker-compose.core.yml`
- `configs/docker/docker-compose.application.yml`
- `configs/docker/docker-compose.support.yml`

### Environment Files:
- `configs/environment/.env.foundation`
- `configs/environment/.env.core`
- `configs/environment/.env.application`
- `configs/environment/.env.support`
- `configs/environment/.env.distroless`
- `configs/docker/distroless/distroless.env`

## Key Distroless Requirements

### Base Images
- **Python Services**: `gcr.io/distroless/python3-debian12:arm64`
- **Java Services**: `gcr.io/distroless/java17-debian12:arm64`
- **Base Services**: `gcr.io/distroless/base-debian12:arm64`

### Security Configuration
- **User**: `65532:65532` (distroless standard)
- **Security Options**: `no-new-privileges:true`, `seccomp:unconfined`
- **Capabilities**: `CAP_DROP=ALL`, `CAP_ADD=NET_BIND_SERVICE`
- **Read-only**: `read_only: true` (where applicable)
- **Tmpfs**: Configured for `/tmp` with security options

### Health Checks
- **Python-based**: `python3 -c "import sys; sys.exit(0)"`
- **HTTP-based**: `curl -f http://localhost:PORT/health`
- **Database**: `mongosh --eval "db.adminCommand('ping')"`

## Deployment Order Summary

1. **Networks** (6 networks) - Phase 1
2. **Environment** (.env files generation) - Phase 2
3. **Distroless Base Infrastructure** (CRITICAL PREREQUISITE) - Phase 3
   - distroless-config.yml
   - distroless-runtime-config.yml
   - distroless-build-config.yml
   - docker-compose.base.yml
   - distroless-development-config.yml (optional)
   - distroless-security-config.yml (production)
4. **Foundation Cluster** (MongoDB, Redis, Elasticsearch, Auth) - Phase 4.1
5. **Core Cluster** (API Gateway, Blockchain, Service Mesh) - Phase 4.2
6. **Application Cluster** (Sessions, RDP, Node Management) - Phase 4.3
7. **Support Cluster** (Admin, TRON Payments) - Phase 4.4
8. **Verification** (Health checks, compliance tests) - Phase 5

## Troubleshooting

### Common Issues

```bash
# Check container logs
docker logs [container-name] --tail=50

# Verify network connectivity
docker network inspect lucid-pi-network

# Check environment variables
docker exec [container-name] env | grep -E "MONGODB|REDIS|JWT"

# Verify distroless compliance
docker exec [container-name] id
docker exec [container-name] sh -c "echo test" 2>&1 | grep "executable file not found"
```

### Rollback Procedures

```bash
# Stop specific cluster
docker-compose -f configs/docker/docker-compose.foundation.yml down

# Stop all services
docker-compose -f configs/docker/docker-compose.foundation.yml down
docker-compose -f configs/docker/docker-compose.core.yml down
docker-compose -f configs/docker/docker-compose.application.yml down
docker-compose -f configs/docker/docker-compose.support.yml down

# Stop distroless infrastructure
docker-compose -f configs/docker/distroless/distroless-config.yml down
docker-compose -f configs/docker/distroless/distroless-runtime-config.yml down
```

## Success Criteria

- ✅ All 6 networks created and verified
- ✅ All environment files generated with secure values
- ✅ All distroless base infrastructure deployed and healthy
- ✅ All 4 service clusters deployed and healthy
- ✅ All services using user 65532:65532
- ✅ No shell access verified on all containers
- ✅ Health checks passing on all services
- ✅ Network connectivity verified between all services
- ✅ Distroless compliance verified on all containers

---

**Generated**: 2025-01-14  
**Target**: Raspberry Pi 5 (192.168.0.75)  
**Architecture**: ARM64 (linux/arm64)  
**Deployment Type**: Distroless Containers  
**Status**: 🚀 READY FOR DEPLOYMENT
