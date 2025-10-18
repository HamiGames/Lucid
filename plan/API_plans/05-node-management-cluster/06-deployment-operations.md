# Node Management Cluster Deployment & Operations

## Deployment Architecture Overview

The Node Management Cluster is deployed using Docker containers with distroless base images, following the Lucid project's security and operational standards. The deployment includes comprehensive monitoring, health checks, and operational procedures.

## Docker Deployment

### Multi-Stage Dockerfile
```dockerfile
# Multi-stage build for Node Management Service
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDKIT_INLINE_CACHE=1
ARG BUILDKIT_PROGRESS=plain
ARG VERSION=1.0.0

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY . .

# Build the application
RUN python -m compileall .

# Create non-root user
RUN useradd --create-home --shell /bin/bash lucid

# Production stage with distroless base
FROM gcr.io/distroless/python3-debian11

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /app /app

# Copy user from builder
COPY --from=builder /etc/passwd /etc/passwd

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV SERVICE_NAME=node-management-service
ENV VERSION=1.0.0

# Create necessary directories with proper permissions
USER root
RUN mkdir -p /app/logs /app/tmp /app/data && \
    chown -R lucid:lucid /app && \
    chmod -R 755 /app

# Switch to non-root user
USER lucid

# Expose port
EXPOSE 8083

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import requests; requests.get('http://localhost:8083/health')"]

# Run the application
ENTRYPOINT ["python", "main.py"]
```

### Docker Compose Configuration
```yaml
version: '3.8'

services:
  node-management:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        VERSION: ${VERSION:-1.0.0}
    image: ghcr.io/hamigames/lucid/node-management:${VERSION:-latest}
    container_name: lucid-node-management
    hostname: node-management
    
    environment:
      # Service configuration
      - SERVICE_NAME=node-management-service
      - VERSION=${VERSION:-1.0.0}
      - PORT=8083
      - ENVIRONMENT=${ENVIRONMENT:-production}
      
      # Database configuration
      - MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongo:27017/lucid?authSource=admin
      - MONGODB_DATABASE=lucid
      
      # Redis configuration
      - REDIS_URL=redis://lucid-redis:6379/0
      
      # Logging configuration
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_FORMAT=json
      
      # Security configuration
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      
      # Node management configuration
      - NODE_HEARTBEAT_INTERVAL=${NODE_HEARTBEAT_INTERVAL:-30}
      - RESOURCE_COLLECTION_INTERVAL=${RESOURCE_COLLECTION_INTERVAL:-60}
      - POOT_VALIDATION_TIMEOUT=${POOT_VALIDATION_TIMEOUT:-30}
      - PAYOUT_BATCH_SIZE=${PAYOUT_BATCH_SIZE:-100}
      
      # Rate limiting
      - RATE_LIMIT_ENABLED=${RATE_LIMIT_ENABLED:-true}
      - RATE_LIMIT_PER_MINUTE=${RATE_LIMIT_PER_MINUTE:-1000}
      
      # Security
      - TOR_ONLY=${TOR_ONLY:-true}
      - HARDWARE_VALIDATION_ENABLED=${HARDWARE_VALIDATION_ENABLED:-true}
      
    ports:
      - "8083:8083"
    
    volumes:
      # Configuration files
      - ./config/node-management.conf:/app/config/node-management.conf:ro
      
      # Logs (if needed for debugging)
      - node-management-logs:/app/logs
      
      # SSL certificates
      - ./ssl:/app/ssl:ro
    
    networks:
      - lucid-network
    
    depends_on:
      - lucid-mongo
      - lucid-redis
    
    restart: unless-stopped
    
    # Resource limits
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
    # Security configuration
    security_opt:
      - no-new-privileges:true
    
    read_only: true
    tmpfs:
      - /tmp
      - /app/logs
    
    # User configuration (non-root)
    user: "1000:1000"
    
    # Health check configuration
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8083/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  node-management-logs:
    driver: local

networks:
  lucid-network:
    external: true
```

