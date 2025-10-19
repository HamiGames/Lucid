# Phase 1 Docker Compose Generation

## Overview
Generate complete Docker Compose file for Phase 1 foundation services with real configurations, health checks, and proper service dependencies.

## Location
`configs/docker/docker-compose.foundation.yml`

## Services Defined

### 1. MongoDB Service
```yaml
lucid-mongodb:
  image: pickme/lucid-mongodb:latest-arm64
  container_name: lucid-mongodb
  restart: unless-stopped
  ports:
    - "27017:27017"
  environment:
    - MONGO_INITDB_ROOT_USERNAME=lucid
    - MONGO_INITDB_ROOT_PASSWORD=${MONGODB_PASSWORD}
    - MONGO_INITDB_DATABASE=lucid
  volumes:
    - mongodb_data:/data/db
    - mongodb_config:/etc/mongod
  networks:
    - lucid-pi-network
  healthcheck:
    test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
      reservations:
        memory: 512M
        cpus: '0.5'
```

### 2. Redis Service
```yaml
lucid-redis:
  image: pickme/lucid-redis:latest-arm64
  container_name: lucid-redis
  restart: unless-stopped
  ports:
    - "6379:6379"
  environment:
    - REDIS_PASSWORD=${REDIS_PASSWORD}
  volumes:
    - redis_data:/data
    - redis_config:/etc/redis
  networks:
    - lucid-pi-network
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.5'
      reservations:
        memory: 256M
        cpus: '0.25'
```

### 3. Elasticsearch Service
```yaml
lucid-elasticsearch:
  image: pickme/lucid-elasticsearch:latest-arm64
  container_name: lucid-elasticsearch
  restart: unless-stopped
  ports:
    - "9200:9200"
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=true
    - xpack.security.authc.api_key.enabled=true
    - xpack.security.transport.ssl.enabled=false
    - xpack.security.http.ssl.enabled=false
    - bootstrap.memory_lock=true
    - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
  volumes:
    - elasticsearch_data:/usr/share/elasticsearch/data
    - elasticsearch_config:/etc/elasticsearch
  networks:
    - lucid-pi-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
      reservations:
        memory: 512M
        cpus: '0.5'
  ulimits:
    memlock:
      soft: -1
      hard: -1
```

### 4. Authentication Service
```yaml
lucid-auth-service:
  image: pickme/lucid-auth-service:latest-arm64
  container_name: lucid-auth-service
  restart: unless-stopped
  ports:
    - "8089:8089"
  environment:
    - MONGODB_URI=${MONGODB_URI}
    - REDIS_URL=${REDIS_URL}
    - ELASTICSEARCH_URL=${ELASTICSEARCH_URL}
    - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    - TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}
  volumes:
    - auth_logs:/app/logs
  networks:
    - lucid-pi-network
  depends_on:
    lucid-mongodb:
      condition: service_healthy
    lucid-redis:
      condition: service_healthy
    lucid-elasticsearch:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8089/health')"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.5'
      reservations:
        memory: 256M
        cpus: '0.25'
```

## Network Configuration
```yaml
networks:
  lucid-pi-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
```

## Volume Configuration
```yaml
volumes:
  mongodb_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/mongodb
  mongodb_config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/config/mongodb
  redis_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/redis
  redis_config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/config/redis
  elasticsearch_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/elasticsearch
  elasticsearch_config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/config/elasticsearch
  auth_logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/logs/auth
```

## Complete Docker Compose File

**File**: `configs/docker/docker-compose.foundation.yml`

```yaml
version: '3.8'

services:
  lucid-mongodb:
    image: pickme/lucid-mongodb:latest-arm64
    container_name: lucid-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGODB_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/etc/mongod
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'

  lucid-redis:
    image: pickme/lucid-redis:latest-arm64
    container_name: lucid-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
      - redis_config:/etc/redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

  lucid-elasticsearch:
    image: pickme/lucid-elasticsearch:latest-arm64
    container_name: lucid-elasticsearch
    restart: unless-stopped
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.authc.api_key.enabled=true
      - xpack.security.transport.ssl.enabled=false
      - xpack.security.http.ssl.enabled=false
      - bootstrap.memory_lock=true
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
      - elasticsearch_config:/etc/elasticsearch
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    ulimits:
      memlock:
        soft: -1
        hard: -1

  lucid-auth-service:
    image: pickme/lucid-auth-service:latest-arm64
    container_name: lucid-auth-service
    restart: unless-stopped
    ports:
      - "8089:8089"
    environment:
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - ELASTICSEARCH_URL=${ELASTICSEARCH_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}
    volumes:
      - auth_logs:/app/logs
    networks:
      - lucid-pi-network
    depends_on:
      lucid-mongodb:
        condition: service_healthy
      lucid-redis:
        condition: service_healthy
      lucid-elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8089/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

networks:
  lucid-pi-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1

volumes:
  mongodb_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/mongodb
  mongodb_config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/config/mongodb
  redis_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/redis
  redis_config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/config/redis
  elasticsearch_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/elasticsearch
  elasticsearch_config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/config/elasticsearch
  auth_logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/logs/auth
```

