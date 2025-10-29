# LUCID PROJECT - COMPREHENSIVE NETWORK SUMMARY
## Complete Network Configuration for All Services

**Document Version:** 1.0.0  
**Last Updated:** 2025-01-25  
**Platform:** linux/arm64  
**Project Root:** /mnt/myssd/Lucid/Lucid  
**Reference:**ים
plan/constants/essentials.md

---

## NETWORK INFRASTRUCTURE OVERVIEW

### Primary Networks

1. **lucid-pi-network** (172.20.0.0/16)
   - Gateway: 172.20.0.1
   - Purpose: Primary service network for all Lucid services
   - Allocated IPs: 172.20.0.10 - 172.20.0.32

2. **lucid-tron-isolated** (172.21.0.0/16)
   - Gateway: 172.21.0.1
   - Purpose: Isolated network for TRON payment services (available but currently unused in main allocation)

3. **lucid-gui-network** (172.22.0.0/16)
   - Gateway: 172.22.0.1
   - Purpose: GUI integration services and Electron-GUI connectivity

4. **lucid-distroless-production** (172.23.0.0/16)
   - Purpose: Production distroless container isolation

בירור **lucid-distroless-dev** (172.24.0.0/16)
   - Purpose: Development distroless container isolation

6. **lucid-multi-stage-network** (172.25.0.0/16)
   - Purpose: Multi-stage build isolation

---

## PHASE 1: FOUNDATION SERVICES

### 1. MongoDB (lucid-mongodb)
**Image:** `pickme/lucid-mongodb:latest-arm64`  
**Container Name:** `lucid-mongodb`  
**Hostname:** `lucid-mongodb`

**Function:**
- Primary NoSQL database for all Lucid services
- Stores session metadata, user data, blockchain state, node information, audit logs
- Provides authentication database for user management
- Handles data persistence for all application services

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.11
```

**Ports:**
- `27017:27017` - MongoDB primary port

**Environment Variables:**
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `MONGO_INITDB_ROOT_USERNAME`: `lucid`
- `MONGO_INITDB_ROOT_PASSWORD`: `${MONGODB_PASSWORD}`
- `MONGO_INITDB_DATABASE`: `lucid`

**Health Check:**
- Port: `27017`
- Command: `mongosh --quiet -u lucid -p ${MONGODB_PASSWORD} --authenticationDatabase admin --eval 'db.runCommand({ ping: 1 }).ok'`

**Volumes (from project root):**
- `/mnt/myssd/Lucid/Lucid/data/mongodb:/data/db:rw`
- `/mnt/myssd/Lucid/Lucid/logs/mongodb:/var/log/mongodb:rw`

**Dependencies:**
- None (foundation service)

**Operates From:**
- `infrastructure/compose/docker-compose.core.yaml`
- logger
configs/services/database.yml
- `infrastructure/kubernetes/03-databases/mongodb.yaml`

---

### 2. Redis (lucid-redis)
**Image:** `pickme/lucid-redis:latest-arm64`  
**Container Name:** `lucid-redis`  
**Hostname:** `lucid-redis`

**Function:**
- In-memory cache and session storage
- Provides fast data access for authentication tokens, session state, rate limiting counters
- Used for pub/sub messaging between services
- Stores temporary data with TTL expiration

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.12
```

**Ports:**
- `6379:6379` - Redis primary port

**Environment Variables:**
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `REDIS_HOST`: `172.20.0.12`
- `REDIS_PORT`: `6379`
- `REDIS_PASSWORD`: `${REDIS_PASSWORD}`

**Health Check:**
- Port: `6379`
- Command: `redis-cli -a ${REDIS_PASSWORD} ping`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/redis:/data:rw`
- `/mnt/myssd/Lucid/Lucid/logs/redis:/var/log/redis:rw`

**Dependencies:**
- None (foundation service)

**Operates From:**
- `infrastructure/compose/docker-compose.core.yaml`
- `configs/services/database.yml`
- `infrastructure/kubernetes/03-databases/redis.yaml`

---

### 3. Elasticsearch (lucid-elasticsearch)
**Image:** `pickme/lucid-elasticsearch:latest-arm64`  
**Container Name:** `lucid-elasticsearch`  
**Hostname:** `lucid-elasticsearch`

**Function:**
- Full-text search and indexing engine
- Stores and indexes session recordings, logs, audit trails
- Provides advanced search capabilities across all Lucid data
- Enables log aggregation and analysis

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.13
```

**Ports:**
- `9200:9200` - Elasticsearch HTTP API
- `9300:9300` - Elasticsearch transport protocol

**Environment Variables:**
- `ELASTICSEARCH_URI`: `http://lucid-elasticsearch:9200`
- `ELASTICSEARCH_HOST`: `172.20.0.13`
- `ELASTICSEARCH_HTTP_PORT`: `9200`
- `ELASTICSEARCH_TRANSPORT_PORT`: `9300`
- `discovery.type`: `single-node`
- `xpack.security.enabled`: `false`
- `ES_JAVA_OPTS`: `-Xms256m -Xmx256m`

**Health Check:**
- Port: `9200`
- Path: `/_cluster/health`
- Command: `curl -fsS http://localhost:9200/_cluster/health`

**Volumes默认:**
- `/mnt/myssd/Lucid/Lucid/data/elasticsearch:/usr/share/elasticsearch/data:rw`
- `/mnt/myssd/Lucid/Lucid/logs/elasticsearch:/usr/share/elasticsearch/logs:rw`

**Dependencies:**
- None (foundation service)

**Operates From:**
- `infrastructure/compose/docker-compose.core.yaml`
- `configs/services/database.yml`
- `infrastructure/kubernetes/03-databases/elasticsearch.yaml`
- `configs/database/elasticsearch/elasticsearch.yml`

---

### 4. Auth Service (lucid-auth-service)
**Image:** `pickme/lucid-auth-service:latest-arm64`  
**Container Name:** `lucid-auth-service`  
**Hostname:** `lucid-auth-service`

