#!/bin/bash
# scripts/validation/validate-phase1-complete.sh
# Complete Phase 1 Foundation Services validation
# Validates all Phase 1 services, networks, distroless infrastructure, and compliance

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PI_SSH_KEY_PATH="$HOME/.ssh/id_rsa"
PI_DEPLOY_DIR="/mnt/myssd/Lucid/Lucid"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Service configuration
FOUNDATION_SERVICES=("lucid-mongodb" "lucid-redis" "lucid-elasticsearch" "lucid-auth-service")
DISTROLESS_SERVICES=("lucid-base" "lucid-minimal-base" "lucid-arm64-base" "distroless-runtime" "minimal-runtime" "arm64-runtime")
REQUIRED_NETWORKS=("lucid-pi-network" "lucid-tron-isolated" "lucid-gui-network" "lucid-distroless-production" "lucid-distroless-dev" "lucid-multi-stage-network")

# Validation results
VALIDATION_LOG="$PROJECT_ROOT/phase1-validation.log"
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Initialize validation
init_validation() {
    echo -e "${BLUE}=== Phase 1 Complete Validation ===${NC}"
    echo "Target Pi: $PI_USER@$PI_HOST"
    echo "Deploy Directory: $PI_DEPLOY_DIR"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
    
    # Clear previous validation log
    > "$VALIDATION_LOG"
    
    # Log validation start
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Phase 1 validation started" >> "$VALIDATION_LOG"
}

# Log validation result
log_result() {
    local check_name="$1"
    local status="$2"
    local message="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $check_name: $message"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $check_name: $message"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    else
        echo -e "${YELLOW}⚠${NC} $check_name: $message"
    fi
    
    # Log to file
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - $check_name - $status - $message" >> "$VALIDATION_LOG"
}

# Test SSH connection to Pi
test_ssh_connection() {
    echo -e "${BLUE}=== Testing SSH Connection ===${NC}"
    
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_result "ssh-connection" "PASS" "SSH connection to Pi established"
        return 0
    else
        log_result "ssh-connection" "FAIL" "SSH connection to Pi failed"
        return 1
    fi
}

# Verify Docker networks
verify_docker_networks() {
    echo -e "${BLUE}=== Verifying Docker Networks ===${NC}"
    
    local all_networks_exist=true
    
    for network in "${REQUIRED_NETWORKS[@]}"; do
        if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker network ls | grep -q '$network'" >/dev/null 2>&1; then
            log_result "network-$network" "PASS" "Network $network exists"
        else
            log_result "network-$network" "FAIL" "Network $network not found"
            all_networks_exist=false
        fi
    done
    
    if [ "$all_networks_exist" = true ]; then
        log_result "all-networks" "PASS" "All 6 required networks exist"
        return 0
    else
        log_result "all-networks" "FAIL" "Some required networks are missing"
        return 1
    fi
}

# Verify data directories
verify_data_directories() {
    echo -e "${BLUE}=== Verifying Data Directories ===${NC}"
    
    local required_dirs=(
        "/mnt/myssd/Lucid/Lucid/data/mongodb"
        "/mnt/myssd/Lucid/Lucid/data/redis"
        "/mnt/myssd/Lucid/Lucid/data/elasticsearch"
        "/mnt/myssd/Lucid/Lucid/data/auth"
        "/mnt/myssd/Lucid/Lucid/logs/auth"
        "/mnt/myssd/Lucid/Lucid/logs/mongodb"
        "/mnt/myssd/Lucid/Lucid/logs/redis"
        "/mnt/myssd/Lucid/Lucid/logs/elasticsearch"
    )
    
    local all_dirs_exist=true
    
    for dir in "${required_dirs[@]}"; do
        if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "test -d '$dir'" >/dev/null 2>&1; then
            log_result "directory-$(basename "$dir")" "PASS" "Directory $dir exists"
        else
            log_result "directory-$(basename "$dir")" "FAIL" "Directory $dir not found"
            all_dirs_exist=false
        fi
    done
    
    if [ "$all_dirs_exist" = true ]; then
        log_result "all-directories" "PASS" "All required directories exist"
        return 0
    else
        log_result "all-directories" "FAIL" "Some required directories are missing"
        return 1
    fi
}

# Verify environment files
verify_environment_files() {
    echo -e "${BLUE}=== Verifying Environment Files ===${NC}"
    
    local env_file="$PI_DEPLOY_DIR/configs/environment/.env.foundation"
    
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "test -f '$env_file'" >/dev/null 2>&1; then
        log_result "env-file" "PASS" "Environment file exists"
        
        # Check for required environment variables
        local required_vars=("MONGODB_PASSWORD" "JWT_SECRET_KEY" "REDIS_PASSWORD" "ELASTICSEARCH_PASSWORD")
        local all_vars_exist=true
        
        for var in "${required_vars[@]}"; do
            if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "grep -q '^${var}=' '$env_file'" >/dev/null 2>&1; then
                log_result "env-var-$var" "PASS" "Environment variable $var is set"
            else
                log_result "env-var-$var" "FAIL" "Environment variable $var not found"
                all_vars_exist=false
            fi
        done
        
        if [ "$all_vars_exist" = true ]; then
            log_result "all-env-vars" "PASS" "All required environment variables are set"
        else
            log_result "all-env-vars" "FAIL" "Some required environment variables are missing"
        fi
    else
        log_result "env-file" "FAIL" "Environment file not found"
        return 1
    fi
}

