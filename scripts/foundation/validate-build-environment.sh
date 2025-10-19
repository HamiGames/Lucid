#!/bin/bash
# Build Environment Validation Script
# Implements Step 3 from docker-build-process-plan.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
BUILD_PLATFORM="linux/arm64"

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

# Function to check Docker Desktop on Windows 11
check_docker_desktop() {
    log_info "Checking Docker Desktop on Windows 11..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    # Check if running on Windows
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -n "$WINDIR" ]]; then
        log_success "Running on Windows - Docker Desktop detected"
    else
        log_warning "Not running on Windows - ensure Docker Desktop is installed"
    fi
    
    # Check Docker version
    local docker_version=$(docker --version)
    log_info "Docker version: $docker_version"
    
    log_success "Docker Desktop validation passed"
    return 0
}

# Function to check Docker Compose v2
check_docker_compose() {
    log_info "Checking Docker Compose v2..."
    
    if command -v docker-compose &> /dev/null; then
        local compose_version=$(docker-compose --version)
        log_info "Docker Compose version: $compose_version"
        log_success "Docker Compose v2 available"
    elif docker compose version &> /dev/null; then
        local compose_version=$(docker compose version)
        log_info "Docker Compose version: $compose_version"
        log_success "Docker Compose v2 available"
    else
        log_error "Docker Compose v2 not found"
        return 1
    fi
    
    return 0
}

# Function to check Docker BuildKit
check_docker_buildkit() {
    log_info "Checking Docker BuildKit..."
    
    if ! docker buildx version &> /dev/null; then
        log_error "Docker BuildKit is not available"
        return 1
    fi
    
    local buildx_version=$(docker buildx version)
    log_info "Docker BuildKit version: $buildx_version"
    
    # Check if buildx is enabled
    if docker info | grep -q "BuildKit"; then
        log_success "Docker BuildKit is enabled"
    else
        log_warning "Docker BuildKit may not be enabled"
    fi
    
    return 0
}

# Function to check SSH connection to Pi
check_ssh_connection() {
    log_info "Checking SSH connection to Raspberry Pi..."
    log_info "Pi Host: $PI_HOST"
    log_info "Pi User: $PI_USER"
    
    if ! command -v ssh &> /dev/null; then
        log_error "SSH client is not installed"
        return 1
    fi
    
    # Test SSH connection
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$PI_USER@$PI_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
        log_success "SSH connection to Pi successful"
    else
        log_error "SSH connection to Pi failed"
        log_info "Please ensure:"
        log_info "  • Pi is accessible at $PI_HOST"
        log_info "  • SSH keys are configured"
        log_info "  • SSH service is running on Pi"
        return 1
    fi
    
    return 0
}

# Function to check Pi disk space
check_pi_disk_space() {
    log_info "Checking Pi disk space..."
    
    local disk_info=$(ssh "$PI_USER@$PI_HOST" "df -h /" 2>/dev/null | tail -1)
    local available_space=$(echo "$disk_info" | awk '{print $4}')
    local available_bytes=$(echo "$disk_info" | awk '{print $4}' | sed 's/G/000000000/' | sed 's/M/000000/' | sed 's/K/000/')
    
    log_info "Pi disk space: $available_space available"
    
    # Check if at least 20GB is available
    if [[ $available_bytes -gt 20000000000 ]]; then
        log_success "Pi has sufficient disk space (>20GB)"
    else
        log_error "Pi has insufficient disk space (<20GB)"
        return 1
    fi
    
    return 0
}

# Function to check Pi architecture
check_pi_architecture() {
    log_info "Checking Pi architecture..."
    
    local pi_arch=$(ssh "$PI_USER@$PI_HOST" "uname -m" 2>/dev/null)
    log_info "Pi architecture: $pi_arch"
    
    if [[ "$pi_arch" == "aarch64" ]]; then
        log_success "Pi architecture is aarch64 (ARM64)"
    else
        log_error "Pi architecture is not aarch64 (ARM64)"
        return 1
    fi
    
    return 0
}

# Function to check Docker daemon on Pi
check_pi_docker_daemon() {
    log_info "Checking Docker daemon on Pi..."
    
    if ssh "$PI_USER@$PI_HOST" "docker info" &> /dev/null; then
        log_success "Docker daemon is running on Pi"
    else
        log_error "Docker daemon is not running on Pi"
        return 1
    fi
    
    # Check Docker version on Pi
    local pi_docker_version=$(ssh "$PI_USER@$PI_HOST" "docker --version" 2>/dev/null)
    log_info "Pi Docker version: $pi_docker_version"
    
    return 0
}

# Function to check network connectivity
check_network_connectivity() {
    log_info "Checking network connectivity..."
    
    # Check Pi connectivity
    if ping -c 1 -W 5 "$PI_HOST" &> /dev/null; then
        log_success "Network connectivity to Pi successful"
    else
        log_error "Network connectivity to Pi failed"
        return 1
    fi
    
    # Check internet connectivity
    if ping -c 1 -W 5 8.8.8.8 &> /dev/null; then
        log_success "Internet connectivity successful"
    else
        log_warning "Internet connectivity failed"
    fi
    
    return 0
}

