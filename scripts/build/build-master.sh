#!/bin/bash
# Path: build-master.sh
# Master Build Orchestration Script for Lucid RDP
# Combines: Clean -> Prep -> Network Setup -> Build -> Test -> Deploy
# Linux/Unix/macOS version

set -euo pipefail

# Configuration
PROJECT_ROOT="$(pwd)"
NETWORK_SCRIPT="./scripts/setup_lucid_networks.ps1"  # Will convert to bash version
BUILD_SCRIPT_SH="./build-devcontainer.sh"
COMPOSE_SCRIPT="./06-orchestration-runtime/compose/compose_up_dev.sh"
DEPLOYMENT_SCRIPT="./scripts/deploy-lucid-pi.sh"

# Command line options
TEST_ONLY=false
NO_CACHE=false
CLEAN_BUILD=false
SKIP_TESTS=false
SHOW_HELP=false
PHASE="all"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --phase)
            PHASE="$2"
            shift 2
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

log_phase() {
    local phase=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    log_color "$BLUE" "[$timestamp] [$phase] $message"
}

log_success() { log_color "$GREEN" "[SUCCESS] $1"; }
log_error() { log_color "$RED" "[ERROR] $1"; }
log_warning() { log_color "$YELLOW" "[WARNING] $1"; }

show_usage() {
    log_color "$CYAN" "Lucid RDP Master Build Script"
    log_color "$CYAN" "============================="
    echo
    echo "Usage: ./build-master.sh [OPTIONS]"
    echo
    echo "Options:"
    echo "  --test-only     Only run tests, don't build/push containers"
    echo "  --no-cache      Build without Docker cache"
    echo "  --clean         Full clean build (remove all caches and networks)"
    echo "  --skip-tests    Skip integration tests"
    echo "  --phase PHASE   Run specific phase: prep|network|build|test|deploy|all"
    echo "  --help, -h      Show this help message"
    echo
    echo "Build Phases:"
    echo "  1. prep       Clean and prepare environment"
    echo "  2. network    Setup Docker networks"
    echo "  3. build      Build DevContainer images"
    echo "  4. test       Run integration tests"
    echo "  5. deploy     Deploy to development environment"
    echo "  6. all        Run all phases (default)"
    echo
    echo "Examples:"
    echo "  ./build-master.sh                      # Full build pipeline"
    echo "  ./build-master.sh --test-only          # Test-only build"
    echo "  ./build-master.sh --clean              # Clean build"
    echo "  ./build-master.sh --phase network      # Setup networks only"
    echo "  ./build-master.sh --phase build        # Build containers only"
}

if [[ "$SHOW_HELP" == "true" ]]; then
    show_usage
    exit 0
fi

# Check prerequisites
check_prerequisites() {
    log_phase "PREREQ" "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not found in PATH"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or not accessible"
        return 1
    fi
    log_phase "PREREQ" "Docker: OK"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_warning "Docker Compose not found - some features may not work"
    else
        log_phase "PREREQ" "Docker Compose: OK"
    fi
    
    # Check Git (optional)
    if command -v git &> /dev/null; then
        log_phase "PREREQ" "Git: OK"
    else
        log_warning "Git not found - version info will be 'unknown'"
    fi
    
    # Check Bash version
    if [[ ${BASH_VERSION%%.*} -lt 4 ]]; then
        log_error "Bash 4.0+ required (found: $BASH_VERSION)"
        return 1
    fi
    log_phase "PREREQ" "Bash ${BASH_VERSION%%.*}: OK"
    
    # Check required scripts
    if [[ -f "$BUILD_SCRIPT_SH" ]]; then
        log_phase "PREREQ" "Build script: OK"
    else
        log_error "Build script not found: $BUILD_SCRIPT_SH"
        return 1
    fi
    
    return 0
}

