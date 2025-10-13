# 13. Configuration Templates

## Overview

This document provides comprehensive configuration templates for the TRON Payment System API, including environment configurations, Docker Compose files, Kubernetes manifests, and deployment scripts.

## Environment Configuration

### Base Configuration Template

```python
# config/base.py
from pydantic import BaseSettings, validator
from typing import List, Optional
import os

class BaseConfig(BaseSettings):
    """Base configuration for TRON Payment API."""
    
    # Application
    APP_NAME: str = "Lucid TRON Payment API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    
    # Security
    SECRET_KEY: str
    ALLOWED_HOSTS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = []
    CORS_ORIGINS: List[str] = []
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # TRON Network
    TRON_NODE_URL: str = "https://api.trongrid.io"
    TRON_NETWORK: str = "mainnet"  # mainnet, testnet
    USDT_CONTRACT_ADDRESS: str = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    WALLET_ADDRESS: str
    WALLET_PRIVATE_KEY: str
    
    # API Gateway
    API_GATEWAY_URL: str
    API_GATEWAY_TOKEN: str
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URL: str = "redis://localhost:6379/1"
    RATE_LIMIT_CALLS: int = 100
    RATE_LIMIT_PERIOD: int = 3600
    
    # Circuit Breaker
    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    @validator('ALLOWED_HOSTS', pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v
    
    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

### Development Configuration

```python
# config/development.py
from .base import BaseConfig

class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
    # Development database
    DATABASE_URL: str = "postgresql://lucid:password@localhost:5432/lucid_payment_dev"
    
    # Development TRON network (testnet)
    TRON_NETWORK: str = "testnet"
    TRON_NODE_URL: str = "https://api.shasta.trongrid.io"
    USDT_CONTRACT_ADDRESS: str = "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"  # Testnet USDT
    
    # Relaxed security for development
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Development API Gateway
    API_GATEWAY_URL: str = "http://localhost:8080"
    API_GATEWAY_TOKEN: str = "dev-token"
    
    class Config:
        env_file = ".env.development"
```

### Production Configuration

```python
# config/production.py
from .base import BaseConfig

class ProductionConfig(BaseConfig):
    """Production configuration."""
    
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Production database
    DATABASE_URL: str = "postgresql://lucid:${DB_PASSWORD}@db:5432/lucid_payment_prod"
    
    # Production TRON network (mainnet)
    TRON_NETWORK: str = "mainnet"
    TRON_NODE_URL: str = "https://api.trongrid.io"
    USDT_CONTRACT_ADDRESS: str = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    
    # Strict security for production
    ALLOWED_ORIGINS: List[str] = []  # Configure specific origins
    
    # Production API Gateway
    API_GATEWAY_URL: str = "https://api-gateway.lucid.example"
    
    # Enhanced security
    RATE_LIMIT_CALLS: int = 50
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    
    class Config:
        env_file = ".env.production"
```

## Docker Configuration

### Multi-Stage Dockerfile

```dockerfile
# Dockerfile
# Build stage
FROM python:3.12-slim-bookworm as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION=3.12

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM gcr.io/distroless/python3-debian12:nonroot

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy application code
COPY --chown=nonroot:nonroot app/ ./app/
COPY --chown=nonroot:nonroot config/ ./config/
COPY --chown=nonroot:nonroot main.py .

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R nonroot:nonroot /app

# Set user
USER nonroot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import requests; requests.get('http://localhost:8000/health')"]

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose - Development

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # TRON Payment API
  tron-payment-api:
    build:
      context: .
      dockerfile: Dockerfile
      target: builder  # Use builder stage for development
    container_name: lucid-tron-payment-api-dev
    ports:
      - "8000:8000"
      - "9090:9090"  # Prometheus metrics
    environment:
      - ENV=development
      - DEBUG=true
      - DATABASE_URL=postgresql://lucid:password@postgres:5432/lucid_payment_dev
      - REDIS_URL=redis://redis:6379/0
      - TRON_NODE_URL=https://api.shasta.trongrid.io
      - TRON_NETWORK=testnet
      - API_GATEWAY_URL=http://api-gateway:8080
    volumes:
      - ./app:/app/app:ro
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - ./secrets:/app/secrets:ro
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      api-gateway:
        condition: service_started
    networks:
      - wallet_plane
      - ops_plane
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: lucid-postgres-dev
    environment:
      - POSTGRES_DB=lucid_payment_dev
      - POSTGRES_USER=lucid
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    ports:
      - "5432:5432"
    networks:
      - wallet_plane
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lucid -d lucid_payment_dev"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: lucid-redis-dev
    command: redis-server --appendonly yes --requirepass redis_password
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - wallet_plane
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # API Gateway
  api-gateway:
    image: nginx:alpine
    container_name: lucid-api-gateway-dev
    ports:
      - "8080:80"
    volumes:
      - ./nginx/api-gateway.conf:/etc/nginx/nginx.conf:ro
    networks:
      - ops_plane
      - wallet_plane
    restart: unless-stopped

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: lucid-prometheus-dev
    ports:
      - "9091:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - ops_plane
    restart: unless-stopped

  # Grafana Dashboard
  grafana:
    image: grafana/grafana:latest
    container_name: lucid-grafana-dev
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    networks:
      - ops_plane
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  ops_plane:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
  wallet_plane:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
  chain_plane:
    driver: bridge
    ipam:
      config:
        - subnet: 172.22.0.0/16
