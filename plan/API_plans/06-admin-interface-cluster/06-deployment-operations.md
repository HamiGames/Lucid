# Admin Interface Cluster - Deployment & Operations

## Overview

Comprehensive deployment and operations guide for the Admin Interface cluster (Cluster 6) covering Docker containerization, orchestration, monitoring, and operational procedures.

## Deployment Architecture

### Container Strategy

#### Distroless Container Design
```dockerfile
# infrastructure/docker/multi-stage/Dockerfile.admin-interface
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY admin_interface/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY admin_interface/ .

# Production stage - Distroless
FROM gcr.io/distroless/python3-debian11

# Copy Python application and dependencies
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LUCID_ENV=production

# Set working directory
WORKDIR /app

# Non-root user for security
USER 65534:65534

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import requests; requests.get('http://localhost:8096/health')"]

# Expose port
EXPOSE 8096

# Start command
CMD ["/usr/bin/python3", "-m", "admin_interface.main"]
```

#### Multi-Stage Build Optimization
```dockerfile
# Optimized multi-stage build for admin interface
FROM python:3.11-slim as dependencies

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY admin_interface/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim as application

WORKDIR /app

# Copy only necessary files
COPY --from=dependencies /root/.local /root/.local
COPY admin_interface/ /app/

# Final distroless stage
FROM gcr.io/distroless/python3-debian11

COPY --from=application /root/.local /root/.local
COPY --from=application /app /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LUCID_ENV=production

WORKDIR /app
USER 65534:65534

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import requests; requests.get('http://localhost:8096/health')"]

EXPOSE 8096

CMD ["/usr/bin/python3", "-m", "admin_interface.main"]
```

### Docker Compose Configuration

#### Development Environment
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  admin-interface:
    build:
      context: .
      dockerfile: infrastructure/docker/multi-stage/Dockerfile.admin-interface
      target: development
    container_name: lucid-admin-interface-dev
    ports:
      - "8096:8096"
    environment:
      - LUCID_ENV=development
      - MONGO_URL=mongodb://lucid:lucid@mongo:27017/lucid?authSource=admin
      - REDIS_URL=redis://redis:6379/0
      - TOR_PROXY_URL=socks5://tor:9050
      - DEBUG=true
      - LOG_LEVEL=debug
    volumes:
      - ./admin_interface:/app/admin_interface
      - ./logs:/app/logs
    depends_on:
      - mongo
      - redis
      - tor
      - blockchain-core
      - session-management
    networks:
      - lucid-dev

  mongo:
    image: mongo:7.0
    container_name: lucid-mongo-dev
    environment:
      - MONGO_INITDB_ROOT_USERNAME=lucid
      - MONGO_INITDB_ROOT_PASSWORD=lucid
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db
    networks:
      - lucid-dev

  redis:
    image: redis:7-alpine
    container_name: lucid-redis-dev
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - lucid-dev

  tor:
    image: alpine:3.18
    container_name: lucid-tor-dev
    volumes:
      - ./configs/tor/torrc.dev:/etc/tor/torrc
    ports:
      - "9050:9050"
      - "9051:9051"
    command: sh -c "apk add --no-cache tor && tor -f /etc/tor/torrc"
    networks:
      - lucid-dev

networks:
  lucid-dev:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  mongo-data:
  redis-data:
