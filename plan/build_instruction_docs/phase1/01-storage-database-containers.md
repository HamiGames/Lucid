# Storage Database Containers

## Overview
Build MongoDB, Redis, and Elasticsearch containers for arm64 using distroless base images for Phase 1 foundation services.

## Location
`infrastructure/containers/storage/`

## Containers to Build

### 1. MongoDB Container
**File**: `infrastructure/containers/storage/Dockerfile.mongodb`

```dockerfile
# Multi-stage build for MongoDB distroless container
FROM mongo:7.0 as mongodb-builder

# Install additional tools for configuration
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create configuration directory
RUN mkdir -p /etc/mongod

# Copy custom configuration
COPY mongod.conf /etc/mongod/mongod.conf

# Create data directory
RUN mkdir -p /data/db && chown -R mongodb:mongodb /data/db

# Final distroless stage
FROM gcr.io/distroless/base-debian12:arm64

# Copy MongoDB binaries and configuration
COPY --from=mongodb-builder /usr/bin/mongod /usr/bin/mongod
COPY --from=mongodb-builder /usr/bin/mongosh /usr/bin/mongosh
COPY --from=mongodb-builder /etc/mongod /etc/mongod
COPY --from=mongodb-builder /data/db /data/db

# Copy required libraries
COPY --from=mongodb-builder /lib/aarch64-linux-gnu/libssl.so.3 /lib/aarch64-linux-gnu/
COPY --from=mongodb-builder /lib/aarch64-linux-gnu/libcrypto.so.3 /lib/aarch64-linux-gnu/
COPY --from=mongodb-builder /lib/aarch64-linux-gnu/libz.so.1 /lib/aarch64-linux-gnu/
COPY --from=mongodb-builder /lib/aarch64-linux-gnu/libsnappy.so.1 /lib/aarch64-linux-gnu/

# Set working directory
WORKDIR /data/db

# Set non-root user
USER 999:999

# Expose port
EXPOSE 27017

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/bin/mongosh", "--eval", "db.adminCommand('ping')"]

# Default command
CMD ["/usr/bin/mongod", "--config", "/etc/mongod/mongod.conf"]
```

**Configuration File**: `infrastructure/containers/storage/mongod.conf`
```yaml
# MongoDB configuration for Lucid system
storage:
  dbPath: /data/db
  journal:
    enabled: true
  wiredTiger:
    engineConfig:
      cacheSizeGB: 1
    collectionConfig:
      blockCompressor: snappy
    indexConfig:
      prefixCompression: true

systemLog:
  destination: file
  path: /var/log/mongodb/mongod.log
  logAppend: true
  verbosity: 1

net:
  port: 27017
  bindIp: 0.0.0.0
  maxIncomingConnections: 100

processManagement:
  fork: false
  pidFilePath: /var/run/mongodb/mongod.pid

security:
  authorization: enabled

replication:
  replSetName: lucid-rs

operationProfiling:
  slowOpThresholdMs: 100
  mode: slowOp
```

### 2. Redis Container
**File**: `infrastructure/containers/storage/Dockerfile.redis`

```dockerfile
# Multi-stage build for Redis distroless container
FROM redis:7.2 as redis-builder

# Install additional tools
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create configuration directory
RUN mkdir -p /etc/redis

# Copy custom configuration
COPY redis.conf /etc/redis/redis.conf

# Create data directory
RUN mkdir -p /data && chown -R redis:redis /data

# Final distroless stage
FROM gcr.io/distroless/base-debian12:arm64

# Copy Redis binaries and configuration
COPY --from=redis-builder /usr/local/bin/redis-server /usr/local/bin/redis-server
COPY --from=redis-builder /usr/local/bin/redis-cli /usr/local/bin/redis-cli
COPY --from=redis-builder /etc/redis /etc/redis
COPY --from=redis-builder /data /data

# Copy required libraries
COPY --from=redis-builder /lib/aarch64-linux-gnu/libssl.so.3 /lib/aarch64-linux-gnu/
COPY --from=redis-builder /lib/aarch64-linux-gnu/libcrypto.so.3 /lib/aarch64-linux-gnu/
COPY --from=redis-builder /lib/aarch64-linux-gnu/libz.so.1 /lib/aarch64-linux-gnu/

# Set working directory
WORKDIR /data

# Set non-root user
USER 999:999

# Expose port
EXPOSE 6379

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/local/bin/redis-cli", "ping"]

# Default command
CMD ["/usr/local/bin/redis-server", "/etc/redis/redis.conf"]
```

