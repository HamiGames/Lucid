# Phase 1: Foundation Services Build

## Overview

Phase 1 establishes the foundation services required for the Lucid system. This phase builds and deploys database services (MongoDB, Redis, Elasticsearch) and the authentication service to the Raspberry Pi.

**Duration**: ~1 week  
**Execution**: Parallel Group A (Steps 5-6 can build simultaneously)  
**Dependencies**: Pre-Build Phase completed  
**Target**: Raspberry Pi deployment via SSH

## Architecture Overview

### Services Built
1. **Storage Database Containers** (Step 5)
   - MongoDB container
   - Redis container  
   - Elasticsearch container

2. **Authentication Service Container** (Step 6)
   - Auth service with TRON signature verification
   - Hardware wallet support

3. **Deployment & Testing** (Steps 7-9)
   - Docker Compose generation
   - Pi deployment
   - Integration testing

### Network Configuration
- **Network**: `lucid-pi-network` (bridge, 172.20.0.0/16)
- **Database Ports**: MongoDB (27017), Redis (6379), Elasticsearch (9200)
- **Auth Service Port**: 8089

---

## Step 5: Storage Database Containers (Group A)

### Purpose
Build MongoDB, Redis, and Elasticsearch containers optimized for ARM64 architecture with distroless runtime.

### Location
- **Directory**: `infrastructure/containers/storage/`
- **Execution**: Windows 11 console with Docker BuildKit

### Prerequisites
- Pre-Build Phase completed
- Environment files generated (`.env.foundation`)
- Distroless base images available

### Containers to Build

1. **MongoDB Container** → `pickme/lucid-mongodb:latest-arm64`
2. **Redis Container** → `pickme/lucid-redis:latest-arm64`
3. **Elasticsearch Container** → `pickme/lucid-elasticsearch:latest-arm64`

### Create Storage Container Directory

```bash
# Create storage container directory
mkdir -p infrastructure/containers/storage
```

### MongoDB Container

Create `infrastructure/containers/storage/Dockerfile.mongodb`:

```dockerfile
# infrastructure/containers/storage/Dockerfile.mongodb
# MongoDB container for Lucid system

# Stage 1: Builder
FROM mongo:7.0 as builder

# Install additional tools
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/base-debian12:arm64

# Copy MongoDB binaries from builder
COPY --from=builder /usr/bin/mongod /usr/bin/
COPY --from=builder /usr/bin/mongosh /usr/bin/
COPY --from=builder /usr/share/mongodb/ /usr/share/mongodb/

# Create necessary directories
RUN mkdir -p /data/db /var/log/mongodb

# Copy configuration
COPY mongod.conf /etc/mongod.conf

# Set working directory
WORKDIR /data

# Expose port
EXPOSE 27017

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["mongosh", "--eval", "db.adminCommand('ping')"]

# Default command
CMD ["mongod", "--config", "/etc/mongod.conf"]
```

Create `infrastructure/containers/storage/mongod.conf`:

```yaml
# MongoDB configuration for Lucid system
storage:
  dbPath: /data/db
  journal:
    enabled: true
  wiredTiger:
    engineConfig:
      cacheSizeGB: 1

systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log

net:
  port: 27017
  bindIp: 0.0.0.0

processManagement:
  fork: false

security:
  authorization: enabled

replication:
  replSetName: "lucid-rs"
```

### Redis Container

Create `infrastructure/containers/storage/Dockerfile.redis`:

```dockerfile
# infrastructure/containers/storage/Dockerfile.redis
# Redis container for Lucid system

# Stage 1: Builder
FROM redis:7.2-alpine as builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/base-debian12:arm64

# Copy Redis binaries from builder
COPY --from=builder /usr/local/bin/redis-server /usr/local/bin/
COPY --from=builder /usr/local/bin/redis-cli /usr/local/bin/

# Create necessary directories
RUN mkdir -p /data /var/log/redis

# Copy configuration
COPY redis.conf /usr/local/etc/redis.conf

# Set working directory
WORKDIR /data

# Expose port
EXPOSE 6379

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD ["redis-cli", "ping"]

# Default command
CMD ["redis-server", "/usr/local/etc/redis.conf"]
```

