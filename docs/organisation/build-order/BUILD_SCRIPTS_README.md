# Lucid Distroless Build Scripts

## Overview

This directory contains PowerShell scripts for building and deploying Lucid distroless Docker images in a phase-based approach. The scripts are designed to create optimized, secure containers for Raspberry Pi deployment.

## Scripts

### 1. `build-distroless-phases.ps1`

**Main build script** that creates all distroless images in dependency order across 5 phases.

**Usage:**

```powershell

# Basic usage (builds and pushes all images)

.\build-distroless-phases.ps1

# Build only (no push to Docker Hub)

.\build-distroless-phases.ps1 -SkipPush

# Verbose output with custom repository

.\build-distroless-phases.ps1 -DockerRepo "your-repo/lucid" -Verbose

# Custom platforms

.\build-distroless-phases.ps1 -Platforms "linux/arm64"

```

**Parameters:**

- `-DockerRepo`: Docker Hub repository (default: "pickme/lucid")

- `-Platforms`: Target platforms (default: "linux/arm64,linux/amd64")

- `-SkipPush`: Build only, don't push to Docker Hub

- `-Verbose`: Enable detailed logging

- `-LogFile`: Custom log file name

### 2. `verify-distroless-images.ps1`

**Verification script** that checks all built images are available in Docker Hub.

**Usage:**

```powershell

# Verify all images

.\verify-distroless-images.ps1

# Verbose verification

.\verify-distroless-images.ps1 -Verbose

# Custom repository

.\verify-distroless-images.ps1 -DockerRepo "your-repo/lucid"

```bash

### 3. `build-and-deploy.bat`

**Windows batch file** for easy execution of the complete build and verification process.

**Usage:**

```cmd

# Double-click or run from command prompt

build-and-deploy.bat

```rust

## Build Phases

### Phase 1: Core Infrastructure

- **server-tools**: Essential system utilities

- **tunnel-tools**: Network tunneling components

- **tor-proxy**: Tor network proxy service

### Phase 2: API Gateway & Core Services

- **api-server**: Main API server

- **api-gateway**: API gateway and routing

- **authentication**: Authentication service

### Phase 3: Session Pipeline

- **session-chunker**: Session data chunking

- **session-encryptor**: Session encryption

- **merkle-builder**: Merkle tree construction

- **session-orchestrator**: Session orchestration

### Phase 4: Blockchain Core

- **blockchain-api**: Blockchain API service

- **blockchain-governance**: Governance system

- **blockchain-ledger**: Ledger management

- **blockchain-sessions-data**: Session data on blockchain

- **blockchain-vm**: Virtual machine for smart contracts

### Phase 5: Payment Systems & Integration

- **tron-node-client**: TRON blockchain client

- **payment-governance**: Payment governance

- **payment-distribution**: Payment distribution

- **usdt-trc20**: USDT TRC20 integration

- **payout-router-v0**: Payout routing v0

- **payout-router-kyc**: KYC payout routing

- **payment-analytics**: Payment analytics

- **openapi-server**: OpenAPI server

- **openapi-gateway**: OpenAPI gateway

- **rdp-server-manager**: RDP server management

- **admin-ui**: Administrative user interface

## Prerequisites

### Windows Development Environment

1. **Docker Desktop** with Buildx support

1. **PowerShell 5.1+** or PowerShell Core

1. **Git** for version control

1. **Docker Hub account** with push permissions

### Setup Commands

```powershell

# Verify Docker Buildx

docker buildx version

# Login to Docker Hub

docker login

# Create buildx builder (if needed)

docker buildx create --name lucid-builder --use
docker buildx inspect --bootstrap

```bash

## Execution Flow

1. **Pre-flight Checks**

   - Verify Docker Buildx availability

   - Initialize buildx builder

   - Check Docker Hub login status

1. **Phase-based Building**

   - Build services in dependency order

   - Multi-platform image creation

   - Push to Docker Hub registry

1. **Verification**

   - Check all images are available

   - Verify platform support

   - Generate deployment readiness report

## Log Files

The scripts generate detailed log files with timestamps:

- `build-distroless-YYYYMMDD-HHMMSS.log`: Build process logs

- `verify-distroless-YYYYMMDD-HHMMSS.log`: Verification logs

## Error Handling

- **Graceful failures**: Individual service failures don't stop the entire process

- **Detailed logging**: All operations are logged with timestamps

- **Exit codes**: Proper exit codes for automation integration

- **Retry logic**: Built-in retry mechanisms for network operations

## Performance Optimization

- **Parallel builds**: Services within phases can be built in parallel

- **Layer caching**: Docker layer caching for faster rebuilds

- **Selective copying**: Only essential files copied to reduce context size

- **Multi-stage builds**: Optimized image sizes using distroless base images

## Security Features

- **Distroless images**: Minimal attack surface with no shell or package manager

- **Non-root execution**: Services run as non-privileged users

- **Secrets management**: Environment variable handling for sensitive data

- **Network isolation**: Container network segmentation

## Deployment Integration

After successful build and verification:

1. **Raspberry Pi Setup**

   ```bash

   ssh pickme@192.168.0.75
   cd /mnt/myssd/Lucid

   ```

1. **Deploy Core Services**

   ```bash

   docker-compose -f infrastructure/compose/docker-compose.core.yaml up -d

   ```

1. **Deploy Additional Phases**

   ```bash

   docker-compose -f infrastructure/compose/docker-compose.sessions.yaml up -d
   docker-compose -f infrastructure/compose/docker-compose.blockchain.yaml up -d
   docker-compose -f infrastructure/compose/docker-compose.payment-systems.yaml up -d

   ```

## Troubleshooting

### Common Issues

1. **Buildx not available**

   ```powershell

   # Install Docker Desktop with Buildx

   # Or install buildx manually

   docker buildx install

   ```

1. **Docker Hub authentication**

   ```powershell

   # Re-login to Docker Hub

   docker logout
   docker login

   ```

1. **Platform not supported**

   ```powershell

   # Check available platforms

   docker buildx inspect --bootstrap

   ```

1. **Out of disk space**

   ```powershell

   # Clean up Docker system

   docker system prune -a

   ```

### Debug Commands

```powershell

# Check buildx builder status

docker buildx ls

# Inspect specific image

docker buildx imagetools inspect pickme/lucid:api-server

# View build logs

Get-Content build-distroless-*.log | Select-String "ERROR"

# Check Docker system usage

docker system df

```

## File Structure

```

Lucid/
├── build-distroless-phases.ps1      # Main build script
├── verify-distroless-images.ps1     # Verification script
├── build-and-deploy.bat             # Windows batch wrapper
├── BUILD_SCRIPTS_README.md          # This documentation
├── build-distroless-*.log           # Build logs
└── verify-distroless-*.log          # Verification logs

```

## Support

For issues or questions:

1. Check the log files for detailed error information

1. Verify all prerequisites are met

1. Ensure Docker Hub credentials are valid

1. Review the LUCID_DISTROLESS_BUILD_GUIDE.md for additional context

---
**Last Updated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Maintainer:** Lucid Development Team
**Version:** 1.0.0
