# 06. Deployment and Operations

## Overview

This document provides comprehensive deployment and operational guidance for the Session Management Cluster, including containerization, orchestration, monitoring, troubleshooting, and disaster recovery procedures.

## Deployment Architecture

### Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Session Management Cluster                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐        │
│  │ Session API │  │   Pipeline   │  │   Session   │        │
│  │   (8087)    │  │   Manager    │  │  Recorder   │        │
│  │             │  │   (8083)     │  │   (8084)    │        │
│  └─────────────┘  └──────────────┘  └─────────────┘        │
│         │                │                   │               │
│         └────────────────┼───────────────────┘               │
│                          │                                   │
│  ┌─────────────┐  ┌──────────────┐                         │
│  │   Chunk     │  │   Session    │                         │
│  │  Processor  │  │   Storage    │                         │
│  │   (8085)    │  │   (8086)     │                         │
│  └─────────────┘  └──────────────┘                         │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                    Supporting Services                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐        │
│  │   MongoDB   │  │    Redis     │  │   Storage   │        │
│  │   (27017)   │  │   (6379)     │  │  Volumes    │        │
│  └─────────────┘  └──────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Service Dependencies

- **Session API** → MongoDB, Redis, Pipeline Manager, Session Recorder
- **Pipeline Manager** → Session Recorder, Chunk Processor, Session Storage
- **Session Recorder** → RDP Services, Chunk Processor
- **Chunk Processor** → Session Storage, Blockchain Core (for anchoring)
- **Session Storage** → MongoDB, Local File System

## Docker Configuration

### Distroless Base Images

All containers MUST use Google's distroless Python images for security:

```dockerfile
# Base image for all services
FROM gcr.io/distroless/python3-debian11:latest
```

### Multi-Stage Dockerfile Examples

#### Session API Service Dockerfile

```dockerfile
# sessions/api/Dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian11:latest

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Set Python path
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY --chown=nonroot:nonroot ./app /app

# Set working directory
WORKDIR /app

# Use non-root user
USER nonroot

# Expose port
EXPOSE 8087

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8087/health')"]

# Run application
ENTRYPOINT ["/usr/bin/python3", "-m", "uvicorn"]
CMD ["app.api.session_api:app", "--host", "0.0.0.0", "--port", "8087"]
```

#### Pipeline Manager Dockerfile

```dockerfile
# sessions/pipeline/Dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian11:latest

# Copy Python dependencies
COPY --from=builder /root/.local /root/.local

# Set Python path
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY --chown=nonroot:nonroot ./app /app

WORKDIR /app

# Use non-root user
USER nonroot

# Expose port
EXPOSE 8083

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8083/health')"]

# Run application
ENTRYPOINT ["/usr/bin/python3", "-m"]
CMD ["app.pipeline.pipeline_manager"]
```

#### Session Recorder Dockerfile

```dockerfile
# sessions/recorder/Dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies (including RDP libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libfreerdp-dev \
    libavcodec-dev \
    libavformat-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime (Distroless with additional libraries)
FROM gcr.io/distroless/python3-debian11:latest

# Copy Python dependencies
COPY --from=builder /root/.local /root/.local

# Copy required system libraries for RDP
COPY --from=builder /usr/lib/x86_64-linux-gnu/libfreerdp* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libavcodec* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libavformat* /usr/lib/x86_64-linux-gnu/

# Set Python path
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY --chown=nonroot:nonroot ./app /app

WORKDIR /app

# Use non-root user
USER nonroot

# Expose port
EXPOSE 8084

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8084/health')"]

# Run application
ENTRYPOINT ["/usr/bin/python3", "-m"]
CMD ["app.recorder.session_recorder"]
```

#### Chunk Processor Dockerfile

```dockerfile
# sessions/processor/Dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libzstd-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian11:latest

# Copy Python dependencies
COPY --from=builder /root/.local /root/.local

# Copy required system libraries
COPY --from=builder /usr/lib/x86_64-linux-gnu/libzstd* /usr/lib/x86_64-linux-gnu/

# Set Python path
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY --chown=nonroot:nonroot ./app /app

WORKDIR /app

# Use non-root user
USER nonroot

# Expose port
EXPOSE 8085

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8085/health')"]

# Run application
ENTRYPOINT ["/usr/bin/python3", "-m"]
CMD ["app.processor.chunk_processor"]
```

#### Session Storage Dockerfile