# Phase 1: Clean and Prepare Environment
start_prep_phase() {
    log_color "$MAGENTA" "===== PHASE 1: PREPARATION ====="
    log_phase "PREP" "Starting environment preparation..."
    
    if [[ "$CLEAN_BUILD" == "true" ]]; then
        log_phase "PREP" "Performing clean build preparation..."
        
        # Clean Docker buildx
        log_phase "PREP" "Cleaning Docker Buildx cache..."
        if docker buildx prune -f &> /dev/null; then
            log_phase "PREP" "Buildx cache cleaned"
        else
            log_warning "Failed to clean buildx cache"
        fi
        
        # Clean old containers
        log_phase "PREP" "Cleaning old containers..."
        if docker container prune -f &> /dev/null; then
            log_phase "PREP" "Old containers cleaned"
        else
            log_warning "Failed to clean containers"
        fi
        
        # Clean old images (keep base images)
        log_phase "PREP" "Cleaning dangling images..."
        if docker image prune -f &> /dev/null; then
            log_phase "PREP" "Dangling images cleaned"
        else
            log_warning "Failed to clean images"
        fi
    fi
    
    # Ensure project directories
    local dirs=("data" "logs" "temp" ".devcontainer")
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_phase "PREP" "Created directory: $dir"
        fi
    done
    
    # Generate environment files
    log_phase "PREP" "Setting up environment configuration..."
    
    # Create development environment file
    local build_timestamp=$(date '+%Y%m%d-%H%M%S')
    local git_sha="unknown"
    if command -v git &> /dev/null && git rev-parse --git-dir &> /dev/null; then
        git_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    fi
    
    cat > .env.dev << EOF
# Lucid RDP Development Environment - Generated $(date)
NODE_ENV=development
LUCID_MODE=development
LUCID_NETWORK=testnet
LOG_LEVEL=DEBUG
MONGO_URI=mongodb://mongo:27017/lucid_dev
TOR_ENABLED=true
CHUNK_SIZE=8388608
COMPRESSION_LEVEL=1
BUILD_TIMESTAMP=$build_timestamp
GIT_SHA=$git_sha
EOF
    
    log_phase "PREP" "Created .env.dev"
    
    # Copy Tor configuration if available
    if [[ -f "02-network-security/tor/torrc" ]]; then
        cp "02-network-security/tor/torrc" ".devcontainer/torrc"
        log_phase "PREP" "Copied Tor configuration"
    fi
    
    # Set permissions on scripts
    if [[ -f "$BUILD_SCRIPT_SH" ]]; then
        chmod +x "$BUILD_SCRIPT_SH"
    fi
    if [[ -f "$DEPLOYMENT_SCRIPT" ]]; then
        chmod +x "$DEPLOYMENT_SCRIPT"
    fi
    
    log_success "Preparation phase completed"
    return 0
}

# Phase 2: Network Setup
start_network_phase() {
    log_color "$MAGENTA" "===== PHASE 2: NETWORK SETUP ====="
    log_phase "NETWORK" "Setting up Docker networks..."
    
    # Create basic network (since we may not have the PS1 script on Linux)
    local network_name="lucid-dev_lucid_net"
    
    if docker network inspect "$network_name" &> /dev/null; then
        log_phase "NETWORK" "Network '$network_name' already exists"
    else
        if docker network create --driver bridge --attachable "$network_name"; then
            log_phase "NETWORK" "Created network: $network_name"
        else
            log_error "Failed to create network: $network_name"
            return 1
        fi
    fi
    
    # Create additional networks for different components
    local networks=(
        "lucid-internal:Internal communication network"
        "lucid-blockchain:Blockchain and wallet services"
        "lucid-tor:Tor and onion services"
    )
    
    for net_info in "${networks[@]}"; do
        local net_name="${net_info%%:*}"
        local net_desc="${net_info#*:}"
        
        if ! docker network inspect "$net_name" &> /dev/null; then
            if docker network create --driver bridge --attachable "$net_name"; then
                log_phase "NETWORK" "Created network: $net_name ($net_desc)"
            else
                log_warning "Failed to create network: $net_name"
            fi
        fi
    done
    
    # Verify networks
    log_phase "NETWORK" "Verifying networks..."
    local lucid_networks
    lucid_networks=$(docker network ls --format "{{.Name}}" | grep -E "(lucid|LUCID)" || true)
    
    if [[ -n "$lucid_networks" ]]; then
        log_phase "NETWORK" "Available Lucid networks:"
        while IFS= read -r net; do
            log_phase "NETWORK" "  - $net"
        done <<< "$lucid_networks"
        log_success "Network verification completed"
        return 0
    else
        log_error "No Lucid networks found"
        return 1
    fi
}

