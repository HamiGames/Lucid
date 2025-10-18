# API Gateway Cluster - Deployment & Operations Guide

## Overview

This document provides comprehensive deployment and operations guidance for the Lucid API Gateway cluster, covering Docker Compose configurations, health checks, monitoring, scaling, troubleshooting, and operational procedures.

## Deployment Architecture

### Service Components

- **lucid-api-gateway**: Main API Gateway service (Port 8080/8081)
- **lucid-auth-proxy**: Authentication proxy service
- **lucid-rate-limiter**: Rate limiting service
- **MongoDB**: Primary database (Port 27017)
- **Redis**: Rate limiting and caching (Port 6379)

### Network Configuration

```yaml
# Network topology for API Gateway cluster
networks:
  lucid-api-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
```

## Docker Compose Configuration

### Production Deployment

```yaml
# docker-compose.prod.yml
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
      - ENVIRONMENT=production
      - MONGO_URL=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongo:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - RATE_LIMIT_REDIS_URL=redis://lucid-redis:6379/1
      - LOG_LEVEL=INFO
      - TOR_PROXY_URL=socks5://lucid-tor:9050
    
    ports:
      - "8080:8080"
      - "8081:8081"
    
    volumes:
      - type: bind
        source: ./configs/api-gateway
        target: /app/config
        read_only: true
      - type: bind
        source: ./logs/api-gateway
        target: /app/logs
    
    networks:
      - lucid-api-net
    
    depends_on:
      - lucid-mongo
      - lucid-redis
      - lucid-tor
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
  
  lucid-auth-proxy:
    image: ghcr.io/hamigames/lucid/auth-proxy:latest
    container_name: lucid-auth-proxy
    hostname: auth-proxy
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-auth-proxy
      - PORT=8082
      - ENVIRONMENT=production
      - MONGO_URL=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongo:27017/lucid?authSource=admin
      - JWT_SECRET=${JWT_SECRET}
      - MFA_SECRET=${MFA_SECRET}
      - LOG_LEVEL=INFO
    
    ports:
      - "8082:8082"
    
    volumes:
      - type: bind
        source: ./configs/auth-proxy
        target: /app/config
        read_only: true
    
    networks:
      - lucid-api-net
    
    depends_on:
      - lucid-mongo
      - lucid-api-gateway
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
  
  lucid-rate-limiter:
    image: ghcr.io/hamigames/lucid/rate-limiter:latest
    container_name: lucid-rate-limiter
    hostname: rate-limiter
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-rate-limiter
      - PORT=8083
      - ENVIRONMENT=production
      - REDIS_URL=redis://lucid-redis:6379/1
      - LOG_LEVEL=INFO
    
    ports:
      - "8083:8083"
    
    volumes:
      - type: bind
        source: ./configs/rate-limiter
        target: /app/config
        read_only: true
    
    networks:
      - lucid-api-net
    
    depends_on:
      - lucid-redis
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8083/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'
        reservations:
          memory: 128M
          cpus: '0.1'
  
  lucid-mongo:
    image: mongo:7.0
    container_name: lucid-mongo
    hostname: mongo
    restart: unless-stopped
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    
    volumes:
      - type: volume
        source: lucid-mongo-data
        target: /data/db
      - type: bind
        source: ./scripts/database/init_mongodb_schema.js
        target: /docker-entrypoint-initdb.d/init_schema.js:ro
      - type: bind
        source: ./configs/mongodb/mongod.conf
        target: /etc/mongod.conf:ro
    
    ports:
      - "27017:27017"
    
    networks:
      - lucid-api-net
    
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
    
    volumes:
      - type: volume
        source: lucid-redis-data
        target: /data
      - type: bind
        source: ./configs/redis/redis.conf
        target: /usr/local/etc/redis/redis.conf:ro
    
    ports:
      - "6379:6379"
    
    networks:
      - lucid-api-net
    
    command: ["redis-server", "/usr/local/etc/redis/redis.conf"]
    
    healthcheck:
      test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
  
  lucid-tor:
    image: alpine:3.18
    container_name: lucid-tor
    hostname: tor
    restart: unless-stopped
    
    volumes:
      - type: bind
        source: ./configs/tor/torrc.prod
        target: /etc/tor/torrc:ro
    
    ports:
      - "9050:9050"  # SOCKS proxy
      - "9051:9051"  # Control port
    
    networks:
      - lucid-api-net
    
    command: ["sh", "-c", "apk add --no-cache tor && tor -f /etc/tor/torrc"]
    
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "9050"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
        reservations:
          memory: 64M
          cpus: '0.1'

volumes:
  lucid-mongo-data:
    name: lucid-mongo-data
    driver: local
  lucid-redis-data:
    name: lucid-redis-data
    driver: local

networks:
  lucid-api-net:
    name: lucid-api-net
    driver: bridge
    attachable: true
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
```