```dockerfile
# sessions/storage/Dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime (Distroless)
FROM gcr.io/distroless/python3-debian11:latest

# Copy Python dependencies
COPY --from=builder /root/.local /root/.local

# Set Python path
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY --chown=nonroot:nonroot ./app /app

WORKDIR /app

# Use non-root user
USER nonroot

# Expose port
EXPOSE 8086

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8086/health')"]

# Run application
ENTRYPOINT ["/usr/bin/python3", "-m"]
CMD ["app.storage.session_storage"]
```

### Security Hardening

#### Container Security Best Practices

1. **Non-root User**: All containers run as `nonroot` user (UID 65532)
2. **Read-only Root Filesystem**: Enable where possible
3. **No Shell Access**: Distroless images have no shell
4. **Minimal Attack Surface**: Only required libraries included
5. **Security Scanning**: Scan images with Trivy/Grype

#### Docker Security Configuration

```yaml
# Example security configuration in docker-compose
services:
  session-api:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

## Docker Compose Setup

### Complete Docker Compose Configuration

```yaml
# sessions/docker-compose.yml
version: '3.8'

services:
  # MongoDB Database
  mongodb:
    image: mongo:6.0
    container_name: lucid-session-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_ROOT_USERNAME}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_ROOT_PASSWORD}
      MONGO_INITDB_DATABASE: lucid_sessions
    volumes:
      - mongodb-data:/data/db
      - mongodb-config:/data/configdb
      - ./mongo-init.js:/docker-entrypoint-initdb.d/mongo-init.js:ro
    networks:
      - session-db-net
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.runCommand({ping: 1})"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: lucid-session-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    networks:
      - session-db-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Session API Gateway
  session-api:
    build:
      context: ./api
      dockerfile: Dockerfile
    image: lucid-session-api:latest
    container_name: lucid-session-api
    restart: unless-stopped
    ports:
      - "8087:8087"
    environment:
      - APP_NAME=Lucid Session Management API
      - DEBUG=false
      - MONGODB_URL=mongodb://${MONGO_ROOT_USERNAME}:${MONGO_ROOT_PASSWORD}@mongodb:27017/lucid_sessions?authSource=admin
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_PASSWORD=${ENCRYPTION_PASSWORD}
      - ENCRYPTION_SALT=${ENCRYPTION_SALT}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
      - RATE_LIMIT_ENABLED=true
    depends_on:
      mongodb:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - session-management-net
      - session-db-net
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8087/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Pipeline Manager
  pipeline-manager:
    build:
      context: ./pipeline
      dockerfile: Dockerfile
    image: lucid-pipeline-manager:latest
    container_name: lucid-pipeline-manager
    restart: unless-stopped
    ports:
      - "8083:8083"
    environment:
      - APP_NAME=Lucid Pipeline Manager
      - MONGODB_URL=mongodb://${MONGO_ROOT_USERNAME}:${MONGO_ROOT_PASSWORD}@mongodb:27017/lucid_sessions?authSource=admin
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - PIPELINE_BUFFER_SIZE=1000
      - PIPELINE_WORKER_COUNT=4
      - PIPELINE_TIMEOUT_SECONDS=30
    depends_on:
      - mongodb
      - redis
    networks:
      - session-management-net
      - session-db-net
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8083/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Session Recorder
  session-recorder:
    build:
      context: ./recorder
      dockerfile: Dockerfile
    image: lucid-session-recorder:latest
    container_name: lucid-session-recorder
    restart: unless-stopped
    ports:
      - "8084:8084"
    environment:
      - APP_NAME=Lucid Session Recorder
      - MONGODB_URL=mongodb://${MONGO_ROOT_USERNAME}:${MONGO_ROOT_PASSWORD}@mongodb:27017/lucid_sessions?authSource=admin
      - DEFAULT_FRAME_RATE=30
      - DEFAULT_RESOLUTION=1920x1080
      - DEFAULT_QUALITY=high
      - DEFAULT_COMPRESSION=zstd
    depends_on:
      - mongodb
    networks:
      - session-management-net
      - session-db-net
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8084/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Chunk Processor
  chunk-processor:
    build:
      context: ./processor
      dockerfile: Dockerfile
    image: lucid-chunk-processor:latest
    container_name: lucid-chunk-processor
    restart: unless-stopped
    ports:
      - "8085:8085"
    environment:
      - APP_NAME=Lucid Chunk Processor
      - MONGODB_URL=mongodb://${MONGO_ROOT_USERNAME}:${MONGO_ROOT_PASSWORD}@mongodb:27017/lucid_sessions?authSource=admin
      - ENCRYPTION_PASSWORD=${ENCRYPTION_PASSWORD}
      - ENCRYPTION_SALT=${ENCRYPTION_SALT}
      - CHUNK_STORAGE_PATH=/storage/chunks
    depends_on:
      - mongodb
    volumes:
      - chunk-storage:/storage/chunks
    networks:
      - session-management-net
      - session-db-net
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8085/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Session Storage
  session-storage:
    build:
      context: ./storage
      dockerfile: Dockerfile
    image: lucid-session-storage:latest
    container_name: lucid-session-storage
    restart: unless-stopped
    ports:
      - "8086:8086"
    environment:
      - APP_NAME=Lucid Session Storage
      - MONGODB_URL=mongodb://${MONGO_ROOT_USERNAME}:${MONGO_ROOT_PASSWORD}@mongodb:27017/lucid_sessions?authSource=admin
      - CHUNK_STORAGE_PATH=/storage/chunks
      - SESSION_STORAGE_PATH=/storage/sessions
      - MAX_STORAGE_SIZE_GB=1000
    depends_on:
      - mongodb
    volumes:
      - chunk-storage:/storage/chunks
      - session-storage:/storage/sessions
    networks:
      - session-management-net
      - session-db-net
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8086/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  session-management-net:
    driver: bridge
    name: session-management-net
  session-db-net:
    driver: bridge
    name: session-db-net
    internal: true