### Kubernetes Deployment
```yaml
# node-management-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lucid-node-management
  namespace: lucid
  labels:
    app: node-management
    version: v1.0.0
    component: node-management-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: node-management
  template:
    metadata:
      labels:
        app: node-management
        version: v1.0.0
    spec:
      serviceAccountName: lucid-node-management
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: node-management
        image: ghcr.io/hamigames/lucid/node-management:1.0.0
        ports:
        - containerPort: 8083
          name: http
        env:
        - name: SERVICE_NAME
          value: "node-management-service"
        - name: VERSION
          value: "1.0.0"
        - name: PORT
          value: "8083"
        - name: ENVIRONMENT
          value: "production"
        - name: MONGODB_URL
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: mongodb-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: redis-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: jwt-secret-key
        - name: ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: lucid-secrets
              key: encryption-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8083
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8083
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: logs
          mountPath: /app/logs
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config
        configMap:
          name: node-management-config
      - name: logs
        emptyDir: {}
      - name: tmp
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: lucid-node-management
  namespace: lucid
  labels:
    app: node-management
spec:
  selector:
    app: node-management
  ports:
  - port: 8083
    targetPort: 8083
    name: http
  type: ClusterIP

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: lucid-node-management
  namespace: lucid
automountServiceAccountToken: false
```

## Health Checks & Monitoring

