# TRON Payment System API - Deployment Procedures

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | TRON-API-DEPLOY-009 |
| Version | 1.0.0 |
| Status | IN PROGRESS |
| Last Updated | 2025-10-12 |
| Owner | Lucid RDP Development Team |

---

## Overview

This document provides comprehensive deployment procedures for the TRON Payment System API, covering build pipelines, container orchestration, Raspberry Pi deployment, environment-specific configurations, and zero-downtime deployment strategies.

### Deployment Principles

- **Automated Builds**: Multi-stage Docker builds with caching
- **Environment Parity**: Consistent deployments across environments
- **Zero Downtime**: Rolling deployments with health checks
- **Rollback Capability**: Quick rollback procedures
- **Security First**: Secrets management and secure deployments

---

## Build Pipeline Specifications

### Multi-Stage Docker Build Process

```bash
#!/bin/bash
# build-payment-service.sh - Automated build script

set -e

# Configuration
REGISTRY="pickme/lucid"
SERVICE_NAME="tron-payment-service"
VERSION="${1:-latest}"
PLATFORMS="linux/amd64,linux/arm64"

echo "Building TRON Payment Service..."
echo "Registry: $REGISTRY"
echo "Service: $SERVICE_NAME"
echo "Version: $VERSION"
echo "Platforms: $PLATFORMS"

# Enable BuildKit
export DOCKER_BUILDKIT=1

# Create buildx builder if it doesn't exist
if ! docker buildx ls | grep -q "lucid-builder"; then
    echo "Creating buildx builder..."
    docker buildx create --name lucid-builder --use --driver docker-container \
        --driver-opt network=host
fi

# Set active builder
docker buildx use lucid-builder

# Build and push images
echo "Building and pushing images..."
docker buildx build \
    --platform $PLATFORMS \
    --target distroless \
    --tag $REGISTRY/$SERVICE_NAME:$VERSION \
    --tag $REGISTRY/$SERVICE_NAME:latest \
    --cache-from type=gha,scope=$SERVICE_NAME \
    --cache-to type=gha,mode=max,scope=$SERVICE_NAME \
    --file payment-systems/tron-payment-service/Dockerfile \
    --push \
    .

echo "Build completed successfully!"
echo "Images pushed:"
echo "  - $REGISTRY/$SERVICE_NAME:$VERSION"
echo "  - $REGISTRY/$SERVICE_NAME:latest"
```

### Build Pipeline with Security Scanning

```yaml
# .github/workflows/build-payment-service.yml
name: Build TRON Payment Service

on:
  push:
    branches: [main, develop]
    paths: ['payment-systems/tron-payment-service/**']
  pull_request:
    branches: [main]
    paths: ['payment-systems/tron-payment-service/**']
  workflow_dispatch:
    inputs:
      version:
        description: 'Version tag'
        required: true
        default: 'latest'

env:
  REGISTRY: pickme/lucid
  SERVICE_NAME: tron-payment-service

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
      image-tag: ${{ steps.build.outputs.tags }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.SERVICE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: ./payment-systems/tron-payment-service
          platforms: linux/amd64,linux/arm64
          target: distroless
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha,scope=${{ env.SERVICE_NAME }}
          cache-to: type=gha,mode=max,scope=${{ env.SERVICE_NAME }}
          build-args: |
            BUILDPLATFORM=${{ steps.build.outputs.platform }}
            TARGETPLATFORM=${{ steps.build.outputs.platform }}
      
      - name: Security scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.build.outputs.digest }}
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
      
      - name: Verify distroless image
        run: |
          # Verify image is properly distroless
          if docker run --rm ${{ steps.build.outputs.tags }} /bin/sh -c "echo 'Shell available'" 2>/dev/null; then
            echo "❌ Image has shell access (not distroless)"
            exit 1
          else
            echo "✅ Image is properly distroless"
          fi
          
          # Verify non-root user
          USER_ID=$(docker run --rm ${{ steps.build.outputs.tags }} python3 -c "import os; print(os.getuid())")
          if [ "$USER_ID" = "65532" ]; then
            echo "✅ Image runs as non-root user (UID 65532)"
          else
            echo "❌ Image does not run as non-root user (UID: $USER_ID)"
            exit 1
          fi
```

---

## Container Registry Workflow

### Registry Configuration

