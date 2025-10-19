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
