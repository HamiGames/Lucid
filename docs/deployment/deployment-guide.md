# Lucid System Deployment Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-DEPLOY-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-01-14 |
| Based On | Master Build Plan v1.0.0 |

---

## Overview

This comprehensive deployment guide covers the complete Lucid blockchain system deployment across all 10 service clusters. The guide follows the distroless container architecture and ensures TRON isolation compliance.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Cluster (A)                  │
│  Ports: 8080 (HTTP), 8081 (HTTPS)                          │
│  Services: Gateway, Router, Load Balancer                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Blockchain Core Cluster (B)                  │
│  Ports: 8084-8087                                           │
│  Services: lucid_blocks, Consensus, Session Anchoring       │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Application Service Clusters                 │
│  Session Management, RDP Services, Node Management          │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Support Service Clusters                     │
│  Admin Interface, Storage, Authentication                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                TRON Payment Cluster (ISOLATED)              │
│  Port: 8085 (isolated)                                      │
│  Services: TRON Client, Payout Router, Wallet Manager       │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended | Production |
|-----------|---------|-------------|------------|
| CPU | 4 cores | 8 cores | 16+ cores |
| RAM | 8GB | 16GB | 32GB+ |
| Storage | 100GB SSD | 500GB SSD | 1TB+ NVMe |
| Network | 1Gbps | 10Gbps | 10Gbps+ |
| OS | Ubuntu 20.04+ | Ubuntu 22.04+ | Ubuntu 22.04+ |

### Software Dependencies

```bash
# Core dependencies
Docker Engine 24.0+
Docker Compose 2.20+
Python 3.11+
Node.js 18+ (for admin UI)
Git 2.30+

# Optional but recommended
Kubernetes 1.25+ (for production)
Helm 3.10+ (for K8s deployments)
```

---

## Phase 1: Foundation Deployment (Clusters 08-09)

### Cluster 08: Storage Database

#### MongoDB Deployment

```yaml
# docker-compose.foundation.yml
version: '3.8'

services:
  lucid-mongodb:
    image: mongo:7.0
    container_name: lucid-mongodb
    hostname: mongodb
    restart: unless-stopped
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    
    ports:
      - "27017:27017"
    
    volumes:
      - lucid-mongo-data:/data/db
      - ./configs/mongodb/mongod.conf:/etc/mongod.conf:ro
      - ./scripts/database/init_schema.js:/docker-entrypoint-initdb.d/init_schema.js:ro
    
    networks:
      - lucid-network
    
    command: ["mongod", "--config", "/etc/mongod.conf", "--replSet", "rs0"]
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand({ping: 1})", "--quiet"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  lucid-redis:
    image: redis:7.2-alpine
    container_name: lucid-redis
    hostname: redis
    restart: unless-stopped
    
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    
    ports:
      - "6379:6379"
    
    volumes:
      - lucid-redis-data:/data
      - ./configs/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
    
    networks:
      - lucid-network
    
    command: ["redis-server", "/usr/local/etc/redis/redis.conf"]
    
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  lucid-elasticsearch:
    image: elasticsearch:8.11.0
    container_name: lucid-elasticsearch
    hostname: elasticsearch
    restart: unless-stopped
    
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    
    ports:
      - "9200:9200"
    
    volumes:
      - lucid-elasticsearch-data:/usr/share/elasticsearch/data
      - ./configs/elasticsearch/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml:ro
    
    networks:
      - lucid-network
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  lucid-mongo-data:
    name: lucid-mongo-data
  lucid-redis-data:
    name: lucid-redis-data
  lucid-elasticsearch-data:
    name: lucid-elasticsearch-data

networks:
  lucid-network:
    name: lucid-network
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
```

#### Deployment Commands

```bash
# Create environment file
cat > .env.foundation << EOF
MONGO_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
EOF

# Deploy foundation services
docker-compose -f docker-compose.foundation.yml up -d

# Initialize MongoDB replica set
docker exec lucid-mongodb mongosh --eval "rs.initiate()"

# Verify deployment
curl -f http://localhost:9200/_cluster/health
docker exec lucid-redis redis-cli ping
```

### Cluster 09: Authentication

#### Authentication Service Deployment