```

#### Production Environment
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  admin-interface:
    image: ghcr.io/hamigames/lucid/admin-interface:latest
    container_name: lucid-admin-interface
    restart: unless-stopped
    ports:
      - "8096:8096"
    environment:
      - LUCID_ENV=production
      - MONGO_URL=${MONGO_URL}
      - REDIS_URL=${REDIS_URL}
      - TOR_PROXY_URL=${TOR_PROXY_URL}
      - LOG_LEVEL=info
      - ADMIN_INTERFACE_SECRET_KEY=${ADMIN_INTERFACE_SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - HARDWARE_WALLET_API_KEY=${HARDWARE_WALLET_API_KEY}
    volumes:
      - admin-logs:/app/logs
      - admin-config:/app/config
      - /etc/ssl/certs:/etc/ssl/certs:ro
      - /etc/ssl/private:/etc/ssl/private:ro
    depends_on:
      - mongo
      - redis
      - tor
    networks:
      - lucid-prod
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8096/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Beta sidecar for admin interface
  admin-interface-beta:
    image: gcr.io/distroless/static-debian11
    container_name: lucid-admin-interface-beta
    command: ["/beta-sidecar"]
    volumes:
      - ./configs/beta-sidecar/admin-interface.yaml:/etc/beta-sidecar/config.yaml:ro
    networks:
      - lucid-prod
    depends_on:
      - admin-interface

networks:
  lucid-prod:
    driver: bridge
    internal: true

volumes:
  admin-logs:
  admin-config:
```

## Orchestration

### Kubernetes Deployment

#### Admin Interface Deployment
```yaml
# k8s/admin-interface-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lucid-admin-interface
  namespace: lucid-system
  labels:
    app: lucid-admin-interface
    cluster: admin-interface
spec:
  replicas: 2
  selector:
    matchLabels:
      app: lucid-admin-interface
  template:
    metadata:
      labels:
        app: lucid-admin-interface
        cluster: admin-interface
    spec:
      serviceAccountName: lucid-admin-interface
      securityContext:
        runAsNonRoot: true
        runAsUser: 65534
        runAsGroup: 65534
        fsGroup: 65534
      containers:
      - name: admin-interface
        image: ghcr.io/hamigames/lucid/admin-interface:latest
        ports:
        - containerPort: 8096
          name: http
        env:
        - name: LUCID_ENV
          value: "production"
        - name: MONGO_URL
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: mongo-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: redis-url
        - name: TOR_PROXY_URL
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: tor-proxy-url
        - name: ADMIN_INTERFACE_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: admin-interface-secret-key
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: jwt-secret-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8096
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8096
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
        - name: admin-logs
          mountPath: /app/logs
        - name: admin-config
          mountPath: /app/config
        - name: ssl-certs
          mountPath: /etc/ssl/certs
          readOnly: true
      - name: beta-sidecar
        image: gcr.io/distroless/static-debian11
        command: ["/beta-sidecar"]
        volumeMounts:
        - name: beta-config
          mountPath: /etc/beta-sidecar
          readOnly: true
      volumes:
      - name: admin-logs
        emptyDir: {}
      - name: admin-config
        configMap:
          name: lucid-admin-interface-config
      - name: ssl-certs
        secret:
          secretName: lucid-ssl-certs
      - name: beta-config
        configMap:
          name: lucid-admin-interface-beta-config
---
apiVersion: v1
kind: Service
metadata:
  name: lucid-admin-interface-service
  namespace: lucid-system
  labels:
    app: lucid-admin-interface
spec:
  selector:
    app: lucid-admin-interface
  ports:
  - name: http
    port: 8096
    targetPort: 8096
    protocol: TCP
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: lucid-admin-interface-netpol
  namespace: lucid-system
spec:
  podSelector:
    matchLabels:
      app: lucid-admin-interface
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: lucid-admin
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: lucid-blockchain
  - to:
    - namespaceSelector:
        matchLabels:
          name: lucid-sessions
  - to:
    - namespaceSelector:
        matchLabels:
          name: lucid-rdp
  - to:
    - namespaceSelector:
        matchLabels:
          name: lucid-storage
```

