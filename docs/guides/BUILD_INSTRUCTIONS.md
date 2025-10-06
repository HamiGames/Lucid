# Lucid Distroless Images - Build & Push Instructions

## Prerequisites

1. **Docker Desktop** installed and running
2. **Docker Buildx** enabled (usually enabled by default in Docker Desktop)
3. **Docker Hub account** logged in

## Step 1: Login to Docker Hub

```powershell
docker login
```

Enter your Docker Hub credentials when prompted.

## Step 2: Verify Buildx

```powershell
docker buildx version
```

If buildx is not available, create a new builder:

```powershell
docker buildx create --name multiplatform --use
docker buildx inspect --bootstrap
```

## Step 3: Build and Push All Images

### Option A: Using PowerShell Script (Recommended for Windows)

```powershell
# Run from the project root directory
.\build-and-push-distroless.ps1
```

### Option B: Using Bash Script (Git Bash or WSL)

```bash
# Make script executable
chmod +x build-and-push-distroless.sh

# Run the script
./build-and-push-distroless.sh
```

### Option C: Build Individual Images Manually

If you want to build specific images one at a time:

#### Layer 1: Session Pipeline

```powershell
# Session Chunker
docker buildx build --platform linux/arm64,linux/amd64 -f sessions/core/Dockerfile.chunker -t pickme/lucid:session-chunker --push .

# Session Encryptor
docker buildx build --platform linux/arm64,linux/amd64 -f sessions/encryption/Dockerfile.encryptor -t pickme/lucid:session-encryptor --push .

# Merkle Builder
docker buildx build --platform linux/arm64,linux/amd64 -f sessions/core/Dockerfile.merkle_builder -t pickme/lucid:merkle-builder --push .

# Session Orchestrator
docker buildx build --platform linux/arm64,linux/amd64 -f sessions/core/Dockerfile.orchestrator -t pickme/lucid:session-orchestrator --push .

# Authentication
docker buildx build --platform linux/arm64,linux/amd64 -f auth/Dockerfile.authentication -t pickme/lucid:authentication --push .
```

#### Core Support Services

```powershell
# Server Tools
docker buildx build --platform linux/arm64,linux/amd64 -f common/server-tools/Dockerfile -t pickme/lucid:server-tools --push common/server-tools

# Tunnel Tools
docker buildx build --platform linux/arm64,linux/amd64 -f 02-network-security/tunnels/Dockerfile -t pickme/lucid:tunnel-tools --push 02-network-security/tunnels

# Tor Proxy
docker buildx build --platform linux/arm64,linux/amd64 -f 02-network-security/tor/Dockerfile -t pickme/lucid:tor-proxy --push 02-network-security/tor
```

#### API Gateway Services

```powershell
# API Gateway
docker buildx build --platform linux/arm64,linux/amd64 -f 03-api-gateway/gateway/Dockerfile.gateway -t pickme/lucid:api-gateway --push 03-api-gateway/gateway

# API Server
docker buildx build --platform linux/arm64,linux/amd64 -f 03-api-gateway/api/Dockerfile.api -t pickme/lucid:api-server --push 03-api-gateway/api
```

#### Open API Services

```powershell
# OpenAPI Gateway
docker buildx build --platform linux/arm64,linux/amd64 -f open-api/gateway/Dockerfile.gateway -t pickme/lucid:openapi-gateway --push open-api/gateway

# OpenAPI Server
docker buildx build --platform linux/arm64,linux/amd64 -f open-api/api/Dockerfile.api -t pickme/lucid:openapi-server --push open-api/api
```

#### Blockchain Services

