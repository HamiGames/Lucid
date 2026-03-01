# Phase 2 Docker Compose Generation

## Overview
Generate Phase 2 Docker Compose file for core services with proper service dependencies and network configuration.

## Location
`configs/docker/docker-compose.core.yml`

## Phase 2 Services

### Core Services
- **API Gateway** - Routing, rate limiting, authentication middleware
- **Service Mesh Controller** - Service discovery, mTLS certificate management
- **Blockchain Engine** - Consensus mechanism, block creation
- **Session Anchoring** - Session data anchoring to blockchain
- **Block Manager** - Block validation and chain management
- **Data Chain** - Data indexing and querying

## Docker Compose Configuration

### File: `configs/docker/docker-compose.core.yml`

```yaml
version: '3.8'

services:
  # API Gateway Service
  lucid-api-gateway:
    image: pickme/lucid-api-gateway:latest-arm64
    container_name: lucid-api-gateway
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - API_GATEWAY_PORT=8080
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - BLOCKCHAIN_CORE_URL=http://lucid-blockchain-engine:8084
      - SESSION_API_URL=http://lucid-session-api:8087
      - NODE_MANAGEMENT_URL=http://lucid-node-management:8095
      - ADMIN_INTERFACE_URL=http://lucid-admin-interface:8083
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - RATE_LIMIT_FREE=100
      - RATE_LIMIT_PREMIUM=1000
      - RATE_LIMIT_ENTERPRISE=10000
    depends_on:
      - lucid-auth-service
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - api_gateway_logs:/app/logs

  # Service Mesh Controller
  lucid-service-mesh-controller:
    image: pickme/lucid-service-mesh-controller:latest-arm64
    container_name: lucid-service-mesh-controller
    restart: unless-stopped
    ports:
      - "8081:8081"
      - "8500:8500"
    environment:
      - SERVICE_MESH_PORT=8081
      - CONSUL_PORT=8500
      - CONSUL_DATACENTER=lucid-dc
      - CONSUL_BIND_ADDR=0.0.0.0
      - CONSUL_CLIENT_ADDR=0.0.0.0
      - CONSUL_UI_ENABLED=true
      - CONSUL_BOOTSTRAP_EXPECT=1
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8081/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - consul_data:/tmp/consul
      - service_mesh_logs:/app/logs

  # Blockchain Engine
  lucid-blockchain-engine:
    image: pickme/lucid-blockchain-engine:latest-arm64
    container_name: lucid-blockchain-engine
    restart: unless-stopped
    ports:
      - "8084:8084"
    environment:
      - BLOCKCHAIN_CORE_PORT=8084
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - BLOCK_INTERVAL=10
      - CONSENSUS_PARTICIPANTS=3
      - BLOCK_SIZE_LIMIT=1048576
      - TRANSACTION_LIMIT=1000
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8084/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - blockchain_data:/app/data
      - blockchain_logs:/app/logs

  # Session Anchoring
  lucid-session-anchoring:
    image: pickme/lucid-session-anchoring:latest-arm64
    container_name: lucid-session-anchoring
    restart: unless-stopped
    ports:
      - "8086:8086"
    environment:
      - SESSION_ANCHORING_PORT=8086
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - MERKLE_TREE_DEPTH=10
      - ANCHORING_BATCH_SIZE=100
      - PROOF_GENERATION_TIMEOUT=30
    depends_on:
      - lucid-blockchain-engine
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8086/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - anchoring_data:/app/data
      - anchoring_logs:/app/logs

  # Block Manager
  lucid-block-manager:
    image: pickme/lucid-block-manager:latest-arm64
    container_name: lucid-block-manager
    restart: unless-stopped
    ports:
      - "8088:8088"
    environment:
      - BLOCK_MANAGER_PORT=8088
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - MAX_BLOCKS_TO_KEEP=10000
      - BLOCK_VALIDATION_ENABLED=true
      - CHAIN_MAINTENANCE_INTERVAL=60
    depends_on:
      - lucid-blockchain-engine
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8088/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - block_manager_data:/app/data
      - block_manager_logs:/app/logs

  # Data Chain
  lucid-data-chain:
    image: pickme/lucid-data-chain:latest-arm64
    container_name: lucid-data-chain
    restart: unless-stopped
    ports:
      - "8090:8090"
    environment:
      - DATA_CHAIN_PORT=8090
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - ELASTICSEARCH_URL=${ELASTICSEARCH_URL}
      - INDEXING_BATCH_SIZE=1000
      - QUERY_CACHE_SIZE=10000
      - DATA_SYNC_INTERVAL=30
    depends_on:
      - lucid-mongodb
      - lucid-redis
      - lucid-elasticsearch
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8090/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - data_chain_data:/app/data
      - data_chain_logs:/app/logs

# Networks
networks:
  lucid-pi-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1

# Volumes
volumes:
  # API Gateway volumes
  api_gateway_logs:
    driver: local

  # Service Mesh volumes
  consul_data:
    driver: local
  service_mesh_logs:
    driver: local

  # Blockchain volumes
  blockchain_data:
    driver: local
  blockchain_logs:
    driver: local

  # Session Anchoring volumes
  anchoring_data:
    driver: local
  anchoring_logs:
    driver: local

  # Block Manager volumes
  block_manager_data:
    driver: local
  block_manager_logs:
    driver: local

  # Data Chain volumes
  data_chain_data:
    driver: local
  data_chain_logs:
    driver: local
```