```

### Docker Compose - Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # TRON Payment API (Distroless)
  tron-payment-api:
    image: lucid/tron-payment-api:latest
    container_name: lucid-tron-payment-api-prod
    ports:
      - "8000:8000"
      - "9090:9090"
    environment:
      - ENV=production
      - DEBUG=false
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - TRON_NODE_URL=${TRON_NODE_URL}
      - TRON_NETWORK=${TRON_NETWORK}
      - WALLET_ADDRESS=${WALLET_ADDRESS}
      - WALLET_PRIVATE_KEY=${WALLET_PRIVATE_KEY}
      - API_GATEWAY_URL=${API_GATEWAY_URL}
      - API_GATEWAY_TOKEN=${API_GATEWAY_TOKEN}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./secrets:/app/secrets:ro
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - wallet_plane
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # PostgreSQL Database (Production)
  postgres:
    image: postgres:15-alpine
    container_name: lucid-postgres-prod
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - wallet_plane
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Redis Cache (Production)
  redis:
    image: redis:7-alpine
    container_name: lucid-redis-prod
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - wallet_plane
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
        reservations:
          memory: 128M
          cpus: '0.1'
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postgres_data:
  redis_data:

networks:
  wallet_plane:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.21.0.0/16
```

## Kubernetes Configuration

### Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lucid-payment
  labels:
    name: lucid-payment
    app.kubernetes.io/name: lucid-payment-api
    app.kubernetes.io/version: "1.0.0"
```

### ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tron-payment-config
  namespace: lucid-payment
data:
  APP_NAME: "Lucid TRON Payment API"
  APP_VERSION: "1.0.0"
  HOST: "0.0.0.0"
  PORT: "8000"
  TRON_NETWORK: "mainnet"
  TRON_NODE_URL: "https://api.trongrid.io"
  USDT_CONTRACT_ADDRESS: "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
  RATE_LIMIT_ENABLED: "true"
  RATE_LIMIT_CALLS: "100"
  RATE_LIMIT_PERIOD: "3600"
  CIRCUIT_BREAKER_ENABLED: "true"
  CIRCUIT_BREAKER_FAILURE_THRESHOLD: "5"
  CIRCUIT_BREAKER_RECOVERY_TIMEOUT: "60"
  PROMETHEUS_ENABLED: "true"
  PROMETHEUS_PORT: "9090"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
```

### Secret

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: tron-payment-secrets
  namespace: lucid-payment
type: Opaque
data:
  # Base64 encoded values
  SECRET_KEY: <base64-encoded-secret-key>
  DATABASE_URL: <base64-encoded-database-url>
  REDIS_URL: <base64-encoded-redis-url>
  WALLET_ADDRESS: <base64-encoded-wallet-address>
  WALLET_PRIVATE_KEY: <base64-encoded-private-key>
  API_GATEWAY_URL: <base64-encoded-gateway-url>
  API_GATEWAY_TOKEN: <base64-encoded-gateway-token>
  REDIS_PASSWORD: <base64-encoded-redis-password>
```

### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tron-payment-api
  namespace: lucid-payment
  labels:
    app: tron-payment-api
    version: "1.0.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tron-payment-api
  template:
    metadata:
      labels:
        app: tron-payment-api
        version: "1.0.0"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: tron-payment-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        fsGroup: 65532
      containers:
      - name: tron-payment-api
        image: lucid/tron-payment-api:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
          protocol: TCP
        - containerPort: 9090
          name: metrics
          protocol: TCP
        env:
        - name: ENV
          value: "production"
        - name: DEBUG
          value: "false"
        envFrom:
        - configMapRef:
            name: tron-payment-config
        - secretRef:
            name: tron-payment-secrets
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
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        volumeMounts:
        - name: logs
          mountPath: /app/logs
        - name: secrets
          mountPath: /app/secrets
          readOnly: true
      volumes:
      - name: logs
        emptyDir: {}
      - name: secrets
        secret:
          secretName: tron-payment-secrets
          items:
          - key: WALLET_PRIVATE_KEY
            path: wallet.key
            mode: 0400
      nodeSelector:
        kubernetes.io/arch: amd64
      tolerations:
      - key: "node-role.kubernetes.io/control-plane"
        operator: "Exists"
        effect: "NoSchedule"
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - tron-payment-api
              topologyKey: kubernetes.io/hostname
```

### Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: tron-payment-api-service
  namespace: lucid-payment
  labels:
    app: tron-payment-api
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
    prometheus.io/path: "/metrics"
spec:
  selector:
    app: tron-payment-api
  ports:
  - name: http
    port: 8000
    targetPort: 8000
    protocol: TCP
  - name: metrics
    port: 9090
    targetPort: 9090
    protocol: TCP
  type: ClusterIP
```

### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tron-payment-api-ingress
  namespace: lucid-payment
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - api-payment.lucid.example
    secretName: tron-payment-api-tls
  rules:
  - host: api-payment.lucid.example
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tron-payment-api-service
            port:
              number: 8000
```

### ServiceAccount and RBAC

```yaml
# k8s/rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tron-payment-sa
  namespace: lucid-payment
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tron-payment-role
  namespace: lucid-payment
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tron-payment-rolebinding
  namespace: lucid-payment
subjects:
- kind: ServiceAccount
  name: tron-payment-sa
  namespace: lucid-payment
roleRef:
  kind: Role
  name: tron-payment-role
  apiGroup: rbac.authorization.k8s.io
```

## Nginx Configuration

### API Gateway Configuration

```nginx
# nginx/api-gateway.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=payouts:10m rate=1r/s;
    
    # Upstream services
    upstream tron_payment_api {
        server tron-payment-api:8000;
        keepalive 32;
    }
    
    upstream auth_service {
        server auth-service:8080;
        keepalive 16;
    }
    
    # Main server block
    server {
        listen 80;
        server_name api-payment.lucid.example;
        
        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        
        # CORS headers
        add_header Access-Control-Allow-Origin "https://app.lucid.example" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
        add_header Access-Control-Max-Age 86400 always;
        
        # Handle preflight requests
        location / {
            if ($request_method = 'OPTIONS') {
                add_header Access-Control-Allow-Origin "https://app.lucid.example";
                add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
                add_header Access-Control-Allow-Headers "Authorization, Content-Type";
                add_header Access-Control-Max-Age 86400;
                add_header Content-Length 0;
                add_header Content-Type text/plain;
                return 204;
            }
        }
        
        # Authentication endpoint
        location /auth/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://auth_service/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            proxy_connect_timeout 5s;
            proxy_send_timeout 10s;
            proxy_read_timeout 10s;
        }
        
        # Payment API endpoints
        location /api/payment/ {
            limit_req zone=api burst=50 nodelay;
            
            # Special rate limiting for payout endpoints
            location ~ ^/api/payment/payouts {
                limit_req zone=payouts burst=5 nodelay;
            }
            
            proxy_pass http://tron_payment_api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Authorization $http_authorization;
            
            proxy_connect_timeout 5s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
            
            # Buffer settings
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }
        
        # Health check endpoint
        location /health {
            proxy_pass http://tron_payment_api/health;
            access_log off;
        }
        
        # Metrics endpoint (internal only)
        location /metrics {
            allow 10.0.0.0/8;
            allow 172.16.0.0/12;
            allow 192.168.0.0/16;
            deny all;
            
            proxy_pass http://tron_payment_api/metrics;
        }
        
        # Default location
        location / {
            return 404;
        }
    }
}
```

## Environment Files

### Development Environment

```bash
# .env.development
ENV=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=1

# Security
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Database
DATABASE_URL=postgresql://lucid:password@localhost:5432/lucid_payment_dev
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=redis_password

# TRON Network (Testnet)
TRON_NETWORK=testnet
TRON_NODE_URL=https://api.shasta.trongrid.io
USDT_CONTRACT_ADDRESS=TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf
WALLET_ADDRESS=TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH
WALLET_PRIVATE_KEY=your_testnet_private_key_here

# API Gateway
API_GATEWAY_URL=http://localhost:8080
API_GATEWAY_TOKEN=dev-token

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/1
RATE_LIMIT_CALLS=1000
RATE_LIMIT_PERIOD=3600

# Circuit Breaker
CIRCUIT_BREAKER_ENABLED=true
CIRCUIT_BREAKER_FAILURE_THRESHOLD=10
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json
```

### Production Environment

