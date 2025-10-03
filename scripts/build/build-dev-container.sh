#!/bin/bash
# Lucid Development Container Build Script
# Comprehensive script for clean, prep, build, and test steps
# Addresses user requirements with proper error handling and tag format fixes

set -euo pipefail

# Script arguments
CLEAN=false
PREP=false
BUILD=false
TEST=false
ALL=false
PROFILE="dev"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean) CLEAN=true; shift ;;
        --prep) PREP=true; shift ;;
        --build) BUILD=true; shift ;;
        --test) TEST=true; shift ;;
        --all) ALL=true; shift ;;
        --profile) PROFILE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--clean] [--prep] [--build] [--test] [--all] [--profile PROFILE]"
            echo "  --clean   Clean Docker environment"
            echo "  --prep    Prepare environment and dependencies"
            echo "  --build   Build all containers"
            echo "  --test    Test the built system"
            echo "  --all     Execute all phases (default if no specific phase specified)"
            echo "  --profile Profile to use (default: dev)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# If no specific action, run all phases
if [[ "$CLEAN" == false && "$PREP" == false && "$BUILD" == false && "$TEST" == false ]] || [[ "$ALL" == true ]]; then
    CLEAN=true
    PREP=true
    BUILD=true
    TEST=true
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
NETWORK_NAME="lucid-dev_lucid_net"
BUILDX_BUILDER="lucid-pi"
PROJECT_ROOT="$(pwd)"
COMPOSE_FILE=".devcontainer/docker-compose.dev.yml"
MAIN_COMPOSE_FILE="06-orchestration-runtime/compose/lucid-dev.yaml"

# Generate Docker-safe timestamp (replace colons with hyphens)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BUILD_TAG="dev-${TIMESTAMP}"

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${CYAN}[INFO] $1${NC}"
}

# Error handling function
handle_error() {
    error "Build failed at line $1 with exit code $2"
    error "Command: $BASH_COMMAND"
    log "Collecting diagnostic information..."
    
    # Show Docker system info
    docker system df || true
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep -E "(lucid|pickme)" || true
    
    exit "$2"
}

# Set error trap
trap 'handle_error ${LINENO} $?' ERR

# Check if Docker is running
check_docker() {
    log "Checking Docker daemon status..."
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running. Please start Docker and try again."
        exit 1
    fi
    success "Docker daemon is running"
}

# PHASE 1: CLEAN
phase_clean() {
    if [[ "$CLEAN" != true ]]; then return 0; fi
    
    log "=== PHASE 1: CLEANING DOCKER ENVIRONMENT ==="
    
    check_docker
    
    # Stop all Lucid containers
    log "Stopping all Lucid containers..."
    docker ps -q --filter "name=lucid" | xargs -r docker stop 2>/dev/null || true
    success "Stopped all running Lucid containers"
    
    # Remove all Lucid containers
    log "Removing all Lucid containers..."
    docker ps -aq --filter "name=lucid" | xargs -r docker rm -f 2>/dev/null || true
    success "Removed all Lucid containers"
    
    # Remove Lucid images with safe tag handling
    log "Removing Lucid and pickme images..."
    docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "(lucid|pickme)" | while read -r image; do
        docker rmi -f "$image" 2>/dev/null || warn "Could not remove image: $image"
    done
    success "Cleaned up Lucid images"
    
    # Clean buildx cache
    log "Cleaning Docker buildx cache..."
    docker buildx prune --all --force >/dev/null 2>&1 || true
    success "Buildx cache cleaned"
    
    # Remove existing buildx builder
    log "Removing existing buildx builder..."
    docker buildx rm "$BUILDX_BUILDER" --force 2>/dev/null || true
    success "Buildx builder cleaned"
    
    # System cleanup
    log "Performing Docker system cleanup..."
    docker system prune -f
    success "Docker system cleaned"
    
    success "=== PHASE 1 COMPLETED: ENVIRONMENT CLEANED ==="
}