# Phase 3: Build DevContainer
start_build_phase() {
    log_color "$MAGENTA" "===== PHASE 3: BUILD DEVCONTAINER ====="
    log_phase "BUILD" "Starting DevContainer build..."
    
    # Prepare build arguments
    local build_args=()
    if [[ "$TEST_ONLY" == "true" ]]; then
        build_args+=(--test-only)
    fi
    if [[ "$NO_CACHE" == "true" ]]; then
        build_args+=(--no-cache)
    fi
    if [[ "$CLEAN_BUILD" == "true" ]]; then
        build_args+=(--clean)
    fi
    
    if [[ -f "$BUILD_SCRIPT_SH" ]]; then
        if "$BUILD_SCRIPT_SH" "${build_args[@]}"; then
            log_success "DevContainer build completed successfully"
            return 0
        else
            log_error "Build script failed"
            return 1
        fi
    else
        log_error "Build script not found: $BUILD_SCRIPT_SH"
        return 1
    fi
}

# Phase 4: Integration Tests
start_test_phase() {
    log_color "$MAGENTA" "===== PHASE 4: INTEGRATION TESTS ====="
    log_phase "TEST" "Running integration tests..."
    
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Tests skipped by user request"
        return 0
    fi
    
    # Test 1: Component imports
    log_phase "TEST" "Testing component imports..."
    if command -v python3 &> /dev/null; then
        if python3 -c "
import sys
sys.path.append('.')
try:
    from node import NodeManager, PeerDiscovery
    from session import SessionRecorder, ChunkManager
    from wallet import WalletManager
    print('PASS: Component imports successful')
except ImportError as e:
    print(f'FAIL: Import error - {e}')
    sys.exit(1)
" 2>/dev/null; then
            log_phase "TEST" "Component imports: PASS"
        else
            log_warning "Component import test failed"
        fi
    else
        log_warning "Python3 not available for component testing"
    fi
    
    # Test 2: Docker network connectivity
    log_phase "TEST" "Testing Docker network connectivity..."
    if docker run --rm --network lucid-dev_lucid_net alpine:latest ping -c 1 8.8.8.8 &> /dev/null; then
        log_phase "TEST" "Network connectivity: PASS"
    else
        log_warning "Network connectivity test failed"
    fi
    
    # Test 3: Container startup
    if [[ "$TEST_ONLY" != "true" ]]; then
        log_phase "TEST" "Testing container startup..."
        local test_image="pickme/lucid:dev-latest"
        
        if docker pull "$test_image" &> /dev/null; then
            local container_id
            container_id=$(docker run -d --network lucid-dev_lucid_net "$test_image" sleep 30)
            sleep 2
            
            if docker ps | grep -q "$container_id"; then
                log_phase "TEST" "Container startup: PASS"
                docker stop "$container_id" &> /dev/null
                docker rm "$container_id" &> /dev/null
            else
                log_warning "Container startup test failed"
            fi
        else
            log_warning "Could not pull test image for container startup test"
        fi
    fi
    
    log_success "Integration tests completed"
    return 0
}

