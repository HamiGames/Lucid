#!/bin/bash
# Test Pi Connection Script
# Tests basic SSH connectivity and permissions

set -euo pipefail

# Configuration
PI_HOST="pickme@192.168.0.75"
PI_PORT="22"
PI_DEPLOY_PATH="/opt/lucid/production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Test SSH connection
test_ssh_connection() {
    log_info "Testing SSH connection to $PI_HOST..."
    
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_success "SSH connection successful"
        return 0
    else
        log_error "SSH connection failed"
        return 1
    fi
}

# Test Pi architecture
test_pi_architecture() {
    log_info "Testing Pi architecture..."
    
    local pi_arch=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "uname -m" 2>/dev/null)
    log_info "Pi architecture: $pi_arch"
    
    if [[ "$pi_arch" == "aarch64" ]]; then
        log_success "Architecture is correct (aarch64)"
    else
        log_warning "Architecture is $pi_arch, expected aarch64"
    fi
}

# Test disk space
test_disk_space() {
    log_info "Testing disk space..."
    
    local disk_space=$(ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "df -h / | awk 'NR==2{print \$4}' | sed 's/G.*//'" 2>/dev/null)
    disk_space=$(echo "$disk_space" | tr -d '[:alpha:]' | head -1)
    
    log_info "Available disk space: ${disk_space}GB"
    
    if [[ "$disk_space" =~ ^[0-9]+$ ]] && [[ "$disk_space" -ge 20 ]]; then
        log_success "Sufficient disk space available"
    else
        log_warning "Low disk space: ${disk_space}GB (recommended: 20GB+)"
    fi
}

# Test Docker
test_docker() {
    log_info "Testing Docker..."
    
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "docker info" >/dev/null 2>&1; then
        log_success "Docker is running"
    else
        log_error "Docker is not running or not accessible"
        return 1
    fi
}

# Test directory permissions
test_directory_permissions() {
    log_info "Testing directory permissions..."
    
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "mkdir -p /tmp/lucid-test && rmdir /tmp/lucid-test" >/dev/null 2>&1; then
        log_success "Basic directory operations work"
    else
        log_warning "Basic directory operations failed"
    fi
    
    # Test deployment directory
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "mkdir -p $PI_DEPLOY_PATH" >/dev/null 2>&1; then
        log_success "Can create deployment directory"
        ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "rmdir $PI_DEPLOY_PATH" >/dev/null 2>&1 || true
    else
        log_warning "Cannot create deployment directory. You may need to run:"
        log_info "  sudo mkdir -p $PI_DEPLOY_PATH"
        log_info "  sudo chown -R pickme:pickme $PI_DEPLOY_PATH"
    fi
}

# Test Docker network
test_docker_network() {
    log_info "Testing Docker network operations..."
    
    if ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PI_HOST" "docker network ls" >/dev/null 2>&1; then
        log_success "Docker network operations work"
    else
        log_error "Docker network operations failed"
        return 1
    fi
}

# Main test function
main() {
    log_info "Starting Pi connection tests..."
    log_info "Target: $PI_HOST"
    log_info "Port: $PI_PORT"
    log_info "Deploy Path: $PI_DEPLOY_PATH"
    echo
    
    # Run all tests
    test_ssh_connection || exit 1
    test_pi_architecture
    test_disk_space
    test_docker || exit 1
    test_directory_permissions
    test_docker_network || exit 1
    
    echo
    log_success "All basic tests completed!"
    log_info "You can now run the deployment script: ./scripts/deploy-phase1-pi.sh"
}

# Run main function
main "$@"