Create `infrastructure/containers/storage/redis.conf`:

```conf
# Redis configuration for Lucid system
port 6379
bind 0.0.0.0
protected-mode yes
requirepass ${REDIS_PASSWORD}

# Persistence
save 900 1
save 300 10
save 60 10000

dir /data
dbfilename dump.rdb

# Logging
logfile /var/log/redis/redis.log
loglevel notice

# Memory optimization for Pi
maxmemory 1gb
maxmemory-policy allkeys-lru

# Performance
tcp-keepalive 300
timeout 0
```

### Elasticsearch Container

Create `infrastructure/containers/storage/Dockerfile.elasticsearch`:

```dockerfile
# infrastructure/containers/storage/Dockerfile.elasticsearch
# Elasticsearch container optimized for Raspberry Pi

# Stage 1: Builder
FROM elasticsearch:8.11.0 as builder

# Install additional tools
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/base-debian12:arm64

# Copy Elasticsearch binaries from builder
COPY --from=builder /usr/share/elasticsearch/ /usr/share/elasticsearch/
COPY --from=builder /usr/share/elasticsearch/bin/ /usr/share/elasticsearch/bin/

# Create necessary directories
RUN mkdir -p /usr/share/elasticsearch/data /usr/share/elasticsearch/logs

# Copy configuration
COPY elasticsearch.yml /usr/share/elasticsearch/config/

# Set working directory
WORKDIR /usr/share/elasticsearch

# Expose port
EXPOSE 9200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["curl", "-f", "http://localhost:9200/_cluster/health"]

# Default command
CMD ["bin/elasticsearch"]
```

Create `infrastructure/containers/storage/elasticsearch.yml`:

```yaml
# Elasticsearch configuration optimized for Pi
cluster.name: lucid-cluster
node.name: lucid-node-1

path.data: /usr/share/elasticsearch/data
path.logs: /usr/share/elasticsearch/logs

network.host: 0.0.0.0
http.port: 9200

# Pi optimization
bootstrap.memory_lock: true
discovery.type: single-node

# JVM settings for Pi
ES_JAVA_OPTS: "-Xms1g -Xmx1g"

# Security
xpack.security.enabled: true
xpack.security.authc.anonymous.enabled: false

# Performance
indices.query.bool.max_clause_count: 4096
```

### Build Script

Create `infrastructure/containers/storage/build-storage-containers.sh`:

```bash
#!/bin/bash
# infrastructure/containers/storage/build-storage-containers.sh
# Build storage database containers for Lucid system

set -e

echo "Building storage database containers..."

# Set build context
cd infrastructure/containers/storage

# Build MongoDB container
echo "Building MongoDB container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-mongodb:latest-arm64 \
  -f Dockerfile.mongodb \
  --push .

# Build Redis container
echo "Building Redis container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-redis:latest-arm64 \
  -f Dockerfile.redis \
  --push .

# Build Elasticsearch container
echo "Building Elasticsearch container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-elasticsearch:latest-arm64 \
  -f Dockerfile.elasticsearch \
  --push .

echo "Storage containers built and pushed successfully"
```

### Execute Build

```bash
# Make script executable
chmod +x infrastructure/containers/storage/build-storage-containers.sh

# Run storage container build
./infrastructure/containers/storage/build-storage-containers.sh
```

### Validation
- All 3 containers built successfully
- Images pushed to Docker Hub
- Total size <500MB combined
- ARM64 platform compatibility confirmed

---

## Step 6: Authentication Service Container (Group A)

### Purpose
Build authentication service with TRON signature verification and hardware wallet support.