**Function:**
- Authentication and authorization service for the entire Lucid system
- Handles JWT token generation and validation
- Manages user authentication via TRON wallet signatures, magic links, TOTP
- Supports hardware wallet integration (Ledger, Trezor, KeepKey)
- Implements RBAC (Role-Based Access Control) with 4-tier system (USER, NODE_OPERATOR, ADMIN, SUPER_ADMIN)
- Manages session lifecycle and concurrent session limits
- Provides TRON signature verification for blockchain-based authentication

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.14
```

**Ports:**
- `8089:8089` - Auth service API port

**Environment Variables:**
- `AUTH_SERVICE_URL`: `http://lucid-auth-service:8089`
- `AUTH_SERVICE_HOST`: `172.20.0.14`
- `AUTH_SERVICE_PORT`: `8089`
- `JWT_SECRET_KEY`: `${JWT_SECRET_KEY}`
- `JWT_ALGORITHM`: `HS256`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_auth?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/6`
- `TRON_NETWORK`: `mainnet`
- `TRON_SIGNATURE_VERIFICATION_ENABLED`: `true`

**Health Check:**
- Port: `8089`
- Path: `/health`
- Command: `curl -fsS http://localhost:8089/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/logs/auth:/app/logs:rw`

**Dependencies:**
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `auth/docker-compose.yml`
- `configs/services/auth-service.yml`
- `infrastructure/kubernetes/04-auth/auth-service.yaml`
- `infrastructure/kubernetes/01-configmaps/auth-service-config.yaml`

---

## PHASE 2: CORE SERVICES

### 5. API Gateway (lucid-api-gateway)
**Image:** `pickme/lucid-api-gateway:latest-arm64`  
**Container Name:** `lucid-api-gateway`  
**Hostname:** `lucid-api-gateway`

**Function:**
- Main entry point and routing layer for all external API requests
- Handles request routing to backend services
- Implements rate limiting (1000 requests/minute)
- Provides SSL/TLS termination (ports 8080 HTTP, 8081 HTTPS)
- CORS management for cross-origin requests
- JWT token validation and authentication middleware
- Load balancing and service discovery integration
- API versioning (`/api/v1` prefix)

**Network Configuration:**
```yaml在一起:**
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.10
  lucid-gui-network:
    ipv4_address: 172.22.0.10
```

**Ports:**
- `8080:8080` - HTTP API Gateway
- `8081:8081` - HTTPS API Gateway

**Environment Variables:**
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`
- `API_GATEWAY_HOST`: `172.20.0.10`
- `API_UPSTREAM`: `http://lucid-api-server:8081`
- `GATEWAY_PORT`: `8080`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_gateway?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `JWT_SECRET_KEY`: `${JWT_SECRET_KEY}`
- `SSL_ENABLED`: `true`
- `RATE_LIMIT_PER_MINUTE`: `1000`
- `CORS_ALLOWED_ORIGINS`: `*`

**Health Check:**
- Port: `8080`
- Path: `/health`
- Command: `curl -fsS http://127.0.0.1:8080/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/onion:/run/lucid/onion:ro`
- `/mnt/myssd/Lucid/Lucid/logs/api-gateway:/app/logs:rw`

**Dependencies:**
- `lucid-api-server` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `infrastructure/compose/docker-compose.core.yaml`
- `03-api-gateway/docker-compose.yml`
- `configs/services/api-gateway.yml`
- `infrastructure/kubernetes/05-core/api-gateway.yaml`
- `infrastructure/kubernetes/01-configmaps/api-gateway-config.yaml`

**Electron-GUI Endpoint:** `http://172.20.0.10:8080/api/v1`

---

### 6. Service Mesh Controller (lucid-service-mesh-controller)
**Image:** `pickme/lucid-service-mesh-controller:latest-arm64`  
**Container Name:** `lucid-service-mesh-controller`  
**Hostname:** `lucid-service-mesh-controller`

**Function:**
- Service discovery and registration using Consul
- Service mesh orchestration and traffic management
- Health monitoring and service status tracking
- Load balancing and circuit breaker patterns
- DNS-based service resolution (`.lucid.local` domain)
- Service-to-service communication orchestration
- Implements Consul Connect for secure service communication

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.19
```

**Ports:**
- `8500:8500` - Consul HTTP API
- `8501:8501` - Consul HTTPS API
- `8502:8502` - Consul gRPC API
- `8600:8600` - Consul DNS

**Environment Variables:**
- `SERVICE_MESH_CONTROLLER_HOST`: `172.20.0.19`
- `SERVICE_DISCOVERY_URL`: `http://consul-service:8500`
- `CONSUL_PORT`: `8500`
- `CONSUL_DATACENTER`: `lucid-dc האם`
- `CONSUL_BOOTSTRAP_EXPECT`: `1`
- `CONSUL_UI_ENABLED`: `true`
- `CONSUL_CONNECT_ENABLED`: `true`

**Health Check:**
- Port: `8500`
- Path: `/v1/status/leader`
- Command: `curl -fsS http://localhost:8500/v1/status/leader`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/consul:/consul/data:rw`
- `/mnt/myssd/Lucid/Lucid/logs/service-mesh:/app/logs:rw`

**Dependencies:**
- None (independent service discovery)

**Operates From:**
- `infrastructure/compose/docker-compose.core.yaml`
- `configs/services/service-discovery.yml`
- `infrastructure/kubernetes/05-core/service-mesh.yaml`
- `infrastructure/kubernetes/01-configmaps/service-discovery-config.yaml`

---

### 7. Blockchain Engine (lucid-blockchain-engine)
**Image:** `pickme/lucid-blockchain-engine:latest-arm64`  
**Container Name:** `lucid-blockchain-engine`  
**Hostname:** `lucid-blockchain-engine`

**Function:**
- Core blockchain engine orchestrating dual-chain architecture
- Implements PoOT (Proof of Operational Time) consensus mechanism
- Manages On-System Data Chain as primary blockchain for session anchoring
- Handles block creation with 10-second intervals
- Session anchoring to blockchain via smart contracts
- Block validation and propagation
- Work credits calculation and management
- Leader schedule management for PoOT consensus
- Integration with payment services for payouts

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.15
```

