#!/bin/bash
# Lucid Local Development Deployment Script
# Deploys all Lucid services locally for development and testing
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
ACTION="${1:-deploy}"
ENVIRONMENT="${2:-dev}"
VERBOSE="${3:-false}"

# Service definitions for all 10 clusters
declare -A SERVICES=(
    # Phase 1: Foundation
    [lucid-mongodb]="27017:MongoDB database service"
    [lucid-redis]="6379:Redis cache service"
    [lucid-elasticsearch]="9200:Elasticsearch search service"
    [lucid-auth-service]="8089:Authentication service"
    
    # Phase 2: Core Services
    [lucid-api-gateway]="8080:API Gateway service"
    [lucid-blockchain-engine]="8084:Blockchain core engine"
    [lucid-session-anchoring]="8085:Session anchoring service"
    [lucid-block-manager]="8086:Block manager service"
    [lucid-data-chain]="8087:Data chain service"
    [lucid-service-mesh]="8500:Service mesh controller"
    
    # Phase 3: Application Services
    [lucid-session-pipeline]="8083:Session pipeline manager"
    [lucid-session-recorder]="8088:Session recorder service"
    [lucid-session-processor]="8089:Session processor service"
    [lucid-session-storage]="8090:Session storage service"
    [lucid-session-api]="8091:Session API service"
    [lucid-rdp-server-manager]="8092:RDP server manager"
    [lucid-xrdp]="8093:XRDP service"
    [lucid-session-controller]="8094:Session controller"
    [lucid-resource-monitor]="8095:Resource monitor"
    [lucid-node-management]="8096:Node management service"
    
    # Phase 4: Support Services
    [lucid-admin-interface]="8083:Admin interface"
    [lucid-tron-client]="8085:TRON client service"
    [lucid-payout-router]="8086:TRON payout router"
    [lucid-wallet-manager]="8087:Wallet manager"
    [lucid-usdt-manager]="8088:USDT manager"
    [lucid-trx-staking]="8089:TRX staking service"
    [lucid-payment-gateway]="8090:Payment gateway"
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for local development..."
    
    local prereq_errors=()
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        prereq_errors+=("Docker not installed")
    elif ! docker --version >/dev/null 2>&1; then
        prereq_errors+=("Docker not working")
    else
        log_success "Docker is available"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1; then
        prereq_errors+=("Docker Compose not installed")
    else
        log_success "Docker Compose is available"
    fi
    
    # Check system requirements
    local memory_gb=$(free -g 2>/dev/null | awk 'NR==2{print $2}' || echo "0")
    if [[ "$memory_gb" -ge 8 ]]; then
        log_success "Memory: ${memory_gb}GB (sufficient for local development)"
    elif [[ "$memory_gb" -ge 4 ]]; then
        log_warning "Memory: ${memory_gb}GB (minimum for local development)"
    else
        prereq_errors+=("Insufficient memory: ${memory_gb}GB (minimum 4GB required)")
    fi
    
    local disk_gb=$(df -BG / 2>/dev/null | awk 'NR==2{print $4}' | sed 's/G//' || echo "0")
    if [[ "$disk_gb" -ge 20 ]]; then
        log_success "Disk space: ${disk_gb}GB available (sufficient)"
    elif [[ "$disk_gb" -ge 10 ]]; then
        log_warning "Disk space: ${disk_gb}GB available (minimum)"
    else
        prereq_errors+=("Insufficient disk space: ${disk_gb}GB available (minimum 10GB required)")
    fi
    
    if [[ ${#prereq_errors[@]} -gt 0 ]]; then
        log_error "Prerequisites check failed:"
        for error in "${prereq_errors[@]}"; do
            echo -e "  ${RED}-${NC} $error"
        done
        return 1
    fi
    
    log_success "All prerequisites met"
    return 0
}

# Initialize environment
initialize_environment() {
    log_info "Initializing local development environment..."
    
    # Create directories
    for dir in "$LOG_DIR" "$DATA_DIR" "$CONFIG_DIR"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_success "Created directory: $dir"
        fi
    done
    
    # Set environment variables
    export LUCID_ENV="$ENVIRONMENT"
    export LUCID_NETWORK="lucid-dev"
    export LUCID_LOG_LEVEL="DEBUG"
    export LUCID_DEBUG="true"
    
    # Create Docker networks
    log_info "Creating Docker networks..."
    docker network create lucid-dev --subnet 172.20.0.0/16 --driver bridge 2>/dev/null || true
    docker network create lucid-internal --subnet 172.21.0.0/16 --driver bridge --internal 2>/dev/null || true
    docker network create lucid-blockchain --subnet 172.22.0.0/16 --driver bridge 2>/dev/null || true
    docker network create lucid-payment --subnet 172.23.0.0/16 --driver bridge 2>/dev/null || true
    
    log_success "Environment initialized"
    return 0
}

# Build all services
build_services() {
    log_info "Building all Lucid services..."
    
    # Build Phase 1: Foundation services
    log_info "Building Phase 1: Foundation services..."
    if [[ -f "${PROJECT_ROOT}/infrastructure/containers/storage/Dockerfile.mongodb" ]]; then
        docker build -t lucid-mongodb:latest -f "${PROJECT_ROOT}/infrastructure/containers/storage/Dockerfile.mongodb" "${PROJECT_ROOT}"
    fi
    
    if [[ -f "${PROJECT_ROOT}/infrastructure/containers/storage/Dockerfile.redis" ]]; then
        docker build -t lucid-redis:latest -f "${PROJECT_ROOT}/infrastructure/containers/storage/Dockerfile.redis" "${PROJECT_ROOT}"
    fi
    
    if [[ -f "${PROJECT_ROOT}/infrastructure/containers/storage/Dockerfile.elasticsearch" ]]; then
        docker build -t lucid-elasticsearch:latest -f "${PROJECT_ROOT}/infrastructure/containers/storage/Dockerfile.elasticsearch" "${PROJECT_ROOT}"
    fi
    
    if [[ -f "${PROJECT_ROOT}/auth/Dockerfile" ]]; then
        docker build -t lucid-auth-service:latest -f "${PROJECT_ROOT}/auth/Dockerfile" "${PROJECT_ROOT}/auth"
    fi
    
    # Build Phase 2: Core services
    log_info "Building Phase 2: Core services..."
    if [[ -f "${PROJECT_ROOT}/03-api-gateway/Dockerfile" ]]; then
        docker build -t lucid-api-gateway:latest -f "${PROJECT_ROOT}/03-api-gateway/Dockerfile" "${PROJECT_ROOT}/03-api-gateway"
    fi
    
    if [[ -f "${PROJECT_ROOT}/blockchain/Dockerfile.engine" ]]; then
        docker build -t lucid-blockchain-engine:latest -f "${PROJECT_ROOT}/blockchain/Dockerfile.engine" "${PROJECT_ROOT}/blockchain"
    fi
    
    # Build Phase 3: Application services
    log_info "Building Phase 3: Application services..."
    if [[ -f "${PROJECT_ROOT}/sessions/Dockerfile.pipeline" ]]; then
        docker build -t lucid-session-pipeline:latest -f "${PROJECT_ROOT}/sessions/Dockerfile.pipeline" "${PROJECT_ROOT}/sessions"
    fi
    
    if [[ -f "${PROJECT_ROOT}/RDP/Dockerfile.server-manager" ]]; then
        docker build -t lucid-rdp-server-manager:latest -f "${PROJECT_ROOT}/RDP/Dockerfile.server-manager" "${PROJECT_ROOT}/RDP"
    fi
    
    if [[ -f "${PROJECT_ROOT}/node/Dockerfile" ]]; then
        docker build -t lucid-node-management:latest -f "${PROJECT_ROOT}/node/Dockerfile" "${PROJECT_ROOT}/node"
    fi
    
    # Build Phase 4: Support services
    log_info "Building Phase 4: Support services..."
    if [[ -f "${PROJECT_ROOT}/admin/Dockerfile" ]]; then
        docker build -t lucid-admin-interface:latest -f "${PROJECT_ROOT}/admin/Dockerfile" "${PROJECT_ROOT}/admin"
    fi
    
    if [[ -f "${PROJECT_ROOT}/payment-systems/tron/Dockerfile.tron-client" ]]; then
        docker build -t lucid-tron-client:latest -f "${PROJECT_ROOT}/payment-systems/tron/Dockerfile.tron-client" "${PROJECT_ROOT}/payment-systems/tron"
    fi
    
    log_success "All services built successfully"
    return 0
}

# Start all services
start_services() {
    log_info "Starting all Lucid services..."
    
    # Use the enhanced docker-compose.dev.yml
    local compose_file="${PROJECT_ROOT}/.devcontainer/docker-compose.dev.yml"
    
    if [[ ! -f "$compose_file" ]]; then
        log_error "Docker compose file not found: $compose_file"
        return 1
    fi
    
    # Start services with development profile
    docker-compose -f "$compose_file" --profile dev up -d
    
    if [[ $? -ne 0 ]]; then
        log_error "Service startup failed"
        return 1
    fi
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    local healthy_services=0
    local total_services=${#SERVICES[@]}
    
    for service in "${!SERVICES[@]}"; do
        local service_info="${SERVICES[$service]}"
        local port="${service_info%%:*}"
        local description="${service_info#*:}"
        
        if test_service_health "$service" "$port"; then
            log_success "$service is healthy ($description)"
            ((healthy_services++))
        else
            log_warning "$service is unhealthy ($description)"
        fi
    done
    
    log_info "$healthy_services/$total_services services are healthy"
    
    if [[ "$healthy_services" -ge $((total_services * 3 / 4)) ]]; then
        log_success "Sufficient services started successfully"
        return 0
    else
        log_error "Too many services failed to start"
        return 1
    fi
}

# Stop all services
stop_services() {
    log_info "Stopping all Lucid services..."
    
    local compose_file="${PROJECT_ROOT}/.devcontainer/docker-compose.dev.yml"
    
    if [[ -f "$compose_file" ]]; then
        docker-compose -f "$compose_file" --profile dev down
        
        if [[ $? -eq 0 ]]; then
            log_success "Services stopped successfully"
            return 0
        else
            log_error "Service stop failed"
            return 1
        fi
    else
        log_warning "Compose file not found, stopping containers manually..."
        docker stop $(docker ps -q --filter "name=lucid-") 2>/dev/null || true
        log_success "Containers stopped"
        return 0
    fi
}

# Test service health
test_service_health() {
    local service_name="$1"
    local port="$2"
    
    # Check if container is running
    if ! docker ps --filter "name=$service_name" --format "{{.Names}}" | grep -q "$service_name"; then
        return 1
    fi
    
    # Test port connectivity
    if command -v nc >/dev/null 2>&1; then
        if ! nc -z localhost "$port" 2>/dev/null; then
            return 1
        fi
    elif command -v curl >/dev/null 2>&1; then
        if ! curl -f --connect-timeout 5 "http://localhost:$port/health" >/dev/null 2>&1; then
            return 1
        fi
    fi
    
    return 0
}

# Show service status
show_service_status() {
    log_header "Lucid Local Development Status"
    
    # Show Docker containers
    echo -e "${YELLOW}Docker Containers:${NC}"
    docker ps --filter "name=lucid-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo
    
    # Show Docker networks
    echo -e "${YELLOW}Docker Networks:${NC}"
    docker network ls --filter "name=lucid" --format "table {{.Name}}\t{{Driver}}\t{{Scope}}"
    echo
    
    # Test service health
    echo -e "${YELLOW}Service Health:${NC}"
    for service in "${!SERVICES[@]}"; do
        local service_info="${SERVICES[$service]}"
        local port="${service_info%%:*}"
        local description="${service_info#*:}"
        
        if test_service_health "$service" "$port"; then
            echo -e "  ${GREEN}[+]${NC} $service: HEALTHY ($description)"
        else
            echo -e "  ${RED}[-]${NC} $service: UNHEALTHY ($description)"
        fi
    done
    
    echo
    
    # Show environment info
    echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
    echo -e "Lucid Network: ${LUCID_NETWORK:-not set}"
    echo -e "Log Level: ${LUCID_LOG_LEVEL:-not set}"
    echo -e "Debug Mode: ${LUCID_DEBUG:-not set}"
    
    # Show system info
    echo
    echo -e "${YELLOW}System Information:${NC}"
    echo -e "Architecture: $(uname -m)"
    echo -e "Kernel: $(uname -r)"
    echo -e "Memory: $(free -h | awk 'NR==2{printf "%.1f/%.1fGB (%.2f%% used)", $3/1024/1024, $2/1024/1024, $3*100/$2}')"
    echo -e "Disk: $(df -h / | awk 'NR==2{printf "%s/%s (%s used)", $4, $2, $5}')"
    echo -e "Load: $(uptime | awk '{print $10 $11 $12}')"
}

# Test deployment
test_deployment() {
    log_info "Testing local development deployment..."
    
    local test_results=()
    local passed=0
    
    # Test 1: Basic Docker functionality
    log_info "Testing Docker functionality..."
    if docker ps >/dev/null 2>&1; then
        test_results+=("Docker:PASS")
        ((passed++))
    else
        test_results+=("Docker:FAIL")
    fi
    
    # Test 2: Network connectivity
    log_info "Testing network connectivity..."
    if docker network ls | grep -q lucid; then
        test_results+=("Networks:PASS")
        ((passed++))
    else
        test_results+=("Networks:FAIL")
    fi
    
    # Test 3: Service health
    log_info "Testing service health..."
    local healthy_count=0
    for service in "${!SERVICES[@]}"; do
        local service_info="${SERVICES[$service]}"
        local port="${service_info%%:*}"
        
        if test_service_health "$service" "$port"; then
            ((healthy_count++))
        fi
    done
    
    if [[ "$healthy_count" -ge $(( ${#SERVICES[@]} * 3 / 4 )) ]]; then
        test_results+=("Services:PASS")
        ((passed++))
    else
        test_results+=("Services:FAIL")
    fi
    
    # Test 4: API endpoints
    log_info "Testing API endpoints..."
    if command -v curl >/dev/null 2>&1; then
        local api_tests=0
        local api_passed=0
        
        # Test API Gateway
        if curl -f --connect-timeout 5 http://localhost:8080/health >/dev/null 2>&1; then
            ((api_passed++))
        fi
        ((api_tests++))
        
        # Test Auth Service
        if curl -f --connect-timeout 5 http://localhost:8089/health >/dev/null 2>&1; then
            ((api_passed++))
        fi
        ((api_tests++))
        
        if [[ "$api_passed" -ge $((api_tests / 2)) ]]; then
            test_results+=("API:PASS")
            ((passed++))
        else
            test_results+=("API:FAIL")
        fi
    else
        test_results+=("API:SKIP")
    fi
    
    # Summary
    log_header "Test Results"
    for result in "${test_results[@]}"; do
        local test_name="${result%%:*}"
        local test_status="${result#*:}"
        
        case "$test_status" in
            "PASS") echo -e "  ${GREEN}✓${NC} $test_name: PASS" ;;
            "FAIL") echo -e "  ${RED}✗${NC} $test_name: FAIL" ;;
            "SKIP") echo -e "  ${YELLOW}−${NC} $test_name: SKIP" ;;
        esac
    done
    
    local total="${#test_results[@]}"
    log_header "$passed/$total tests passed"
    
    return $(( passed >= total * 3 / 4 ? 0 : 1 ))
}

# Clean deployment
clean_deployment() {
    log_info "Cleaning local development deployment..."
    
    # Stop services
    stop_services
    
    # Remove containers
    log_info "Removing containers..."
    docker system prune -f --volumes
    
    # Remove networks
    log_info "Removing networks..."
    for network in lucid-dev lucid-internal lucid-blockchain lucid-payment; do
        docker network rm "$network" 2>/dev/null || true
    done
    
    # Clean data directories
    if [[ -d "$DATA_DIR" ]]; then
        rm -rf "$DATA_DIR"
        log_success "Cleaned data directory"
    fi
    
    log_success "Cleanup completed"
    return 0
}

# Show usage
show_usage() {
    echo "Usage: $0 <action> [environment] [verbose]"
    echo
    echo "Actions:"
    echo "  deploy    - Full local deployment (default)"
    echo "  start     - Start services"
    echo "  stop      - Stop services"
    echo "  status    - Show service status"
    echo "  test      - Test deployment"
    echo "  clean     - Clean deployment"
    echo
    echo "Environment:"
    echo "  dev       - Development environment (default)"
    echo "  test      - Test environment"
    echo
    echo "Verbose:"
    echo "  true      - Verbose output"
    echo "  false     - Normal output (default)"
}

# Main execution
main() {
    log_header "Lucid Local Development Deployment"
    echo -e "${YELLOW}Action:${NC} $ACTION"
    echo -e "${YELLOW}Environment:${NC} $ENVIRONMENT"
    echo -e "${YELLOW}Verbose:${NC} $VERBOSE"
    echo
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Execute action
    local success=false
    
    case "$ACTION" in
        "deploy")
            if initialize_environment && build_services && start_services; then
                success=true
                test_deployment || true  # Test but don't fail deployment on test failures
            fi
            ;;
        
        "start")
            if initialize_environment && start_services; then
                success=true
            fi
            ;;
        
        "stop")
            if stop_services; then
                success=true
            fi
            ;;
        
        "status")
            show_service_status
            success=true
            ;;
        
        "test")
            if test_deployment; then
                success=true
            fi
            ;;
        
        "clean")
            if clean_deployment; then
                success=true
            fi
            ;;
        
        *)
            log_error "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
    
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
