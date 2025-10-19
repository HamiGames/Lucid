#!/bin/bash
# Pre-Phase 1 Pi Deployment Script
# Ensures all pre-build requirements are complete on the Pi side
# Based on docker-build-process-plan.md requirements

set -euo pipefail

# Configuration
PI_HOST="pickme@192.168.0.75"
PI_PORT="22"
PI_DEPLOY_PATH="/opt/lucid/production"
PI_DOCKER_HUB_USER="pickme"
PI_DOCKER_HUB_NAMESPACE="pickme/lucid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

log_section() {
    echo -e "\n${PURPLE}=== $1 ===${NC}"
}

log_step() {
    echo -e "\n${CYAN}--- $1 ---${NC}"
}

# Test SSH connection with persistent connection
test_ssh_connection() {
    log_step "Testing SSH Connection"
    
    # Create SSH control directory
    mkdir -p ~/.ssh
    
    log_info "Testing SSH connection to $PI_HOST..."
    
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_success "SSH connection established and persistent connection configured"
        return 0
    else
        log_error "SSH connection failed to $PI_HOST"
        log_error "Please ensure:"
        log_error "  - Pi is powered on and connected to network"
        log_error "  - SSH key is properly configured"
        log_error "  - Network connectivity to 192.168.0.75 exists"
        log_error "  - User 'pickme' exists on Pi"
        return 1
    fi
}

# Test Pi architecture and system info
test_pi_system() {
    log_step "Testing Pi System Architecture"
    
    log_info "Checking Pi architecture..."
    local pi_arch=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "uname -m" 2>/dev/null)
    log_info "Pi architecture: $pi_arch"
    
    if [[ "$pi_arch" == "aarch64" ]]; then
        log_success "Architecture is correct (aarch64) for ARM64 builds"
    else
        log_warning "Architecture is $pi_arch, expected aarch64 for optimal performance"
    fi
    
    # Get Pi system info
    log_info "Gathering Pi system information..."
    local pi_os=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2" | tr -d '"' 2>/dev/null)
    local pi_mem=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "free -h | awk 'NR==2{print \$2}'" 2>/dev/null)
    local pi_cpu=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "nproc" 2>/dev/null)
    
    log_info "Pi OS: $pi_os"
    log_info "Pi Memory: $pi_mem"
    log_info "Pi CPU Cores: $pi_cpu"
}

# Test disk space requirements
test_disk_space() {
    log_step "Testing Disk Space Requirements"
    
    log_info "Checking available disk space..."
    local disk_space=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "df -h / | awk 'NR==2{print \$4}' | sed 's/G.*//'" 2>/dev/null)
    disk_space=$(echo "$disk_space" | tr -d '[:alpha:]' | head -1)
    
    log_info "Available disk space: ${disk_space}GB"
    
    if [[ "$disk_space" =~ ^[0-9]+$ ]] && [[ "$disk_space" -ge 20 ]]; then
        log_success "Sufficient disk space available (${disk_space}GB >= 20GB required)"
    else
        log_warning "Low disk space: ${disk_space}GB (recommended: 20GB+)"
        log_warning "Consider cleaning up or expanding storage before deployment"
    fi
}

# Test Docker installation and configuration
test_docker_setup() {
    log_step "Testing Docker Setup"
    
    log_info "Checking Docker installation..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker --version" >/dev/null 2>&1; then
        local docker_version=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker --version" 2>/dev/null)
        log_success "Docker is installed: $docker_version"
    else
        log_error "Docker is not installed on Pi"
        log_error "Please install Docker on Pi first:"
        log_error "  curl -fsSL https://get.docker.com -o get-docker.sh"
        log_error "  sudo sh get-docker.sh"
        log_error "  sudo usermod -aG docker pickme"
        return 1
    fi
    
    log_info "Checking Docker daemon status..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker info" >/dev/null 2>&1; then
        log_success "Docker daemon is running"
    else
        log_error "Docker daemon is not running or not accessible"
        log_error "Please ensure Docker daemon is started:"
        log_error "  sudo systemctl start docker"
        log_error "  sudo systemctl enable docker"
        return 1
    fi
    
    # Check Docker Compose
    log_info "Checking Docker Compose..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker compose version" >/dev/null 2>&1; then
        local compose_version=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker compose version" 2>/dev/null)
        log_success "Docker Compose is available: $compose_version"
    else
        log_warning "Docker Compose not found, will use docker-compose command"
        if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker-compose --version" >/dev/null 2>&1; then
            log_success "docker-compose command is available"
        else
            log_error "Neither 'docker compose' nor 'docker-compose' is available"
            return 1
        fi
    fi
}

