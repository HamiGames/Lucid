# Lucid System Scaling Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-SCALE-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-01-14 |
| Based On | Master Build Plan v1.0.0 |

---

## Overview

This comprehensive scaling guide covers horizontal and vertical scaling strategies for the Lucid blockchain system across all 10 service clusters. The guide provides detailed procedures for scaling individual services and the entire system to handle increased load and user demand.

### Scaling Strategy Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer Layer                      │
│  Traefik/Nginx with SSL termination and routing            │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                    API Gateway Cluster                     │
│  Horizontal scaling: 3-5 replicas                         │
│  Vertical scaling: 2-4 CPU cores, 4-8GB RAM              │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Service Clusters (Auto-scaling)             │
│  Session Management: 2-10 replicas                        │
│  RDP Services: 1-5 replicas                               │
│  Node Management: 1-3 replicas                            │
│  Admin Interface: 1-2 replicas                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Database Layer (Clustered)                 │
│  MongoDB: 3-node replica set                             │
│  Redis: 3-node cluster                                   │
│  Elasticsearch: 3-node cluster                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Horizontal Scaling

### API Gateway Scaling

#### Load Balancer Configuration

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  traefik:
    image: traefik:v3.0
    container_name: lucid-traefik
    hostname: traefik
    restart: unless-stopped
    
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@lucid.onion"
      - "--certificatesresolvers.letsencrypt.acme.storage=/acme.json"
    
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Traefik dashboard
    
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./acme.json:/acme.json
      - ./configs/traefik:/etc/traefik:ro
    
    networks:
      - lucid-network
    
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik.rule=Host(`traefik.lucid.onion`)"
      - "traefik.http.routers.traefik.service=api@internal"

  lucid-api-gateway-1:
    image: ghcr.io/hamigames/lucid/api-gateway:latest
    container_name: lucid-api-gateway-1
    hostname: api-gateway-1
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-api-gateway-1
      - PORT=8080
      - INSTANCE_ID=1
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URI=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network
    
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api-gateway.rule=Host(`api.lucid.onion`)"
      - "traefik.http.services.api-gateway.loadbalancer.server.port=8080"
      - "traefik.http.services.api-gateway.loadbalancer.server.weight=1"
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-api-gateway-2:
    image: ghcr.io/hamigames/lucid/api-gateway:latest
    container_name: lucid-api-gateway-2
    hostname: api-gateway-2
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-api-gateway-2
      - PORT=8080
      - INSTANCE_ID=2
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URI=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network
    
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api-gateway.rule=Host(`api.lucid.onion`)"
      - "traefik.http.services.api-gateway.loadbalancer.server.port=8080"
      - "traefik.http.services.api-gateway.loadbalancer.server.weight=1"
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-api-gateway-3:
    image: ghcr.io/hamigames/lucid/api-gateway:latest
    container_name: lucid-api-gateway-3
    hostname: api-gateway-3
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-api-gateway-3
      - PORT=8080
      - INSTANCE_ID=3
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URI=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network
    
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api-gateway.rule=Host(`api.lucid.onion`)"
      - "traefik.http.services.api-gateway.loadbalancer.server.port=8080"
      - "traefik.http.services.api-gateway.loadbalancer.server.weight=1"
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### Auto-scaling Configuration

```yaml
# docker-compose.autoscale.yml
version: '3.8'

services:
  lucid-api-gateway:
    image: ghcr.io/hamigames/lucid/api-gateway:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.api-gateway.rule=Host(`api.lucid.onion`)"
        - "traefik.http.services.api-gateway.loadbalancer.server.port=8080"
    
    environment:
      - SERVICE_NAME=lucid-api-gateway
      - PORT=8080
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URI=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network
```

### Session Management Scaling

#### Session Pipeline Scaling