volumes:
  mongodb-data:
    driver: local
  mongodb-config:
    driver: local
  redis-data:
    driver: local
  chunk-storage:
    driver: local
  session-storage:
    driver: local
```

### Environment Variables

#### .env.example
```bash
# sessions/.env.example

# MongoDB Configuration
MONGO_ROOT_USERNAME=lucid_admin
MONGO_ROOT_PASSWORD=change_this_password
MONGODB_DATABASE=lucid_sessions

# Redis Configuration
REDIS_PASSWORD=change_this_redis_password

# Application Security
JWT_SECRET_KEY=change_this_jwt_secret_key_to_random_string
ENCRYPTION_PASSWORD=change_this_encryption_password
ENCRYPTION_SALT=change_this_encryption_salt

# API Configuration
ALLOWED_HOSTS=localhost,127.0.0.1,api.lucid.example
ALLOWED_ORIGINS=https://app.lucid.example,https://admin.lucid.example

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URL=redis://:${REDIS_PASSWORD}@redis:6379/1

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Volume Management

#### Storage Volume Configuration

```bash
# Create storage directories
mkdir -p /var/lucid/storage/chunks
mkdir -p /var/lucid/storage/sessions
mkdir -p /var/lucid/storage/backups

# Set permissions
chown -R 65532:65532 /var/lucid/storage

# Production volume mount
volumes:
  - /var/lucid/storage/chunks:/storage/chunks:rw
  - /var/lucid/storage/sessions:/storage/sessions:rw
```

## Kubernetes Deployment (Optional)

### Deployment Manifests

#### Session API Deployment
```yaml
# k8s/session-api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: session-api
  namespace: lucid-sessions
  labels:
    app: session-api
    component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: session-api
  template:
    metadata:
      labels:
        app: session-api
        component: api
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        fsGroup: 65532
      containers:
      - name: session-api
        image: lucid-session-api:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8087
          name: http
          protocol: TCP
        env:
        - name: MONGODB_URL
          valueFrom:
            secretKeyRef:
              name: session-secrets
              key: mongodb-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: session-secrets
              key: redis-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: session-secrets
              key: jwt-secret
        envFrom:
        - configMapRef:
            name: session-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8087
          initialDelaySeconds: 40
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8087
          initialDelaySeconds: 20
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: session-api
  namespace: lucid-sessions
  labels:
    app: session-api
spec:
  type: ClusterIP
  ports:
  - port: 8087
    targetPort: 8087
    protocol: TCP
    name: http
  selector:
    app: session-api
```

#### ConfigMap
```yaml
# k8s/session-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: session-config
  namespace: lucid-sessions
data:
  APP_NAME: "Lucid Session Management"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  RATE_LIMIT_ENABLED: "true"
  DEFAULT_FRAME_RATE: "30"
  DEFAULT_RESOLUTION: "1920x1080"
  DEFAULT_QUALITY: "high"
  DEFAULT_COMPRESSION: "zstd"
```