#### Beta Sidecar Configuration
```yaml
# k8s/admin-interface-beta-sidecar.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lucid-admin-interface-beta-config
  namespace: lucid-system
data:
  config.yaml: |
    beta_sidecar:
      service_name: "admin-interface"
      cluster: "admin-interface"
      
      network_policies:
        - name: "admin-to-blockchain"
          action: "ALLOW"
          from: ["admin-interface"]
          to: ["blockchain-core"]
          ports: [8082]
          protocols: ["TCP"]
          
        - name: "admin-to-sessions"
          action: "ALLOW"
          from: ["admin-interface"]
          to: ["session-management"]
          ports: [8083]
          protocols: ["TCP"]
          
        - name: "admin-to-rdp"
          action: "ALLOW"
          from: ["admin-interface"]
          to: ["rdp-services"]
          ports: [8084]
          protocols: ["TCP"]
          
        - name: "admin-to-storage"
          action: "ALLOW"
          from: ["admin-interface"]
          to: ["storage-database"]
          ports: [8085]
          protocols: ["TCP"]
          
        - name: "deny-all-other"
          action: "DENY"
          from: ["*"]
          to: ["admin-interface"]
          ports: ["*"]
          protocols: ["*"]
      
      tls_config:
        cert_file: "/etc/ssl/certs/admin-interface.crt"
        key_file: "/etc/ssl/private/admin-interface.key"
        ca_file: "/etc/ssl/certs/lucid-ca.crt"
        verify_peer: true
        verify_hostname: true
        
      audit_logging:
        enabled: true
        log_level: "INFO"
        log_file: "/var/log/beta-sidecar/admin-interface.log"
        audit_file: "/var/log/beta-sidecar/admin-interface-audit.log"
        
      monitoring:
        enabled: true
        metrics_port: 9090
        health_check_interval: 30s
```

## Monitoring & Observability

### Health Checks

#### Application Health Monitoring
```python
# admin_interface/health/health_checker.py
import asyncio
import time
from typing import Dict, Any
from admin_interface.services.database import DatabaseService
from admin_interface.services.redis import RedisService
from admin_interface.services.blockchain import BlockchainService
from admin_interface.services.session import SessionService

class AdminInterfaceHealthChecker:
    def __init__(self):
        self.database_service = DatabaseService()
        self.redis_service = RedisService()
        self.blockchain_service = BlockchainService()
        self.session_service = SessionService()
        
    async def check_health(self) -> Dict[str, Any]:
        """Comprehensive health check for admin interface"""
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0",
            "checks": {}
        }
        
        # Check database connectivity
        db_health = await self._check_database()
        health_status["checks"]["database"] = db_health
        
        # Check Redis connectivity
        redis_health = await self._check_redis()
        health_status["checks"]["redis"] = redis_health
        
        # Check blockchain service connectivity
        blockchain_health = await self._check_blockchain()
        health_status["checks"]["blockchain"] = blockchain_health
        
        # Check session service connectivity
        session_health = await self._check_sessions()
        health_status["checks"]["sessions"] = session_health
        
        # Check system resources
        system_health = await self._check_system_resources()
        health_status["checks"]["system"] = system_health
        
        # Determine overall status
        all_healthy = all(
            check["status"] == "healthy" 
            for check in health_status["checks"].values()
        )
        
        if not all_healthy:
            health_status["status"] = "unhealthy"
        
        return health_status
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            await self.database_service.ping()
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "connection_pool": await self.database_service.get_connection_pool_status()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            start_time = time.time()
            await self.redis_service.ping()
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "memory_usage": await self.redis_service.get_memory_usage()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _check_blockchain(self) -> Dict[str, Any]:
        """Check blockchain service connectivity"""
        try:
            blockchain_status = await self.blockchain_service.get_status()
            return {
                "status": "healthy",
                "blockchain_height": blockchain_status.get("height"),
                "network_status": blockchain_status.get("network_status"),
                "consensus_status": blockchain_status.get("consensus_status")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _check_sessions(self) -> Dict[str, Any]:
        """Check session service connectivity"""
        try:
            session_stats = await self.session_service.get_statistics()
            return {
                "status": "healthy",
                "active_sessions": session_stats.get("active_sessions"),
                "total_sessions": session_stats.get("total_sessions"),
                "session_health": session_stats.get("health_status")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        import psutil
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy" if cpu_percent < 80 and memory.percent < 80 else "warning",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100,
                "available_memory_mb": memory.available // (1024 * 1024)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
```

### Metrics & Monitoring

