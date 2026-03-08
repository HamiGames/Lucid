# Service Mesh Container Design

## Overview

The `service-mesh` container provides service discovery, mTLS certificate management, and Envoy proxy configuration for the Lucid platform. It uses a multi-stage Dockerfile targeting distroless runtime for security.

**Image**: `pickme/lucid-service-mesh:latest-arm64`  
**Ports**: 8500, 8501, 8502, 8600, 8088  
**Base**: `gcr.io/distroless/python3-debian12:latest`

---

## Dockerfile Structure

### Stage 1: Builder (`python:3.11-slim-bookworm`)

1. **Build dependencies**: gcc, libffi-dev, libssl-dev, pkg-config
2. **System directory markers**: Creates content-filled markers in `/var/run/.keep` and `/var/lib/.keep`
3. **Python packages**: Installs to `/root/.local/lib/python3.11/site-packages`
4. **Package markers**: Creates `.lucid-marker` files after pip install
5. **Source code copy**: Copies `service-mesh/` with verification
6. **Source markers**: Creates `.lucid-source-marker` and `.lucid-config-marker`

### Stage 2: Runtime (Distroless)

1. **Copy system directories**: `/var/run`, `/var/lib`
2. **Copy CA certificates**: For TLS verification
3. **Copy packages**: To `/usr/local/lib/python3.11/site-packages`
4. **Runtime verification**: Asserts all packages and markers exist
5. **Copy application**: To `/app/service-mesh`
6. **Application verification**: Asserts all source files exist

---

## Key Design Patterns

### Dockerfile-copy-pattern.md Compliance

All COPY operations include verification steps:

```dockerfile
# Create marker with content (not empty)
RUN echo "LUCID_SERVICE_MESH_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker

# Verify in runtime stage
RUN ["/usr/bin/python3.11", "-c", "import os; \
assert os.path.exists('/usr/local/lib/python3.11/site-packages/.lucid-marker'), 'marker missing'; \
assert os.path.getsize('/usr/local/lib/python3.11/site-packages/.lucid-marker') > 0, 'marker empty'"]
```

### Distroless Python Path

Uses explicit Python 3.11 path for all commands:

```dockerfile
ENTRYPOINT []
CMD ["/usr/bin/python3.11", "-c", "import asyncio; from controller.main import main; asyncio.run(main())"]
```

### Health Check

Socket-based health check on port 8088:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', 8088)); s.close(); exit(0 if result == 0 else 1)"]
```

---

## Errors Resolved

### 1. Read-only File System Error

**Error**: `[Errno 30] Read-only file system: '/app/certificates'`

**Cause**: Distroless containers have read-only filesystems. The certificate manager tried to write to `/app/certificates`.

**Fix**: Added writable volume mounts in `docker-compose.core.yml`:

```yaml
volumes:
  - /mnt/myssd/Lucid/Lucid/data/service-mesh/certificates:/app/certificates
  - /mnt/myssd/Lucid/Lucid/data/service-mesh/envoy-configs:/app/envoy-configs
```

### 2. Health Check Connection Refused

**Error**: `ConnectionRefusedError: [Errno 111] Connection refused` in health checks

**Cause**: `SERVICE_MESH_HOST` was set to `service-mesh` (hostname) instead of `0.0.0.0` (bind address). Uvicorn bound to the container hostname, but health check connected to `localhost`.

**Fix**: Changed in `docker-compose.core.yml`:

```yaml
# Before (wrong - hostname)
- SERVICE_MESH_HOST=service-mesh

# After (correct - bind address)
- SERVICE_MESH_HOST=0.0.0.0
```

### 3. Missing Controller Module

**Error**: `ModuleNotFoundError: No module named 'controller'`

**Cause**: Dockerfile CMD referenced `from controller.main import main` but the `controller/` directory didn't exist.

**Fix**: Created `service-mesh/controller/__init__.py` and `service-mesh/controller/main.py` with proper entry point.

### 4. Python Path Issues

**Error**: Import failures in distroless environment

**Cause**: Default Python path didn't include site-packages location.

**Fix**: Set explicit PYTHONPATH:

```dockerfile
ENV PYTHONPATH=/app/service-mesh:/usr/local/lib/python3.11/site-packages
```

### 5. Empty Marker Files

**Error**: Silent COPY failures (directories existed but were empty)

**Cause**: Docker COPY creates destination directories even when source is missing.

**Fix**: Create markers with actual content and verify size > 0:

```dockerfile
RUN echo "LUCID_SERVICE_MESH_PACKAGES_INSTALLED_$(date +%s)" > /path/.lucid-marker
# Verify: assert os.path.getsize(marker_path) > 0
```

---

## Build Command

```bash
docker build \
  --platform linux/arm64 \
  -t pickme/lucid-service-mesh:latest-arm64 \
  -f service-mesh/Dockerfile \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=1.0.0 \
  .
```

---

## Container Start Command

```bash
docker compose -p lucid-foundation \
  --env-file configs/environment/.env.secrets \
  --env-file configs/environment/.env.foundation \
  --env-file configs/environment/.env.core \
  -f configs/docker/docker-compose.foundation.yml \
  -f configs/docker/docker-compose.core.yml \
  up -d service-mesh
```

---

## Environment Configuration

All configuration via `.env.service-mesh`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_MESH_HOST` | `0.0.0.0` | Bind address (NOT hostname) |
| `HTTP_PORT` | `8088` | HTTP API port |
| `CONSUL_HOST` | `localhost` | Consul server address |
| `CONSUL_PORT` | `8500` | Consul port |
| `LOG_LEVEL` | `INFO` | Logging level |

See `service-mesh/config/env-service-mesh.template` for complete list.

---

## Related Files

- `service-mesh/Dockerfile` - Main Dockerfile
- `service-mesh/requirements.txt` - Python dependencies
- `service-mesh/controller/main.py` - Entry point
- `service-mesh/config/` - YAML/JSON configuration files
- `configs/docker/docker-compose.core.yml` - Compose definition
- `configs/environment/.env.service-mesh` - Environment variables