### Development Deployment

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  lucid-api-gateway:
    build:
      context: ../../03-api-gateway/api
      dockerfile: Dockerfile
      target: development
    container_name: lucid-api-gateway-dev
    hostname: api-gateway-dev
    restart: unless-stopped
    
    environment:
      - SERVICE_NAME=lucid-api-gateway
      - PORT=8080
      - ENVIRONMENT=development
      - MONGO_URL=mongodb://lucid:lucid@lucid-mongo-dev:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis-dev:6379/0
      - JWT_SECRET=dev-jwt-secret-change-in-production
      - LOG_LEVEL=DEBUG
      - DEBUG=true
      - TOR_PROXY_URL=socks5://lucid-tor-dev:9050
    
    ports:
      - "8080:8080"
      - "8081:8081"
    
    volumes:
      - type: bind
        source: ../../03-api-gateway/api
        target: /app
        consistency: cached
      - type: bind
        source: ./configs/api-gateway
        target: /app/config
        read_only: true
    
    networks:
      - lucid-dev-net
    
    depends_on:
      - lucid-mongo-dev
      - lucid-redis-dev
      - lucid-tor-dev
    
    command: ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

  # Additional development services...
  lucid-mongo-dev:
    image: mongo:7.0
    container_name: lucid-mongo-dev
    hostname: mongo-dev
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=lucid
      - MONGO_INITDB_DATABASE=lucid
    
    ports:
      - "27018:27017"
    
    networks:
      - lucid-dev-net
    
    command: ["mongod", "--replSet", "rs0", "--bind_ip_all"]

networks:
  lucid-dev-net:
    name: lucid-dev-net
    driver: bridge
    attachable: true
```

## Environment Configuration

### Production Environment Variables

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

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PUBLIC_REQ_PER_MIN=100
RATE_LIMIT_AUTH_REQ_PER_MIN=1000
RATE_LIMIT_ADMIN_REQ_PER_MIN=10000

# DDoS Protection Configuration
DDOS_PROTECTION_ENABLED=true
DDOS_MAX_REQUESTS_PER_MIN=1000
DDOS_BURST_LIMIT=200

# Tor Configuration
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# Health Check Configuration
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3
```

### Development Environment Variables

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

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PUBLIC_REQ_PER_MIN=10000
RATE_LIMIT_AUTH_REQ_PER_MIN=100000
RATE_LIMIT_ADMIN_REQ_PER_MIN=1000000

# DDoS Protection Configuration
DDOS_PROTECTION_ENABLED=false

# Tor Configuration
TOR_ENABLED=true
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# Health Check Configuration
HEALTH_CHECK_INTERVAL=10
HEALTH_CHECK_TIMEOUT=5
HEALTH_CHECK_RETRIES=1
```

## Health Checks & Monitoring

### Service Health Endpoints

```python
# Health check implementation
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "lucid-api-gateway",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "checks": {
            "database": await check_database_health(),
            "redis": await check_redis_health(),
            "tor": await check_tor_health(),
            "rate_limiter": await check_rate_limiter_health()
        }
    }
    
    # Determine overall health status
    all_healthy = all(
        check["status"] == "healthy" 
        for check in health_status["checks"].values()
    )
    
    if not all_healthy:
        health_status["status"] = "unhealthy"
        return JSONResponse(
            status_code=503,
            content=health_status
        )
    
    return health_status

async def check_database_health():
    """Check MongoDB connection health"""
    try:
        await mongo_client.admin.command('ping')
        return {
            "status": "healthy",
            "response_time_ms": 0,  # TODO: Implement actual timing
            "last_check": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        }