**Configuration File**: `infrastructure/containers/storage/redis.conf`
```conf
# Redis configuration for Lucid system
port 6379
bind 0.0.0.0
protected-mode yes
requirepass SecureRedisPass123!

# Memory configuration
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence configuration
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis.log

# Network
tcp-keepalive 300
timeout 0

# Security
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Performance
tcp-backlog 511
databases 16
```

### 3. Elasticsearch Container
**File**: `infrastructure/containers/storage/Dockerfile.elasticsearch`

```dockerfile
# Multi-stage build for Elasticsearch distroless container
FROM elasticsearch:8.11.0 as elasticsearch-builder

# Install additional tools
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create configuration directory
RUN mkdir -p /etc/elasticsearch

# Copy custom configuration
COPY elasticsearch.yml /etc/elasticsearch/elasticsearch.yml

# Create data directory
RUN mkdir -p /usr/share/elasticsearch/data && \
    chown -R elasticsearch:elasticsearch /usr/share/elasticsearch/data

# Final distroless stage
FROM gcr.io/distroless/base-debian12:arm64

# Copy Elasticsearch binaries and configuration
COPY --from=elasticsearch-builder /usr/share/elasticsearch /usr/share/elasticsearch
COPY --from=elasticsearch-builder /etc/elasticsearch /etc/elasticsearch
COPY --from=elasticsearch-builder /usr/share/elasticsearch/data /usr/share/elasticsearch/data

# Copy required libraries
COPY --from=elasticsearch-builder /lib/aarch64-linux-gnu/libssl.so.3 /lib/aarch64-linux-gnu/
COPY --from=elasticsearch-builder /lib/aarch64-linux-gnu/libcrypto.so.3 /lib/aarch64-linux-gnu/
COPY --from=elasticsearch-builder /lib/aarch64-linux-gnu/libz.so.1 /lib/aarch64-linux-gnu/

# Set working directory
WORKDIR /usr/share/elasticsearch

# Set non-root user
USER 1000:1000

# Expose port
EXPOSE 9200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/share/elasticsearch/bin/elasticsearch", "--version"]

# Default command
CMD ["/usr/share/elasticsearch/bin/elasticsearch"]
```

**Configuration File**: `infrastructure/containers/storage/elasticsearch.yml`
```yaml
# Elasticsearch configuration for Lucid system
cluster.name: lucid-cluster
node.name: lucid-node-1
node.roles: [ master, data, ingest ]

# Network configuration
network.host: 0.0.0.0
http.port: 9200
transport.port: 9300

# Discovery configuration
discovery.type: single-node

# Security configuration
xpack.security.enabled: true
xpack.security.authc.api_key.enabled: true
xpack.security.transport.ssl.enabled: false
xpack.security.http.ssl.enabled: false

# Memory configuration
bootstrap.memory_lock: true
indices.memory.index_buffer_size: 20%
indices.queries.cache.size: 10%

# Logging configuration
logger.level: INFO
logger.level.org.elasticsearch: WARN

# Performance configuration
thread_pool.write.queue_size: 1000
thread_pool.search.queue_size: 1000
```

## Build Commands

### MongoDB Container
```bash
# Build MongoDB container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-mongodb:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.mongodb \
  --push \
  .
```

### Redis Container
```bash
# Build Redis container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-redis:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.redis \
  --push \
  .
```

### Elasticsearch Container
```bash
# Build Elasticsearch container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-elasticsearch:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.elasticsearch \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/foundation/build-storage-containers.sh`