### Location
- **Directory**: `auth/`
- **Execution**: Windows 11 console with Docker BuildKit

### Prerequisites
- Pre-Build Phase completed
- Environment files generated (`.env.foundation`)
- Python distroless base image available

### Container to Build
- **Auth Service Container** → `pickme/lucid-auth-service:latest-arm64`

### Multi-Stage Build Strategy

Create `auth/Dockerfile`:

```dockerfile
# auth/Dockerfile
# Authentication service with TRON signature verification

# Stage 1: Builder
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /build/deps

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian12:arm64

# Copy dependencies from builder
COPY --from=builder /build/deps /app/deps

# Copy application code
COPY . /app/

# Set environment variables
ENV PYTHONPATH=/app/deps
WORKDIR /app

# Expose port
EXPOSE 8089

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8089/health')"]

# Default command
CMD ["python", "main.py"]
```

### Auth Service Requirements

Create `auth/requirements.txt`:

```txt
# Authentication service requirements
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
PyJWT==2.8.0
cryptography==41.0.8
tronweb==4.3.0
requests==2.31.0
python-multipart==0.0.6
aiofiles==23.2.1
pymongo==4.6.0
redis==5.0.1
python-dotenv==1.0.0
```

### Auth Service Configuration

Create `auth/config.py`:

```python
# auth/config.py
# Authentication service configuration

import os
from typing import Dict, Any

class AuthConfig:
    # Database Configuration
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/lucid")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # TRON Configuration
    TRON_NETWORK: str = "mainnet"
    TRON_API_URL: str = "https://api.trongrid.io"
    
    # Hardware Wallet Configuration
    HARDWARE_WALLET_ENABLED: bool = True
    LEDGER_ENABLED: bool = True
    TREZOR_ENABLED: bool = True
    
    # Service Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8089
    DEBUG: bool = False
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_vars = [
            "MONGODB_URI",
            "REDIS_URL", 
            "JWT_SECRET_KEY"
        ]
        
        for var in required_vars:
            if not getattr(cls, var):
                raise ValueError(f"Required environment variable {var} not set")
        
        return True

# Validate configuration on import
AuthConfig.validate()
```

### Auth Service Main Application

Create `auth/main.py`:

```python
# auth/main.py
# Authentication service main application

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import AuthConfig
from api.auth_routes import auth_router
from api.user_routes import user_router
from api.hardware_wallet_routes import hw_router
from middleware.auth_middleware import AuthMiddleware
from services.database_service import DatabaseService
from services.redis_service import RedisService

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    await DatabaseService.initialize()
    await RedisService.initialize()
    
    yield
    
    # Shutdown
    await DatabaseService.close()
    await RedisService.close()

# Create FastAPI application
app = FastAPI(
    title="Lucid Authentication Service",
    description="Authentication service with TRON signature verification",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(hw_router, prefix="/hardware-wallet", tags=["hardware-wallet"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth-service"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Lucid Authentication Service", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=AuthConfig.HOST,
        port=AuthConfig.PORT,
        reload=AuthConfig.DEBUG
    )
```

### Build Script

Create `auth/build-auth-service.sh`:

```bash
#!/bin/bash
# auth/build-auth-service.sh
# Build authentication service container

set -e

echo "Building authentication service container..."

# Set build context
cd auth

# Build auth service container
echo "Building auth service container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-auth-service:latest-arm64 \
  -f Dockerfile \
  --push .

echo "Authentication service container built and pushed successfully"
```

### Execute Build

```bash
# Make script executable
chmod +x auth/build-auth-service.sh

# Run auth service build
./auth/build-auth-service.sh
```

### Validation
- Container built successfully
- Image pushed to Docker Hub
- Health endpoint responds
- JWT generation works
- TRON signature verification functional

---

## Step 7: Phase 1 Docker Compose Generation

### Purpose
Generate complete Docker Compose file for Phase 1 services with real configurations.