```yaml
# docker-compose.session-scale.yml
version: '3.8'

services:
  lucid-session-pipeline:
    image: ghcr.io/hamigames/lucid/session-pipeline:latest
    deploy:
      replicas: 5
      update_config:
        parallelism: 2
        delay: 15s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    
    environment:
      - SERVICE_NAME=lucid-session-pipeline
      - PORT=8083
      - API_GATEWAY_URL=http://lucid-api-gateway:8080
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network

  lucid-session-recorder:
    image: ghcr.io/hamigames/lucid/session-recorder:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 20s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
    environment:
      - SERVICE_NAME=lucid-session-recorder
      - PORT=8084
      - SESSION_PIPELINE_URL=http://lucid-session-pipeline:8083
      - LOG_LEVEL=INFO
    
    volumes:
      - lucid-session-data:/data/sessions
    
    networks:
      - lucid-network

  lucid-chunk-processor:
    image: ghcr.io/hamigames/lucid/chunk-processor:latest
    deploy:
      replicas: 10
      update_config:
        parallelism: 3
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    
    environment:
      - SERVICE_NAME=lucid-chunk-processor
      - PORT=8085
      - SESSION_RECORDER_URL=http://lucid-session-recorder:8084
      - LOG_LEVEL=INFO
    
    volumes:
      - lucid-chunk-data:/data/chunks
    
    networks:
      - lucid-network
```

### RDP Services Scaling

#### RDP Manager Scaling

```yaml
# docker-compose.rdp-scale.yml
version: '3.8'

services:
  lucid-rdp-manager:
    image: ghcr.io/hamigames/lucid/rdp-manager:latest
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 30s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 15s
        max_attempts: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    
    environment:
      - SERVICE_NAME=lucid-rdp-manager
      - PORT=8090
      - API_GATEWAY_URL=http://lucid-api-gateway:8080
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network

  lucid-xrdp:
    image: ghcr.io/hamigames/lucid/xrdp:latest
    deploy:
      replicas: 5
      update_config:
        parallelism: 2
        delay: 20s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
    environment:
      - SERVICE_NAME=lucid-xrdp
      - PORT=8091
      - RDP_MANAGER_URL=http://lucid-rdp-manager:8090
      - LOG_LEVEL=INFO
    
    ports:
      - "13389-14389:13389-14389"  # RDP port range
    
    networks:
      - lucid-network
```

---

## Vertical Scaling

### Resource Optimization

#### CPU Scaling

```yaml
# docker-compose.vertical-scale.yml
version: '3.8'

services:
  lucid-api-gateway:
    image: ghcr.io/hamigames/lucid/api-gateway:latest
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
    
    environment:
      - SERVICE_NAME=lucid-api-gateway
      - PORT=8080
      - WORKER_PROCESSES=4
      - WORKER_CONNECTIONS=1024
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network

  lucid-blockchain-engine:
    image: ghcr.io/hamigames/lucid/blockchain-engine:latest
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
        reservations:
          memory: 2G
          cpus: '2.0'
    
    environment:
      - SERVICE_NAME=lucid-blocks
      - PORT=8084
      - CONSENSUS_WORKERS=4
      - BLOCK_PROCESSING_THREADS=8
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network

  lucid-session-recorder:
    image: ghcr.io/hamigames/lucid/session-recorder:latest
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
    
    environment:
      - SERVICE_NAME=lucid-session-recorder
      - PORT=8084
      - RECORDING_THREADS=8
      - CHUNK_SIZE_MB=10
      - LOG_LEVEL=INFO
    
    volumes:
      - lucid-session-data:/data/sessions
    
    networks:
      - lucid-network
```

#### Memory Scaling

```yaml
# docker-compose.memory-scale.yml
version: '3.8'

services:
  lucid-mongodb:
    image: mongo:7.0
    deploy:
      resources:
        limits:
          memory: 16G
          cpus: '4.0'
        reservations:
          memory: 4G
          cpus: '2.0'
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    
    command: ["mongod", "--wiredTigerCacheSizeGB", "8", "--maxConns", "1000"]
    
    volumes:
      - lucid-mongo-data:/data/db
    
    networks:
      - lucid-network

  lucid-redis:
    image: redis:7.2-alpine
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
    
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    
    command: ["redis-server", "--maxmemory", "3gb", "--maxmemory-policy", "allkeys-lru"]
    
    volumes:
      - lucid-redis-data:/data
    
    networks:
      - lucid-network

  lucid-elasticsearch:
    image: elasticsearch:8.11.0
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
    
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms4g -Xmx4g"
    
    volumes:
      - lucid-elasticsearch-data:/usr/share/elasticsearch/data
    
    networks:
      - lucid-network
```

---

## Database Scaling

### MongoDB Replica Set

#### Primary-Secondary Configuration

