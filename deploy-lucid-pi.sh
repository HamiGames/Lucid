#!/bin/bash
# Lucid RDP Raspberry Pi 5 Deployment Script
# Handles deployment and operations on Raspberry Pi 5 (ARM64)
# Based on LUCID-STRICT requirements

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Runtime variables aligned for Raspberry Pi 5
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"
BUILD_DIR="${PROJECT_ROOT}/_build"
LOG_DIR="${PROJECT_ROOT}/logs"
DATA_DIR="${PROJECT_ROOT}/data"
CONFIG_DIR="${PROJECT_ROOT}/config"

# Default parameters
ACTION="${1:-deploy}"
ENVIRONMENT="${2:-dev}"
FORCE="${3:-false}"

# Environment configuration
declare -A ENV_VARS=(
    [dev_TRON_NETWORK]="shasta"
    [dev_LUCID_ENV]="dev"
    [dev_MONGO_URL]="mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin&retryWrites=false"
    [dev_BLOCK_RPC_URL]="http://localhost:8545"
    [dev_LOG_LEVEL]="DEBUG"
    
    [prod_TRON_NETWORK]="mainnet"
    [prod_LUCID_ENV]="prod"
    [prod_MONGO_URL]="mongodb://admin:\${MONGO_PROD_PASSWORD}@lucid_mongo:27017/lucid?authSource=admin&retryWrites=true"
    [prod_BLOCK_RPC_URL]="\${BLOCK_ONION}"
    [prod_LOG_LEVEL]="INFO"
)

