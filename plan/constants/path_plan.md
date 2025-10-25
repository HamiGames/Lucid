## this document is for the pi-side deploymet paths

*Root Project Path:*
  - PROJECT=/mnt/myssd/Lucid/Lucid/
*ROOT scripts path:*
 - /mnt/myssd/Lucid/Lucid/scripts/*/
 
**ALL env documents steam:**
- ENV_DIR=/mnt/myssd/Lucid/Lucid/configs/environment/

 **Total Images**: 35  
**Target Architecture**: linux/arm64  
**Registry**: Docker Hub (pickme/lucid namespace)

---
*Image names*
## 📋 **PHASE 1: BASE INFRASTRUCTURE (3 images)**
1. pickme/lucid-base:python-distroless-arm64
2. pickme/lucid-base:java-distroless-arm64
3. pickme/lucid-base:latest-arm64

## 📋 **PHASE 2: FOUNDATION SERVICES (4 images)**
4. pickme/lucid-mongodb:latest-arm64
5. pickme/lucid-redis:latest-arm64
6. pickme/lucid-elasticsearch:latest-arm64
7. pickme/lucid-auth-service:latest-arm64

## 📋 **PHASE 3: CORE SERVICES (6 images)**
8. pickme/lucid-api-gateway:latest-arm64
9. pickme/lucid-service-mesh-controller:latest-arm64
10. pickme/lucid-blockchain-engine:latest-arm64
11. pickme/lucid-session-anchoring:latest-arm64
12. pickme/lucid-block-manager:latest-arm64
13. pickme/lucid-data-chain:latest-arm64

## 📋 **PHASE 4: APPLICATION SERVICES (10 images)**
14. pickme/lucid-session-pipeline:latest-arm64
15. pickme/lucid-session-recorder:latest-arm64
16. pickme/lucid-chunk-processor:latest-arm64
17. pickme/lucid-session-storage:latest-arm64
18. pickme/lucid-session-api:latest-arm64
19. pickme/lucid-rdp-server-manager:latest-arm64
20. pickme/lucid-rdp-xrdp:latest-arm64
21. pickme/lucid-rdp-controller:latest-arm64
22. pickme/lucid-rdp-monitor:latest-arm64
23. pickme/lucid-node-management:latest-arm64

## 📋 **PHASE 5: SUPPORT SERVICES (7 images)**
24. pickme/lucid-admin-interface:latest-arm64
25. pickme/lucid-tron-client:latest-arm64
26. pickme/lucid-payout-router:latest-arm64
27. pickme/lucid-wallet-manager:latest-arm64
28. pickme/lucid-usdt-manager:latest-arm64
29. pickme/lucid-trx-staking:latest-arm64
30. pickme/lucid-payment-gateway:latest-arm64

## 📋 **PHASE 6: SPECIALIZED SERVICES (5 images)**
31. pickme/lucid-gui:latest-arm64
32. pickme/lucid-rdp:latest-arm64
33. pickme/lucid-vm:latest-arm64
34. pickme/lucid-database:latest-arm64
35. pickme/lucid-storage:latest-arm64

*Ports used in API systems:*
**API Gateway & Core Services**
 - 8080: API Gateway (HTTP)
 - 8081: API Gateway (HTTPS) / RDP Server Manager
 - 8082 Session Controller / Storage Database
 - 8083: Admin Interface
 - 8084: Blockchain Engine
 - 8085: Session Anchoring / TRON Payment (isolated)
 - 8086: Block Manager
 - 8087: Data Chain / Session Management
 - 8088: Admin Interface (staging)
 - 8089: Auth Service

**Session Management & RDP Services**
 - 8090: Resource Monitor / RDP Server Manager
 - 8091: TRON Client
 - 8092: Payout Router / Session Controller
 - 8093: - Wallet Manager / Resource Monitor
 - 8094:- USDT Manager
 - 8095: - TRX Staking / Node Management
 - 8096: Payment Gateway / Admin Interface (isolated)
 - 8097: (Reserved for future use)
 - 8098: (Reserved for future use)
 - 8099: Node Management (staging)

**Extended Ports (8100-8107)**
 - 8100: Admin Interface (monitoring)
 - 8101-8106: TRON Payment services (monitoring)
 - 8107: Service Mesh (monitoring)

*Database & Infrastructure Ports*
**Database Services**
 - 27017: MongoDB (primary)
 - 27018: MongoDB (RDP services)
 - 6379: Redis (primary)
 - 6380: Redis (RDP services)
 - 9200: Elasticsearch (HTTP)
 - 9300: Elasticsearch (transport)
**Monitoring & Management**
 - 3000: Grafana
 - 8500: Consul (service discovery)
 - 8501: Consul (HTTPS)
 - 8502: Consul (gRPC)
 - 8600: Consul (DNS)
 - 8601: Consul (DNS admin)
 - 9090: Prometheus
**Development & Testing**
 - 8000:  Base application port
 - 8443:  HTTPS alternative
 - 15000:  Envoy admin
 - 15001: Envoy proxy
**External Service Ports**
 - 3389: XRDP Integration (RDP protocol)

*Port Allocation Summary by Service Category*
**Phase 1: Foundation Services**
 - MongoDB: 27017
 - Redis: 6379
 - Elasticsearch: 9200
 - Auth Service: 8089
**Phase 2: Core Services**
 - API Gateway: 8080/8081
 - Blockchain Engine: 8084
 - Session Anchoring: 8085
 - Block Manager: 8086
 - Data Chain: 8087
 - Service Mesh Controller: 8500
**Phase 3: Application Services**
 - Session Management: 8083-8087
 - RDP Services: 8090-8093
 - Node Management: 8095
**Phase 4: Support Services**
 - Admin Interface: 8083
 - TRON Payment Services: 8091-8096
 - Monitoring: 3000, 9090
**Port Ranges by Function:**
 - 8080-8089: Core application services
 - 8090-8099: Application and RDP services
 - 8100-8107: Monitoring and extended services
 - 27017: MongoDB databases
 - 6379: Redis caches
 - 9200: Elasticsearch
 - 3000: Grafana monitoring
 - 8500: Consul service discovery
 - 9090: Prometheus monitoring
 - 3389: RDP protocol

*Named Global Values*
**System Configuration**
 - PROJECT_NAME=Lucid
 - PROJECT_VERSION=0.1.0
 - ENVIRONMENT=production
 - DEBUG=false
 - LOG_LEVEL=INFO
 - PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
 - PI_USER=pickme
 - PI_HOST=192.168.0.75

**Network Configuration**
 - LUCID_PI_NETWORK=lucid-pi-network
 - LUCID_PI_SUBNET=172.20.0.0/16
 - LUCID_PI_GATEWAY=172.20.0.1
 - LUCID_TRON_ISOLATED=lucid-tron-isolated
 - LUCID_TRON_SUBNET=172.21.0.0/16
 - LUCID_TRON_GATEWAY=172.21.0.1
 - LUCID_GUI_NETWORK=lucid-gui-network
 - LUCID_GUI_SUBNET=172.22.0.0/16
 - LUCID_GUI_GATEWAY=172.22.0.1
 - LUCID_DISTROLESS_PRODUCTION=lucid-distroless-production
 - LUCID_DISTROLESS_PROD_SUBNET=172.23.0.0/16
 - LUCID_DISTROLESS_PROD_GATEWAY=172.23.0.1
 - LUCID_DISTROLESS_DEV=lucid-distroless-dev
 - LUCID_DISTROLESS_DEV_SUBNET=172.24.0.0/16
 - LUCID_DISTROLESS_DEV_GATEWAY=172.24.0.1
 - LUCID_MULTI_STAGE_NETWORK=lucid-multi-stage-network
 - LUCID_MULTI_STAGE_SUBNET=172.25.0.0/16
 - LUCID_MULTI_STAGE_GATEWAY=172.25.0.1

**Service IP Addresses**
 - API_GATEWAY_HOST=172.20.0.10
 - MONGODB_HOST=172.20.0.11
 - REDIS_HOST=172.20.0.12
 - ELASTICSEARCH_HOST=172.20.0.13
 - AUTH_SERVICE_HOST=172.20.0.14
 - BLOCKCHAIN_ENGINE_HOST=172.20.0.15
 - SESSION_ANCHORING_HOST=172.20.0.16
 - BLOCK_MANAGER_HOST=172.20.0.17
 - DATA_CHAIN_HOST=172.20.0.18
 - SERVICE_MESH_CONTROLLER_HOST=172.20.0.19
 - SESSION_API_HOST=172.20.0.20
 - RDP_SERVER_MANAGER_HOST=172.20.0.21
 - XRDP_INTEGRATION_HOST=172.20.0.22
 - SESSION_CONTROLLER_HOST=172.20.0.23
 - RESOURCE_MONITOR_HOST=172.20.0.24
 - NODE_MANAGEMENT_HOST=172.20.0.25
 - ADMIN_INTERFACE_HOST=172.20.0.26
 - TRON_CLIENT_HOST=172.20.0.27
 - TRON_PAYOUT_ROUTER_HOST=172.20.0.28
 - TRON_WALLET_MANAGER_HOST=172.20.0.29
 - TRON_USDT_MANAGER_HOST=172.20.0.30
 - TRON_STAKING_HOST=172.20.0.31
 - TRON_PAYMENT_GATEWAY_HOST=172.20.0.32

**Port Configuration**
 - API_GATEWAY_PORT=8080
 - MONGODB_PORT=27017
 - REDIS_PORT=6379
 - ELASTICSEARCH_HTTP_PORT=9200
 - ELASTICSEARCH_TRANSPORT_PORT=9300
 - AUTH_SERVICE_PORT=8089
 - BLOCKCHAIN_ENGINE_PORT=8084
 - SESSION_ANCHORING_PORT=8085
 - BLOCK_MANAGER_PORT=8086
 - DATA_CHAIN_PORT=8087
 - SERVICE_MESH_CONTROLLER_PORT=8500
 - RDP_SERVER_MANAGER_PORT=8081
 - XRDP_INTEGRATION_PORT=3389
 - SESSION_CONTROLLER_PORT=8092
 - RESOURCE_MONITOR_PORT=8093
 - NODE_MANAGEMENT_PORT=8095
 - ADMIN_INTERFACE_PORT=8083
 - TRON_CLIENT_PORT=8091
 - TRON_PAYOUT_ROUTER_PORT=8092
 - TRON_WALLET_MANAGER_PORT=8093
 - TRON_USDT_MANAGER_PORT=8094
 - TRON_STAKING_PORT=8096
 - TRON_PAYMENT_GATEWAY_PORT=8097

**Database Configuration**
 - MONGODB_URI=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
 - MONGODB_DATABASE=lucid_gateway
 - MONGODB_PASSWORD=${MONGODB_PASSWORD}
 - REDIS_URL=redis://lucid-redis:6379/0
 - REDIS_PASSWORD=${REDIS_PASSWORD}
 - ELASTICSEARCH_URI=http://lucid-elasticsearch:9200
 - ELASTICSEARCH_CLUSTER_NAME=lucid-cluster
 - ELASTICSEARCH_NODE_NAME=lucid-node

**Security Configuration**
 - JWT_SECRET_KEY=${JWT_SECRET_KEY}
 - JWT_ALGORITHM=HS256
 - JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
 - JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
 - ENCRYPTION_KEY=${ENCRYPTION_KEY}
 - SSL_ENABLED=true
 - SECURITY_HEADERS_ENABLED=true
 - TOR_PASSWORD=${TOR_PASSWORD}
 - TRON_NETWORK=mainnet
 - TRON_API_KEY=${TRON_API_KEY}
 - USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

**Docker Configuration**
 - DOCKER_BUILDKIT=1
 - DOCKER_DEFAULT_PLATFORM=linux/arm64
 - COMPOSE_DOCKER_CLI_BUILD=1
 - LUCID_PLATFORM=arm64
 - LUCID_ARCHITECTURE=linux/arm64
 - LUCID_TARGET_PLATFORM=linux/arm64
 - DISTROLESS_BASE_IMAGE=gcr.io/distroless/python3-debian12
 - DISTROLESS_USER=65532:65532
 - DISTROLESS_SHELL=/bin/false

**Service URLs**
 - API_GATEWAY_URL=http://lucid-api-gateway:8080
 - BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
 - AUTH_SERVICE_URL=http://lucid-auth-service:8089
 - TRON_PAYMENT_URL=http://lucid-tron-client:8091
 - SESSION_MANAGEMENT_URL=http://lucid-session-api:8087

**Hardware Configuration**
 - HARDWARE_ACCELERATION=true
 - V4L2_ENABLED=true
 - GPU_ENABLED=false
 - RPI_GPIO_ENABLED=true
 - RPI_CAMERA_ENABLED=true

**Monitoring Configuration**
 - HEALTH_CHECK_ENABLED=true
 - HEALTH_CHECK_INTERVAL=30
 - METRICS_ENABLED=true
 - PROMETHEUS_ENABLED=true
 - GRAFANA_ENABLED=true
 - ALERTING_ENABLED=true
 - ALERT_CPU_THRESHOLD=80
 - ALERT_MEMORY_THRESHOLD=85

**Backup Configuration**
 - BACKUP_ENABLED=true
 - BACKUP_SCHEDULE="0 2 * * *"
 - BACKUP_RETENTION_DAYS=30
 - BACKUP_PATH=/mnt/myssd/Lucid/Lucid/backups

**Blockchain Configuration**
 - BLOCKCHAIN_NETWORK=lucid-mainnet
 - BLOCKCHAIN_CONSENSUS=PoOT
 - ANCHORING_ENABLED=true
 - BLOCK_INTERVAL=10

**Rate Limiting**
 - RATE_LIMIT_ENABLED=true
 - RATE_LIMIT_REQUESTS_PER_MINUTE=100
 - RATE_LIMIT_BURST_SIZE=200
 - API_RATE_LIMIT=1000

**CORS Configuration**
 - ALLOWED_HOSTS=*
 - CORS_ORIGINS=*
 - CORS_CREDENTIALS=true

**Session Configuration**
 - SESSION_TIMEOUT=1800
 - SESSION_CHUNK_SIZE=10485760
 - SESSION_COMPRESSION_LEVEL=6
 - SESSION_PIPELINE_STATES=recording,chunk_generation,compression,encryption,merkle_building,storage

**Node Management**
 - MAX_NODES_PER_POOL=100
 - PAYOUT_THRESHOLD_USDT=10.0
 - NODE_ADDRESS=${NODE_ADDRESS}
 - NODE_PRIVATE_KEY=${NODE_PRIVATE_KEY}

**Build Arguments**
 - BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
 - GIT_COMMIT=${GIT_COMMIT}
 - BUILDPLATFORM=linux/amd64
 - TARGETPLATFORM=linux/arm64

**Registry Configuration**
 - DOCKER_REGISTRY=docker.io
 - DOCKER_NAMESPACE=pickme
 - DOCKER_TAG=latest-arm64

**Data Paths**
 - DATA_PATH=/mnt/myssd/Lucid/Lucid/data
 - LOGS_PATH=/mnt/myssd/Lucid/Lucid/logs
 - BACKUPS_PATH=/mnt/myssd/Lucid/Lucid/backups
 - CONFIGS_PATH=/mnt/myssd/Lucid/Lucid/configs

**Environment Files**
 - ENV_FOUNDATION=configs/environment/.env.foundation
 - ENV_CORE=configs/environment/.env.core
 - ENV_APPLICATION=configs/environment/.env.application
 - ENV_SUPPORT=configs/environment/.env.support
 - ENV_DISTROLESS=configs/environment/.env.distroless
**Validation Requirements**
 - PROJECT_NAME=Lucid
 - API_GATEWAY_HOST=172.20.0.10
 - JWT_SECRET_KEY=${JWT_SECRET_KEY}
 - ENCRYPTION_KEY=${ENCRYPTION_KEY}
 - BLOCKCHAIN_NETWORK=lucid-mainnet

 *.env file names*
**Core Environment Files (Phase-based)**
 .env.foundation - Phase 1 Foundation Services configuration
 .env.core - Phase 2 Core Services configuration
 .env.application - Phase 3 Application Services configuration
 .env.support - Phase 4 Support Services configuration
 .env.distroless - Distroless deployment configuration
**Master and Security Files**
 .env.master - Master environment file for all services
 .env.secrets - Secure secrets reference (chmod 600)
 .env.secure - Master backup of secure values
**Service-Specific Environment Files**
 .env.api-gateway - API Gateway configuration
 .env.api-server - API Server configuration
 .env.authentication - Authentication service
 .env.authentication-service-distroless - Distroless auth service
 .env.orchestrator - Session orchestrator
 .env.chunker - Session chunker
 .env.merkle-builder - Merkle tree builder
 .env.tor-proxy - Tor proxy configuration
 .env.tunnel-tools - Tunnel tools configuration
 .env.server-tools - Server tools configuration
 .env.openapi-gateway - OpenAPI Gateway configuration
 .env.openapi-server - OpenAPI Server configuration
**Development and Build Files**
 .env.development - Development environment
 .env.staging - Staging environment
 .env.production - Production environment
 .env.test - Test environment
 .env.pi - Raspberry Pi deployment configuration
 .env.pi-build - Pi build configuration
**GUI and Application Files**
  .env.gui - GUI integration configuration
  .env.api - Direct API service configuration (in 03-api-gateway/api/)
**Specialized Configuration Files**
 .env.blockchain-api - Blockchain API configuration
 .env.blockchain-governance - Blockchain governance 
 .env.tron-client - TRON client configuration
 .env.tron-payout-router - TRON payout router
 .env.tron-wallet-manager - TRON wallet manager
 .env.tron-usdt-manager - TRON USDT manager
 .env.tron-staking - TRON staking configuration
 .env.tron-payment-gateway - TRON payment gateway
***File Locations***
**Most environment files are located in:**
 configs/environment/ - Main environment directory
 03-api-gateway/api/ - API Gateway specific
 sessions/core/ - Session management specific
 scripts/config/ - Generation scripts
 Usage Pattern
**The project follows a hierarchical environment loading pattern:**
 .env.foundation - Base configuration for all phases
 .env.core - Loaded with foundation for Phase 2
 .env.application - Loaded with foundation for Phase 3
 .env.support - Loaded with foundation for Phase 4
 .env.secure - Master backup with secure permissions (600)

 *Network Configurations:*
 **GUI:**
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-gui:latest-arm64 \
  -f infrastructure/docker/multi-stage/Dockerfile.gui \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=1.0.0 \
  --push \
  .

**RDP:**
# Build RDP distroless image
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-rdp:latest-arm64 \
  -f infrastructure/docker/multi-stage/Dockerfile.rdp \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=1.0.0 \
  --push \
  .

**node management:**
*Complete*
 # Build Node Management distroless image
 docker buildx build \
   --platform linux/arm64 \
   -t pickme/lucid-node:latest-arm64 \
   -f infrastructure/docker/multi-stage/Dockerfile.node \
   --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
   --build-arg VCS_REF=$(git rev-parse --short HEAD) \
   --build-arg VERSION=1.0.0 \
   --push \
   .

**Storage Services:**
*Complete*
 # Build Storage distroless image
 docker buildx build \
   --platform linux/arm64 \
   -t pickme/lucid-storage:latest-arm64 \
   -f infrastructure/docker/multi-stage/Dockerfile.storage \
   --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
   --build-arg VCS_REF=$(git rev-parse --short HEAD) \
   --build-arg VERSION=1.0.0 \
   --push \
   .


**Database:**
 # Build Database distroless image
 docker buildx build \
   --platform linux/arm64 \
   -t pickme/lucid-database:latest-arm64 \
   -f infrastructure/docker/multi-stage/Dockerfile.database \
   --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
   --build-arg VCS_REF=$(git rev-parse --short HEAD) \
   --build-arg VERSION=1.0.0 \
   --push \
   .

**Virtual machine:**
 # Build VM Management distroless image
 docker buildx build \
   --platform linux/arm64 \
   -t pickme/lucid-vm:latest-arm64 \
   -f infrastructure/docker/multi-stage/Dockerfile.vm \
   --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
   --build-arg VCS_REF=$(git rev-parse --short HEAD) \
   --build-arg VERSION=1.0.0 \
   --push \
   .
