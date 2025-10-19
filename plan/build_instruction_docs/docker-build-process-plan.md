# Docker Build Process Plan

## Build Environment

**Build Host:** Windows 11 console with Docker Desktop + BuildKit

**Target Host:** Raspberry Pi 5 (192.168.0.75) via SSH (user: pickme)

**Platform:** linux/arm64 (aarch64)

**Registry:** Docker Hub (pickme/lucid namespace)

**Timeline:** ~7 weeks total

## Critical Success Factors

- **No Placeholders**: All configurations with real generated values
- **Distroless Compliance**: All containers use distroless base images for security
- **TRON Isolation**: Zero TRON references in blockchain core
- **Pi Target**: All builds for linux/arm64 platform
- **SSH Deployment**: All Pi deployments via SSH

## Pre-Build Phase (~2 hours)

### Step 1: Docker Hub Cleanup

**Script:** `scripts/registry/cleanup-dockerhub.sh`

Actions:

- Authenticate to Docker Hub (pickme account)
- List all existing pickme/lucid repositories
- Clean local Docker cache (`docker system prune -a -f`)
- Clean buildx cache (`docker builder prune -a -f`)
- Verify no lucid images remain

Validation: `docker search pickme/lucid` returns no results

### Step 2: Environment Configuration Generation

**Script:** `scripts/config/generate-all-env.sh`

Generate 6 environment files in `configs/environment/`:

- `.env.pi-build` - Raspberry Pi target configuration
- `.env.foundation` - Phase 1 database/auth configs
- `.env.core` - Phase 2 gateway/blockchain configs
- `.env.application` - Phase 3 session/RDP/node configs
- `.env.support` - Phase 4 admin/TRON configs
- `.env.gui` - Electron GUI integration configs

Generate secure values using `openssl rand -base64`:

- MONGODB_PASSWORD (32 bytes)
- REDIS_PASSWORD (32 bytes)
- JWT_SECRET (64 bytes)
- ENCRYPTION_KEY (32 bytes)
- TOR_PASSWORD (32 bytes)

Validation: Grep for `${` placeholders - must return zero matches

### Step 3: Build Environment Validation

**Script:** `scripts/foundation/validate-build-environment.sh`

Validate:

- Docker Desktop running on Windows 11
- Docker Compose v2 available
- Docker BuildKit enabled (`docker buildx version`)
- SSH connection to Pi (pickme@192.168.0.75)
- Pi disk space >20GB free
- Pi architecture = aarch64
- Docker daemon running on Pi
- Network connectivity (ping 192.168.0.75)
- Base images accessible (python:3.11-slim, gcr.io/distroless/python3-debian12:arm64)

### Step 4: Distroless Base Images

**Directory:** `infrastructure/containers/base/`

**Script:** `infrastructure/containers/base/build-base-images.sh`

Build 2 base images:

1. **Python Distroless Base** (`pickme/lucid-base:python-distroless-arm64`)

   - Stage 1: python:3.11-slim builder with dependencies
   - Stage 2: gcr.io/distroless/python3-debian12:arm64 runtime
   - Includes: fastapi, uvicorn, pydantic, pymongo, redis, cryptography

2. **Java Distroless Base** (`pickme/lucid-base:java-distroless-arm64`)

   - Stage 1: openjdk:17-jdk-slim builder
   - Stage 2: gcr.io/distroless/java17-debian12:arm64 runtime

Build command template:

```bash
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-base:python-distroless-arm64 \
  -f Dockerfile.python-base \
  --push .
```

Validation: `docker manifest inspect` confirms ARM64 images exist

---

## Phase 1: Foundation Services (~1 week)

**Dependencies:** Pre-Build Phase completed

**Network:** lucid-pi-network (bridge, 172.20.0.0/16)

### Step 5: Storage Database Containers (Group A - Parallel)

**Directory:** `infrastructure/containers/storage/`

**Script:** `infrastructure/containers/storage/build-storage-containers.sh`

Build 3 containers:

1. **MongoDB** (`pickme/lucid-mongodb:latest-arm64`)

   - Base: mongo:7.0 → gcr.io/distroless/base-debian12:arm64
   - Port: 27017
   - Config: `mongod.conf` (replication, auth, 1GB cache)