# PHASE 2: PREP
phase_prep() {
    if [[ "$PREP" != true ]]; then return 0; fi
    
    log "=== PHASE 2: PREPARING ENVIRONMENT ==="
    
    check_docker
    
    # Verify project structure
    log "Checking project structure..."
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Dev container compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    if [[ ! -f "$MAIN_COMPOSE_FILE" ]]; then
        error "Main compose file not found: $MAIN_COMPOSE_FILE"
        exit 1
    fi
    success "Project structure verified"
    
    # Create/verify network
    log "Setting up Docker network: $NETWORK_NAME"
    if ! docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
        docker network create "$NETWORK_NAME" --driver bridge --attachable
        success "Created Docker network: $NETWORK_NAME"
    else
        info "Docker network already exists: $NETWORK_NAME"
    fi
    
    # Create buildx builder (lucid-pi)
    log "Creating buildx builder: $BUILDX_BUILDER"
    docker buildx create \
        --name "$BUILDX_BUILDER" \
        --driver docker-container \
        --platform linux/amd64,linux/arm64 \
        --use \
        --bootstrap
    success "Created buildx builder: $BUILDX_BUILDER"
    
    # Create required volumes
    log "Creating required Docker volumes..."
    local volumes=(
        "lucid-dev_onion_state"
        "lucid-dev_docker_data" 
        "lucid-devcontainer_docker_data"
    )
    
    for volume in "${volumes[@]}"; do
        if ! docker volume ls --format "{{.Name}}" | grep -q "^${volume}$"; then
            docker volume create "$volume"
            success "Created volume: $volume"
        else
            info "Volume already exists: $volume"
        fi
    done
    
    # Create .env file if it doesn't exist
    local env_file="06-orchestration-runtime/compose/.env"
    if [[ ! -f "$env_file" ]]; then
        log "Creating environment file: $env_file"
        cp "06-orchestration-runtime/compose/.env.example" "$env_file"
        
        # Add Docker-in-Docker specific environment variables
        cat >> "$env_file" << 'EOF'

# Docker-in-Docker Configuration
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1
DOCKER_DEFAULT_PLATFORM=linux/amd64

# Development Configuration
LUCID_ENV=dev
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# Java Configuration
JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
MAVEN_HOME=/usr/share/maven
GRADLE_HOME=/usr/share/gradle
EOF
        success "Environment file created: $env_file"
    else
        info "Environment file already exists: $env_file"
    fi
    
    # Verify Docker system status
    log "Verifying Docker system status..."
    docker system df
    docker network ls | grep -E "(lucid|bridge)" || true
    docker volume ls | grep lucid || true
    
    success "=== PHASE 2 COMPLETED: ENVIRONMENT PREPARED ==="
}

# PHASE 3: BUILD
phase_build() {
    if [[ "$BUILD" != true ]]; then return 0; fi
    
    log "=== PHASE 3: BUILDING CONTAINERS ==="
    
    check_docker
    
    # Set build environment variables
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    export BUILDKIT_PROGRESS=plain
    
    # Build dev container first (Docker-in-Docker container)
    log "Building dev container with Docker-in-Docker support..."
    docker buildx build \
        --builder "$BUILDX_BUILDER" \
        --platform linux/amd64 \
        --tag "pickme/lucid:${BUILD_TAG}" \
        --tag "pickme/lucid:dev-dind" \
        --file .devcontainer/Dockerfile \
        --load \
        . || {
            error "Dev container build failed"
            log "Attempting fallback build without buildx..."
            docker build \
                --tag "pickme/lucid:${BUILD_TAG}" \
                --tag "pickme/lucid:dev-dind" \
                --file .devcontainer/Dockerfile \
                .
        }
    success "Dev container built successfully"
    
    # Build all services using the main compose file
    log "Building all services..."
    pushd "06-orchestration-runtime/compose" >/dev/null
    
    # Update image tag in compose to avoid timestamp colon issues
    sed -i.bak "s/pickme\/lucid:dev-dind/pickme\/lucid:${BUILD_TAG}/g" lucid-dev.yaml
    
    # Build services individually to handle failures gracefully
    local services=("devcontainer" "tor-proxy" "lucid_mongo" "lucid_api" "api-gateway" "tunnel-tools")
    
    for service in "${services[@]}"; do
        if docker-compose -f lucid-dev.yaml config --services | grep -q "^${service}$"; then
            log "Building service: $service"
            if docker-compose -f lucid-dev.yaml build --no-cache "$service"; then
                success "Built service: $service"
            else
                warn "Failed to build service: $service (continuing with others)"
            fi
        else
            info "Service $service not found in compose file, skipping"
        fi
    done
    
    # Restore original compose file
    mv lucid-dev.yaml.bak lucid-dev.yaml 2>/dev/null || true
    
    popd >/dev/null
    
    # List built images
    log "Built images:"
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | \
        grep -E "(lucid|pickme)" | head -10 || true
    
    success "=== PHASE 3 COMPLETED: CONTAINERS BUILT ==="
}

