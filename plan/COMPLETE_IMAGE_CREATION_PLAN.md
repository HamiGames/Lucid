# Complete Image Creation Plan for Lucid Project

## Overview

This document provides a comprehensive plan for creating all Docker images referenced in the Lucid project plan documents. All images are built for ARM64 architecture targeting Raspberry Pi 5 deployment.

**Build Environment:** Windows 11 console with Docker Desktop + BuildKit  
**Target Host:** Raspberry Pi 5 (192.168.0.75)  
**Architecture:** linux/arm64 (aarch64)  
**Registry:** Docker Hub (pickme/lucid namespace)  

## Image Creation Categories

### 1. Base Infrastructure Images
### 2. Phase 1: Foundation Services Images  
### 3. Phase 2: Core Services Images
### 4. Phase 3: Application Services Images
### 5. Phase 4: Support Services Images
### 6. Specialized Service Images

---

## 1. Base Infrastructure Images

### 1.1 Python Distroless Base
**File:** `infrastructure/containers/base/Dockerfile.python-base`  
**Image:** `pickme/lucid-base:python-distroless-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Dependencies:** fastapi, uvicorn, pydantic, pymongo, redis, cryptography  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:python-distroless-arm64 \
  -f infrastructure/containers/base/Dockerfile.python-base \
  --push \
  .
```

### 1.2 Java Distroless Base
**File:** `infrastructure/containers/base/Dockerfile.java-base`  
**Image:** `pickme/lucid-base:java-distroless-arm64`  
**Base:** `gcr.io/distroless/java17-debian12:arm64`  
**Dependencies:** OpenJDK 17, minimal runtime  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:java-distroless-arm64 \
  -f infrastructure/containers/base/Dockerfile.java-base \
  --push \
  .
```

### 1.3 Base Distroless Runtime
**File:** `infrastructure/docker/distroless/base/Dockerfile.base`  
**Image:** `pickme/lucid-base:latest-arm64`  
**Base:** `gcr.io/distroless/base-debian12:arm64`  
**Purpose:** Core distroless runtime for all services  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:latest-arm64 \
  -f infrastructure/docker/distroless/base/Dockerfile.base \
  --push \
  .
```

---

## 2. Phase 1: Foundation Services Images

### 2.1 MongoDB Container
**File:** `infrastructure/containers/storage/Dockerfile.mongodb`  
**Image:** `pickme/lucid-mongodb:latest-arm64`  
**Base:** `gcr.io/distroless/base-debian12:arm64`  
**Port:** 27017  
**Configuration:** `mongod.conf`  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-mongodb:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.mongodb \
  --push \
  .
```

### 2.2 Redis Container
**File:** `infrastructure/containers/storage/Dockerfile.redis`  
**Image:** `pickme/lucid-redis:latest-arm64`  
**Base:** `gcr.io/distroless/base-debian12:arm64`  
**Port:** 6379  
**Configuration:** `redis.conf`  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-redis:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.redis \
  --push \
  .
```

### 2.3 Elasticsearch Container
**File:** `infrastructure/containers/storage/Dockerfile.elasticsearch`  
**Image:** `pickme/lucid-elasticsearch:latest-arm64`  
**Base:** `gcr.io/distroless/base-debian12:arm64`  
**Port:** 9200  
**Configuration:** `elasticsearch.yml`  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-elasticsearch:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.elasticsearch \
  --push \
  .
```

### 2.4 Authentication Service
**File:** `auth/Dockerfile`  
**Image:** `pickme/lucid-auth-service:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8089  
**Features:** JWT generation, TRON signature verification, hardware wallet support  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-auth-service:latest-arm64 \
  -f auth/Dockerfile \
  --push \
  .
```

---

## 3. Phase 2: Core Services Images

### 3.1 API Gateway
**File:** `03-api-gateway/Dockerfile`  
**Image:** `pickme/lucid-api-gateway:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8080  
**Features:** Routing, rate limiting, authentication middleware, service discovery  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-api-gateway:latest-arm64 \
  -f 03-api-gateway/Dockerfile \
  --push \
  .
```

### 3.2 Service Mesh Controller
**File:** `service-mesh/Dockerfile`  
**Image:** `pickme/lucid-service-mesh-controller:latest-arm64`  
**Base:** `gcr.io/distroless/base-debian12:arm64`  
**Ports:** 8086 (controller), 8500 (consul)  
**Features:** Service discovery, mTLS, health checking  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-service-mesh-controller:latest-arm64 \
  -f service-mesh/Dockerfile \
  --push \
  .
```