```yaml
# Registry configuration for different environments
registries:
  development:
    url: "ghcr.io/hamigames/lucid"
    auth_method: "github_token"
    
  staging:
    url: "pickme/lucid"
    auth_method: "docker_credentials"
    
  production:
    url: "pickme/lucid"
    auth_method: "docker_credentials"
    security_scanning: true
```

### Image Tagging Strategy

```bash
#!/bin/bash
# tag-images.sh - Image tagging strategy

# Semantic versioning tags
VERSION="1.0.0"
BUILD_NUMBER="${GITHUB_RUN_NUMBER:-$(date +%s)}"
COMMIT_SHA="${GITHUB_SHA:-$(git rev-parse HEAD)}"

# Generate tags
TAGS=(
    "$REGISTRY/$SERVICE_NAME:$VERSION"           # Semantic version
    "$REGISTRY/$SERVICE_NAME:$VERSION-$BUILD_NUMBER"  # Version with build
    "$REGISTRY/$SERVICE_NAME:latest"             # Latest stable
    "$REGISTRY/$SERVICE_NAME:main"               # Main branch
    "$REGISTRY/$SERVICE_NAME:$COMMIT_SHA"        # Commit SHA
)

# Tag and push images
for tag in "${TAGS[@]}"; do
    echo "Tagging image: $tag"
    docker tag $REGISTRY/$SERVICE_NAME:latest $tag
    docker push $tag
done

echo "All images tagged and pushed successfully!"
```

---

## Container Orchestration with Docker Compose

