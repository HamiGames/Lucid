# RDP Server Manager Container Design Document

**Version:** 1.0.0  
**Last Updated:** 2025-12-28  
**Service:** `lucid-rdp-server-manager`  
**Container Name:** `rdp-server-manager`  
**Purpose:** RDP server lifecycle management service for the Lucid RDP system

This document provides a design reference for the `rdp-server-manager` container, documenting its architecture, configuration, and operational patterns.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Docker Compose Configuration](#2-docker-compose-configuration)
3. [Directory Structure](#3-directory-structure)
4. [Module Organization](#4-module-organization)
5. [Configuration Management](#5-configuration-management)
6. [API Endpoints](#6-api-endpoints)
7. [Key Components](#7-key-components)
8. [Build Process](#8-build-process)
9. [Operational Considerations](#9-operational-considerations)

---

## 1. Overview

### 1.1 Purpose

The `rdp-server-manager` service manages the lifecycle of RDP server instances, including:

- Server instance creation and deletion
- Port allocation and management (range: 13389-14389)
- Server status tracking (creating, configuring, starting, running, stopping, stopped, failed)
- Resource allocation and limits
- Configuration file generation for xrdp servers

### 1.2 Service Identity

- **Service Name:** `lucid-rdp-server-manager`
- **Container Name:** `rdp-server-manager`
- **Image:** `pickme/lucid-rdp-server-manager:latest-arm64`
- **Port:** `8081` (HTTP, configurable via `RDP_SERVER_MANAGER_PORT`)
- **Protocol:** REST API (FastAPI)
- **Version:** `1.0.0`

### 1.3 Key Features

- **Distroless Container:** Minimal attack surface using `gcr.io/distroless/python3-debian12`
- **FastAPI Framework:** Modern async Python web framework
- **Port Management:** Dynamic port allocation with tracking and availability checking
- **Server Lifecycle:** Complete lifecycle management from creation to deletion
- **Configuration Management:** Generates xrdp configuration files dynamically
- **MongoDB & Redis:** Stores server metadata and state

---

## 2. Docker Compose Configuration

### 2.1 Service Definition

```yaml
rdp-server-manager:
  image: pickme/lucid-rdp-server-manager:latest-arm64
  container_name: rdp-server-manager
  restart: unless-stopped
  env_file:
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.application
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.rdp-server-manager
  networks:
    - lucid-pi-network
  ports:
    - "${RDP_SERVER_MANAGER_PORT:-8081}:${RDP_SERVER_MANAGER_PORT:-8081}"
  volumes:
    - /mnt/myssd/Lucid/Lucid/data/rdp-server-manager:/app/data:rw
    - /mnt/myssd/Lucid/Lucid/logs/rdp-server-manager:/app/logs:rw
    - rdp-server-manager-cache:/tmp/server-manager
  environment:
    - LUCID_ENV=production
    - LUCID_PLATFORM=arm64
    - PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
    - RDP_SERVER_MANAGER_HOST=rdp-server-manager
    - RDP_SERVER_MANAGER_PORT=${RDP_SERVER_MANAGER_PORT:-8081}
    - RDP_SERVER_MANAGER_URL=http://rdp-server-manager:${RDP_SERVER_MANAGER_PORT:-8081}
    - MONGODB_URL=${MONGODB_URL:?MONGODB_URL not set}
    - REDIS_URL=${REDIS_URL:?REDIS_URL not set}
    - API_GATEWAY_URL=${API_GATEWAY_URL:-http://api-gateway:8080}
    - AUTH_SERVICE_URL=${AUTH_SERVICE_URL:-http://lucid-auth-service:8089}
    - PORT_RANGE_START=${PORT_RANGE_START:-13389}
    - PORT_RANGE_END=${PORT_RANGE_END:-14389}
    - MAX_CONCURRENT_SERVERS=${MAX_CONCURRENT_SERVERS:-50}
  user: "65532:65532"
  security_opt:
    - no-new-privileges:true
    - seccomp:unconfined
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE
  read_only: true
  tmpfs:
    - /tmp:noexec,nosuid,size=100m
  healthcheck:
    test:
      [
        "CMD",
        "/usr/bin/python3.11",
        "-c",
        "import os, urllib.request, sys; port = os.getenv('RDP_SERVER_MANAGER_PORT', '8081'); url = 'http://127.0.0.1:' + str(port) + '/health'; urllib.request.urlopen(url, timeout=10).read(); sys.exit(0)",
      ]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  labels:
    - "lucid.service=rdp-server-manager"
    - "lucid.type=distroless"
    - "lucid.platform=arm64"
    - "lucid.security=hardened"
    - "lucid.cluster=application"
  depends_on:
    tor-proxy:
      condition: service_started
    lucid-mongodb:
      condition: service_healthy
    lucid-redis:
      condition: service_healthy
```

### 2.2 Environment Files

Configuration is loaded from multiple environment files in priority order:

1. `.env.foundation` - Foundation service URLs
2. `.env.core` - Core service configuration
3. `.env.application` - Application-level settings
4. `.env.secrets` - Sensitive credentials
5. `.env.rdp-server-manager` - Service-specific overrides

### 2.3 Volume Configuration

```yaml
volumes:
  rdp-server-manager-cache:
    driver: local
    name: lucid-rdp-server-manager-cache
    external: false
```

---

## 3. Directory Structure

### 3.1 Container Internal Structure

```
/app/
├── server_manager/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and lifespan
│   ├── config.py            # Configuration management (Pydantic Settings)
│   ├── config_manager.py    # xrdp configuration file manager
│   ├── entrypoint.py        # Container entrypoint
│   ├── server_manager.py    # Server lifecycle management
│   ├── port_manager.py      # Port allocation management
│   └── config/
│       └── env.rdp-server-manager.template
├── data/                    # Volume mount: /app/data
│   ├── xrdp/
│   │   └── servers/         # xrdp server configurations
│   └── sessions/            # Session data
└── logs/                    # Volume mount: /app/logs
    └── xrdp/
        └── servers/         # Server logs
```

### 3.2 Host Volume Mounts

- **Data:** `/mnt/myssd/Lucid/Lucid/data/rdp-server-manager` → `/app/data:rw`
- **Logs:** `/mnt/myssd/Lucid/Lucid/logs/rdp-server-manager` → `/app/logs:rw`
- **Cache:** `rdp-server-manager-cache` → `/tmp/server-manager:rw`

---

## 4. Module Organization

### 4.1 main.py

**Purpose:** FastAPI application setup and lifespan management

**Key Components:**
- FastAPI app instance
- Lifespan context manager (startup/shutdown)
- API route definitions
- Global exception handler

**Lifespan Events:**
- **Startup:** Initialize `RDPServerManagerConfigManager`, `ConfigManager`, `PortManager`, and `RDPServerManager`
- **Shutdown:** Shutdown `RDPServerManager` gracefully

### 4.2 config.py

**Purpose:** Configuration management using Pydantic Settings

**Key Classes:**
- `RDPServerManagerSettings`: Pydantic BaseSettings with validation
- `RDPServerManagerConfigManager`: Configuration manager wrapper

**Configuration Fields:**
- Service configuration (host, port, URL)
- Database configuration (MongoDB, Redis)
- Port management (range start/end, max concurrent servers)
- Integration URLs (API Gateway, Auth Service)

**Validation:**
- Port range validation (1024-65535)
- Max concurrent servers (1-1000)
- MongoDB/Redis URL validation (no localhost)

### 4.3 entrypoint.py

**Purpose:** Container entrypoint script (Python-based for distroless)

**Key Functions:**
- Python path setup
- Environment variable reading (`RDP_SERVER_MANAGER_PORT`)
- Uvicorn server startup
- Error handling with diagnostics

**Bind Address:** Always binds to `0.0.0.0` (all interfaces)

### 4.4 server_manager.py

**Purpose:** RDP server lifecycle management

**Key Classes:**
- `RDPServerManager`: Main server management class
- `RDPServer`: Server instance dataclass
- `ServerStatus`: Server status enum

**Responsibilities:**
- Server instance creation/deletion
- Server process management
- Configuration file generation
- Resource tracking

### 4.5 port_manager.py

**Purpose:** Port allocation and management

**Key Classes:**
- `PortManager`: Port allocation manager
- `PortInfo`: Port information dataclass
- `PortStatus`: Port status enum

**Features:**
- Dynamic port allocation from configured range
- Port availability checking (socket-based)
- Port tracking and reservation
- Port release on server deletion

### 4.6 config_manager.py

**Purpose:** xrdp configuration file management

**Key Responsibilities:**
- Generate xrdp server configuration files
- Template substitution with server-specific values
- Configuration file path management
- Configuration file cleanup

---

## 5. Configuration Management

### 5.1 Required Environment Variables

```bash
# Database Connections (Required)
MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0

# Service Configuration
RDP_SERVER_MANAGER_HOST=rdp-server-manager
RDP_SERVER_MANAGER_PORT=8081
RDP_SERVER_MANAGER_URL=http://rdp-server-manager:8081
```

### 5.2 Optional Environment Variables

```bash
# Port Management
PORT_RANGE_START=13389          # Default: 13389
PORT_RANGE_END=14389            # Default: 14389
MAX_CONCURRENT_SERVERS=50       # Default: 50

# Integration URLs (Optional)
API_GATEWAY_URL=http://api-gateway:8080
AUTH_SERVICE_URL=http://lucid-auth-service:8089

# Logging
LOG_LEVEL=INFO                  # Default: INFO
```

### 5.3 Configuration Validation

**Pydantic Validators:**
- `validate_port_range()`: Ensures ports are in valid range (1024-65535)
- `validate_max_servers()`: Ensures max servers is between 1 and 1000
- `validate_log_level()`: Ensures log level is valid
- MongoDB/Redis URL validation (no localhost)

---

## 6. API Endpoints

### 6.1 Base Path

All endpoints are under `/` (root path)

### 6.2 Server Management Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| POST | `/servers` | Create new RDP server | `ServerResponse` |
| GET | `/servers/{server_id}` | Get server status | `ServerStatusResponse` |
| GET | `/servers` | List all active servers | `List[ServerStatusResponse]` |
| DELETE | `/servers/{server_id}` | Delete server | `{}` |

### 6.3 Server Control Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| POST | `/servers/{server_id}/start` | Start server | `{}` |
| POST | `/servers/{server_id}/stop` | Stop server | `{}` |
| POST | `/servers/{server_id}/restart` | Restart server | `{}` |

### 6.4 System Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/health` | Health check | `{}` |
| GET | `/` | Root endpoint | `{}` |

---

## 7. Key Components

### 7.1 PortManager

**Purpose:** Manages port allocation for RDP servers

**Key Methods:**
- `allocate_port(server_id)`: Allocate a port for a server
- `release_port(port)`: Release a port when server is deleted
- `is_port_available(port)`: Check if port is available (socket-based)
- `get_available_ports()`: Get list of available ports

**Port Range:**
- Default: 13389-14389 (1000 ports)
- Configurable via `PORT_RANGE_START` and `PORT_RANGE_END`

**Port Status:**
- `AVAILABLE`: Port is available for allocation
- `ALLOCATED`: Port is allocated to a server
- `RESERVED`: Port is reserved (not yet active)
- `BLOCKED`: Port is blocked/unavailable

### 7.2 RDPServerManager

**Purpose:** Manages RDP server lifecycle

**Key Methods:**
- `create_server(request)`: Create new server instance
- `start_server(server_id)`: Start server process
- `stop_server(server_id)`: Stop server process
- `delete_server(server_id)`: Delete server and cleanup resources
- `get_server_status(server_id)`: Get current server status

**Server Status Lifecycle:**
```
CREATING → CONFIGURING → STARTING → RUNNING → STOPPING → STOPPED
                                              ↓
                                            FAILED
```

**Resource Management:**
- Configuration files: `/app/data/xrdp/servers/{server_id}/`
- Log files: `/app/logs/xrdp/servers/{server_id}/`
- Session data: `/app/data/sessions/{server_id}/`

### 7.3 ConfigManager

**Purpose:** Manages xrdp configuration files

**Key Methods:**
- `generate_server_config(server)`: Generate xrdp configuration for server
- `cleanup_server_config(server_id)`: Remove configuration files
- `get_config_path(server_id)`: Get configuration file path

**Configuration Location:**
- Base path: `/app/data/config` (writable volume mount)
- Server configs: `/app/data/config/xrdp/servers/{server_id}/`

---

## 8. Build Process

### 8.1 Dockerfile Location

`RDP/Dockerfile.server-manager`

### 8.2 Build Command

```bash
docker build \
  --platform linux/arm64 \
  -t pickme/lucid-rdp-server-manager:latest-arm64 \
  -f RDP/Dockerfile.server-manager \
  .
```

### 8.3 Build Stages

**Stage 1: Builder**
- Base: `python:3.11-slim-bookworm`
- Purpose: Install Python packages and build application
- Output: Packages in `/root/.local/lib/python3.11/site-packages`
- Output: Application source in `/build/server_manager`

**Stage 2: Runtime**
- Base: `gcr.io/distroless/python3-debian12:latest`
- Purpose: Minimal runtime environment
- Copies: Packages and application from builder stage
- User: `65532:65532` (non-root)

### 8.4 Dependencies

**Python Packages:**
- `fastapi>=0.104.0`: Web framework
- `uvicorn>=0.24.0`: ASGI server
- `pydantic>=2.0.0`: Data validation
- `pydantic-settings>=2.1.0`: Settings management
- `motor>=3.3.0`: Async MongoDB driver
- `pymongo>=4.6.0`: MongoDB driver
- `redis>=5.0.0`: Redis client

---

## 9. Operational Considerations

### 9.1 Startup Sequence

1. **Entrypoint:** `entrypoint.py` sets up Python path
2. **Uvicorn:** Starts FastAPI application
3. **Lifespan Startup:** 
   - Initialize `RDPServerManagerConfigManager`
   - Initialize `ConfigManager`
   - Initialize `PortManager` (scans port range for availability)
   - Initialize `RDPServerManager`
4. **Service Ready:** Health check passes

### 9.2 Shutdown Sequence

1. **Signal Received:** SIGTERM or SIGINT
2. **Lifespan Shutdown:** Shutdown `RDPServerManager`
3. **Cleanup:** Stop all active servers, release ports, cleanup configs
4. **Exit:** Container exits gracefully

### 9.3 Health Checks

**Type:** HTTP-based (connects to `/health` endpoint)

**Health Check Configuration:**
```yaml
healthcheck:
  test:
    [
      "CMD",
      "/usr/bin/python3.11",
      "-c",
      "import os, urllib.request, sys; port = os.getenv('RDP_SERVER_MANAGER_PORT', '8081'); url = 'http://127.0.0.1:' + str(port) + '/health'; urllib.request.urlopen(url, timeout=10).read(); sys.exit(0)",
    ]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 9.4 Logging

**Log Format:**
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**Log Levels:** Controlled via `LOG_LEVEL` environment variable (default: `INFO`)

**Log Destination:** Volume mount at `/app/logs`

### 9.5 Port Management

**Port Range:**
- Default: 13389-14389 (1000 ports)
- Configurable via environment variables
- Ports checked for availability using socket connection

**Port Allocation:**
- First available port in range is allocated
- Ports are tracked in memory and Redis
- Released ports become available for new allocations

**Port Limits:**
- Maximum concurrent servers: `MAX_CONCURRENT_SERVERS` (default: 50)
- Port range size determines maximum capacity

### 9.6 Security Configuration

**Container Security:**
```yaml
user: "65532:65532"  # Non-root user
security_opt:
  - no-new-privileges:true
  - seccomp:unconfined
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # Required for binding to port 8081
read_only: true  # Read-only root filesystem
tmpfs:
  - /tmp:noexec,nosuid,size=100m  # Writable tmpfs
```

**Permission Requirements:**
- Host directories must be owned by user `65532:65532`
- Volume mounts must have write permissions

### 9.7 Integration with Other Services

**Dependencies:**
- **MongoDB:** Server metadata and state storage
- **Redis:** Port allocation tracking and caching
- **API Gateway:** Optional integration for request routing
- **Auth Service:** Optional integration for authentication

**Depended On By:**
- `rdp-controller`: Requires server manager to be healthy
- `rdp-monitor`: Requires server manager URL for monitoring

---

## 10. Related Documentation

- `build/docs/mod-design-template.md` - General module design template
- `build/docs/session-api-design.md` - Session API design (similar patterns)
- `build/docs/master-docker-design.md` - Master Docker design principles
- `RDP/server-manager/README.md` - Server manager specific documentation

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-12-28 | Initial design document creation | System |

---

**Last Updated:** 2025-12-28  
**Status:** ACTIVE  
**Maintained By:** Lucid Development Team