async def check_redis_health():
    """Check Redis connection health"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "response_time_ms": 0,  # TODO: Implement actual timing
            "last_check": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        }
```

### Monitoring Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'lucid-api-gateway'
    static_configs:
      - targets: ['lucid-api-gateway:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'lucid-auth-proxy'
    static_configs:
      - targets: ['lucid-auth-proxy:8082']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'lucid-rate-limiter'
    static_configs:
      - targets: ['lucid-rate-limiter:8083']
    metrics_path: '/metrics'
    scrape_interval: 30s

# Grafana dashboard configuration
# dashboards/api-gateway-dashboard.json
{
  "dashboard": {
    "title": "Lucid API Gateway Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
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
      },
      {
        "title": "Rate Limiting",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(rate_limit_hits_total[5m])",
            "legendFormat": "Rate limit hits"
          }
        ]
      }
    ]
  }
}
```

## Scaling & Performance

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
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
    # Load balancer configuration
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api-gateway.rule=Host(`api.lucid.local`)"
      - "traefik.http.services.api-gateway.loadbalancer.server.port=8080"

  # Load balancer service
  traefik:
    image: traefik:v3.0
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Traefik dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - lucid-api-net
```

### Performance Optimization

```python
# Performance monitoring and optimization
import asyncio
import time
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('http_active_connections', 'Active HTTP connections')

def monitor_performance(func):
    """Decorator to monitor API endpoint performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Increment active connections
        ACTIVE_CONNECTIONS.inc()
        
        try:
            result = await func(*args, **kwargs)
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=200
            ).inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).inc()
            raise
        finally:
            # Record request duration
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            # Decrement active connections
            ACTIVE_CONNECTIONS.dec()
    
    return wrapper

# Connection pooling configuration
DATABASE_POOL_SIZE = 20
REDIS_POOL_SIZE = 50

# Async connection pools
mongo_pool = AsyncIOMotorClient(
    MONGO_URL,
    maxPoolSize=DATABASE_POOL_SIZE,
    minPoolSize=5,
    maxIdleTimeMS=30000,
    serverSelectionTimeoutMS=5000
)

redis_pool = aioredis.ConnectionPool.from_url(
    REDIS_URL,
    max_connections=REDIS_POOL_SIZE,
    retry_on_timeout=True
)
```

## Backup & Recovery

### Database Backup Strategy

```bash
#!/bin/bash
# scripts/backup/mongodb-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_mongo_backup_${DATE}.gz"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Perform backup
echo "Starting MongoDB backup..."
mongodump \
  --host="lucid-mongo:27017" \
  --username="lucid" \
  --password="$MONGO_PASSWORD" \
  --authenticationDatabase="admin" \
  --gzip \
  --archive="$BACKUP_DIR/$BACKUP_FILE"

echo "Backup completed: $BACKUP_DIR/$BACKUP_FILE"

# Verify backup
echo "Verifying backup..."
mongorestore --dryRun \
  --gzip \
  --archive="$BACKUP_DIR/$BACKUP_FILE" \
  --quiet

# Cleanup old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "lucid_mongo_backup_*.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup process completed successfully"

# Upload to cloud storage (optional)
if [ "$CLOUD_BACKUP_ENABLED" = "true" ]; then
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://lucid-backups/mongodb/$BACKUP_FILE"
    echo "Backup uploaded to cloud storage"
fi
```

### Redis Backup Strategy

```bash
#!/bin/bash
# scripts/backup/redis-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_redis_backup_${DATE}.rdb"
RETENTION_DAYS=7

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Perform backup
echo "Starting Redis backup..."
docker exec lucid-redis redis-cli --rdb "/data/$BACKUP_FILE"

# Copy backup from container
docker cp "lucid-redis:/data/$BACKUP_FILE" "$BACKUP_DIR/$BACKUP_FILE"

echo "Backup completed: $BACKUP_DIR/$BACKUP_FILE"

# Cleanup old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "lucid_redis_backup_*.rdb" -mtime +$RETENTION_DAYS -delete

echo "Backup process completed successfully"
```

### Recovery Procedures

```bash
#!/bin/bash
# scripts/recovery/mongodb-restore.sh

set -e