## Generation Script Implementation

**File**: `scripts/foundation/generate-phase1-compose.sh`

```bash
#!/bin/bash
# scripts/foundation/generate-phase1-compose.sh
# Generate Phase 1 Docker Compose file

set -e

echo "Generating Phase 1 Docker Compose file..."

# Create configs directory if it doesn't exist
mkdir -p configs/docker

# Generate Docker Compose file
cat > configs/docker/docker-compose.foundation.yml << 'EOF'
version: '3.8'

services:
  lucid-mongodb:
    image: pickme/lucid-mongodb:latest-arm64
    container_name: lucid-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGODB_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/etc/mongod
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'

  lucid-redis:
    image: pickme/lucid-redis:latest-arm64
    container_name: lucid-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
      - redis_config:/etc/redis
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

  lucid-elasticsearch:
    image: pickme/lucid-elasticsearch:latest-arm64
    container_name: lucid-elasticsearch
    restart: unless-stopped
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.authc.api_key.enabled=true
      - xpack.security.transport.ssl.enabled=false
      - xpack.security.http.ssl.enabled=false
      - bootstrap.memory_lock=true
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
      - elasticsearch_config:/etc/elasticsearch
    networks:
      - lucid-pi-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    ulimits:
      memlock:
        soft: -1
        hard: -1

  lucid-auth-service:
    image: pickme/lucid-auth-service:latest-arm64
    container_name: lucid-auth-service
    restart: unless-stopped
    ports:
      - "8089:8089"
    environment:
      - MONGODB_URI=${MONGODB_URI}
      - REDIS_URL=${REDIS_URL}
      - ELASTICSEARCH_URL=${ELASTICSEARCH_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - TOR_CONTROL_PASSWORD=${TOR_CONTROL_PASSWORD}
    volumes:
      - auth_logs:/app/logs
    networks:
      - lucid-pi-network
    depends_on:
      lucid-mongodb:
        condition: service_healthy
      lucid-redis:
        condition: service_healthy
      lucid-elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8089/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

networks:
  lucid-pi-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1

volumes:
  mongodb_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/mongodb
  mongodb_config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/config/mongodb
  redis_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/redis
  redis_config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/config/redis
  elasticsearch_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/elasticsearch
  elasticsearch_config:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/config/elasticsearch
  auth_logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/logs/auth
EOF

echo "Phase 1 Docker Compose file generated successfully!"
echo "File: configs/docker/docker-compose.foundation.yml"
```

## Validation Criteria
- `docker-compose config` validates successfully
- All service dependencies are correctly defined
- Health checks are properly configured
- Resource limits are appropriate for Pi hardware
- Network configuration is correct
- Volume mounts are properly configured

## Environment Variables Required
- `MONGODB_PASSWORD` - MongoDB root password
- `REDIS_PASSWORD` - Redis password
- `MONGODB_URI` - MongoDB connection string
- `REDIS_URL` - Redis connection string
- `ELASTICSEARCH_URL` - Elasticsearch connection string
- `JWT_SECRET_KEY` - JWT signing secret
- `ENCRYPTION_KEY` - Encryption key for sensitive data
- `TOR_CONTROL_PASSWORD` - Tor control password

## Service Dependencies
1. **MongoDB** - No dependencies (foundation service)
2. **Redis** - No dependencies (foundation service)
3. **Elasticsearch** - No dependencies (foundation service)
4. **Authentication Service** - Depends on MongoDB, Redis, and Elasticsearch

## Health Check Configuration
- **MongoDB**: `mongosh --eval "db.adminCommand('ping')"`
- **Redis**: `redis-cli ping`
- **Elasticsearch**: `curl -f http://localhost:9200/_cluster/health`
- **Authentication Service**: HTTP GET to `/health` endpoint

## Resource Allocation
- **MongoDB**: 1GB memory, 1 CPU core (max), 512MB memory, 0.5 CPU core (reserved)
- **Redis**: 512MB memory, 0.5 CPU core (max), 256MB memory, 0.25 CPU core (reserved)
- **Elasticsearch**: 1GB memory, 1 CPU core (max), 512MB memory, 0.5 CPU core (reserved)
- **Authentication Service**: 512MB memory, 0.5 CPU core (max), 256MB memory, 0.25 CPU core (reserved)

## Troubleshooting

### Compose Validation
```bash
# Validate compose file
docker-compose -f configs/docker/docker-compose.foundation.yml config

# Check for syntax errors
docker-compose -f configs/docker/docker-compose.foundation.yml config --quiet
```

### Environment Variables
```bash
# Check environment variables are set
echo $MONGODB_PASSWORD
echo $REDIS_PASSWORD
echo $JWT_SECRET_KEY
```

### Network Issues
```bash
# Check network configuration
docker network ls
docker network inspect lucid-pi-network
```

## Next Steps
After successful Docker Compose generation, proceed to Phase 1 deployment to Pi.
