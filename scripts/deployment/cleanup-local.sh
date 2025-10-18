#!/bin/bash
# Lucid Local Development Cleanup Script
# Cleans up all Lucid services and resources for local development
# Based on Step 50 requirements from BUILD_REQUIREMENTS_GUIDE.md

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
DATA_DIR="${PROJECT_ROOT}/data"
CONFIG_DIR="${PROJECT_ROOT}/configs"

# Default parameters
ACTION="${1:-clean}"
ENVIRONMENT="${2:-dev}"
FORCE="${3:-false}"
DRY_RUN="${4:-false}"

# Service definitions for cleanup
declare -A LUCID_SERVICES=(
    # Phase 1: Foundation
    [lucid-mongodb]="MongoDB database service"
    [lucid-redis]="Redis cache service"
    [lucid-elasticsearch]="Elasticsearch search service"
    [lucid-auth-service]="Authentication service"
    
    # Phase 2: Core Services
    [lucid-api-gateway]="API Gateway service"
    [lucid-blockchain-engine]="Blockchain core engine"
    [lucid-session-anchoring]="Session anchoring service"
    [lucid-block-manager]="Block manager service"
    [lucid-data-chain]="Data chain service"
    [lucid-service-mesh]="Service mesh controller"
    
    # Phase 3: Application Services
    [lucid-session-pipeline]="Session pipeline manager"
    [lucid-session-recorder]="Session recorder service"
    [lucid-session-processor]="Session processor service"
    [lucid-session-storage]="Session storage service"
    [lucid-session-api]="Session API service"
    [lucid-rdp-server-manager]="RDP server manager"
    [lucid-xrdp]="XRDP service"
    [lucid-session-controller]="Session controller"
    [lucid-resource-monitor]="Resource monitor"
    [lucid-node-management]="Node management service"
    
    # Phase 4: Support Services
    [lucid-admin-interface]="Admin interface"
    [lucid-tron-client]="TRON client service"
    [lucid-payout-router]="TRON payout router"
    [lucid-wallet-manager]="Wallet manager"
    [lucid-usdt-manager]="USDT manager"
    [lucid-trx-staking]="TRX staking service"
    [lucid-payment-gateway]="Payment gateway"
)

# Network definitions for cleanup
declare -A LUCID_NETWORKS=(
    [lucid-dev]="Main development network"
    [lucid-internal]="Internal services network"
    [lucid-blockchain]="Blockchain services network"
    [lucid-payment]="Payment services network"
)

# Volume definitions for cleanup
declare -A LUCID_VOLUMES=(
    [lucid-mongo-data]="MongoDB data volume"
    [lucid-redis-data]="Redis data volume"
    [lucid-elasticsearch-data]="Elasticsearch data volume"
    [lucid-blockchain-data]="Blockchain data volume"
    [lucid-session-data]="Session data volume"
    [lucid-chunk-data]="Chunk storage volume"
    [lucid-merkle-data]="Merkle tree data volume"
)

# Utility functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${CYAN}===== $1 =====${NC}"
}

# Check if running in dry run mode
is_dry_run() {
    [[ "$DRY_RUN" == "true" ]]
}

# Execute command with dry run support
execute_cmd() {
    local cmd="$1"
    local description="$2"
    
    if is_dry_run; then
        log_info "[DRY RUN] $description"
        log_info "[DRY RUN] Would execute: $cmd"
    else
        log_info "$description"
        if eval "$cmd"; then
            log_success "$description completed"
        else
            log_error "$description failed"
            return 1
        fi
    fi
}

# Stop all Lucid containers
stop_lucid_containers() {
    log_info "Stopping all Lucid containers..."
    
    # Find all Lucid containers
    local lucid_containers=$(docker ps -a --filter "name=lucid-" --format "{{.Names}}" 2>/dev/null || echo "")
    
    if [[ -n "$lucid_containers" ]]; then
        for container in $lucid_containers; do
            execute_cmd "docker stop '$container'" "Stopping container: $container"
        done
    else
        log_info "No Lucid containers found"
    fi
    
    log_success "All Lucid containers stopped"
    return 0
}

