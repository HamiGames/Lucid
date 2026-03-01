#!/bin/bash
# LUCID RDP Services Container Smoke Test Script
# Step 21-22: RDP Services Containers Smoke Testing
# Tests all RDP containers for basic functionality and health

set -euo pipefail

# Configuration
REGISTRY="pickme"
NAMESPACE="lucid"
PLATFORM="linux/arm64"
VERSION="latest"

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

# Test function for individual container
test_container() {
    local service_name=$1
    local image_name=$2
    local port=$3
    local health_endpoint=$4
    
    log_info "Testing ${service_name} container..."
    
    # Pull the image
    log_info "Pulling ${image_name}..."
    if ! docker pull ${image_name}; then
        log_error "Failed to pull ${image_name}"
        return 1
    fi
    
    # Start container in background
    log_info "Starting ${service_name} container..."
    local container_id
    container_id=$(docker run -d \
        --name "test-${service_name}" \
        --rm \
        -p ${port}:${port} \
        -e LOG_LEVEL=INFO \
        -e DEBUG=false \
        ${image_name})
    
    if [ -z "${container_id}" ]; then
        log_error "Failed to start ${service_name} container"
        return 1
    fi
    
    # Wait for container to be ready
    log_info "Waiting for ${service_name} to be ready..."
    sleep 10
    
    # Check container status
    if ! docker ps | grep -q "test-${service_name}"; then
        log_error "${service_name} container is not running"
        docker logs "test-${service_name}" || true
        return 1
    fi
    
    # Test health endpoint
    log_info "Testing health endpoint for ${service_name}..."
    local health_url="http://localhost:${port}${health_endpoint}"
    
    # Wait for health endpoint to be available
    local max_attempts=30
    local attempt=0
    
    while [ ${attempt} -lt ${max_attempts} ]; do
        if curl -s -f "${health_url}" > /dev/null 2>&1; then
            log_success "${service_name} health endpoint is responding"
            break
        fi
        
        attempt=$((attempt + 1))
        log_info "Attempt ${attempt}/${max_attempts}: Waiting for health endpoint..."
        sleep 2
    done
    
    if [ ${attempt} -eq ${max_attempts} ]; then
        log_error "${service_name} health endpoint is not responding"
        docker logs "test-${service_name}" || true
        return 1
    fi
    
    # Test basic API functionality
    log_info "Testing basic API functionality for ${service_name}..."
    
    case ${service_name} in
        "rdp-server-manager")
            # Test server list endpoint
            if curl -s -f "http://localhost:${port}/servers" > /dev/null 2>&1; then
                log_success "${service_name} API endpoints are responding"
            else
                log_warning "${service_name} API endpoints may not be fully functional"
            fi
            ;;
        "xrdp-integration")
            # Test services list endpoint
            if curl -s -f "http://localhost:${port}/services" > /dev/null 2>&1; then
                log_success "${service_name} API endpoints are responding"
            else
                log_warning "${service_name} API endpoints may not be fully functional"
            fi
            ;;
        "session-controller")
            # Test sessions endpoint
            if curl -s -f "http://localhost:${port}/api/v1/sessions" > /dev/null 2>&1; then
                log_success "${service_name} API endpoints are responding"
            else
                log_warning "${service_name} API endpoints may not be fully functional"
            fi
            ;;
        "resource-monitor")
            # Test monitoring summary endpoint
            if curl -s -f "http://localhost:${port}/api/v1/monitoring/summary" > /dev/null 2>&1; then
                log_success "${service_name} API endpoints are responding"
            else
                log_warning "${service_name} API endpoints may not be fully functional"
            fi
            ;;
    esac
    
    # Stop container
    log_info "Stopping ${service_name} container..."
    docker stop "test-${service_name}" > /dev/null 2>&1 || true
    
    log_success "${service_name} container test passed!"
    return 0
}

# Verify test environment
verify_test_env() {
    log_info "Verifying test environment..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running"
        exit 1
    fi
    
    # Check if curl is available
    if ! command -v curl > /dev/null 2>&1; then
        log_error "curl is required for testing but not installed"
        exit 1
    fi
    
    log_success "Test environment verified"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test containers..."
    
    # Stop and remove any remaining test containers
    docker ps -a --filter "name=test-" --format "{{.Names}}" | xargs -r docker stop
    docker ps -a --filter "name=test-" --format "{{.Names}}" | xargs -r docker rm -f
    
    log_success "Cleanup completed"
}

# Main test process
main() {
    log_info "Starting RDP Services Container Smoke Tests"
    log_info "Registry: ${REGISTRY}/${NAMESPACE}"
    log_info "Platform: ${PLATFORM}"
    
    # Verify environment
    verify_test_env
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Test results tracking
    local passed=0
    local failed=0
    local total=0
    
    # Test RDP Server Manager (Port 8081)
    total=$((total + 1))
    if test_container \
        "rdp-server-manager" \
        "${REGISTRY}/${NAMESPACE}-rdp-server-manager:${VERSION}-arm64" \
        "8081" \
        "/health"; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
    fi
    
    # Test XRDP Integration (Port 3389)
    total=$((total + 1))
    if test_container \
        "xrdp-integration" \
        "${REGISTRY}/${NAMESPACE}-xrdp-integration:${VERSION}-arm64" \
        "3389" \
        "/health"; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
    fi
    
    # Test Session Controller (Port 8082)
    total=$((total + 1))
    if test_container \
        "session-controller" \
        "${REGISTRY}/${NAMESPACE}-session-controller:${VERSION}-arm64" \
        "8082" \
        "/health"; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
    fi
    
    # Test Resource Monitor (Port 8090)
    total=$((total + 1))
    if test_container \
        "resource-monitor" \
        "${REGISTRY}/${NAMESPACE}-resource-monitor:${VERSION}-arm64" \
        "8090" \
        "/health"; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
    fi
    
    # Display test results
    log_info "Smoke Test Results:"
    echo "  Total Tests: ${total}"
    echo "  Passed: ${passed}"
    echo "  Failed: ${failed}"
    
    if [ ${failed} -eq 0 ]; then
        log_success "All RDP Services container smoke tests passed!"
        exit 0
    else
        log_error "Some RDP Services container smoke tests failed!"
        exit 1
    fi
}

# Run main function
main "$@"