2. **Redis** (`pickme/lucid-redis:latest-arm64`)

   - Base: redis:7.2-alpine → gcr.io/distroless/base-debian12:arm64
   - Port: 6379
   - Config: `redis.conf` (persistence, 1GB maxmemory)

3. **Elasticsearch** (`pickme/lucid-elasticsearch:latest-arm64`)

   - Base: elasticsearch:8.11.0 → gcr.io/distroless/base-debian12:arm64
   - Port: 9200
   - Config: `elasticsearch.yml` (single-node, 1GB heap)

### Step 6: Authentication Service Container (Group A - Parallel)

**Directory:** `auth/`

**Script:** `auth/build-auth-service.sh`

Build auth service (`pickme/lucid-auth-service:latest-arm64`):

- Base: python:3.11-slim → gcr.io/distroless/python3-debian12:arm64
- Port: 8089
- Features: JWT generation, TRON signature verification, hardware wallet support
- Dependencies: fastapi, PyJWT, tronweb, pymongo, redis

### Step 7: Phase 1 Docker Compose

**File:** `configs/docker/docker-compose.foundation.yml`

Define services:

- lucid-mongodb (depends: none)
- lucid-redis (depends: none)
- lucid-elasticsearch (depends: none)
- lucid-auth-service (depends: mongodb, redis)

Include health checks, volumes, and environment variable references.

### Step 8: Phase 1 Deployment

**Script:** `scripts/deployment/deploy-phase1-pi.sh`

Actions:

- Create /opt/lucid/production on Pi
- Copy compose file and .env.foundation to Pi
- Pull ARM64 images on Pi
- Deploy with `docker-compose up -d`
- Wait 90s for health checks
- Initialize MongoDB replica set
- Create Elasticsearch index

### Step 9: Phase 1 Integration Tests

**Script:** `tests/integration/phase1/run_phase1_tests.sh`

**Tests:** `tests/integration/phase1/test_phase1_integration.py`

Test:

- MongoDB connection and query performance (<10ms)
- Redis caching operations
- Elasticsearch indexing and search
- Auth service login/logout flow
- JWT token generation
- Cross-service communication

---

## Phase 2: Core Services (~1 week)

**Dependencies:** Phase 1 completed

**Network:** Extends lucid-pi-network

### Step 10: API Gateway Container (Group B - Parallel)

**Directory:** `03-api-gateway/`

**Script:** `03-api-gateway/build-api-gateway.sh`

Build API Gateway (`pickme/lucid-api-gateway:latest-arm64`):

- Base: python:3.11-slim → gcr.io/distroless/python3-debian12:arm64
- Port: 8080
- Features: Routing, rate limiting, authentication middleware, service discovery
- Dependencies: fastapi, slowapi, consul, httpx

### Step 11: Service Mesh Controller (Group B - Parallel)

**Directory:** `service-mesh/`

**Script:** `service-mesh/build-service-mesh.sh`

Build Service Mesh (`pickme/lucid-service-mesh-controller:latest-arm64`):

- Base: python:3.11-slim + Consul + Envoy → gcr.io/distroless/base-debian12:arm64
- Ports: 8086 (controller), 8500 (consul)
- Features: Service discovery, mTLS, health checking

### Step 12: Blockchain Core Containers (Group C - Parallel)

**Directory:** `blockchain/`

**Script:** `blockchain/build-blockchain-containers.sh`

**CRITICAL: TRON Isolation Verification**

Before build, scan for TRON references:

```bash
grep -r "tron" blockchain/ --exclude-dir=node_modules
grep -r "TronWeb" blockchain/
grep -r "payment" blockchain/core/
# Expected: Zero matches
```

Build 4 blockchain containers:

1. **Blockchain Engine** (`pickme/lucid-blockchain-engine:latest-arm64`)

   - Port: 8084
   - Features: Consensus (PoOT), block creation (10s intervals)

2. **Session Anchoring** (`pickme/lucid-session-anchoring:latest-arm64`)

   - Port: 8085
   - Features: Session manifest anchoring to blockchain

3. **Block Manager** (`pickme/lucid-block-manager:latest-arm64`)

   - Port: 8086
   - Features: Block validation and propagation

4. **Data Chain** (`pickme/lucid-data-chain:latest-arm64`)

   - Port: 8087
   - Features: Data storage and retrieval

All use multi-stage build: python:3.11-slim → gcr.io/distroless/python3-debian12:arm64

### Step 13: Phase 2 Docker Compose