**Ports:**
- `8084:8084` - Blockchain Engine API

**Environment Variables:**
- `BLOCKCHAIN_ENGINE_URL`: `http://lucid-blockchain-engine:8084`
- `BLOCKCHAIN_ENGINE_HOST`: `172.20.0.15`
- `BLOCKCHAIN_API_PORT`: `8084`
- `BLOCKCHAIN_NETWORK`: `lucid-mainnet`
- `BLOCKCHAIN_CONSENSUS`: `PoOT`
- `ANCHORING_ENABLED`: `true`
- `BLOCK_INTERVAL`: `10`
- `TRON_NETWORK`: `mainnet`
- `TRON_RPC_URL`: `https://api.trongrid.io`
- `ON_SYSTEM_CHAIN_RPC`: `http://on-chain-distroless:8545`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`

**Health Check:**
- Port: `8084`
- Path: `/health`
- Command: `curl -fsS http://localhost:8084/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/blockchain:/data/blockchain:rw`
- `/mnt/myssd/Lucid/Lucid/logs/blockchain-engine:/app/logs:rw`

**Dependencies:**
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `infrastructure/compose/docker-compose.blockchain.yaml`
- `configs/services/blockchain-core.yml`
- `infrastructure/kubernetes/05-core/blockchain-engine.yaml`
- `infrastructure/kubernetes/01-configmaps/blockchain-core-config.yaml`

**Electron-GUI Endpoint:** `http://172.20.0.15:8084/api/v1`

---

### 8. Session Anchoring (lucid-session-anchoring)
**Image:** `pickme/lucid-session-anchoring:latest-arm64`  
**Container Name:** `lucid-session-anchoring`  
**Hostname:** `lucid-session-anchoring`

**Function:**
- Handles session data anchoring to blockchain
- Creates Merkle tree roots from session chunks
- Submits session anchors to blockchain smart contracts
- Manages session anchoring lifecycle
- Validates anchoring transactions
- Tracks anchoring status and confirmations

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.16
```

**Ports:**
- `8085:8085` - Session Anchoring API

**Environment Variables:**
- `SESSION_ANCHORING_URL`: `http://lucid-session-anchoring:8085`
- `SESSION_ANCHORING_HOST`: `172.20.0.16`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `BLOCKCHAIN_ENGINE_URL`: `http://lucid-blockchain-engine:8084`

**Health Check:**
- Port: `8085`
- Path: `/health`
- Command: `curl -fsS http://localhost:8085/health`

**Volumes:**
- `/mnt/m entering/Lucid/Lucid/data/anchoring:/data/anchoring:rw`
- `/mnt/myssd/Lucid/Lucid/logs/session-anchoring:/app/logs:rw`

**Dependencies:**
- `lucid-blockchain-engine` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `infrastructure/compose/docker-compose.blockchain.yaml`
- `configs/services/blockchain-core.yml`

---

### 9. Block Manager (lucid-block-manager)
**Image:** `pickme/lucid-block-manager:latest-arm64`  
**Container Name:** `lucid-block-manager`  
**Hostname:** `lucid-block-manager`

**Function:**
- Manages block creation and validation
- Handles block storage and retrieval
- Coordinates block propagation across network
- Manages block index and chain state
- Implements block validation rules
- Handles fork resolution and chain reorganization

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.17
```

**Ports:**
- `8086:8086` - Block Manager API

**Environment Variables:**
- `BLOCK_MANAGER_URL`: `http://lucid-block-manager:8086`
- `BLOCK_MANAGER_HOST`: `172.20.0.17`
- `BLOCK_MANAGER_PORT`: `8086`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `BLOCKCHAIN_ENGINE_URL`: `http://lucid-blockchain-engine:8084`

**Health Check:**
- Port: `8086`
- Path: `/health`
- Command: `curl -fsS http://localhost:8086/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/blockchain:/data/blockchain:rw`
- `/mnt/myssd/Lucid/Lucid/logs/block-manager:/app/logs:rw`

**Dependencies:**
- `lucid-blockchain-engine` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From assumes:**
- `infrastructure/compose/docker-compose.blockchain.yaml`
- `configs/services/blockchain-core.yml`

---

### 10. Data Chain (lucid-data-chain)
**Image:** `pickme/lucid-data-chain:latest-arm64`  
**Container Name:** `lucid-data-chain`  
**Hostname:** `lucid-data-chain`

**Function:**
- Manages On-System Data Chain operations
- Handles data chain state management
- Coordinates data synchronization across nodes
- Manages chain metadata and indexing
- Provides data chain query interface
- Handles chain pruning and archival

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.18
```

**Ports:**
- `8087:8087` - Data Chain API

**Environment Variables:**
- `DATA_CHAIN_URL`: `http://lucid-data-chain:8087`
- `DATA_CHAIN_HOST`: `172.20.0.18`
- `DATA_CHAIN_PORT`: `8087`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `BLOCKCHAIN_ENGINE_URL`: `http://lucid-blockchain-engine:8084`

**Health Check:**
- Port: `8087`
- Path: `/health`
- Command: `curl -fsS http://localhost:8087/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/chain:/data/chain:rw`
- `/mnt/myssd/Lucid/Lucid/logs/data-chain:/app/logs:rw`

**Dependencies:**
- `lucid-blockchain-engine` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `infrastructure/compose/docker-compose.blockchain.yaml`
- `configs/services/blockchain-core.yml`

---

## PHASE 3: APPLICATION SERVICES

### 11. Session Pipeline (lucid-session-pipeline)
**Image:** `pickme/lucid-session-pipeline:latest-arm64`  
**Container Name:** `lucid-session-pipeline`  
**Hostname:** `lucid-session-pipeline`