### Comprehensive Health Check Implementation
```python
# health_checker.py
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import psutil
import requests

from node.config.database import get_database
from node.resources.resource_monitor import ResourceMonitor
from node.config.settings import settings

logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self, app: FastAPI):
        self.app = app
        self.db = get_database()
        self.resource_monitor = ResourceMonitor()
        self.start_time = datetime.utcnow()
        
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.version,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "checks": {}
        }
        
        # Check database connectivity
        db_status = await self._check_database()
        health_status["checks"]["database"] = db_status
        
        # Check resource monitoring
        resource_status = await self._check_resource_monitoring()
        health_status["checks"]["resource_monitoring"] = resource_status
        
        # Check Redis connectivity
        redis_status = await self._check_redis()
        health_status["checks"]["redis"] = redis_status
        
        # Check node connectivity
        node_status = await self._check_node_connectivity()
        health_status["checks"]["nodes"] = node_status
        
        # Check system resources
        system_status = await self._check_system_resources()
        health_status["checks"]["system_resources"] = system_status
        
        # Check external dependencies
        external_status = await self._check_external_dependencies()
        health_status["checks"]["external_dependencies"] = external_status
        
        # Determine overall status
        critical_checks = ["database", "redis", "nodes"]
        critical_healthy = all(
            health_status["checks"][check]["status"] == "healthy" 
            for check in critical_checks
        )
        
        if not critical_healthy:
            health_status["status"] = "unhealthy"
        elif any(
            health_status["checks"][check]["status"] == "degraded" 
            for check in health_status["checks"]
        ):
            health_status["status"] = "degraded"
        
        return health_status
    
    async def check_readiness(self) -> Dict[str, Any]:
        """Check if service is ready to accept traffic."""
        readiness_status = {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check database readiness
        db_ready = await self._check_database_readiness()
        readiness_status["checks"]["database"] = db_ready
        
        # Check Redis readiness
        redis_ready = await self._check_redis_readiness()
        readiness_status["checks"]["redis"] = redis_ready
        
        # Check resource monitor readiness
        monitor_ready = await self._check_resource_monitor_readiness()
        readiness_status["checks"]["resource_monitor"] = monitor_ready
        
        # Determine overall readiness
        all_ready = all(
            check["status"] == "ready" 
            for check in readiness_status["checks"].values()
        )
        
        if not all_ready:
            readiness_status["status"] = "not_ready"
        
        return readiness_status
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start_time = datetime.utcnow()
            
            # Test database connection
            await self.db.command("ping")
            
            # Test collection access
            nodes_collection = self.db.nodes
            await nodes_collection.find_one()
            
            # Test write performance
            test_doc = {"_test": datetime.utcnow()}
            await nodes_collection.insert_one(test_doc)
            await nodes_collection.delete_one({"_test": {"$exists": True}})
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "response_time_ms": response_time * 1000,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_resource_monitoring(self) -> Dict[str, Any]:
        """Check resource monitoring system."""
        try:
            # Test resource monitor
            is_running = await self.resource_monitor.is_running()
            
            if is_running:
                # Check if monitoring is collecting data
                recent_metrics = await self.resource_monitor.get_recent_metrics(limit=1)
                
                if recent_metrics:
                    return {
                        "status": "healthy",
                        "message": "Resource monitoring active with data collection",
                        "last_metric_time": recent_metrics[0]["timestamp"].isoformat(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "status": "degraded",
                        "message": "Resource monitoring active but no recent data",
                        "timestamp": datetime.utcnow().isoformat()
                    }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Resource monitoring inactive",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Resource monitoring health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Resource monitoring failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        try:
            import redis.asyncio as redis
            
            start_time = datetime.utcnow()
            
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            
            # Test write/read performance
            test_key = f"health_check_{int(datetime.utcnow().timestamp())}"
            await redis_client.set(test_key, "test_value", ex=60)
            value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            if value == b"test_value":
                await redis_client.close()
                return {
                    "status": "healthy",
                    "message": "Redis connection and operations successful",
                    "response_time_ms": response_time * 1000,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                await redis_client.close()
                return {
                    "status": "degraded",
                    "message": "Redis connection successful but read/write operations failed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Redis connection failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_node_connectivity(self) -> Dict[str, Any]:
        """Check connectivity to managed nodes."""
        try:
            # Get active nodes
            nodes_collection = self.db.nodes
            active_nodes = await nodes_collection.find(
                {"status": "active"}
            ).to_list(100)
            
            # Check heartbeat status
            now = datetime.utcnow()
            healthy_nodes = 0
            total_nodes = len(active_nodes)
            node_details = []
            
            for node in active_nodes:
                node_id = node["node_id"]
                if node.get("last_heartbeat"):
                    heartbeat_age = (now - node["last_heartbeat"]).total_seconds()
                    is_healthy = heartbeat_age < 300  # 5 minutes
                    if is_healthy:
                        healthy_nodes += 1
                    
                    node_details.append({
                        "node_id": node_id,
                        "heartbeat_age_seconds": heartbeat_age,
                        "healthy": is_healthy
                    })
            
            health_ratio = healthy_nodes / total_nodes if total_nodes > 0 else 1.0
            
            if health_ratio >= 0.8:  # 80% of nodes healthy
                status = "healthy"
                message = f"{healthy_nodes}/{total_nodes} nodes healthy"
            elif health_ratio >= 0.5:  # 50% of nodes healthy
                status = "degraded"
                message = f"Only {healthy_nodes}/{total_nodes} nodes healthy"
            else:
                status = "unhealthy"
                message = f"Critical: Only {healthy_nodes}/{total_nodes} nodes healthy"
            
            return {
                "status": status,
                "message": message,
                "healthy_nodes": healthy_nodes,
                "total_nodes": total_nodes,
                "health_ratio": health_ratio,
                "node_details": node_details,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Node connectivity health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Node connectivity check failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            # Get system resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check for resource issues
            issues = []
            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent}%")
            if memory.percent > 90:
                issues.append(f"High memory usage: {memory.percent}%")
            if disk.percent > 90:
                issues.append(f"High disk usage: {disk.percent}%")
            
            if issues:
                status = "degraded"
                message = f"Resource issues detected: {'; '.join(issues)}"
            else:
                status = "healthy"
                message = "System resources within normal limits"
            
            return {
                "status": status,
                "message": message,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "issues": issues,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System resources health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"System resources check failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_external_dependencies(self) -> Dict[str, Any]:
        """Check external service dependencies."""
        dependencies = [
            {
                "name": "blockchain_core",
                "url": "http://blockchain-core:8084/health",
                "timeout": 5
            },
            {
                "name": "session_management",
                "url": "http://session-management:8082/health",
                "timeout": 5
            },
            {
                "name": "api_gateway",
                "url": "http://api-gateway:8080/health",
                "timeout": 5
            }
        ]
        
        dependency_status = {}
        overall_status = "healthy"
        
        for dep in dependencies:
            try:
                response = requests.get(
                    dep["url"], 
                    timeout=dep["timeout"],
                    headers={"User-Agent": "lucid-node-management/health-check"}
                )
                
                if response.status_code == 200:
                    dependency_status[dep["name"]] = {
                        "status": "healthy",
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                else:
                    dependency_status[dep["name"]] = {
                        "status": "degraded",
                        "message": f"HTTP {response.status_code}"
                    }
                    overall_status = "degraded"
                    
            except Exception as e:
                dependency_status[dep["name"]] = {
                    "status": "unhealthy",
                    "message": str(e)
                }
                overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "dependencies": dependency_status,
            "timestamp": datetime.utcnow().isoformat()
        }
```

