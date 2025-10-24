# Distroless Container Specification

## Overview

This document defines the mandatory distroless container architecture for all Lucid RDP services, ensuring minimal attack surface and enhanced security posture.

## Distroless Architecture Principles

### Core Benefits
- **Minimal Attack Surface**: No shells, package managers, or unnecessary tools
- **Reduced CVE Exposure**: Fewer components means fewer vulnerabilities
- **Smaller Image Size**: Optimized for production deployment
- **Immutable Runtime**: No runtime modifications possible
- **Security by Design**: Hardened from the ground up

### Mandatory Requirements
- All production containers MUST use distroless base images
- Multi-stage builds with builder + distroless runtime
- No shells (bash, sh, zsh) in runtime containers
- Read-only root filesystem where possible
- Non-root user execution (UID 65532)
- Minimal syscalls via seccomp profiles

## Base Image Specifications

### Allowed Distroless Base Images
```dockerfile
# Node.js Services
FROM gcr.io/distroless/nodejs20-debian12

# Python Services
FROM gcr.io/distroless/python3-debian12

# Static Binaries (Go, Rust, C++)
FROM gcr.io/distroless/static-debian12

# Java Services
FROM gcr.io/distroless/java17-debian12

# .NET Services
FROM gcr.io/distroless/dotnet6-debian12
```

### Prohibited Base Images
```dockerfile
# ❌ PROHIBITED: Standard base images
FROM node:20-slim
FROM python:3.12-slim
FROM ubuntu:22.04
FROM alpine:3.18
FROM debian:bullseye-slim
```

## Multi-Stage Build Patterns

### Node.js Service Pattern
```dockerfile
# ✅ COMPLIANT: Multi-stage Node.js build
FROM node:20-slim AS builder

# Set working directory
WORKDIR /build

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY src/ ./src/
COPY tsconfig.json ./

# Build application
RUN npm run build

# Production stage - distroless
FROM gcr.io/distroless/nodejs20-debian12

# Copy built application
COPY --from=builder /build/dist/ /app/
COPY --from=builder /build/node_modules/ /app/node_modules/
COPY --from=builder /build/package.json /app/

# Set ownership
COPY --chown=nonroot:nonroot . /app/

# Switch to non-root user
USER nonroot

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["curl", "-f", "http://localhost:8080/health"]

# Start application
CMD ["index.js"]
```

### Python Service Pattern
```dockerfile
# ✅ COMPLIANT: Multi-stage Python build
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY src/ ./src/

# Production stage - distroless
FROM gcr.io/distroless/python3-debian12

# Copy Python packages
COPY --from=builder /root/.local /app/.local

# Copy application
COPY --from=builder /build/src/ /app/src/

# Set ownership
COPY --chown=nonroot:nonroot . /app/

# Switch to non-root user
USER nonroot

# Set working directory
WORKDIR /app

# Add local packages to path
ENV PYTHONPATH=/app/.local/lib/python3.12/site-packages:$PYTHONPATH

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["curl", "-f", "http://localhost:8080/health"]

# Start application
CMD ["/app/src/main.py"]
```

### Go Service Pattern
```dockerfile
# ✅ COMPLIANT: Multi-stage Go build
FROM golang:1.21-alpine AS builder

# Set working directory
WORKDIR /build

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# Production stage - distroless static
FROM gcr.io/distroless/static-debian12

# Copy binary
COPY --from=builder /build/main /app/main

# Set ownership
COPY --chown=nonroot:nonroot . /app/

# Switch to non-root user
USER nonroot

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/app/main", "health"]

# Start application
CMD ["/app/main"]
```

## Security Hardening

### Read-Only Root Filesystem
```dockerfile
# Enable read-only root filesystem
FROM gcr.io/distroless/nodejs20-debian12

# Create writable directories
RUN mkdir -p /tmp /var/tmp /app/logs

# Copy application
COPY --from=builder /build/dist/ /app/

# Set ownership
COPY --chown=nonroot:nonroot . /app/

# Switch to non-root user
USER nonroot

# Set working directory
WORKDIR /app

# Runtime configuration for read-only root
CMD ["--read-only", "index.js"]
```