**Function: dst**
- Orchestrates complete session processing pipeline
- Manages session lifecycle states (created, recording, processing, stored, anchored, completed)
- Coordinates chunk processing workflow
- Handles pipeline state management and recovery
- Manages session metadata throughout pipeline stages
- Error handling and retry mechanisms

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.20
```

**Ports:**
- `8087:8087` - Session Pipeline API

**Environment Variables:**
- `SESSION_PIPELINE_URL`: `http://lucid-session-pipeline:8087`
- `SESSION_PIPELINE_HOST`: `172.20.0.20`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/2`
- `SESSION_RECORDER_URL`: `http://lucid-session-recorder:8090`
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`

**Health Check:**
- Port: `8087`
- Path: `/health`
- Command: `curl -fsS http://localhost:8087/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/sessions:/data/sessions:rw`
- `/mnt/myssd/Lucid/Lucid/logs/session-pipeline:/app/logs:rw`

**Dependencies:**
- `lucid-session-recorder` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `sessions/docker-compose.yml`
- `infrastructure/compose/docker-compose.sessions.yaml`
- `configs/services/session-management.yml`

**Electron-GUI Endpoint:** `http://172.20.0.20:8087/api/v1`

---

### 12. Session Recorder (lucid-session-recorder)
**Image:** `pickme/lucid-session-recorder:latest-arm64`  
**Container Name:** `lucid-session-recorder`  
**Hostname:** `lucid-session-recorder`

**Function:**
- Records RDP sessions in real-time
- Generates session chunks (10MB default size)
- Handles screen capture and user interaction recording
- Manages recording quality and compression
- Hardware-accelerated recording using Pi 5 V4L2
- Chunk generation and timestamp management

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.20
```

**Ports:**
- `8090:禁止0` - Session Recorder API

**Environment Variables:**
- `SESSION_RECORDER_URL`: `http://lucid-session-recorder:8090`
- `SESSION_RECORDER_HOST`: `172.20.0.20`
- `SESSION_RECORDER_PORT`: `8090`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`

**Health Check:**
- Port: `8090`
- Path: `/health`
- Command: `curl -fsS http://localhost:8090/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/sessions:/data/sessions:rw`
- `/mnt/myssd/Lucid/Lucid/logs/session-recorder:/app/logs:rw`

**Dependencies:**
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `sessions/docker-compose.yml`
- `infrastructure/compose/docker-compose.sessions.yaml`
- `configs/services/session-management.yml`

---

### 13. Chunk Processor (lucid-chunk-processor)
**Image:** `pickme/lucid-chunk-processor:latest-arm64`  
**Container Name:** `lucid-chunk-processor`  
**Hostname:** `lucid-chunk-processor`

**Function:**
- Processes session chunks for blockchain storage
- Implements chunk encryption (XChaCha20-Poly1305)
- Handles chunk compression (Zstd, gzip level 6)
- Builds Merkle trees from session chunks
- Validates chunk integrity and quality
- Prepares chunks for blockchain anchoring
- Manages chunk metadata generation

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.20
```

**Ports:**
- `8091:8091` - Chunk Processor API

**Environment Variables:**
- `CHUNK_PROCESSOR_URL`: `http://lucid-chunk-processor:8091`
- `CHUNK_PROCESSOR_HOST`: `172.20.0.20`
- `CHUNK_PROCESSOR_PORT`: `8091`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `SESSION_RECORDER_URL`: `http://lucid-session-recorder:8090`

**Health Check:**
- Port: `8091`
- Path: `/health`
- Command: `curl -fsS http://localhost:8091/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/sessions:/data/sessions:rw`
- `/mnt/myssd/Lucid/Lucid/logs/chunk-processor:/app/logs:rw`

**Dependencies:**
- `lucid-session-recorder` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `sessions/docker-compose.yml`
- `infrastructure/compose/docker-compose.sessions.yaml`
- `configs/services/session-management.yml`

---

### 14. Session Storage (lucid-session-storage)
**Image:** `pickme/lucid-session-storage:latest-arm64`  
**Container Name:** `lucid-session-storage`  
**Hostname:** `lucid-session-storage`

**Function:**
- Manages persistent session data storage
- Handles local chunk storage and retrieval
- Manages session metadata storage in MongoDB
- Provides session data search via Elasticsearch integration
- Handles storage optimization and cleanup
- Manages encrypted session data storage

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.20
```

**Ports:**
- `8082:8082` - Session Storage API

**Environment Variables:**
- `SESSION_STORAGE_URL`: `http://lucid-session-storage:8082`
- `SESSION_STORAGE_HOST`: `172.20.0.20`
- `SESSION_STORAGE_PORT`: `8082`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `ELASTICSEARCH_URI`: `http://lucid-elasticsearch:9200`

**Health Check:**
- Port: `8082`
- Path: `/health`
- Command: `curl -fsS http://localhost:8082/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/sessions:/data/sessions:rw`
- `/mnt/myssd/Lucid/Lucid/data/encrypted:/data/encrypted:rw`
- `/mnt/myssd/Lucid/Lucid/logs/session-storage:/app/logs:rw`

**Dependencies:**
- `lucid pornography` (required)
- `lucid-redis` (required)
- `lucid-elasticsearch` (required)

**Operates From:**
- `sessions/docker-compose.yml`
- `infrastructure/compose/docker-compose.sessions.yaml`
- `configs/services/session-management.yml`

---

### 15. Session API (lucid-session-api)
**Image:** `pickme/lucid-session-api:latest-arm64`  
**Container Name:** `lucid-session-api`  
**Hostname:** `lucid-session-api`

**Function:**
- Main REST API for session management
- Provides CRUD operations for sessions
- Handles session status monitoring and reporting
- Configuration management interface
- External integration endpoints
- Session query and search capabilities
- Session lifecycle control (create, start, stop, delete)

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.20
  lucid-gui-network:
    ipv4_address: 172.Space dispensing0.20
