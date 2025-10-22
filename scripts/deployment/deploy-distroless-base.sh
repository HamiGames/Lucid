#!/bin/bash
# Path: scripts/deployment/deploy-distroless-base.sh
# Deploy Distroless Base Infrastructure
# Deploys distroless runtime, development, and security configurations
# MUST RUN ON PI CONSOLE

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

# Project root
PROJECT_ROOT="${PROJECT_ROOT:-/mnt/myssd/Lucid/Lucid}"

echo ""
log_info "========================================"
log_info "Deploying Distroless Base Infrastructure"
log_info "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "configs/docker/distroless/distroless-runtime-config.yml" ]; then
    log_error "Not in project root directory!"
    log_error "Please run from: $PROJECT_ROOT"
    exit 1
fi

# Check if distroless .env exists
if [ ! -f "configs/environment/.env.distroless" ]; then
    log_error "Distroless .env file not found!"
    log_error "Please run first: bash scripts/deployment/create-distroless-env.sh"
    exit 1
fi

# Check if distroless.env exists
if [ ! -f "configs/docker/distroless/distroless.env" ]; then
    log_error "Distroless base .env file not found!"
    log_error "Expected: configs/docker/distroless/distroless.env"
    exit 1
fi

log_info "Found required configuration files"
echo ""

# Function to deploy distroless configuration
deploy_distroless_config() {
    local config_file=$1
    local config_name=$2
    local description=$3
    
    log_info "Deploying $config_name..."
    log_info "Description: $description"
    
    # Check if config file exists
    if [ ! -f "$config_file" ]; then
        log_error "Config file not found: $config_file"
        return 1
    fi
    
    # Deploy with environment files
    docker-compose \
        --env-file configs/environment/.env.distroless \
        --env-file configs/docker/distroless/distroless.env \
        -f "$config_file" \
        up -d
    
    if [ $? -eq 0 ]; then
        log_success "$config_name deployed successfully"
        
        # Wait for services to start
        log_info "Waiting for services to initialize..."
        sleep 30
        
        # Check container health
        local containers=$(docker-compose -f "$config_file" ps -q)
        if [ -n "$containers" ]; then
            for container in $containers; do
                local container_name=$(docker inspect --format '{{.Name}}' "$container" | sed 's/^\///')
                local health=$(docker inspect --format '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-healthcheck")
                
                if [ "$health" = "healthy" ]; then
                    log_success "Container $container_name is healthy"
                elif [ "$health" = "no-healthcheck" ]; then
                    log_info "Container $container_name has no health check"
                else
                    log_warning "Container $container_name health status: $health"
                fi
            done
        fi
        
        return 0
    else
        log_error "Failed to deploy $config_name"
        return 1
    fi
}

# Function to verify distroless containers
verify_distroless_containers() {
    log_info "Verifying distroless containers..."
    
    # Check running containers
    local distroless_containers=$(docker ps --format '{{.Names}}' | grep -E 'distroless|multi-stage' || true)
    
    if [ -z "$distroless_containers" ]; then
        log_warning "No distroless containers found running"
        return 1
    fi
    
    echo ""
    log_info "Found distroless containers:"
    echo "$distroless_containers" | while read container; do
        echo "  • $container"
    done
    echo ""
    
    # Test basic Python execution
    log_info "Testing Python execution in distroless containers..."
    echo "$distroless_containers" | while read container; do
        if docker exec "$container" python -c "import sys; print(f'Python {sys.version}'); sys.exit(0)" 2>/dev/null; then
            log_success "Container $container: Python execution successful"
        else
            log_warning "Container $container: Python execution failed"
        fi
    done
    
    return 0
}

# Main deployment process

# Step 1: Deploy distroless runtime configuration
log_info "Step 1: Deploying distroless runtime configuration"
echo ""

if ! deploy_distroless_config \
    "configs/docker/distroless/distroless-runtime-config.yml" \
    "Distroless Runtime" \
    "Main ARM64 runtime, minimal runtime, and ARM64-optimized runtime for Pi 5"; then
    log_error "Failed to deploy distroless runtime"
    exit 1
fi

echo ""

# Step 2: Deploy distroless development configuration (optional)
read -p "Deploy distroless development environment? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Step 2: Deploying distroless development configuration"
    echo ""
    
    if ! deploy_distroless_config \
        "configs/docker/distroless/distroless-development-config.yml" \
        "Distroless Development" \
        "Development environment with hot reload, minimal dev config, and dev tools"; then
        log_warning "Failed to deploy distroless development (continuing...)"
    fi
    
    echo ""
fi

# Step 3: Deploy distroless security configuration (optional)
read -p "Deploy distroless security configuration? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Step 3: Deploying distroless security configuration"
    echo ""
    
    if ! deploy_distroless_config \
        "configs/docker/distroless/distroless-security-config.yml" \
        "Distroless Security" \
        "Security-hardened distroless with AppArmor/Seccomp, minimal secure config, and security monitoring"; then
        log_warning "Failed to deploy distroless security (continuing...)"
    fi
    
    echo ""
fi

# Step 4: Verify deployment
log_info "Step 4: Verifying distroless base infrastructure"
echo ""

if ! verify_distroless_containers; then
    log_warning "Distroless container verification had issues"
fi

echo ""

# Step 5: Show network assignments
log_info "Network assignments:"
docker network ls | grep lucid | while read line; do
    local network_name=$(echo "$line" | awk '{print $2}')
    local network_id=$(echo "$line" | awk '{print $1}')
    echo "  • $network_name (ID: $network_id)"
done

echo ""

# Step 6: Show container status
log_info "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "distroless|multi-stage" || log_info "No distroless containers running"

echo ""

log_success "========================================"
log_success "Distroless base infrastructure deployed!"
log_success "========================================"
echo ""
log_info "Deployed configurations:"
log_info "  • Distroless Runtime - Main ARM64 runtime environment"
log_info "  • Distroless Development - Development environment (if selected)"
log_info "  • Distroless Security - Security-hardened environment (if selected)"
echo ""
log_info "Next steps:"
log_info "  1. Deploy Lucid services:"
log_info "     bash scripts/deployment/deploy-lucid-services.sh"
log_info ""
log_info "  2. Or deploy multi-stage build infrastructure:"
log_info "     bash scripts/deployment/deploy-multi-stage-build.sh"
echo ""