```yaml
# docker-compose.mongodb-cluster.yml
version: '3.8'

services:
  lucid-mongodb-primary:
    image: mongo:7.0
    container_name: lucid-mongodb-primary
    hostname: mongodb-primary
    restart: unless-stopped
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    
    ports:
      - "27017:27017"
    
    volumes:
      - lucid-mongo-primary-data:/data/db
      - ./configs/mongodb/mongod-primary.conf:/etc/mongod.conf:ro
    
    networks:
      - lucid-network
    
    command: ["mongod", "--config", "/etc/mongod.conf", "--replSet", "rs0"]
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand({ping: 1})", "--quiet"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-mongodb-secondary-1:
    image: mongo:7.0
    container_name: lucid-mongodb-secondary-1
    hostname: mongodb-secondary-1
    restart: unless-stopped
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    
    ports:
      - "27018:27017"
    
    volumes:
      - lucid-mongo-secondary-1-data:/data/db
      - ./configs/mongodb/mongod-secondary.conf:/etc/mongod.conf:ro
    
    networks:
      - lucid-network
    
    command: ["mongod", "--config", "/etc/mongod.conf", "--replSet", "rs0"]
    
    depends_on:
      - lucid-mongodb-primary
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand({ping: 1})", "--quiet"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  lucid-mongodb-secondary-2:
    image: mongo:7.0
    container_name: lucid-mongodb-secondary-2
    hostname: mongodb-secondary-2
    restart: unless-stopped
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    
    ports:
      - "27019:27017"
    
    volumes:
      - lucid-mongo-secondary-2-data:/data/db
      - ./configs/mongodb/mongod-secondary.conf:/etc/mongod.conf:ro
    
    networks:
      - lucid-network
    
    command: ["mongod", "--config", "/etc/mongod.conf", "--replSet", "rs0"]
    
    depends_on:
      - lucid-mongodb-primary
    
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand({ping: 1})", "--quiet"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  lucid-mongo-primary-data:
    name: lucid-mongo-primary-data
  lucid-mongo-secondary-1-data:
    name: lucid-mongo-secondary-1-data
  lucid-mongo-secondary-2-data:
    name: lucid-mongo-secondary-2-data
```

#### Replica Set Initialization

```bash
#!/bin/bash
# scripts/database/init-mongodb-replica-set.sh

set -e

echo "Initializing MongoDB replica set..."

# Wait for all MongoDB instances to be ready
echo "Waiting for MongoDB instances to be ready..."
sleep 30

# Initialize replica set
echo "Initializing replica set..."
docker exec lucid-mongodb-primary mongosh --eval "
rs.initiate({
  _id: 'rs0',
  members: [
    { _id: 0, host: 'mongodb-primary:27017', priority: 2 },
    { _id: 1, host: 'mongodb-secondary-1:27017', priority: 1 },
    { _id: 2, host: 'mongodb-secondary-2:27017', priority: 1 }
  ]
})
"

# Wait for replica set to be ready
echo "Waiting for replica set to be ready..."
sleep 30

# Check replica set status
echo "Checking replica set status..."
docker exec lucid-mongodb-primary mongosh --eval "rs.status()"

echo "MongoDB replica set initialized successfully!"
```

### Redis Cluster

#### Redis Cluster Configuration

```yaml
# docker-compose.redis-cluster.yml
version: '3.8'

services:
  lucid-redis-node-1:
    image: redis:7.2-alpine
    container_name: lucid-redis-node-1
    hostname: redis-node-1
    restart: unless-stopped
    
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    
    ports:
      - "7001:6379"
    
    volumes:
      - lucid-redis-node-1-data:/data
      - ./configs/redis/redis-cluster-node-1.conf:/usr/local/etc/redis/redis.conf:ro
    
    networks:
      - lucid-network
    
    command: ["redis-server", "/usr/local/etc/redis/redis.conf"]
    
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  lucid-redis-node-2:
    image: redis:7.2-alpine
    container_name: lucid-redis-node-2
    hostname: redis-node-2
    restart: unless-stopped
    
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    
    ports:
      - "7002:6379"
    
    volumes:
      - lucid-redis-node-2-data:/data
      - ./configs/redis/redis-cluster-node-2.conf:/usr/local/etc/redis/redis.conf:ro
    
    networks:
      - lucid-network
    
    command: ["redis-server", "/usr/local/etc/redis/redis.conf"]
    
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  lucid-redis-node-3:
    image: redis:7.2-alpine
    container_name: lucid-redis-node-3
    hostname: redis-node-3
    restart: unless-stopped
    
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    
    ports:
      - "7003:6379"
    
    volumes:
      - lucid-redis-node-3-data:/data
      - ./configs/redis/redis-cluster-node-3.conf:/usr/local/etc/redis/redis.conf:ro
    
    networks:
      - lucid-network
    
    command: ["redis-server", "/usr/local/etc/redis/redis.conf"]
    
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

volumes:
  lucid-redis-node-1-data:
    name: lucid-redis-node-1-data
  lucid-redis-node-2-data:
    name: lucid-redis-node-2-data
  lucid-redis-node-3-data:
    name: lucid-redis-node-3-data
```