### Health Check Endpoints
```python
# health_routes.py
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from health_checker import HealthChecker

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/", response_model=Dict[str, Any])
async def health_check():
    """Comprehensive health check endpoint."""
    health_checker = HealthChecker(app)
    health_status = await health_checker.check_health()
    
    status_code = status.HTTP_200_OK
    if health_status["status"] == "unhealthy":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif health_status["status"] == "degraded":
        status_code = status.HTTP_206_PARTIAL_CONTENT
    
    return JSONResponse(
        status_code=status_code,
        content=health_status
    )

@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check():
    """Readiness check endpoint for Kubernetes."""
    health_checker = HealthChecker(app)
    readiness_status = await health_checker.check_readiness()
    
    status_code = status.HTTP_200_OK
    if readiness_status["status"] != "ready":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content=readiness_status
    )

@router.get("/live", response_model=Dict[str, Any])
async def liveness_check():
    """Liveness check endpoint for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version
    }
```

## Monitoring & Observability

### Prometheus Metrics
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
import time
from functools import wraps

# Service metrics
service_info = Info('lucid_node_management_info', 'Node Management Service Information')
service_info.info({
    'version': '1.0.0',
    'service': 'node-management',
    'environment': 'production'
})

# Request metrics
http_requests_total = Counter(
    'lucid_node_management_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration = Histogram(
    'lucid_node_management_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Node metrics
active_nodes = Gauge(
    'lucid_node_management_active_nodes_total',
    'Number of active nodes'
)

node_operations_total = Counter(
    'lucid_node_management_node_operations_total',
    'Total node operations',
    ['operation', 'status']
)

# PoOT metrics
poot_validations_total = Counter(
    'lucid_node_management_poot_validations_total',
    'Total PoOT validations',
    ['node_id', 'status']
)

poot_validation_duration = Histogram(
    'lucid_node_management_poot_validation_duration_seconds',
    'PoOT validation duration in seconds',
    ['node_id']
)

poot_scores = Histogram(
    'lucid_node_management_poot_scores',
    'PoOT scores distribution',
    ['node_id']
)

# Payout metrics
payouts_total = Counter(
    'lucid_node_management_payouts_total',
    'Total payouts processed',
    ['currency', 'status']
)

payout_amounts = Histogram(
    'lucid_node_management_payout_amounts',
    'Payout amounts distribution',
    ['currency']
)

# Resource metrics
resource_usage = Gauge(
    'lucid_node_management_resource_usage',
    'Resource usage metrics',
    ['node_id', 'resource_type', 'unit']
)

# Database metrics
database_operations_total = Counter(
    'lucid_node_management_database_operations_total',
    'Total database operations',
    ['operation', 'collection', 'status']
)

database_operation_duration = Histogram(
    'lucid_node_management_database_operation_duration_seconds',
    'Database operation duration in seconds',
    ['operation', 'collection']
)

# Redis metrics
redis_operations_total = Counter(
    'lucid_node_management_redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)

redis_operation_duration = Histogram(
    'lucid_node_management_redis_operation_duration_seconds',
    'Redis operation duration in seconds',
    ['operation']
)

def track_http_request(method: str, endpoint: str):
    """Decorator to track HTTP requests."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                status_code = getattr(result, 'status_code', 200)
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).inc()
                
                return result
                
            except Exception as e:
                status_code = getattr(e, 'status_code', 500)
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).inc()
                raise
                
            finally:
                duration = time.time() - start_time
                http_request_duration.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
        
        return wrapper
    return decorator

def track_database_operation(operation: str, collection: str):
    """Decorator to track database operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                database_operations_total.labels(
                    operation=operation,
                    collection=collection,
                    status='success'
                ).inc()
                
                return result
                
            except Exception as e:
                database_operations_total.labels(
                    operation=operation,
                    collection=collection,
                    status='error'
                ).inc()
                raise
                
            finally:
                duration = time.time() - start_time
                database_operation_duration.labels(
                    operation=operation,
                    collection=collection
                ).observe(duration)
        
        return wrapper
    return decorator

# Start Prometheus metrics server
def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics server."""
    start_http_server(port)
    logger.info(f"Prometheus metrics server started on port {port}")
```

### Logging Configuration
```python
# logging_config.py
import logging
import logging.config
import sys
from datetime import datetime
import json
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "service": "node-management",
            "version": "1.0.0"
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)

class StructuredLogger:
    """Structured logger with context support."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_with_context(
        self, 
        level: int, 
        message: str, 
        extra_fields: Dict[str, Any] = None
    ):
        """Log message with additional context."""
        if extra_fields:
            # Create new record with extra fields
            record = self.logger.makeRecord(
                self.logger.name, level, "", 0, message, (), None
            )
            record.extra_fields = extra_fields
            self.logger.handle(record)
        else:
            self.logger.log(level, message)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, kwargs)

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": JSONFormatter,
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "json",
            "stream": sys.stdout
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "/app/logs/node-management.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "": {  # Root logger
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "node": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        }
    }
}

