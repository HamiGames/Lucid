# LUCID DISTROLESS DEPLOYMENT SCRIPTS

This directory contains comprehensive PowerShell scripts for building, configuring, and deploying the Lucid project as a complete distroless container cluster.

## Overview

The Lucid project uses a multi-container architecture with distroless images for enhanced security and minimal attack surface. These scripts automate the entire deployment pipeline from building images to running the complete cluster.

## Scripts

### 1. `build-all-distroless-images.ps1`

**Purpose**: Builds all Dockerfiles in `infrastructure/docker/` as distroless images

**Features**:

- Scans for all Dockerfiles, prioritizing `.distroless` versions

- Validates Dockerfile compliance with distroless standards

- Multi-platform builds (`linux/amd64,linux/arm64`)

- Pushes to `pickme/lucid` Docker Hub registry

- Generates Docker Compose file with all services

- Comprehensive build validation and error handling

**Usage**:

```powershell

# Build all images locally (no push)

.\scripts\build-all-distroless-images.ps1

# Build and push to registry

.\scripts\build-all-distroless-images.ps1 -Push

# Force rebuild without cache

.\scripts\build-all-distroless-images.ps1 -Push -Force

# Verbose output

.\scripts\build-all-distroless-images.ps1 -Push -Verbose

```php

**Parameters**:

- `-Push`: Push images to Docker Hub registry

- `-Force`: Force rebuild without cache

- `-Verbose`: Enable verbose output

- `-Registry`: Docker registry (default: "pickme")

- `-Repository`: Repository name (default: "lucid")

- `-Tag`: Image tag (default: "latest")

### 2. `generate-service-environments.ps1`

**Purpose**: Generates environment configuration files for all services

**Features**:

- Creates individual `.env` files for each service

- Generates Docker Compose environment configurations

- Creates master environment file with all variables

- Service-specific configurations with sensible defaults

- Production-ready security settings

**Usage**:

```powershell

# Generate all configurations

.\scripts\generate-service-environments.ps1

# Generate only compose environments

.\scripts\generate-service-environments.ps1 -GenerateEnv:$false

# Verbose output

.\scripts\generate-service-environments.ps1 -Verbose

```javascript

**Output**:

- `configs/environment/services/` - Individual service `.env` files

- `configs/environment/compose/` - Compose environment files

- `configs/environment/lucid-master.env` - Master environment file

### 3. `deploy-distroless-cluster.ps1`

**Purpose**: Complete deployment orchestration script

**Features**:

- Orchestrates the entire deployment pipeline

- Prerequisites validation

- Builds images (optional)

- Generates configurations (optional)

- Deploys the complete cluster

- Health checks and service validation

- Comprehensive status reporting

**Usage**:

```powershell

# Complete deployment (build + config + deploy)

.\scripts\deploy-distroless-cluster.ps1 -Build -GenerateConfig -Deploy -Push

# Deploy only (assuming images are already built)

.\scripts\deploy-distroless-cluster.ps1 -Deploy

# Development deployment (no push)

.\scripts\deploy-distroless-cluster.ps1 -Build -GenerateConfig -Deploy

```javascript

**Parameters**:

- `-Build`: Build distroless images

- `-Push`: Push images to registry

- `-Deploy`: Deploy the cluster

- `-GenerateConfig`: Generate environment configurations

- `-Force`: Force rebuild without cache

- `-Verbose`: Enable verbose output

## Services Included

The deployment includes the following services:

### Core Infrastructure

- **mongodb**: MongoDB database with authentication

- **redis**: Redis cache and session storage

### API Services

- **admin-ui**: Next.js admin interface (Port 3000)

- **blockchain-api**: Blockchain API service (Port 8084)

- **authentication-service**: User authentication (Port 8085)

- **user-manager**: User management (Port 8086)

### Session Processing

- **session-recorder**: Session recording service (Port 8087)

- **chunker**: Data chunking service (Port 8088)

- **encryptor**: Encryption service (Port 8089)

- **merkle-builder**: Merkle tree builder (Port 8090)

### Blockchain Integration

- **chain-client**: On-System Chain client (Port 8091)

- **tron-client**: TRON blockchain client (Port 8092)

- **dht-node**: Distributed hash table node (Port 8093)

### Security & Management

- **hardware-wallet**: Hardware wallet integration (Port 8094)