```bash
#!/bin/bash
# scripts/foundation/build-storage-containers.sh
# Build storage database containers for Phase 1

set -e

echo "Building storage database containers..."

# Create storage containers directory
mkdir -p infrastructure/containers/storage

# Create MongoDB configuration
cat > infrastructure/containers/storage/mongod.conf << 'EOF'
# MongoDB configuration for Lucid system
storage:
  dbPath: /data/db
  journal:
    enabled: true
  wiredTiger:
    engineConfig:
      cacheSizeGB: 1
    collectionConfig:
      blockCompressor: snappy
    indexConfig:
      prefixCompression: true

systemLog:
  destination: file
  path: /var/log/mongodb/mongod.log
  logAppend: true
  verbosity: 1

net:
  port: 27017
  bindIp: 0.0.0.0
  maxIncomingConnections: 100

processManagement:
  fork: false
  pidFilePath: /var/run/mongodb/mongod.pid

security:
  authorization: enabled

replication:
  replSetName: lucid-rs

operationProfiling:
  slowOpThresholdMs: 100
  mode: slowOp
EOF

# Create Redis configuration
cat > infrastructure/containers/storage/redis.conf << 'EOF'
# Redis configuration for Lucid system
port 6379
bind 0.0.0.0
protected-mode yes
requirepass SecureRedisPass123!

# Memory configuration
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence configuration
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis.log

# Network
tcp-keepalive 300
timeout 0

# Security
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Performance
tcp-backlog 511
databases 16
EOF

# Create Elasticsearch configuration
cat > infrastructure/containers/storage/elasticsearch.yml << 'EOF'
# Elasticsearch configuration for Lucid system
cluster.name: lucid-cluster
node.name: lucid-node-1
node.roles: [ master, data, ingest ]

# Network configuration
network.host: 0.0.0.0
http.port: 9200
transport.port: 9300

# Discovery configuration
discovery.type: single-node

# Security configuration
xpack.security.enabled: true
xpack.security.authc.api_key.enabled: true
xpack.security.transport.ssl.enabled: false
xpack.security.http.ssl.enabled: false

# Memory configuration
bootstrap.memory_lock: true
indices.memory.index_buffer_size: 20%
indices.queries.cache.size: 10%

# Logging configuration
logger.level: INFO
logger.level.org.elasticsearch: WARN

# Performance configuration
thread_pool.write.queue_size: 1000
thread_pool.search.queue_size: 1000
EOF

# Create MongoDB Dockerfile
cat > infrastructure/containers/storage/Dockerfile.mongodb << 'EOF'
# Multi-stage build for MongoDB distroless container
FROM mongo:7.0 as mongodb-builder

# Install additional tools for configuration
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create configuration directory
RUN mkdir -p /etc/mongod

# Copy custom configuration
COPY mongod.conf /etc/mongod/mongod.conf

# Create data directory
RUN mkdir -p /data/db && chown -R mongodb:mongodb /data/db

# Final distroless stage
FROM gcr.io/distroless/base-debian12:arm64

# Copy MongoDB binaries and configuration
COPY --from=mongodb-builder /usr/bin/mongod /usr/bin/mongod
COPY --from=mongodb-builder /usr/bin/mongosh /usr/bin/mongosh
COPY --from=mongodb-builder /etc/mongod /etc/mongod
COPY --from=mongodb-builder /data/db /data/db

# Copy required libraries
COPY --from=mongodb-builder /lib/aarch64-linux-gnu/libssl.so.3 /lib/aarch64-linux-gnu/
COPY --from=mongodb-builder /lib/aarch64-linux-gnu/libcrypto.so.3 /lib/aarch64-linux-gnu/
COPY --from=mongodb-builder /lib/aarch64-linux-gnu/libz.so.1 /lib/aarch64-linux-gnu/
COPY --from=mongodb-builder /lib/aarch64-linux-gnu/libsnappy.so.1 /lib/aarch64-linux-gnu/

# Set working directory
WORKDIR /data/db

# Set non-root user
USER 999:999

# Expose port
EXPOSE 27017

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/bin/mongosh", "--eval", "db.adminCommand('ping')"]

# Default command
CMD ["/usr/bin/mongod", "--config", "/etc/mongod/mongod.conf"]
EOF

# Create Redis Dockerfile
cat > infrastructure/containers/storage/Dockerfile.redis << 'EOF'
# Multi-stage build for Redis distroless container
FROM redis:7.2 as redis-builder

# Install additional tools
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create configuration directory
RUN mkdir -p /etc/redis

# Copy custom configuration
COPY redis.conf /etc/redis/redis.conf

# Create data directory
RUN mkdir -p /data && chown -R redis:redis /data

# Final distroless stage
FROM gcr.io/distroless/base-debian12:arm64

# Copy Redis binaries and configuration
COPY --from=redis-builder /usr/local/bin/redis-server /usr/local/bin/redis-server
COPY --from=redis-builder /usr/local/bin/redis-cli /usr/local/bin/redis-cli
COPY --from=redis-builder /etc/redis /etc/redis
COPY --from=redis-builder /data /data

# Copy required libraries
COPY --from=redis-builder /lib/aarch64-linux-gnu/libssl.so.3 /lib/aarch64-linux-gnu/
COPY --from=redis-builder /lib/aarch64-linux-gnu/libcrypto.so.3 /lib/aarch64-linux-gnu/
COPY --from=redis-builder /lib/aarch64-linux-gnu/libz.so.1 /lib/aarch64-linux-gnu/

# Set working directory
WORKDIR /data

# Set non-root user
USER 999:999

# Expose port
EXPOSE 6379

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/local/bin/redis-cli", "ping"]

# Default command
CMD ["/usr/local/bin/redis-server", "/etc/redis/redis.conf"]
EOF

# Create Elasticsearch Dockerfile
cat > infrastructure/containers/storage/Dockerfile.elasticsearch << 'EOF'
# Multi-stage build for Elasticsearch distroless container
FROM elasticsearch:8.11.0 as elasticsearch-builder

# Install additional tools
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create configuration directory
RUN mkdir -p /etc/elasticsearch

# Copy custom configuration
COPY elasticsearch.yml /etc/elasticsearch/elasticsearch.yml

# Create data directory
RUN mkdir -p /usr/share/elasticsearch/data && \
    chown -R elasticsearch:elasticsearch /usr/share/elasticsearch/data

# Final distroless stage
FROM gcr.io/distroless/base-debian12:arm64

# Copy Elasticsearch binaries and configuration
COPY --from=elasticsearch-builder /usr/share/elasticsearch /usr/share/elasticsearch
COPY --from=elasticsearch-builder /etc/elasticsearch /etc/elasticsearch
COPY --from=elasticsearch-builder /usr/share/elasticsearch/data /usr/share/elasticsearch/data

# Copy required libraries
COPY --from=elasticsearch-builder /lib/aarch64-linux-gnu/libssl.so.3 /lib/aarch64-linux-gnu/
COPY --from=elasticsearch-builder /lib/aarch64-linux-gnu/libcrypto.so.3 /lib/aarch64-linux-gnu/
COPY --from=elasticsearch-builder /lib/aarch64-linux-gnu/libz.so.1 /lib/aarch64-linux-gnu/

# Set working directory
WORKDIR /usr/share/elasticsearch

# Set non-root user
USER 1000:1000

# Expose port
EXPOSE 9200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/share/elasticsearch/bin/elasticsearch", "--version"]

# Default command
CMD ["/usr/share/elasticsearch/bin/elasticsearch"]
EOF

# Build MongoDB container
echo "Building MongoDB container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-mongodb:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.mongodb \
  --push \
  .

# Build Redis container
echo "Building Redis container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-redis:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.redis \
  --push \
  .

# Build Elasticsearch container
echo "Building Elasticsearch container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-elasticsearch:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.elasticsearch \
  --push \
  .

echo "Storage database containers built and pushed successfully!"
echo "Available containers:"
echo "- pickme/lucid-mongodb:latest-arm64"
echo "- pickme/lucid-redis:latest-arm64"
echo "- pickme/lucid-elasticsearch:latest-arm64"
```