#### Prometheus Metrics
```python
# admin_interface/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
import time

# Request metrics
admin_requests_total = Counter(
    'admin_requests_total',
    'Total admin interface requests',
    ['method', 'endpoint', 'status_code']
)

admin_request_duration = Histogram(
    'admin_request_duration_seconds',
    'Admin interface request duration',
    ['method', 'endpoint']
)

# Authentication metrics
admin_auth_attempts_total = Counter(
    'admin_auth_attempts_total',
    'Total admin authentication attempts',
    ['method', 'result']
)

admin_auth_duration = Histogram(
    'admin_auth_duration_seconds',
    'Admin authentication duration',
    ['method']
)

# Session management metrics
admin_sessions_managed_total = Counter(
    'admin_sessions_managed_total',
    'Total sessions managed by admin',
    ['action', 'result']
)

admin_bulk_operations_total = Counter(
    'admin_bulk_operations_total',
    'Total bulk operations performed',
    ['operation_type', 'result']
)

# Blockchain operations metrics
admin_blockchain_operations_total = Counter(
    'admin_blockchain_operations_total',
    'Total blockchain operations by admin',
    ['operation_type', 'result']
)

admin_anchoring_duration = Histogram(
    'admin_anchoring_duration_seconds',
    'Blockchain anchoring operation duration'
)

# System metrics
admin_active_connections = Gauge(
    'admin_active_connections',
    'Number of active admin connections'
)

admin_memory_usage = Gauge(
    'admin_memory_usage_bytes',
    'Admin interface memory usage'
)

admin_database_connections = Gauge(
    'admin_database_connections',
    'Number of active database connections'
)

# Version info
admin_version_info = Info(
    'admin_version_info',
    'Admin interface version information'
)

class AdminMetricsCollector:
    def __init__(self):
        self.start_time = time.time()
        
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        admin_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        admin_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_auth_attempt(self, method: str, success: bool, duration: float):
        """Record authentication attempt metrics"""
        result = "success" if success else "failure"
        admin_auth_attempts_total.labels(method=method, result=result).inc()
        admin_auth_duration.labels(method=method).observe(duration)
    
    def record_session_operation(self, action: str, success: bool, count: int = 1):
        """Record session management operation metrics"""
        result = "success" if success else "failure"
        admin_sessions_managed_total.labels(action=action, result=result).inc(count)
    
    def record_bulk_operation(self, operation_type: str, success: bool, count: int = 1):
        """Record bulk operation metrics"""
        result = "success" if success else "failure"
        admin_bulk_operations_total.labels(
            operation_type=operation_type,
            result=result
        ).inc(count)
    
    def record_blockchain_operation(self, operation_type: str, success: bool, duration: float = 0):
        """Record blockchain operation metrics"""
        result = "success" if success else "failure"
        admin_blockchain_operations_total.labels(
            operation_type=operation_type,
            result=result
        ).inc()
        
        if operation_type == "anchor_blocks":
            admin_anchoring_duration.observe(duration)
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        import psutil
        
        # Update memory usage
        memory = psutil.virtual_memory()
        admin_memory_usage.set(memory.used)
        
        # Update active connections
        connections = len(psutil.net_connections())
        admin_active_connections.set(connections)
        
        # Update database connections (mock for now)
        admin_database_connections.set(10)  # This would be actual DB connection count
```

### Logging Configuration