### Production Docker Compose

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  tron-payment-service:
    image: pickme/lucid:tron-payment-service:${VERSION:-latest}
    container_name: tron-payment-service
    restart: unless-stopped
    
    # Environment configuration
    environment:
      - LUCID_ENV=production
      - SERVICE_NAME=tron-payment-service
      - SERVICE_PORT=8090
      - TRON_NETWORK=mainnet
      - MONGO_URL=${MONGO_URL}
      - TOR_PROXY=${TOR_PROXY_URL}
    
    # Volume mounts
    volumes:
      - ./configs/secrets:/run/secrets:ro
      - ./logs/tron-payment:/app/logs
      - ./tmp/tron-payment:/app/tmp
    
    # Network configuration
    networks:
      - wallet_plane
      - tor_network
    
    # Health checks
    healthcheck:
      test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8090/health').read()\""]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    # Resource limits
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
    
    # Dependencies
    depends_on:
      mongo:
        condition: service_healthy
      tor-proxy:
        condition: service_healthy

  mongo:
    image: mongo:7.0
    container_name: lucid-mongo-payments
    restart: unless-stopped
    
    environment:
      - MONGO_INITDB_ROOT_USERNAME=${MONGO_ROOT_USERNAME}
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD}
      - MONGO_INITDB_DATABASE=lucid_payments
    
    volumes:
      - mongo_payments_data:/data/db
      - ./scripts/database/init_payment_collections.js:/docker-entrypoint-initdb.d/init.js:ro
    
    command: ["mongod", "--replSet", "rs0", "--bind_ip_all"]
    
    healthcheck:
      test: ["CMD-SHELL", "mongosh --eval 'db.runCommand({ping: 1})' --quiet"]
      interval: 30s
      timeout: 10s
      start_period: 30s
      retries: 3
    
    networks:
      - wallet_plane
      - chain_plane

  tor-proxy:
    image: alpine:3.18
    container_name: lucid-tor-payment
    restart: unless-stopped
    
    volumes:
      - ./configs/tor/torrc.production:/etc/tor/torrc:ro
    
    expose:
      - "9050"
      - "9051"
    
    command: ["sh", "-c", "apk add --no-cache tor curl && tor -f /etc/tor/torrc"]
    
    healthcheck:
      test: ["CMD-SHELL", "curl -f --socks5 localhost:9050 http://httpbin.org/ip"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    
    networks:
      - tor_network

networks:
  wallet_plane:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.30.0.0/16
          gateway: 172.30.0.1
  
  chain_plane:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.25.0.0/16
          gateway: 172.25.0.1
  
  tor_network:
    driver: bridge
    internal: false
    ipam:
      config:
        - subnet: 172.35.0.0/16
          gateway: 172.35.0.1

volumes:
  mongo_payments_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/lucid/data/mongo_payments
```

---

## Raspberry Pi Deployment Steps

### Pi-Specific Deployment Script

```bash
#!/bin/bash
# deploy-to-pi.sh - Raspberry Pi deployment script

set -e

# Configuration
PI_HOST="${PI_HOST:-raspberrypi.local}"
PI_USER="${PI_USER:-pickme}"
PI_SSH_KEY="${PI_SSH_KEY:-~/.ssh/pi_key}"
SERVICE_VERSION="${SERVICE_VERSION:-latest}"
BACKUP_DIR="/opt/lucid/backups"
DEPLOY_DIR="/opt/lucid/current"

echo "Deploying TRON Payment Service to Raspberry Pi..."
echo "Host: $PI_HOST"
echo "User: $PI_USER"
echo "Version: $SERVICE_VERSION"

# Test SSH connection
echo "Testing SSH connection..."
ssh -i $PI_SSH_KEY -o ConnectTimeout=10 $PI_USER@$PI_HOST "echo 'SSH connection successful'"

# Create backup of current deployment
echo "Creating backup of current deployment..."
ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << 'EOF'
    if [ -d "/opt/lucid/current" ]; then
        BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
        sudo mkdir -p /opt/lucid/backups
        sudo cp -r /opt/lucid/current "/opt/lucid/backups/$BACKUP_NAME"
        echo "Backup created: $BACKUP_NAME"
    else
        echo "No current deployment found to backup"
    fi
EOF

# Create deployment directory
echo "Creating deployment directory..."
ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << 'EOF'
    sudo mkdir -p /opt/lucid/current
    sudo mkdir -p /opt/lucid/data/mongo_payments
    sudo mkdir -p /opt/lucid/logs/tron-payment
    sudo mkdir -p /opt/lucid/tmp/tron-payment
    sudo mkdir -p /opt/lucid/configs/secrets
    sudo chown -R $USER:$USER /opt/lucid/current
    sudo chown -R $USER:$USER /opt/lucid/logs
    sudo chown -R $USER:$USER /opt/lucid/tmp
EOF

# Copy deployment files
echo "Copying deployment files..."
scp -i $PI_SSH_KEY docker-compose.production.yml $PI_USER@$PI_HOST:/opt/lucid/current/
scp -i $PI_SSH_KEY -r configs/ $PI_USER@$PI_HOST:/opt/lucid/current/
scp -i $PI_SSH_KEY -r scripts/ $PI_USER@$PI_HOST:/opt/lucid/current/

# Copy environment file
echo "Copying environment configuration..."
scp -i $PI_SSH_KEY .env.production $PI_USER@$PI_HOST:/opt/lucid/current/.env

# Login to registry on Pi
echo "Logging into container registry on Pi..."
ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
    echo "$DOCKER_REGISTRY_PASSWORD" | docker login $DOCKER_REGISTRY_URL -u $DOCKER_REGISTRY_USERNAME --password-stdin
EOF

# Pull latest images
echo "Pulling latest images..."
ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
    cd /opt/lucid/current
    docker-compose -f docker-compose.production.yml pull
EOF

# Stop existing services
echo "Stopping existing services..."
ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
    cd /opt/lucid/current
    docker-compose -f docker-compose.production.yml down || true
EOF

# Start new services
echo "Starting new services..."
ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
    cd /opt/lucid/current
    docker-compose -f docker-compose.production.yml up -d
EOF

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
    cd /opt/lucid/current
    timeout 300 bash -c 'until docker-compose -f docker-compose.production.yml ps | grep -q "healthy"; do sleep 10; done'
EOF

# Verify deployment
echo "Verifying deployment..."
ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
    cd /opt/lucid/current
    
    # Check service status
    echo "Service Status:"
    docker-compose -f docker-compose.production.yml ps
    
    # Check health endpoints
    echo "Health Check:"
    docker exec tron-payment-service python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8090/health').read().decode())"
    
    # Check logs
    echo "Recent Logs:"
    docker-compose -f docker-compose.production.yml logs --tail=20 tron-payment-service
EOF

echo "Deployment completed successfully!"
```

### Pi-Specific Configuration

```yaml
# docker-compose.pi.yml - Raspberry Pi specific overrides
version: '3.8'

services:
  tron-payment-service:
    # Pi-specific resource limits
    deploy:
      resources:
        limits:
          memory: 512M  # Reduced for Pi
          cpus: '0.25'
        reservations:
          memory: 256M
          cpus: '0.1'
    
    # Pi-specific environment variables
    environment:
      - LUCID_ENV=production
      - PLATFORM=raspberry-pi
      - WORKER_THREADS=1  # Single worker for Pi
      - LOG_LEVEL=INFO    # Reduced logging for Pi

  mongo:
    # Pi-specific MongoDB configuration
    deploy:
      resources:
        limits:
          memory: 512M  # Reduced for Pi
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    
    # Pi-specific MongoDB settings
    command: [
      "mongod",
      "--replSet", "rs0",
      "--bind_ip_all",
      "--wiredTigerCacheSizeGB", "0.25",  # Reduced cache for Pi
      "--maxConns", "50"                  # Reduced connections for Pi
    ]
```

---

## Environment-Specific Configurations

### Development Environment

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  tron-payment-service:
    image: pickme/lucid:tron-payment-service:dev
    environment:
      - LUCID_ENV=development
      - TRON_NETWORK=shasta  # Testnet
      - LOG_LEVEL=DEBUG
      - DEBUG=true
      - RELOAD=true
    
    volumes:
      - ./payment-systems/tron-payment-service:/app:ro
      - ./configs/dev:/app/configs:ro
      - ./logs/dev:/app/logs
    
    command: ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--reload"]
    
    ports:
      - "8090:8090"  # Expose for development
    
    networks:
      - dev_network

networks:
  dev_network:
    driver: bridge
```

### Staging Environment

```yaml
# docker-compose.staging.yml
version: '3.8'

services:
  tron-payment-service:
    image: pickme/lucid:tron-payment-service:staging
    environment:
      - LUCID_ENV=staging
      - TRON_NETWORK=shasta  # Testnet for staging
      - LOG_LEVEL=INFO
      - DEBUG=false
    
    # Staging-specific configuration
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'
        reservations:
          memory: 256M
          cpus: '0.1'
    
    networks:
      - staging_network

networks:
  staging_network:
    driver: bridge
    internal: false  # Allow external access for testing
```

### Production Environment

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  tron-payment-service:
    image: pickme/lucid:tron-payment-service:production
    environment:
      - LUCID_ENV=production
      - TRON_NETWORK=mainnet
      - LOG_LEVEL=WARNING
      - DEBUG=false
      - SECURE_MODE=true
    
    # Production-specific configuration
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
    
    # Security hardening
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    
    networks:
      - production_network

networks:
  production_network:
    driver: bridge
    internal: true  # No external access
```

---

## Secrets Deployment Workflow

### SOPS-Based Secrets Management

```bash
#!/bin/bash
# deploy-secrets.sh - Secrets deployment script

set -e

ENVIRONMENT="${1:-development}"
SECRETS_DIR="./configs/secrets"
TARGET_DIR="/opt/lucid/configs/secrets"

echo "Deploying secrets for environment: $ENVIRONMENT"

# Validate SOPS is available
if ! command -v sops &> /dev/null; then
    echo "❌ SOPS not found. Please install SOPS first."
    exit 1
fi

# Validate secrets file exists
SECRETS_FILE="$SECRETS_DIR/$ENVIRONMENT.enc.yaml"
if [ ! -f "$SECRETS_FILE" ]; then
    echo "❌ Secrets file not found: $SECRETS_FILE"
    exit 1
fi

# Decrypt and validate secrets
echo "Validating secrets file..."
sops -d "$SECRETS_FILE" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Secrets file is valid"
else
    echo "❌ Secrets file validation failed"
    exit 1
fi

# Deploy to target environment
if [ "$ENVIRONMENT" = "production" ]; then
    # Production deployment
    echo "Deploying to production environment..."
    
    # Copy encrypted secrets
    scp -i $PI_SSH_KEY "$SECRETS_FILE" $PI_USER@$PI_HOST:$TARGET_DIR/
    
    # Set proper permissions
    ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
        sudo chown root:root $TARGET_DIR/$ENVIRONMENT.enc.yaml
        sudo chmod 600 $TARGET_DIR/$ENVIRONMENT.enc.yaml
        sudo chattr +i $TARGET_DIR/$ENVIRONMENT.enc.yaml  # Make immutable
EOF
    
    echo "✅ Secrets deployed to production"
    
else
    # Development/staging deployment
    echo "Deploying to $ENVIRONMENT environment..."
    
    # Create target directory
    mkdir -p "$TARGET_DIR"
    
    # Copy secrets
    cp "$SECRETS_FILE" "$TARGET_DIR/"
    
    # Set permissions
    chmod 600 "$TARGET_DIR/$ENVIRONMENT.enc.yaml"
    
    echo "✅ Secrets deployed to $ENVIRONMENT"
fi

echo "Secrets deployment completed successfully!"
```

### Environment-Specific Secrets

```yaml
# configs/secrets/development.enc.yaml (SOPS encrypted)
tron_private_key: |
  -----BEGIN PRIVATE KEY-----
  # ... development private key ...
  -----END PRIVATE KEY-----

internal_auth_secret: "dev_secret_key"
mongo_password: "dev_password"
api_keys:
  tron_grid_api_key: "dev_api_key"
  monitoring_api_key: "dev_monitoring_key"

# configs/secrets/staging.enc.yaml (SOPS encrypted)
tron_private_key: |
  -----BEGIN PRIVATE KEY-----
  # ... staging private key ...
  -----END PRIVATE KEY-----

internal_auth_secret: "staging_secret_key"
mongo_password: "staging_password"
api_keys:
  tron_grid_api_key: "staging_api_key"
  monitoring_api_key: "staging_monitoring_key"

# configs/secrets/production.enc.yaml (SOPS encrypted)
tron_private_key: |
  -----BEGIN PRIVATE KEY-----
  # ... production private key ...
  -----END PRIVATE KEY-----

internal_auth_secret: "production_secret_key"
mongo_password: "production_password"
api_keys:
  tron_grid_api_key: "production_api_key"
  monitoring_api_key: "production_monitoring_key"
```

---

## Pre-Deployment Validation Checklist

### Validation Script

```bash
#!/bin/bash
# pre-deployment-validation.sh

set -e

echo "Running pre-deployment validation..."

# Check required tools
echo "Checking required tools..."
required_tools=("docker" "docker-compose" "sops" "ssh")
for tool in "${required_tools[@]}"; do
    if ! command -v $tool &> /dev/null; then
        echo "❌ $tool not found"
        exit 1
    else
        echo "✅ $tool found"
    fi
done

# Check Docker daemon
echo "Checking Docker daemon..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker daemon not running"
    exit 1
else
    echo "✅ Docker daemon running"
fi

# Check Docker Compose file
echo "Checking Docker Compose file..."
if [ ! -f "docker-compose.production.yml" ]; then
    echo "❌ Docker Compose file not found"
    exit 1
else
    echo "✅ Docker Compose file found"
fi

# Validate Docker Compose syntax
if docker-compose -f docker-compose.production.yml config > /dev/null 2>&1; then
    echo "✅ Docker Compose syntax valid"
else
    echo "❌ Docker Compose syntax invalid"
    exit 1
fi

# Check environment variables
echo "Checking environment variables..."
required_vars=("MONGO_URL" "TOR_PROXY_URL" "DOCKER_REGISTRY_URL" "DOCKER_REGISTRY_USERNAME")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Environment variable $var not set"
        exit 1
    else
        echo "✅ Environment variable $var set"
    fi
done

# Check secrets files
echo "Checking secrets files..."
if [ ! -f "configs/secrets/production.enc.yaml" ]; then
    echo "❌ Production secrets file not found"
    exit 1
else
    echo "✅ Production secrets file found"
fi

# Validate secrets file
if sops -d configs/secrets/production.enc.yaml > /dev/null 2>&1; then
    echo "✅ Production secrets file valid"
else
    echo "❌ Production secrets file invalid"
    exit 1
fi

# Check SSH connection to Pi
echo "Checking SSH connection to Pi..."
if [ -n "$PI_HOST" ] && [ -n "$PI_USER" ]; then
    if ssh -i $PI_SSH_KEY -o ConnectTimeout=10 $PI_USER@$PI_HOST "echo 'SSH connection successful'" > /dev/null 2>&1; then
        echo "✅ SSH connection to Pi successful"
    else
        echo "❌ SSH connection to Pi failed"
        exit 1
    fi
else
    echo "⚠️ Pi deployment variables not set, skipping SSH check"
fi

# Check image availability
echo "Checking image availability..."
IMAGE_TAG="pickme/lucid:tron-payment-service:latest"
if docker manifest inspect $IMAGE_TAG > /dev/null 2>&1; then
    echo "✅ Image $IMAGE_TAG available"
else
    echo "❌ Image $IMAGE_TAG not available"
    exit 1
fi

echo "✅ All pre-deployment validations passed!"
```

---

## Deployment Execution Steps

### Automated Deployment Script

```bash
#!/bin/bash
# deploy.sh - Complete deployment script

set -e

# Configuration
ENVIRONMENT="${1:-production}"
VERSION="${2:-latest}"
DRY_RUN="${3:-false}"

echo "Starting deployment..."
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"
echo "Dry run: $DRY_RUN"

# Run pre-deployment validation
echo "Running pre-deployment validation..."
./scripts/pre-deployment-validation.sh

# Create deployment backup
echo "Creating deployment backup..."
./scripts/create-backup.sh $ENVIRONMENT

# Deploy secrets
echo "Deploying secrets..."
./scripts/deploy-secrets.sh $ENVIRONMENT

# Deploy application
if [ "$DRY_RUN" = "true" ]; then
    echo "Dry run mode - skipping actual deployment"
    echo "Would deploy:"
    echo "  - Image: pickme/lucid:tron-payment-service:$VERSION"
    echo "  - Environment: $ENVIRONMENT"
    echo "  - Configuration: docker-compose.$ENVIRONMENT.yml"
else
    echo "Deploying application..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        # Production deployment to Pi
        ./scripts/deploy-to-pi.sh $VERSION
    else
        # Local deployment
        docker-compose -f docker-compose.$ENVIRONMENT.yml pull
        docker-compose -f docker-compose.$ENVIRONMENT.yml up -d
    fi
fi

# Run post-deployment validation
echo "Running post-deployment validation..."
./scripts/post-deployment-validation.sh $ENVIRONMENT

echo "Deployment completed successfully!"
```

### Zero-Downtime Deployment

```bash
#!/bin/bash
# zero-downtime-deploy.sh

set -e

VERSION="${1:-latest}"
HEALTH_CHECK_TIMEOUT=300

echo "Starting zero-downtime deployment..."
echo "Version: $VERSION"

# Create new container with new image
echo "Creating new container..."
docker-compose -f docker-compose.production.yml pull tron-payment-service:$VERSION

# Start new container alongside old one
echo "Starting new container..."
docker-compose -f docker-compose.production.yml up -d --scale tron-payment-service=2

# Wait for new container to be healthy
echo "Waiting for new container to be healthy..."
NEW_CONTAINER_ID=$(docker-compose -f docker-compose.production.yml ps -q tron-payment-service | tail -1)

timeout $HEALTH_CHECK_TIMEOUT bash -c "
    until docker exec $NEW_CONTAINER_ID python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8090/health').read()\" > /dev/null 2>&1; do
        echo 'Waiting for new container to be healthy...'
        sleep 10
    done
"

echo "New container is healthy, switching traffic..."

# Stop old container
echo "Stopping old container..."
OLD_CONTAINER_ID=$(docker-compose -f docker-compose.production.yml ps -q tron-payment-service | head -1)
docker stop $OLD_CONTAINER_ID

# Scale back to single container
echo "Scaling back to single container..."
docker-compose -f docker-compose.production.yml up -d --scale tron-payment-service=1

# Remove old container
echo "Removing old container..."
docker rm $OLD_CONTAINER_ID

echo "Zero-downtime deployment completed successfully!"
```

---

## Post-Deployment Verification

### Verification Script

```bash
#!/bin/bash
# post-deployment-validation.sh

set -e

ENVIRONMENT="${1:-production}"

echo "Running post-deployment validation for $ENVIRONMENT..."

# Check service status
echo "Checking service status..."
if [ "$ENVIRONMENT" = "production" ]; then
    # Remote validation
    ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
        cd /opt/lucid/current
        docker-compose -f docker-compose.production.yml ps
EOF
else
    # Local validation
    docker-compose -f docker-compose.$ENVIRONMENT.yml ps
fi

# Check health endpoints
echo "Checking health endpoints..."
if [ "$ENVIRONMENT" = "production" ]; then
    ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
        docker exec tron-payment-service python3 -c "
            import urllib.request
            import json
            response = urllib.request.urlopen('http://localhost:8090/health')
            health_data = json.loads(response.read().decode())
            print('Health Status:', health_data.get('status'))
            print('Service:', health_data.get('service'))
            print('Version:', health_data.get('version'))
        "
EOF
else
    docker exec tron-payment-service python3 -c "
        import urllib.request
        import json
        response = urllib.request.urlopen('http://localhost:8090/health')
        health_data = json.loads(response.read().decode())
        print('Health Status:', health_data.get('status'))
        print('Service:', health_data.get('service'))
        print('Version:', health_data.get('version'))
    "
fi

# Check metrics endpoint
echo "Checking metrics endpoint..."
if [ "$ENVIRONMENT" = "production" ]; then
    ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
        docker exec tron-payment-service python3 -c "
            import urllib.request
            response = urllib.request.urlopen('http://localhost:8090/metrics')
            metrics = response.read().decode()
            print('Metrics endpoint responding:', len(metrics) > 0)
            print('Key metrics found:', 'tron_payment_requests_total' in metrics)
        "
EOF
else
    docker exec tron-payment-service python3 -c "
        import urllib.request
        response = urllib.request.urlopen('http://localhost:8090/metrics')
        metrics = response.read().decode()
        print('Metrics endpoint responding:', len(metrics) > 0)
        print('Key metrics found:', 'tron_payment_requests_total' in metrics)
    "
fi

# Check logs for errors
echo "Checking logs for errors..."
if [ "$ENVIRONMENT" = "production" ]; then
    ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
        cd /opt/lucid/current
        echo "Recent logs:"
        docker-compose -f docker-compose.production.yml logs --tail=50 tron-payment-service | grep -i error || echo "No errors found in recent logs"
EOF
else
    echo "Recent logs:"
    docker-compose -f docker-compose.$ENVIRONMENT.yml logs --tail=50 tron-payment-service | grep -i error || echo "No errors found in recent logs"
fi

# Performance check
echo "Running performance check..."
if [ "$ENVIRONMENT" = "production" ]; then
    ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
        docker exec tron-payment-service python3 -c "
            import time
            import urllib.request
            start_time = time.time()
            response = urllib.request.urlopen('http://localhost:8090/health')
            end_time = time.time()
            print('Response time:', round(end_time - start_time, 3), 'seconds')
        "
EOF
else
    docker exec tron-payment-service python3 -c "
        import time
        import urllib.request
        start_time = time.time()
        response = urllib.request.urlopen('http://localhost:8090/health')
        end_time = time.time()
        print('Response time:', round(end_time - start_time, 3), 'seconds')
    "
fi

echo "✅ Post-deployment validation completed successfully!"
```

---

## Rollback Strategies and Procedures

### Automated Rollback Script

```bash
#!/bin/bash
# rollback.sh - Automated rollback script

set -e

ENVIRONMENT="${1:-production}"
BACKUP_NAME="${2:-latest}"

echo "Starting rollback for $ENVIRONMENT..."
echo "Backup: $BACKUP_NAME"

if [ "$ENVIRONMENT" = "production" ]; then
    # Production rollback
    echo "Rolling back production deployment..."
    
    # Stop current services
    ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
        cd /opt/lucid/current
        docker-compose -f docker-compose.production.yml down
    EOF
    
    # Restore from backup
    ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
        if [ -d "/opt/lucid/backups/$BACKUP_NAME" ]; then
            echo "Restoring from backup: $BACKUP_NAME"
            sudo rm -rf /opt/lucid/current
            sudo cp -r "/opt/lucid/backups/$BACKUP_NAME" /opt/lucid/current
            sudo chown -R $USER:$USER /opt/lucid/current
        else
            echo "Backup not found: $BACKUP_NAME"
            exit 1
        fi
    EOF
    
    # Start services with previous configuration
    ssh -i $PI_SSH_KEY $PI_USER@$PI_HOST << EOF
        cd /opt/lucid/current
        docker-compose -f docker-compose.production.yml up -d
    EOF
    
else
    # Local rollback
    echo "Rolling back local deployment..."
    
    # Stop current services
    docker-compose -f docker-compose.$ENVIRONMENT.yml down
    
    # Restore from backup
    if [ -d "./backups/$BACKUP_NAME" ]; then
        echo "Restoring from backup: $BACKUP_NAME"
        rm -rf ./current
        cp -r "./backups/$BACKUP_NAME" ./current
    else
        echo "Backup not found: $BACKUP_NAME"
        exit 1
    fi
    
    # Start services with previous configuration
    docker-compose -f docker-compose.$ENVIRONMENT.yml up -d
fi

# Verify rollback
echo "Verifying rollback..."
./scripts/post-deployment-validation.sh $ENVIRONMENT

echo "✅ Rollback completed successfully!"
```

### Backup Management

```bash
#!/bin/bash
# manage-backups.sh - Backup management script

ACTION="${1:-list}"
BACKUP_NAME="${2:-}"

case $ACTION in
    "list")
        echo "Available backups:"
        if [ -d "/opt/lucid/backups" ]; then
            ls -la /opt/lucid/backups/ | grep backup-
        else
            echo "No backups found"
        fi
        ;;
    
    "create")
        BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
        echo "Creating backup: $BACKUP_NAME"
        
        mkdir -p /opt/lucid/backups
        cp -r /opt/lucid/current "/opt/lucid/backups/$BACKUP_NAME"
        echo "Backup created: $BACKUP_NAME"
        ;;
    
    "restore")
        if [ -z "$BACKUP_NAME" ]; then
            echo "Usage: $0 restore <backup_name>"
            exit 1
        fi
        
        if [ -d "/opt/lucid/backups/$BACKUP_NAME" ]; then
            echo "Restoring from backup: $BACKUP_NAME"
            rm -rf /opt/lucid/current
            cp -r "/opt/lucid/backups/$BACKUP_NAME" /opt/lucid/current
            echo "Backup restored: $BACKUP_NAME"
        else
            echo "Backup not found: $BACKUP_NAME"
            exit 1
        fi
        ;;
    
    "cleanup")
        echo "Cleaning up old backups..."
        # Keep only last 10 backups
        ls -t /opt/lucid/backups/ | tail -n +11 | xargs -I {} rm -rf /opt/lucid/backups/{}
        echo "Cleanup completed"
        ;;
    
    *)
        echo "Usage: $0 {list|create|restore|cleanup}"
        exit 1
        ;;