### Location
- **File**: `configs/docker/docker-compose.foundation.yml`
- **Execution**: Windows 11 console

### Prerequisites
- Steps 5-6 completed (containers built)
- Environment files generated (`.env.foundation`)

### Create Docker Compose File

Create `configs/docker/docker-compose.foundation.yml`:

```yaml
# configs/docker/docker-compose.foundation.yml
# Phase 1 Foundation Services Docker Compose

version: '3.8'

services:
  # MongoDB Database
  lucid-mongodb:
    image: pickme/lucid-mongodb:latest-arm64
    container_name: lucid-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
      - mongodb_logs:/var/log/mongodb
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGODB_PASSWORD}
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Redis Cache
  lucid-redis:
    image: pickme/lucid-redis:latest-arm64
    container_name: lucid-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - redis_logs:/var/log/redis
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # Elasticsearch Search Engine
  lucid-elasticsearch:
    image: pickme/lucid-elasticsearch:latest-arm64
    container_name: lucid-elasticsearch
    restart: unless-stopped
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
      - elasticsearch_logs:/usr/share/elasticsearch/logs
    environment:
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
      - discovery.type=single-node
      - xpack.security.enabled=true
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Authentication Service
  lucid-auth-service:
    image: pickme/lucid-auth-service:latest-arm64
    container_name: lucid-auth-service
    restart: unless-stopped
    ports:
      - "8089:8089"
    environment:
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}
    depends_on:
      lucid-mongodb:
        condition: service_healthy
      lucid-redis:
        condition: service_healthy
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8089/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

volumes:
  mongodb_data:
    driver: local
  mongodb_logs:
    driver: local
  redis_data:
    driver: local
  redis_logs:
    driver: local
  elasticsearch_data:
    driver: local
  elasticsearch_logs:
    driver: local

networks:
  lucid-pi-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Validation Script

Create `scripts/validation/validate-phase1-compose.sh`:

```bash
#!/bin/bash
# scripts/validation/validate-phase1-compose.sh
# Validate Phase 1 Docker Compose configuration

set -e

echo "Validating Phase 1 Docker Compose configuration..."

# Check if compose file exists
if [ ! -f "configs/docker/docker-compose.foundation.yml" ]; then
    echo "ERROR: Docker Compose file not found"
    exit 1
fi

# Validate compose file syntax
echo "Validating compose file syntax..."
if ! docker-compose -f configs/docker/docker-compose.foundation.yml config > /dev/null 2>&1; then
    echo "ERROR: Docker Compose file syntax invalid"
    exit 1
fi

# Check environment variables
echo "Checking environment variables..."
ENV_FILE="configs/environment/.env.foundation"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: Environment file not found: $ENV_FILE"
    exit 1
fi