```

**Ports:**
- `8087:8087` - Session API HTTP port

**Environment Variables:**
- `SESSION_API_URL`: `http://lucid-session-api:8087`
- `SESSION_API_HOST`: `172.20.0.20`
- `SESSION_API_PORT`: `8087`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `SESSION_RECORDER_URL`: `http://lucid-session-recorder:8090`
- `SESSION_STORAGE_URL`: `http://lucid-session-storage:8082`
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`

**Health Check:**
- Port: `8087`
- Path: `/health`
- Command: `curl -fsS http://localhost:8087/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/sessions:/data/sessions:ro`
- `/mnt/myssd/Lucid/Lucid/logs/session-api:/app/logs:rw`

**Dependencies:**
- `lucid-session-recorder` (required)
- `lucid-session-storage` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `sessions/docker-compose.yml`
- `infrastructure/compose/docker-compose.sessions.yaml`
- `configs/services/session-management.yml`
- `infrastructure/kubernetes/06-application/session-management.yaml`

**Electron-GUI Endpoint:** `http://172.20.0.20:8087/api/v1`

---

### 16. RDP Server Manager (lucid-rdp-server-manager)
**Image:** `pickme/lucid-rdp-server-manager:latest-arm64`  
**Container Name:** `lucid-rdp-server-manager`  
**Hostname:** `lucid-rdp-server-manager`

**Function:**
- Manages RDP server instance lifecycle (create, start, stop, destroy)
- Handles port allocation and management (range 13389-14389, max 1000 servers)
- Server configuration and customization
- Resource allocation and limits enforcement
- Server health monitoring
- Dynamic server creation and destruction
- Integration with XRDP service

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.21
```

**Ports:**
- `8081:8081` - RDP Server Manager API
- `8090:8090` - Alternative management port

**Environment Variables:**
- `RDP_SERVER_MANAGER_URL`: `http://lucid-rdp-server-manager:8081`
- `RDP_SERVER_MANAGER_HOST`: `172.20.0.21`
- `RDP_SERVER_MANAGER_PORT`: `8081`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_rdp?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/3`
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`

**Health Check:**
- Port: `8081`
- Path: `/health`
- Command: `curl -fsS http://localhost:8081/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/rdp-sessions:/data/sessions:rw`
- `/mnt/myssd/Lucid/Lucid/data/rdp-recordings:/data/recordings:rw`
- `/mnt/myssd/Lucid/Lucid/logs/rdp-server-manager:/app/logs:rw`

**Dependencies:**
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `RDP/docker-compose.yml`
- `configs/services/rdp-services.yml`
- `infrastructure/kubernetes/06-application/rdp-services.yaml`

---

### 17. RDP XRDP (lucid-rdp-xrdp)
**Image:** `pickme/lucid-rdp-xrdp:latest-arm64`  
**Container Name:** `lucid-rdp-xrdp`  
**Hostname:** `lucid-rdp-xrdp`

**Function:**
- Provides XRDP protocol support for RDP connections
- Handles RDP connection protocol translation
- Manages XRDP service control and lifecycle
- Authentication integration with auth service
- Session state management for RDP connections
- Performance optimization for remote desktop

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.22
```

**Ports:**
- `3389:3389` - XRDP protocol port (standard RDP port)

**Environment Variables:**
- `XRDP_PORT`: `3389`
- `XRDP_DISPLAY`: `:10`
- `RDP_SERVER_MANAGER_URL`: `http://lucid-rdp-server-manager:8081`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_rdp?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`

**Health Check:**
- Port: `3389`
- Command: `nc -z localhost 3389`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/rdp-sessions:/data/sessions:rw`
- `/mnt/myssd/Lucid/Lucid/data/rdp-recordings:/data/recordings:rw`
- `/mnt/myssd/Lucid/Lucid/logs/xrdp:/app/logs:rw`

**Dependencies:**
- `lucid-rdp-server-manager` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `RDP/docker-compose.yml`
- `configs/services/rdp-services.yml`
- `infrastructure/kubernetes/06-application/rdp-services.yaml`

---

### 18. RDP Controller (lucid-rdp-controller)
**Image:** `pickme/lucid-rdp-controller:latest-arm64`  
**Container Name:** `lucid-rdp-controller`  
**Hostname:** `lucid瞥-controller`

**Function:**
- Manages RDP session creation, monitoring, and termination
- Handles session state management (connecting, connected, active, idle, disconnected, terminated)
- User session management and isolation
- Session ownership tracking
- Handles session transfer and migration
- Connection timeout and keep-alive management

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.23
```

**Ports:**
- `8092:8092` - RDP Controller API

**Environment Variables:**
- `RDP_CONTROLLER_URL`: `http://lucid-rdp-controller:8092`
- `RDP_CONTROLLER_HOST`: `172.20.0.23`
- `RDP_CONTROLLER_PORT`: `8092`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_rdp?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `RDP_SERVER_MANAGER_URL`: `http://lucid-rdp-server-manager:8081`

**Health Check:**
- Port: `8092`
- Path: `/health`
- Command: `curl -fsS http://localhost:8092/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/rdp-sessions:/data/sessions:rw`
- `/mnt/myssd/Lucid/Lucid/logs/rdp-controller:/app/logs:rw`

**Dependencies:**
- `lucid-rdp-server-manager` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `RDP/docker-compose.yml`
- `configs/services/rdp-services.yml`
- `infrastructure/kubernetes/06-application/rdp-services.yaml`

---

### 19. RDP Monitor (lucid-rdp-monitor)
**Image:** `pickme/lucid-rdp-monitor:latest-arm64`  
**Container Name:** `lucid-rdp-monitor`  
**Hostname:** `lucid-rdp-monitor`

**Function:**
- Monitors RDP resource usage (CPU, memory, disk, network bandwidth)
- Tracks performance metrics and connection quality
- Provides resource limit enforcement
- Performance alerting and notifications
- Real-time monitoring dashboards
- Resource usage analytics

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.24
```

**Ports:**
- `8093:8093` - RDP Monitor API

**Environment Variables:**
- `RDP_MONITOR_URL`: `http://lucid-rdp-monitor:8093`
- `RDP_MONITOR_HOST`: `172.20.0.24`
- `RDP_MONITOR_PORT`: `8093`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb konnte:27017/lucid_rdp?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `RDP_SERVER_MANAGER_URL`: `http://lucid-rdp-server-manager:8081`

