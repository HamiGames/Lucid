# Lucid RDP DevContainer Development Environment

This document provides comprehensive guidance for using the Lucid RDP development container system. The devcontainer is designed to simulate a Raspberry Pi 5 environment with full development capabilities and can be pushed to DockerHub as `pickme/lucid`.

## Overview

The Lucid DevContainer system provides:

- **Multi-stage Dockerfile** with Pi 5 simulation capabilities

- **ARM64 + AMD64 support** for cross-platform development

- **Complete development stack** (Python 3.12, Node.js 20, MongoDB 7, Tor)

- **Docker Compose integration** with MongoDB and Tor services

- **VS Code integration** with comprehensive extensions and settings

- **DockerHub publishing** to `pickme/lucid` repository

## Quick Start

### Prerequisites

- Docker Desktop with BuildKit support

- VS Code with Dev Containers extension

- Git (for versioning)

### Option 1: VS Code DevContainer (Recommended)

1. **Clone and Open**:

   ```bash

   git clone https://github.com/HamiGames/Lucid.git
   cd Lucid
   code .

   ```

1. **Open in DevContainer**:

   - Press `F1` → "Dev Containers: Reopen in Container"

   - Or click the popup: "Reopen in Container"

1. **Wait for Setup**:

   - Initial build may take 10-15 minutes

   - Services (MongoDB, Tor) will start automatically

### Option 2: Docker Compose

```bash

# Create network

docker network create --driver bridge --attachable lucid-dev_lucid_net

# Start services

docker-compose -f .devcontainer/docker-compose.dev.yml up -d

# Enter development container

docker exec -it lucid_devcontainer bash

```

### Option 3: Pre-built Image

```bash

# Pull latest image

docker pull pickme/lucid:dev-latest

# Run with network

docker run -it --rm \
  --network lucid-dev_lucid_net \
  -v $(pwd):/workspaces/Lucid \
  pickme/lucid:dev-latest

```

## Architecture

### Container Structure

The devcontainer uses a multi-stage build process:

```bash

Stage 1: Base (Python 3.12-slim-bookworm)
├── Environment setup per LUCID-STRICT requirements
└── Workspace configuration

Stage 2: System Dependencies
├── Build tools (gcc, cmake, pkg-config)
├── Network tools (netcat, socat, jq)
├── Crypto libraries (libsodium, libssl)
├── Video/Audio tools (ffmpeg, v4l-utils)
├── Compression (zstd)
└── Security tools (tor, torsocks)

Stage 3: Node.js 20 LTS
├── Node.js 20.x installation
└── Global packages (truffle, tronweb@6, etc.)

Stage 4: MongoDB Tools
└── MongoDB 7 CLI tools (mongosh, database-tools)

Stage 5: Python Environment
├── Requirements installation
├── Cryptography libraries (PyNaCl, blake3)
└── TRON development tools (tronpy)

Stage 6: Workspace Setup
└── Project directory structure creation

Stage 7: Tor Configuration
└── Development Tor setup (ports 9050/9051)

Stage 8: Final Environment
├── Project installation (-e .)
├── Service startup scripts
└── Health checks

```yaml

### Service Architecture

```yaml

Services:
  devcontainer:          # Main development environment
    └── VS Code attaches here
  lucid_mongo:          # MongoDB 7 database
    └── Port 27017, replica set rs0
  tor-proxy:            # Tor anonymization
    └── Ports 9050 (SOCKS), 9051 (Control)
  server-tools:         # Testing utilities (optional)
    └── Alpine with curl, jq, netcat, etc.

```bash

## Development Workflow

### Starting Development

1. **Open Project**: Launch VS Code in devcontainer

1. **Verify Services**: Check MongoDB and Tor are running

1. **Install Dependencies**: `pip install -e .` (auto-run)

1. **Start Development**: Begin coding with full stack available

### Common Commands

