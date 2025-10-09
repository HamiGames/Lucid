# LUCID Distroless Docker Standards

**Version:** 1.0.0  
**Last Updated:** 2025-01-27  
**Compliance:** LUCID-STRICT Mode  

---

## 🎯 **Overview**

This document defines the standards for creating distroless Docker images in the LUCID project. All Dockerfiles must comply with these standards to ensure maximum security, minimal attack surface, and consistent deployment practices.

---

## ✅ **Distroless Compliance Requirements**

### **1. Base Image Standards**

**Required Base Images:**
- `gcr.io/distroless/python3-debian12:nonroot` - For Python services
- `gcr.io/distroless/nodejs20-debian12:nonroot` - For Node.js services  
- `gcr.io/distroless/base-debian12:latest` - For system utilities

**Prohibited Base Images:**
- `python:*-slim` (use only in builder stage)
- `ubuntu:*`, `debian:*` (use only in builder stage)
- `alpine:*` (use only in builder stage)
- Any image with package managers or shells

### **2. Multi-Stage Build Requirements**

**Mandatory Structure:**
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder
# ... build dependencies and application setup

# Stage 2: Distroless Runtime
FROM gcr.io/distroless/python3-debian12:nonroot
# ... copy only necessary components
```

**Builder Stage Requirements:**
- Install all dependencies and build tools
- Compile and prepare application
- Create non-root users
- Set proper file permissions

**Runtime Stage Requirements:**
- Copy only essential binaries and libraries
- Copy application code with proper ownership
- Set non-root user execution
- Include health checks

### **3. Security Requirements**

**User Execution:**
- All containers MUST run as non-root user
- Use `USER nonroot` or specific service users
- Never use `USER root` in runtime stage

**File Permissions:**
- Set proper ownership with `--chown=user:group`
- Use appropriate file permissions (755 for executables, 644 for configs)
- Secure sensitive directories (700 for secrets)

**Attack Surface Minimization:**
- No shell access (`/bin/sh`, `/bin/bash`)
- No package managers (`apt`, `pip`, `npm`)
- No unnecessary binaries or tools
- Minimal dynamic libraries

### **4. Import Pathway Standards**

**Python Services:**
```dockerfile
# Copy Python installation
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin/python3.11 /usr/local/bin/python3.11
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Set Python path
ENV PYTHONPATH=/app:/home/nonroot/.local/lib/python3.12/site-packages
```

**Node.js Services:**
```dockerfile
# Copy Node.js installation
COPY --from=builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=builder /usr/local/bin/node /usr/local/bin/node
COPY --from=builder /usr/local/bin/npm /usr/local/bin/npm
```

**System Utilities:**
```dockerfile
# Copy essential system tools
COPY --from=builder /usr/bin/curl /usr/bin/curl
COPY --from=builder /bin/nc /bin/nc
COPY --from=builder /usr/bin/jq /usr/bin/jq
COPY --from=builder /usr/sbin/gosu /usr/sbin/gosu
```

### **5. Required Dynamic Libraries**

**Standard Library Set:**
```dockerfile
# Copy required dynamic libraries (architecture-specific)
COPY --from=builder /lib/*-linux-*/libc.so.6 /lib/
COPY --from=builder /lib/*-linux-*/libssl.so.3 /lib/
COPY --from=builder /lib/*-linux-*/libcrypto.so.3 /lib/
COPY --from=builder /lib/*-linux-*/libz.so.1 /lib/
COPY --from=builder /lib/*-linux-*/liblzma.so.5 /lib/
COPY --from=builder /lib/*-linux-*/libzstd.so.1 /lib/
COPY --from=builder /lib*/ld-linux-*.so.2 /lib64/
```

### **6. Metadata Requirements**

**Mandatory LABEL Sections:**
```dockerfile
LABEL maintainer="Lucid Development Team" \
      version="1.0.0-distroless" \
      description="Service description for Lucid (Distroless)" \
      org.lucid.plane="ops|chain|gui" \
      org.lucid.service="service-name" \
      org.lucid.layer="0|1|2|3" \
      org.lucid.expose="port-number"
```

**Plane Classifications:**
- `ops` - Operations and infrastructure services
- `chain` - Blockchain and smart contract services  
- `gui` - Graphical user interface services
- `wallet` - Wallet and key management services

**Layer Classifications:**
- `0` - Core support services (API Gateway, Tor Proxy)
- `1` - Session pipeline services (Authentication, Session Recorder)
- `2` - Service integration (Blockchain APIs, RDP Services)
- `3` - Advanced services (Governance, Admin UI)

### **7. Health Check Requirements**

**Standard Health Check Pattern:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import requests; requests.get('http://localhost:PORT/health', timeout=5)"]
```