```yaml
# docker-compose.auth.yml
version: '3.8'

services:
  lucid-auth-service:
    image: ghcr.io/hamigames/lucid/auth-service:latest
    container_name: lucid-auth-service
    hostname: auth-service
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-auth-service
      - PORT=8089
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URI=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - MFA_SECRET=${MFA_SECRET}
      - LOG_LEVEL=INFO
    
    ports:
      - "8089:8089"
    
    volumes:
      - ./configs/auth:/app/config:ro
      - ./logs/auth:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-mongodb
      - lucid-redis
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8089/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## Phase 2: Core Services Deployment (Clusters 01-02, 10)

### Cluster 01: API Gateway

```yaml
# docker-compose.api-gateway.yml
version: '3.8'

services:
  lucid-api-gateway:
    image: ghcr.io/hamigames/lucid/api-gateway:latest
    container_name: lucid-api-gateway
    hostname: api-gateway
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-api-gateway
      - PORT=8080
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URI=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - JWT_SECRET=${JWT_SECRET}
      - LOG_LEVEL=INFO
    
    ports:
      - "8080:8080"
      - "8081:8081"
    
    volumes:
      - ./configs/api-gateway:/app/config:ro
      - ./logs/api-gateway:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-mongodb
      - lucid-redis
      - lucid-auth-service
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Cluster 02: Blockchain Core

```yaml
# docker-compose.blockchain.yml
version: '3.8'

services:
  lucid-blockchain-engine:
    image: ghcr.io/hamigames/lucid/blockchain-engine:latest
    container_name: lucid-blockchain-engine
    hostname: blockchain-engine
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-blocks
      - PORT=8084
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid_blocks?authSource=admin
      - CONSENSUS_ALGORITHM=PoOT
      - BLOCK_TIME_SECONDS=10
      - LOG_LEVEL=INFO
    
    ports:
      - "8084:8084"
    
    volumes:
      - lucid-blockchain-data:/data/blocks
      - ./configs/blockchain:/app/config:ro
      - ./logs/blockchain:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-mongodb
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8084/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-session-anchoring:
    image: ghcr.io/hamigames/lucid/session-anchoring:latest
    container_name: lucid-session-anchoring
    hostname: session-anchoring
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-session-anchoring
      - PORT=8085
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid_blocks?authSource=admin
      - LOG_LEVEL=INFO
    
    ports:
      - "8085:8085"
    
    volumes:
      - lucid-merkle-data:/data/merkle
      - ./configs/session-anchoring:/app/config:ro
      - ./logs/session-anchoring:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-blockchain-engine
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8085/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  lucid-blockchain-data:
    name: lucid-blockchain-data
  lucid-merkle-data:
    name: lucid-merkle-data
```

### Cluster 10: Cross-Cluster Integration

```yaml
# docker-compose.service-mesh.yml
version: '3.8'

services:
  lucid-consul:
    image: consul:1.16
    container_name: lucid-consul
    hostname: consul
    restart: unless-stopped
    
    environment:
      - CONSUL_BIND_INTERFACE=eth0
      - CONSUL_CLIENT_INTERFACE=eth0
    
    ports:
      - "8500:8500"
      - "8600:8600/udp"
    
    volumes:
      - lucid-consul-data:/consul/data
      - ./configs/consul:/consul/config:ro
    
    networks:
      - lucid-network
    
    command: ["consul", "agent", "-server", "-bootstrap-expect=1", "-ui", "-client=0.0.0.0", "-bind=0.0.0.0"]
    
    healthcheck:
      test: ["CMD", "consul", "members"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  lucid-envoy:
    image: envoyproxy/envoy:v1.28
    container_name: lucid-envoy
    hostname: envoy
    restart: unless-stopped
    
    ports:
      - "9901:9901"  # Admin interface
      - "10000:10000"  # HTTP proxy
    
    volumes:
      - ./configs/envoy:/etc/envoy:ro
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-consul
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9901/server_info"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

volumes:
  lucid-consul-data:
    name: lucid-consul-data
```

---

## Phase 3: Application Services Deployment (Clusters 03-05)

### Cluster 03: Session Management