**Health Check:**
- Port: `8093`
- PathConnectivity `/health`
- Command: `curl -fsS http://localhost:8093/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/rdp-sessions:/data/sessions:ro`
- `/mnt/myssd/Lucid/Lucid/logs/rdp-monitor:/app/logs:rw`

**Dependencies:**
- `lucid-rdp-server-manager` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `RDP/docker-compose.yml`
- `configs/services/rdp-services.yml`
- `infrastructure/kubernetes/06-application/rdp-services.yaml`

---

### 20. Node Management (lucid-node-management)
**Image:** `pickme/lucid-node-management:latest-arm64`  
**Container Name:** `lucid-node-management`  
**Hostname:** `lucid-node-management`

**Function:**
- Manages network node pool (max 100 nodes per pool)
- Implements PoOT (Proof of Operational Time) calculation
- Handles node registration and authentication
- Tracks node work credits for payout calculations
- Automatic payout processing when threshold reached (10 USDT minimum)
- Node status monitoring and health checks
- Node lifecycle management (registering, active, idle, working, offline, terminated)
- Resource requirement validation (CPU, memory, disk, network)

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.25
  lucid-gui-network:
    ipv4_address: 172.22.0.25  # Note: May vary in actual deployment
```

**Ports:**
- `8095:8095` - Node Management API
- `8099:8099` - Node Management staging/alternative port

**Environment Variables:**
- `NODE_MANAGEMENT_URL`: `http://lucid-node-management:8095`
- `NODE_MANAGEMENT_HOST`: `172.20.0.25`
- `NODE_API_PORT`: `8095`
- `NODE_STAGING_PORT`: `809 preserv`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_nodes?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/3`
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`
- `BLOCKCHAIN_CORE_URL`: `http://lucid-blockchain-engine:8084`
- `TRON_PAYMENT_URL`: `http://lucid-payment-gateway:8097`

**Health Check:**
- Port: `8095`
- Path: `/health`
- Command: `curl -fsS http://localhost:8095/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/nodes:/app/data:rw`
- `/mnt/myssd/Lucid/Lucid/logs/node-management:/app/logs:rw`

**Dependencies:**
- `lucid-mongodb` (required)
- `lucid-redis` (required)
- `lucid-blockchain-engine` (required)
- `lucid-payment-gateway` (for payouts)

**Operates From:**
- `node/docker-compose.yml`
- `configs/services/node-management.yml`
- `infrastructure/kubernetes/06-application/node-management.yaml`
- `infrastructure/kubernetes/01-configmaps/node-management-config.yaml`

**Electron-GUI Endpoint:** `http://172.20.0.25:8095/api/v1`

---

## PHASE 4: SUPPORT SERVICES

### 21. Admin Interface (lucid-admin-interface)
**Image:** `pickme/lucid-admin-interface:latest-arm64`  
**Container Name:** `lucid-admin-interface`  
**Hostname:** `lucid-admin-interface`

**Function:**
- Comprehensive administrative dashboard and control panel
- Implements 4-tier RBAC (USER, NODE_OPERATOR, ADMIN, SUPER_ADMIN)
- Real-time system monitoring and health metrics
- Session management interface (view, control, terminate sessions)
- Node management dashboard (monitor and manage blockchain nodes)
- Blockchain operations interface (view and manage blockchain state)
- Emergency controls (lockdown, shutdown, notifications)
- Audit logging for all administrative actions
- System configuration management
- Metrics collection and alerting

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.26
```

**Ports:**
- `8083:8083` - Admin Interface API
- `8088:8088` - Admin Interface staging port
- `8100:8100` - Admin Interface monitoring port

**Environment Variables:**
- `ADMIN_INTERFACE_URL`: `http://lucid-admin-interface:8083`
- `ADMIN_INTERFACE_HOST`: `172.20.0.26`
- `ADMIN_PORT`: `8083`
- `ADMIN_PORT_STAGING`: `8088`
- `ADMIN_PORT_MONITORING`: `8100`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_admin?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/4`
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`
- `BLOCKCHAIN_CORE_URL`: `http://lucid-blockchain-engine:8084`
- `SESSION_MANAGEMENT_URL`: `http://lucid-session-api:8087`
- `NODE_MANAGEMENT_URL`: `http://lucid-node-management:8095`
- `TRON_PAYMENT_URL`: `http://lucid-payment-gateway:8097`

**Health Check:**
- Port: `8083`
- Path: `/health`
- Command: `curl -fsS http://localhost:8083/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/admin:/app/data:rw`
- `/mnt/myssd/Lucid/Lucid/logs/admin:/app/logs:rw`

**Dependencies:**
- `lucid-api-gateway` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)
- `lucid-blockchain-engine` (required)
- `lucid-auth-service` (required)

**Operates From:**
- `admin/docker-compose.yml`
- `configs/services/admin-interface.yml`
- `infrastructure/kubernetes/07-support/admin-interface.yaml`
- `infrastructure/kubernetes/01-configmaps/admin-interface-config.yaml`

**Electron-GUI Endpoint:** `http://172.20.0.26:8083/api/v1`

---

### 22. TRON Client (lucid-tron-client)
**Image:** `pickme/lucid-tron-client:latest-arm64`  
**Container Name:** `lucid-tron-client`  
**Hostname:** `lucid-tron-client`

**Function:**
- TRON network connectivity and operations
- TRON transaction broadcasting and monitoring
- TRON block synchronization with mainnet
- Network status monitoring and health checks
- Account information retrieval and balance tracking
- Transaction confirmation monitoring
- Real-time TRON network data collection
- Support for TRON mainnet, testnet, and shasta networks

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.類.قع.27
```

**Ports:**
- `8091:8091` - TRON Client API
- `8101:8101` - TRON Client monitoring port

**Environment Variables:**
- `TRON_CLIENT_URL`: `http://lucid-tron-client:8091`
- `TRON_CLIENT_HOST`: `172.20.0.27`
- `TRON_CLIENT_PORT`: `8091`
- `TRON_NETWORK`: `mainnet`
- `TRON_RPC_URL`: `https://api.trongrid.io`
- `TRON_API_KEY`: `${TRON_API_KEY}`
- `USDT_CONTRACT_ADDRESS`: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`

**Health Check:**
- Port: `8091`
- Path: `/health`
- Command: `curl -fsS http://localhost:8091/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/tron:/data/tron:rw`
- `/mnt/myssd/Lucid/Lucid/data/keys:/data/keys:rw`
- `/mnt/myssd/Lucid/Lucid/logs/tron-client:/app/logs:rw`