#### Secrets
```yaml
# k8s/session-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: session-secrets
  namespace: lucid-sessions
type: Opaque
stringData:
  mongodb-url: "mongodb://username:password@mongodb:27017/lucid_sessions"
  redis-url: "redis://:password@redis:6379/0"
  jwt-secret: "your-jwt-secret-key-here"
  encryption-password: "your-encryption-password-here"
  encryption-salt: "your-encryption-salt-here"
```

## Health Checks

### Liveness Probes

Liveness probes determine if a container needs to be restarted.

#### HTTP Health Check Implementation
```python
# sessions/core/health.py
from fastapi import APIRouter
from typing import Dict
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict:
    """Basic health check endpoint for liveness probe."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "session-management-api"
    }

@router.get("/health/live")
async def liveness() -> Dict:
    """Liveness probe endpoint."""
    return {"status": "alive"}
```

### Readiness Probes

Readiness probes determine if a container is ready to receive traffic.

```python
# sessions/core/health.py (continued)
from app.core.database import check_mongodb_connection
from app.core.cache import check_redis_connection

@router.get("/health/ready")
async def readiness() -> Dict:
    """Readiness probe endpoint with dependency checks."""
    
    checks = {
        "mongodb": await check_mongodb_connection(),
        "redis": await check_redis_connection(),
        "storage": check_storage_available()
    }
    
    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503
    
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

async def check_mongodb_connection() -> bool:
    """Check MongoDB connection."""
    try:
        from app.core.database import get_db
        db = next(get_db())
        await db.command("ping")
        return True
    except Exception:
        return False

async def check_redis_connection() -> bool:
    """Check Redis connection."""
    try:
        from app.core.cache import get_redis
        redis = get_redis()
        await redis.ping()
        return True
    except Exception:
        return False

def check_storage_available() -> bool:
    """Check storage availability."""
    try:
        import os
        from app.core.config import settings
        
        storage_path = settings.CHUNK_STORAGE_PATH
        stat = os.statvfs(storage_path)
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        
        # Require at least 10GB available
        return available_gb > 10
    except Exception:
        return False
```

### Startup Probes

Startup probes determine when a container has started successfully.

```python
@router.get("/health/startup")
async def startup() -> Dict:
    """Startup probe endpoint."""
    
    # Check if application has fully initialized
    from app.core.startup import is_initialized
    
    if is_initialized():
        return {"status": "started"}
    else:
        raise HTTPException(status_code=503, detail="Application still starting")
```

## Monitoring and Observability

### Prometheus Metrics