#### Structured Logging
```python
# admin_interface/logging/logger.py
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any

class AdminInterfaceLogger:
    def __init__(self, name: str = "admin_interface"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove default handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add structured JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)
        
        # Add file handler for audit logs
        audit_handler = logging.FileHandler('/app/logs/admin-audit.log')
        audit_handler.setFormatter(StructuredFormatter())
        audit_handler.addFilter(AuditFilter())
        self.logger.addHandler(audit_handler)
        
        # Add file handler for error logs
        error_handler = logging.FileHandler('/app/logs/admin-errors.log')
        error_handler.setFormatter(StructuredFormatter())
        error_handler.setLevel(logging.ERROR)
        self.logger.addHandler(error_handler)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with structured data"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def audit(self, event: str, admin_id: str, action: str, **kwargs):
        """Log audit event with structured data"""
        audit_data = {
            "event_type": "audit",
            "event": event,
            "admin_id": admin_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self._log(logging.INFO, f"Audit: {event}", **audit_data)
    
    def security(self, event: str, admin_id: str = None, **kwargs):
        """Log security event with structured data"""
        security_data = {
            "event_type": "security",
            "event": event,
            "admin_id": admin_id,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self._log(logging.WARNING, f"Security: {event}", **security_data)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method"""
        log_data = {
            "level": logging.getLevelName(level),
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "admin-interface",
            **kwargs
        }
        
        self.logger.log(level, json.dumps(log_data))

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        # Extract structured data from record
        if hasattr(record, 'structured_data'):
            return record.structured_data
        return record.getMessage()

class AuditFilter(logging.Filter):
    def filter(self, record):
        # Only allow audit events to pass through
        return hasattr(record, 'audit_event') and record.audit_event

# Global logger instance
admin_logger = AdminInterfaceLogger()
```

## Operational Procedures

### Deployment Procedures

#### Blue-Green Deployment
```bash
#!/bin/bash
# scripts/deploy/admin-interface-blue-green.sh

set -e

# Configuration
NAMESPACE="lucid-system"
SERVICE_NAME="lucid-admin-interface"
NEW_IMAGE_TAG="${1:-latest}"
CURRENT_COLOR=$(kubectl get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector.color}')

if [ "$CURRENT_COLOR" = "blue" ]; then
    NEW_COLOR="green"
    OLD_COLOR="blue"
else
    NEW_COLOR="blue"
    OLD_COLOR="green"
fi

echo "Deploying admin interface: $OLD_COLOR -> $NEW_COLOR"
echo "New image tag: $NEW_IMAGE_TAG"

# Deploy new version
kubectl set image deployment/$SERVICE_NAME-$NEW_COLOR \
    admin-interface=ghcr.io/hamigames/lucid/admin-interface:$NEW_IMAGE_TAG \
    -n $NAMESPACE

# Wait for rollout to complete
kubectl rollout status deployment/$SERVICE_NAME-$NEW_COLOR -n $NAMESPACE --timeout=300s

# Run health checks
echo "Running health checks..."
kubectl run health-check-$NEW_COLOR --rm -i --restart=Never \
    --image=curlimages/curl \
    -- curl -f http://$SERVICE_NAME-$NEW_COLOR:8096/health

if [ $? -eq 0 ]; then
    echo "Health checks passed. Switching traffic to $NEW_COLOR..."
    
    # Switch traffic to new version
    kubectl patch service $SERVICE_NAME -n $NAMESPACE -p '{"spec":{"selector":{"color":"'$NEW_COLOR'"}}}'
    
    # Wait for traffic to switch
    sleep 30
    
    # Verify traffic switch
    kubectl run traffic-check --rm -i --restart=Never \
        --image=curlimages/curl \
        -- curl -f http://$SERVICE_NAME:8096/health
    
    if [ $? -eq 0 ]; then
        echo "Traffic switch successful. Cleaning up $OLD_COLOR..."
        
        # Scale down old version
        kubectl scale deployment $SERVICE_NAME-$OLD_COLOR --replicas=0 -n $NAMESPACE
        
        echo "Blue-green deployment completed successfully!"
    else
        echo "Traffic switch failed. Rolling back..."
        kubectl patch service $SERVICE_NAME -n $NAMESPACE -p '{"spec":{"selector":{"color":"'$OLD_COLOR'"}}}'
        exit 1
    fi
else
    echo "Health checks failed. Rolling back..."
    kubectl rollout undo deployment/$SERVICE_NAME-$NEW_COLOR -n $NAMESPACE
    exit 1
fi
```

