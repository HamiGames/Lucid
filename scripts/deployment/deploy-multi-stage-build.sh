#!/bin/bash
# Path: scripts/deployment/deploy-multi-stage-build.sh
# Deploy Multi-Stage Build Infrastructure
# Deploys multi-stage build environment for CI/CD and local development
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
log_info "Deploying Multi-Stage Build Infrastructure"
log_info "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "configs/docker/multi-stage/multi-stage-config.yml" ]; then
    log_error "Not in project root directory!"
    log_error "Please run from: $PROJECT_ROOT"
    exit 1
fi

# Check if multi-stage.env exists
if [ ! -f "configs/docker/multi-stage/multi-stage.env" ]; then
    log_error "Multi-stage .env file not found!"
    log_error "Expected: configs/docker/multi-stage/multi-stage.env"
    exit 1
fi

log_info "Found required configuration files"
echo ""

# Function to deploy multi-stage configuration
deploy_multi_stage_config() {
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
    
    # Deploy with environment file
    docker-compose \
        --env-file configs/docker/multi-stage/multi-stage.env \
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
                local status=$(docker inspect --format '{{.State.Status}}' "$container")
                
                if [ "$status" = "running" ]; then
                    if [ "$health" = "healthy" ]; then
                        log_success "Container $container_name is healthy"
                    elif [ "$health" = "no-healthcheck" ]; then
                        log_info "Container $container_name is running (no health check)"
                    else
                        log_warning "Container $container_name health status: $health"
                    fi
                else
                    log_error "Container $container_name status: $status"
                fi
            done
        fi
        
        return 0
    else
        log_error "Failed to deploy $config_name"
        return 1
    fi
}

# Function to verify multi-stage containers
verify_multi_stage_containers() {
    log_info "Verifying multi-stage containers..."
    
    # Check running containers
    local multi_stage_containers=$(docker ps --format '{{.Names}}' | grep -E 'multi-stage|build' || true)
    
    if [ -z "$multi_stage_containers" ]; then
        log_warning "No multi-stage containers found running"
        return 1
    fi
    
    echo ""
    log_info "Found multi-stage containers:"
    echo "$multi_stage_containers" | while read container; do
        echo "  • $container"
    done
    echo ""
    
    # Test basic functionality
    log_info "Testing multi-stage container functionality..."
    echo "$multi_stage_containers" | while read container; do
        if docker exec "$container" python -c "import sys; print(f'Python {sys.version}'); sys.exit(0)" 2>/dev/null; then
            log_success "Container $container: Python execution successful"
        else
            log_warning "Container $container: Python execution failed"
        fi
    done
    
    return 0
}

# Main deployment process

# Step 1: Deploy multi-stage base configuration
log_info "Step 1: Deploying multi-stage base configuration"
echo ""

if ! deploy_multi_stage_config \
    "configs/docker/multi-stage/multi-stage-config.yml" \
    "Multi-Stage Base" \
    "Base multi-stage runtime, development, and builder configurations"; then
    log_error "Failed to deploy multi-stage base"
    exit 1
fi

echo ""

# Step 2: Deploy multi-stage build configuration (optional)
read -p "Deploy multi-stage build tools? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Step 2: Deploying multi-stage build tools"
    echo ""
    
    if ! deploy_multi_stage_config \
        "configs/docker/multi-stage/multi-stage-build-config.yml" \
        "Multi-Stage Build Tools" \
        "Build orchestrator, layer analyzer, cache optimizer, and build validator"; then
        log_warning "Failed to deploy multi-stage build tools (continuing...)"
    fi
    
    echo ""
fi

# Step 3: Deploy multi-stage development configuration (optional)
read -p "Deploy multi-stage development environment? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Step 3: Deploying multi-stage development environment"
    echo ""
    
    if ! deploy_multi_stage_config \
        "configs/docker/multi-stage/multi-stage-development-config.yml" \
        "Multi-Stage Development" \
        "Development environment with debugging capabilities and development database"; then
        log_warning "Failed to deploy multi-stage development (continuing...)"
    fi
    
    echo ""
fi

# Step 4: Deploy multi-stage testing configuration (optional)
read -p "Deploy multi-stage testing environment? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Step 4: Deploying multi-stage testing environment"
    echo ""
    
    if ! deploy_multi_stage_config \
        "configs/docker/multi-stage/multi-stage-testing-config.yml" \
        "Multi-Stage Testing" \
        "Testing environment with test database, build testing, and result aggregation"; then
        log_warning "Failed to deploy multi-stage testing (continuing...)"
    fi
    
    echo ""
fi

# Step 5: Deploy multi-stage runtime configuration (optional)
read -p "Deploy multi-stage runtime configuration? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Step 5: Deploying multi-stage runtime configuration"
    echo ""
    
    if ! deploy_multi_stage_config \
        "configs/docker/multi-stage/multi-stage-runtime-config.yml" \
        "Multi-Stage Runtime" \
        "Production runtime, development runtime, and monitoring runtime"; then
        log_warning "Failed to deploy multi-stage runtime (continuing...)"
    fi
    
    echo ""
fi

# Step 6: Verify deployment
log_info "Step 6: Verifying multi-stage build infrastructure"
echo ""

if ! verify_multi_stage_containers; then
    log_warning "Multi-stage container verification had issues"
fi

echo ""

# Step 7: Show network assignments
log_info "Network assignments:"
docker network ls | grep lucid | while read line; do
    local network_name=$(echo "$line" | awk '{print $2}')
    local network_id=$(echo "$line" | awk '{print $1}')
    echo "  • $network_name (ID: $network_id)"
done

echo ""

# Step 8: Show container status
log_info "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "multi-stage|build" || log_info "No multi-stage containers running"

echo ""

# Step 9: Show build capabilities
log_info "Multi-stage build capabilities:"
log_info "  • Layer optimization and caching"
log_info "  • Build validation and testing"
log_info "  • Development tools and debugging"
log_info "  • Performance monitoring and analytics"
log_info "  • Test result aggregation"
echo ""

log_success "========================================"
log_success "Multi-stage build infrastructure deployed!"
log_success "========================================"
echo ""
log_info "Deployed configurations:"
log_info "  • Multi-Stage Base - Runtime, development, and builder configurations"
log_info "  • Multi-Stage Build Tools - Build orchestrator and optimization tools (if selected)"
log_info "  • Multi-Stage Development - Development environment with debugging (if selected)"
log_info "  • Multi-Stage Testing - Testing environment with test database (if selected)"
log_info "  • Multi-Stage Runtime - Production runtime and monitoring (if selected)"
echo ""
log_info "Network: lucid-multi-stage-network (172.25.0.0/16)"
echo ""
log_info "Usage examples:"
log_info "  1. Build optimized images:"
log_info "     docker-compose -f configs/docker/multi-stage/multi-stage-build-config.yml up -d"
log_info ""
log_info "  2. Run development environment:"
log_info "     docker-compose -f configs/docker/multi-stage/multi-stage-development-config.yml up -d"
log_info ""
log_info "  3. Execute tests:"
log_info "     docker-compose -f configs/docker/multi-stage/multi-stage-testing-config.yml up -d"
echo ""
log_info "Next steps:"
log_info "  1. Configure CI/CD pipelines to use multi-stage builds"
log_info "  2. Set up automated testing with multi-stage testing environment"
log_info "  3. Monitor build performance and optimize layer caching"
log_info "  4. Integrate with existing Lucid services for development workflows"
echo ""
