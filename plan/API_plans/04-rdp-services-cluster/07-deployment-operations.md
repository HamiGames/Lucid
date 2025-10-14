# RDP Services Cluster - Deployment & Operations

## Overview
This document provides deployment procedures, operational guidelines, monitoring setup, and troubleshooting strategies for the RDP Services Cluster.

## Docker Compose Configuration

### Development Environment

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  # RDP Server Manager Service
  rdp-server-manager:
    build:
      context: ./services/rdp-server-manager
      dockerfile: Dockerfile
    container_name: rdp-server-manager
    ports:
      - "8090:8090"
    environment:
      - SERVICE_NAME=rdp-server-manager
      - SERVICE_PORT=8090
      - MONGODB_URI=mongodb://mongo:27017/lucid_rdp
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
      - LOG_LEVEL=INFO
      - PROMETHEUS_ENABLED=true
    depends_on:
      - mongo
      - redis
    networks:
      - rdp-cluster
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # XRDP Integration Service
  xrdp-integration:
    build:
      context: ./services/xrdp-integration
      dockerfile: Dockerfile
    container_name: xrdp-integration
    ports:
      - "8091:8091"
    environment:
      - SERVICE_NAME=xrdp-integration
      - SERVICE_PORT=8091
      - MONGODB_URI=mongodb://mongo:27017/lucid_rdp
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
      - XRDP_CONFIG_PATH=/etc/xrdp
      - LOG_LEVEL=INFO
    privileged: true  # Required for XRDP service control
    volumes:
      - /etc/xrdp:/etc/xrdp
      - /var/log/xrdp:/var/log/xrdp
    depends_on:
      - mongo
      - redis
    networks:
      - rdp-cluster
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8091/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Session Controller Service
  rdp-session-controller:
    build:
      context: ./services/rdp-session-controller
      dockerfile: Dockerfile
    container_name: rdp-session-controller
    ports:
      - "8092:8092"
    environment:
      - SERVICE_NAME=rdp-session-controller
      - SERVICE_PORT=8092
      - MONGODB_URI=mongodb://mongo:27017/lucid_rdp
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
      - MAX_CONCURRENT_SESSIONS=100
      - SESSION_TIMEOUT=3600
      - LOG_LEVEL=INFO
    depends_on:
      - mongo
      - redis
    networks:
      - rdp-cluster
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8092/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Resource Monitor Service
  rdp-resource-monitor:
    build:
      context: ./services/rdp-resource-monitor
      dockerfile: Dockerfile
    container_name: rdp-resource-monitor
    ports:
      - "8093:8093"
      - "9090:9090"  # Prometheus metrics
    environment:
      - SERVICE_NAME=rdp-resource-monitor
      - SERVICE_PORT=8093
      - MONGODB_URI=mongodb://mongo:27017/lucid_rdp
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
      - PROMETHEUS_PORT=9090
      - METRICS_INTERVAL=30
      - LOG_LEVEL=INFO
    depends_on:
      - mongo
      - redis
    networks:
      - rdp-cluster
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8093/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # MongoDB Database
  mongo:
    image: mongo:7
    container_name: rdp-mongodb
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db
      - ./scripts/mongo-init.js:/docker-entrypoint-initdb.d/init.js:ro
    environment:
      - MONGO_INITDB_DATABASE=lucid_rdp
    networks:
      - rdp-cluster
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: rdp-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    networks:
      - rdp-cluster
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: rdp-prometheus
    ports:
      - "9091:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - rdp-cluster
    restart: unless-stopped

volumes:
  mongo-data:
  redis-data:
  prometheus-data:

networks:
  rdp-cluster:
    driver: bridge
```

### Environment Configuration

**File**: `.env.example`

```bash
# Service Configuration
JWT_SECRET=your-super-secret-jwt-key-change-in-production
ENVIRONMENT=development

# Database Configuration
MONGODB_URI=mongodb://mongo:27017/lucid_rdp
MONGODB_MAX_POOL_SIZE=50
MONGODB_MIN_POOL_SIZE=10

# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_MAX_CONNECTIONS=50

# Authentication
AUTH_SERVICE_URL=https://auth.lucid-blockchain.org

# Resource Limits
MAX_CONCURRENT_SERVERS=50
MAX_CONCURRENT_SESSIONS=100
MAX_CPU_USAGE=80
MAX_MEMORY_USAGE=80

