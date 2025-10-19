#!/bin/bash
# Build Environment Validation Script
# Validates Windows 11 build host and Raspberry Pi target before starting builds
# Based on lucid-container-build-plan.plan.md Step 3

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATION_LOG="$PROJECT_ROOT/build-environment-validation.log"
VALIDATION_RESULTS=()

# Pi connection configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_SSH_PORT="22"
PI_SSH_KEY_PATH="$HOME/.ssh/id_rsa"

# Initialize validation
init_validation() {
    echo -e "${BLUE}=== Build Environment Validation ===${NC}"
    echo "Project Root: $PROJECT_ROOT"
    echo "Validation Log: $VALIDATION_LOG"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
    
    # Clear previous validation log
    > "$VALIDATION_LOG"
}

# Log validation result
log_result() {
    local check="$1"
    local status="$2"
    local message="$3"
    local details="$4"
    
    VALIDATION_RESULTS+=("{\"check\":\"$check\",\"status\":\"$status\",\"message\":\"$message\",\"details\":\"$details\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}")
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $check: $message"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $check: $message"
    else
        echo -e "${YELLOW}⚠${NC} $check: $message"
    fi
    
    # Log to file
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - $check - $status - $message" >> "$VALIDATION_LOG"
}

# Check Docker Desktop on Windows 11
check_docker_desktop() {
    echo -e "${BLUE}=== Docker Desktop Validation ===${NC}"
    
    # Check if Docker is running
    if docker info >/dev/null 2>&1; then
        log_result "docker-running" "PASS" "Docker daemon is running"
        
        # Check Docker version
        local docker_version=$(docker --version 2>/dev/null | cut -d' ' -f3 | cut -d',' -f1)
        if [ -n "$docker_version" ]; then
            log_result "docker-version" "PASS" "Docker version: $docker_version"
        else
            log_result "docker-version" "FAIL" "Unable to determine Docker version"
        fi
        
        # Check Docker Compose version
        if docker compose version >/dev/null 2>&1; then
            local compose_version=$(docker compose version --short 2>/dev/null)
            log_result "docker-compose-version" "PASS" "Docker Compose version: $compose_version"
        else
            log_result "docker-compose-version" "FAIL" "Docker Compose not available"
        fi
        
        # Check BuildKit support
        if docker buildx version >/dev/null 2>&1; then
            log_result "docker-buildkit" "PASS" "Docker BuildKit is available"
        else
            log_result "docker-buildkit" "FAIL" "Docker BuildKit not available"
        fi
        
        # Check if running on Windows
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
            log_result "docker-windows" "PASS" "Running on Windows platform"
        else
            log_result "docker-windows" "WARN" "Not running on Windows platform (OSTYPE: $OSTYPE)"
        fi
        
    else
        log_result "docker-running" "FAIL" "Docker daemon is not running"
        log_result "docker-version" "FAIL" "Cannot check Docker version - daemon not running"
        log_result "docker-compose-version" "FAIL" "Cannot check Docker Compose - daemon not running"
        log_result "docker-buildkit" "FAIL" "Cannot check BuildKit - daemon not running"
    fi
    
    echo ""
}

# Check SSH connection to Pi
check_pi_ssh_connection() {
    echo -e "${BLUE}=== Raspberry Pi SSH Connection Validation ===${NC}"
    
    # Check if SSH key exists
    if [ -f "$PI_SSH_KEY_PATH" ]; then
        log_result "ssh-key-exists" "PASS" "SSH key found at $PI_SSH_KEY_PATH"
        
        # Set correct permissions on SSH key
        chmod 600 "$PI_SSH_KEY_PATH" 2>/dev/null || true
        
    else
        log_result "ssh-key-exists" "FAIL" "SSH key not found at $PI_SSH_KEY_PATH"
    fi
    
    # Test SSH connection to Pi
    echo "Testing SSH connection to $PI_USER@$PI_HOST..."
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_result "ssh-connection" "PASS" "SSH connection to Pi successful"
        
        # Check Pi system information
        local pi_info=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "uname -a" 2>/dev/null)
        if [ -n "$pi_info" ]; then
            log_result "pi-system-info" "PASS" "Pi system: $pi_info"
        else
            log_result "pi-system-info" "FAIL" "Unable to get Pi system information"
        fi
        
    else
        log_result "ssh-connection" "FAIL" "SSH connection to Pi failed"
        log_result "pi-system-info" "FAIL" "Cannot get Pi system information - SSH failed"
    fi
    
    echo ""
}

# Check Pi disk space
check_pi_disk_space() {
    echo -e "${BLUE}=== Raspberry Pi Disk Space Validation ===${NC}"
    
    echo "Checking Pi disk space..."
    local disk_info=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "df -h /" 2>/dev/null)
    
    if [ -n "$disk_info" ]; then
        log_result "pi-disk-info" "PASS" "Pi disk information retrieved"
        
        # Extract available space (in GB)
        local available_space=$(echo "$disk_info" | tail -1 | awk '{print $4}' | sed 's/G//')
        if [ -n "$available_space" ] && [ "$available_space" -gt 20 ]; then
            log_result "pi-disk-space" "PASS" "Pi has $available_space GB free space (minimum 20GB required)"
        else
            log_result "pi-disk-space" "FAIL" "Pi has insufficient free space: $available_space GB (minimum 20GB required)"
        fi
        
    else
        log_result "pi-disk-info" "FAIL" "Unable to get Pi disk information"
        log_result "pi-disk-space" "FAIL" "Cannot check Pi disk space"
    fi
    
    echo ""
}