**Health Check Variations:**
- HTTP services: Use `requests.get()` with health endpoint
- System services: Use `pgrep` to check process status
- Database services: Use connection tests
- Custom services: Use service-specific health commands

### **8. Environment Variable Standards**

**Required Environment Variables:**
```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SERVICE_PORT=8080 \
    MONGODB_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
```

**Service-Specific Variables:**
- Database connections: `MONGODB_URL`, `REDIS_URL`
- Blockchain networks: `TRON_NETWORK`, `ETH_RPC_URL`
- Security settings: `TOR_SOCKS_PORT`, `ENCRYPTION_KEY`
- Service discovery: `SERVICE_DISCOVERY_URL`

---

## 🚫 **Prohibited Practices**

### **Security Violations:**
- Running as root user in runtime stage
- Including package managers in runtime
- Exposing shell access
- Using full base images in runtime
- Hardcoded secrets or passwords

### **Build Violations:**
- Single-stage builds for production
- Missing health checks
- Incomplete metadata
- Inconsistent import pathways
- Missing non-root user setup

### **Runtime Violations:**
- Installing packages at runtime
- Modifying system files
- Running unnecessary services
- Exposing unnecessary ports
- Missing security restrictions

---

## 📋 **Compliance Checklist**

### **Pre-Build Verification:**
- [ ] Uses distroless base image in runtime stage
- [ ] Implements multi-stage build pattern
- [ ] Sets non-root user execution
- [ ] Includes all required metadata labels
- [ ] Defines proper health checks
- [ ] Sets appropriate environment variables

### **Build Verification:**
- [ ] Builder stage installs all dependencies
- [ ] Runtime stage copies only essential components
- [ ] File permissions are properly set
- [ ] Dynamic libraries are correctly copied
- [ ] Import pathways are consistent
- [ ] Security restrictions are applied

### **Runtime Verification:**
- [ ] Container runs as non-root user
- [ ] No shell access available
- [ ] Health checks pass
- [ ] Service starts correctly
- [ ] Logs are properly formatted
- [ ] Resource usage is optimized

---

## 🔧 **Implementation Examples**

### **Python Service Template:**
```dockerfile
# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS builder

# Build dependencies and setup
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn

COPY app/ /app/
RUN adduser --disabled-password --gecos '' service_user

# Distroless runtime
FROM gcr.io/distroless/python3-debian12:nonroot

COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin/python3.11 /usr/local/bin/python3.11
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

COPY --from=builder /lib/*-linux-*/libc.so.6 /lib/
COPY --from=builder /lib*/ld-linux-*.so.2 /lib64/

COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

COPY --from=builder --chown=service_user:service_user /app /app

ENV PYTHONPATH=/app
EXPOSE 8080
USER service_user
WORKDIR /app

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "-c", "import requests; requests.get('http://localhost:8080/health', timeout=5)"]

ENTRYPOINT ["/usr/local/bin/python3.11", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### **Node.js Service Template:**
```dockerfile
# syntax=docker/dockerfile:1.7
FROM node:20-slim AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

RUN adduser --disabled-password --gecos '' service_user

# Distroless runtime
FROM gcr.io/distroless/nodejs20-debian12:nonroot

COPY --from=builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=builder /usr/local/bin/node /usr/local/bin/node

COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

COPY --from=builder --chown=service_user:service_user /app /app

ENV NODE_ENV=production
EXPOSE 3000
USER service_user
WORKDIR /app

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["node", "-e", "require('http').get('http://localhost:3000/health', (res) => process.exit(res.statusCode === 200 ? 0 : 1))"]

ENTRYPOINT ["/usr/local/bin/node", "server.js"]
```

---

## 🎯 **Quality Assurance**

### **Automated Checks:**
- Dockerfile linting with `hadolint`
- Security scanning with `trivy`
- Distroless compliance verification
- Import pathway validation
- Health check testing

### **Manual Reviews:**
- Security team approval for new services
- Architecture team review for layer assignments
- Operations team validation for deployment readiness
- Performance team assessment for resource optimization

---

## 📚 **References**

- [Google Distroless Images](https://github.com/GoogleContainerTools/distroless)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [LUCID Architecture Specification](docs/architecture/)
- [LUCID Security Guidelines](docs/security/)

---

**Compliance Status:** All LUCID Docker images must meet these standards before production deployment.