# Verify Docker images
verify_docker_images() {
    echo -e "${BLUE}=== Verifying Docker Images ===${NC}"
    
    local required_images=(
        "pickme/lucid-mongodb:latest-arm64"
        "pickme/lucid-redis:latest-arm64"
        "pickme/lucid-elasticsearch:latest-arm64"
        "pickme/lucid-auth-service:latest-arm64"
        "pickme/lucid-base:latest-arm64"
    )
    
    local all_images_exist=true
    
    for image in "${required_images[@]}"; do
        if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker images | grep -q '$image'" >/dev/null 2>&1; then
            log_result "image-$(echo "$image" | cut -d'/' -f2 | cut -d':' -f1)" "PASS" "Image $image exists"
        else
            log_result "image-$(echo "$image" | cut -d'/' -f2 | cut -d':' -f1)" "FAIL" "Image $image not found"
            all_images_exist=false
        fi
    done
    
    if [ "$all_images_exist" = true ]; then
        log_result "all-images" "PASS" "All required images are available"
        return 0
    else
        log_result "all-images" "FAIL" "Some required images are missing"
        return 1
    fi
}

# Verify distroless infrastructure
verify_distroless_infrastructure() {
    echo -e "${BLUE}=== Verifying Distroless Infrastructure ===${NC}"
    
    local all_distroless_running=true
    
    for service in "${DISTROLESS_SERVICES[@]}"; do
        if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker ps | grep -q '$service'" >/dev/null 2>&1; then
            log_result "distroless-$service" "PASS" "Distroless service $service is running"
        else
            log_result "distroless-$service" "FAIL" "Distroless service $service is not running"
            all_distroless_running=false
        fi
    done
    
    if [ "$all_distroless_running" = true ]; then
        log_result "all-distroless" "PASS" "All distroless infrastructure services are running"
        return 0
    else
        log_result "all-distroless" "FAIL" "Some distroless infrastructure services are not running"
        return 1
    fi
}

# Verify foundation services
verify_foundation_services() {
    echo -e "${BLUE}=== Verifying Foundation Services ===${NC}"
    
    local all_services_running=true
    
    for service in "${FOUNDATION_SERVICES[@]}"; do
        if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker ps | grep -q '$service'" >/dev/null 2>&1; then
            log_result "service-$service" "PASS" "Service $service is running"
        else
            log_result "service-$service" "FAIL" "Service $service is not running"
            all_services_running=false
        fi
    done
    
    if [ "$all_services_running" = true ]; then
        log_result "all-foundation-services" "PASS" "All foundation services are running"
        return 0
    else
        log_result "all-foundation-services" "FAIL" "Some foundation services are not running"
        return 1
    fi
}

# Verify service health
verify_service_health() {
    echo -e "${BLUE}=== Verifying Service Health ===${NC}"
    
    # Test MongoDB
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker exec lucid-mongodb mongosh --eval 'db.adminCommand(\"ping\")'" >/dev/null 2>&1; then
        log_result "mongodb-health" "PASS" "MongoDB is healthy and responding"
    else
        log_result "mongodb-health" "FAIL" "MongoDB health check failed"
    fi
    
    # Test Redis
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker exec lucid-redis redis-cli ping" >/dev/null 2>&1; then
        log_result "redis-health" "PASS" "Redis is healthy and responding"
    else
        log_result "redis-health" "FAIL" "Redis health check failed"
    fi
    
    # Test Elasticsearch
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "curl -f http://localhost:9200/_cluster/health" >/dev/null 2>&1; then
        log_result "elasticsearch-health" "PASS" "Elasticsearch is healthy and responding"
    else
        log_result "elasticsearch-health" "FAIL" "Elasticsearch health check failed"
    fi
    
    # Test Auth Service
    if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "curl -f http://localhost:8089/health" >/dev/null 2>&1; then
        log_result "auth-service-health" "PASS" "Auth Service is healthy and responding"
    else
        log_result "auth-service-health" "FAIL" "Auth Service health check failed"
    fi
}

# Verify distroless compliance
verify_distroless_compliance() {
    echo -e "${BLUE}=== Verifying Distroless Compliance ===${NC}"
    
    local all_compliant=true
    
    for service in "${FOUNDATION_SERVICES[@]}"; do
        # Check user ID (should be 65532:65532)
        local user_id=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker exec $service id 2>/dev/null" 2>/dev/null || echo "unknown")
        
        if [[ "$user_id" == *"65532"* ]]; then
            log_result "distroless-user-$service" "PASS" "Service $service running as user 65532"
        else
            log_result "distroless-user-$service" "FAIL" "Service $service not running as user 65532 (got: $user_id)"
            all_compliant=false
        fi
        
        # Check no shell access (should fail)
        local shell_test=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker exec $service sh -c 'echo test' 2>&1" 2>/dev/null || echo "shell-failed")
        
        if [[ "$shell_test" == *"executable file not found"* ]]; then
            log_result "distroless-shell-$service" "PASS" "Service $service has no shell access (distroless)"
        else
            log_result "distroless-shell-$service" "FAIL" "Service $service has shell access (not distroless)"
            all_compliant=false
        fi
    done
    
    if [ "$all_compliant" = true ]; then
        log_result "all-distroless-compliance" "PASS" "All services are distroless compliant"
        return 0
    else
        log_result "all-distroless-compliance" "FAIL" "Some services are not distroless compliant"
        return 1
    fi
}