# Check Pi architecture
check_pi_architecture() {
    echo -e "${BLUE}=== Raspberry Pi Architecture Validation ===${NC}"
    
    echo "Checking Pi architecture..."
    local arch_info=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "uname -m" 2>/dev/null)
    
    if [ -n "$arch_info" ]; then
        if [[ "$arch_info" == "aarch64" || "$arch_info" == "arm64" ]]; then
            log_result "pi-architecture" "PASS" "Pi architecture: $arch_info (ARM64 compatible)"
        else
            log_result "pi-architecture" "FAIL" "Pi architecture: $arch_info (ARM64 required)"
        fi
        
        # Check if it's a Raspberry Pi
        local pi_model=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "cat /proc/device-tree/model 2>/dev/null || echo 'Unknown'" 2>/dev/null)
        if [ -n "$pi_model" ] && [[ "$pi_model" == *"Raspberry Pi"* ]]; then
            log_result "pi-model" "PASS" "Pi model: $pi_model"
        else
            log_result "pi-model" "WARN" "Pi model: $pi_model (not confirmed as Raspberry Pi)"
        fi
        
    else
        log_result "pi-architecture" "FAIL" "Unable to get Pi architecture information"
        log_result "pi-model" "FAIL" "Cannot check Pi model"
    fi
    
    echo ""
}

# Check network connectivity
check_network_connectivity() {
    echo -e "${BLUE}=== Network Connectivity Validation ===${NC}"
    
    # Check if Pi is reachable via ping
    if ping -c 1 -W 5 "$PI_HOST" >/dev/null 2>&1; then
        log_result "pi-ping" "PASS" "Pi is reachable via ping"
    else
        log_result "pi-ping" "FAIL" "Pi is not reachable via ping"
    fi
    
    # Check if SSH port is open
    if nc -z -w 5 "$PI_HOST" "$PI_SSH_PORT" 2>/dev/null; then
        log_result "pi-ssh-port" "PASS" "SSH port $PI_SSH_PORT is open on Pi"
    else
        log_result "pi-ssh-port" "FAIL" "SSH port $PI_SSH_PORT is not open on Pi"
    fi
    
    # Check internet connectivity from build host
    if ping -c 1 -W 5 "8.8.8.8" >/dev/null 2>&1; then
        log_result "build-host-internet" "PASS" "Build host has internet connectivity"
    else
        log_result "build-host-internet" "FAIL" "Build host has no internet connectivity"
    fi
    
    # Check internet connectivity from Pi
    local pi_internet=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1 && echo 'OK' || echo 'FAIL'" 2>/dev/null)
    if [ "$pi_internet" = "OK" ]; then
        log_result "pi-internet" "PASS" "Pi has internet connectivity"
    else
        log_result "pi-internet" "FAIL" "Pi has no internet connectivity"
    fi
    
    echo ""
}

# Check Docker daemon on Pi
check_pi_docker() {
    echo -e "${BLUE}=== Raspberry Pi Docker Validation ===${NC}"
    
    echo "Checking Docker on Pi..."
    
    # Check if Docker is installed on Pi
    local docker_installed=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "which docker >/dev/null 2>&1 && echo 'OK' || echo 'FAIL'" 2>/dev/null)
    if [ "$docker_installed" = "OK" ]; then
        log_result "pi-docker-installed" "PASS" "Docker is installed on Pi"
        
        # Check if Docker daemon is running
        local docker_running=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker info >/dev/null 2>&1 && echo 'OK' || echo 'FAIL'" 2>/dev/null)
        if [ "$docker_running" = "OK" ]; then
            log_result "pi-docker-running" "PASS" "Docker daemon is running on Pi"
            
            # Check Docker version on Pi
            local pi_docker_version=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker --version 2>/dev/null | cut -d' ' -f3 | cut -d',' -f1" 2>/dev/null)
            if [ -n "$pi_docker_version" ]; then
                log_result "pi-docker-version" "PASS" "Pi Docker version: $pi_docker_version"
            else
                log_result "pi-docker-version" "FAIL" "Unable to determine Pi Docker version"
            fi
            
            # Check Docker Compose on Pi
            local pi_compose=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker compose version >/dev/null 2>&1 && echo 'OK' || echo 'FAIL'" 2>/dev/null)
            if [ "$pi_compose" = "OK" ]; then
                log_result "pi-docker-compose" "PASS" "Docker Compose is available on Pi"
            else
                log_result "pi-docker-compose" "FAIL" "Docker Compose not available on Pi"
            fi
            
        else
            log_result "pi-docker-running" "FAIL" "Docker daemon is not running on Pi"
            log_result "pi-docker-version" "FAIL" "Cannot check Pi Docker version - daemon not running"
            log_result "pi-docker-compose" "FAIL" "Cannot check Pi Docker Compose - daemon not running"
        fi
        
    else
        log_result "pi-docker-installed" "FAIL" "Docker is not installed on Pi"
        log_result "pi-docker-running" "FAIL" "Cannot check Docker daemon - Docker not installed"
        log_result "pi-docker-version" "FAIL" "Cannot check Pi Docker version - Docker not installed"
        log_result "pi-docker-compose" "FAIL" "Cannot check Pi Docker Compose - Docker not installed"
    fi
    
    echo ""
}