esac
```

---

## Troubleshooting Common Deployment Issues

### Common Issues and Solutions

```bash
#!/bin/bash
# troubleshoot-deployment.sh

echo "TRON Payment Service Deployment Troubleshooting"
echo "=============================================="

# Check Docker daemon
echo "1. Checking Docker daemon..."
if docker info > /dev/null 2>&1; then
    echo "✅ Docker daemon is running"
else
    echo "❌ Docker daemon is not running"
    echo "   Solution: Start Docker daemon"
    exit 1
fi

# Check Docker Compose
echo "2. Checking Docker Compose..."
if docker-compose --version > /dev/null 2>&1; then
    echo "✅ Docker Compose is available"
else
    echo "❌ Docker Compose is not available"
    echo "   Solution: Install Docker Compose"
    exit 1
fi

# Check container status
echo "3. Checking container status..."
if docker-compose -f docker-compose.production.yml ps | grep -q "Up"; then
    echo "✅ Containers are running"
else
    echo "❌ Containers are not running"
    echo "   Solution: Check logs with: docker-compose logs"
fi

# Check health endpoints
echo "4. Checking health endpoints..."
if docker exec tron-payment-service python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/health').read()" > /dev/null 2>&1; then
    echo "✅ Health endpoint is responding"
else
    echo "❌ Health endpoint is not responding"
    echo "   Solution: Check service logs and configuration"