# Function to check base images accessibility
check_base_images_accessibility() {
    log_info "Checking base images accessibility..."
    
    local base_images=(
        "python:3.11-slim"
        "gcr.io/distroless/python3-debian12:arm64"
        "openjdk:17-jdk-slim"
        "gcr.io/distroless/java17-debian12:arm64"
        "mongo:7.0"
        "redis:7.2-alpine"
        "elasticsearch:8.11.0"
    )
    
    for image in "${base_images[@]}"; do
        log_info "Checking base image: $image"
        
        if docker manifest inspect "$image" &> /dev/null; then
            log_success "Base image accessible: $image"
        else
            log_warning "Base image may not be accessible: $image"
        fi
    done
    
    return 0
}

# Function to check required tools
check_required_tools() {
    log_info "Checking required tools..."
    
    local required_tools=("docker" "docker-compose" "ssh" "ping" "openssl")
    
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_success "Tool available: $tool"
        else
            log_error "Tool not found: $tool"
            return 1
        fi
    done
    
    # Check optional tools
    local optional_tools=("jq" "yq" "curl" "git")
    
    for tool in "${optional_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_success "Optional tool available: $tool"
        else
            log_warning "Optional tool not found: $tool"
        fi
    done
    
    return 0
}

# Function to check build environment variables
check_build_environment_variables() {
    log_info "Checking build environment variables..."
    
    local required_vars=(
        "BUILD_PLATFORM"
        "PI_HOST"
        "PI_USER"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            log_success "Environment variable set: $var=${!var}"
        else
            log_warning "Environment variable not set: $var"
        fi
    done
    
    return 0
}

# Function to check project structure
check_project_structure() {
    log_info "Checking project structure..."
    
    local required_dirs=(
        "infrastructure/containers/base"
        "auth"
        "database"
        "configs"
        "scripts"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            log_success "Directory exists: $dir"
        else
            log_error "Directory not found: $dir"
            return 1
        fi
    done
    
    return 0
}

# Function to check Dockerfile existence
check_dockerfile_existence() {
    log_info "Checking Dockerfile existence..."
    
    local required_dockerfiles=(
        "infrastructure/containers/base/Dockerfile.python-base"
        "infrastructure/containers/base/Dockerfile.java-base"
        "auth/Dockerfile"
        "database/Dockerfile"
    )
    
    for dockerfile in "${required_dockerfiles[@]}"; do
        if [[ -f "$dockerfile" ]]; then
            log_success "Dockerfile exists: $dockerfile"
        else
            log_error "Dockerfile not found: $dockerfile"
            return 1
        fi
    done
    
    return 0
}

# Function to display validation summary
display_validation_summary() {
    log_info "Build Environment Validation Summary:"
    echo ""
    echo "Validation Results:"
    echo "  • Docker Desktop: $(check_docker_desktop && echo "PASS" || echo "FAIL")"
    echo "  • Docker Compose v2: $(check_docker_compose && echo "PASS" || echo "FAIL")"
    echo "  • Docker BuildKit: $(check_docker_buildkit && echo "PASS" || echo "FAIL")"
    echo "  • SSH Connection: $(check_ssh_connection && echo "PASS" || echo "FAIL")"
    echo "  • Pi Disk Space: $(check_pi_disk_space && echo "PASS" || echo "FAIL")"
    echo "  • Pi Architecture: $(check_pi_architecture && echo "PASS" || echo "FAIL")"
    echo "  • Pi Docker Daemon: $(check_pi_docker_daemon && echo "PASS" || echo "FAIL")"
    echo "  • Network Connectivity: $(check_network_connectivity && echo "PASS" || echo "FAIL")"
    echo "  • Base Images: $(check_base_images_accessibility && echo "PASS" || echo "FAIL")"
    echo "  • Required Tools: $(check_required_tools && echo "PASS" || echo "FAIL")"
    echo "  • Environment Variables: $(check_build_environment_variables && echo "PASS" || echo "FAIL")"
    echo "  • Project Structure: $(check_project_structure && echo "PASS" || echo "FAIL")"
    echo "  • Dockerfile Existence: $(check_dockerfile_existence && echo "PASS" || echo "FAIL")"
    echo ""
}

# Main execution
main() {
    log_info "=== Build Environment Validation ==="
    log_info "Build Host: Windows 11 console"
    log_info "Target Host: Raspberry Pi 5 ($PI_HOST)"
    log_info "Platform: $BUILD_PLATFORM (aarch64)"
    echo ""
    
    local validation_passed=true
    
    # Run all validation checks
    check_docker_desktop || validation_passed=false
    check_docker_compose || validation_passed=false
    check_docker_buildkit || validation_passed=false
    check_ssh_connection || validation_passed=false
    check_pi_disk_space || validation_passed=false
    check_pi_architecture || validation_passed=false
    check_pi_docker_daemon || validation_passed=false
    check_network_connectivity || validation_passed=false
    check_base_images_accessibility || validation_passed=false
    check_required_tools || validation_passed=false
    check_build_environment_variables || validation_passed=false
    check_project_structure || validation_passed=false
    check_dockerfile_existence || validation_passed=false
    
    # Display summary
    echo ""
    display_validation_summary
    
    if [[ "$validation_passed" == "true" ]]; then
        log_success "Build environment validation completed successfully!"
        log_info "All prerequisites are met for building Docker images"
        return 0
    else
        log_error "Build environment validation failed!"
        log_info "Please fix the issues above before proceeding with the build"
        return 1
    fi
}

# Run main function
main "$@"