# Check required base images
check_base_images() {
    echo -e "${BLUE}=== Base Images Validation ===${NC}"
    
    # Check if distroless base images are available
    local distroless_python=$(docker image inspect gcr.io/distroless/python3-debian12:latest >/dev/null 2>&1 && echo "OK" || echo "FAIL")
    if [ "$distroless_python" = "OK" ]; then
        log_result "base-image-python" "PASS" "Distroless Python base image available"
    else
        log_result "base-image-python" "FAIL" "Distroless Python base image not available"
    fi
    
    local distroless_java=$(docker image inspect gcr.io/distroless/java17-debian12:latest >/dev/null 2>&1 && echo "OK" || echo "FAIL")
    if [ "$distroless_java" = "OK" ]; then
        log_result "base-image-java" "PASS" "Distroless Java base image available"
    else
        log_result "base-image-java" "FAIL" "Distroless Java base image not available"
    fi
    
    local distroless_base=$(docker image inspect gcr.io/distroless/base-debian12:latest >/dev/null 2>&1 && [[ "$distroless_base" == *"gcr.io/distroless/base-debian12:latest"* ]] && echo "OK" || echo "FAIL")
    if [ "$distroless_base" = "OK" ]; then
        log_result "base-image-base" "PASS" "Distroless base image available"
    else
        log_result "base-image-base" "FAIL" "Distroless base image not available"
    fi
    
    echo ""
}

# Check project structure
check_project_structure() {
    echo -e "${BLUE}=== Project Structure Validation ===${NC}"
    
    # Check required directories
    local required_dirs=(
        "infrastructure/containers/base"
        "infrastructure/containers/database"
        "infrastructure/containers/auth"
        "configs/environment"
        "scripts/validation"
        "scripts/config"
        "scripts/deployment"
        "auth"
        "database"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            log_result "project-dir-$dir" "PASS" "Directory exists: $dir"
        else
            log_result "project-dir-$dir" "FAIL" "Directory missing: $dir"
        fi
    done
    
    # Check required files
    local required_files=(
        "infrastructure/containers/base/Dockerfile.python-base"
        "infrastructure/containers/base/Dockerfile.java-base"
        "infrastructure/containers/database/Dockerfile.mongodb"
        "infrastructure/containers/database/Dockerfile.redis"
        "infrastructure/containers/auth/Dockerfile.auth-service"
        "auth/main.py"
        "database/init_collections.js"
    )
    
    for file in "${required_files[@]}"; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            log_result "project-file-$file" "PASS" "File exists: $file"
        else
            log_result "project-file-$file" "FAIL" "File missing: $file"
        fi
    done
    
    echo ""
}

# Generate validation report
generate_report() {
    echo -e "${BLUE}=== Generating Validation Report ===${NC}"
    
    local total_checks=${#VALIDATION_RESULTS[@]}
    local passed_checks=0
    local failed_checks=0
    local warning_checks=0
    
    for result in "${VALIDATION_RESULTS[@]}"; do
        local status=$(echo "$result" | jq -r '.status')
        case "$status" in
            "PASS") ((passed_checks++)) ;;
            "FAIL") ((failed_checks++)) ;;
            "WARN") ((warning_checks++)) ;;
        esac
    done
    
    echo ""
    echo -e "${BLUE}=== Validation Summary ===${NC}"
    echo "Total Checks: $total_checks"
    echo -e "Passed: ${GREEN}$passed_checks${NC}"
    echo -e "Failed: ${RED}$failed_checks${NC}"
    echo -e "Warnings: ${YELLOW}$warning_checks${NC}"
    echo -e "Success Rate: $(( (passed_checks * 100) / total_checks ))%"
    
    if [ $failed_checks -eq 0 ]; then
        echo -e "${GREEN}✓ Build environment validation completed successfully!${NC}"
        echo -e "${GREEN}✓ Ready to proceed with Phase 1 Foundation Services Build${NC}"
        return 0
    else
        echo -e "${RED}✗ Build environment validation failed with $failed_checks errors${NC}"
        echo -e "${RED}✗ Please fix the issues before proceeding with Phase 1 build${NC}"
        return 1
    fi
}

# Main execution
main() {
    init_validation
    
    check_docker_desktop
    check_pi_ssh_connection
    check_pi_disk_space
    check_pi_architecture
    check_network_connectivity
    check_pi_docker
    check_base_images
    check_project_structure
    
    generate_report
}

# Run main function
main "$@"