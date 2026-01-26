# GUI Docker Manager Service

Docker container management service for Lucid Electron GUI, providing REST API for managing containers, services, and docker-compose projects.

## Overview

The **gui-docker-manager** service provides a REST API for the Electron GUI to manage Docker containers and services running on the Lucid system. It implements role-based access control to ensure users can only manage services appropriate to their permission level.

## Features

- **Container Management**: Start, stop, restart containers; view logs and statistics
- **Service Groups**: Manage services grouped by deployment phase (foundation, core, application, support)
- **Docker Compose**: Control docker-compose projects
- **Role-Based Access Control**: User, Developer, and Admin roles with granular permissions
- **Health Monitoring**: Check service health and Docker daemon status
- **Metrics**: Prometheus-compatible metrics endpoint

## Architecture

### Service Structure

```
gui-docker-manager/
├── Dockerfile.gui-docker-manager         # Multi-stage distroless build
├── requirements.txt                       # Python dependencies
├── README.md                              # This file
└── gui-docker-manager/
    ├── __init__.py                        # Package initialization
    ├── entrypoint.py                      # Container entrypoint script
    ├── main.py                            # FastAPI application
    ├── config.py                          # Configuration management (Pydantic)
    ├── docker_manager_service.py          # Core service logic
    ├── config/
    │   └── env.gui-docker-manager.template    # Environment variables template
    ├── integration/
    │   ├── __init__.py
    │   ├── service_base.py               # Base client for service communication
    │   └── docker_client.py              # Async Docker socket client
    ├── middleware/
    │   ├── __init__.py
    │   ├── auth.py                       # Authentication middleware
    │   └── rate_limit.py                 # Rate limiting middleware
    ├── routers/
    │   ├── __init__.py
    │   ├── containers.py                 # Container management endpoints
    │   ├── services.py                   # Service group endpoints
    │   ├── compose.py                    # Docker Compose endpoints
    │   └── health.py                     # Health check endpoints
    ├── services/
    │   ├── __init__.py
    │   ├── container_service.py          # Container business logic
    │   ├── compose_service.py            # Compose business logic
    │   └── access_control_service.py     # Role-based access control
    ├── models/
    │   ├── __init__.py
    │   ├── container.py                  # Container data models
    │   ├── service_group.py              # Service group models
    │   └── permissions.py                # Permission and role models
    └── utils/
        ├── __init__.py
        ├── errors.py                     # Custom exceptions
        └── logging.py                    # Logging configuration
```

## API Endpoints

### Containers

- `GET /api/v1/containers` - List all containers
- `GET /api/v1/containers/{id}` - Get container details
- `POST /api/v1/containers/{id}/start` - Start container
- `POST /api/v1/containers/{id}/stop` - Stop container (with timeout)
- `POST /api/v1/containers/{id}/restart` - Restart container
- `GET /api/v1/containers/{id}/logs` - Get container logs (tail N lines)
- `GET /api/v1/containers/{id}/stats` - Get container statistics

### Services

- `GET /api/v1/services` - List service groups
- `GET /api/v1/services/{group}` - Get service group details
- `POST /api/v1/services/{group}/start` - Start all services in group
- `POST /api/v1/services/{group}/stop` - Stop all services in group

### Docker Compose

- `POST /api/v1/compose/up` - Start compose project
- `POST /api/v1/compose/down` - Stop compose project
- `GET /api/v1/compose/status` - Get compose project status

### Health & Status

- `GET /health` - Service health check
- `GET /api/v1/health` - Detailed health check
- `GET /api/v1/ready` - Readiness probe (Kubernetes)
- `GET /api/v1/live` - Liveness probe (Kubernetes)
- `GET /metrics` - Prometheus metrics

## Configuration

### Environment Variables

