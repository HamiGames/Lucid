#!/bin/bash
# Path: scripts/deployment/deploy-distroless-complete.sh
# Complete Distroless Deployment Orchestrator
# Orchestrates the entire distroless deployment process
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
log_info "Complete Distroless Deployment Orchestrator"
log_info "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "configs/docker/distroless/distroless-runtime-config.yml" ]; then
    log_error "Not in project root directory!"
    log_error "Please run from: $PROJECT_ROOT"
    exit 1
fi

# Function to run script with error handling
run_script() {
    local script_name=$1
    local script_path=$2
    local description=$3
    
    log_info "Running: $script_name"
    log_info "Description: $description"
    echo ""
    
    if [ ! -f "$script_path" ]; then
        log_error "Script not found: $script_path"
        return 1
    fi
    
    # Make script executable
    chmod +x "$script_path"
    
    # Run script
    if bash "$script_path"; then
        log_success "$script_name completed successfully"
        return 0
    else
        log_error "$script_name failed"
        return 1
    fi
}

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
    
    # Check required directories
    for dir in "configs/environment" "configs/docker/distroless" "configs/docker/multi-stage" "scripts/deployment"; do
        if [ ! -d "$dir" ]; then
            log_error "Required directory not found: $dir"
            exit 1
        fi
    done
    log_success "Required directories found"
    
    # Check required scripts
    for script in "scripts/config/generate-all-env-complete.sh" "scripts/deployment/create-distroless-networks.sh" "scripts/deployment/create-distroless-env.sh"; do
        if [ ! -f "$script" ]; then
            log_error "Required script not found: $script"
            exit 1
        fi
    done
    log_success "Required scripts found"
    
    echo ""
}

# Function to show deployment options
show_deployment_options() {
    log_info "Deployment Options:"
    echo ""
    echo "1. Full Deployment (Recommended)"
    echo "   - All networks, environment files, distroless base, and Lucid services"
    echo "   - Complete production-ready deployment"
    echo ""
    echo "2. Networks Only"
    echo "   - Create all required networks"
    echo "   - Generate environment files"
    echo "   - Skip service deployment"
    echo ""
    echo "3. Distroless Base Only"
    echo "   - Deploy distroless base infrastructure"
    echo "   - Skip Lucid services deployment"
    echo ""
    echo "4. Lucid Services Only"
    echo "   - Deploy Lucid services (requires networks and .env files)"
    echo "   - Skip distroless base infrastructure"
    echo ""
    echo "5. Multi-Stage Build Only"
    echo "   - Deploy multi-stage build infrastructure"
    echo "   - For CI/CD and development workflows"
    echo ""
}

# Function to execute full deployment
execute_full_deployment() {
    log_info "Executing Full Distroless Deployment"
    echo ""
    
    # Step 1: Generate environment files
    if ! run_script \
        "Generate Environment Files" \
        "scripts/config/generate-all-env-complete.sh" \
        "Generate secure .env files with cryptographic values"; then
        log_error "Environment file generation failed"
        exit 1
    fi
    echo ""
    
    # Step 2: Create networks
    if ! run_script \
        "Create Enhanced Networks" \
        "scripts/deployment/create-distroless-networks.sh" \
        "Create all 6 Docker networks (3 main + 3 distroless/multi-stage)"; then
        log_error "Network creation failed"
        exit 1
    fi
    echo ""
    
    # Step 3: Create distroless environment
    if ! run_script \
        "Create Distroless Environment" \
        "scripts/deployment/create-distroless-env.sh" \
        "Create distroless-specific .env file with secure values"; then
        log_error "Distroless environment creation failed"
        exit 1
    fi
    echo ""
    
    # Step 4: Deploy distroless base infrastructure
    if ! run_script \
        "Deploy Distroless Base" \
        "scripts/deployment/deploy-distroless-base.sh" \
        "Deploy distroless runtime, development, and security configurations"; then
        log_error "Distroless base deployment failed"
        exit 1
    fi
    echo ""
    
    # Step 5: Deploy Lucid services
    if ! run_script \
        "Deploy Lucid Services" \
        "scripts/deployment/deploy-lucid-services.sh" \
        "Deploy Lucid services using pre-built distroless images"; then
        log_error "Lucid services deployment failed"
        exit 1
    fi
    echo ""
    
    # Step 6: Deploy multi-stage build (optional)
    read -p "Deploy multi-stage build infrastructure? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! run_script \
            "Deploy Multi-Stage Build" \
            "scripts/deployment/deploy-multi-stage-build.sh" \
            "Deploy multi-stage build infrastructure for CI/CD"; then
            log_warning "Multi-stage build deployment failed (continuing...)"
        fi
        echo ""
    fi
    
    log_success "Full deployment completed successfully!"
}

