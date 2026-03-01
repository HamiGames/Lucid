# Blockchain Core Cluster - Deployment & Operations

## Overview

Deployment and operations guide for the Lucid blockchain core cluster (lucid_blocks), covering Docker containerization, health checks, monitoring, troubleshooting, and operational procedures. This document ensures reliable deployment and maintenance of the blockchain core system while enforcing TRON isolation.

## Deployment Architecture

### Container Strategy

**Distroless Container Base:**
```yaml
# infrastructure/docker/multi-stage/Dockerfile.blockchain
FROM gcr.io/distroless/python3-debian11:latest

# Copy application code
COPY --from=builder /app/blockchain /app/blockchain
COPY --from=builder /app/requirements.txt /app/requirements.txt

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8084

# Set environment variables
ENV SERVICE_NAME="lucid-blocks"
ENV PORT=8084
ENV PYTHONPATH="/app"
ENV LUCID_ENV="production"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD ["python3", "-c", "import requests; requests.get('http://localhost:8084/health')"]

# Run application
ENTRYPOINT ["python3", "-m", "blockchain.api.main"]
```

**Multi-Stage Build:**
```yaml
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY blockchain/ ./blockchain/

# Production stage
FROM gcr.io/distroless/python3-debian11:latest

# Copy application from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/blockchain /app/blockchain

WORKDIR /app
EXPOSE 8084
ENV SERVICE_NAME="lucid-blocks"
ENV PORT=8084

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD ["python3", "-c", "import requests; requests.get('http://localhost:8084/health')"]

ENTRYPOINT ["python3", "-m", "blockchain.api.main"]
```

### Docker Compose Configuration

**Production Deployment:**
```yaml
# docker-compose.blockchain.yml
version: '3.8'

services:
  lucid-blocks:
    image: ghcr.io/hamigames/lucid/blockchain:latest
    container_name: lucid-blocks
    hostname: lucid-blocks
    
    environment:
      - LUCID_ENV=production
      - SERVICE_NAME=lucid-blocks
      - PORT=8084
      - MONGO_URL=mongodb://lucid:${MONGO_PASSWORD}@lucid-mongo:27017/lucid?authSource=admin
      - REDIS_URL=redis://lucid-redis:6379/0
      - TOR_PROXY_URL=socks5://lucid-tor:9050
      - LOG_LEVEL=INFO
      - METRICS_ENABLED=true
    
    ports:
      - "8084:8084"
    
    volumes:
      - blockchain_data:/app/data
      - blockchain_logs:/app/logs
      - /etc/localtime:/etc/localtime:ro
    
    networks:
      - lucid_network
    
    depends_on:
      - lucid-mongo
      - lucid-redis
      - lucid-tor
    
    restart: unless-stopped
    
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
    healthcheck:
      test: ["CMD", "python3", "-c", "import requests; requests.get('http://localhost:8084/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  lucid-mongo:
    image: mongo:7.0
    container_name: lucid-mongo
    hostname: lucid-mongo
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid
    
    volumes:
      - mongo_data:/data/db
      - ./scripts/database/init_mongodb_schema.js:/docker-entrypoint-initdb.d/init_schema.js:ro
    
    networks:
      - lucid_network
    
    restart: unless-stopped
    
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  lucid-redis:
    image: redis:7-alpine
    container_name: lucid-redis
    hostname: lucid-redis
    
    volumes:
      - redis_data:/data
    
    networks:
      - lucid_network
    
    restart: unless-stopped
    
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'

  lucid-tor:
    image: alpine:3.18
    container_name: lucid-tor
    hostname: lucid-tor
    
    volumes:
      - ./configs/tor/torrc.prod:/etc/tor/torrc:ro
    
    ports:
      - "9050:9050"
      - "9051:9051"
    
    networks:
      - lucid_network
    
    command: ["sh", "-c", "apk add --no-cache tor && tor -f /etc/tor/torrc"]
    
    restart: unless-stopped

volumes:
  blockchain_data:
    driver: local
  blockchain_logs:
    driver: local
  mongo_data:
    driver: local
  redis_data:
    driver: local

networks:
  lucid_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Health Checks & Monitoring

### Health Check Endpoints

**Application Health Checks:**
```python
# blockchain/api/health.py
from fastapi import APIRouter, HTTPException
from blockchain.core.blockchain_engine import BlockchainEngine
from database.mongodb_volume import MongoDBVolume
import redis
import asyncio

router = APIRouter()

