# RDP Server Manager Service

**Service Name:** `rdp-server-manager`  
**Container Name:** `rdp-server-manager` (in docker-compose.application.yml)  
**Port:** 8081  
**Cluster:** support  
**Type:** distroless Python service

## Overview

The RDP Server Manager service is responsible for managing the lifecycle of RDP server instances in the Lucid system. It handles server creation, configuration, port allocation, and resource management.

## Architecture

This service follows the Lucid module design template pattern:
- **Distroless container** using `gcr.io/distroless/python3-debian12`
- **FastAPI** application with lifespan management
- **Pydantic Settings** for configuration management
- **Python entrypoint** script for clean startup

## Files

### Core Service Files

- `entrypoint.py` - Container entrypoint script (UTF-8 encoded)
- `main.py` - FastAPI application with lifespan manager
- `config.py` - Pydantic Settings configuration management
- `server_manager.py` - RDP server lifecycle management
- `port_manager.py` - Port allocation and management
- `config_manager.py` - Configuration template management

### Configuration Files

- `config/env.rdp-server-manager.template` - Environment variable template
- `../docker-compose.yml` - Docker Compose service definition
- `../Dockerfile.server-manager` - Multi-stage distroless Dockerfile

## Configuration

### Environment Variables

The service uses Pydantic Settings for configuration validation. Required environment variables:

- `RDP_SERVER_MANAGER_HOST` - Service hostname (default: `rdp-server-manager`)
- `RDP_SERVER_MANAGER_PORT` - Service port (default: `8081`)
- `RDP_SERVER_MANAGER_URL` - Service URL
- `MONGODB_URL` - MongoDB connection URL (required)
- `REDIS_URL` - Redis connection URL (required)

Optional environment variables:
- `API_GATEWAY_URL` - API Gateway URL
- `AUTH_SERVICE_URL` - Auth Service URL
- `PORT_RANGE_START` - Start of port allocation range (default: `13389`)
- `PORT_RANGE_END` - End of port allocation range (default: `14389`)
- `MAX_CONCURRENT_SERVERS` - Maximum concurrent RDP servers (default: `50`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

See `config/env.rdp-server-manager.template` for the complete list.

### Docker Compose Configuration

The service is defined in `docker-compose.yml` with:
- **Network:** `lucid-pi-network` (dynamic IP assignment, no static IPs)
- **Volumes:**
  - `/mnt/myssd/Lucid/Lucid/data/rdp-server-manager:/app/data:rw`
  - `/mnt/myssd/Lucid/Lucid/logs/rdp-server-manager:/app/logs:rw`
  - `rdp-server-manager-cache:/tmp/server-manager`
- **Security:** Non-root user (65532:65532), read-only root filesystem, minimal capabilities
- **Healthcheck:** Python-based HTTP healthcheck

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /` - Root endpoint
- `POST /servers` - Create new RDP server instance
- `GET /servers/{server_id}` - Get server status
- `POST /servers/{server_id}/start` - Start RDP server
- `POST /servers/{server_id}/stop` - Stop RDP server
- `POST /servers/{server_id}/restart` - Restart RDP server
- `GET /servers` - List all active servers
- `DELETE /servers/{server_id}` - Delete RDP server

## Design Patterns

This service follows the Lucid module design template:
- ✅ Distroless container runtime
- ✅ Multi-stage Dockerfile build
- ✅ Python entrypoint script (not shell)
- ✅ Pydantic Settings for configuration
- ✅ FastAPI with lifespan manager (not deprecated @app.on_event)
- ✅ Dynamic IP assignment (no static IPs)
- ✅ Standard volume mount patterns
- ✅ Python-based healthcheck (not curl)
- ✅ Proper security configuration
- ✅ Structured logging

## Related Documentation

- `build/docs/mod-design-template.md` - Module design template
- `build/docs/dockerfile-design.md` - Dockerfile patterns
- `build/docs/master-docker-design.md` - Master design principles
- `plan/constants/Dockerfile-copy-pattern.md` - COPY command patterns