#### Rolling Update Deployment
```bash
#!/bin/bash
# scripts/deploy/admin-interface-rolling.sh

set -e

NAMESPACE="lucid-system"
DEPLOYMENT="lucid-admin-interface"
NEW_IMAGE_TAG="${1:-latest}"

echo "Starting rolling update for admin interface..."
echo "New image tag: $NEW_IMAGE_TAG"

# Update deployment
kubectl set image deployment/$DEPLOYMENT \
    admin-interface=ghcr.io/hamigames/lucid/admin-interface:$NEW_IMAGE_TAG \
    -n $NAMESPACE

# Wait for rollout to complete
kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE --timeout=600s

# Verify deployment
echo "Verifying deployment..."
kubectl get pods -l app=lucid-admin-interface -n $NAMESPACE

# Run post-deployment tests
echo "Running post-deployment tests..."
kubectl run post-deploy-test --rm -i --restart=Never \
    --image=curlimages/curl \
    -- curl -f http://lucid-admin-interface-service:8096/health

if [ $? -eq 0 ]; then
    echo "Rolling update completed successfully!"
else
    echo "Post-deployment tests failed. Rolling back..."
    kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE
    exit 1
fi
```

### Backup & Recovery

#### Configuration Backup
```bash
#!/bin/bash
# scripts/backup/admin-interface-backup.sh

set -e

BACKUP_DIR="/backups/admin-interface/$(date +%Y%m%d_%H%M%S)"
NAMESPACE="lucid-system"

echo "Starting admin interface backup..."

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup Kubernetes resources
echo "Backing up Kubernetes resources..."
kubectl get all -l app=lucid-admin-interface -n $NAMESPACE -o yaml > $BACKUP_DIR/k8s-resources.yaml

# Backup ConfigMaps
kubectl get configmaps -l app=lucid-admin-interface -n $NAMESPACE -o yaml > $BACKUP_DIR/configmaps.yaml

# Backup Secrets (excluding sensitive data)
kubectl get secrets -l app=lucid-admin-interface -n $NAMESPACE -o yaml | \
    sed 's/data:.*/data: [REDACTED]/' > $BACKUP_DIR/secrets.yaml

# Backup Persistent Volumes
echo "Backing up persistent volumes..."
kubectl get pv,pvc -l app=lucid-admin-interface -n $NAMESPACE -o yaml > $BACKUP_DIR/volumes.yaml

# Backup application logs
echo "Backing up application logs..."
kubectl logs -l app=lucid-admin-interface -n $NAMESPACE --previous > $BACKUP_DIR/previous-logs.log
kubectl logs -l app=lucid-admin-interface -n $NAMESPACE > $BACKUP_DIR/current-logs.log

# Create backup manifest
cat > $BACKUP_DIR/backup-manifest.json << EOF
{
    "backup_type": "admin-interface",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "namespace": "$NAMESPACE",
    "components": [
        "deployment",
        "service",
        "configmap",
        "secret",
        "persistentvolume",
        "persistentvolumeclaim",
        "logs"
    ],
    "backup_size": "$(du -sh $BACKUP_DIR | cut -f1)",
    "retention_days": 30
}
EOF

echo "Backup completed: $BACKUP_DIR"

# Cleanup old backups (keep last 30 days)
find /backups/admin-interface -type d -mtime +30 -exec rm -rf {} \;

echo "Old backups cleaned up."
```