```bash
# .env.production
ENV=production
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Security
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=api-payment.lucid.example
ALLOWED_ORIGINS=https://app.lucid.example

# Database
DATABASE_URL=${DATABASE_URL}
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=${REDIS_URL}
REDIS_PASSWORD=${REDIS_PASSWORD}

# TRON Network (Mainnet)
TRON_NETWORK=mainnet
TRON_NODE_URL=https://api.trongrid.io
USDT_CONTRACT_ADDRESS=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
WALLET_ADDRESS=${WALLET_ADDRESS}
WALLET_PRIVATE_KEY=${WALLET_PRIVATE_KEY}

# API Gateway
API_GATEWAY_URL=https://api-gateway.lucid.example
API_GATEWAY_TOKEN=${API_GATEWAY_TOKEN}

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URL=${REDIS_URL}/1
RATE_LIMIT_CALLS=100
RATE_LIMIT_PERIOD=3600

# Circuit Breaker
CIRCUIT_BREAKER_ENABLED=true
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Deployment Scripts

### Build Script

```bash
#!/bin/bash
# scripts/build.sh

set -euo pipefail

# Configuration
REGISTRY="lucid"
IMAGE_NAME="tron-payment-api"
VERSION="${1:-latest}"
PLATFORMS="linux/amd64,linux/arm64"

echo "Building TRON Payment API image..."
echo "Registry: ${REGISTRY}"
echo "Image: ${IMAGE_NAME}"
echo "Version: ${VERSION}"
echo "Platforms: ${PLATFORMS}"

# Create buildx builder if it doesn't exist
docker buildx create --name lucid-builder --use --bootstrap || true

# Build multi-platform image
docker buildx build \
    --platform "${PLATFORMS}" \
    --tag "${REGISTRY}/${IMAGE_NAME}:${VERSION}" \
    --tag "${REGISTRY}/${IMAGE_NAME}:latest" \
    --push \
    --progress=plain \
    --no-cache \
    .

echo "Build completed successfully!"
echo "Image: ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
```

### Deployment Script

```bash
#!/bin/bash
# scripts/deploy.sh

set -euo pipefail

# Configuration
NAMESPACE="lucid-payment"
IMAGE_TAG="${1:-latest}"
ENVIRONMENT="${2:-production}"

echo "Deploying TRON Payment API..."
echo "Namespace: ${NAMESPACE}"
echo "Image Tag: ${IMAGE_TAG}"
echo "Environment: ${ENVIRONMENT}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
    echo "Creating namespace ${NAMESPACE}..."
    kubectl create namespace "${NAMESPACE}"
fi

# Apply configurations
echo "Applying Kubernetes configurations..."

# Apply in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/rbac.yaml

# Update image tag in deployment
sed "s|image: lucid/tron-payment-api:.*|image: lucid/tron-payment-api:${IMAGE_TAG}|g" \
    k8s/deployment.yaml | kubectl apply -f -

kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Wait for deployment to be ready
echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/tron-payment-api -n "${NAMESPACE}" --timeout=300s

# Verify deployment
echo "Verifying deployment..."
kubectl get pods -n "${NAMESPACE}" -l app=tron-payment-api

echo "Deployment completed successfully!"
```

### Health Check Script

```bash
#!/bin/bash
# scripts/health-check.sh

set -euo pipefail

# Configuration
API_URL="${1:-http://localhost:8000}"
TIMEOUT="${2:-30}"

echo "Performing health check on TRON Payment API..."
echo "URL: ${API_URL}"
echo "Timeout: ${TIMEOUT}s"

# Function to check endpoint
check_endpoint() {
    local endpoint="$1"
    local expected_status="$2"
    
    echo "Checking ${endpoint}..."
    
    response=$(curl -s -w "%{http_code}" -o /dev/null \
        --max-time "${TIMEOUT}" \
        "${API_URL}${endpoint}")
    
    if [ "${response}" -eq "${expected_status}" ]; then
        echo "✓ ${endpoint} - OK (${response})"
        return 0
    else
        echo "✗ ${endpoint} - FAILED (${response})"
        return 1
    fi
}

# Check health endpoints
echo "=== Health Check Results ==="

failed=0

# Basic health check
check_endpoint "/health" 200 || failed=$((failed + 1))

# Readiness check
check_endpoint "/ready" 200 || failed=$((failed + 1))

# Liveness check
check_endpoint "/live" 200 || failed=$((failed + 1))

# API endpoints (should require authentication)
check_endpoint "/api/payment/stats" 401 || failed=$((failed + 1))

# Metrics endpoint
check_endpoint "/metrics" 200 || failed=$((failed + 1))

echo "=== Summary ==="
if [ "${failed}" -eq 0 ]; then
    echo "✓ All health checks passed!"
    exit 0
else
    echo "✗ ${failed} health check(s) failed!"
    exit 1
fi
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-XX  
**Next Review**: 2024-04-XX