# Service definitions
declare -A SERVICES=(
    [lucid_tor]="9050:Tor proxy service"
    [lucid_mongo]="27017:MongoDB database"
    [lucid_api]="8081:Main API gateway"
    [lucid_blockchain]="8082:Blockchain core service"
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

# Check if running on Raspberry Pi 5
check_pi_hardware() {
    log_info "Checking Raspberry Pi hardware..."
    
    if [[ -f /sys/firmware/devicetree/base/model ]]; then
        PI_MODEL=$(cat /sys/firmware/devicetree/base/model | tr -d '\0')
        if [[ "$PI_MODEL" == *"Raspberry Pi 5"* ]]; then
            log_success "Running on Raspberry Pi 5: $PI_MODEL"
            return 0
        else
            log_warning "Not running on Raspberry Pi 5: $PI_MODEL"
            if [[ "$FORCE" != "true" ]]; then
                log_error "Use FORCE=true to continue on non-Pi hardware"
                return 1
            fi
        fi
    else
        log_warning "Cannot detect hardware model"
        if [[ "$FORCE" != "true" ]]; then
            log_error "Use FORCE=true to continue"
            return 1
        fi
    fi
    
    # Check ARM64 architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" == "aarch64" ]]; then
        log_success "ARM64 architecture confirmed: $ARCH"
    else
        log_warning "Non-ARM64 architecture: $ARCH"
    fi
    
    return 0
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local prereq_errors=()
    
    # Check Docker
    if command -v docker >/dev/null 2>&1; then
        if docker --version >/dev/null 2>&1; then
            log_success "Docker is available"
        else
            prereq_errors+=("Docker not working")
        fi
    else
        prereq_errors+=("Docker not installed")
    fi
    
    # Check Docker Compose
    if command -v docker-compose >/dev/null 2>&1; then
        log_success "Docker Compose is available"
    else
        prereq_errors+=("Docker Compose not installed")
    fi
    
    # Check Python
    if command -v python3 >/dev/null 2>&1; then
        log_success "Python 3 is available"
    else
        prereq_errors+=("Python 3 not installed")
    fi
    
    # Check system requirements
    local memory_gb=$(free -g | awk 'NR==2{print $2}')
    if [[ "$memory_gb" -ge 4 ]]; then
        log_success "Memory: ${memory_gb}GB (sufficient)"
    else
        log_warning "Memory: ${memory_gb}GB (may be insufficient)"
    fi
    
    local disk_gb=$(df -BG / | awk 'NR==2{print $4}' | sed 's/G//')
    if [[ "$disk_gb" -ge 10 ]]; then
        log_success "Disk space: ${disk_gb}GB available (sufficient)"
    else
        prereq_errors+=("Insufficient disk space: ${disk_gb}GB available")
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
    log_info "Initializing environment: $ENVIRONMENT"
    
    # Create directories
    for dir in "$BUILD_DIR" "$LOG_DIR" "$DATA_DIR" "$CONFIG_DIR"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_success "Created directory: $dir"
        fi
    done
    
    # Set environment variables
    for key in "${!ENV_VARS[@]}"; do
        if [[ "$key" == "${ENVIRONMENT}_"* ]]; then
            var_name="${key#${ENVIRONMENT}_}"
            var_value="${ENV_VARS[$key]}"
            export "$var_name"="$var_value"
            log_success "Set $var_name=$var_value"
        fi
    done
    
    # Initialize Docker networks
    log_info "Creating Docker networks..."
    if [[ -f "${SCRIPT_DIR}/06-orchestration-runtime/net/setup_lucid_networks.sh" ]]; then
        "${SCRIPT_DIR}/06-orchestration-runtime/net/setup_lucid_networks.sh" create "$ENVIRONMENT"
    else
        log_warning "Network setup script not found, creating basic networks..."
        
        # Create networks manually
        docker network create lucid_internal --subnet 172.20.0.0/24 --internal || true
        docker network create lucid_external --subnet 172.21.0.0/24 || true
        docker network create lucid_blockchain --subnet 172.22.0.0/24 --internal || true
        docker network create lucid_tor --subnet 172.23.0.0/24 || true
        docker network create lucid_dev --subnet 172.24.0.0/24 || true
    fi
    
    return 0
}

# Build ARM64 images
build_images() {
    log_info "Building ARM64 Docker images..."
    
    # Pull base images for ARM64
    log_info "Pulling ARM64 base images..."
    docker pull --platform linux/arm64 python:3.12-slim
    docker pull --platform linux/arm64 mongo:7
    docker pull --platform linux/arm64 nginx:alpine
    docker pull --platform linux/arm64 alpine:3.22.1
    
    # Build custom images if Dockerfiles exist
    if [[ -f "${SCRIPT_DIR}/.devcontainer/Dockerfile" ]]; then
        log_info "Building custom development image..."
        docker build \
            --platform linux/arm64 \
            -t pickme/lucid-dev:latest \
            -f "${SCRIPT_DIR}/.devcontainer/Dockerfile" \
            "${SCRIPT_DIR}"
        
        if [[ $? -eq 0 ]]; then
            log_success "Development image built successfully"
        else
            log_error "Development image build failed"
            return 1
        fi
    fi
    
    log_success "Images built successfully"
    return 0
}

# Start services
start_services() {
    log_info "Starting Lucid services..."
    
    # Check if compose file exists
    local compose_file="${SCRIPT_DIR}/_compose_resolved.yaml"
    if [[ ! -f "$compose_file" ]]; then
        compose_file="${SCRIPT_DIR}/docker-compose.yml"
    fi
    
    if [[ ! -f "$compose_file" ]]; then
        log_error "Docker compose file not found"
        return 1
    fi
    
    # Start services
    docker-compose -f "$compose_file" --profile dev up -d
    
    if [[ $? -ne 0 ]]; then
        log_error "Service startup failed"
        return 1
    fi
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 15
    
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
            log_error "$service is unhealthy ($description)"
        fi
    done
    
    if [[ "$healthy_services" -eq "$total_services" ]]; then
        log_success "All services started successfully"
        return 0
    else
        log_error "$((total_services - healthy_services)) services failed to start"
        return 1
    fi
}

# Stop services
stop_services() {
    log_info "Stopping Lucid services..."
    
    local compose_file="${SCRIPT_DIR}/_compose_resolved.yaml"
    if [[ ! -f "$compose_file" ]]; then
        compose_file="${SCRIPT_DIR}/docker-compose.yml"
    fi
    
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
        docker stop $(docker ps -q --filter "name=lucid_") 2>/dev/null || true
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
    fi
    
    return 0
}

# Show service status
show_service_status() {
    log_header "Lucid Service Status"
    
    # Show Docker containers
    echo -e "${YELLOW}Docker Containers:${NC}"
    docker ps --filter "name=lucid_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
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
    echo -e "TRON Network: ${TRON_NETWORK:-not set}"
    echo -e "Lucid Env: ${LUCID_ENV:-not set}"
    echo -e "Log Level: ${LOG_LEVEL:-not set}"
    
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
    log_info "Testing deployment..."
    
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
    
    if [[ "$healthy_count" -eq "${#SERVICES[@]}" ]]; then
        test_results+=("Services:PASS")
        ((passed++))
    else
        test_results+=("Services:FAIL")
    fi
    
    # Test 4: API endpoints (if services are running)
    log_info "Testing API endpoints..."
    if command -v curl >/dev/null 2>&1; then
        if curl -f --connect-timeout 5 http://localhost:8081/health >/dev/null 2>&1; then
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
    
    return $(( passed == total ? 0 : 1 ))
}

# Clean deployment
clean_deployment() {
    log_info "Cleaning deployment..."
    
    # Stop services
    stop_services
    
    # Remove containers
    log_info "Removing containers..."
    docker system prune -f --volumes
    
    # Remove networks
    log_info "Removing networks..."
    for network in lucid_internal lucid_external lucid_blockchain lucid_tor lucid_dev; do
        docker network rm "$network" 2>/dev/null || true
    done
    
    # Clean build directory
    if [[ -d "$BUILD_DIR" ]]; then
        rm -rf "$BUILD_DIR"
        log_success "Cleaned build directory"
    fi
    
    log_success "Cleanup completed"
    return 0
}

# Show usage
show_usage() {
    echo "Usage: $0 <action> [environment] [force]"
    echo
    echo "Actions:"
    echo "  deploy    - Full deployment (default)"
    echo "  start     - Start services"
    echo "  stop      - Stop services"
    echo "  status    - Show service status"
    echo "  test      - Test deployment"
    echo "  clean     - Clean deployment"
    echo
    echo "Environment:"
    echo "  dev       - Development environment (default)"
    echo "  prod      - Production environment"
    echo
    echo "Force:"
    echo "  true      - Force deployment on non-Pi hardware"
    echo "  false     - Strict Pi hardware check (default)"
}

# Main execution
main() {
    log_header "Lucid RDP Raspberry Pi 5 Deployment"
    echo -e "${YELLOW}Action:${NC} $ACTION"
    echo -e "${YELLOW}Environment:${NC} $ENVIRONMENT"
    echo -e "${YELLOW}Force:${NC} $FORCE"
    echo
    
    # Check hardware (unless force is true)
    if ! check_pi_hardware; then
        exit 1
    fi
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Execute action
    local success=false
    
    case "$ACTION" in
        "deploy")
            if initialize_environment && build_images && start_services; then
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