def setup_logging():
    """Setup logging configuration."""
    logging.config.dictConfig(LOGGING_CONFIG)
    
    # Create structured logger instances
    logger = StructuredLogger("node-management")
    logger.info("Logging configured", component="logging")
    
    return logger
```

## Operational Procedures

### Deployment Procedures

#### Blue-Green Deployment Script
```bash
#!/bin/bash
# blue-green-deployment.sh

set -e

# Configuration
SERVICE_NAME="node-management"
CURRENT_VERSION="1.0.0"
NEW_VERSION="1.1.0"
NAMESPACE="lucid"
HEALTH_CHECK_URL="http://node-management:8083/health"
MAX_WAIT_TIME=300  # 5 minutes

echo "Starting blue-green deployment for $SERVICE_NAME"

# Function to check service health
check_health() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    echo "Checking health at $url"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "Health check passed on attempt $attempt"
            return 0
        fi
        
        echo "Health check failed on attempt $attempt, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    echo "Health check failed after $max_attempts attempts"
    return 1
}

# Function to wait for rollout
wait_for_rollout() {
    local deployment=$1
    local namespace=$2
    
    echo "Waiting for deployment $deployment to rollout..."
    kubectl rollout status deployment/$deployment -n $namespace --timeout=$MAX_WAIT_TIME
}

# Step 1: Deploy new version (green)
echo "Step 1: Deploying new version $NEW_VERSION"
kubectl set image deployment/$SERVICE_NAME node-management=ghcr.io/hamigames/lucid/node-management:$NEW_VERSION -n $NAMESPACE

# Step 2: Wait for rollout
echo "Step 2: Waiting for rollout to complete"
wait_for_rollout $SERVICE_NAME $NAMESPACE

# Step 3: Health check new version
echo "Step 3: Performing health check on new version"
if ! check_health $HEALTH_CHECK_URL; then
    echo "Health check failed, rolling back..."
    kubectl rollout undo deployment/$SERVICE_NAME -n $NAMESPACE
    exit 1
fi

# Step 4: Verify metrics and logs
echo "Step 4: Verifying metrics and logs"
kubectl logs deployment/$SERVICE_NAME -n $NAMESPACE --tail=100 | grep -i error || echo "No errors found in logs"

# Step 5: Update service labels
echo "Step 5: Deployment completed successfully"
kubectl label deployment $SERVICE_NAME version=$NEW_VERSION -n $NAMESPACE --overwrite

echo "Blue-green deployment completed successfully"
```

#### Rollback Script
```bash
#!/bin/bash
# rollback.sh

set -e

SERVICE_NAME="node-management"
NAMESPACE="lucid"
HEALTH_CHECK_URL="http://node-management:8083/health"