## Service Dependencies

### Dependency Graph
```
lucid-mongodb (Phase 1)
    ↓
lucid-redis (Phase 1)
    ↓
lucid-elasticsearch (Phase 1)
    ↓
lucid-auth-service (Phase 1)
    ↓
lucid-api-gateway (Phase 2)
    ↓
lucid-service-mesh-controller (Phase 2)
    ↓
lucid-blockchain-engine (Phase 2)
    ↓
lucid-session-anchoring (Phase 2)
    ↓
lucid-block-manager (Phase 2)
    ↓
lucid-data-chain (Phase 2)
```

### Service Communication
- **API Gateway** → Auth Service (authentication)
- **API Gateway** → Blockchain Engine (blockchain operations)
- **Service Mesh Controller** → All services (service discovery)
- **Blockchain Engine** → MongoDB (block storage)
- **Session Anchoring** → Blockchain Engine (anchoring)
- **Block Manager** → Blockchain Engine (block validation)
- **Data Chain** → MongoDB (data storage)

## Environment Variables

### Core Configuration
```bash
# Database Configuration
MONGODB_URI=mongodb://lucid:${GENERATED_MONGODB_PASSWORD}@192.168.0.75:27017/lucid?authSource=admin&retryWrites=false
REDIS_URL=redis://:${GENERATED_REDIS_PASSWORD}@192.168.0.75:6379/0
ELASTICSEARCH_URL=http://192.168.0.75:9200

# Network Configuration
LUCID_NETWORK=lucid-pi-network
PI_HOST=192.168.0.75
PI_USER=pickme
PI_DEPLOY_DIR=/opt/lucid/production

# Service Ports
API_GATEWAY_PORT=8080
SERVICE_MESH_PORT=8081
BLOCKCHAIN_CORE_PORT=8084
SESSION_ANCHORING_PORT=8086
BLOCK_MANAGER_PORT=8088
DATA_CHAIN_PORT=8090

# Security
JWT_SECRET_KEY=${GENERATED_JWT_SECRET}
ENCRYPTION_KEY=${GENERATED_ENCRYPTION_KEY}
```

## Build Script Implementation

**File**: `scripts/core/generate-phase2-compose.sh`