# Function to execute networks only
execute_networks_only() {
    log_info "Executing Networks-Only Deployment"
    echo ""
    
    # Step 1: Generate environment files
    if ! run_script \
        "Generate Environment Files" \
        "scripts/config/generate-all-env-complete.sh" \
        "Generate secure .env files with cryptographic values"; then
        log_error "Environment file generation failed"
        exit 1
    fi
    echo ""
    
    # Step 2: Create networks
    if ! run_script \
        "Create Enhanced Networks" \
        "scripts/deployment/create-distroless-networks.sh" \
        "Create all 6 Docker networks (3 main + 3 distroless/multi-stage)"; then
        log_error "Network creation failed"
        exit 1
    fi
    echo ""
    
    # Step 3: Create distroless environment
    if ! run_script \
        "Create Distroless Environment" \
        "scripts/deployment/create-distroless-env.sh" \
        "Create distroless-specific .env file with secure values"; then
        log_error "Distroless environment creation failed"
        exit 1
    fi
    echo ""
    
    log_success "Networks-only deployment completed successfully!"
    log_info "You can now deploy services manually:"
    log_info "  • bash scripts/deployment/deploy-distroless-base.sh"
    log_info "  • bash scripts/deployment/deploy-lucid-services.sh"
}

# Function to execute distroless base only
execute_distroless_base_only() {
    log_info "Executing Distroless Base-Only Deployment"
    echo ""
    
    # Check if networks exist
    if ! docker network ls | grep -q "lucid-pi-network"; then
        log_error "Required networks not found!"
        log_error "Please run networks-only deployment first:"
        log_error "  bash scripts/deployment/deploy-distroless-complete.sh networks"
        exit 1
    fi
    
    # Check if .env files exist
    if [ ! -f "configs/environment/.env.distroless" ]; then
        log_error "Distroless .env file not found!"
        log_error "Please run networks-only deployment first:"
        log_error "  bash scripts/deployment/deploy-distroless-complete.sh networks"
        exit 1
    fi
    
    # Deploy distroless base
    if ! run_script \
        "Deploy Distroless Base" \
        "scripts/deployment/deploy-distroless-base.sh" \
        "Deploy distroless runtime, development, and security configurations"; then
        log_error "Distroless base deployment failed"
        exit 1
    fi
    echo ""
    
    log_success "Distroless base deployment completed successfully!"
}

# Function to execute Lucid services only
execute_lucid_services_only() {
    log_info "Executing Lucid Services-Only Deployment"
    echo ""
    
    # Check if networks exist
    if ! docker network ls | grep -q "lucid-pi-network"; then
        log_error "Required networks not found!"
        log_error "Please run networks-only deployment first:"
        log_error "  bash scripts/deployment/deploy-distroless-complete.sh networks"
        exit 1
    fi
    
    # Check if .env files exist
    for env_file in "configs/environment/.env.foundation" "configs/environment/.env.core" "configs/environment/.env.application" "configs/environment/.env.support"; do
        if [ ! -f "$env_file" ]; then
            log_error "Required .env file not found: $env_file"
            log_error "Please run networks-only deployment first:"
            log_error "  bash scripts/deployment/deploy-distroless-complete.sh networks"
            exit 1
        fi
    done
    
    # Deploy Lucid services
    if ! run_script \
        "Deploy Lucid Services" \
        "scripts/deployment/deploy-lucid-services.sh" \
        "Deploy Lucid services using pre-built distroless images"; then
        log_error "Lucid services deployment failed"
        exit 1
    fi
    echo ""
    
    log_success "Lucid services deployment completed successfully!"
}

# Function to execute multi-stage build only
execute_multi_stage_build_only() {
    log_info "Executing Multi-Stage Build-Only Deployment"
    echo ""
    
    # Check if networks exist
    if ! docker network ls | grep -q "lucid-multi-stage-network"; then
        log_error "Required networks not found!"
        log_error "Please run networks-only deployment first:"
        log_error "  bash scripts/deployment/deploy-distroless-complete.sh networks"
        exit 1
    fi
    
    # Deploy multi-stage build
    if ! run_script \
        "Deploy Multi-Stage Build" \
        "scripts/deployment/deploy-multi-stage-build.sh" \
        "Deploy multi-stage build infrastructure for CI/CD"; then
        log_error "Multi-stage build deployment failed"
        exit 1
    fi
    echo ""
    
    log_success "Multi-stage build deployment completed successfully!"
}

# Main execution
main() {
    # Check prerequisites
    check_prerequisites
    
    # Show deployment options
    show_deployment_options
    
    # Get deployment option
    local deployment_option=${1:-"full"}
    
    case $deployment_option in
        "full"|"1")
            execute_full_deployment
            ;;
        "networks"|"2")
            execute_networks_only
            ;;
        "distroless"|"3")
            execute_distroless_base_only
            ;;
        "lucid"|"4")
            execute_lucid_services_only
            ;;
        "multi-stage"|"5")
            execute_multi_stage_build_only
            ;;
        *)
            log_error "Invalid deployment option: $deployment_option"
            log_info "Valid options: full, networks, distroless, lucid, multi-stage"
            log_info "Usage: $0 [full|networks|distroless|lucid|multi-stage]"
            exit 1
            ;;
    esac
    
    echo ""
    log_success "========================================"
    log_success "Deployment completed successfully!"
    log_success "========================================"
    echo ""
    log_info "Next steps:"
    log_info "  1. Test service endpoints manually"
    log_info "  2. Configure monitoring and logging"
    log_info "  3. Set up backup procedures"
    log_info "  4. Review security configurations"
    echo ""
}

# Run main function with all arguments
main "$@"