**File:** `configs/docker/docker-compose.core.yml`

Define services with dependencies:

- lucid-service-mesh-controller (depends: none)
- lucid-api-gateway (depends: auth-service, service-mesh)
- lucid-blockchain-engine (depends: mongodb, redis)
- lucid-session-anchoring (depends: blockchain-engine)
- lucid-block-manager (depends: blockchain-engine)
- lucid-data-chain (depends: mongodb, redis)

Network: `lucid-pi-network` (external: true)

### Step 14: Phase 2 Deployment

**Script:** `scripts/deployment/deploy-phase2-pi.sh`

Actions:

- Copy compose and .env.core to Pi
- Deploy with both foundation and core compose files
- Wait 60s for service mesh registration
- Verify blockchain creating blocks
- Check all services healthy

### Step 15: Phase 2 Integration Tests

**Script:** `tests/integration/phase2/run_phase2_tests.sh`

Test:

- API Gateway → Auth Service flow
- API Gateway → Blockchain proxy
- Blockchain consensus mechanism
- Session anchoring to blockchain
- Service mesh communication (gRPC)
- Rate limiting enforcement

### Step 16: TRON Isolation Security Scan

**Script:** `scripts/verification/verify-tron-isolation.sh`

Scan for TRON violations:

- No "tron" references in blockchain/
- No "TronWeb" references
- No "payment" in blockchain/core/
- No "USDT" or "TRX" references
- Verify payment-systems/tron/ exists and isolated
- Verify no blockchain references in payment-systems/tron/

Exit 1 if any violations found.

### Step 17: Phase 2 Performance Benchmarks

**Script:** `tests/performance/phase2/run_phase2_performance.sh`

Benchmark:

- API Gateway throughput: >500 req/s sustained
- Blockchain block creation: 1 block per 10 seconds
- Database queries: <10ms p95 latency
- Service mesh overhead: <5ms added latency

---

## Phase 3: Application Services (~2 weeks)

**Dependencies:** Phase 2 completed

### Step 18-20: Session Management Containers

Build 5 session management containers:

1. Session Pipeline (`pickme/lucid-session-pipeline:latest-arm64`)
2. Session Recorder (`pickme/lucid-session-recorder:latest-arm64`)
3. Chunk Processor (`pickme/lucid-chunk-processor:latest-arm64`)
4. Session Storage (`pickme/lucid-session-storage:latest-arm64`)
5. Session API (`pickme/lucid-session-api:latest-arm64` - Port 8087)

Features: Recording, chunking, encryption, Merkle tree building, manifest creation

### Step 21-22: RDP Services Containers

Build 4 RDP service containers:

1. RDP Server Manager (`pickme/lucid-rdp-server-manager:latest-arm64` - Port 8081)
2. XRDP Integration (`pickme/lucid-xrdp-integration:latest-arm64` - Port 3389)
3. Session Controller (`pickme/lucid-session-controller:latest-arm64` - Port 8082)
4. Resource Monitor (`pickme/lucid-resource-monitor:latest-arm64` - Port 8090)

Features: XRDP lifecycle management, session control, resource monitoring

### Step 23: Node Management Container

Build node management (`pickme/lucid-node-management:latest-arm64`):

- Port: 8095
- Features: Node pool management, PoOT calculation, payout threshold (10 USDT), max 100 nodes

### Step 24: Phase 3 Docker Compose

**File:** `configs/docker/docker-compose.application.yml`

Define all session, RDP, and node services with proper dependencies.

### Step 25: Phase 3 Deployment

Deploy to Pi with foundation + core + application compose files.

### Step 26: Phase 3 Integration Tests

Test session recording pipeline, RDP session lifecycle, node registration.

### Step 27: Phase 3 Performance Tests

Test chunk processing throughput, RDP connection latency, node pool management.

---

## Phase 4: Support Services (~1 week)

**Dependencies:** Phase 3 completed

### Step 28: Admin Interface Container

Build admin interface (`pickme/lucid-admin-interface:latest-arm64`):

- Port: 8083
- Features: Dashboard, monitoring, session administration, blockchain anchoring, payout triggers

### Step 29-30: TRON Payment Containers (ISOLATED)

**CRITICAL: Separate isolated network**

Build 6 TRON payment containers on `lucid-tron-isolated` network:

