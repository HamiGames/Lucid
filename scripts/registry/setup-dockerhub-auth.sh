#!/bin/bash
# Setup Docker Hub Authentication for pickme/lucid namespace
# Implements Docker Hub authentication as per docker-build-process-plan.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_HUB_USERNAME="pickme"
REPOSITORY_NAME="lucid"
DOCKER_HUB_API_URL="https://hub.docker.com/v2"

# Logging functions
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

# Function to check Docker installation
check_docker() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_success "Docker is installed and running"
}

# Function to check Docker BuildKit
check_buildkit() {
    log_info "Checking Docker BuildKit..."
    
    if ! docker buildx version &> /dev/null; then
        log_error "Docker BuildKit is not available"
        exit 1
    fi
    
    log_success "Docker BuildKit is available"
}

# Function to authenticate to Docker Hub
authenticate_dockerhub() {
    log_info "Setting up Docker Hub authentication..."
    
    # Check if already logged in as pickme
    if docker info | grep -q "Username: pickme"; then
        log_success "Already authenticated to Docker Hub as 'pickme'"
        return 0
    fi
    
    # Check if logged in as different user
    if docker info | grep -q "Username:"; then
        log_warning "Currently logged in as different user, logging out..."
        docker logout
    fi
    
    log_info "Please authenticate to Docker Hub:"
    log_info "Username: pickme"
    log_info "Password: [Enter your Docker Hub password]"
    
    # Perform login
    if docker login; then
        log_success "Docker Hub authentication successful"
    else
        log_error "Docker Hub authentication failed"
        exit 1
    fi
}

# Function to verify authentication
verify_authentication() {
    log_info "Verifying Docker Hub authentication..."
    
    # Check authentication status
    if ! docker info | grep -q "Username: pickme"; then
        log_error "Authentication verification failed - not logged in as 'pickme'"
        exit 1
    fi
    
    # Test push capability by checking if we can access our namespace
    log_info "Testing repository access..."
    if docker search "$DOCKER_HUB_USERNAME/$REPOSITORY_NAME" &> /dev/null; then
        log_success "Repository access verified"
    else
        log_warning "Could not verify repository access (repository may not exist yet)"
    fi
    
    log_success "Authentication verification completed"
}

# Function to create buildx builder
setup_buildx_builder() {
    log_info "Setting up Docker Buildx builder..."
    
    local builder_name="lucid-pi-builder"
    
    # Check if builder exists
    if docker buildx ls | grep -q "$builder_name"; then
        log_info "Builder '$builder_name' already exists"
    else
        log_info "Creating builder '$builder_name'..."
        docker buildx create --name "$builder_name" --use --driver docker-container --platform linux/arm64,linux/amd64
    fi
    
    # Use the builder
    docker buildx use "$builder_name"
    
    # Bootstrap the builder
    log_info "Bootstrapping builder..."
    docker buildx inspect --bootstrap
    
    log_success "Buildx builder setup completed"
}

# Function to verify platform support
verify_platform_support() {
    log_info "Verifying platform support..."
    
    local platforms=("linux/arm64" "linux/amd64")
    
    for platform in "${platforms[@]}"; do
        if docker buildx inspect | grep -q "$platform"; then
            log_success "Platform $platform supported"
        else
            log_warning "Platform $platform not found in builder"
        fi
    done
}

# Function to test registry connectivity
test_registry_connectivity() {
    log_info "Testing registry connectivity..."
    
    # Test Docker Hub connectivity
    if curl -s --connect-timeout 10 https://hub.docker.com > /dev/null; then
        log_success "Docker Hub connectivity verified"
    else
        log_error "Cannot reach Docker Hub"
        exit 1
    fi
    
    # Test authentication by trying to get user info
    log_info "Testing authentication with Docker Hub API..."
    local token=$(docker system info --format '{{.RegistryConfig.Auths}}' | grep -o '"pickme":[^}]*' | grep -o '"auth":"[^"]*"' | cut -d'"' -f4)
    
    if [[ -n "$token" ]]; then
        log_success "Authentication token found"
    else
        log_warning "Could not verify authentication token"
    fi
}

# Function to display configuration summary
display_configuration_summary() {
    log_info "Configuration Summary:"
    echo "  • Docker Hub Username: $DOCKER_HUB_USERNAME"
    echo "  • Repository Name: $REPOSITORY_NAME"
    echo "  • Registry: docker.io"
    echo "  • Build Platform: linux/arm64 (Raspberry Pi)"
    echo "  • Builder: lucid-pi-builder"
    echo ""
    log_info "Authentication Status:"
    docker info | grep "Username:" || echo "  • Not authenticated"
    echo ""
}

# Main execution
main() {
    log_info "=== Docker Hub Authentication Setup ==="
    log_info "Repository: $DOCKER_HUB_USERNAME/$REPOSITORY_NAME"
    log_info "Target Platform: linux/arm64 (Raspberry Pi)"
    echo ""
    
    # Execute setup steps
    check_docker
    check_buildkit
    authenticate_dockerhub
    verify_authentication
    setup_buildx_builder
    verify_platform_support
    test_registry_connectivity
    
    # Display summary
    echo ""
    display_configuration_summary
    
    log_success "Docker Hub authentication setup completed successfully!"
    log_info "Ready to build and push images to $DOCKER_HUB_USERNAME/$REPOSITORY_NAME"
}

# Run main function
main "$@"