#### Redis Cluster Initialization

```bash
#!/bin/bash
# scripts/database/init-redis-cluster.sh

set -e

echo "Initializing Redis cluster..."

# Wait for all Redis instances to be ready
echo "Waiting for Redis instances to be ready..."
sleep 30

# Create Redis cluster
echo "Creating Redis cluster..."
docker exec lucid-redis-node-1 redis-cli --cluster create \
  redis-node-1:6379 \
  redis-node-2:6379 \
  redis-node-3:6379 \
  --cluster-replicas 0 \
  --cluster-yes

# Check cluster status
echo "Checking cluster status..."
docker exec lucid-redis-node-1 redis-cli --cluster nodes

echo "Redis cluster initialized successfully!"
```

### Elasticsearch Cluster

#### Elasticsearch Cluster Configuration

```yaml
# docker-compose.elasticsearch-cluster.yml
version: '3.8'

services:
  lucid-elasticsearch-node-1:
    image: elasticsearch:8.11.0
    container_name: lucid-elasticsearch-node-1
    hostname: elasticsearch-node-1
    restart: unless-stopped
    
    environment:
      - node.name=elasticsearch-node-1
      - cluster.name=lucid-cluster
      - discovery.seed_hosts=elasticsearch-node-2,elasticsearch-node-3
      - cluster.initial_master_nodes=elasticsearch-node-1,elasticsearch-node-2,elasticsearch-node-3
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    
    ports:
      - "9201:9200"
    
    volumes:
      - lucid-elasticsearch-node-1-data:/usr/share/elasticsearch/data
    
    networks:
      - lucid-network
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  lucid-elasticsearch-node-2:
    image: elasticsearch:8.11.0
    container_name: lucid-elasticsearch-node-2
    hostname: elasticsearch-node-2
    restart: unless-stopped
    
    environment:
      - node.name=elasticsearch-node-2
      - cluster.name=lucid-cluster
      - discovery.seed_hosts=elasticsearch-node-1,elasticsearch-node-3
      - cluster.initial_master_nodes=elasticsearch-node-1,elasticsearch-node-2,elasticsearch-node-3
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    
    ports:
      - "9202:9200"
    
    volumes:
      - lucid-elasticsearch-node-2-data:/usr/share/elasticsearch/data
    
    networks:
      - lucid-network
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  lucid-elasticsearch-node-3:
    image: elasticsearch:8.11.0
    container_name: lucid-elasticsearch-node-3
    hostname: elasticsearch-node-3
    restart: unless-stopped
    
    environment:
      - node.name=elasticsearch-node-3
      - cluster.name=lucid-cluster
      - discovery.seed_hosts=elasticsearch-node-1,elasticsearch-node-2
      - cluster.initial_master_nodes=elasticsearch-node-1,elasticsearch-node-2,elasticsearch-node-3
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    
    ports:
      - "9203:9200"
    
    volumes:
      - lucid-elasticsearch-node-3-data:/usr/share/elasticsearch/data
    
    networks:
      - lucid-network
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  lucid-elasticsearch-node-1-data:
    name: lucid-elasticsearch-node-1-data
  lucid-elasticsearch-node-2-data:
    name: lucid-elasticsearch-node-2-data
  lucid-elasticsearch-node-3-data:
    name: lucid-elasticsearch-node-3-data
```

---

## Auto-scaling Configuration

### Docker Swarm Auto-scaling

