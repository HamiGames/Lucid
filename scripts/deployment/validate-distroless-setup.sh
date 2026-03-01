#!/bin/bash
# Path: scripts/deployment/validate-distroless-setup.sh
# Validate Distroless Setup
# Validates the distroless deployment configuration and environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
log_info "========================================"
log_info "Validating Distroless Setup"
log_info "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "configs/docker/distroless/distroless-runtime-config.yml" ]; then
    log_error "Not in project root directory!"
    log_error "Please run from: /mnt/myssd/Lucid/Lucid"
    exit 1
fi

# Check Docker
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running!"
    exit 1
fi
log_success "Docker is running"

# Check Docker Compose
if ! docker-compose --version > /dev/null 2>&1; then
    log_error "Docker Compose not found!"
    exit 1
fi
log_success "Docker Compose is available"

# Check required files
log_info "Checking required configuration files..."

required_files=(
    "configs/environment/.env.distroless"
    "configs/docker/distroless/distroless.env"
    "configs/docker/distroless/distroless-runtime-config.yml"
    "configs/docker/distroless/test-runtime-config.yml"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        log_success "Found: $file"
    else
        log_error "Missing: $file"
        exit 1
    fi
done

# Check networks
log_info "Checking Docker networks..."

required_networks=(
    "lucid-distroless-production"
    "lucid-pi-network"
)

for network in "${required_networks[@]}"; do
    if docker network ls | grep -q "$network"; then
        log_success "Network exists: $network"
    else
        log_warning "Network missing: $network"
    fi
done

# Test Docker Compose configuration
log_info "Testing Docker Compose configuration..."

if docker-compose \
    --env-file configs/environment/.env.distroless \
    --env-file configs/docker/distroless/distroless.env \
    -f "configs/docker/distroless/test-runtime-config.yml" \
    config > /dev/null 2>&1; then
    log_success "Docker Compose configuration test passed"
else
    log_error "Docker Compose configuration test failed"
    log_error "Run the following command to see detailed errors:"
    log_error "docker-compose --env-file configs/environment/.env.distroless --env-file configs/docker/distroless/distroless.env -f configs/docker/distroless/test-runtime-config.yml config"
    exit 1
fi

# Test actual deployment
log_info "Testing actual deployment..."

if docker-compose \
    --env-file configs/environment/.env.distroless \
    --env-file configs/docker/distroless/distroless.env \
    -f "configs/docker/distroless/test-runtime-config.yml" \
    up -d --remove-orphans; then
    log_success "Test deployment successful"
    
    # Wait a moment
    sleep 5
    
    # Check container status
    if docker-compose -f "configs/docker/distroless/test-runtime-config.yml" ps | grep -q "Up"; then
        log_success "Test containers are running"
    else
        log_warning "Test containers may not be running properly"
    fi
    
    # Clean up
    log_info "Cleaning up test containers..."
    docker-compose \
        --env-file configs/environment/.env.distroless \
        --env-file configs/docker/distroless/distroless.env \
        -f "configs/docker/distroless/test-runtime-config.yml" \
        down --remove-orphans > /dev/null 2>&1 || true
    
    log_success "Test cleanup completed"
else
    log_error "Test deployment failed"
    exit 1
fi

echo ""
log_success "========================================"
log_success "Distroless setup validation completed!"
log_success "========================================"
echo ""
log_info "The distroless deployment should now work properly."
log_info "You can run the full deployment with:"
log_info "  bash scripts/deployment/deploy-distroless-complete.sh full"
echo ""
