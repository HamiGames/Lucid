#!/bin/bash
# Lucid Docker Environment Setup Script
# Complete Docker-in-Docker setup with lucid-pi buildx builder and network configuration
# Addresses user requirements for full script assessment and dev container system config

set -euo pipefail

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

# Logging function
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

# Check if Docker is running
check_docker() {
    log "Checking Docker daemon status..."
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running. Please start Docker and try again."
        exit 1
    fi
    success "Docker daemon is running"
}

# Docker network pre-configuration and checks
setup_network() {
    log "=== DOCKER NETWORK SETUP ==="
    
    # Check if network exists and remove if needed
    if docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
        warn "Network ${NETWORK_NAME} already exists, removing..."
        docker network rm "${NETWORK_NAME}" || true
    fi
    
    # Create the lucid-dev network
    log "Creating Docker network: ${NETWORK_NAME}"
    docker network create \
        --driver bridge \
        --attachable \
        --subnet=172.20.0.0/16 \
        --ip-range=172.20.1.0/24 \
        --gateway=172.20.1.1 \
        "${NETWORK_NAME}"
    
    success "Network ${NETWORK_NAME} created successfully"
    
    # Verify network creation
    docker network inspect "${NETWORK_NAME}" >/dev/null
    success "Network verification passed"
}

# Docker buildx clear and rebuild
setup_buildx() {
    log "=== DOCKER BUILDX SETUP ==="
    
    # Clear existing buildx cache
    log "Clearing Docker buildx cache..."
    docker buildx prune --all --force >/dev/null 2>&1 || true
    success "Buildx cache cleared"
    
    # Remove existing builder if it exists
    if docker buildx ls | grep -q "${BUILDX_BUILDER}"; then
        warn "Builder ${BUILDX_BUILDER} already exists, removing..."
        docker buildx rm "${BUILDX_BUILDER}" --force || true
    fi
    
    # Create new buildx builder with SSH support
    log "Creating buildx builder: ${BUILDX_BUILDER}"
    docker buildx create \
        --name "${BUILDX_BUILDER}" \
        --driver docker-container \
        --platform linux/amd64,linux/arm64 \
        --use \
        --bootstrap \
        --config /dev/stdin << 'EOF'
[registry."docker.io"]
  mirrors = ["https://mirror.gcr.io"]
EOF
    
    success "Buildx builder ${BUILDX_BUILDER} created successfully"
    
    # Verify builder
    docker buildx inspect "${BUILDX_BUILDER}"
    success "Buildx builder verification passed"
}

# SSH configuration for dev-container
setup_ssh_config() {
    log "=== SSH CONFIGURATION ==="
    
    # Create SSH directory in project if it doesn't exist
    mkdir -p "${PROJECT_ROOT}/.ssh"
    
    # Create basic SSH config for dev container
    cat > "${PROJECT_ROOT}/.ssh/config" << 'EOF'
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    LogLevel ERROR
    ServerAliveInterval 60
    ServerAliveCountMax 3

Host lucid-pi
    HostName raspberry-pi.local
    User pi
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    ForwardAgent yes
EOF
    
    chmod 600 "${PROJECT_ROOT}/.ssh/config"
    success "SSH configuration created"
}

# Create development environment files
setup_env_files() {
    log "=== ENVIRONMENT FILES SETUP ==="
    
    # Create .env file for compose
    if [[ ! -f "${PROJECT_ROOT}/06-orchestration-runtime/compose/.env" ]]; then
        log "Creating environment file..."
        cp "${PROJECT_ROOT}/06-orchestration-runtime/compose/.env.example" \
           "${PROJECT_ROOT}/06-orchestration-runtime/compose/.env"
        
        # Add required environment variables
        cat >> "${PROJECT_ROOT}/06-orchestration-runtime/compose/.env" << 'EOF'

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
        success "Environment file created"
    else
        warn "Environment file already exists, skipping creation"
    fi
}

# Create Docker volumes
setup_volumes() {
    log "=== DOCKER VOLUMES SETUP ==="
    
    local volumes=(
        "lucid-dev_onion_state"
        "lucid-dev_docker_data"
        "lucid-devcontainer_docker_data"
    )
    
    for volume in "${volumes[@]}"; do
        if ! docker volume ls --format "{{.Name}}" | grep -q "^${volume}$"; then
            log "Creating volume: ${volume}"
            docker volume create "${volume}"
            success "Volume ${volume} created"
        else
            warn "Volume ${volume} already exists"
        fi
    done
}

# Validate Docker-in-Docker functionality
test_dind() {
    log "=== DOCKER-IN-DOCKER VALIDATION ==="
    
    # Start the dev container for testing
    log "Starting dev container for DinD testing..."
    docker-compose -f "${COMPOSE_FILE}" up -d devcontainer
    
    # Wait for container to be ready
    sleep 10
    
    # Test Docker availability inside container
    log "Testing Docker availability inside dev container..."
    if docker exec lucid-devcontainer docker --version >/dev/null 2>&1; then
        success "Docker is available inside dev container"
        
        # Test container creation capability
        log "Testing container creation inside dev container..."
        if docker exec lucid-devcontainer docker run --rm hello-world >/dev/null 2>&1; then
            success "Container creation test PASSED - Docker-in-Docker is working"
        else
            error "Container creation test FAILED"
            return 1
        fi
    else
        error "Docker is not available inside dev container"
        return 1
    fi
    
    # Stop test container
    docker-compose -f "${COMPOSE_FILE}" down
    success "Docker-in-Docker validation completed"
}

# Main execution
main() {
    log "Starting Lucid Docker Environment Setup..."
    log "Project root: ${PROJECT_ROOT}"
    
    # Verify we're in the right directory
    if [[ ! -f "${COMPOSE_FILE}" ]]; then
        error "Docker compose file not found: ${COMPOSE_FILE}"
        error "Please run this script from the Lucid project root directory"
        exit 1
    fi
    
    # Execute setup phases
    check_docker
    setup_network
    setup_buildx
    setup_ssh_config
    setup_env_files
    setup_volumes
    
    # Test the setup
    log "=== TESTING CONFIGURATION ==="
    test_dind
    
    # Final status
    log "=== SETUP COMPLETE ==="
    success "Lucid Docker Environment Setup completed successfully!"
    
    echo ""
    log "Configuration Summary:"
    echo "  • Network: ${NETWORK_NAME}"
    echo "  • Buildx Builder: ${BUILDX_BUILDER}"
    echo "  • SSH Config: ${PROJECT_ROOT}/.ssh/config"
    echo "  • Docker-in-Docker: Enabled and tested"
    echo ""
    log "Next Steps:"
    echo "  1. Run: ./build-dev-container.sh --all"
    echo "  2. Open VS Code and use 'Dev Containers: Reopen in Container'"
    echo "  3. Inside the dev container, Docker will be available for building other containers"
    echo ""
    log "Access Methods:"
    echo "  • VS Code Dev Container: Recommended method"
    echo "  • SSH: ssh -p 2222 root@localhost"
    echo "  • Docker exec: docker exec -it lucid-devcontainer bash"
}

# Execute main function
main "$@"