class HealthChecker:
    def __init__(self):
        self.blockchain_engine = BlockchainEngine()
        self.mongodb = MongoDBVolume()
        self.redis_client = redis.Redis(host='lucid-redis', port=6379, db=0)
    
    async def check_blockchain_health(self):
        """Check blockchain engine health"""
        try:
            # Test block creation
            test_block = self.blockchain_engine.create_block([])
            return {"status": "healthy", "last_block": test_block.hash}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Blockchain engine unhealthy: {str(e)}")
    
    async def check_database_health(self):
        """Check database connectivity"""
        try:
            # Test database connection
            result = await self.mongodb.ping()
            return {"status": "healthy", "response_time": result["response_time"]}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")
    
    async def check_redis_health(self):
        """Check Redis connectivity"""
        try:
            # Test Redis connection
            self.redis_client.ping()
            return {"status": "healthy"}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Redis unhealthy: {str(e)}")
    
    async def check_dependencies(self):
        """Check all external dependencies"""
        checks = {
            "blockchain": await self.check_blockchain_health(),
            "database": await self.check_database_health(),
            "redis": await self.check_redis_health()
        }
        
        return {
            "status": "healthy",
            "checks": checks,
            "timestamp": datetime.datetime.now().isoformat()
        }

health_checker = HealthChecker()

@router.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    return await health_checker.check_dependencies()

@router.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        await health_checker.check_dependencies()
        return {"status": "ready"}
    except HTTPException as e:
        raise e