- **policy-engine**: Policy enforcement engine (Port 8095)

- **rdp-host**: Remote desktop hosting (Port 3389)

## Configuration

### Environment Variables

Each service has its own environment configuration with production-ready defaults:

#### Security Settings

```bash

JWT_SECRET_KEY=lucid-jwt-secret-key-change-in-production
KEY_ENC_SECRET=lucid-key-encryption-secret-change-in-production
ENCRYPTION_KEY=lucid-encryption-key-change-in-production

```ini

#### Database Configuration

```bash

MONGO_URI=mongodb://lucid:lucid@mongodb:27017/lucid?authSource=admin
REDIS_URL=redis://redis:6379/0

```ini

#### Blockchain Configuration

```bash

TRON_NETWORK=shasta
RPC_URL=http://localhost:8545
CHAIN_ID=1337

```

### Network Configuration

The cluster uses a dedicated Docker network:

- **Network**: `lucid_core_net`

- **Subnet**: `172.21.0.0/24`

- **Gateway**: `172.21.0.1`

### Volume Configuration

Each service has persistent data volumes:

- **Format**: `lucid_{service}_data`

- **Mount**: `/data`

- **Labels**: Include layer and service information

## Deployment Workflow

### 1. Prerequisites

- Docker and Docker Compose installed

- Docker daemon running

- Git available

- PowerShell 5.1 or later

- Docker Hub access (if pushing images)

### 2. Build Images

```powershell

.\scripts\build-all-distroless-images.ps1 -Push -Verbose

```

### 3. Generate Configurations

```powershell

.\scripts\generate-service-environments.ps1 -Verbose

```

### 4. Deploy Cluster

```powershell

.\scripts\deploy-distroless-cluster.ps1 -Deploy -Verbose

```

### 5. Verify Deployment

```powershell

docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml ps

```

## Monitoring and Health Checks

### Service Health

Each service includes health check endpoints:

- **Endpoint**: `http://localhost:{port}/health`

- **Method**: GET

- **Response**: 200 OK for healthy services

### Container Status

```powershell

# View all containers

docker ps --filter "label=org.lucid.service"

# View service logs

docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml logs {service}

# View all logs

docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml logs -f

```

### Service URLs

- **Admin UI**: http://localhost:3000

- **Blockchain API**: http://localhost:8084

- **Authentication**: http://localhost:8085

- **User Manager**: http://localhost:8086

- **Session Recorder**: http://localhost:8087

## Troubleshooting

### Common Issues

#### Build Failures

```powershell

# Check Docker Buildx

docker buildx version

# Check Docker Hub login

docker login

# Verify registry access

docker pull pickme/lucid:test

```

#### Deployment Issues

```powershell

# Validate compose file

docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml config

# Check network connectivity

docker network ls | grep lucid

# View container logs

docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml logs

```

#### Service Health Issues

```powershell

# Check individual service health

curl -f http://localhost:3000/health
curl -f http://localhost:8084/health

# Restart specific service

docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml restart {service}

```

### Debug Commands

```powershell

# Check for build contexts

grep -r "build:" infrastructure/compose/

# Check for non-distroless images

grep -r "FROM.*slim\|FROM.*alpine" infrastructure/docker/

# Verify pull policies

grep -r "pull_policy: always" infrastructure/compose/

# Check environment variables

docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml config

```

## Security Features

### Distroless Images

- Minimal attack surface

- No shell interpreters

- Non-root user execution

- Read-only filesystems where possible

### Network Security

- Isolated Docker network

- No exposed ports except necessary services

- Internal service communication only

### Data Security

- Encrypted environment variables

- Secure key management

- Audit logging enabled

- Policy enforcement

## Compliance

The deployment follows Lucid project regulations:

- **REGULATION 1**: Distroless images only

- **REGULATION 2**: YAML composition only (no build contexts)

- **REGULATION 3**: Multi-platform builds

- **REGULATION 4**: Standardized networks and volumes

- **REGULATION 5**: Pull policy enforcement

## Support

For issues or questions:

1. Check the troubleshooting section above

1. Review service logs for errors

1. Verify environment configurations

1. Ensure all prerequisites are met

1. Check Docker Hub connectivity (if pushing)

## License

This deployment system is part of the Lucid project and follows the same licensing terms.