# Remove all Lucid containers
remove_lucid_containers() {
    log_info "Removing all Lucid containers..."
    
    # Find all Lucid containers
    local lucid_containers=$(docker ps -a --filter "name=lucid-" --format "{{.Names}}" 2>/dev/null || echo "")
    
    if [[ -n "$lucid_containers" ]]; then
        for container in $lucid_containers; do
            execute_cmd "docker rm '$container'" "Removing container: $container"
        done
    else
        log_info "No Lucid containers found"
    fi
    
    log_success "All Lucid containers removed"
    return 0
}

# Remove Lucid images
remove_lucid_images() {
    log_info "Removing Lucid images..."
    
    # Find all Lucid images
    local lucid_images=$(docker images --filter "reference=lucid-*" --format "{{.Repository}}:{{.Tag}}" 2>/dev/null || echo "")
    
    if [[ -n "$lucid_images" ]]; then
        for image in $lucid_images; do
            execute_cmd "docker rmi '$image'" "Removing image: $image"
        done
    else
        log_info "No Lucid images found"
    fi
    
    log_success "All Lucid images removed"
    return 0
}

# Remove Lucid networks
remove_lucid_networks() {
    log_info "Removing Lucid networks..."
    
    for network in "${!LUCID_NETWORKS[@]}"; do
        local description="${LUCID_NETWORKS[$network]}"
        
        if docker network ls --filter "name=$network" --format "{{.Name}}" | grep -q "$network"; then
            execute_cmd "docker network rm '$network'" "Removing network: $network ($description)"
        else
            log_info "Network $network not found"
        fi
    done
    
    log_success "All Lucid networks removed"
    return 0
}

# Remove Lucid volumes
remove_lucid_volumes() {
    log_info "Removing Lucid volumes..."
    
    for volume in "${!LUCID_VOLUMES[@]}"; do
        local description="${LUCID_VOLUMES[$volume]}"
        
        if docker volume ls --filter "name=$volume" --format "{{.Name}}" | grep -q "$volume"; then
            execute_cmd "docker volume rm '$volume'" "Removing volume: $volume ($description)"
        else
            log_info "Volume $volume not found"
        fi
    done
    
    log_success "All Lucid volumes removed"
    return 0
}

# Clean Docker system
clean_docker_system() {
    log_info "Cleaning Docker system..."
    
    if [[ "$FORCE" == "true" ]]; then
        execute_cmd "docker system prune -a -f --volumes" "Cleaning Docker system (force)"
    else
        execute_cmd "docker system prune -f" "Cleaning Docker system"
    fi
    
    log_success "Docker system cleaned"
    return 0
}

# Clean project directories
clean_project_directories() {
    log_info "Cleaning project directories..."
    
    # Clean log directory
    if [[ -d "$LOG_DIR" ]]; then
        execute_cmd "rm -rf '$LOG_DIR'" "Cleaning log directory: $LOG_DIR"
    fi
    
    # Clean data directory
    if [[ -d "$DATA_DIR" ]]; then
        execute_cmd "rm -rf '$DATA_DIR'" "Cleaning data directory: $DATA_DIR"
    fi
    
    # Clean build artifacts
    local build_dir="${PROJECT_ROOT}/_build"
    if [[ -d "$build_dir" ]]; then
        execute_cmd "rm -rf '$build_dir'" "Cleaning build directory: $build_dir"
    fi
    
    # Clean temporary files
    local temp_files=(
        "${PROJECT_ROOT}/.env.local"
        "${PROJECT_ROOT}/docker-compose.override.yml"
        "${PROJECT_ROOT}/_compose_resolved.yaml"
    )
    
    for file in "${temp_files[@]}"; do
        if [[ -f "$file" ]]; then
            execute_cmd "rm -f '$file'" "Removing temporary file: $file"
        fi
    done
    
    log_success "Project directories cleaned"
    return 0
}

# Clean Docker Compose files
clean_compose_files() {
    log_info "Cleaning Docker Compose files..."
    
    # Stop and remove containers from compose files
    local compose_files=(
        "${PROJECT_ROOT}/.devcontainer/docker-compose.dev.yml"
        "${PROJECT_ROOT}/docker-compose.yml"
        "${PROJECT_ROOT}/docker-compose.dev.yml"
    )
    
    for compose_file in "${compose_files[@]}"; do
        if [[ -f "$compose_file" ]]; then
            execute_cmd "docker-compose -f '$compose_file' down --remove-orphans" "Cleaning compose file: $compose_file"
        fi
    done
    
    log_success "Docker Compose files cleaned"
    return 0
}