```yaml
# docker-compose.session.yml
version: '3.8'

services:
  lucid-session-pipeline:
    image: ghcr.io/hamigames/lucid/session-pipeline:latest
    container_name: lucid-session-pipeline
    hostname: session-pipeline
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-session-pipeline
      - PORT=8083
      - API_GATEWAY_URL=http://lucid-api-gateway:8080
      - LOG_LEVEL=INFO
    
    ports:
      - "8083:8083"
    
    volumes:
      - ./configs/session-pipeline:/app/config:ro
      - ./logs/session-pipeline:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-api-gateway
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8083/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-session-recorder:
    image: ghcr.io/hamigames/lucid/session-recorder:latest
    container_name: lucid-session-recorder
    hostname: session-recorder
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-session-recorder
      - PORT=8084
      - SESSION_PIPELINE_URL=http://lucid-session-pipeline:8083
      - LOG_LEVEL=INFO
    
    ports:
      - "8084:8084"
    
    volumes:
      - lucid-session-data:/data/sessions
      - ./configs/session-recorder:/app/config:ro
      - ./logs/session-recorder:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-session-pipeline
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8084/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-chunk-processor:
    image: ghcr.io/hamigames/lucid/chunk-processor:latest
    container_name: lucid-chunk-processor
    hostname: chunk-processor
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-chunk-processor
      - PORT=8085
      - SESSION_RECORDER_URL=http://lucid-session-recorder:8084
      - LOG_LEVEL=INFO
    
    ports:
      - "8085:8085"
    
    volumes:
      - lucid-chunk-data:/data/chunks
      - ./configs/chunk-processor:/app/config:ro
      - ./logs/chunk-processor:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-session-recorder
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8085/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-session-storage:
    image: ghcr.io/hamigames/lucid/session-storage:latest
    container_name: lucid-session-storage
    hostname: session-storage
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-session-storage
      - PORT=8086
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - LOG_LEVEL=INFO
    
    ports:
      - "8086:8086"
    
    volumes:
      - lucid-session-storage-data:/data/storage
      - ./configs/session-storage:/app/config:ro
      - ./logs/session-storage:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-mongodb
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-session-api:
    image: ghcr.io/hamigames/lucid/session-api:latest
    container_name: lucid-session-api
    hostname: session-api
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-session-api
      - PORT=8087
      - API_GATEWAY_URL=http://lucid-api-gateway:8080
      - SESSION_STORAGE_URL=http://lucid-session-storage:8086
      - LOG_LEVEL=INFO
    
    ports:
      - "8087:8087"
    
    volumes:
      - ./configs/session-api:/app/config:ro
      - ./logs/session-api:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-api-gateway
      - lucid-session-storage
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8087/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  lucid-session-data:
    name: lucid-session-data
  lucid-chunk-data:
    name: lucid-chunk-data
  lucid-session-storage-data:
    name: lucid-session-storage-data
```

### Cluster 04: RDP Services

```yaml
# docker-compose.rdp.yml
version: '3.8'

services:
  lucid-rdp-manager:
    image: ghcr.io/hamigames/lucid/rdp-manager:latest
    container_name: lucid-rdp-manager
    hostname: rdp-manager
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-rdp-manager
      - PORT=8090
      - API_GATEWAY_URL=http://lucid-api-gateway:8080
      - LOG_LEVEL=INFO
    
    ports:
      - "8090:8090"
    
    volumes:
      - ./configs/rdp-manager:/app/config:ro
      - ./logs/rdp-manager:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-api-gateway
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-xrdp:
    image: ghcr.io/hamigames/lucid/xrdp:latest
    container_name: lucid-xrdp
    hostname: xrdp
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-xrdp
      - PORT=8091
      - RDP_MANAGER_URL=http://lucid-rdp-manager:8090
      - LOG_LEVEL=INFO
    
    ports:
      - "8091:8091"
      - "13389-14389:13389-14389"  # RDP port range
    
    volumes:
      - ./configs/xrdp:/app/config:ro
      - ./logs/xrdp:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-rdp-manager
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8091/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-session-controller:
    image: ghcr.io/hamigames/lucid/session-controller:latest
    container_name: lucid-session-controller
    hostname: session-controller
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-session-controller
      - PORT=8092
      - XRDP_URL=http://lucid-xrdp:8091
      - LOG_LEVEL=INFO
    
    ports:
      - "8092:8092"
    
    volumes:
      - ./configs/session-controller:/app/config:ro
      - ./logs/session-controller:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-xrdp
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8092/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-resource-monitor:
    image: ghcr.io/hamigames/lucid/resource-monitor:latest
    container_name: lucid-resource-monitor
    hostname: resource-monitor
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-resource-monitor
      - PORT=8093
      - SESSION_CONTROLLER_URL=http://lucid-session-controller:8092
      - LOG_LEVEL=INFO
    
    ports:
      - "8093:8093"
    
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - ./configs/resource-monitor:/app/config:ro
      - ./logs/resource-monitor:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-session-controller
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8093/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Cluster 05: Node Management

```yaml
# docker-compose.node.yml
version: '3.8'