# Test Docker Hub connectivity
test_docker_hub_access() {
    log_step "Testing Docker Hub Access"
    
    log_info "Testing Docker Hub connectivity..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker pull hello-world:latest" >/dev/null 2>&1; then
        log_success "Docker Hub connectivity verified"
        # Clean up test image
        ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker rmi hello-world:latest" >/dev/null 2>&1 || true
    else
        log_error "Cannot pull images from Docker Hub"
        log_error "Please check:"
        log_error "  - Internet connectivity on Pi"
        log_error "  - Docker Hub access (no rate limiting)"
        log_error "  - DNS resolution on Pi"
        return 1
    fi
    
    # Test ARM64 image pull capability
    log_info "Testing ARM64 image pull capability..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker pull --platform linux/arm64 alpine:latest" >/dev/null 2>&1; then
        log_success "ARM64 image pull capability verified"
        # Clean up test image
        ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker rmi alpine:latest" >/dev/null 2>&1 || true
    else
        log_warning "ARM64 image pull failed, but this may be normal for some registries"
    fi
}

# Create required directories on Pi
setup_pi_directories() {
    log_step "Setting Up Pi Directories"
    
    log_info "Creating deployment directory: $PI_DEPLOY_PATH"
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "sudo mkdir -p $PI_DEPLOY_PATH" >/dev/null 2>&1; then
        log_success "Deployment directory created"
    else
        log_error "Failed to create deployment directory"
        return 1
    fi
    
    log_info "Setting ownership of deployment directory..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "sudo chown -R pickme:pickme $PI_DEPLOY_PATH" >/dev/null 2>&1; then
        log_success "Deployment directory ownership set to pickme:pickme"
    else
        log_error "Failed to set directory ownership"
        return 1
    fi
    
    # Create subdirectories for different phases
    log_info "Creating subdirectories for deployment phases..."
    local subdirs=("foundation" "core" "application" "support" "configs" "logs" "data" "backups")
    
    for subdir in "${subdirs[@]}"; do
        if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "mkdir -p $PI_DEPLOY_PATH/$subdir" >/dev/null 2>&1; then
            log_success "Created $PI_DEPLOY_PATH/$subdir"
        else
            log_warning "Failed to create $PI_DEPLOY_PATH/$subdir"
        fi
    done
}

# Test Docker network capabilities
test_docker_networking() {
    log_step "Testing Docker Networking"
    
    log_info "Testing Docker network operations..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker network ls" >/dev/null 2>&1; then
        log_success "Docker network operations work"
    else
        log_error "Docker network operations failed"
        return 1
    fi
    
    # Test creating a test network
    log_info "Testing network creation capability..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker network create test-network" >/dev/null 2>&1; then
        log_success "Network creation capability verified"
        # Clean up test network
        ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker network rm test-network" >/dev/null 2>&1 || true
    else
        log_warning "Network creation failed, but this may not be critical"
    fi
}

# Test Docker volume capabilities
test_docker_volumes() {
    log_step "Testing Docker Volume Capabilities"
    
    log_info "Testing Docker volume operations..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker volume ls" >/dev/null 2>&1; then
        log_success "Docker volume operations work"
    else
        log_error "Docker volume operations failed"
        return 1
    fi
    
    # Test creating a test volume
    log_info "Testing volume creation capability..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker volume create test-volume" >/dev/null 2>&1; then
        log_success "Volume creation capability verified"
        # Clean up test volume
        ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker volume rm test-volume" >/dev/null 2>&1 || true
    else
        log_warning "Volume creation failed, but this may not be critical"
    fi
}