```yaml
# docker-compose.autoscale.yml
version: '3.8'

services:
  lucid-api-gateway:
    image: ghcr.io/hamigames/lucid/api-gateway:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.api-gateway.rule=Host(`api.lucid.onion`)"
        - "traefik.http.services.api-gateway.loadbalancer.server.port=8080"
    
    environment:
      - SERVICE_NAME=lucid-api-gateway
      - PORT=8080
      - MONGODB_URI=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
      - REDIS_URI=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
      - AUTH_SERVICE_URL=http://lucid-auth-service:8089
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network

  lucid-session-pipeline:
    image: ghcr.io/hamigames/lucid/session-pipeline:latest
    deploy:
      replicas: 5
      update_config:
        parallelism: 2
        delay: 15s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    
    environment:
      - SERVICE_NAME=lucid-session-pipeline
      - PORT=8083
      - API_GATEWAY_URL=http://lucid-api-gateway:8080
      - LOG_LEVEL=INFO
    
    networks:
      - lucid-network

  lucid-chunk-processor:
    image: ghcr.io/hamigames/lucid/chunk-processor:latest
    deploy:
      replicas: 10
      update_config:
        parallelism: 3
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    
    environment:
      - SERVICE_NAME=lucid-chunk-processor
      - PORT=8085
      - SESSION_RECORDER_URL=http://lucid-session-recorder:8084
      - LOG_LEVEL=INFO
    
    volumes:
      - lucid-chunk-data:/data/chunks
    
    networks:
      - lucid-network
```

### Kubernetes Auto-scaling

```yaml
# k8s/autoscale.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lucid-api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lucid-api-gateway
  template:
    metadata:
      labels:
        app: lucid-api-gateway
    spec:
      containers:
      - name: lucid-api-gateway
        image: ghcr.io/hamigames/lucid/api-gateway:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        env:
        - name: SERVICE_NAME
          value: "lucid-api-gateway"
        - name: PORT
          value: "8080"
        - name: MONGODB_URI
          value: "mongodb://lucid:${MONGO_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin"
        - name: REDIS_URI
          value: "redis://:${REDIS_PASSWORD}@lucid-redis:6379/0"
        - name: AUTH_SERVICE_URL
          value: "http://lucid-auth-service:8089"
        - name: LOG_LEVEL
          value: "INFO"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: lucid-api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: lucid-api-gateway
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Performance Monitoring

### Scaling Metrics

```yaml
# monitoring/scaling-metrics.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: scaling-metrics
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    scrape_configs:
      - job_name: 'lucid-scaling'
        static_configs:
          - targets: ['lucid-api-gateway:8080', 'lucid-session-pipeline:8083', 'lucid-chunk-processor:8085']
        metrics_path: '/metrics'
        scrape_interval: 30s

    rule_files:
      - "scaling-rules.yml"

    alerting:
      alertmanagers:
        - static_configs:
            - targets:
              - alertmanager:9093

  scaling-rules.yml: |
    groups:
      - name: lucid-scaling
        rules:
          - alert: HighCPUUsage
            expr: rate(container_cpu_usage_seconds_total[5m]) > 0.8
            for: 2m
            labels:
              severity: warning
            annotations:
              summary: "High CPU usage detected"
              description: "CPU usage is {{ $value }}% for {{ $labels.container }}"

          - alert: HighMemoryUsage
            expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8
            for: 2m
            labels:
              severity: warning
            annotations:
              summary: "High memory usage detected"
              description: "Memory usage is {{ $value }}% for {{ $labels.container }}"

          - alert: ServiceDown
            expr: up{job="lucid-.*"} == 0
            for: 1m
            labels:
              severity: critical
            annotations:
              summary: "Service is down"
              description: "Service {{ $labels.job }} has been down for more than 1 minute"
```

### Auto-scaling Scripts

```bash
#!/bin/bash
# scripts/scaling/auto-scale.sh

set -e

# Configuration
MIN_REPLICAS=3
MAX_REPLICAS=10
CPU_THRESHOLD=70
MEMORY_THRESHOLD=80
SCALE_UP_THRESHOLD=80
SCALE_DOWN_THRESHOLD=30

echo "Starting auto-scaling process..."

# Get current metrics
CPU_USAGE=$(docker stats --no-stream --format "{{.CPUPerc}}" lucid-api-gateway | sed 's/%//')
MEMORY_USAGE=$(docker stats --no-stream --format "{{.MemPerc}}" lucid-api-gateway | sed 's/%//')

echo "Current CPU usage: ${CPU_USAGE}%"
echo "Current memory usage: ${MEMORY_USAGE}%"