services:
  lucid-node-management:
    image: ghcr.io/hamigames/lucid/node-management:latest
    container_name: lucid-node-management
    hostname: node-management
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-node-management
      - PORT=8095
      - API_GATEWAY_URL=http://lucid-api-gateway:8080
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - LOG_LEVEL=INFO
    
    ports:
      - "8095:8095"
    
    volumes:
      - ./configs/node-management:/app/config:ro
      - ./logs/node-management:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-api-gateway
      - lucid-mongodb
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8095/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## Phase 4: Support Services Deployment (Clusters 06-07)

### Cluster 06: Admin Interface

```yaml
# docker-compose.admin.yml
version: '3.8'

services:
  lucid-admin-interface:
    image: ghcr.io/hamigames/lucid/admin-interface:latest
    container_name: lucid-admin-interface
    hostname: admin-interface
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-admin-interface
      - PORT=8083
      - API_GATEWAY_URL=http://lucid-api-gateway:8080
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - LOG_LEVEL=INFO
    
    ports:
      - "8083:8083"
    
    volumes:
      - ./configs/admin-interface:/app/config:ro
      - ./logs/admin-interface:/app/logs
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-api-gateway
      - lucid-mongodb
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8083/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Cluster 07: TRON Payment (Isolated)

```yaml
# docker-compose.tron.yml
version: '3.8'

services:
  lucid-tron-client:
    image: ghcr.io/hamigames/lucid/tron-client:latest
    container_name: lucid-tron-client
    hostname: tron-client
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-tron-client
      - PORT=8085
      - TRON_NETWORK=mainnet
      - TRON_API_URL=https://api.trongrid.io
      - LOG_LEVEL=INFO
    
    ports:
      - "8085:8085"
    
    volumes:
      - ./configs/tron-client:/app/config:ro
      - ./logs/tron-client:/app/logs
    
    networks:
      - lucid-tron-network  # Isolated network
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8085/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-payout-router:
    image: ghcr.io/hamigames/lucid/payout-router:latest
    container_name: lucid-payout-router
    hostname: payout-router
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-payout-router
      - PORT=8086
      - TRON_CLIENT_URL=http://lucid-tron-client:8085
      - LOG_LEVEL=INFO
    
    ports:
      - "8086:8086"
    
    volumes:
      - ./configs/payout-router:/app/config:ro
      - ./logs/payout-router:/app/logs
    
    networks:
      - lucid-tron-network
    
    depends_on:
      - lucid-tron-client
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-wallet-manager:
    image: ghcr.io/hamigames/lucid/wallet-manager:latest
    container_name: lucid-wallet-manager
    hostname: wallet-manager
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-wallet-manager
      - PORT=8087
      - TRON_CLIENT_URL=http://lucid-tron-client:8085
      - LOG_LEVEL=INFO
    
    ports:
      - "8087:8087"
    
    volumes:
      - lucid-wallet-data:/data/wallets
      - ./configs/wallet-manager:/app/config:ro
      - ./logs/wallet-manager:/app/logs
    
    networks:
      - lucid-tron-network
    
    depends_on:
      - lucid-tron-client
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8087/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-usdt-manager:
    image: ghcr.io/hamigames/lucid/usdt-manager:latest
    container_name: lucid-usdt-manager
    hostname: usdt-manager
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-usdt-manager
      - PORT=8088
      - TRON_CLIENT_URL=http://lucid-tron-client:8085
      - USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
      - LOG_LEVEL=INFO
    
    ports:
      - "8088:8088"
    
    volumes:
      - ./configs/usdt-manager:/app/config:ro
      - ./logs/usdt-manager:/app/logs
    
    networks:
      - lucid-tron-network
    
    depends_on:
      - lucid-tron-client
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-trx-staking:
    image: ghcr.io/hamigames/lucid/trx-staking:latest
    container_name: lucid-trx-staking
    hostname: trx-staking
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-trx-staking
      - PORT=8089
      - TRON_CLIENT_URL=http://lucid-tron-client:8085
      - LOG_LEVEL=INFO
    
    ports:
      - "8089:8089"
    
    volumes:
      - ./configs/trx-staking:/app/config:ro
      - ./logs/trx-staking:/app/logs
    
    networks:
      - lucid-tron-network
    
    depends_on:
      - lucid-tron-client
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8089/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-payment-gateway:
    image: ghcr.io/hamigames/lucid/payment-gateway:latest
    container_name: lucid-payment-gateway
    hostname: payment-gateway
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-payment-gateway
      - PORT=8090
      - PAYOUT_ROUTER_URL=http://lucid-payout-router:8086
      - WALLET_MANAGER_URL=http://lucid-wallet-manager:8087
      - USDT_MANAGER_URL=http://lucid-usdt-manager:8088
      - LOG_LEVEL=INFO
    
    ports:
      - "8090:8090"
    
    volumes:
      - ./configs/payment-gateway:/app/config:ro
      - ./logs/payment-gateway:/app/logs
    
    networks:
      - lucid-tron-network
    
    depends_on:
      - lucid-payout-router
      - lucid-wallet-manager
      - lucid-usdt-manager
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  lucid-wallet-data:
    name: lucid-wallet-data