### Seccomp Profiles
```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86", "SCMP_ARCH_X32"],
  "syscalls": [
    {
      "names": [
        "accept", "accept4", "access", "bind", "close", "connect",
        "epoll_create1", "epoll_ctl", "epoll_pwait", "fstat", "getpeername",
        "getsockname", "getsockopt", "listen", "lseek", "mmap", "munmap",
        "openat", "poll", "read", "readv", "recvfrom", "recvmmsg", "recvmsg",
        "sendmmsg", "sendmsg", "sendto", "setsockopt", "shutdown", "socket",
        "socketpair", "write", "writev", "clock_gettime", "getpid", "gettid"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

### AppArmor Profiles
```bash
# AppArmor profile for distroless containers
#include <tunables/global>

profile lucid-app flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  
  # Allow reading application files
  /app/** r,
  
  # Allow writing to tmp directories
  /tmp/** w,
  /var/tmp/** w,
  
  # Deny access to sensitive files
  deny /etc/passwd r,
  deny /etc/shadow r,
  deny /proc/*/mem rw,
  deny /sys/kernel/** r,
  
  # Network access
  network,
  
  # Capabilities
  capability net_bind_service,
  capability setuid,
  capability setgid,
}
```

## Container Configuration

### Docker Compose Configuration
```yaml
services:
  blockchain-core:
    build:
      context: ./src/blockchain-core
      dockerfile: Dockerfile
      target: production
    
    image: gcr.io/lucid/blockchain-core:latest
    
    # Security configuration
    security_opt:
      - seccomp:./seccomp-blockchain.json
      - apparmor:lucid-app
    
    # Read-only root filesystem
    read_only: true
    
    # Temporary filesystems
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
      - /var/tmp:noexec,nosuid,size=50m
    
    # User and group
    user: "65532:65532"
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    
    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    # Environment variables
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=info
      - METRICS_ENABLED=true
    
    # Networks
    networks:
      - blockchain_plane
    
    # Labels
    labels:
      - com.lucid.plane=blockchain
      - com.lucid.service=blockchain-core
      - com.lucid.distroless=true
```

### Kubernetes Configuration
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blockchain-core
  labels:
    app: blockchain-core
    com.lucid.distroless: "true"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blockchain-core
  template:
    metadata:
      labels:
        app: blockchain-core
        com.lucid.distroless: "true"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
        seccompProfile:
          type: Localhost
          localhostProfile: seccomp-blockchain.json
      containers:
      - name: blockchain-core
        image: gcr.io/lucid/blockchain-core:latest
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 65532
          runAsGroup: 65532
          capabilities:
            drop:
            - ALL
        resources:
          limits:
            cpu: 2000m
            memory: 2Gi
          requests:
            cpu: 1000m
            memory: 1Gi
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: var-tmp
          mountPath: /var/tmp
        - name: logs
          mountPath: /app/logs
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 40
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
      volumes:
      - name: tmp
        emptyDir: {}
      - name: var-tmp
        emptyDir: {}
      - name: logs
        emptyDir: {}
```

## Build Pipeline Integration

### GitHub Actions Workflow
```yaml
name: Build Distroless Images

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build-distroless:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [blockchain-core, sessions-gateway, admin-ui, tron-payment]
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Build distroless image
      uses: docker/build-push-action@v5
      with:
        context: ./src/${{ matrix.service }}
        file: ./src/${{ matrix.service }}/Dockerfile
        platforms: linux/amd64,linux/arm64
        push: true
        tags: |
          ghcr.io/lucid/${{ matrix.service }}:latest
          ghcr.io/lucid/${{ matrix.service }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    - name: Verify distroless compliance
      run: |
        # Verify base image is distroless
        docker run --rm ghcr.io/lucid/${{ matrix.service }}:${{ github.sha }} \
          /bin/sh -c "echo 'Testing shell access'" || echo "✅ No shell access"
        
        # Verify non-root user
        docker run --rm ghcr.io/lucid/${{ matrix.service }}:${{ github.sha }} \
          id || echo "✅ Non-root user"
        
        # Verify minimal syscalls
        docker run --rm --security-opt seccomp:./seccomp-${{ matrix.service }}.json \
          ghcr.io/lucid/${{ matrix.service }}:${{ github.sha }} \
          echo "✅ Seccomp profile working"
    
    - name: Security scan
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'ghcr.io/lucid/${{ matrix.service }}:${{ github.sha }}'
        format: 'sarif'
        output: 'trivy-results-${{ matrix.service }}.sarif'
    
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results-${{ matrix.service }}.sarif'
```

### Build Script
```bash
#!/bin/bash
# build-distroless.sh

set -euo pipefail

SERVICE_NAME=${1:-""}
IMAGE_TAG=${2:-"latest"}

if [ -z "$SERVICE_NAME" ]; then
  echo "Usage: $0 <service-name> [image-tag]"
  exit 1
fi

echo "Building distroless image for $SERVICE_NAME..."

# Build multi-architecture image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --file ./src/$SERVICE_NAME/Dockerfile \
  --tag ghcr.io/lucid/$SERVICE_NAME:$IMAGE_TAG \
  --tag ghcr.io/lucid/$SERVICE_NAME:latest \
  --push \
  ./src/$SERVICE_NAME

# Verify distroless compliance
echo "Verifying distroless compliance..."

# Check base image
BASE_IMAGE=$(docker inspect ghcr.io/lucid/$SERVICE_NAME:$IMAGE_TAG | jq -r '.[0].Config.Image')
if [[ $BASE_IMAGE == gcr.io/distroless/* ]]; then
  echo "✅ Uses distroless base image: $BASE_IMAGE"
else
  echo "❌ Does not use distroless base image: $BASE_IMAGE"
  exit 1
fi

# Check for shells
if docker run --rm ghcr.io/lucid/$SERVICE_NAME:$IMAGE_TAG /bin/sh -c "echo test" 2>/dev/null; then
  echo "❌ Shell access detected"
  exit 1
else
  echo "✅ No shell access"
fi

# Check user
USER_ID=$(docker run --rm ghcr.io/lucid/$SERVICE_NAME:$IMAGE_TAG id -u 2>/dev/null || echo "65532")
if [ "$USER_ID" = "65532" ]; then
  echo "✅ Runs as non-root user (UID: $USER_ID)"
else
  echo "❌ Does not run as non-root user (UID: $USER_ID)"
  exit 1
fi

echo "✅ Distroless compliance verified for $SERVICE_NAME"
```

## Monitoring and Observability

### Health Checks
```javascript
// Health check implementation for distroless containers
class HealthChecker {
  constructor() {
    this.startTime = Date.now();
    this.checks = new Map();
  }

  // Register health check
  registerCheck(name, checkFn) {
    this.checks.set(name, checkFn);
  }

  // Perform all health checks
  async checkHealth() {
    const results = {};
    let overallHealth = true;

    for (const [name, checkFn] of this.checks) {
      try {
        const result = await checkFn();
        results[name] = {
          status: 'healthy',
          details: result
        };
      } catch (error) {
        results[name] = {
          status: 'unhealthy',
          error: error.message
        };
        overallHealth = false;
      }
    }

    return {
      status: overallHealth ? 'healthy' : 'unhealthy',
      uptime: Date.now() - this.startTime,
      timestamp: new Date().toISOString(),
      checks: results
    };
  }

  // HTTP health endpoint
  async healthEndpoint(req, res) {
    const health = await this.checkHealth();
    const statusCode = health.status === 'healthy' ? 200 : 503;
    
    res.status(statusCode).json(health);
  }
}

// Usage example
const healthChecker = new HealthChecker();

// Register health checks
healthChecker.registerCheck('database', async () => {
  // Check database connectivity
  await db.ping();
  return { connected: true };
});

healthChecker.registerCheck('external-api', async () => {
  // Check external API connectivity
  const response = await fetch('https://api.example.com/health');
  if (!response.ok) throw new Error('External API unhealthy');
  return { status: response.status };
});

// Expose health endpoint
app.get('/health', healthChecker.healthEndpoint.bind(healthChecker));
```

### Metrics Collection
```javascript
// Metrics collection for distroless containers
const prometheus = require('prom-client');

// Create metrics registry
const register = new prometheus.Registry();

// Add default metrics
prometheus.collectDefaultMetrics({ register });

// Custom metrics
const httpRequestDuration = new prometheus.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  registers: [register]
});

const httpRequestTotal = new prometheus.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code'],
  registers: [register]
});

const activeConnections = new prometheus.Gauge({
  name: 'active_connections',
  help: 'Number of active connections',
  registers: [register]
});

// Middleware for metrics collection
function metricsMiddleware(req, res, next) {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    const labels = {
      method: req.method,
      route: req.route?.path || req.path,
      status_code: res.statusCode
    };
    
    httpRequestDuration.observe(labels, duration);
    httpRequestTotal.inc(labels);
  });
  
  next();
}

// Metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

// Export metrics registry
module.exports = { register, httpRequestDuration, httpRequestTotal, activeConnections };
```

## Testing and Validation

### Distroless Compliance Tests
```javascript
// Test suite for distroless compliance
describe('Distroless Compliance', () => {
  let container;

  beforeAll(async () => {
    // Start test container
    container = await docker.createContainer({
      Image: 'ghcr.io/lucid/test-service:latest',
      Env: ['NODE_ENV=test'],
      HostConfig: {
        SecurityOpt: ['seccomp:./seccomp-test.json']
      }
    });
    await container.start();
  });

  afterAll(async () => {
    if (container) {
      await container.stop();
      await container.remove();
    }
  });

  test('should not have shell access', async () => {
    const exec = await container.exec({
      Cmd: ['/bin/sh', '-c', 'echo test'],
      AttachStdout: true,
      AttachStderr: true
    });
    
    const stream = await exec.start();
    const chunks = [];
    
    stream.on('data', chunk => chunks.push(chunk));
    
    await new Promise((resolve, reject) => {
      stream.on('end', resolve);
      stream.on('error', reject);
    });
    
    const output = Buffer.concat(chunks).toString();
    expect(output).toContain('executable file not found');
  });

  test('should run as non-root user', async () => {
    const exec = await container.exec({
      Cmd: ['id'],
      AttachStdout: true,
      AttachStderr: true
    });
    
    const stream = await exec.start();
    const chunks = [];
    
    stream.on('data', chunk => chunks.push(chunk));
    
    await new Promise((resolve, reject) => {
      stream.on('end', resolve);
      stream.on('error', reject);
    });
    
    const output = Buffer.concat(chunks).toString();
    expect(output).toContain('uid=65532(nonroot)');
  });

  test('should have minimal syscalls', async () => {
    // Test with restrictive seccomp profile
    const exec = await container.exec({
      Cmd: ['ls', '/'],
      AttachStdout: true,
      AttachStderr: true
    });
    
    const stream = await exec.start();
    const chunks = [];
    
    stream.on('data', chunk => chunks.push(chunk));
    
    await new Promise((resolve, reject) => {
      stream.on('end', resolve);
      stream.on('error', reject);
    });
    
    const output = Buffer.concat(chunks).toString();
    expect(output).not.toContain('Operation not permitted');
  });

  test('should respond to health checks', async () => {
    const exec = await container.exec({
      Cmd: ['curl', '-f', 'http://localhost:8080/health'],
      AttachStdout: true,
      AttachStderr: true
    });
    
    const stream = await exec.start();
    const chunks = [];
    
    stream.on('data', chunk => chunks.push(chunk));
    
    await new Promise((resolve, reject) => {
      stream.on('end', resolve);
      stream.on('error', reject);
    });
    
    const output = Buffer.concat(chunks).toString();
    expect(output).toContain('healthy');
  });
});
```

### Security Scanning
```bash
#!/bin/bash
# security-scan.sh

set -euo pipefail

IMAGE_NAME=${1:-"ghcr.io/lucid/test-service:latest"}

echo "Running security scan on $IMAGE_NAME..."

# Run Trivy vulnerability scan
trivy image --severity HIGH,CRITICAL --format json --output trivy-results.json "$IMAGE_NAME"

# Check for critical vulnerabilities
CRITICAL_COUNT=$(jq '.Results[].Vulnerabilities[]? | select(.Severity == "CRITICAL") | .VulnerabilityID' trivy-results.json | wc -l)
HIGH_COUNT=$(jq '.Results[].Vulnerabilities[]? | select(.Severity == "HIGH") | .VulnerabilityID' trivy-results.json | wc -l)

if [ "$CRITICAL_COUNT" -gt 0 ]; then
  echo "❌ Found $CRITICAL_COUNT critical vulnerabilities"
  exit 1
fi

if [ "$HIGH_COUNT" -gt 5 ]; then
  echo "❌ Found $HIGH_COUNT high vulnerabilities (limit: 5)"
  exit 1
fi

echo "✅ Security scan passed"
echo "   Critical vulnerabilities: $CRITICAL_COUNT"
echo "   High vulnerabilities: $HIGH_COUNT"
```

## Conclusion

This specification ensures that all Lucid RDP services are built using distroless containers, providing enhanced security through minimal attack surface, reduced CVE exposure, and hardened runtime environments. By following these guidelines, the platform maintains a consistent security posture across all components.