```bash

# Python development

pytest                           # Run tests
pytest --cov                     # With coverage
mypy 03-api-gateway/api         # Type checking
ruff check .                    # Linting
black .                         # Formatting

# Service management

service tor start               # Start Tor proxy
service tor status              # Check Tor status
mongosh                        # MongoDB shell

# API development

cd 03-api-gateway/api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8081

cd 04-blockchain-core/api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8082

# Container services

docker-compose -f .devcontainer/docker-compose.dev.yml logs
docker-compose -f .devcontainer/docker-compose.dev.yml restart

```

### Development Ports

| Port | Service | Description |

|------|---------|-------------|

| 8080 | API Gateway | Main API entry point |

| 8081 | API Server | Core API service |

| 8082 | Blockchain Core | TRON integration service |

| 27017 | MongoDB | Database service |

| 9050 | Tor SOCKS | SOCKS proxy for .onion access |

| 9051 | Tor Control | Tor control interface |

## Building and Publishing

### Building Images

#### Linux/macOS

```bash

# Full build and push

./build-devcontainer.sh

# Test build only

./build-devcontainer.sh --test-only

# Build without cache

./build-devcontainer.sh --no-cache

```ini

#### Windows PowerShell

```powershell

# Full build and push

.\build-devcontainer.ps1

# Test build only

.\build-devcontainer.ps1 -TestOnly

# Build without cache

.\build-devcontainer.ps1 -NoCache

```ini

### Published Tags

The build scripts create multiple tags on DockerHub `pickme/lucid`:

- `pickme/lucid:0.1.0` (version from pyproject.toml)

- `pickme/lucid:dev-latest` (latest development)

- `pickme/lucid:0.1.0-abcd123` (version + git SHA)

- `pickme/lucid:dev-2024-01-15T10:30:00Z` (timestamped)

### Multi-Architecture Support

Images are built for both:

- **linux/arm64** - Raspberry Pi 5 target platform

- **linux/amd64** - Development machines

## Configuration

### Environment Variables

The devcontainer sets these environment variables:

```bash

# Core system

PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
DOCKER_DEFAULT_PLATFORM=linux/arm64
LUCID_ENV=dev

# Database

MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false

# API configuration

SERVICE_NAME=lucid-api
VERSION=0.1.0
PORT=8081

# Blockchain (empty for development)

BLOCK_ONION=
BLOCK_RPC_URL=
ONION=
TOR_CONTROL_PASSWORD=

```

### VS Code Configuration

The devcontainer includes comprehensive VS Code setup:

#### Extensions

- Python development (python, pylance, mypy)

- Code formatting (ruff, black-formatter)

- Docker integration (docker, remote-containers)

- Testing (pytest)

- Git integration (gitlens)

- AI assistance (GitHub Copilot)

#### Settings

- Python interpreter: `/usr/local/bin/python`

- Format on save enabled

- Ruff linting enabled

- Black formatting enabled

- PyTest as test framework

## Network Architecture

### Container Networking

All services communicate through the `lucid-dev_lucid_net` bridge network:

```yaml

lucid-dev_lucid_net (bridge)
├── devcontainer (lucid_devcontainer)
├── lucid_mongo (lucid-mongo)
├── tor-proxy (lucid-tor)
└── server-tools (server-tools)

```yaml

### Service Discovery

Services use container names for internal communication:

- Database: `mongodb://lucid_mongo:27017`

- Tor proxy: `lucid_tor:9050` (SOCKS)

- API services: `devcontainer:8081`

## Security Configuration

### Tor Integration (R-MUST-014, R-MUST-020)

Tor is configured for development with:

- **SOCKS proxy**: Port 9050

- **Control interface**: Port 9051 with cookie auth

- **Data directory**: `/var/lib/tor`

- **Configuration**: `/etc/tor/torrc`

### Container Security

All services run with:

- `security_opt: no-new-privileges:true`

- Non-root user where possible

- Resource limits (4GB memory, 2 CPU cores)

- Read-only mounts where appropriate

### Database Security

MongoDB runs with:

- Authentication enabled (`--auth`)

- User: `lucid` / Password: `lucid` (development only)

- Replica set configuration (`rs0`)

- Bind to all interfaces within container network

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash

# Check Docker daemon

docker info