# Verify volume mounts
verify_volume_mounts() {
    echo -e "${BLUE}=== Verifying Volume Mounts ===${NC}"
    
    local all_volumes_mounted=true
    
    for service in "${FOUNDATION_SERVICES[@]}"; do
        local mount_check=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker inspect $service | grep -A 10 'Mounts'" 2>/dev/null || echo "no-mounts")
        
        if [[ "$mount_check" == *"/mnt/myssd/Lucid/Lucid"* ]]; then
            log_result "volume-mounts-$service" "PASS" "Service $service has correct volume mounts"
        else
            log_result "volume-mounts-$service" "FAIL" "Service $service volume mounts not found"
            all_volumes_mounted=false
        fi
    done
    
    if [ "$all_volumes_mounted" = true ]; then
        log_result "all-volume-mounts" "PASS" "All services have correct volume mounts"
        return 0
    else
        log_result "all-volume-mounts" "FAIL" "Some services have incorrect volume mounts"
        return 1
    fi
}

# Verify network connectivity
verify_network_connectivity() {
    echo -e "${BLUE}=== Verifying Network Connectivity ===${NC}"
    
    # Test connectivity between services
    local connectivity_tests=(
        "lucid-mongodb:27017"
        "lucid-redis:6379"
        "lucid-elasticsearch:9200"
        "lucid-auth-service:8089"
    )
    
    local all_connectivity_ok=true
    
    for test in "${connectivity_tests[@]}"; do
        local service=$(echo "$test" | cut -d':' -f1)
        local port=$(echo "$test" | cut -d':' -f2)
        
        if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i "$PI_SSH_KEY_PATH" "$PI_USER@$PI_HOST" "docker exec $service python3 -c 'import socket; socket.create_connection((\"localhost\", $port), timeout=5)'" >/dev/null 2>&1; then
            log_result "connectivity-$service" "PASS" "Service $service can connect to port $port"
        else
            log_result "connectivity-$service" "FAIL" "Service $service cannot connect to port $port"
            all_connectivity_ok=false
        fi
    done
    
    if [ "$all_connectivity_ok" = true ]; then
        log_result "all-network-connectivity" "PASS" "All network connectivity tests passed"
        return 0
    else
        log_result "all-network-connectivity" "FAIL" "Some network connectivity tests failed"
        return 1
    fi
}

# Generate validation summary
generate_validation_summary() {
    echo -e "${BLUE}=== Validation Summary ===${NC}"
    
    local summary_file="$PROJECT_ROOT/phase1-validation-summary.json"
    
    cat > "$summary_file" << EOF
{
  "validation_summary": {
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "phase": "Phase 1 Foundation Services",
    "target_pi": "$PI_USER@$PI_HOST",
    "deploy_directory": "$PI_DEPLOY_DIR",
    "total_checks": $TOTAL_CHECKS,
    "passed_checks": $PASSED_CHECKS,
    "failed_checks": $FAILED_CHECKS,
    "success_rate": "$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))%",
    "validation_log": "$VALIDATION_LOG"
  },
  "validation_status": "$(if [ $FAILED_CHECKS -eq 0 ]; then echo "PASSED"; else echo "FAILED"; fi)",
  "next_steps": [
    "Review failed checks if any",
    "Proceed with Phase 2 Core Services deployment if all checks passed",
    "Monitor service health and performance"
  ]
}
EOF
    
    echo "Validation summary generated: $summary_file"
    echo ""
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Phase 1 Foundation Services validation PASSED!"
        echo -e "${GREEN}✓${NC} All $PASSED_CHECKS checks passed successfully"
        echo -e "${GREEN}✓${NC} Ready to proceed to Phase 2: Core Services"
    else
        echo -e "${RED}✗${NC} Phase 1 Foundation Services validation FAILED!"
        echo -e "${RED}✗${NC} $FAILED_CHECKS checks failed out of $TOTAL_CHECKS total"
        echo -e "${YELLOW}⚠${NC} Please review failed checks before proceeding"
    fi
}

# Main validation function
main() {
    init_validation
    
    # Execute validation steps
    test_ssh_connection || exit 1
    verify_docker_networks || exit 1
    verify_data_directories || exit 1
    verify_environment_files || exit 1
    verify_docker_images || exit 1
    verify_distroless_infrastructure || exit 1
    verify_foundation_services || exit 1
    verify_service_health || exit 1
    verify_distroless_compliance || exit 1
    verify_volume_mounts || exit 1
    verify_network_connectivity || exit 1
    
    generate_validation_summary
}

# Run main function
main "$@"