networks:
  lucid-tron-network:
    name: lucid-tron-network
    driver: bridge
    internal: true  # Isolated network
    ipam:
      config:
        - subnet: 172.21.0.0/16
          gateway: 172.21.0.1
```

---

## Complete System Deployment

### Master Docker Compose

```yaml
# docker-compose.all.yml
version: '3.8'

services:
  # Include all services from previous phases
  # Foundation services
  lucid-mongodb:
    extends:
      file: docker-compose.foundation.yml
      service: lucid-mongodb
  
  lucid-redis:
    extends:
      file: docker-compose.foundation.yml
      service: lucid-redis
  
  lucid-elasticsearch:
    extends:
      file: docker-compose.foundation.yml
      service: lucid-elasticsearch
  
  # Authentication
  lucid-auth-service:
    extends:
      file: docker-compose.auth.yml
      service: lucid-auth-service
  
  # API Gateway
  lucid-api-gateway:
    extends:
      file: docker-compose.api-gateway.yml
      service: lucid-api-gateway
  
  # Blockchain Core
  lucid-blockchain-engine:
    extends:
      file: docker-compose.blockchain.yml
      service: lucid-blockchain-engine
  
  lucid-session-anchoring:
    extends:
      file: docker-compose.blockchain.yml
      service: lucid-session-anchoring
  
  # Service Mesh
  lucid-consul:
    extends:
      file: docker-compose.service-mesh.yml
      service: lucid-consul
  
  lucid-envoy:
    extends:
      file: docker-compose.service-mesh.yml
      service: lucid-envoy
  
  # Session Management
  lucid-session-pipeline:
    extends:
      file: docker-compose.session.yml
      service: lucid-session-pipeline
  
  lucid-session-recorder:
    extends:
      file: docker-compose.session.yml
      service: lucid-session-recorder
  
  lucid-chunk-processor:
    extends:
      file: docker-compose.session.yml
      service: lucid-chunk-processor
  
  lucid-session-storage:
    extends:
      file: docker-compose.session.yml
      service: lucid-session-storage
  
  lucid-session-api:
    extends:
      file: docker-compose.session.yml
      service: lucid-session-api
  
  # RDP Services
  lucid-rdp-manager:
    extends:
      file: docker-compose.rdp.yml
      service: lucid-rdp-manager
  
  lucid-xrdp:
    extends:
      file: docker-compose.rdp.yml
      service: lucid-xrdp
  
  lucid-session-controller:
    extends:
      file: docker-compose.rdp.yml
      service: lucid-session-controller
  
  lucid-resource-monitor:
    extends:
      file: docker-compose.rdp.yml
      service: lucid-resource-monitor
  
  # Node Management
  lucid-node-management:
    extends:
      file: docker-compose.node.yml
      service: lucid-node-management
  
  # Admin Interface
  lucid-admin-interface:
    extends:
      file: docker-compose.admin.yml
      service: lucid-admin-interface
  
  # TRON Payment (Isolated)
  lucid-tron-client:
    extends:
      file: docker-compose.tron.yml
      service: lucid-tron-client
  
  lucid-payout-router:
    extends:
      file: docker-compose.tron.yml
      service: lucid-payout-router
  
  lucid-wallet-manager:
    extends:
      file: docker-compose.tron.yml
      service: lucid-wallet-manager
  
  lucid-usdt-manager:
    extends:
      file: docker-compose.tron.yml
      service: lucid-usdt-manager
  
  lucid-trx-staking:
    extends:
      file: docker-compose.tron.yml
      service: lucid-trx-staking
  
  lucid-payment-gateway:
    extends:
      file: docker-compose.tron.yml
      service: lucid-payment-gateway