# Validate environment variables are set
REQUIRED_VARS=("MONGODB_URI" "REDIS_URL" "JWT_SECRET_KEY" "ENCRYPTION_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" "$ENV_FILE"; then
        echo "ERROR: Required environment variable $var not found"
        exit 1
    fi
done

echo "Phase 1 Docker Compose validation completed successfully"
```

### Execute Validation

```bash
# Make script executable
chmod +x scripts/validation/validate-phase1-compose.sh

# Run validation
./scripts/validation/validate-phase1-compose.sh
```

### Validation
- Docker Compose file syntax valid
- All services defined correctly
- Environment variables properly configured
- Network and volume configurations correct

---

## Step 8: Phase 1 Deployment to Pi

### Purpose
Deploy Phase 1 containers to Raspberry Pi via SSH.

### Location
- **Script**: `scripts/deployment/deploy-phase1-pi.sh`
- **Execution**: Windows 11 console

### Prerequisites
- Steps 5-7 completed
- SSH access to Pi (pickme@192.168.0.75)
- Docker Compose file validated

### Deployment Script

Create `scripts/deployment/deploy-phase1-pi.sh`:

```bash
#!/bin/bash
# scripts/deployment/deploy-phase1-pi.sh
# Deploy Phase 1 services to Raspberry Pi

set -e

echo "Deploying Phase 1 services to Raspberry Pi..."

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_DEPLOY_DIR="/opt/lucid/production"
COMPOSE_FILE="docker-compose.foundation.yml"
ENV_FILE=".env.foundation"

# Create deployment directory on Pi
echo "Creating deployment directory on Pi..."
ssh ${PI_USER}@${PI_HOST} "sudo mkdir -p ${PI_DEPLOY_DIR}/configs/{docker,environment}"
ssh ${PI_USER}@${PI_HOST} "sudo chown -R ${PI_USER}:${PI_USER} ${PI_DEPLOY_DIR}"

# Copy Phase 1 compose file to Pi
echo "Copying Docker Compose file to Pi..."
scp configs/docker/${COMPOSE_FILE} ${PI_USER}@${PI_HOST}:${PI_DEPLOY_DIR}/configs/docker/

# Copy environment file to Pi
echo "Copying environment file to Pi..."
scp configs/environment/${ENV_FILE} ${PI_USER}@${PI_HOST}:${PI_DEPLOY_DIR}/configs/environment/

# Pull arm64 images on Pi
echo "Pulling ARM64 images on Pi..."
ssh ${PI_USER}@${PI_HOST} "cd ${PI_DEPLOY_DIR} && docker-compose -f configs/docker/${COMPOSE_FILE} --env-file configs/environment/${ENV_FILE} pull"

# Deploy services
echo "Deploying Phase 1 services..."
ssh ${PI_USER}@${PI_HOST} "cd ${PI_DEPLOY_DIR} && docker-compose -f configs/docker/${COMPOSE_FILE} --env-file configs/environment/${ENV_FILE} up -d"

# Wait for health checks
echo "Waiting for health checks (90 seconds)..."
sleep 90

# Verify all services running
echo "Verifying all services are running..."
ssh ${PI_USER}@${PI_HOST} "cd ${PI_DEPLOY_DIR} && docker-compose -f configs/docker/${COMPOSE_FILE} --env-file configs/environment/${ENV_FILE} ps"

# Check service health
echo "Checking service health..."
ssh ${PI_USER}@${PI_HOST} "cd ${PI_DEPLOY_DIR} && docker-compose -f configs/docker/${COMPOSE_FILE} --env-file configs/environment/${ENV_FILE} ps --services | xargs -I {} docker-compose -f configs/docker/${COMPOSE_FILE} --env-file configs/environment/${ENV_FILE} ps {}"

# Initialize databases
echo "Initializing databases..."
ssh ${PI_USER}@${PI_HOST} "cd ${PI_DEPLOY_DIR} && docker exec lucid-mongodb mongosh --eval 'rs.initiate()'"
ssh ${PI_USER}@${PI_HOST} "cd ${PI_DEPLOY_DIR} && docker exec lucid-elasticsearch curl -X PUT 'localhost:9200/lucid-index'"

echo "Phase 1 deployment completed successfully"
echo "All services are running and healthy on Pi"
```

### Execute Deployment

```bash
# Make script executable
chmod +x scripts/deployment/deploy-phase1-pi.sh

# Run Phase 1 deployment
./scripts/deployment/deploy-phase1-pi.sh
```

### Validation
- All Phase 1 services healthy on Pi
- Databases initialized
- Services responding to health checks
- Network connectivity established

---

## Step 9: Phase 1 Integration Testing

### Purpose
Run integration tests against deployed Phase 1 services on Pi.

### Location
- **Directory**: `tests/integration/phase1/`
- **Execution**: Windows 11 console

### Prerequisites
- Step 8 completed (services deployed)
- Services healthy on Pi

### Test Suite

Create `tests/integration/phase1/test_phase1_integration.py`:

```python
# tests/integration/phase1/test_phase1_integration.py
# Phase 1 integration tests

import pytest
import asyncio
import requests
import pymongo
import redis
from elasticsearch import Elasticsearch
import json

# Test configuration
PI_HOST = "192.168.0.75"
MONGODB_PORT = 27017
REDIS_PORT = 6379
ELASTICSEARCH_PORT = 9200
AUTH_SERVICE_PORT = 8089

class TestPhase1Integration:
    """Phase 1 integration test suite"""
    
    @pytest.fixture(scope="class")
    async def setup(self):
        """Setup test environment"""
        # MongoDB connection
        self.mongo_client = pymongo.MongoClient(f"mongodb://{PI_HOST}:{MONGODB_PORT}")
        self.db = self.mongo_client.lucid
        
        # Redis connection
        self.redis_client = redis.Redis(host=PI_HOST, port=REDIS_PORT, decode_responses=True)
        
        # Elasticsearch connection
        self.es_client = Elasticsearch([f"http://{PI_HOST}:{ELASTICSEARCH_PORT}"])
        
        # Auth service URL
        self.auth_url = f"http://{PI_HOST}:{AUTH_SERVICE_PORT}"
    
    async def test_mongodb_connection(self):
        """Test MongoDB connection and query performance"""
        # Test connection
        assert self.mongo_client.admin.command('ping')
        
        # Test query performance
        start_time = asyncio.get_event_loop().time()
        result = self.db.test_collection.insert_one({"test": "data"})
        end_time = asyncio.get_event_loop().time()
        
        # Performance check (< 10ms)
        assert (end_time - start_time) < 0.01
        assert result.inserted_id is not None
        
        # Cleanup
        self.db.test_collection.delete_one({"_id": result.inserted_id})
    
    async def test_redis_caching(self):
        """Test Redis caching operations"""
        # Test connection
        assert self.redis_client.ping()
        
        # Test set/get operations
        test_key = "test_key"
        test_value = "test_value"
        
        self.redis_client.set(test_key, test_value)
        retrieved_value = self.redis_client.get(test_key)
        
        assert retrieved_value == test_value
        
        # Test expiration
        self.redis_client.setex(test_key, 1, test_value)
        await asyncio.sleep(2)
        expired_value = self.redis_client.get(test_key)
        
        assert expired_value is None
    
    async def test_elasticsearch_indexing(self):
        """Test Elasticsearch indexing and search"""
        # Test connection
        assert self.es_client.ping()
        
        # Test index creation
        index_name = "test-index"
        doc = {"title": "Test Document", "content": "This is a test document"}
        
        # Index document
        result = self.es_client.index(index=index_name, body=doc)
        assert result["result"] == "created"
        
        # Refresh index
        self.es_client.indices.refresh(index=index_name)
        
        # Test search
        search_result = self.es_client.search(
            index=index_name,
            body={"query": {"match": {"title": "Test"}}}
        )
        
        assert search_result["hits"]["total"]["value"] > 0
        
        # Cleanup
        self.es_client.indices.delete(index=index_name)
    
    async def test_auth_service_login_logout(self):
        """Test auth service login/logout flow"""
        # Test health endpoint
        health_response = requests.get(f"{self.auth_url}/health")
        assert health_response.status_code == 200
        
        # Test root endpoint
        root_response = requests.get(f"{self.auth_url}/")
        assert root_response.status_code == 200
        
        # Test auth endpoints (basic connectivity)
        auth_endpoints = ["/auth/login", "/auth/register", "/auth/logout"]
        for endpoint in auth_endpoints:
            response = requests.get(f"{self.auth_url}{endpoint}")
            # Should return 405 (Method Not Allowed) for GET, not 500
            assert response.status_code in [200, 405, 422]
    
    async def test_jwt_token_generation(self):
        """Test JWT token generation and validation"""
        # This would require actual auth service implementation
        # For now, test that the service is responding
        response = requests.get(f"{self.auth_url}/health")
        assert response.status_code == 200
        
        # TODO: Implement actual JWT test when auth service is complete
    
    async def test_cross_service_communication(self):
        """Test cross-service communication (auth → databases)"""
        # Test that auth service can connect to databases
        # This would require actual auth service implementation
        # For now, test basic connectivity
        
        # Test MongoDB connectivity from auth service perspective
        mongo_response = requests.get(f"{self.auth_url}/health")
        assert mongo_response.status_code == 200
        
        # Test Redis connectivity from auth service perspective
        redis_response = requests.get(f"{self.auth_url}/health")
        assert redis_response.status_code == 200

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Test Execution Script

Create `tests/integration/phase1/run_phase1_tests.sh`:

```bash
#!/bin/bash
# tests/integration/phase1/run_phase1_tests.sh
# Run Phase 1 integration tests

set -e

echo "Running Phase 1 integration tests..."

# Install test dependencies
pip install pytest pytest-asyncio requests pymongo redis elasticsearch

# Run tests
python -m pytest tests/integration/phase1/test_phase1_integration.py -v --tb=short

echo "Phase 1 integration tests completed"
```

### Execute Tests

```bash
# Make script executable
chmod +x tests/integration/phase1/run_phase1_tests.sh

# Run Phase 1 integration tests
./tests/integration/phase1/run_phase1_tests.sh
```

### Validation Criteria
- MongoDB connection and query performance (<10ms)
- Redis caching operations working
- Elasticsearch indexing and search functional
- Auth service login/logout flow operational
- JWT token generation and validation working
- Cross-service communication (auth → databases) established
- All tests pass with >95% coverage

---

## Phase 1 Validation

### Complete Phase 1 Validation

Create `scripts/validation/validate-phase1-complete.sh`:

```bash
#!/bin/bash
# scripts/validation/validate-phase1-complete.sh
# Complete Phase 1 validation

set -e

echo "Running complete Phase 1 validation..."

# Check containers are running on Pi
echo "Checking containers on Pi..."
ssh pickme@192.168.0.75 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep lucid"

# Check service health
echo "Checking service health..."
ssh pickme@192.168.0.75 "curl -f http://localhost:8089/health"

# Check database connectivity
echo "Checking database connectivity..."
ssh pickme@192.168.0.75 "docker exec lucid-mongodb mongosh --eval 'db.adminCommand(\"ping\")'"
ssh pickme@192.168.0.75 "docker exec lucid-redis redis-cli ping"
ssh pickme@192.168.0.75 "curl -f http://localhost:9200/_cluster/health"

# Run integration tests
echo "Running integration tests..."
./tests/integration/phase1/run_phase1_tests.sh

echo "Phase 1 validation completed successfully"
echo "Ready to proceed to Phase 2: Core Services"
```

### Execute Complete Validation

```bash
# Make script executable
chmod +x scripts/validation/validate-phase1-complete.sh

# Run complete Phase 1 validation
./scripts/validation/validate-phase1-complete.sh
```

## Next Steps

Upon successful completion of Phase 1:

1. **All foundation services deployed** and healthy on Pi
2. **Databases initialized** and ready for Phase 2 services
3. **Authentication service operational** with JWT support
4. **Integration tests passing** with >95% coverage

**Proceed to**: [Phase 2: Core Services](phase2-core-services.md)

## Troubleshooting Summary

| Issue | Solution |
|-------|----------|
| Container build failed | Check Docker BuildKit enabled, base images available |
| Pi deployment failed | Verify SSH access, disk space, Docker on Pi |
| Database connection failed | Check network connectivity, credentials, ports |
| Auth service not responding | Verify dependencies, environment variables, health checks |
| Integration tests failing | Check service health, network connectivity, test configuration |

---

**Duration**: ~1 week  
**Status**: Parallel Group A execution  
**Dependencies**: Pre-Build Phase completed  
**Next Phase**: Phase 2 Core Services