@router.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe"""
    try:
        await health_checker.check_blockchain_health()
        return {"status": "alive"}
    except HTTPException as e:
        raise e
```

### Monitoring Configuration

**Prometheus Metrics:**
```python
# blockchain/api/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import APIRouter, Response

router = APIRouter()

# Metrics definitions
REQUEST_COUNT = Counter('blockchain_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('blockchain_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
ACTIVE_CONNECTIONS = Gauge('blockchain_active_connections', 'Active connections')
BLOCK_HEIGHT = Gauge('blockchain_block_height', 'Current block height')
TRANSACTION_COUNT = Counter('blockchain_transactions_total', 'Total transactions')
WALLET_COUNT = Gauge('blockchain_wallets_total', 'Total wallets')
CONTRACT_COUNT = Gauge('blockchain_contracts_total', 'Total contracts')

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

# Middleware for metrics collection
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```

**Grafana Dashboard Configuration:**
```yaml
# monitoring/grafana/dashboards/blockchain-dashboard.json
{
  "dashboard": {
    "title": "Lucid Blockchain Core",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(blockchain_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(blockchain_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Block Height",
        "type": "singlestat",
        "targets": [
          {
            "expr": "blockchain_block_height",
            "legendFormat": "Current Height"
          }
        ]
      },
      {
        "title": "Active Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "blockchain_active_connections",
            "legendFormat": "Active"
          }
        ]
      }
    ]
  }
}
```

## Logging Configuration

### Structured Logging

**Logging Setup:**
```python
# blockchain/api/logging.py
import logging
import json
import datetime
from pathlib import Path

class StructuredLogger:
    def __init__(self, name, log_file=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_request(self, request_id, method, endpoint, status_code, duration):
        """Log HTTP request"""
        log_entry = {
            "event": "http_request",
            "request_id": request_id,
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": duration * 1000,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_blockchain_event(self, event_type, block_hash=None, transaction_hash=None, **kwargs):
        """Log blockchain-specific events"""
        log_entry = {
            "event": f"blockchain_{event_type}",
            "timestamp": datetime.datetime.now().isoformat(),
            **kwargs
        }
        
        if block_hash:
            log_entry["block_hash"] = block_hash
        if transaction_hash:
            log_entry["transaction_hash"] = transaction_hash
        
        self.logger.info(json.dumps(log_entry))
    
    def log_error(self, error_type, error_message, **context):
        """Log error events"""
        log_entry = {
            "event": "error",
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.datetime.now().isoformat(),
            **context
        }
        self.logger.error(json.dumps(log_entry))

# Global logger instance
logger = StructuredLogger("lucid-blocks", "/app/logs/blockchain.log")
```

### Log Rotation

**Logrotate Configuration:**
```yaml
# /etc/logrotate.d/lucid-blocks
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 lucid lucid
    postrotate
        # Reload application to reopen log files
        docker exec lucid-blocks pkill -HUP python3
    endscript
}
```

## Deployment Procedures

### Production Deployment

**Deployment Script:**
```bash
#!/bin/bash
# scripts/deploy/blockchain-deploy.sh

set -e

# Configuration
REGISTRY="ghcr.io/hamigames/lucid"
SERVICE="blockchain"
VERSION="${1:-latest}"
ENVIRONMENT="${2:-production}"

echo "Deploying Lucid Blockchain Core v${VERSION} to ${ENVIRONMENT}"

# Pre-deployment checks
echo "Running pre-deployment checks..."
docker-compose -f docker-compose.blockchain.yml config > /dev/null
echo "✓ Docker Compose configuration valid"

# Backup current deployment
echo "Creating backup..."
BACKUP_DIR="/opt/lucid/backups/blockchain-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
docker-compose -f docker-compose.blockchain.yml down
echo "✓ Backup created at $BACKUP_DIR"

# Pull new images
echo "Pulling new images..."
docker-compose -f docker-compose.blockchain.yml pull
echo "✓ Images pulled successfully"

# Start services
echo "Starting services..."
docker-compose -f docker-compose.blockchain.yml up -d
echo "✓ Services started"

# Wait for health checks
echo "Waiting for health checks..."
for i in {1..30}; do
    if curl -f http://localhost:8084/health > /dev/null 2>&1; then
        echo "✓ Health check passed"
        break
    fi
    echo "Waiting for health check... ($i/30)"
    sleep 10
done

# Post-deployment validation
echo "Running post-deployment validation..."
python3 scripts/validate/blockchain-validation.py
echo "✓ Validation passed"

echo "Deployment completed successfully!"
```

**Rollback Procedure:**
```bash
#!/bin/bash
# scripts/deploy/blockchain-rollback.sh

set -e

echo "Rolling back Lucid Blockchain Core deployment..."

# Find latest backup
LATEST_BACKUP=$(ls -t /opt/lucid/backups/ | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "No backup found for rollback"
    exit 1
fi

echo "Rolling back to: $LATEST_BACKUP"

# Stop current services
echo "Stopping current services..."
docker-compose -f docker-compose.blockchain.yml down

# Restore from backup
echo "Restoring from backup..."
cp -r "/opt/lucid/backups/$LATEST_BACKUP"/* /opt/lucid/current/

# Start services with previous configuration
echo "Starting services with previous configuration..."
docker-compose -f docker-compose.blockchain.yml up -d

# Wait for health checks
echo "Waiting for health checks..."
for i in {1..30}; do
    if curl -f http://localhost:8084/health > /dev/null 2>&1; then
        echo "✓ Rollback completed successfully"
        break
    fi
    echo "Waiting for health check... ($i/30)"
    sleep 10
done

echo "Rollback completed!"
```

### Kubernetes Deployment

**Kubernetes Manifests:**
```yaml
# k8s/blockchain-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lucid-blocks
  namespace: lucid
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lucid-blocks
  template:
    metadata:
      labels:
        app: lucid-blocks
    spec:
      containers:
      - name: blockchain
        image: ghcr.io/hamigames/lucid/blockchain:latest
        ports:
        - containerPort: 8084
        env:
        - name: LUCID_ENV
          value: "production"
        - name: SERVICE_NAME
          value: "lucid-blocks"
        - name: PORT
          value: "8084"
        - name: MONGO_URL
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: mongo-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health/liveness
            port: 8084
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 8084
          initialDelaySeconds: 10
          periodSeconds: 10
        volumeMounts:
        - name: blockchain-data
          mountPath: /app/data
        - name: blockchain-logs
          mountPath: /app/logs
      volumes:
      - name: blockchain-data
        persistentVolumeClaim:
          claimName: blockchain-data-pvc
      - name: blockchain-logs
        persistentVolumeClaim:
          claimName: blockchain-logs-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: lucid-blocks-service
  namespace: lucid
spec:
  selector:
    app: lucid-blocks
  ports:
  - port: 8084
    targetPort: 8084
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: blockchain-data-pvc
  namespace: lucid
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: blockchain-logs-pvc
  namespace: lucid
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

## Troubleshooting

### Common Issues

**Service Won't Start:**
```bash
# Check container logs
docker logs lucid-blocks

# Check container status
docker ps -a | grep lucid-blocks

# Check resource usage
docker stats lucid-blocks

# Check network connectivity
docker exec lucid-blocks ping lucid-mongo
docker exec lucid-blocks ping lucid-redis
```

**Database Connection Issues:**
```bash
# Test MongoDB connection
docker exec lucid-blocks python3 -c "
from database.mongodb_volume import MongoDBVolume
db = MongoDBVolume()
print(db.test_connection())
"

# Check MongoDB logs
docker logs lucid-mongo

# Verify MongoDB is running
docker exec lucid-mongo mongosh --eval "db.runCommand('ping')"
```

**Performance Issues:**
```bash
# Check system resources
docker stats lucid-blocks

# Check application metrics
curl http://localhost:8084/metrics

# Check database performance
docker exec lucid-mongo mongosh --eval "
db.runCommand({collStats: 'blocks'})
db.runCommand({collStats: 'transactions'})
"
```

### Diagnostic Tools

**Health Check Script:**
```bash
#!/bin/bash
# scripts/diagnostics/blockchain-health.sh

echo "Lucid Blockchain Core Health Check"
echo "=================================="

# Check container status
echo "Container Status:"
docker ps | grep lucid-blocks

# Check health endpoint
echo -e "\nHealth Endpoint:"
curl -s http://localhost:8084/health | jq .

# Check metrics
echo -e "\nMetrics:"
curl -s http://localhost:8084/metrics | grep blockchain_

# Check logs for errors
echo -e "\nRecent Errors:"
docker logs lucid-blocks --tail 50 | grep ERROR

# Check database connectivity
echo -e "\nDatabase Connectivity:"
docker exec lucid-blocks python3 -c "
from database.mongodb_volume import MongoDBVolume
db = MongoDBVolume()
try:
    result = db.ping()
    print('✓ Database connection healthy')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
"

echo -e "\nHealth check completed"
```

**Performance Monitoring Script:**
```bash
#!/bin/bash
# scripts/diagnostics/blockchain-performance.sh

echo "Lucid Blockchain Core Performance Check"
echo "======================================="

# Check response times
echo "API Response Times:"
for endpoint in "/health" "/api/v1/chain/info" "/api/v1/chain/height"; do
    echo -n "  $endpoint: "
    curl -w "%{time_total}s\n" -o /dev/null -s "http://localhost:8084$endpoint"
done

# Check resource usage
echo -e "\nResource Usage:"
docker stats lucid-blocks --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check database performance
echo -e "\nDatabase Performance:"
docker exec lucid-mongo mongosh --eval "
print('Database Stats:');
print(JSON.stringify(db.runCommand({dbStats: 1}), null, 2));
print('Collection Stats:');
print('Blocks:', JSON.stringify(db.runCommand({collStats: 'blocks'}), null, 2));
print('Transactions:', JSON.stringify(db.runCommand({collStats: 'transactions'}), null, 2));
"

echo -e "\nPerformance check completed"
```

## Backup & Recovery

### Backup Procedures

**Automated Backup Script:**
```bash
#!/bin/bash
# scripts/backup/blockchain-backup.sh

BACKUP_DIR="/opt/lucid/backups/blockchain-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Starting blockchain backup to $BACKUP_DIR"

# Backup database
echo "Backing up database..."
docker exec lucid-mongo mongodump --out /tmp/backup
docker cp lucid-mongo:/tmp/backup "$BACKUP_DIR/database"

# Backup application data
echo "Backing up application data..."
docker cp lucid-blocks:/app/data "$BACKUP_DIR/app-data"

# Backup configuration
echo "Backing up configuration..."
cp docker-compose.blockchain.yml "$BACKUP_DIR/"

# Create backup manifest
cat > "$BACKUP_DIR/backup-manifest.json" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "service": "lucid-blocks",
  "version": "$(docker inspect lucid-blocks --format='{{.Config.Labels.version}}')",
  "backup_type": "full",
  "components": [
    "database",
    "application_data",
    "configuration"
  ]
}
EOF

# Compress backup
echo "Compressing backup..."
tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" .
rm -rf "$BACKUP_DIR"

echo "Backup completed: $BACKUP_DIR.tar.gz"
```

### Recovery Procedures

**Recovery Script:**
```bash
#!/bin/bash
# scripts/recovery/blockchain-recovery.sh

BACKUP_FILE="$1"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    exit 1
fi

echo "Starting blockchain recovery from $BACKUP_FILE"

# Extract backup
BACKUP_DIR="/tmp/blockchain-recovery-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
tar -xzf "$BACKUP_FILE" -C "$BACKUP_DIR"

# Stop services
echo "Stopping services..."
docker-compose -f docker-compose.blockchain.yml down

# Restore database
echo "Restoring database..."
docker-compose -f docker-compose.blockchain.yml up -d lucid-mongo
sleep 10
docker exec lucid-mongo mongorestore /tmp/backup

# Restore application data
echo "Restoring application data..."
docker cp "$BACKUP_DIR/app-data" lucid-blocks:/app/data

# Start services
echo "Starting services..."
docker-compose -f docker-compose.blockchain.yml up -d

# Verify recovery
echo "Verifying recovery..."
sleep 30
curl -f http://localhost:8084/health > /dev/null && echo "✓ Recovery successful" || echo "✗ Recovery failed"

# Cleanup
rm -rf "$BACKUP_DIR"

echo "Recovery completed"
```

This deployment and operations document ensures reliable deployment, monitoring, and maintenance of the blockchain core cluster while maintaining TRON isolation and operational excellence.