# Clean development environment
clean_development_environment() {
    log_info "Cleaning development environment..."
    
    # Clean Python cache
    execute_cmd "find '$PROJECT_ROOT' -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true" "Cleaning Python cache"
    
    # Clean Python bytecode
    execute_cmd "find '$PROJECT_ROOT' -name '*.pyc' -delete 2>/dev/null || true" "Cleaning Python bytecode"
    
    # Clean Node modules if any
    execute_cmd "find '$PROJECT_ROOT' -name 'node_modules' -type d -exec rm -rf {} + 2>/dev/null || true" "Cleaning Node modules"
    
    # Clean build artifacts
    execute_cmd "find '$PROJECT_ROOT' -name '*.egg-info' -type d -exec rm -rf {} + 2>/dev/null || true" "Cleaning Python egg info"
    execute_cmd "find '$PROJECT_ROOT' -name 'dist' -type d -exec rm -rf {} + 2>/dev/null || true" "Cleaning dist directories"
    execute_cmd "find '$PROJECT_ROOT' -name 'build' -type d -exec rm -rf {} + 2>/dev/null || true" "Cleaning build directories"
    
    log_success "Development environment cleaned"
    return 0
}

# Reset Docker to clean state
reset_docker() {
    log_info "Resetting Docker to clean state..."
    
    if [[ "$FORCE" == "true" ]]; then
        # Stop all containers
        execute_cmd "docker stop \$(docker ps -aq) 2>/dev/null || true" "Stopping all containers"
        
        # Remove all containers
        execute_cmd "docker rm \$(docker ps -aq) 2>/dev/null || true" "Removing all containers"
        
        # Remove all images
        execute_cmd "docker rmi \$(docker images -aq) 2>/dev/null || true" "Removing all images"
        
        # Remove all volumes
        execute_cmd "docker volume rm \$(docker volume ls -q) 2>/dev/null || true" "Removing all volumes"
        
        # Remove all networks
        execute_cmd "docker network rm \$(docker network ls -q) 2>/dev/null || true" "Removing all networks"
        
        # Prune system
        execute_cmd "docker system prune -a -f --volumes" "Pruning Docker system"
    else
        log_warning "Force mode not enabled, skipping Docker reset"
    fi
    
    log_success "Docker reset completed"
    return 0
}

# Show cleanup summary
show_cleanup_summary() {
    log_header "Cleanup Summary"
    
    echo -e "${YELLOW}Action:${NC} $ACTION"
    echo -e "${YELLOW}Environment:${NC} $ENVIRONMENT"
    echo -e "${YELLOW}Force:${NC} $FORCE"
    echo -e "${YELLOW}Dry Run:${NC} $DRY_RUN"
    echo
    
    # Show remaining resources
    echo -e "${YELLOW}Remaining Resources:${NC}"
    
    # Check containers
    local remaining_containers=$(docker ps -a --filter "name=lucid-" --format "{{.Names}}" 2>/dev/null | wc -l)
    echo -e "  Containers: $remaining_containers"
    
    # Check images
    local remaining_images=$(docker images --filter "reference=lucid-*" --format "{{.Repository}}" 2>/dev/null | wc -l)
    echo -e "  Images: $remaining_images"
    
    # Check networks
    local remaining_networks=$(docker network ls --filter "name=lucid" --format "{{.Name}}" 2>/dev/null | wc -l)
    echo -e "  Networks: $remaining_networks"
    
    # Check volumes
    local remaining_volumes=$(docker volume ls --filter "name=lucid" --format "{{.Name}}" 2>/dev/null | wc -l)
    echo -e "  Volumes: $remaining_volumes"
    
    echo
    
    if [[ "$remaining_containers" -eq 0 && "$remaining_images" -eq 0 && "$remaining_networks" -eq 0 && "$remaining_volumes" -eq 0 ]]; then
        log_success "All Lucid resources have been cleaned up"
    else
        log_warning "Some Lucid resources may still exist"
    fi
}