echo "Starting rollback for $SERVICE_NAME"

# Rollback deployment
echo "Rolling back deployment..."
kubectl rollout undo deployment/$SERVICE_NAME -n $NAMESPACE

# Wait for rollout
echo "Waiting for rollback to complete..."
kubectl rollout status deployment/$SERVICE_NAME -n $NAMESPACE --timeout=300

# Health check
echo "Performing health check..."
if curl -f -s "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
    echo "Rollback completed successfully"
    exit 0
else
    echo "Rollback health check failed"
    exit 1
fi
```

### Backup & Recovery Procedures

#### Database Backup Script
```bash
#!/bin/bash
# backup-database.sh

set -e

# Configuration
MONGODB_HOST="lucid-mongo"
MONGODB_PORT="27017"
MONGODB_DATABASE="lucid"
MONGODB_USER="lucid"
BACKUP_DIR="/backups/mongodb"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Generate backup filename
BACKUP_FILE="$BACKUP_DIR/lucid_backup_$(date +%Y%m%d_%H%M%S).tar.gz"

echo "Starting database backup..."

# Create backup
mongodump \
    --host $MONGODB_HOST:$MONGODB_PORT \
    --db $MONGODB_DATABASE \
    --username $MONGODB_USER \
    --authenticationDatabase admin \
    --out /tmp/lucid_backup

# Compress backup
tar -czf $BACKUP_FILE -C /tmp lucid_backup

# Cleanup temp directory
rm -rf /tmp/lucid_backup

# Verify backup
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    echo "Backup completed successfully: $BACKUP_FILE"
    
    # Get backup size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup size: $BACKUP_SIZE"
    
    # Cleanup old backups
    find $BACKUP_DIR -name "lucid_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
    echo "Cleaned up backups older than $RETENTION_DAYS days"
    
else
    echo "Backup failed or file is empty"
    exit 1
fi
```

#### Database Recovery Script
```bash
#!/bin/bash
# restore-database.sh

set -e

# Configuration
MONGODB_HOST="lucid-mongo"
MONGODB_PORT="27017"
MONGODB_DATABASE="lucid"
MONGODB_USER="lucid"
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Starting database restore from $BACKUP_FILE"

# Extract backup
echo "Extracting backup..."
tar -xzf "$BACKUP_FILE" -C /tmp

# Get extracted directory
EXTRACTED_DIR=$(find /tmp -name "lucid_backup" -type d | head -1)

if [ -z "$EXTRACTED_DIR" ]; then
    echo "Could not find extracted backup directory"
    exit 1
fi

# Restore database
echo "Restoring database..."
mongorestore \
    --host $MONGODB_HOST:$MONGODB_PORT \
    --db $MONGODB_DATABASE \
    --username $MONGODB_USER \
    --authenticationDatabase admin \
    --drop \
    "$EXTRACTED_DIR/lucid"

# Cleanup
rm -rf /tmp/lucid_backup

echo "Database restore completed successfully"
```

### Troubleshooting Procedures

#### Common Issues & Solutions

##### Issue 1: Node Management Service Not Starting
```bash
# Check container logs
kubectl logs deployment/node-management -n lucid --tail=100

# Check pod status
kubectl get pods -n lucid -l app=node-management

# Check events
kubectl describe pod -n lucid -l app=node-management

# Common causes:
# 1. Database connection issues
# 2. Missing environment variables
# 3. Resource constraints
# 4. Configuration errors
```

##### Issue 2: High Memory Usage
```bash
# Check memory usage
kubectl top pods -n lucid -l app=node-management

# Check memory limits
kubectl describe pod -n lucid -l app=node-management | grep -A 5 "Limits:"

# Check for memory leaks
kubectl exec -it -n lucid deployment/node-management -- python -c "
import psutil
import gc
print('Memory usage:', psutil.virtual_memory().percent)
print('GC counts:', gc.get_count())
gc.collect()
print('After GC:', psutil.virtual_memory().percent)
"

# Solutions:
# 1. Increase memory limits
# 2. Restart service
# 3. Check for memory leaks in code
# 4. Optimize database queries
```

##### Issue 3: Database Connection Issues
```bash
# Test database connectivity
kubectl exec -it -n lucid deployment/node-management -- python -c "
import asyncio
import motor.motor_asyncio
import os