#### Disaster Recovery
```bash
#!/bin/bash
# scripts/recovery/admin-interface-recovery.sh

set -e

BACKUP_PATH="${1}"
NAMESPACE="lucid-system"

if [ -z "$BACKUP_PATH" ]; then
    echo "Usage: $0 <backup_path>"
    echo "Available backups:"
    ls -la /backups/admin-interface/
    exit 1
fi

echo "Starting admin interface recovery from: $BACKUP_PATH"

# Verify backup exists
if [ ! -d "$BACKUP_PATH" ]; then
    echo "Backup path does not exist: $BACKUP_PATH"
    exit 1
fi

# Verify backup manifest
if [ ! -f "$BACKUP_PATH/backup-manifest.json" ]; then
    echo "Invalid backup: missing manifest file"
    exit 1
fi

echo "Verifying backup integrity..."
BACKUP_TIMESTAMP=$(cat $BACKUP_PATH/backup-manifest.json | jq -r '.timestamp')
echo "Backup timestamp: $BACKUP_TIMESTAMP"

# Stop current deployment
echo "Stopping current deployment..."
kubectl scale deployment lucid-admin-interface --replicas=0 -n $NAMESPACE

# Wait for pods to terminate
kubectl wait --for=delete pod -l app=lucid-admin-interface -n $NAMESPACE --timeout=300s

# Restore Kubernetes resources
echo "Restoring Kubernetes resources..."
kubectl apply -f $BACKUP_PATH/k8s-resources.yaml -n $NAMESPACE

# Restore ConfigMaps
echo "Restoring ConfigMaps..."
kubectl apply -f $BACKUP_PATH/configmaps.yaml -n $NAMESPACE

# Restore Secrets (manual intervention required)
echo "WARNING: Secrets restoration requires manual intervention"
echo "Please restore secrets manually from: $BACKUP_PATH/secrets.yaml"

# Restore Persistent Volumes
echo "Restoring Persistent Volumes..."
kubectl apply -f $BACKUP_PATH/volumes.yaml -n $NAMESPACE

# Wait for deployment to be ready
echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available deployment/lucid-admin-interface -n $NAMESPACE --timeout=600s

# Verify recovery
echo "Verifying recovery..."
kubectl run recovery-test --rm -i --restart=Never \
    --image=curlimages/curl \
    -- curl -f http://lucid-admin-interface-service:8096/health

if [ $? -eq 0 ]; then
    echo "Recovery completed successfully!"
else
    echo "Recovery verification failed!"
    exit 1
fi
```

### Monitoring & Alerting

#### Alert Rules
```yaml
# monitoring/admin-interface-alerts.yaml
groups:
- name: admin-interface
  rules:
  - alert: AdminInterfaceDown
    expr: up{job="admin-interface"} == 0
    for: 1m
    labels:
      severity: critical
      cluster: admin-interface
    annotations:
      summary: "Admin Interface is down"
      description: "Admin Interface has been down for more than 1 minute."
      
  - alert: AdminInterfaceHighErrorRate
    expr: rate(admin_requests_total{status_code=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
      cluster: admin-interface
    annotations:
      summary: "High error rate in Admin Interface"
      description: "Error rate is {{ $value }} errors per second."
      
  - alert: AdminInterfaceHighResponseTime
    expr: histogram_quantile(0.95, rate(admin_request_duration_seconds_bucket[5m])) > 2
    for: 3m
    labels:
      severity: warning
      cluster: admin-interface
    annotations:
      summary: "High response time in Admin Interface"
      description: "95th percentile response time is {{ $value }} seconds."
      
  - alert: AdminInterfaceHighMemoryUsage
    expr: admin_memory_usage_bytes / (1024^3) > 1.5
    for: 5m
    labels:
      severity: warning
      cluster: admin-interface
    annotations:
      summary: "High memory usage in Admin Interface"
      description: "Memory usage is {{ $value }} GB."
      
  - alert: AdminInterfaceDatabaseConnectionFailure
    expr: admin_database_connections == 0
    for: 1m
    labels:
      severity: critical
      cluster: admin-interface
    annotations:
      summary: "Database connection failure in Admin Interface"
      description: "No active database connections."
      
  - alert: AdminInterfaceFailedAuthAttempts
    expr: rate(admin_auth_attempts_total{result="failure"}[5m]) > 5
    for: 2m
    labels:
      severity: warning
      cluster: admin-interface
    annotations:
      summary: "High failed authentication attempts"
      description: "{{ $value }} failed auth attempts per second."
```

This comprehensive deployment and operations guide ensures the Admin Interface cluster can be reliably deployed, monitored, and maintained in production environments while maintaining security and performance standards.