# Test Pi performance characteristics
test_pi_performance() {
    log_step "Testing Pi Performance Characteristics"
    
    log_info "Testing CPU performance..."
    local cpu_test=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "timeout 5 dd if=/dev/zero of=/dev/null bs=1M count=100 2>&1 | grep -o '[0-9.]* MB/s'" 2>/dev/null || echo "N/A")
    log_info "CPU performance test: $cpu_test"
    
    log_info "Testing memory performance..."
    local mem_test=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "free -h | awk 'NR==2{print \$3\"/\"\$2}'" 2>/dev/null)
    log_info "Memory usage: $mem_test"
    
    log_info "Testing disk I/O performance..."
    local disk_test=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "timeout 5 dd if=/dev/zero of=/tmp/test-io bs=1M count=50 2>&1 | grep -o '[0-9.]* MB/s'" 2>/dev/null || echo "N/A")
    log_info "Disk I/O performance: $disk_test"
    
    # Clean up test file
    ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "rm -f /tmp/test-io" >/dev/null 2>&1 || true
}

# Test Docker resource limits
test_docker_resources() {
    log_step "Testing Docker Resource Limits"
    
    log_info "Testing Docker container resource limits..."
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker run --rm --memory=100m alpine:latest echo 'Resource test successful'" >/dev/null 2>&1; then
        log_success "Docker resource limits work correctly"
    else
        log_warning "Docker resource limits may not be working properly"
    fi
}

# Clean up any existing Lucid containers/images
cleanup_existing_lucid() {
    log_step "Cleaning Up Existing Lucid Resources"
    
    log_info "Checking for existing Lucid containers..."
    local existing_containers=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker ps -a --filter 'name=lucid' --format '{{.Names}}'" 2>/dev/null || echo "")
    
    if [[ -n "$existing_containers" ]]; then
        log_warning "Found existing Lucid containers:"
        echo "$existing_containers"
        log_info "Stopping and removing existing Lucid containers..."
        ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker stop \$(docker ps -a --filter 'name=lucid' -q) 2>/dev/null || true" >/dev/null 2>&1
        ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker rm \$(docker ps -a --filter 'name=lucid' -q) 2>/dev/null || true" >/dev/null 2>&1
        log_success "Existing Lucid containers cleaned up"
    else
        log_success "No existing Lucid containers found"
    fi
    
    log_info "Checking for existing Lucid images..."
    local existing_images=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker images --filter 'reference=pickme/lucid*' --format '{{.Repository}}:{{.Tag}}'" 2>/dev/null || echo "")
    
    if [[ -n "$existing_images" ]]; then
        log_warning "Found existing Lucid images:"
        echo "$existing_images"
        log_info "Removing existing Lucid images..."
        ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker rmi \$(docker images --filter 'reference=pickme/lucid*' -q) 2>/dev/null || true" >/dev/null 2>&1
        log_success "Existing Lucid images cleaned up"
    else
        log_success "No existing Lucid images found"
    fi
    
    log_info "Cleaning up Docker system..."
    ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker system prune -f" >/dev/null 2>&1 || true
    log_success "Docker system cleaned up"
}

# Generate Pi-specific environment file
generate_pi_environment() {
    log_step "Generating Pi-Specific Environment Configuration"
    
    log_info "Creating Pi environment file..."
    cat > "/tmp/lucid-pi.env" << EOF
# LUCID Pi Deployment Environment
# Generated by pre-phase1-pi-deploy.sh

# Environment Configuration
LUCID_ENV=pi
LUCID_PLANE=ops
CLUSTER_ID=pi-core
DEPLOYMENT_PATH=$PI_DEPLOY_PATH

# Pi-Specific Settings
PI_ARCH=aarch64
PI_HOST=192.168.0.75
PI_USER=pickme

# Docker Configuration
DOCKER_REGISTRY=docker.io
DOCKER_NAMESPACE=$PI_DOCKER_HUB_NAMESPACE
DOCKER_PLATFORM=linux/arm64

# Network Configuration
LUCID_NETWORK=lucid-pi-network
LUCID_NETWORK_SUBNET=172.20.0.0/16

# Database Configuration (will be set by Phase 1)
MONGO_URL=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin&retryWrites=false
REDIS_URL=redis://lucid-redis:6379/0
ELASTICSEARCH_URL=http://lucid-elasticsearch:9200

# Service Ports
AUTH_SERVICE_PORT=8089
API_GATEWAY_PORT=8080
BLOCKCHAIN_ENGINE_PORT=8084
SESSION_ANCHORING_PORT=8085
BLOCK_MANAGER_PORT=8086
DATA_CHAIN_PORT=8087

# Security Settings
JWT_SECRET=\$(openssl rand -base64 64)
ENCRYPTION_KEY=\$(openssl rand -base64 32)
TOR_PASSWORD=\$(openssl rand -base64 32)

# Pi Performance Settings
MAX_MEMORY_USAGE=80%
MAX_CPU_USAGE=80%
DISK_CLEANUP_THRESHOLD=85%
EOF

    log_success "Pi environment file created at /tmp/lucid-pi.env"
}