# Get current replica count
CURRENT_REPLICAS=$(docker service ls --format "{{.Replicas}}" --filter name=lucid-api-gateway | cut -d'/' -f1)

echo "Current replicas: ${CURRENT_REPLICAS}"

# Scale up if needed
if (( $(echo "$CPU_USAGE > $SCALE_UP_THRESHOLD" | bc -l) )) || (( $(echo "$MEMORY_USAGE > $SCALE_UP_THRESHOLD" | bc -l) )); then
    if [ "$CURRENT_REPLICAS" -lt "$MAX_REPLICAS" ]; then
        NEW_REPLICAS=$((CURRENT_REPLICAS + 1))
        echo "Scaling up to ${NEW_REPLICAS} replicas..."
        docker service scale lucid-api-gateway=${NEW_REPLICAS}
    else
        echo "Already at maximum replicas (${MAX_REPLICAS})"
    fi
fi

# Scale down if needed
if (( $(echo "$CPU_USAGE < $SCALE_DOWN_THRESHOLD" | bc -l) )) && (( $(echo "$MEMORY_USAGE < $SCALE_DOWN_THRESHOLD" | bc -l) )); then
    if [ "$CURRENT_REPLICAS" -gt "$MIN_REPLICAS" ]; then
        NEW_REPLICAS=$((CURRENT_REPLICAS - 1))
        echo "Scaling down to ${NEW_REPLICAS} replicas..."
        docker service scale lucid-api-gateway=${NEW_REPLICAS}
    else
        echo "Already at minimum replicas (${MIN_REPLICAS})"
    fi
fi

echo "Auto-scaling process completed!"
```

---

## Load Testing

### Load Testing Scripts

```bash
#!/bin/bash
# scripts/load-test/run-load-test.sh

set -e

# Configuration
CONCURRENT_USERS=100
TEST_DURATION=300  # 5 minutes
API_ENDPOINT="http://localhost:8080"

echo "Starting load test..."
echo "Concurrent users: ${CONCURRENT_USERS}"
echo "Test duration: ${TEST_DURATION} seconds"
echo "API endpoint: ${API_ENDPOINT}"

# Install k6 if not present
if ! command -v k6 &> /dev/null; then
    echo "Installing k6..."
    curl -s https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz | tar xz
    sudo mv k6-v0.47.0-linux-amd64/k6 /usr/local/bin/
fi

# Create load test script
cat > load-test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: __ENV.CONCURRENT_USERS || 100,
  duration: __ENV.TEST_DURATION || '5m',
};

export default function() {
  // Test API Gateway health
  let response = http.get(`${__ENV.API_ENDPOINT}/health`);
  check(response, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 100ms': (r) => r.timings.duration < 100,
  });

  // Test authentication endpoint
  response = http.post(`${__ENV.API_ENDPOINT}/api/v1/auth/login`, {
    email: 'test@example.com',
    password: 'testpassword'
  });
  check(response, {
    'login status is 200 or 401': (r) => r.status === 200 || r.status === 401,
    'login response time < 500ms': (r) => r.timings.duration < 500,
  });

  // Test session creation
  response = http.post(`${__ENV.API_ENDPOINT}/api/v1/sessions`, {
    name: 'Test Session',
    description: 'Load test session'
  });
  check(response, {
    'session creation status is 200 or 401': (r) => r.status === 200 || r.status === 401,
    'session creation response time < 1000ms': (r) => r.timings.duration < 1000,
  });

  sleep(1);
}
EOF

# Run load test
echo "Running load test..."
k6 run --env CONCURRENT_USERS=${CONCURRENT_USERS} --env TEST_DURATION=${TEST_DURATION}s --env API_ENDPOINT=${API_ENDPOINT} load-test.js

echo "Load test completed!"
```

### Performance Benchmarks

```bash
#!/bin/bash
# scripts/load-test/performance-benchmarks.sh

set -e

echo "=== Lucid System Performance Benchmarks ==="

# API Gateway benchmarks
echo "=== API Gateway Benchmarks ==="
echo "Testing API Gateway performance..."

# Test health endpoint
echo "Testing health endpoint..."
for i in {1..100}; do
  curl -s -w "%{time_total}\n" -o /dev/null http://localhost:8080/health
done | awk '{sum+=$1; count++} END {print "Average response time: " sum/count " seconds"}'