1. TRON Client (`pickme/lucid-tron-client:latest-arm64` - Port 8091)
2. Payout Router (`pickme/lucid-payout-router:latest-arm64` - Port 8092)
3. Wallet Manager (`pickme/lucid-wallet-manager:latest-arm64` - Port 8093)
4. USDT Manager (`pickme/lucid-usdt-manager:latest-arm64` - Port 8094)
5. TRX Staking (`pickme/lucid-trx-staking:latest-arm64` - Port 8096)
6. Payment Gateway (`pickme/lucid-payment-gateway:latest-arm64` - Port 8097)

Configuration:

- TRON_NETWORK=mainnet
- TRON_API_URL=https://api.trongrid.io
- USDT_TRC20_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
- Minimum payout: 10 USDT

### Step 31: Phase 4 Docker Compose

**File:** `configs/docker/docker-compose.support.yml`

Define admin and TRON services with:

- Admin on lucid-pi-network
- TRON services on lucid-tron-isolated network
- Payment Gateway as bridge between networks

### Step 32: Phase 4 Deployment

Deploy with all 4 compose files (foundation + core + application + support).

### Step 33: Phase 4 Integration Tests

Test admin dashboard, TRON payout flow (isolated), payment routing.

### Step 34: Final System Integration Test

Test complete system end-to-end:

- User authentication
- RDP session creation
- Session recording and chunking
- Blockchain anchoring
- Payout calculation and distribution

### Step 35: Master Docker Compose

**File:** `configs/docker/docker-compose.master.yml`

Consolidate all services into single master compose file for production deployment.

---

## Build Execution Order

**Sequential phases:**

1. Pre-Build → Phase 1 → Phase 2 → Phase 3 → Phase 4

**Parallel within phases:**

- Pre-Build: All sequential
- Phase 1: Steps 5-6 parallel (Group A)
- Phase 2: Steps 10-11 parallel (Group B), Step 12 parallel (Group C)
- Phase 3: Session containers parallel, RDP containers parallel
- Phase 4: TRON containers parallel

## Key File Paths

**Scripts:**

- `scripts/registry/cleanup-dockerhub.sh`
- `scripts/config/generate-all-env.sh`
- `scripts/foundation/validate-build-environment.sh`
- `infrastructure/containers/base/build-base-images.sh`
- `scripts/deployment/deploy-phase{1-4}-pi.sh`
- `scripts/verification/verify-tron-isolation.sh`

**Configs:**

- `configs/environment/.env.{pi-build,foundation,core,application,support,gui}`
- `configs/docker/docker-compose.{foundation,core,application,support,master}.yml`

**Container Sources:**

- `infrastructure/containers/{base,storage}/`
- `auth/`, `03-api-gateway/`, `service-mesh/`, `blockchain/`
- Session/RDP/Node/Admin/TRON service directories

## Validation Gates

Each phase requires:

1. All containers built and pushed to Docker Hub
2. Compose file syntax validated
3. Deployment successful on Pi
4. Integration tests passing
5. Health checks green for all services

Phase 2 additional: TRON isolation scan passes

Phase 4 additional: Final system integration test passes

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| Build fails | Check BuildKit enabled, platform=linux/arm64 |
| Push fails | Verify Docker Hub authentication |
| SSH fails | Check network, SSH keys, Pi accessibility |
| Service unhealthy | Check logs, environment variables, dependencies |
| TRON violation | Remove all TRON refs from blockchain core |
| Performance issues | Optimize for Pi hardware, check resource limits |

### To-dos

- [ ] Complete Pre-Build Phase: Docker Hub cleanup, environment generation, validation, base images
- [ ] Build Phase 1 Foundation Services: MongoDB, Redis, Elasticsearch, Auth containers
- [ ] Deploy and test Phase 1 services on Raspberry Pi
- [ ] Build Phase 2 Gateway and Service Mesh containers (parallel Group B)
- [ ] Build Phase 2 Blockchain Core containers with TRON isolation verification (parallel Group C)
- [ ] Deploy Phase 2, run integration tests and TRON isolation scan
- [ ] Build Phase 3 Application Services: Session Management, RDP Services, Node Management
- [ ] Deploy and test Phase 3 services on Pi
- [ ] Build Phase 4 Support Services: Admin Interface and TRON Payment containers (isolated)
- [ ] Deploy Phase 4, run final system integration tests, generate master compose file