# Include all volumes and networks
volumes:
  lucid-mongo-data:
  lucid-redis-data:
  lucid-elasticsearch-data:
  lucid-blockchain-data:
  lucid-merkle-data:
  lucid-consul-data:
  lucid-session-data:
  lucid-chunk-data:
  lucid-session-storage-data:
  lucid-wallet-data:

networks:
  lucid-network:
    name: lucid-network
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
  
  lucid-tron-network:
    name: lucid-tron-network
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.21.0.0/16
          gateway: 172.21.0.1
```

### Deployment Script

```bash
#!/bin/bash
# scripts/deployment/deploy-all.sh

set -e

ENVIRONMENT="${1:-production}"
VERSION="${2:-latest}"

echo "Starting Lucid system deployment..."
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"

# Create environment file
cat > .env.production << EOF
# Database Configuration
MONGO_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)

# Security Configuration
JWT_SECRET=$(openssl rand -base64 64)
MFA_SECRET=$(openssl rand -base64 32)

# Service Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# Network Configuration
LUCID_NETWORK_SUBNET=172.20.0.0/16
TRON_NETWORK_SUBNET=172.21.0.0/16
EOF

# Deploy in phases
echo "Phase 1: Deploying foundation services..."
docker-compose -f docker-compose.foundation.yml up -d

echo "Waiting for foundation services to be ready..."
sleep 30

echo "Phase 2: Deploying authentication..."
docker-compose -f docker-compose.auth.yml up -d

echo "Waiting for authentication to be ready..."
sleep 20

echo "Phase 3: Deploying core services..."
docker-compose -f docker-compose.api-gateway.yml up -d
docker-compose -f docker-compose.blockchain.yml up -d
docker-compose -f docker-compose.service-mesh.yml up -d

echo "Waiting for core services to be ready..."
sleep 30

echo "Phase 4: Deploying application services..."
docker-compose -f docker-compose.session.yml up -d
docker-compose -f docker-compose.rdp.yml up -d
docker-compose -f docker-compose.node.yml up -d

echo "Waiting for application services to be ready..."
sleep 30

echo "Phase 5: Deploying support services..."
docker-compose -f docker-compose.admin.yml up -d
docker-compose -f docker-compose.tron.yml up -d

echo "Waiting for support services to be ready..."
sleep 30

echo "Running health checks..."
./scripts/health/check-all-services.sh

echo "Deployment completed successfully!"
echo "System is ready for use."
```

---

## Environment Configuration

### Production Environment

```bash
# .env.production
# Database Configuration
MONGO_PASSWORD=your-secure-mongo-password-here
REDIS_PASSWORD=your-secure-redis-password-here

# Security Configuration
JWT_SECRET=your-256-bit-jwt-secret-key-here
MFA_SECRET=your-mfa-secret-key-here

# Service Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# Network Configuration
LUCID_NETWORK_SUBNET=172.20.0.0/16
TRON_NETWORK_SUBNET=172.21.0.0/16

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PUBLIC_REQ_PER_MIN=100
RATE_LIMIT_AUTH_REQ_PER_MIN=1000
RATE_LIMIT_ADMIN_REQ_PER_MIN=10000

# Blockchain Configuration
CONSENSUS_ALGORITHM=PoOT
BLOCK_TIME_SECONDS=10
BLOCK_SIZE_LIMIT_MB=1

# TRON Configuration
TRON_NETWORK=mainnet
TRON_API_URL=https://api.trongrid.io
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
```

### Development Environment

```bash
# .env.development
# Database Configuration
MONGO_PASSWORD=lucid
REDIS_PASSWORD=lucid