### 3.3 Blockchain Engine
**File:** `blockchain/Dockerfile.engine`  
**Image:** `pickme/lucid-blockchain-engine:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8084  
**Features:** Consensus (PoOT), block creation (10s intervals)  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-blockchain-engine:latest-arm64 \
  -f blockchain/Dockerfile.engine \
  --push \
  .
```

### 3.4 Session Anchoring
**File:** `blockchain/Dockerfile.anchoring`  
**Image:** `pickme/lucid-session-anchoring:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8085  
**Features:** Session manifest anchoring to blockchain  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-session-anchoring:latest-arm64 \
  -f blockchain/Dockerfile.anchoring \
  --push \
  .
```

### 3.5 Block Manager
**File:** `blockchain/Dockerfile.manager`  
**Image:** `pickme/lucid-block-manager:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8086  
**Features:** Block validation and propagation  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-block-manager:latest-arm64 \
  -f blockchain/Dockerfile.manager \
  --push \
  .
```

### 3.6 Data Chain
**File:** `blockchain/Dockerfile.data`  
**Image:** `pickme/lucid-data-chain:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8087  
**Features:** Data storage and retrieval  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-data-chain:latest-arm64 \
  -f blockchain/Dockerfile.data \
  --push \
  .
```

---

## 4. Phase 3: Application Services Images

### 4.1 Session Pipeline
**File:** `sessions/Dockerfile.pipeline`  
**Image:** `pickme/lucid-session-pipeline:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8083  
**Features:** Session recording pipeline management  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-session-pipeline:latest-arm64 \
  -f sessions/Dockerfile.pipeline \
  --push \
  .
```

### 4.2 Session Recorder
**File:** `sessions/Dockerfile.recorder`  
**Image:** `pickme/lucid-session-recorder:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8084  
**Features:** Session recording and chunking  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-session-recorder:latest-arm64 \
  -f sessions/Dockerfile.recorder \
  --push \
  .
```

### 4.3 Session Processor
**File:** `sessions/Dockerfile.processor`  
**Image:** `pickme/lucid-chunk-processor:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8085  
**Features:** Chunk processing and encryption  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-chunk-processor:latest-arm64 \
  -f sessions/Dockerfile.processor \
  --push \
  .
```

### 4.4 Session Storage
**File:** `sessions/Dockerfile.storage`  
**Image:** `pickme/lucid-session-storage:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8086  
**Features:** Session data storage and retrieval  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-session-storage:latest-arm64 \
  -f sessions/Dockerfile.storage \
  --push \
  .
```

### 4.5 Session API
**File:** `sessions/Dockerfile.api`  
**Image:** `pickme/lucid-session-api:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8087  
**Features:** Session management API  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-session-api:latest-arm64 \
  -f sessions/Dockerfile.api \
  --push \
  .
```

### 4.6 RDP Server Manager
**File:** `RDP/Dockerfile.server-manager`  
**Image:** `pickme/lucid-rdp-server-manager:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8090  
**Features:** RDP server lifecycle management  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-rdp-server-manager:latest-arm64 \
  -f RDP/Dockerfile.server-manager \
  --push \
  .
```

### 4.7 RDP XRDP Integration
**File:** `RDP/Dockerfile.xrdp`  
**Image:** `pickme/lucid-rdp-xrdp:latest-arm64`  
**Base:** `gcr.io/distroless/base-debian12:arm64`  
**Ports:** 8091, 3389  
**Features:** XRDP protocol implementation  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-rdp-xrdp:latest-arm64 \
  -f RDP/Dockerfile.xrdp \
  --push \
  .
```

### 4.8 RDP Controller
**File:** `RDP/Dockerfile.controller`  
**Image:** `pickme/lucid-rdp-controller:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8092  
**Features:** RDP session control  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-rdp-controller:latest-arm64 \
  -f RDP/Dockerfile.controller \
  --push \
  .
```

### 4.9 RDP Monitor
**File:** `RDP/Dockerfile.monitor`  
**Image:** `pickme/lucid-rdp-monitor:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8093  
**Features:** RDP resource monitoring  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-rdp-monitor:latest-arm64 \
  -f RDP/Dockerfile.monitor \
  --push \
  .
```

### 4.10 Node Management
**File:** `node/Dockerfile`  
**Image:** `pickme/lucid-node-management:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8095  
**Features:** Node pool management, PoOT calculation, payout threshold (10 USDT), max 100 nodes  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-node-management:latest-arm64 \
  -f node/Dockerfile \
  --push \
  .