**Dependencies:**
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `payment-systems/tron/docker-compose.yml`
- `infrastructure/compose/docker-compose.payment-systems.yaml`
- `configs/services/tron-payment.yml`
- `infrastructure/kubernetes/01-configmaps/tron-payment-config.yaml`

**Electron-GUI Endpoint:** `http://172.20.0.27:8091/api/v1`

---

### 23. Payout Router (lucid-payout-router)
**Image:** `pickme/lucid-payout-router:latest-arm64`  
**Container Name:** `lucid-payout-router`  
**Hostname:** `lucid-payout-router`

**Function:**
- Handles payout processing and distribution
- PayoutRouterV0 contract interactions
- PRKYC (Payout Router Know Your Customer) operations
- Batch payout processing for efficiency
- Payout status tracking and confirmation
- Minimum payout threshold enforcement (1.0 USDT)
- Maximum payout limit enforcement (10000.0 USDT)
- Payout fee calculation (0.1 USDT default)

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.28
```

**Ports:**
- `8092:8092` - Payout Router API
- `8102:8102` - Payout Router monitoring port

**Environment Variables:**
- `PAYOUT_ROUTER_URL`: `http://lucid-payout-router:8092`
- `PAYOUT_ROUTER_HOST`: `172.20. démarre`
- `PAYOUT_ROUTER_PORT`: `8092`
- `TRON_NETWORK`: `mainnet`
- `TRON_RPC_URL`: `https://api.trongrid.io`
- `TRON_API_KEY`: `${TRON_API_KEY}`
- `USDT_CONTRACT_ADDRESS`: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`
- `TRON_CLIENT_URL`: `http://lucid-tron-client:8091`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `MIN_PAYOUT_AMOUNT`: `1.0`
- `MAX_PAYOUT_AMOUNT`: `10000.0`
- `PAYOUT_FEE`: `0.1`

**Health Check:**
- Port: `8092`
- Path: `/health`
- Command: `curl -fsS http://localhost:8092/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/payments:/data/payouts:rw`
- `/mnt/myssd/Lucid/Lucid/data/batches:/data/batches:rw`
- `/mnt/myssd/Lucid/Lucid/logs/payout-router:/app/logs:rw`

**Dependencies:**
- `lucid-tron-client` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `payment-systems/tron/docker-compose.yml`
- `infrastructure/compose/docker-compose.payment-systems.yaml`
- `configs/services/tron-payment.yml`

---

### 24. Wallet Manager (lucid-wallet-manager)
**Image:** `pickme/lucid-wallet-manager:latest-arm64`  
**Container Name:** `lucid-wallet-manager`  
**Hostname:** `lucid-wallet-manager`

**Function:**
- User wallet management (create, update, delete)
- Private key encryption and secure storage (AES-256-GCM)
- Wallet balance monitoring and real-time updates
- Multi-wallet support with categorization (hot, cold, multisig, hardware)
- Wallet lifecycle management
- Hardware wallet integration support
- Wallet transaction history tracking
- Secure wallet backup and recovery

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.29
```

**Ports:**
- `8093:8093` - Wallet Manager API
- `8103:8103ء` - Wallet Manager monitoring port

**Environment Variables:**
- `WALLET_MANAGER_URL`: `http://lucid-wallet-manager:8093`
- `WALLET_MANAGER_HOST`: `172.20.0.29`
- `WALLET_MANAGER_PORT`: `8093`
- `TRON_NETWORK`: `mainnet`
- `TRON_RPC_URL`: `https://api.trongrid.io`
- `TRON_API_KEY`: `${TRON_API_KEY}`
- `USDT_CONTRACT_ADDRESS`: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`
- `TRON_CLIENT_URL`: `http://lucid-tron-client:8091`
- `WALLET_ENCRYPTION_KEY`: `${WALLET_ENCRYPTION_KEY}`
- `WALLET_ENCRYPTION_ALGORITHM`: `AES-256-GCM`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`

**Health Check:**
- Port: `8093`
- Path: `/health`
- Command: `curl -fsS http://localhost:8093/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/wallets:/data/wallets:rw`
- `/mnt/myssd/Lucid/Lucid/data/keys:/data/keys:ro`
- `/mnt/myssd/Lucid/Lucid/logs/wallet-manager:/app/logs:rw`

**Dependencies:**
- `lucid-tron-client` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `payment-systems/tron/docker-compose.yml`
- `infrastructure/compose/docker-compose.payment-systems.yaml`
- `configs/services/tron-payment.yml`

**Electron-GUI Endpoint:** `http://172.20.0.29:8093/api/v1`

---

### 25. USDT Manager (lucid-usdt-manager)
**Image:** `pickme/lucid-usdt-manager:latest-arm64`  
**Container Name:** `lucid-usdt-manager`  
**Hostname:** `lucid-usdt-manager`

**Function:**
- USDT-TRC20 token operations and management
- USDT transfers and balance queries
- Token contract interaction (TR7NHqje intrudedxGTCi8q8ZY4pL8otSzgjLj6t)
- USDT transaction history tracking
- Token allowance management
- USDT balance caching and updates
- Transaction confirmation monitoring

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.30
```

**Ports:**
- `8094:8094` - USDT Manager API
- `8104:8104` - USDT Manager monitoring port

**Environment Variables:**
- `USDT_MANAGER_URL`: `http://lucid-usdt-manager:8094`
- `USDT_MANAGER_HOST`: `172.20.0.30`
- `USDT_MANAGER_PORT`: `8094`
- `TRON_NETWORK`: `mainnet`
- `TRON_RPC_URL`: `https://api.trongrid.io`
- `USDT_CONTRACT_ADDRESS`: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`
- `TRON_CLIENT_URL`: `http://lucid-tron-client:8091`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `MIN_PAYOUT_AMOUNT`: `1.0`
- `MAX_PAYOUT_AMOUNT`: `10000.0`

