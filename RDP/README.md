# Lucid RDP Service

## Overview

The Lucid RDP Service provides Remote Desktop Protocol (RDP) functionality for the Lucid RDP system. It includes session controllers, server management, XRDP integration, and resource monitoring.

**Service Name**: `lucid-rdp`  
**Cluster ID**: Phase 3 Application Services  
**Port**: 8081 (Server Manager), 8082 (Controller), 3389 (XRDP), 8090 (Monitor)  
**Phase**: Phase 3 Application Services  
**Status**: Production Ready ✅

---

## Features

### Core RDP Functionality
- ✅ **Session Control** - Manage RDP sessions
- ✅ **Server Management** - Control RDP servers
- ✅ **XRDP Integration** - XRDP protocol support
- ✅ **Resource Monitoring** - Monitor RDP resources
- ✅ **Connection Management** - Handle RDP connections
- ✅ **Quality Control** - Ensure connection quality

### Security Features
- ✅ **Encrypted Sessions** - Encrypted RDP sessions
- ✅ **Access Control** - Role-based access control
- ✅ **Audit Logging** - Complete RDP audit trail
- ✅ **Connection Validation** - Validate RDP connections

### Infrastructure
- ✅ **Distroless Container** - Minimal attack surface
- ✅ **Multi-Service Architecture** - Separate services for different functions
- ✅ **Health Checks** - Built-in health monitoring
- ✅ **Horizontal Scaling** - Stateless design

---

## Service Components

### 1. RDP Server Manager (Port 8081)
Manages:
- RDP server lifecycle
- Server configuration
- Connection management

### 2. RDP Session Controller (Port 8082)
Controls:
- RDP session lifecycle
- Session state management
- Connection handling

### 3. XRDP Integration (Port 3389)
Provides:
- XRDP protocol support
- RDP connection handling
- Protocol translation

### 4. Resource Monitor (Port 8090)
Monitors:
- Resource usage
- Performance metrics
- Connection quality

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- XRDP server (for full functionality)
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

```bash
# 1. Navigate to RDP directory
cd Lucid/RDP

# 2. Start all RDP services
docker-compose up -d

# 3. Verify health
curl http://localhost:8081/health  # Server Manager
curl http://localhost:8082/health  # Session Controller
curl http://localhost:3389/health  # XRDP
curl http://localhost:8090/health  # Resource Monitor
```

### Using Docker

```bash
# Build and run Server Manager
docker build -f Dockerfile.server-manager -t lucid-rdp-server-manager:latest .
docker run -d --name lucid-rdp-server-manager -p 8081:8081 \
  lucid-rdp-server-manager:latest

# Similar for other services
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run server manager
python -m server-manager.main

# Or with uvicorn
uvicorn server-manager.main:app --host 0.0.0.0 --port 8081 --reload
```

---

## API Endpoints

### RDP Server Manager Endpoints (Port 8081)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/servers` | Create server | JWT Token |
| GET | `/api/v1/servers` | List servers | JWT Token |
| GET | `/api/v1/servers/{server_id}` | Get server details | JWT Token |
| PUT | `/api/v1/servers/{server_id}` | Update server | JWT Token |
| DELETE | `/api/v1/servers/{server_id}` | Delete server | JWT Token |

### RDP Session Controller Endpoints (Port 8082)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/sessions` | Create session | JWT Token |
| GET | `/api/v1/sessions/{session_id}` | Get session | JWT Token |
| POST | `/api/v1/sessions/{session_id}/terminate` | Terminate session | JWT Token |

### Resource Monitor Endpoints (Port 8090)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/monitoring/summary` | Get system summary | JWT Token |
| GET | `/api/v1/monitoring/metrics` | Get metrics | JWT Token |

### Health & Meta Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/health` | Service health check | None |
| GET | `/metrics` | Prometheus metrics | None |

---

## Configuration

### Environment Variables

**Server Manager:**
- `LOG_LEVEL` - Logging level (default: INFO)
- `RDP_PORT` - RDP port (default: 3389)

**Session Controller:**
- `LOG_LEVEL` - Logging level (default: INFO)

**Resource Monitor:**
- `LOG_LEVEL` - Logging level (default: INFO)
- `MONITORING_INTERVAL` - Monitoring interval (default: 30s)

---

## Architecture

### Components

```
RDP/
├── server-manager/     # Server Manager
│   └── main.py        # Manager entry point
├── session-controller/ # Session Controller
│   └── main.py        # Controller entry point
├── xrdp/              # XRDP Integration
│   └── main.py        # XRDP entry point
├── resource-monitor/   # Resource Monitor
│   └── main.py        # Monitor entry point
├── Dockerfile.server-manager
├── Dockerfile.controller
├── Dockerfile.xrdp
├── Dockerfile.monitor
├── requirements.txt
└── README.md
```

---

## Development

### Project Structure

```
RDP/
├── server-manager/     # Server Manager service
├── session-controller/ # Session Controller service
├── xrdp/              # XRDP service
├── resource-monitor/   # Resource Monitor service
├── protocol/          # RDP protocol
├── common/            # Common utilities
└── utils/             # Utilities
```

### Building Containers

```bash
# Build all services
docker build -f Dockerfile.server-manager -t lucid-rdp-server-manager:latest .
docker build -f Dockerfile.controller -t lucid-rdp-controller:latest .
docker build -f Dockerfile.xrdp -t lucid-xrdp:latest .
docker build -f Dockerfile.monitor -t lucid-rdp-monitor:latest .
```

---

## Deployment

### Production Deployment

Deploy using Docker Compose:

```yaml
services:
  rdp-server-manager:
    image: lucid-rdp-server-manager:latest
    ports:
      - "8081:8081"
    networks:
      - lucid-network
```

---

## Monitoring

### Health Checks

```bash
# Check all services
curl http://localhost:8081/health  # Server Manager
curl http://localhost:8082/health  # Session Controller
curl http://localhost:3389/health  # XRDP
curl http://localhost:8090/health  # Resource Monitor
```

---

## License

Proprietary - Lucid RDP Development Team

---

## Support

For issues and questions:
- GitHub Issues: [link]
- Email: dev@lucid-rdp.onion
- Documentation: [link]