# Security Configuration
JWT_SECRET=dev-jwt-secret-change-in-production
MFA_SECRET=dev-mfa-secret-change-in-production

# Service Configuration
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true

# Network Configuration
LUCID_NETWORK_SUBNET=172.20.0.0/16
TRON_NETWORK_SUBNET=172.21.0.0/16

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PUBLIC_REQ_PER_MIN=10000
RATE_LIMIT_AUTH_REQ_PER_MIN=100000
RATE_LIMIT_ADMIN_REQ_PER_MIN=1000000

# Blockchain Configuration
CONSENSUS_ALGORITHM=PoOT
BLOCK_TIME_SECONDS=5
BLOCK_SIZE_LIMIT_MB=1

# TRON Configuration
TRON_NETWORK=shasta
TRON_API_URL=https://api.shasta.trongrid.io
USDT_CONTRACT_ADDRESS=TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs
```

---

## Health Checks

### System Health Check Script

```bash
#!/bin/bash
# scripts/health/check-all-services.sh

set -e

echo "=== Lucid System Health Check ==="

# Foundation services
echo "Checking foundation services..."
curl -f http://localhost:27017/ || echo "MongoDB: FAILED"
curl -f http://localhost:6379/ || echo "Redis: FAILED"
curl -f http://localhost:9200/_cluster/health || echo "Elasticsearch: FAILED"

# Authentication
echo "Checking authentication..."
curl -f http://localhost:8089/health || echo "Auth Service: FAILED"

# API Gateway
echo "Checking API Gateway..."
curl -f http://localhost:8080/health || echo "API Gateway: FAILED"

# Blockchain Core
echo "Checking blockchain core..."
curl -f http://localhost:8084/health || echo "Blockchain Engine: FAILED"
curl -f http://localhost:8085/health || echo "Session Anchoring: FAILED"

# Service Mesh
echo "Checking service mesh..."
curl -f http://localhost:8500/v1/status/leader || echo "Consul: FAILED"
curl -f http://localhost:9901/server_info || echo "Envoy: FAILED"

# Session Management
echo "Checking session management..."
curl -f http://localhost:8083/health || echo "Session Pipeline: FAILED"
curl -f http://localhost:8084/health || echo "Session Recorder: FAILED"
curl -f http://localhost:8085/health || echo "Chunk Processor: FAILED"
curl -f http://localhost:8086/health || echo "Session Storage: FAILED"
curl -f http://localhost:8087/health || echo "Session API: FAILED"

# RDP Services
echo "Checking RDP services..."
curl -f http://localhost:8090/health || echo "RDP Manager: FAILED"
curl -f http://localhost:8091/health || echo "XRDP: FAILED"
curl -f http://localhost:8092/health || echo "Session Controller: FAILED"
curl -f http://localhost:8093/health || echo "Resource Monitor: FAILED"

# Node Management
echo "Checking node management..."
curl -f http://localhost:8095/health || echo "Node Management: FAILED"

# Admin Interface
echo "Checking admin interface..."
curl -f http://localhost:8083/health || echo "Admin Interface: FAILED"

# TRON Payment (Isolated)
echo "Checking TRON payment services..."
curl -f http://localhost:8085/health || echo "TRON Client: FAILED"
curl -f http://localhost:8086/health || echo "Payout Router: FAILED"
curl -f http://localhost:8087/health || echo "Wallet Manager: FAILED"
curl -f http://localhost:8088/health || echo "USDT Manager: FAILED"
curl -f http://localhost:8089/health || echo "TRX Staking: FAILED"
curl -f http://localhost:8090/health || echo "Payment Gateway: FAILED"