# Transfer environment file to Pi
transfer_environment_to_pi() {
    log_step "Transferring Environment Configuration to Pi"
    
    log_info "Transferring environment file to Pi..."
    if scp -P "$PI_PORT" -o StrictHostKeyChecking=no "/tmp/lucid-pi.env" "$PI_HOST:$PI_DEPLOY_PATH/configs/lucid-pi.env" >/dev/null 2>&1; then
        log_success "Environment file transferred to Pi"
    else
        log_error "Failed to transfer environment file to Pi"
        return 1
    fi
    
    # Clean up local environment file
    rm -f "/tmp/lucid-pi.env"
    log_success "Local environment file cleaned up"
}

# Final validation
final_validation() {
    log_step "Final Validation"
    
    log_info "Performing final validation checks..."
    
    # Check deployment directory exists and is writable
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "test -w $PI_DEPLOY_PATH" >/dev/null 2>&1; then
        log_success "Deployment directory is writable"
    else
        log_error "Deployment directory is not writable"
        return 1
    fi
    
    # Check environment file exists
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "test -f $PI_DEPLOY_PATH/configs/lucid-pi.env" >/dev/null 2>&1; then
        log_success "Environment configuration file exists"
    else
        log_error "Environment configuration file not found"
        return 1
    fi
    
    # Check Docker is still running
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPath=~/.ssh/control-%r@%h:%p -o ControlPersist=60s "$PI_HOST" "docker info" >/dev/null 2>&1; then
        log_success "Docker is still running"
    else
        log_error "Docker is not running"
        return 1
    fi
    
    log_success "All final validation checks passed"
}

# Main execution function
main() {
    log_section "LUCID Pre-Phase 1 Pi Deployment Setup"
    log_info "This script ensures all pre-build requirements are complete on the Pi side"
    log_info "Target Pi: $PI_HOST"
    log_info "Deployment Path: $PI_DEPLOY_PATH"
    log_info "Docker Hub Namespace: $PI_DOCKER_HUB_NAMESPACE"
    echo
    
    # Run all validation and setup steps
    test_ssh_connection || exit 1
    test_pi_system
    test_disk_space
    test_docker_setup || exit 1
    test_docker_hub_access || exit 1
    setup_pi_directories || exit 1
    test_docker_networking || exit 1
    test_docker_volumes || exit 1
    test_pi_performance
    test_docker_resources
    cleanup_existing_lucid
    generate_pi_environment
    transfer_environment_to_pi || exit 1
    final_validation || exit 1
    
    echo
    log_section "Pre-Phase 1 Setup Complete"
    log_success "✅ All pre-build requirements are now complete on the Pi side"
    log_success "✅ Pi is ready for Phase 1 deployment"
    log_info "Next steps:"
    log_info "  1. Run Phase 1 build scripts on Windows build host"
    log_info "  2. Deploy Phase 1 services using deploy-phase1-pi.sh"
    log_info "  3. Run Phase 1 integration tests"
    echo
    log_info "Pi deployment directory: $PI_DEPLOY_PATH"
    log_info "Environment file: $PI_DEPLOY_PATH/configs/lucid-pi.env"
    log_info "Ready for Phase 1 Foundation Services deployment"
}

# Run main function
main "$@"