Required:
- `PORT` - Service port (default: 8098)
- `DOCKER_HOST` - Docker socket path (default: unix:///var/run/docker.sock)

Optional:
- `MONGODB_URL` - MongoDB connection for metrics
- `REDIS_URL` - Redis connection for caching
- `JWT_SECRET_KEY` - JWT key for authentication
- `LUCID_ENV` - Environment name (production/development)
- `LUCID_PLATFORM` - Platform (arm64/amd64)

See `gui-docker-manager/config/env.gui-docker-manager.template` for all available options.

## Role-Based Access Control

### User Role
- **Permissions**: Read-only access to container status, logs, and system info
- **Services**: No management access

### Developer Role
- **Permissions**: Can start/stop/restart containers, read logs and stats
- **Services**: Can manage foundation, core, and application services

### Admin Role
- **Permissions**: Full control over all operations
- **Services**: Can manage all service groups (foundation, core, application, support)

## Docker Socket Access

The service requires access to the Docker socket for container management:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

The socket is mounted as read-only (`ro`) in the docker-compose configuration, and the service uses the Docker daemon's remote API through Python's `docker` library.

## Implementation Details

### Multi-Stage Build

The Dockerfile follows the `dockerfile-design.md` pattern:

1. **Builder Stage**: Installs dependencies using `python:3.11-slim-bookworm`
2. **Runtime Stage**: Uses `gcr.io/distroless/python3-debian12:latest` for minimal attack surface

Features:
- Marker files created with actual content (not empty placeholders)
- Package verification in both builder and runtime stages
- Socket-based health check (no curl required in distroless)
- Non-root user (65532:65532)
- Read-only filesystem with tmpfs for writable /tmp

### Async Architecture

All Docker operations are async using `asyncio` and `httpx` for:
- Non-blocking I/O operations
- Better concurrency handling
- Responsive API even under load

### Service Communication

Docker commands are executed via subprocess to interact with the Docker daemon:
- Retry logic with exponential backoff
- Timeout handling
- Error recovery

## Health Checks

### Docker Daemon Health
- Verifies Docker daemon is accessible
- Checks Docker version compatibility

### Service Health
- Socket connectivity test on port 8098
- Can be customized per environment

## Metrics

Prometheus-compatible metrics available at `/metrics`:
- `lucid_containers_total` - Total number of containers by state
- `lucid_services_healthy` - Number of healthy services
- `docker_operations_total` - Total Docker operations performed

## Security

- **Distroless runtime**: No shell or package manager
- **Non-root user**: Runs as UID 65532
- **Read-only filesystem**: Tmpfs only for /tmp
- **No new privileges**: `security_opt: [no-new-privileges:true]`
- **Capability dropping**: All capabilities dropped except NET_BIND_SERVICE

## Dependencies

### Python Packages
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Configuration validation
- `docker` - Docker SDK for Python
- `httpx` - Async HTTP client
- `redis` - Redis client
- `motor` - MongoDB async driver

### System
- Docker daemon with API endpoint
- Python 3.11+
- Linux kernel with Docker support

## Running Locally

### Development

```bash
cd gui-docker-manager
pip install -r requirements.txt
python -m gui_docker_manager.entrypoint
```

### Docker Build

```bash
docker build -f Dockerfile.gui-docker-manager -t lucid-gui-docker-manager:latest .
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -p 8098:8098 \
  lucid-gui-docker-manager:latest
```

## Troubleshooting

### Container Not Found
Ensure the container is running and accessible via Docker API. Check Docker socket permissions.

### Permission Denied
Verify the service has read access to `/var/run/docker.sock`. The user running the service must have Docker access.

### Health Check Failing
Ensure port 8098 is accessible and not blocked by firewall rules.

## References

- [build/docs/container-design.md](../build/docs/container-design.md) - Container design standards
- [build/docs/dockerfile-design.md](../build/docs/dockerfile-design.md) - Dockerfile patterns
- [configs/services/gui-docker-manager.yml](../configs/services/gui-docker-manager.yml) - Service configuration reference
- [Docker Python SDK](https://docker-py.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## License

Part of the Lucid Project. See main project repository for license information.

## Support

For issues or questions, refer to the project documentation or open an issue in the repository.