async def test_db():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGODB_URL'))
    try:
        await client.admin.command('ping')
        print('Database connection successful')
    except Exception as e:
        print(f'Database connection failed: {e}')
    finally:
        client.close()

asyncio.run(test_db())
"

# Check MongoDB status
kubectl get pods -n lucid -l app=mongodb

# Check MongoDB logs
kubectl logs -n lucid -l app=mongodb --tail=50

# Solutions:
# 1. Check MongoDB service status
# 2. Verify connection string
# 3. Check network connectivity
# 4. Verify credentials
```

##### Issue 4: PoOT Validation Failures
```bash
# Check PoOT validation logs
kubectl logs deployment/node-management -n lucid --tail=100 | grep -i "poot"

# Check PoOT metrics
kubectl exec -it -n lucid deployment/node-management -- curl -s http://localhost:9090/metrics | grep poot

# Check node status
kubectl exec -it -n lucid deployment/node-management -- python -c "
import asyncio
from node.config.database import get_database

async def check_nodes():
    db = get_database()
    nodes = await db.nodes.find({'status': 'active'}).to_list(100)
    print(f'Active nodes: {len(nodes)}')
    for node in nodes:
        print(f'Node {node[\"node_id\"]}: status={node[\"status\"]}, heartbeat={node.get(\"last_heartbeat\")}')

asyncio.run(check_nodes())
"

# Solutions:
# 1. Check node connectivity
# 2. Verify PoOT calculation logic
# 3. Check for timestamp issues
# 4. Validate input data
```

#### Monitoring & Alerting Setup

##### Prometheus Alert Rules
```yaml
# node-management-alerts.yaml
groups:
- name: node-management
  rules:
  - alert: NodeManagementDown
    expr: up{job="node-management"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Node Management service is down"
      description: "Node Management service has been down for more than 1 minute"

  - alert: HighErrorRate
    expr: rate(lucid_node_management_http_requests_total{status_code=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in Node Management"
      description: "Error rate is {{ $value }} errors per second"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(lucid_node_management_http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time in Node Management"
      description: "95th percentile response time is {{ $value }} seconds"

  - alert: LowNodeHealth
    expr: lucid_node_management_active_nodes_total < 5
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Low number of healthy nodes"
      description: "Only {{ $value }} nodes are healthy"

  - alert: PoOTValidationFailures
    expr: rate(lucid_node_management_poot_validations_total{status="failed"}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High PoOT validation failure rate"
      description: "PoOT validation failure rate is {{ $value }} failures per second"

  - alert: HighMemoryUsage
    expr: lucid_node_management_resource_usage{resource_type="memory"} > 0.9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value }}% on node {{ $labels.node_id }}"

  - alert: DatabaseConnectionIssues
    expr: rate(lucid_node_management_database_operations_total{status="error"}[5m]) > 0.05
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Database connection issues"
      description: "Database error rate is {{ $value }} errors per second"
```

##### Grafana Dashboard Configuration
```json
{
  "dashboard": {
    "title": "Node Management Cluster",
    "panels": [
      {
        "title": "Service Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"node-management\"}",
            "legendFormat": "Service Status"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(lucid_node_management_http_requests_total[5m])",
            "legendFormat": "{{ method }} {{ endpoint }}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(lucid_node_management_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Active Nodes",
        "type": "graph",
        "targets": [
          {
            "expr": "lucid_node_management_active_nodes_total",
            "legendFormat": "Active Nodes"
          }
        ]
      },
      {
        "title": "PoOT Validations",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(lucid_node_management_poot_validations_total[5m])",
            "legendFormat": "{{ status }}"
          }
        ]
      },
      {
        "title": "Resource Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "lucid_node_management_resource_usage",
            "legendFormat": "{{ node_id }} {{ resource_type }}"
          }
        ]
      }
    ]
  }
}
```

This comprehensive deployment and operations document provides complete guidance for deploying, monitoring, and maintaining the Node Management Cluster with proper health checks, monitoring, and troubleshooting procedures following the Lucid project standards.
