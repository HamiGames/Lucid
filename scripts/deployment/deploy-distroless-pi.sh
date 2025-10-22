#!/bin/bash
# Path: scripts/deployment/deploy-distroless-pi.sh
# Distroless Deployment for Raspberry Pi Console
# MUST RUN ON PI CONSOLE - Deploys distroless containers using pre-built images

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
log_info "Distroless Deployment for Raspberry Pi"
log_info "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "configs/docker/distroless/distroless-runtime-config.yml" ]; then
    log_error "Not in project root directory!"
    log_error "Please run from: $PROJECT_ROOT"
    exit 1
fi

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running!"
        log_error "Please start Docker: sudo systemctl start docker"
        exit 1
    fi
    log_success "Docker is running"
    
    # Check Docker Compose
    if ! docker-compose --version > /dev/null 2>&1; then
        log_error "Docker Compose not found!"
        log_error "Please install Docker Compose"
        exit 1
    fi
    log_success "Docker Compose is available"
    
    # Check required networks
    if ! docker network ls | grep -q "lucid-distroless-production"; then
        log_error "Required network not found: lucid-distroless-production"
        log_error "Please create networks first:"
        log_error "  bash scripts/deployment/create-distroless-networks.sh"
        exit 1
    fi
    log_success "Required networks found"
    
    # Check required images
    local required_images=(
        "pickme/lucid-base:latest-arm64"
        "pickme/lucid-auth-service:latest-arm64"
        "pickme/lucid-mongodb:latest-arm64"
        "pickme/lucid-redis:latest-arm64"
    )
    
    for image in "${required_images[@]}"; do
        if ! docker image inspect "$image" > /dev/null 2>&1; then
            log_error "Required image not found: $image"
            log_error "Please pull the required images first:"
            log_error "  docker pull $image"
            exit 1
        fi
    done
    log_success "Required images found"
    
    echo ""
}

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
        up -d --remove-orphans
    
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

# Function to show deployment options
show_deployment_options() {
    log_info "Distroless Deployment Options:"
    echo ""
    echo "1. Runtime Deployment (Recommended)"
    echo "   - Deploy distroless runtime containers"
    echo "   - Production-ready configuration"
    echo ""
    echo "2. Development Deployment"
    echo "   - Deploy development distroless containers"
    echo "   - Debug-friendly configuration"
    echo ""
    echo "3. Security Deployment"
    echo "   - Deploy security-hardened distroless containers"
    echo "   - Maximum security configuration"
    echo ""
    echo "4. Test Deployment"
    echo "   - Deploy test distroless containers"
    echo "   - For testing and validation"
    echo ""
}

# Function to execute runtime deployment
execute_runtime_deployment() {
    log_info "Executing Distroless Runtime Deployment"
    echo ""
    
    if ! deploy_distroless_config \
        "configs/docker/distroless/distroless-runtime-config.yml" \
        "Distroless Runtime" \
        "Production distroless runtime containers"; then
        log_error "Runtime deployment failed"
        exit 1
    fi
    
    log_success "Runtime deployment completed successfully!"
}

# Function to execute development deployment
execute_development_deployment() {
    log_info "Executing Distroless Development Deployment"
    echo ""
    
    if ! deploy_distroless_config \
        "configs/docker/distroless/distroless-development-config.yml" \
        "Distroless Development" \
        "Development distroless containers"; then
        log_error "Development deployment failed"
        exit 1
    fi
    
    log_success "Development deployment completed successfully!"
}

# Function to execute security deployment
execute_security_deployment() {
    log_info "Executing Distroless Security Deployment"
    echo ""
    
    if ! deploy_distroless_config \
        "configs/docker/distroless/distroless-security-config.yml" \
        "Distroless Security" \
        "Security-hardened distroless containers"; then
        log_error "Security deployment failed"
        exit 1
    fi
    
    log_success "Security deployment completed successfully!"
}

# Function to execute test deployment
execute_test_deployment() {
    log_info "Executing Distroless Test Deployment"
    echo ""
    
    if ! deploy_distroless_config \
        "configs/docker/distroless/test-runtime-config.yml" \
        "Distroless Test" \
        "Test distroless containers"; then
        log_error "Test deployment failed"
        exit 1
    fi
    
    log_success "Test deployment completed successfully!"
}

# Main execution
main() {
    # Check prerequisites
    check_prerequisites
    
    # Show deployment options
    show_deployment_options
    
    # Get deployment option
    local deployment_option=${1:-"runtime"}
    
    case $deployment_option in
        "runtime"|"1")
            execute_runtime_deployment
            ;;
        "development"|"2")
            execute_development_deployment
            ;;
        "security"|"3")
            execute_security_deployment
            ;;
        "test"|"4")
            execute_test_deployment
            ;;
        *)
            log_error "Invalid deployment option: $deployment_option"
            log_info "Valid options: runtime, development, security, test"
            log_info "Usage: $0 [runtime|development|security|test]"
            exit 1
            ;;
    esac
    
    echo ""
    log_success "========================================"
    log_success "Distroless deployment completed!"
    log_success "========================================"
    echo ""
    log_info "Next steps:"
    log_info "  1. Verify container health: docker ps"
    log_info "  2. Check logs: docker logs <container_name>"
    log_info "  3. Test endpoints manually"
    log_info "  4. Configure monitoring and logging"
    echo ""
}

# Run main function with all arguments
main "$@"