# Configuration
BACKUP_FILE="$1"
MONGO_CONTAINER="lucid-mongo"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 /opt/lucid/backups/mongodb/lucid_mongo_backup_20240101_120000.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Starting MongoDB restore from: $BACKUP_FILE"

# Stop application services to prevent data corruption
echo "Stopping application services..."
docker-compose stop lucid-api-gateway lucid-auth-proxy

# Restore database
echo "Restoring database..."
docker exec -i "$MONGO_CONTAINER" mongorestore \
  --drop \
  --gzip \
  --archive < "$BACKUP_FILE"

# Restart application services
echo "Restarting application services..."
docker-compose start lucid-api-gateway lucid-auth-proxy

echo "MongoDB restore completed successfully"
```

## Troubleshooting Guide

### Common Issues & Solutions

#### 1. Service Startup Failures

**Problem**: API Gateway service fails to start
```bash
# Check service logs
docker logs lucid-api-gateway

# Common causes:
# - Database connection failure
# - Missing environment variables
# - Port conflicts
# - Insufficient resources
```

**Solutions**:
```bash
# Check database connectivity
docker exec lucid-mongo mongosh --eval "db.runCommand({ping: 1})"

# Verify environment variables
docker exec lucid-api-gateway env | grep -E "(MONGO|REDIS|JWT)"

# Check port availability
netstat -tuln | grep -E "(8080|8081|27017|6379)"

# Check resource usage
docker stats lucid-api-gateway
```

#### 2. Database Connection Issues

**Problem**: Cannot connect to MongoDB
```bash
# Check MongoDB status
docker logs lucid-mongo

# Check network connectivity
docker exec lucid-api-gateway ping lucid-mongo

# Check MongoDB replica set status
docker exec lucid-mongo mongosh --eval "rs.status()"
```

**Solutions**:
```bash
# Restart MongoDB service
docker-compose restart lucid-mongo

# Initialize replica set if needed
docker exec lucid-mongo mongosh --eval "rs.initiate()"

# Check authentication
docker exec lucid-mongo mongosh --eval "db.runCommand({connectionStatus: 1})"
```

#### 3. Rate Limiting Issues

**Problem**: Rate limiting not working
```bash
# Check Redis connectivity
docker exec lucid-redis redis-cli ping

# Check rate limiter service
docker logs lucid-rate-limiter

# Verify Redis data
docker exec lucid-redis redis-cli keys "*rate*"
```

**Solutions**:
```bash
# Restart rate limiter service
docker-compose restart lucid-rate-limiter

# Clear rate limit data if needed
docker exec lucid-redis redis-cli flushdb

# Check rate limiter configuration
docker exec lucid-rate-limiter cat /app/config/rate_limit.json
```

#### 4. Tor Connectivity Issues

**Problem**: Tor proxy not working
```bash
# Check Tor service status
docker logs lucid-tor

# Test SOCKS proxy
curl --socks5 localhost:9050 http://check.torproject.org/api/ip

# Check Tor configuration
docker exec lucid-tor cat /etc/tor/torrc
```

**Solutions**:
```bash
# Restart Tor service
docker-compose restart lucid-tor

# Check Tor logs for errors
docker logs lucid-tor | grep -i error

# Verify Tor circuit
docker exec lucid-tor wget -qO- --proxy=on --proxy=socks5://127.0.0.1:9050 http://check.torproject.org/api/ip
```

### Log Analysis

```bash
#!/bin/bash
# scripts/logs/analyze-logs.sh

# Analyze API Gateway logs
echo "=== API Gateway Log Analysis ==="
docker logs lucid-api-gateway --since 1h | grep -E "(ERROR|WARN|CRITICAL)" | tail -20

# Analyze error patterns
echo "=== Error Pattern Analysis ==="
docker logs lucid-api-gateway --since 24h | grep -o "LUCID_ERR_[0-9]*" | sort | uniq -c | sort -nr

# Analyze performance issues
echo "=== Performance Analysis ==="
docker logs lucid-api-gateway --since 1h | grep -E "slow|timeout|duration" | tail -10

# Analyze authentication issues
echo "=== Authentication Issues ==="
docker logs lucid-auth-proxy --since 1h | grep -E "(auth|login|token)" | tail -10
```

### Performance Monitoring

```bash
#!/bin/bash
# scripts/monitoring/performance-check.sh