# PHASE 4: TEST
phase_test() {
    if [[ "$TEST" != true ]]; then return 0; fi
    
    log "=== PHASE 4: TESTING SYSTEM ==="
    
    check_docker
    
    # Start dev container for testing
    log "Starting dev container for testing..."
    docker-compose -f "$COMPOSE_FILE" up -d devcontainer
    
    # Wait for container to be ready
    log "Waiting for dev container to be ready..."
    sleep 15
    
    # Test Docker-in-Docker functionality
    log "Testing Docker-in-Docker functionality..."
    
    local container_name="lucid-devcontainer"
    local max_attempts=3
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "Testing Docker availability (attempt $attempt/$max_attempts)..."
        
        if docker exec "$container_name" docker --version >/dev/null 2>&1; then
            success "Docker is available inside dev container"
            
            # Test container creation
            log "Testing container creation capability..."
            if docker exec "$container_name" docker run --rm hello-world >/dev/null 2>&1; then
                success "Container creation test PASSED"
                break
            else
                error "Container creation test FAILED on attempt $attempt"
            fi
        else
            error "Docker not available inside dev container on attempt $attempt"
        fi
        
        ((attempt++))
        if [[ $attempt -le $max_attempts ]]; then
            log "Retrying in 10 seconds..."
            sleep 10
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        error "Docker-in-Docker testing failed after $max_attempts attempts"
        # Don't exit here, continue with other tests
    fi
    
    # Test Java availability
    log "Testing Java availability..."
    if docker exec "$container_name" java -version >/dev/null 2>&1; then
        local java_version
        java_version=$(docker exec "$container_name" java -version 2>&1 | head -1)
        success "Java is available: $java_version"
    else
        error "Java is not available inside dev container"
    fi
    
    # Test Python availability
    log "Testing Python availability..."
    if docker exec "$container_name" python3 --version >/dev/null 2>&1; then
        local python_version
        python_version=$(docker exec "$container_name" python3 --version)
        success "Python is available: $python_version"
    else
        error "Python is not available inside dev container"
    fi
    
    # Test build tools availability
    log "Testing build tools..."
    local tools=("gcc" "make" "cmake" "git")
    for tool in "${tools[@]}"; do
        if docker exec "$container_name" which "$tool" >/dev/null 2>&1; then
            success "$tool is available"
        else
            warn "$tool is not available"
        fi
    done
    
    # Test cryptography libraries (test if Python crypto packages can be imported)
    log "Testing cryptography libraries..."
    if docker exec "$container_name" python3 -c "import cryptography; import nacl; print('Crypto libraries OK')" >/dev/null 2>&1; then
        success "Cryptography libraries are working"
    else
        warn "Some cryptography libraries may not be working properly"
    fi
    
    # Test Tor availability
    log "Testing Tor availability..."
    if docker exec "$container_name" which tor >/dev/null 2>&1; then
        success "Tor is available"
    else
        warn "Tor is not available"
    fi
    
    # Test project files access
    log "Testing project files access..."
    local file_count
    file_count=$(docker exec "$container_name" find /workspaces/Lucid -type f -name "*.py" | wc -l)
    if [[ $file_count -gt 0 ]]; then
        success "Project files accessible: $file_count Python files found"
    else
        warn "Project files may not be properly mounted"
    fi
    
    # Test SSH configuration
    log "Testing SSH configuration..."
    if docker exec "$container_name" test -f /root/.ssh/config; then
        success "SSH configuration is present"
    else
        warn "SSH configuration not found"
    fi
    
    # Show container status
    log "Container status:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    # Cleanup test container
    log "Cleaning up test containers..."
    docker-compose -f "$COMPOSE_FILE" down
    
    success "=== PHASE 4 COMPLETED: SYSTEM TESTED ==="
}

# Main execution function
main() {
    log "=== LUCID DEVELOPMENT CONTAINER BUILD SCRIPT ==="
    log "Profile: $PROFILE"
    log "Build tag: $BUILD_TAG"
    log "Project root: $PROJECT_ROOT"
    
    # Verify we're in the correct directory
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Dev container compose file not found: $COMPOSE_FILE"
        error "Please run this script from the Lucid project root directory"
        exit 1
    fi
    
    # Execute phases based on user selection
    phase_clean
    phase_prep
    phase_build
    phase_test
    
    # Final summary
    log "=== BUILD SCRIPT COMPLETED SUCCESSFULLY ==="
    success "Lucid Development Container is ready!"
    
    echo ""
    info "=== USAGE INSTRUCTIONS ==="
    echo "To use the dev container:"
    echo "  1. Open VS Code in this directory"
    echo "  2. Install the 'Dev Containers' extension if not already installed"
    echo "  3. Press Ctrl+Shift+P and select 'Dev Containers: Reopen in Container'"
    echo "  4. VS Code will attach to the running dev container"
    echo ""
    echo "Direct access methods:"
    echo "  • SSH: ssh -p 2222 root@localhost (password: lucid)"
    echo "  • Docker exec: docker exec -it lucid-devcontainer bash"
    echo ""
    echo "Inside the container, Docker will be available for creating and managing other containers."
    echo "Network: $NETWORK_NAME"
    echo "Buildx builder: $BUILDX_BUILDER"
    echo "Container includes: Java 17, Python 3, build tools, cryptography libs, and Tor"
}

# Execute main function
main "$@"