echo "=== Health Check Complete ==="
```

---

## Monitoring and Logging

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'lucid-foundation'
    static_configs:
      - targets: ['lucid-mongodb:27017', 'lucid-redis:6379', 'lucid-elasticsearch:9200']
    scrape_interval: 30s

  - job_name: 'lucid-auth'
    static_configs:
      - targets: ['lucid-auth-service:8089']
    scrape_interval: 30s

  - job_name: 'lucid-api-gateway'
    static_configs:
      - targets: ['lucid-api-gateway:8080']
    scrape_interval: 30s

  - job_name: 'lucid-blockchain'
    static_configs:
      - targets: ['lucid-blockchain-engine:8084', 'lucid-session-anchoring:8085']
    scrape_interval: 30s

  - job_name: 'lucid-session'
    static_configs:
      - targets: ['lucid-session-pipeline:8083', 'lucid-session-recorder:8084', 'lucid-chunk-processor:8085', 'lucid-session-storage:8086', 'lucid-session-api:8087']
    scrape_interval: 30s

  - job_name: 'lucid-rdp'
    static_configs:
      - targets: ['lucid-rdp-manager:8090', 'lucid-xrdp:8091', 'lucid-session-controller:8092', 'lucid-resource-monitor:8093']
    scrape_interval: 30s

  - job_name: 'lucid-node'
    static_configs:
      - targets: ['lucid-node-management:8095']
    scrape_interval: 30s

  - job_name: 'lucid-admin'
    static_configs:
      - targets: ['lucid-admin-interface:8083']
    scrape_interval: 30s

  - job_name: 'lucid-tron'
    static_configs:
      - targets: ['lucid-tron-client:8085', 'lucid-payout-router:8086', 'lucid-wallet-manager:8087', 'lucid-usdt-manager:8088', 'lucid-trx-staking:8089', 'lucid-payment-gateway:8090']
    scrape_interval: 30s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Lucid System Overview",
    "panels": [
      {
        "title": "Service Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=~\"lucid-.*\"}",
            "legendFormat": "{{job}}"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      }
    ]
  }
}
```

---

## Security Considerations

### Container Security

All containers use distroless base images for minimal attack surface:

```dockerfile
# Example distroless container
FROM gcr.io/distroless/python3-debian12:latest

# Create non-root user
USER 65534:65534

# Copy application with proper permissions
COPY --chown=65534:65534 . /app
WORKDIR /app

# Set security options
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/app/health_check.sh"]

CMD ["python", "-m", "main"]
```

### Network Security

```yaml
# Network isolation
networks:
  lucid-network:
    driver: bridge
    internal: false  # Allow external access only through defined ports
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
  
  lucid-tron-network:
    driver: bridge
    internal: true  # Completely isolated TRON network
    ipam:
      config:
        - subnet: 172.21.0.0/16
          gateway: 172.21.0.1
```

### Secrets Management

```bash
#!/bin/bash
# scripts/secrets/generate-secrets.sh

# Generate secure secrets
JWT_SECRET=$(openssl rand -base64 64)
MFA_SECRET=$(openssl rand -base64 32)
MONGO_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)

# Create secrets file
cat > .env.secrets << EOF
JWT_SECRET=$JWT_SECRET
MFA_SECRET=$MFA_SECRET
MONGO_PASSWORD=$MONGO_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
EOF

# Set proper permissions
chmod 600 .env.secrets

echo "Secrets generated and saved to .env.secrets"
```

---

## Validation

### Deployment Validation

```bash
#!/bin/bash
# scripts/validation/validate-deployment.sh

set -e

echo "=== Lucid Deployment Validation ==="

# Check all containers are running
echo "Checking container status..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep lucid

# Check all services are healthy
echo "Running health checks..."
./scripts/health/check-all-services.sh

# Check network connectivity
echo "Checking network connectivity..."
docker network ls | grep lucid

# Check volumes are mounted
echo "Checking volumes..."
docker volume ls | grep lucid

# Check logs for errors
echo "Checking for errors in logs..."
docker logs lucid-api-gateway 2>&1 | grep -i error | tail -5
docker logs lucid-blockchain-engine 2>&1 | grep -i error | tail -5

echo "=== Deployment Validation Complete ==="
```

---

## References

- [Master Build Plan](../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)
- [API Gateway Build Guide](../plan/API_plans/00-master-architecture/02-CLUSTER_01_API_GATEWAY_BUILD_GUIDE.md)
- [Blockchain Core Build Guide](../plan/API_plans/00-master-architecture/03-CLUSTER_02_BLOCKCHAIN_CORE_BUILD_GUIDE.md)
- [TRON Isolation Architecture](../docs/architecture/TRON-PAYMENT-ISOLATION.md)
- [Distroless Container Spec](../docs/architecture/DISTROLESS-CONTAINER-SPEC.md)

---

**Document Version**: 1.0.0  
**Status**: ACTIVE  
**Last Updated**: 2025-01-14