# Verify cleanup
verify_cleanup() {
    log_info "Verifying cleanup..."
    
    local issues=()
    
    # Check for remaining containers
    local remaining_containers=$(docker ps -a --filter "name=lucid-" --format "{{.Names}}" 2>/dev/null)
    if [[ -n "$remaining_containers" ]]; then
        issues+=("Remaining containers: $remaining_containers")
    fi
    
    # Check for remaining images
    local remaining_images=$(docker images --filter "reference=lucid-*" --format "{{.Repository}}:{{.Tag}}" 2>/dev/null)
    if [[ -n "$remaining_images" ]]; then
        issues+=("Remaining images: $remaining_images")
    fi
    
    # Check for remaining networks
    local remaining_networks=$(docker network ls --filter "name=lucid" --format "{{.Name}}" 2>/dev/null)
    if [[ -n "$remaining_networks" ]]; then
        issues+=("Remaining networks: $remaining_networks")
    fi
    
    # Check for remaining volumes
    local remaining_volumes=$(docker volume ls --filter "name=lucid" --format "{{.Name}}" 2>/dev/null)
    if [[ -n "$remaining_volumes" ]]; then
        issues+=("Remaining volumes: $remaining_volumes")
    fi
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        log_warning "Cleanup verification found issues:"
        for issue in "${issues[@]}"; do
            echo -e "  ${YELLOW}-${NC} $issue"
        done
        return 1
    else
        log_success "Cleanup verification passed"
        return 0
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 <action> [environment] [force] [dry_run]"
    echo
    echo "Actions:"
    echo "  clean     - Clean all Lucid resources (default)"
    echo "  stop      - Stop all Lucid containers"
    echo "  remove    - Remove all Lucid containers"
    echo "  images    - Remove all Lucid images"
    echo "  networks  - Remove all Lucid networks"
    echo "  volumes   - Remove all Lucid volumes"
    echo "  system    - Clean Docker system"
    echo "  project   - Clean project directories"
    echo "  dev       - Clean development environment"
    echo "  reset     - Reset Docker to clean state"
    echo "  verify    - Verify cleanup"
    echo "  summary   - Show cleanup summary"
    echo
    echo "Environment:"
    echo "  dev       - Development environment (default)"
    echo "  test      - Test environment"
    echo "  prod      - Production environment"
    echo
    echo "Force:"
    echo "  true      - Force cleanup (removes all Docker resources)"
    echo "  false     - Safe cleanup (default)"
    echo
    echo "Dry Run:"
    echo "  true      - Show what would be done without executing"
    echo "  false     - Execute cleanup (default)"
}

# Main execution
main() {
    log_header "Lucid Local Development Cleanup"
    echo -e "${YELLOW}Action:${NC} $ACTION"
    echo -e "${YELLOW}Environment:${NC} $ENVIRONMENT"
    echo -e "${YELLOW}Force:${NC} $FORCE"
    echo -e "${YELLOW}Dry Run:${NC} $DRY_RUN"
    echo
    
    if is_dry_run; then
        log_info "Running in DRY RUN mode - no changes will be made"
    fi
    
    # Execute action
    local success=false
    
    case "$ACTION" in
        "clean")
            if stop_lucid_containers && remove_lucid_containers && remove_lucid_images && \
               remove_lucid_networks && remove_lucid_volumes && clean_docker_system && \
               clean_project_directories && clean_development_environment; then
                success=true
            fi
            ;;
        
        "stop")
            if stop_lucid_containers; then
                success=true
            fi
            ;;
        
        "remove")
            if remove_lucid_containers; then
                success=true
            fi
            ;;
        
        "images")
            if remove_lucid_images; then
                success=true
            fi
            ;;
        
        "networks")
            if remove_lucid_networks; then
                success=true
            fi
            ;;
        
        "volumes")
            if remove_lucid_volumes; then
                success=true
            fi
            ;;
        
        "system")
            if clean_docker_system; then
                success=true
            fi
            ;;
        
        "project")
            if clean_project_directories; then
                success=true
            fi
            ;;
        
        "dev")
            if clean_development_environment; then
                success=true
            fi
            ;;
        
        "reset")
            if reset_docker; then
                success=true
            fi
            ;;
        
        "verify")
            if verify_cleanup; then
                success=true
            fi
            ;;
        
        "summary")
            show_cleanup_summary
            success=true
            ;;
        
        *)
            log_error "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
    
    # Show summary
    show_cleanup_summary
    
    # Verify cleanup if not in dry run mode
    if [[ "$success" == "true" && "$DRY_RUN" != "true" ]]; then
        verify_cleanup || true
    fi
    
    # Summary
    echo
    if [[ "$success" == "true" ]]; then
        log_header "$ACTION completed successfully"
        exit 0
    else
        log_header "$ACTION failed"
        exit 1
    fi
}

# Run main function
main "$@"