#### Metrics Endpoint Implementation
```python
# sessions/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response
import time

# Session metrics
sessions_created_total = Counter(
    'sessions_created_total',
    'Total number of sessions created',
    ['status']
)

sessions_active = Gauge(
    'sessions_active',
    'Number of active sessions'
)

session_duration_seconds = Histogram(
    'session_duration_seconds',
    'Session duration in seconds',
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800]
)

# Chunk metrics
chunks_processed_total = Counter(
    'chunks_processed_total',
    'Total number of chunks processed',
    ['status']
)

chunk_processing_duration_seconds = Histogram(
    'chunk_processing_duration_seconds',
    'Chunk processing duration',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

chunk_size_bytes = Histogram(
    'chunk_size_bytes',
    'Chunk size in bytes',
    buckets=[1024, 10240, 102400, 1024000, 10240000, 102400000]
)

# Storage metrics
storage_used_bytes = Gauge(
    'storage_used_bytes',
    'Storage used in bytes',
    ['type']
)

storage_operations_total = Counter(
    'storage_operations_total',
    'Total storage operations',
    ['operation', 'status']
)

# API metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

# Pipeline metrics
pipeline_stage_duration_seconds = Histogram(
    'pipeline_stage_duration_seconds',
    'Pipeline stage processing duration',
    ['stage']
)

pipeline_errors_total = Counter(
    'pipeline_errors_total',
    'Total pipeline errors',
    ['stage', 'error_type']
)

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### Grafana Dashboards

#### Session Management Dashboard JSON
```json
{
  "dashboard": {
    "title": "Session Management Cluster",
    "panels": [
      {
        "title": "Active Sessions",
        "type": "graph",
        "targets": [
          {
            "expr": "sessions_active",
            "legendFormat": "Active Sessions"
          }
        ]
      },
      {
        "title": "Session Creation Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(sessions_created_total[5m])",
            "legendFormat": "Sessions/sec"
          }
        ]
      },
      {
        "title": "Chunk Processing Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(chunks_processed_total{status='success'}[5m])",
            "legendFormat": "Chunks/sec"
          }
        ]
      },
      {
        "title": "Storage Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "storage_used_bytes",
            "legendFormat": "{{ type }}"
          }
        ]
      },
      {
        "title": "API Latency (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{ endpoint }}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(pipeline_errors_total[5m])",
            "legendFormat": "{{ stage }}"
          }
        ]
      }
    ]
  }
}
```

### Alert Rules

#### Prometheus Alert Rules
```yaml
# prometheus/alerts/session-management.yml
groups:
  - name: session_management_alerts
    interval: 30s
    rules:
      # Service availability alerts
      - alert: SessionAPIDown
        expr: up{job="session-api"} == 0
        for: 2m
        labels:
          severity: critical
          component: session-api
        annotations:
          summary: "Session API is down"
          description: "Session API has been down for more than 2 minutes"
      
      - alert: PipelineManagerDown
        expr: up{job="pipeline-manager"} == 0
        for: 2m
        labels:
          severity: critical
          component: pipeline-manager
        annotations:
          summary: "Pipeline Manager is down"
          description: "Pipeline Manager has been down for more than 2 minutes"
      
      # Performance alerts
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m])) > 0.2
        for: 5m
        labels:
          severity: warning
          component: session-api
        annotations:
          summary: "High API latency detected"
          description: "95th percentile API latency is above 200ms for 5 minutes"
      
      - alert: LowChunkProcessingRate
        expr: rate(chunks_processed_total{status="success"}[5m]) < 16.67
        for: 5m
        labels:
          severity: warning
          component: chunk-processor
        annotations:
          summary: "Low chunk processing rate"
          description: "Chunk processing rate is below 1000/minute (SLA threshold)"
      
      # Storage alerts
      - alert: StorageSpaceLow
        expr: storage_used_bytes{type="chunks"} / (1024^3) > 900
        for: 10m
        labels:
          severity: warning
          component: storage
        annotations:
          summary: "Storage space running low"
          description: "Chunk storage usage is above 900GB (90% of 1TB limit)"
      
      - alert: StorageSpaceCritical
        expr: storage_used_bytes{type="chunks"} / (1024^3) > 950
        for: 5m
        labels:
          severity: critical
          component: storage
        annotations:
          summary: "Storage space critically low"
          description: "Chunk storage usage is above 950GB (95% of 1TB limit)"
      
      # Error rate alerts
      - alert: HighPipelineErrorRate
        expr: rate(pipeline_errors_total[5m]) > 0.01
        for: 5m
        labels:
          severity: warning
          component: pipeline
        annotations:
          summary: "High pipeline error rate"
          description: "Pipeline error rate is above 1% for 5 minutes"
      
      - alert: CriticalPipelineErrorRate
        expr: rate(pipeline_errors_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
          component: pipeline
        annotations:
          summary: "Critical pipeline error rate"
          description: "Pipeline error rate is above 5% for 2 minutes"
      
      # Resource alerts
      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes{container=~"lucid-.*"} / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
          component: container
        annotations:
          summary: "High memory usage"
          description: "Container {{ $labels.container }} memory usage is above 90%"
      
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total{container=~"lucid-.*"}[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
          component: container
        annotations:
          summary: "High CPU usage"
          description: "Container {{ $labels.container }} CPU usage is above 80%"
```

### Log Aggregation

#### Structured Logging Configuration
```python
# sessions/core/logging.py
import logging
import json
from datetime import datetime
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

def setup_logging():
    """Configure structured logging."""
    from app.core.config import settings
    
    # Create logger
    logger = logging.getLogger("lucid.sessions")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Create handler
    handler = logging.StreamHandler()
    
    # Set formatter
    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: Session API Not Starting

**Symptoms:**
- Container starts but health checks fail
- Connection refused errors

**Diagnosis:**
```bash
# Check container logs
docker logs lucid-session-api

# Check container status
docker ps -a | grep lucid-session-api

# Inspect container
docker inspect lucid-session-api
```

**Solutions:**
1. Verify MongoDB connection:
```bash
docker exec lucid-session-mongodb mongosh --eval "db.runCommand({ping: 1})"
```

2. Check environment variables:
```bash
docker exec lucid-session-api env | grep MONGODB_URL
```

3. Verify port availability:
```bash
netstat -tulpn | grep 8087
```

#### Issue 2: High Memory Usage

**Symptoms:**
- Container OOM kills
- Slow performance
- Memory usage above 90%

**Diagnosis:**
```bash
# Check container memory usage
docker stats lucid-session-api

# Check detailed memory stats
docker exec lucid-session-api cat /sys/fs/cgroup/memory/memory.stat
```

**Solutions:**
1. Increase memory limits in docker-compose.yml:
```yaml
services:
  session-api:
    deploy:
      resources:
        limits:
          memory: 1024M
```

2. Check for memory leaks:
```bash
# Enable memory profiling
docker exec lucid-session-api python -m memory_profiler app/api/session_api.py
```

3. Optimize chunk buffer size:
```bash
# Reduce buffer size
PIPELINE_BUFFER_SIZE=500
```

#### Issue 3: Slow Chunk Processing

**Symptoms:**
- Chunk processing below SLA (1000/minute)
- Increasing queue backlog
- High latency

**Diagnosis:**
```bash
# Check pipeline metrics
curl http://localhost:8087/metrics | grep chunk_processing

# Check worker count
docker exec lucid-pipeline-manager env | grep PIPELINE_WORKER_COUNT
```

**Solutions:**
1. Increase worker count:
```yaml
environment:
  - PIPELINE_WORKER_COUNT=8
```

2. Optimize compression settings:
```python
# Use faster compression level
recording_config.compression = "lz4"  # instead of zstd
```

3. Scale horizontally:
```bash
docker-compose up --scale chunk-processor=3
```

#### Issue 4: Storage Space Issues

**Symptoms:**
- "No space left on device" errors
- Failed chunk writes
- Storage alerts firing

**Diagnosis:**
```bash
# Check storage usage
df -h /var/lucid/storage/chunks

# Check largest sessions
du -sh /var/lucid/storage/chunks/* | sort -h | tail -20

# Check inode usage
df -i /var/lucid/storage/chunks
```

**Solutions:**
1. Clean up old sessions:
```bash
# Run retention cleanup
docker exec lucid-session-storage python -m app.core.retention cleanup
```

2. Compress old chunks:
```bash
# Compress inactive chunks
find /var/lucid/storage/chunks -mtime +7 -exec gzip {} \;
```

3. Expand storage volume:
```bash
# Add new volume
docker volume create --name chunk-storage-2
```

### Debug Procedures

#### Enable Debug Mode

```bash
# Set debug environment variable
docker exec lucid-session-api sh -c 'export DEBUG=true'

# Restart service
docker restart lucid-session-api

# Check debug logs
docker logs -f lucid-session-api
```

#### Database Query Debugging

```python
# sessions/core/debug.py
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("motor").setLevel(logging.DEBUG)

# Enable MongoDB query logging
client = AsyncIOMotorClient(
    "mongodb://localhost:27017",
    event_listeners=[CommandLogger()]
)
```

#### Network Debugging

```bash
# Check service connectivity
docker exec lucid-session-api ping mongodb

# Check DNS resolution
docker exec lucid-session-api nslookup mongodb

# Trace network packets
docker exec lucid-session-api tcpdump -i any port 27017
```

## Backup and Recovery

### MongoDB Backup

#### Automated Backup Script
```bash
#!/bin/bash
# scripts/backup-mongodb.sh

BACKUP_DIR="/var/lucid/backups/mongodb"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="mongodb_backup_$TIMESTAMP"

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform backup
docker exec lucid-session-mongodb mongodump \
    --out=/tmp/$BACKUP_NAME \
    --db=lucid_sessions \
    --gzip

# Copy backup from container
docker cp lucid-session-mongodb:/tmp/$BACKUP_NAME $BACKUP_DIR/

# Remove old backups (keep last 7 days)
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR/$BACKUP_NAME"
```

#### Restore Procedure
```bash
#!/bin/bash
# scripts/restore-mongodb.sh

BACKUP_PATH=$1

if [ -z "$BACKUP_PATH" ]; then
    echo "Usage: $0 <backup_path>"
    exit 1
fi

# Copy backup to container
docker cp $BACKUP_PATH lucid-session-mongodb:/tmp/restore/

# Restore database
docker exec lucid-session-mongodb mongorestore \
    --db=lucid_sessions \
    --gzip \
    /tmp/restore/

echo "Restore completed from: $BACKUP_PATH"
```

### Chunk Storage Backup

#### Incremental Backup
```bash
#!/bin/bash
# scripts/backup-chunks.sh

SOURCE_DIR="/var/lucid/storage/chunks"
BACKUP_DIR="/var/lucid/backups/chunks"
TIMESTAMP=$(date +%Y%m%d)

# Create backup using rsync (incremental)
rsync -avz --delete \
    --link-dest=$BACKUP_DIR/latest \
    $SOURCE_DIR/ \
    $BACKUP_DIR/$TIMESTAMP/

# Update latest symlink
ln -snf $BACKUP_DIR/$TIMESTAMP $BACKUP_DIR/latest

echo "Chunk backup completed: $BACKUP_DIR/$TIMESTAMP"
```

### Disaster Recovery

#### Recovery Procedure
```markdown
1. **Stop all services:**
   ```bash
   docker-compose down
   ```

2. **Restore MongoDB:**
   ```bash
   ./scripts/restore-mongodb.sh /var/lucid/backups/mongodb/mongodb_backup_20240115_120000
   ```

3. **Restore chunk storage:**
   ```bash
   rsync -avz /var/lucid/backups/chunks/latest/ /var/lucid/storage/chunks/
   ```

4. **Verify data integrity:**
   ```bash
   docker-compose up -d mongodb
   docker exec lucid-session-mongodb mongosh --eval "db.sessions.countDocuments({})"
   ```

5. **Start services:**
   ```bash
   docker-compose up -d
   ```

6. **Verify health:**
   ```bash
   curl http://localhost:8087/health
   ```
```

## Scaling Strategies

### Horizontal Scaling

#### Load Balancer Configuration (Nginx)
```nginx
# nginx/session-api-lb.conf
upstream session_api {
    least_conn;
    server session-api-1:8087 max_fails=3 fail_timeout=30s;
    server session-api-2:8087 max_fails=3 fail_timeout=30s;
    server session-api-3:8087 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api-sessions.lucid.example;

    location / {
        proxy_pass http://session_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

#### Scaling with Docker Swarm
```yaml
# docker-compose.swarm.yml
version: '3.8'

services:
  session-api:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        max_attempts: 3
      placement:
        constraints:
          - node.role == worker
```

### Resource Allocation

#### Recommended Resource Limits

| Service | CPU (Cores) | Memory (GB) | Storage (GB) |
|---------|------------|-------------|--------------|
| Session API | 0.5-1.0 | 0.5-1.0 | - |
| Pipeline Manager | 1.0-2.0 | 1.0-2.0 | - |
| Session Recorder | 1.0-2.0 | 1.0-2.0 | - |
| Chunk Processor | 2.0-4.0 | 2.0-4.0 | - |
| Session Storage | 0.5-1.0 | 0.5-1.0 | 100+ |
| MongoDB | 2.0-4.0 | 4.0-8.0 | 50+ |
| Redis | 0.5-1.0 | 2.0-4.0 | 10+ |

## Maintenance Procedures

### Rolling Updates

```bash
#!/bin/bash
# scripts/rolling-update.sh

SERVICES=("session-api" "pipeline-manager" "session-recorder" "chunk-processor" "session-storage")

for service in "${SERVICES[@]}"; do
    echo "Updating $service..."
    
    # Pull new image
    docker-compose pull $service
    
    # Recreate service
    docker-compose up -d --no-deps --build $service
    
    # Wait for health check
    sleep 30
    
    # Verify health
    if ! docker exec lucid-$service curl -f http://localhost:808X/health; then
        echo "Health check failed for $service"
        exit 1
    fi
    
    echo "$service updated successfully"
done

echo "All services updated successfully"
```

### Database Maintenance

```bash
# Monthly maintenance script
docker exec lucid-session-mongodb mongosh --eval "
    use lucid_sessions;
    
    // Compact collections
    db.runCommand({ compact: 'sessions' });
    db.runCommand({ compact: 'chunks' });
    
    // Rebuild indexes
    db.sessions.reIndex();
    db.chunks.reIndex();
    
    // Update statistics
    db.runCommand({ dbStats: 1 });
"
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-XX  
**Next Review**: 2024-04-XX