fi

# Check network connectivity
echo "5. Checking network connectivity..."
if docker exec tron-payment-service python3 -c "import socket; socket.create_connection(('mongo', 27017), timeout=5)" > /dev/null 2>&1; then
    echo "✅ Database connectivity is working"
else
    echo "❌ Database connectivity is not working"
    echo "   Solution: Check MongoDB container and network configuration"
fi

# Check disk space
echo "6. Checking disk space..."
DISK_USAGE=$(df /opt/lucid | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 90 ]; then
    echo "✅ Disk space is adequate ($DISK_USAGE% used)"
else
    echo "❌ Disk space is low ($DISK_USAGE% used)"
    echo "   Solution: Free up disk space or expand storage"
fi

# Check memory usage
echo "7. Checking memory usage..."
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEMORY_USAGE -lt 90 ]; then
    echo "✅ Memory usage is adequate ($MEMORY_USAGE% used)"
else
    echo "❌ Memory usage is high ($MEMORY_USAGE% used)"
    echo "   Solution: Check for memory leaks or increase memory allocation"
fi

echo "Troubleshooting completed!"
```

---

## References

- [06b_DISTROLESS_DEPLOYMENT.md](06b_DISTROLESS_DEPLOYMENT.md) - Container deployment
- [10_MONITORING_ALERTING.md](10_MONITORING_ALERTING.md) - Post-deployment monitoring
- [Docker Compose Documentation](https://docs.docker.com/compose/) - Container orchestration
- [SOPS Documentation](https://github.com/mozilla/sops) - Secrets management
- [GitHub Actions](https://docs.github.com/en/actions) - CI/CD pipelines

---

**Document Status**: [IN PROGRESS]  
**Last Review**: 2025-10-12  
**Next Review**: 2025-11-12