## Validation Criteria
- All 3 containers built and pushed to Docker Hub
- Total combined size <500MB
- All containers use distroless base images
- Health checks configured for all containers
- Non-root users configured
- Proper security configurations applied

## Environment Configuration
Uses `.env.foundation` for:
- Database connection strings
- Authentication credentials
- Port configurations
- Health check settings

## Security Features
- **Distroless Runtime**: No shell or package manager
- **Non-root Users**: All containers run as non-root
- **Authentication**: All databases require authentication
- **Network Security**: Protected mode enabled
- **Command Restrictions**: Dangerous commands disabled

## Performance Optimizations
- **Memory Limits**: Appropriate memory limits for Pi hardware
- **Compression**: Snappy compression for MongoDB
- **Caching**: Redis LRU eviction policy
- **Indexing**: Optimized Elasticsearch indices

## Troubleshooting

### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain \
  --platform linux/arm64 \
  -t pickme/lucid-mongodb:latest-arm64 \
  -f infrastructure/containers/storage/Dockerfile.mongodb \
  .
```

### Configuration Issues
- Verify configuration files are properly formatted
- Check port assignments don't conflict
- Ensure authentication credentials are set

### Health Check Failures
```bash
# Test health checks manually
docker run --rm pickme/lucid-mongodb:latest-arm64 mongosh --eval "db.adminCommand('ping')"
```

## Next Steps
After successful storage container builds, proceed to authentication service container build.