# Verify network exists

docker network ls | grep lucid-dev_lucid_net

# Check build logs

docker-compose -f .devcontainer/docker-compose.dev.yml logs devcontainer

```

#### MongoDB Connection Issues

```bash

# Check MongoDB health

docker-compose -f .devcontainer/docker-compose.dev.yml exec lucid_mongo mongosh --eval "db.runCommand({ping: 1})"

# Check MongoDB logs

docker-compose -f .devcontainer/docker-compose.dev.yml logs lucid_mongo

```

#### Tor Proxy Issues

```bash

# Check Tor status

docker-compose -f .devcontainer/docker-compose.dev.yml exec tor-proxy sh /usr/local/bin/tor-health

# Test SOCKS proxy

curl --socks5 127.0.0.1:9050 http://check.torproject.org/

```python

#### Build Issues

```bash

# Clear Docker cache

docker system prune -a

# Rebuild without cache

./build-devcontainer.sh --no-cache

# Check buildx setup

docker buildx ls

```yaml

### Performance Issues

#### Slow Build Times

- Use `--cache-from` and `--cache-to` options

- Pre-pull base images

- Ensure sufficient disk space (>10GB)

#### Container Resource Limits

```yaml

# Adjust in docker-compose.dev.yml

deploy:
  resources:
    limits:
      memory: 8G      # Increase if needed
      cpus: '4.0'     # Increase for faster builds

```python

### Development Debugging

#### Python Debugging

```bash

# Install debug tools

pip install ipdb pdbpp

# Use in code

import ipdb; ipdb.set_trace()

```bash

#### API Debugging

```bash

# Enable debug logging

export PYTHONPATH=/workspaces/Lucid
export LOG_LEVEL=DEBUG

# Run with reload

uvicorn app.main:app --reload --log-level debug

```yaml

## Advanced Usage

### Custom Configuration

#### Override Docker Compose

```bash

# Create docker-compose.override.yml

version: '3.8'
services:
  devcontainer:
    environment:

      - CUSTOM_VAR=value

    volumes:

      - custom-volume:/custom/path

```json

#### Custom VS Code Settings

```json

// .vscode/settings.json (local)
{
  "python.defaultInterpreterPath": "/usr/local/bin/python",
  "python.testing.pytestArgs": ["tests", "-v"]
}

```python

### Production Simulation

The devcontainer can simulate production Pi 5 environment:

```bash

# Set production-like environment

export LUCID_ENV=prod
export MONGO_URL=mongodb://prod_mongo:27017/lucid

# Test ARM64 specific code

docker run --platform=linux/arm64 pickme/lucid:dev-latest python -c "import platform; print(platform.machine())"

```bash

### Integration with CI/CD

```yaml

# .github/workflows/devcontainer-test.yml

name: DevContainer Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:

      - uses: actions/checkout@v4

      - name: Build DevContainer

        run: ./build-devcontainer.sh --test-only

```

## Specification Compliance

This devcontainer system implements the following specification requirements:

### R-MUST Requirements Met

- **R-MUST-001**: Pi 5 simulation with containerized services

- **R-MUST-002**: ARM64 build pipeline with NVMe workspace simulation

- **R-MUST-014**: Tor-only access configuration

- **R-MUST-019**: MongoDB 7 only (no SQL)

- **R-MUST-020**: Service-to-service Tor routing capability

### R-SHOULD Requirements Met

- **R-SHOULD-001**: Hardware acceleration simulation via V4L2/FFmpeg

- **R-SHOULD-003**: Local-first identity development setup

- **R-SHOULD-004**: API endpoint development environment

### Development Benefits

- Complete Pi 5 environment simulation on any platform

- Multi-architecture build support (ARM64 + AMD64)

- Production-ready service configuration

- Comprehensive development tool integration

- Automated testing and quality assurance

- DockerHub publishing for team collaboration

---

**Need Help?**

- Check the [WARP.md](./WARP.md) for additional development guidance

- Review specification documents in `./Build_guide_docs/`

- Consult the LUCID-STRICT mode requirements for response formatting