```bash
#!/bin/bash
# scripts/core/generate-phase2-compose.sh
# Generate Phase 2 Docker Compose file

set -e

echo "Generating Phase 2 Docker Compose file..."

# Create configs directory if it doesn't exist
mkdir -p configs/docker

# Generate Phase 2 compose file
cat > configs/docker/docker-compose.core.yml << 'EOF'
version: '3.8'

services:
  # API Gateway Service
  lucid-api-gateway:
    image: pickme/lucid-api-gateway:latest-arm64
    container_name: lucid-api-gateway
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - API_GATEWAY_PORT=8080
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - BLOCKCHAIN_CORE_URL=http://lucid-blockchain-engine:8084
      - SESSION_API_URL=http://lucid-session-api:8087
      - NODE_MANAGEMENT_URL=http://lucid-node-management:8095
      - ADMIN_INTERFACE_URL=http://lucid-admin-interface:8083
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - RATE_LIMIT_FREE=100
      - RATE_LIMIT_PREMIUM=1000
      - RATE_LIMIT_ENTERPRISE=10000
    depends_on:
      - lucid-auth-service
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - api_gateway_logs:/app/logs

  # Service Mesh Controller
  lucid-service-mesh-controller:
    image: pickme/lucid-service-mesh-controller:latest-arm64
    container_name: lucid-service-mesh-controller
    restart: unless-stopped
    ports:
      - "8081:8081"
      - "8500:8500"
    environment:
      - SERVICE_MESH_PORT=8081
      - CONSUL_PORT=8500
      - CONSUL_DATACENTER=lucid-dc
      - CONSUL_BIND_ADDR=0.0.0.0
      - CONSUL_CLIENT_ADDR=0.0.0.0
      - CONSUL_UI_ENABLED=true
      - CONSUL_BOOTSTRAP_EXPECT=1
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8081/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - consul_data:/tmp/consul
      - service_mesh_logs:/app/logs

  # Blockchain Engine
  lucid-blockchain-engine:
    image: pickme/lucid-blockchain-engine:latest-arm64
    container_name: lucid-blockchain-engine
    restart: unless-stopped
    ports:
      - "8084:8084"
    environment:
      - BLOCKCHAIN_CORE_PORT=8084
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - BLOCK_INTERVAL=10
      - CONSENSUS_PARTICIPANTS=3
      - BLOCK_SIZE_LIMIT=1048576
      - TRANSACTION_LIMIT=1000
    depends_on:
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8084/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - blockchain_data:/app/data
      - blockchain_logs:/app/logs

  # Session Anchoring
  lucid-session-anchoring:
    image: pickme/lucid-session-anchoring:latest-arm64
    container_name: lucid-session-anchoring
    restart: unless-stopped
    ports:
      - "8086:8086"
    environment:
      - SESSION_ANCHORING_PORT=8086
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - MERKLE_TREE_DEPTH=10
      - ANCHORING_BATCH_SIZE=100
      - PROOF_GENERATION_TIMEOUT=30
    depends_on:
      - lucid-blockchain-engine
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8086/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - anchoring_data:/app/data
      - anchoring_logs:/app/logs

  # Block Manager
  lucid-block-manager:
    image: pickme/lucid-block-manager:latest-arm64
    container_name: lucid-block-manager
    restart: unless-stopped
    ports:
      - "8088:8088"
    environment:
      - BLOCK_MANAGER_PORT=8088
      - BLOCKCHAIN_ENGINE_URL=http://lucid-blockchain-engine:8084
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - MAX_BLOCKS_TO_KEEP=10000
      - BLOCK_VALIDATION_ENABLED=true
      - CHAIN_MAINTENANCE_INTERVAL=60
    depends_on:
      - lucid-blockchain-engine
      - lucid-mongodb
      - lucid-redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8088/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - block_manager_data:/app/data
      - block_manager_logs:/app/logs

  # Data Chain
  lucid-data-chain:
    image: pickme/lucid-data-chain:latest-arm64
    container_name: lucid-data-chain
    restart: unless-stopped
    ports:
      - "8090:8090"
    environment:
      - DATA_CHAIN_PORT=8090
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - ELASTICSEARCH_URL=${ELASTICSEARCH_URL}
      - INDEXING_BATCH_SIZE=1000
      - QUERY_CACHE_SIZE=10000
      - DATA_SYNC_INTERVAL=30
    depends_on:
      - lucid-mongodb
      - lucid-redis
      - lucid-elasticsearch
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8090/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - data_chain_data:/app/data
      - data_chain_logs:/app/logs

# Networks
networks:
  lucid-pi-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1

# Volumes
volumes:
  # API Gateway volumes
  api_gateway_logs:
    driver: local

  # Service Mesh volumes
  consul_data:
    driver: local
  service_mesh_logs:
    driver: local

  # Blockchain volumes
  blockchain_data:
    driver: local
  blockchain_logs:
    driver: local

  # Session Anchoring volumes
  anchoring_data:
    driver: local
  anchoring_logs:
    driver: local

  # Block Manager volumes
  block_manager_data:
    driver: local
  block_manager_logs:
    driver: local

  # Data Chain volumes
  data_chain_data:
    driver: local
  data_chain_logs:
    driver: local
EOF

echo "Phase 2 Docker Compose file generated successfully!"
echo "File: configs/docker/docker-compose.core.yml"
```

## Validation Criteria
- Docker Compose file validates successfully
- Service dependencies correctly defined
- Network configuration proper
- Volume mounts configured
- Health checks defined
- Environment variables set

## Service Ports
- **API Gateway**: 8080
- **Service Mesh Controller**: 8081 (API), 8500 (Consul)
- **Blockchain Engine**: 8084
- **Session Anchoring**: 8086
- **Block Manager**: 8088
- **Data Chain**: 8090

## Network Configuration
- **Network**: `lucid-pi-network`
- **Subnet**: 172.20.0.0/16
- **Gateway**: 172.20.0.1
- **Driver**: bridge

## Volume Configuration
- **API Gateway**: `api_gateway_logs`
- **Service Mesh**: `consul_data`, `service_mesh_logs`
- **Blockchain**: `blockchain_data`, `blockchain_logs`
- **Session Anchoring**: `anchoring_data`, `anchoring_logs`
- **Block Manager**: `block_manager_data`, `block_manager_logs`
- **Data Chain**: `data_chain_data`, `data_chain_logs`

## Troubleshooting

### Compose Validation
```bash
# Validate compose file
docker-compose -f configs/docker/docker-compose.core.yml config

# Check service dependencies
docker-compose -f configs/docker/docker-compose.core.yml config --services
```

### Service Issues
```bash
# Check service status
docker-compose -f configs/docker/docker-compose.core.yml ps

# Check service logs
docker-compose -f configs/docker/docker-compose.core.yml logs lucid-api-gateway
```

### Network Issues
```bash
# Check network configuration
docker network ls
docker network inspect lucid-pi-network
```

## Next Steps
After successful Phase 2 Docker Compose generation, proceed to Phase 2 deployment to Pi.