# XRDP Configuration
XRDP_CONFIG_PATH=/etc/xrdp
XRDP_LOG_PATH=/var/log/xrdp

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Distroless Container Dockerfiles

### RDP Server Manager Dockerfile

**File**: `services/rdp-server-manager/Dockerfile`

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian12:nonroot

# Set labels
LABEL maintainer="Lucid Development Team <dev@lucid-blockchain.org>"
LABEL service="rdp-server-manager"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/nonroot/.local

# Copy application code
COPY --chown=nonroot:nonroot . .

# Set environment variables
ENV PYTHONPATH=/app:/home/nonroot/.local/lib/python3.11/site-packages
ENV PATH=/home/nonroot/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=rdp-server-manager
ENV SERVICE_PORT=8090

# Expose port
EXPOSE 8090

# Run as non-root user
USER nonroot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8090/health')"]

# Run the application
ENTRYPOINT ["python", "-m", "services.rdp_server_manager.main"]
```

## Health Check Endpoints

### Health Check Implementation

**File**: `shared/monitoring/health_checks.py`

```python
from fastapi import APIRouter, status
from typing import Dict
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from redis import asyncio as aioredis

router = APIRouter()

async def check_mongodb(uri: str) -> Dict:
    """Check MongoDB connection"""
    try:
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        client.close()
        return {"status": "healthy", "message": "MongoDB is accessible"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"MongoDB error: {str(e)}"}

async def check_redis(url: str) -> Dict:
    """Check Redis connection"""
    try:
        redis = aioredis.from_url(url, socket_timeout=5)
        await redis.ping()
        await redis.close()
        return {"status": "healthy", "message": "Redis is accessible"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Redis error: {str(e)}"}

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "rdp-services-cluster",
        "version": "1.0.0"
    }

@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check(mongodb_uri: str, redis_url: str):
    """Readiness check with dependency validation"""
    
    # Check all dependencies
    mongo_status = await check_mongodb(mongodb_uri)
    redis_status = await check_redis(redis_url)
    
    # Determine overall status
    is_ready = (
        mongo_status["status"] == "healthy" and
        redis_status["status"] == "healthy"
    )
    
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "ready": is_ready,
        "checks": {
            "mongodb": mongo_status,
            "redis": redis_status,
        }
    }