```

---

## 5. Phase 4: Support Services Images

### 5.1 Admin Interface
**File:** `admin/Dockerfile`  
**Image:** `pickme/lucid-admin-interface:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8083  
**Features:** Dashboard, monitoring, session administration, blockchain anchoring, payout triggers  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-admin-interface:latest-arm64 \
  -f admin/Dockerfile \
  --push \
  .
```

### 5.2 TRON Client
**File:** `payment-systems/tron/Dockerfile.tron-client`  
**Image:** `pickme/lucid-tron-client:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8091  
**Features:** TRON network integration  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-tron-client:latest-arm64 \
  -f payment-systems/tron/Dockerfile.tron-client \
  --push \
  .
```

### 5.3 TRON Payout Router
**File:** `payment-systems/tron/Dockerfile.payout-router`  
**Image:** `pickme/lucid-payout-router:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8092  
**Features:** TRON payout routing  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-payout-router:latest-arm64 \
  -f payment-systems/tron/Dockerfile.payout-router \
  --push \
  .
```

### 5.4 TRON Wallet Manager
**File:** `payment-systems/tron/Dockerfile.wallet-manager`  
**Image:** `pickme/lucid-wallet-manager:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8093  
**Features:** TRON wallet management  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-wallet-manager:latest-arm64 \
  -f payment-systems/tron/Dockerfile.wallet-manager \
  --push \
  .
```

### 5.5 TRON USDT Manager
**File:** `payment-systems/tron/Dockerfile.usdt-manager`  
**Image:** `pickme/lucid-usdt-manager:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8094  
**Features:** USDT token management  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-usdt-manager:latest-arm64 \
  -f payment-systems/tron/Dockerfile.usdt-manager \
  --push \
  .
```

### 5.6 TRON Staking
**File:** `payment-systems/tron/Dockerfile.trx-staking`  
**Image:** `pickme/lucid-trx-staking:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8096  
**Features:** TRX staking operations  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-trx-staking:latest-arm64 \
  -f payment-systems/tron/Dockerfile.trx-staking \
  --push \
  .
```

### 5.7 TRON Payment Gateway
**File:** `payment-systems/tron/Dockerfile.payment-gateway`  
**Image:** `pickme/lucid-payment-gateway:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8097  
**Features:** TRON payment processing gateway  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-payment-gateway:latest-arm64 \
  -f payment-systems/tron/Dockerfile.payment-gateway \
  --push \
  .
```

---

## 6. Specialized Service Images

### 6.1 GUI Services
**File:** `infrastructure/docker/distroless/gui/Dockerfile.gui`  
**Image:** `pickme/lucid-gui:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 8083  
**Features:** Electron GUI services  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-gui:latest-arm64 \
  -f infrastructure/docker/distroless/gui/Dockerfile.gui \
  --push \
  .
```

### 6.2 RDP Services
**File:** `infrastructure/docker/distroless/rdp/Dockerfile.rdp`  
**Image:** `pickme/lucid-rdp:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Port:** 3389  
**Features:** RDP protocol services  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-rdp:latest-arm64 \
  -f infrastructure/docker/distroless/rdp/Dockerfile.rdp \
  --push \
  .
```

### 6.3 VM Services
**File:** `infrastructure/docker/multi-stage/Dockerfile.vm`  
**Image:** `pickme/lucid-vm:latest-arm64`  
**Base:** `gcr.io/distroless/python3-debian12:arm64`  
**Features:** Virtual machine management  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-vm:latest-arm64 \
  -f infrastructure/docker/multi-stage/Dockerfile.vm \
  --push \
  .
```

### 6.4 Database Services
**File:** `infrastructure/containers/database/Dockerfile.database`  
**Image:** `pickme/lucid-database:latest-arm64`  
**Base:** `gcr.io/distroless/base-debian12:arm64`  
**Features:** Database management services  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-database:latest-arm64 \
  -f infrastructure/containers/database/Dockerfile.database \
  --push \
  .
```

### 6.5 Storage Services
**File:** `infrastructure/containers/storage/Dockerfile.storage`  
**Image:** `pickme/lucid-storage:latest-arm64`  
**Base:** `gcr.io/distroless/base-debian12:arm64`  
**Features:** Storage management services  
**Build Command:**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-storage:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.storage \
  --push \
  .
```

---

## Build Execution Order

### Phase 1: Base Infrastructure (2 hours)
1. Python Distroless Base
2. Java Distroless Base  
3. Base Distroless Runtime

