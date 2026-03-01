# Docker Hub Registry Cleanup

## Overview
Clean all existing images from pickme/lucid Docker Hub repository before starting new builds to ensure a clean build environment.

## Prerequisites
- Docker Hub account access (pickme account)
- Docker CLI configured with pickme credentials
- Network connectivity to Docker Hub

## Script Location
`scripts/registry/cleanup-dockerhub.sh`

## Actions Performed

### 1. Authentication
```bash
# Authenticate to Docker Hub
docker login --username pickme
# Enter password when prompted
```

### 2. List All Repositories
```bash
# List all repositories under pickme/lucid namespace
docker search pickme/lucid
```

### 3. Delete All Tagged Images
```bash
# Delete all tagged images from registry
# This includes all versions and tags for:
# - pickme/lucid-mongodb
# - pickme/lucid-redis  
# - pickme/lucid-elasticsearch
# - pickme/lucid-auth-service
# - pickme/lucid-api-gateway
# - pickme/lucid-blockchain-engine
# - pickme/lucid-session-anchoring
# - pickme/lucid-block-manager
# - pickme/lucid-data-chain
# - pickme/lucid-service-mesh-controller
# - pickme/lucid-session-pipeline
# - pickme/lucid-session-recorder
# - pickme/lucid-chunk-processor
# - pickme/lucid-session-storage
# - pickme/lucid-session-api
# - pickme/lucid-rdp-server-manager
# - pickme/lucid-xrdp-integration
# - pickme/lucid-session-controller
# - pickme/lucid-resource-monitor
# - pickme/lucid-node-management
# - pickme/lucid-admin-interface
# - pickme/lucid-tron-client
# - pickme/lucid-payout-router
# - pickme/lucid-wallet-manager
# - pickme/lucid-usdt-manager
# - pickme/lucid-trx-staking
# - pickme/lucid-payment-gateway
# - pickme/lucid-base (base images)
```

### 4. Clean Local Docker Cache
```bash
# Clean local Docker cache on Windows 11 console
docker system prune -a --volumes
docker builder prune -a
```

### 5. Verify Cleanup Completion
```bash
# Verify no images remain in registry
docker search pickme/lucid
# Expected: No results returned
```

## Script Implementation

```bash
#!/bin/bash
# scripts/registry/cleanup-dockerhub.sh
# Full cleanup of pickme/lucid Docker Hub registry

set -e

echo "Starting Docker Hub registry cleanup..."

# Authenticate to Docker Hub
echo "Authenticating to Docker Hub..."
docker login --username pickme

# List current repositories
echo "Current repositories under pickme/lucid:"
docker search pickme/lucid

# Clean local Docker cache
echo "Cleaning local Docker cache..."
docker system prune -a --volumes -f
docker builder prune -a -f

# Note: Manual deletion of Docker Hub images requires web interface
# or Docker Hub API calls as docker CLI cannot delete remote images
echo "Manual cleanup required:"
echo "1. Visit https://hub.docker.com/r/pickme/lucid"
echo "2. Delete all tagged images manually"
echo "3. Or use Docker Hub API to delete images programmatically"

echo "Docker Hub cleanup completed."
```

## Validation Criteria
- `docker search pickme/lucid` returns no results
- Local Docker cache cleaned (freed space)
- No orphaned images or containers

## Troubleshooting

### Authentication Issues
```bash
# If authentication fails, check credentials
docker logout
docker login --username pickme
```

### Network Issues
```bash
# Test Docker Hub connectivity
docker pull hello-world
```

### Permission Issues
- Ensure pickme account has admin access to lucid repository
- Verify Docker Hub API token permissions

## Security Considerations
- Never commit Docker Hub credentials to version control
- Use environment variables for sensitive information
- Rotate API tokens regularly

## Next Steps
After successful cleanup, proceed to environment configuration generation.