@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Liveness check endpoint"""
    return {
        "alive": True,
        "timestamp": asyncio.get_event_loop().time()
    }
```

## Prometheus Metrics

### Prometheus Configuration

**File**: `config/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'rdp-services'
    environment: 'production'

scrape_configs:
  - job_name: 'rdp-server-manager'
    static_configs:
      - targets: ['rdp-server-manager:9090']
        labels:
          service: 'rdp-server-manager'
  
  - job_name: 'xrdp-integration'
    static_configs:
      - targets: ['xrdp-integration:9090']
        labels:
          service: 'xrdp-integration'
  
  - job_name: 'rdp-session-controller'
    static_configs:
      - targets: ['rdp-session-controller:9090']
        labels:
          service: 'rdp-session-controller'
  
  - job_name: 'rdp-resource-monitor'
    static_configs:
      - targets: ['rdp-resource-monitor:9090']
        labels:
          service: 'rdp-resource-monitor'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/alerts/*.yml'
```

### Custom Metrics Implementation

**File**: `shared/monitoring/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# Request metrics
request_count = Counter(
    'rdp_requests_total',
    'Total number of requests',
    ['service', 'endpoint', 'method', 'status']
)

request_duration = Histogram(
    'rdp_request_duration_seconds',
    'Request duration in seconds',
    ['service', 'endpoint', 'method']
)

# RDP Server metrics
rdp_servers_total = Gauge(
    'rdp_servers_total',
    'Total number of RDP servers',
    ['status']
)

rdp_servers_created = Counter(
    'rdp_servers_created_total',
    'Total number of RDP servers created'
)

rdp_servers_deleted = Counter(
    'rdp_servers_deleted_total',
    'Total number of RDP servers deleted'
)

# Session metrics
rdp_sessions_total = Gauge(
    'rdp_sessions_total',
    'Total number of active RDP sessions',
    ['status']
)

rdp_sessions_created = Counter(
    'rdp_sessions_created_total',
    'Total number of RDP sessions created'
)

rdp_sessions_terminated = Counter(
    'rdp_sessions_terminated_total',
    'Total number of RDP sessions terminated'
)

# Resource metrics
rdp_cpu_usage = Gauge(
    'rdp_cpu_usage_percent',
    'CPU usage percentage',
    ['server_id']
)

rdp_memory_usage = Gauge(
    'rdp_memory_usage_percent',
    'Memory usage percentage',
    ['server_id']
)

rdp_network_in = Gauge(
    'rdp_network_in_kbps',
    'Network input in KB/s',
    ['server_id']
)

rdp_network_out = Gauge(
    'rdp_network_out_kbps',
    'Network output in KB/s',
    ['server_id']
)

def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

## Deployment Procedures

### Initial Deployment

**File**: `scripts/deploy.sh`

```bash
#!/bin/bash
set -e

echo "========================================="
echo "RDP Services Cluster Deployment"
echo "========================================="

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "Error: .env file not found"
    exit 1
fi

# Validate required environment variables
REQUIRED_VARS=("JWT_SECRET" "MONGODB_URI" "REDIS_URL")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set"
        exit 1
    fi
done

# Build containers
echo "Building Docker containers..."
docker-compose build

# Start database services first
echo "Starting database services..."
docker-compose up -d mongo redis

# Wait for databases to be ready
echo "Waiting for MongoDB..."
until docker exec rdp-mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; do
    sleep 2
done

echo "Waiting for Redis..."
until docker exec rdp-redis redis-cli ping > /dev/null 2>&1; do
    sleep 2
done

# Run database migrations
echo "Running database migrations..."
docker-compose run --rm rdp-server-manager python -m alembic upgrade head

# Start all services
echo "Starting all services..."
docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check health status
services=("rdp-server-manager:8090" "xrdp-integration:8091" "rdp-session-controller:8092" "rdp-resource-monitor:8093")
for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    echo "Checking $name..."
    
    max_retries=30
    retry=0
    until curl -f "http://localhost:$port/health" > /dev/null 2>&1; do
        retry=$((retry + 1))
        if [ $retry -ge $max_retries ]; then
            echo "Error: $name failed to start"
            docker-compose logs $name
            exit 1
        fi
        sleep 2
    done
    echo "$name is healthy"
done

echo "========================================="
echo "Deployment completed successfully!"
echo "========================================="
echo ""
echo "Services:"
echo "  - RDP Server Manager: http://localhost:8090"
echo "  - XRDP Integration: http://localhost:8091"
echo "  - Session Controller: http://localhost:8092"
echo "  - Resource Monitor: http://localhost:8093"
echo "  - Prometheus: http://localhost:9091"
echo ""
```

### Rolling Update

**File**: `scripts/rolling-update.sh`

```bash
#!/bin/bash
set -e

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "Usage: ./rolling-update.sh <service-name>"
    exit 1
fi

echo "Performing rolling update for $SERVICE..."

# Pull latest image
docker-compose pull $SERVICE

# Update service with zero downtime
docker-compose up -d --no-deps --scale $SERVICE=2 $SERVICE

# Wait for new container to be healthy
sleep 15

# Check health
if curl -f "http://localhost:$(docker-compose port $SERVICE | cut -d: -f2)/health"; then
    echo "New container is healthy, removing old container"
    docker-compose up -d --no-deps --scale $SERVICE=1 --remove-orphans $SERVICE
    echo "Rolling update completed successfully"
else
    echo "New container failed health check, rolling back"
    docker-compose up -d --no-deps --scale $SERVICE=1 $SERVICE
    exit 1
fi
```

## Service Dependencies

### Startup Order

```yaml
# Dependency graph
MongoDB → Redis → [All Services]
                ↓
         RDP Server Manager
                ↓
         XRDP Integration
                ↓
         Session Controller
                ↓
         Resource Monitor
```

### Dependency Management

```python
# Wait for dependencies before starting
async def wait_for_dependencies():
    """Wait for all dependencies to be ready"""
    import asyncio
    
    dependencies = [
        ("MongoDB", check_mongodb),
        ("Redis", check_redis),
    ]
    
    for name, check_func in dependencies:
        max_retries = 30
        for attempt in range(max_retries):
            try:
                result = await check_func()
                if result["status"] == "healthy":
                    logger.info(f"{name} is ready")
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to connect to {name}: {e}")
                await asyncio.sleep(2)
```

## Troubleshooting

### Common Issues

#### 1. XRDP Service Failures

**Symptoms:**
- XRDP service fails to start
- Connection refused errors
- Port conflicts

**Diagnostics:**
```bash
# Check XRDP service status
docker exec xrdp-integration systemctl status xrdp

# Check XRDP logs
docker exec xrdp-integration cat /var/log/xrdp/xrdp.log

# Check port availability
docker exec xrdp-integration netstat -tuln | grep 3389
```

**Solutions:**
```bash
# Restart XRDP service
docker exec xrdp-integration systemctl restart xrdp

# Check configuration
docker exec xrdp-integration cat /etc/xrdp/xrdp.ini

# Verify SSL certificates
docker exec xrdp-integration ls -l /etc/ssl/certs/xrdp.crt
```

#### 2. Port Conflicts

**Symptoms:**
- Service fails to bind to port
- Address already in use errors

**Diagnostics:**
```bash
# Find process using port
lsof -i :8090
netstat -tuln | grep 8090

# Check Docker port bindings
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

**Solutions:**
```bash
# Kill process using port
kill -9 $(lsof -t -i:8090)

# Use different port
# Update docker-compose.yml port mapping
```

#### 3. Database Connection Failures

**Symptoms:**
- Services can't connect to MongoDB
- Connection timeout errors

**Diagnostics:**
```bash
# Check MongoDB status
docker exec rdp-mongodb mongosh --eval "db.adminCommand('ping')"

# Check network connectivity
docker exec rdp-server-manager ping mongo

# Check MongoDB logs
docker logs rdp-mongodb
```

**Solutions:**
```bash
# Restart MongoDB
docker-compose restart mongo

# Check connection string
echo $MONGODB_URI

# Verify network
docker network inspect rdp-cluster_rdp-cluster
```

#### 4. High Resource Usage

**Symptoms:**
- Slow API responses
- High CPU/memory usage
- Resource alerts

**Diagnostics:**
```bash
# Check container resource usage
docker stats

# Check specific service
docker stats rdp-server-manager

# View resource metrics
curl http://localhost:8093/api/v1/resources/usage
```

**Solutions:**
```bash
# Scale up resources
# Update docker-compose.yml resource limits

# Restart high-usage service
docker-compose restart <service-name>

# Check for memory leaks
docker exec <service> ps aux --sort=-%mem
```

### Logging

#### Centralized Logging

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f rdp-server-manager

# Filter logs by level
docker-compose logs | grep ERROR

# Export logs
docker-compose logs > deployment-logs.txt
```

#### Log Rotation

**File**: `/etc/docker/daemon.json`

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## Backup & Restore

### Database Backup

**File**: `scripts/backup.sh`

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups/rdp-services"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/mongodb_backup_$TIMESTAMP.gz"

echo "Starting MongoDB backup..."

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform backup
docker exec rdp-mongodb mongodump \
    --db=lucid_rdp \
    --archive=/tmp/backup.gz \
    --gzip

# Copy backup from container
docker cp rdp-mongodb:/tmp/backup.gz $BACKUP_FILE

# Clean up old backups (keep last 7 days)
find $BACKUP_DIR -name "mongodb_backup_*.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

### Database Restore

**File**: `scripts/restore.sh`

```bash
#!/bin/bash
set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup-file>"
    exit 1
fi

echo "Restoring MongoDB from $BACKUP_FILE..."

# Copy backup to container
docker cp $BACKUP_FILE rdp-mongodb:/tmp/restore.gz

# Restore backup
docker exec rdp-mongodb mongorestore \
    --archive=/tmp/restore.gz \
    --gzip \
    --drop

echo "Restore completed successfully"
```

## Monitoring Dashboard

### Grafana Dashboard Configuration

**File**: `config/grafana-dashboard.json`

```json
{
  "dashboard": {
    "title": "RDP Services Cluster",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(rdp_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Active Sessions",
        "targets": [
          {
            "expr": "rdp_sessions_total{status='active'}"
          }
        ]
      },
      {
        "title": "CPU Usage",
        "targets": [
          {
            "expr": "rdp_cpu_usage_percent"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "targets": [
          {
            "expr": "rdp_memory_usage_percent"
          }
        ]
      }
    ]
  }
}
```

## Maintenance

### Regular Maintenance Tasks

| Task | Frequency | Command |
|------|-----------|---------|
| Database backup | Daily | `./scripts/backup.sh` |
| Log rotation | Daily | Automatic |
| Security updates | Weekly | `docker-compose pull && docker-compose up -d` |
| Resource cleanup | Weekly | `docker system prune -a` |
| Health check | Continuous | Automatic |
| Performance review | Monthly | Manual |

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10