```powershell
# Blockchain API
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/api/Dockerfile -t pickme/lucid:blockchain-api --push 04-blockchain-core/api

# Blockchain Governance
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/governance/Dockerfile -t pickme/lucid:blockchain-governance --push 04-blockchain-core/governance

# Blockchain Sessions Data
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/sessions-data/Dockerfile -t pickme/lucid:blockchain-sessions-data --push 04-blockchain-core/sessions-data

# Blockchain VM
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/vm/Dockerfile -t pickme/lucid:blockchain-vm --push 04-blockchain-core/vm

# Blockchain Ledger
docker buildx build --platform linux/arm64,linux/amd64 -f 04-blockchain-core/ledger/Dockerfile -t pickme/lucid:blockchain-ledger --push 04-blockchain-core/ledger

# Legacy Blockchain API
docker buildx build --platform linux/arm64,linux/amd64 -f blockchain/api/Dockerfile -t pickme/lucid:blockchain-api-legacy --push blockchain/api
```

## Step 4: Verify Images on Docker Hub

After the build completes, verify your images at:
- https://hub.docker.com/r/pickme/lucid/tags

## Step 5: Pull Images on Raspberry Pi

On your Raspberry Pi, pull the images:

```bash
# Example: Pull session-chunker
docker pull pickme/lucid:session-chunker

# Pull all Layer 1 images
docker pull pickme/lucid:session-chunker
docker pull pickme/lucid:session-encryptor
docker pull pickme/lucid:merkle-builder
docker pull pickme/lucid:session-orchestrator
docker pull pickme/lucid:authentication
```

## Troubleshooting

### Issue: "buildx: command not found"

**Solution**: Enable buildx in Docker Desktop settings or create a builder:
```powershell
docker buildx create --name multiplatform --use
docker buildx inspect --bootstrap
```

### Issue: "push access denied"

**Solution**: Make sure you're logged in and have access to the `pickme` organization:
```powershell
docker login
```

### Issue: Build is very slow

**Solution**: 
- Building for multiple platforms takes time (ARM64 + AMD64)
- First build will be slower due to layer caching
- Subsequent builds will be faster
- Consider building for single platform first for testing:
  ```powershell
  # Build for ARM64 only (faster for Pi testing)
  docker buildx build --platform linux/arm64 -f <dockerfile> -t <tag> --push <context>
  ```

### Issue: Out of disk space

**Solution**: Clean up old images and build cache:
```powershell
docker system prune -a --volumes
docker buildx prune -a
```

## Image Tags Summary

All images are tagged as: `pickme/lucid:<service-name>`

| Service Name | Image Tag |
|--------------|-----------|
| Session Chunker | `pickme/lucid:session-chunker` |
| Session Encryptor | `pickme/lucid:session-encryptor` |
| Merkle Builder | `pickme/lucid:merkle-builder` |
| Session Orchestrator | `pickme/lucid:session-orchestrator` |
| Authentication | `pickme/lucid:authentication` |
| Server Tools | `pickme/lucid:server-tools` |
| Tunnel Tools | `pickme/lucid:tunnel-tools` |
| Tor Proxy | `pickme/lucid:tor-proxy` |
| API Gateway | `pickme/lucid:api-gateway` |
| API Server | `pickme/lucid:api-server` |
| OpenAPI Gateway | `pickme/lucid:openapi-gateway` |
| OpenAPI Server | `pickme/lucid:openapi-server` |
| Blockchain API | `pickme/lucid:blockchain-api` |
| Blockchain Governance | `pickme/lucid:blockchain-governance` |
| Blockchain Sessions Data | `pickme/lucid:blockchain-sessions-data` |
| Blockchain VM | `pickme/lucid:blockchain-vm` |
| Blockchain Ledger | `pickme/lucid:blockchain-ledger` |
| Legacy Blockchain API | `pickme/lucid:blockchain-api-legacy` |

## Notes

- All images are **multi-platform** (ARM64 + AMD64)
- All images use **distroless base** for maximum security
- Build time: ~10-30 minutes per image (depending on dependencies)
- Total build time for all images: ~4-8 hours (first time)
- Subsequent builds are much faster due to Docker layer caching