# Check service response times
echo "=== Service Health Check ==="
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8080/health

# Check database performance
echo "=== Database Performance ==="
docker exec lucid-mongo mongosh --eval "db.runCommand({serverStatus: 1}).metrics.command"

# Check Redis performance
echo "=== Redis Performance ==="
docker exec lucid-redis redis-cli info stats | grep -E "(instantaneous_ops_per_sec|keyspace_hits|keyspace_misses)"

# Check memory usage
echo "=== Memory Usage ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

## Operational Procedures

### Deployment Procedures

```bash
#!/bin/bash
# scripts/deploy/deploy.sh

set -e

# Configuration
ENVIRONMENT="$1"
VERSION="$2"
BACKUP_ENABLED="true"

if [ -z "$ENVIRONMENT" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <environment> <version>"
    echo "Example: $0 production v1.2.3"
    exit 1
fi

echo "Starting deployment to $ENVIRONMENT with version $VERSION"

# Pre-deployment backup
if [ "$BACKUP_ENABLED" = "true" ]; then
    echo "Creating pre-deployment backup..."
    ./scripts/backup/mongodb-backup.sh
    ./scripts/backup/redis-backup.sh
fi

# Pull new images
echo "Pulling new images..."
docker-compose -f docker-compose.$ENVIRONMENT.yml pull

# Deploy with zero-downtime strategy
echo "Deploying with zero-downtime strategy..."

# Update rate limiter first (least critical)
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d --no-deps lucid-rate-limiter

# Wait for rate limiter to be healthy
echo "Waiting for rate limiter to be healthy..."
timeout 60 bash -c 'until docker logs lucid-rate-limiter 2>&1 | grep -q "ready"; do sleep 2; done'

# Update auth proxy
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d --no-deps lucid-auth-proxy

# Wait for auth proxy to be healthy
echo "Waiting for auth proxy to be healthy..."
timeout 60 bash -c 'until docker logs lucid-auth-proxy 2>&1 | grep -q "ready"; do sleep 2; done'

# Update API Gateway (most critical)
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d --no-deps lucid-api-gateway

# Wait for API Gateway to be healthy
echo "Waiting for API Gateway to be healthy..."
timeout 120 bash -c 'until curl -f http://localhost:8080/health; do sleep 5; done'

# Run post-deployment tests
echo "Running post-deployment tests..."
./scripts/testing/post-deployment-tests.sh

echo "Deployment completed successfully!"
```

### Rollback Procedures

```bash
#!/bin/bash
# scripts/deploy/rollback.sh

set -e

ENVIRONMENT="$1"
BACKUP_TIMESTAMP="$2"

if [ -z "$ENVIRONMENT" ] || [ -z "$BACKUP_TIMESTAMP" ]; then
    echo "Usage: $0 <environment> <backup_timestamp>"
    echo "Example: $0 production 20240101_120000"
    exit 1
fi

echo "Starting rollback for $ENVIRONMENT to backup $BACKUP_TIMESTAMP"

# Stop all services
echo "Stopping all services..."
docker-compose -f docker-compose.$ENVIRONMENT.yml down

# Restore database
echo "Restoring database from backup..."
./scripts/recovery/mongodb-restore.sh "/opt/lucid/backups/mongodb/lucid_mongo_backup_${BACKUP_TIMESTAMP}.gz"

# Restore Redis (if available)
if [ -f "/opt/lucid/backups/redis/lucid_redis_backup_${BACKUP_TIMESTAMP}.rdb" ]; then
    echo "Restoring Redis from backup..."
    docker cp "/opt/lucid/backups/redis/lucid_redis_backup_${BACKUP_TIMESTAMP}.rdb" lucid-redis:/data/dump.rdb
fi

# Start services with previous configuration
echo "Starting services..."
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d

# Verify rollback
echo "Verifying rollback..."
timeout 120 bash -c 'until curl -f http://localhost:8080/health; do sleep 5; done'

echo "Rollback completed successfully!"
```

### Maintenance Procedures