# Test authentication endpoint
echo "Testing authentication endpoint..."
for i in {1..50}; do
  curl -s -w "%{time_total}\n" -o /dev/null -X POST http://localhost:8080/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"testpassword"}'
done | awk '{sum+=$1; count++} END {print "Average response time: " sum/count " seconds"}'

# Test session creation endpoint
echo "Testing session creation endpoint..."
for i in {1..50}; do
  curl -s -w "%{time_total}\n" -o /dev/null -X POST http://localhost:8080/api/v1/sessions \
    -H "Content-Type: application/json" \
    -d '{"name":"Test Session","description":"Benchmark test"}'
done | awk '{sum+=$1; count++} END {print "Average response time: " sum/count " seconds"}'

# Blockchain benchmarks
echo "=== Blockchain Benchmarks ==="
echo "Testing blockchain performance..."

# Test blockchain info endpoint
echo "Testing blockchain info endpoint..."
for i in {1..100}; do
  curl -s -w "%{time_total}\n" -o /dev/null http://localhost:8084/api/v1/blockchain/info
done | awk '{sum+=$1; count++} END {print "Average response time: " sum/count " seconds"}'

# Test block creation
echo "Testing block creation..."
for i in {1..50}; do
  curl -s -w "%{time_total}\n" -o /dev/null -X POST http://localhost:8084/api/v1/blocks \
    -H "Content-Type: application/json" \
    -d '{"transactions":[],"previous_hash":"test"}'
done | awk '{sum+=$1; count++} END {print "Average response time: " sum/count " seconds"}'

# Session Management benchmarks
echo "=== Session Management Benchmarks ==="
echo "Testing session management performance..."

# Test session pipeline
echo "Testing session pipeline..."
for i in {1..50}; do
  curl -s -w "%{time_total}\n" -o /dev/null http://localhost:8083/api/v1/pipeline/status
done | awk '{sum+=$1; count++} END {print "Average response time: " sum/count " seconds"}'

# Test session recording
echo "Testing session recording..."
for i in {1..50}; do
  curl -s -w "%{time_total}\n" -o /dev/null http://localhost:8084/api/v1/recording/status
done | awk '{sum+=$1; count++} END {print "Average response time: " sum/count " seconds"}'

# Test chunk processing
echo "Testing chunk processing..."
for i in {1..50}; do
  curl -s -w "%{time_total}\n" -o /dev/null http://localhost:8085/api/v1/processing/status
done | awk '{sum+=$1; count++} END {print "Average response time: " sum/count " seconds"}'

echo "=== Performance Benchmarks Complete ==="
```

---

## Scaling Validation

### Scaling Validation Script

```bash
#!/bin/bash
# scripts/scaling/validate-scaling.sh

set -e

echo "=== Lucid System Scaling Validation ==="

# Check current replica counts
echo "=== Current Replica Counts ==="
docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" --filter name=lucid-

# Check resource usage
echo "=== Resource Usage ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check service health
echo "=== Service Health ==="
curl -f http://localhost:8080/health || echo "API Gateway: FAILED"
curl -f http://localhost:8084/health || echo "Blockchain Engine: FAILED"
curl -f http://localhost:8083/health || echo "Session Pipeline: FAILED"
curl -f http://localhost:8085/health || echo "Chunk Processor: FAILED"

# Check load balancer status
echo "=== Load Balancer Status ==="
curl -f http://localhost:8080/api/v1/load-balancer/status || echo "Load Balancer: FAILED"

# Check database cluster status
echo "=== Database Cluster Status ==="
docker exec lucid-mongodb-primary mongosh --eval "rs.status()" | grep -E "(name|stateStr|uptime)"
docker exec lucid-redis-node-1 redis-cli --cluster nodes | head -5

# Check auto-scaling status
echo "=== Auto-scaling Status ==="
docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" --filter name=lucid- | grep -E "(api-gateway|session-pipeline|chunk-processor)"

echo "=== Scaling Validation Complete ==="
```

---

## References

- [Deployment Guide](./deployment-guide.md)
- [Troubleshooting Guide](./troubleshooting-guide.md)
- [Backup Recovery Guide](./backup-recovery-guide.md)
- [Security Hardening Guide](./security-hardening-guide.md)
- [Master Build Plan](../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)

---

**Document Version**: 1.0.0  
**Status**: ACTIVE  
**Last Updated**: 2025-01-14