### Phase 2: Foundation Services (1 day)
4. MongoDB Container
5. Redis Container
6. Elasticsearch Container
7. Authentication Service

### Phase 3: Core Services (1 week)
8. API Gateway
9. Service Mesh Controller
10. Blockchain Engine
11. Session Anchoring
12. Block Manager
13. Data Chain

### Phase 4: Application Services (2 days)
14. Session Pipeline
15. Session Recorder
16. Session Processor
17. Session Storage
18. Session API
19. RDP Server Manager
20. RDP XRDP Integration
21. RDP Controller
22. RDP Monitor
23. Node Management

### Phase 5: Support Services (1 day)
24. Admin Interface
25. TRON Client
26. TRON Payout Router
27. TRON Wallet Manager
28. TRON USDT Manager
29. TRON Staking
30. TRON Payment Gateway

### Phase 6: Specialized Services (1 day)
31. GUI Services
32. RDP Services
33. VM Services
34. Database Services
35. Storage Services

---

## Build Script Template

**File:** `scripts/build/build-all-images.sh`

```bash
#!/bin/bash
# Complete image build script for Lucid project

set -e

echo "Starting Lucid image creation process..."

# Phase 1: Base Infrastructure
echo "Phase 1: Building base infrastructure images..."
# [Base image build commands]

# Phase 2: Foundation Services
echo "Phase 2: Building foundation service images..."
# [Foundation service build commands]

# Phase 3: Core Services
echo "Phase 3: Building core service images..."
# [Core service build commands]

# Phase 4: Application Services
echo "Phase 4: Building application service images..."
# [Application service build commands]

# Phase 5: Support Services
echo "Phase 5: Building support service images..."
# [Support service build commands]

# Phase 6: Specialized Services
echo "Phase 6: Building specialized service images..."
# [Specialized service build commands]

echo "All images built and pushed successfully!"
echo "Total images created: 35"
echo "Registry: pickme/lucid namespace on Docker Hub"
echo "Architecture: linux/arm64"
echo "Target: Raspberry Pi 5 deployment"
```

---

## Validation Criteria

### Build Success Criteria
- All 35 images built successfully
- All images pushed to Docker Hub
- All images use distroless base images
- All images target linux/arm64 platform
- All images have proper health checks
- All images use non-root users (65532:65532)
- All images have security hardening applied

### Quality Assurance
- No placeholder values in configurations
- All environment variables properly configured
- All port mappings correctly defined
- All volume mounts properly configured
- All network configurations correct
- All security options applied

### Performance Requirements
- Total combined image size <10GB
- Individual image sizes optimized
- Build times <2 hours per phase
- Memory usage optimized for Pi hardware
- CPU usage optimized for Pi hardware

---

## Security Requirements

### Distroless Compliance
- All images use distroless base images
- No shell access in runtime containers
- No package managers in runtime
- Minimal attack surface
- Non-root user execution

### Security Hardening
- Security options: `no-new-privileges:true`
- Capability dropping: `CAP_DROP=ALL`
- Read-only filesystems where applicable
- Resource limits configured
- Network isolation implemented

### TRON Isolation
- Zero TRON references in blockchain core
- TRON services isolated on separate network
- Payment services properly segmented
- No cross-contamination between services

---

## Troubleshooting

### Common Build Issues
1. **Platform Mismatch**: Ensure `--platform linux/arm64` is specified
2. **Registry Authentication**: Verify Docker Hub credentials
3. **Build Context**: Ensure correct build context paths
4. **Dependency Issues**: Check all required files exist
5. **Memory Issues**: Increase Docker Desktop memory allocation

### Build Optimization
1. **Parallel Builds**: Use buildx for parallel builds
2. **Layer Caching**: Optimize Dockerfile layer ordering
3. **Multi-stage Builds**: Use multi-stage builds for size optimization
4. **Dependency Management**: Minimize dependencies in final images

---

## Next Steps

After successful image creation:

1. **Deploy to Pi**: Use deployment scripts to deploy images to Raspberry Pi
2. **Integration Testing**: Run comprehensive integration tests
3. **Performance Testing**: Validate performance on Pi hardware
4. **Security Scanning**: Run security scans on all images
5. **Documentation**: Update deployment documentation
6. **Monitoring**: Set up monitoring and alerting

---

**Generated:** 2025-01-14  
**Total Images:** 35  
**Build Time Estimate:** 7 days  
**Target Architecture:** ARM64 (linux/arm64)  
**Registry:** Docker Hub (pickme/lucid)  
**Status:** 🚀 READY FOR EXECUTION