**Health Check:**
- Port: `8094`
- Path: `/health`
- Command: `curl -fsS http://localhost:8094/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/usdt:/data/usdt:rw`
- `/mnt/myssd/Lucid/Lucid/data/keys:/data/keys:ro`
- `/mnt/myssd/Lucid/Lucid/logs/usdt-manager:/app/logs:rw`

**Dependencies:**
- `lucid-tron-client` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `payment-systems/tron/docker-compose.yml`
- `infrastructure/compose/docker-compose.payment-systems.yaml`
- `configs/services/tron-payment.yml`

---

### 26. TRX Staking (lucid-trx-staking)
**Image:** `pickme/lucid-trx-staking:latest-arm64`  
**Container Name:** `lucid-trx-staking`  
**Hostname:** `lucid-trx-zapping`

**Function:**
- TRX staking operations and management
- Staking contract interactions (TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH)
- Staking duration and reward calculation
- Minimum staking amount enforcement (1000.0 TRX)
- Staking period management (3 days default)
- Reward rate tracking (0.1 default)
- Staking status monitoring and reporting

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.31
```

**Ports:**
- `8096:8096` - TRX Staking API
- `8105:8105` - TRX Staking monitoring port

**Environment Variables:**
- `TRX_STAKING_URL`: `http://lucid-trx-staking:8096`
- `TRX_STAKING_HOST`: `172.20.0.31`
- `TRX_STAKING_PORT`: `8096`
- `TRON_NETWORK`: `mainnet`
- `TRON_RPC_URL`: `https://api.trongrid.io`
- `STAKING_CONTRACT_ADDRESS`: `TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH`
- `TRON_CLIENT_URL`: `http://lucid-tron-client:8091`
- `MIN_STAKING_AMOUNT`: `1000.0`
- `STAKING_DURATION_DAYS`: `3`
- `STAKING_REWARD_RATE`: `0.1`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`

**Health Check:**
- Port: `8096`
- Path: `/health`
- Command: `curl -fsS http://localhost:8096/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/staking:/data/staking:rw`
- `/mnt/myssd/Lucid/Lucid/data/keys:/data/keys:ro`
- `/mnt/myssd/Lucid/Lucid/logs/trx-staking:/app/logs:rw`

**Dependencies:**
- `lucid-tron-client` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `payment-systems/tron/docker-compose.yml`
- `infrastructure/compose/docker-compose.payment-systems.yaml`
- `configs/services/tron-payment.yml`

---

### 27. Payment Gateway (lucid-payment-gateway)
**Image:** `pickme/lucid-payment-gateway:latest-arm64`  
**Container Name:** `lucid-payment-gateway`  
**Hostname:** `lucid-payment-gateway`

**Function:**
- Main payment processing orchestration
- Coordinates all TRON payment services
- Payment transaction management
- Payment status tracking and reporting
- Integration with payout router, wallet manager, and USDT manager
- Payment gateway API for external integrations
- Transaction timeout management (300 seconds)
- Rate limiting for payment requests (100 requests per minute)

**Network Configuration:**
```yaml
networks:
  lucid-pi-network:
    ipv4_address: 172.20.0.32
```

**Ports:**
- `8097:8097` - Payment Gateway API
- `8106:8106` - Payment Gateway monitoring port

**Environment Variables:**
- `PAYMENT_GATEWAY_URL`: `http://lucid-payment-gateway:8097`
- `PAYMENT_GATEWAY_HOST`: `172.20.0.32`
- `PAYMENT_GATEWAY_PORT`: `8097`
- `TRON_NETWORK`: `mainnet`
- `TRON_RPC_URL`: `https://api.trongrid.io`
- `USDT_CONTRACT_ADDRESS`: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`
- `TRON_CLIENT_URL`: `http://lucid-tron-client:8091`
- `PAYOUT_ROUTER_URL`: `http://lucid-payout-router:8092`
- `WALLET_MANAGER_URL`: `http://lucid-wallet-manager:8093`
- `USDT_MANAGER_URL`: `http://lucid-usdt-manager:8094`
- `API_GATEWAY_URL`: `http://lucid-api-gateway:8080`
- `MONGODB_URI`: `mongodb://lucid:{MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin`
- `REDIS_URL`: `redis://lucid-redis:6379/0`
- `MIN_PAYOUT_AMOUNT`: `1.0`
- `MAX_PAYOUT_AMOUNT`: `10000.0`
- `PAYOUT_FEE`: `0.1`
- `TRANSACTION_TIMEOUT`: `300`

**Health Check:**
- Port: `8097`
- Path: `/health`
- Command: `curl -fsS http://localhost:8097/health`

**Volumes:**
- `/mnt/myssd/Lucid/Lucid/data/gateway:/data/gateway:rw`
- `/mnt/myssd/Lucid/Lucid/data/keys:/data/keys:ro`
- `/mnt/myssd/Lucid/Lucid/logs/payment-gateway:/app/logs:rw`

**Dependencies:**
- `lucid-tron-client` (required)
- `lucid-payout-router` (required)
- `lucid-wallet-manager` (required)
- `lucid-usdt-manager` (required)
- `lucid-mongodb` (required)
- `lucid-redis` (required)

**Operates From:**
- `payment-systems/tron/docker-compose.yml`
- `infrastructure/compose/docker-compose.payment-systems.yaml`
- `configs/services/tron-payment.yml`
- `infrastructure/kubernetes/01-configmaps/tron-payment-config.yaml`

**Electron-GUI Endpoint:** `http://172.20.0.32:8097/api/v1`

---

## NETWORK SERVICE DEPENDENCY MAP

### Service Communication Flow