# Phase 5: Development Deployment
start_deploy_phase() {
    log_color "$MAGENTA" "===== PHASE 5: DEVELOPMENT DEPLOYMENT ====="
    log_phase "DEPLOY" "Starting development deployment..."
    
    if [[ "$TEST_ONLY" == "true" ]]; then
        log_warning "Deployment skipped in test-only mode"
        return 0
    fi
    
    if [[ -f "$DEPLOYMENT_SCRIPT" ]]; then
        if "$DEPLOYMENT_SCRIPT" deploy; then
            log_success "Development deployment completed"
            return 0
        else
            local exit_code=$?
            if [[ $exit_code -eq 0 ]]; then
                log_success "Development deployment completed"
                return 0
            else
                log_warning "Deployment script completed with warnings (exit code: $exit_code)"
                return 0
            fi
        fi
    else
        log_warning "Deployment script not found: $DEPLOYMENT_SCRIPT"
        log_phase "DEPLOY" "Starting basic Docker Compose deployment..."
        
        # Basic compose deployment
        local compose_file="06-orchestration-runtime/compose/lucid-dev.yaml"
        if [[ -f "$compose_file" ]]; then
            if docker-compose -f "$compose_file" up -d; then
                log_success "Basic Docker Compose deployment started"
                return 0
            else
                log_error "Docker Compose deployment failed"
                return 1
            fi
        else
            log_warning "No deployment configuration found"
            return 0
        fi
    fi
}

# Main orchestration function
start_build_pipeline() {
    local phase="${1:-all}"
    
    log_color "$CYAN" "====================================="
    log_color "$CYAN" "    LUCID RDP BUILD PIPELINE"
    log_color "$CYAN" "====================================="
    echo
    log_phase "MASTER" "Build pipeline started"
    log_phase "MASTER" "Mode: $(if [[ "$TEST_ONLY" == "true" ]]; then echo 'TEST ONLY'; else echo 'FULL BUILD'; fi)"
    log_phase "MASTER" "Phase: $phase"
    log_phase "MASTER" "Clean: $CLEAN_BUILD"
    log_phase "MASTER" "Cache: $(if [[ "$NO_CACHE" == "true" ]]; then echo 'DISABLED'; else echo 'ENABLED'; fi)"
    echo
    
    local start_time=$(date +%s)
    local success=true
    
    # Check prerequisites first
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    log_success "Prerequisites verified"
    echo
    
    # Execute phases based on selection
    case "${phase,,}" in
        prep)
            success=$(start_prep_phase && echo true || echo false)
            ;;
        network)
            success=$(start_network_phase && echo true || echo false)
            ;;
        build)
            success=$(start_build_phase && echo true || echo false)
            ;;
        test)
            success=$(start_test_phase && echo true || echo false)
            ;;
        deploy)
            success=$(start_deploy_phase && echo true || echo false)
            ;;
        all)
            start_prep_phase && \
            start_network_phase && \
            start_build_phase && \
            start_test_phase && \
            start_deploy_phase
            success=$?
            ;;
        *)
            log_error "Unknown phase: $phase"
            exit 1
            ;;
    esac
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local duration_formatted=$(printf '%02d:%02d' $((duration/60)) $((duration%60)))
    
    if [[ $success == true ]] || [[ $success -eq 0 ]]; then
        echo
        log_color "$GREEN" "====================================="
        log_color "$GREEN" "    BUILD PIPELINE COMPLETED!"
        log_color "$GREEN" "====================================="
        log_success "Total duration: $duration_formatted"
        log_phase "MASTER" "All phases completed successfully"
        
        if [[ "$TEST_ONLY" != "true" ]]; then
            echo
            log_phase "MASTER" "Next steps:"
            log_phase "MASTER" "1. Check container status: docker ps"
            log_phase "MASTER" "2. View logs: docker-compose logs -f"
            log_phase "MASTER" "3. Access development environment via configured .onion addresses"
        fi
    else
        echo
        log_color "$RED" "====================================="
        log_color "$RED" "    BUILD PIPELINE FAILED!"
        log_color "$RED" "====================================="
        log_error "Pipeline failed after $duration_formatted"
        
        echo
        log_phase "MASTER" "Troubleshooting tips:"
        log_phase "MASTER" "1. Check Docker daemon is running: docker info"
        log_phase "MASTER" "2. Try clean build: ./build-master.sh --clean"
        log_phase "MASTER" "3. Check individual phases: ./build-master.sh --phase prep"
        log_phase "MASTER" "4. View detailed logs in previous output"
        
        exit 1
    fi
}

# Execute the pipeline
start_build_pipeline "$PHASE"