# Docker Directory Documentation - Lucid Project

## Overview

This document provides a comprehensive directory of all Docker-related files in the Lucid project, including their purposes, configurations, and usage instructions.

## Project Structure

```

Lucid/
├── Dockerfile.lucid-direct          # Main development container
└── docs/organisation/
    └── DOCKER_DIR.md               # This documentation file

```

## Docker Files Inventory

### 1. Dockerfile.lucid-direct

**Location:** `C:\Users\surba\Desktop\personal\THE_FUCKER\lucid_2\Lucid\Dockerfile.lucid-direct`

**Purpose:** Optimized development container for Lucid project with direct build approach

**Description:**
This Dockerfile creates a comprehensive development environment specifically designed for the Lucid project. It addresses context size issues through selective file copying and provides a complete development stack.

**Key Features:**

- **Base Image:** Ubuntu 22.04 LTS

- **Multi-language Support:** Python 3, Java 17, Node.js 18.x

- **Development Tools:** Docker CLI, Docker Compose, Buildx

- **Optimized Build:** Selective copying to reduce context size

- **Health Monitoring:** Built-in health checks

**Environment Variables:**

```dockerfile

ENV DEBIAN_FRONTEND=noninteractive
ENV DOCKER_BUILDKIT=1
ENV DOCKER_DEFAULT_PLATFORM=linux/amd64
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV MAVEN_HOME=/usr/share/maven
ENV NODE_ENV=development
ENV LUCID_ENV=dev

```go

**Installed Components:**

- **System Tools:** curl, wget, git, vim, nano, sudo

- **Build Essentials:** build-essential, pkg-config

- **Python:** python3, pip, venv, dev packages

- **Java:** OpenJDK 17, Maven

- **Node.js:** Version 18.x via NodeSource

- **Docker:** Docker CLI, Docker Compose plugin, Buildx

- **Utilities:** jq, tree, htop, procps, openssh-client

**Python Packages:**

- requests

- pyyaml

- cryptography

- pytest

- black

- ruff

**Build Instructions:**

```bash

# Build the container

docker build -f Dockerfile.lucid-direct -t lucid-dev .

# Run the container

docker run -it --name lucid-dev-container lucid-dev

# Run with volume mounting for development

docker run -it --name lucid-dev-container -v ${PWD}:/workspaces/Lucid lucid-dev

```go

**Health Check:**

- **Interval:** 30 seconds

- **Timeout:** 10 seconds

- **Start Period:** 5 seconds

- **Retries:** 3 attempts

## Docker Compose Files

# No docker-compose files found in the current project structure.

## Build Context Optimization

The `Dockerfile.lucid-direct` implements several optimization strategies:

1. **Selective File Copying:** Only copies essential configuration files initially

1. **Layer Optimization:** Groups related installations to minimize layers

1. **Cache Efficiency:** Uses specific package versions where possible

1. **Context Size Reduction:** Avoids copying entire project during build

## Development Workflow

### Prerequisites

- Docker Engine 20.10+

- Docker Buildx plugin

- Git (for version control)

### Build Process

1. **Context Preparation:** Ensure `.env*`, `requirements*.txt`, `package.json*`, `pom.xml*` files exist

1. **Build Execution:** Run build command with appropriate tags

1. **Container Startup:** Launch container with volume mounts for live development

### Volume Mounting Strategy

```bash

# Development with live code changes

docker run -it \
  --name lucid-dev-container \
  -v ${PWD}:/workspaces/Lucid \
  -p 3000:3000 \
  -p 8080:8080 \
  lucid-dev

```go

## Platform Compatibility

- **Build Platform:** Windows 11 (PowerShell)

- **Target Platform:** Linux/AMD64 (Raspberry Pi compatible)

- **Development Platform:** Cross-platform (Windows, Linux, macOS)

## Security Considerations

- Non-root user configuration recommended for production

- Environment variable management for sensitive data

- Network isolation for development containers

- Regular base image updates for security patches

## Maintenance Notes

- **Base Image Updates:** Monitor Ubuntu 22.04 LTS security updates

- **Package Versions:** Keep Node.js, Java, and Python versions current

- **Docker Tools:** Update Docker CLI and Buildx regularly

- **Dependencies:** Review and update Python packages in requirements files

## Troubleshooting

### Common Issues

1. **Build Context Size:** Ensure only necessary files are in build context

1. **Permission Issues:** Check file permissions for volume mounts

1. **Network Connectivity:** Verify Docker daemon is running

1. **Platform Mismatches:** Use `--platform` flag for cross-platform builds

### Debug Commands

```bash

# Check container health

docker inspect lucid-dev-container

# View container logs

docker logs lucid-dev-container

# Execute commands in running container

docker exec -it lucid-dev-container /bin/bash

# Check build history

docker history lucid-dev

```

## Future Enhancements

- Multi-stage builds for production optimization

- Docker Compose integration for service orchestration

- Automated testing within container builds

- CI/CD pipeline integration

- Security scanning integration

## Related Documentation

- Project README files

- Development setup guides

- Deployment documentation

- CI/CD pipeline configurations

---
**Last Updated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Maintainer:** Lucid Development Team
**Version:** 1.0.0