```bash
#!/bin/bash
# scripts/maintenance/maintenance.sh

set -e

echo "Starting maintenance procedures..."

# Database maintenance
echo "Running database maintenance..."
docker exec lucid-mongo mongosh --eval "
db.runCommand({compact: 'users'});
db.runCommand({compact: 'sessions'});
db.runCommand({compact: 'manifests'});
"

# Redis maintenance
echo "Running Redis maintenance..."
docker exec lucid-redis redis-cli --rdb /data/maintenance_backup.rdb

# Log rotation
echo "Rotating logs..."
docker exec lucid-api-gateway find /app/logs -name "*.log" -mtime +7 -delete

# Clean up old Docker images
echo "Cleaning up old Docker images..."
docker image prune -f

# Update system packages (if needed)
echo "Checking for system updates..."
docker exec lucid-api-gateway apt-get update && apt-get upgrade -y

echo "Maintenance completed successfully!"
```

## Security Considerations

### Container Security

```dockerfile
# Security-hardened Dockerfile
FROM gcr.io/distroless/python3-debian12:latest

# Create non-root user
USER 65534:65534

# Copy application with proper permissions
COPY --chown=65534:65534 . /app
WORKDIR /app

# Remove unnecessary packages and files
RUN rm -rf /tmp/* /var/tmp/* /var/log/* /var/cache/*

# Set security options
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Use distroless base for minimal attack surface
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/app/health_check.sh"]

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Network Security

```yaml
# Network security configuration
networks:
  lucid-api-net:
    driver: bridge
    internal: false  # Allow external access only through defined ports
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1

# Firewall rules (iptables)
# Allow only necessary ports
iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp --dport 8081 -j ACCEPT
iptables -A INPUT -p tcp --dport 27017 -j DROP  # Block direct MongoDB access
iptables -A INPUT -p tcp --dport 6379 -j DROP   # Block direct Redis access
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

## Monitoring & Alerting

### Prometheus Metrics

```python
# Custom metrics for API Gateway
from prometheus_client import Counter, Histogram, Gauge, Summary

# API Metrics
API_REQUESTS_TOTAL = Counter('lucid_api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
API_REQUEST_DURATION = Histogram('lucid_api_request_duration_seconds', 'API request duration', ['method', 'endpoint'])
API_ACTIVE_CONNECTIONS = Gauge('lucid_api_active_connections', 'Active API connections')

# Authentication Metrics
AUTH_ATTEMPTS_TOTAL = Counter('lucid_auth_attempts_total', 'Total authentication attempts', ['method', 'status'])
AUTH_TOKEN_VALIDATIONS = Counter('lucid_auth_token_validations_total', 'Token validation attempts', ['status'])

# Rate Limiting Metrics
RATE_LIMIT_HITS = Counter('lucid_rate_limit_hits_total', 'Rate limit hits', ['endpoint', 'limit_type'])
RATE_LIMIT_BUCKETS = Gauge('lucid_rate_limit_buckets', 'Rate limit bucket usage', ['endpoint', 'bucket'])

# Database Metrics
DB_CONNECTIONS_ACTIVE = Gauge('lucid_db_connections_active', 'Active database connections')
DB_QUERY_DURATION = Histogram('lucid_db_query_duration_seconds', 'Database query duration', ['collection', 'operation'])

# Redis Metrics
REDIS_CONNECTIONS_ACTIVE = Gauge('lucid_redis_connections_active', 'Active Redis connections')
REDIS_OPERATION_DURATION = Histogram('lucid_redis_operation_duration_seconds', 'Redis operation duration', ['operation'])
```

### Alerting Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: lucid-api-gateway
    rules:
      - alert: APIGatewayDown
        expr: up{job="lucid-api-gateway"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API Gateway is down"
          description: "API Gateway has been down for more than 1 minute"
      
      - alert: HighErrorRate
        expr: rate(lucid_api_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests per second"
      
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(lucid_api_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }} seconds"
      
      - alert: DatabaseConnectionFailure
        expr: lucid_db_connections_active == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "No active database connections"
      
      - alert: RateLimitExceeded
        expr: rate(lucid_rate_limit_hits_total[5m]) > 100
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "High rate limit hits"
          description: "Rate limit hits: {{ $value }} per second"
```

This deployment and operations guide provides comprehensive coverage of all aspects needed to deploy, monitor, and maintain the Lucid API Gateway cluster in production environments, following the distroless container principles and security best practices outlined in the master plan.
