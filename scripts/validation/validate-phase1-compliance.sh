#!/bin/bash
# Phase 1 Foundation Services Build Validation Script
# Validates alignment with lucid-container-build-plan.plan.md Steps 5-9
# Ensures compatibility with architecture documents and project structure

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
VALIDATION_LOG="$PROJECT_ROOT/validation-report-phase1.json"
VALIDATION_RESULTS=()

# Initialize validation results
init_validation() {
    echo -e "${BLUE}=== Phase 1 Foundation Services Build Validation ===${NC}"
    echo "Project Root: $PROJECT_ROOT"
    echo "Validation Log: $VALIDATION_LOG"
    echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
}

# Log validation result
log_result() {
    local step="$1"
    local status="$2"
    local message="$3"
    local details="$4"
    
    VALIDATION_RESULTS+=("{\"step\":\"$step\",\"status\":\"$status\",\"message\":\"$message\",\"details\":\"$details\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}")
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $step: $message"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $step: $message"
    else
        echo -e "${YELLOW}⚠${NC} $step: $message"
    fi
}

# Step 5: Storage Database Containers Validation
validate_step5_storage_database() {
    echo -e "${BLUE}=== Step 5: Storage Database Containers Validation ===${NC}"
    
    # Check MongoDB Dockerfile exists and is distroless
    local mongodb_dockerfile="$PROJECT_ROOT/infrastructure/containers/database/Dockerfile.mongodb"
    if [ -f "$mongodb_dockerfile" ]; then
        if grep -q "gcr.io/distroless" "$mongodb_dockerfile"; then
            log_result "step5-mongodb-distroless" "PASS" "MongoDB container uses distroless base image"
        else
            log_result "step5-mongodb-distroless" "FAIL" "MongoDB container does not use distroless base image"
        fi
        
        if grep -q "mongo:7" "$mongodb_dockerfile"; then
            log_result "step5-mongodb-version" "PASS" "MongoDB container uses version 7.0"
        else
            log_result "step5-mongodb-version" "FAIL" "MongoDB container does not use version 7.0"
        fi
    else
        log_result "step5-mongodb-dockerfile" "FAIL" "MongoDB Dockerfile not found"
    fi
    
    # Check Redis Dockerfile exists and is distroless
    local redis_dockerfile="$PROJECT_ROOT/infrastructure/containers/database/Dockerfile.redis"
    if [ -f "$redis_dockerfile" ]; then
        if grep -q "gcr.io/distroless" "$redis_dockerfile"; then
            log_result "step5-redis-distroless" "PASS" "Redis container uses distroless base image"
        else
            log_result "step5-redis-distroless" "FAIL" "Redis container does not use distroless base image"
        fi
        
        if grep -q "redis:7" "$redis_dockerfile"; then
            log_result "step5-redis-version" "PASS" "Redis container uses version 7.2"
        else
            log_result "step5-redis-version" "FAIL" "Redis container does not use version 7.2"
        fi
    else
        log_result "step5-redis-dockerfile" "FAIL" "Redis Dockerfile not found"
    fi
    
    # Check Elasticsearch Dockerfile exists (should be created)
    local elasticsearch_dockerfile="$PROJECT_ROOT/infrastructure/containers/database/Dockerfile.elasticsearch"
    if [ -f "$elasticsearch_dockerfile" ]; then
        if grep -q "gcr.io/distroless" "$elasticsearch_dockerfile"; then
            log_result "step5-elasticsearch-distroless" "PASS" "Elasticsearch container uses distroless base image"
        else
            log_result "step5-elasticsearch-distroless" "FAIL" "Elasticsearch container does not use distroless base image"
        fi
    else
        log_result "step5-elasticsearch-dockerfile" "FAIL" "Elasticsearch Dockerfile not found - needs to be created"
    fi
    
    # Check database initialization scripts
    local db_init_script="$PROJECT_ROOT/database/init_collections.js"
    if [ -f "$db_init_script" ]; then
        log_result "step5-db-init-script" "PASS" "Database initialization script exists"
        
        if grep -q "authentication" "$db_init_script"; then
            log_result "step5-auth-collection" "PASS" "Authentication collection defined in init script"
        else
            log_result "step5-auth-collection" "FAIL" "Authentication collection not defined in init script"
        fi
    else
        log_result "step5-db-init-script" "FAIL" "Database initialization script not found"
    fi
    
    echo ""
}

# Step 6: Authentication Service Container Validation
validate_step6_authentication() {
    echo -e "${BLUE}=== Step 6: Authentication Service Container Validation ===${NC}"
    
    # Check auth service Dockerfile exists and is distroless
    local auth_dockerfile="$PROJECT_ROOT/infrastructure/containers/auth/Dockerfile.auth-service"
    if [ -f "$auth_dockerfile" ]; then
        if grep -q "gcr.io/distroless/python3-debian12" "$auth_dockerfile"; then
            log_result "step6-auth-distroless" "PASS" "Authentication service uses distroless Python base"
        else
            log_result "step6-auth-distroless" "FAIL" "Authentication service does not use distroless Python base"
        fi
        
        if grep -q "AUTH_SERVICE_PORT=8089" "$auth_dockerfile"; then
            log_result "step6-auth-port" "PASS" "Authentication service configured for port 8089"
        else
            log_result "step6-auth-port" "FAIL" "Authentication service not configured for port 8089"
        fi
    else
        log_result "step6-auth-dockerfile" "FAIL" "Authentication service Dockerfile not found"
    fi
    
    # Check TRON isolation compliance
    local auth_main="$PROJECT_ROOT/auth/main.py"
    if [ -f "$auth_main" ]; then
        if grep -q "tron" "$auth_main" || grep -q "TRON" "$auth_main"; then
            log_result "step6-tron-isolation" "WARN" "TRON references found in auth service - verify this is only for signature verification"
        else
            log_result "step6-tron-isolation" "PASS" "No TRON references found in auth service main.py"
        fi
    else
        log_result "step6-auth-main" "FAIL" "Authentication service main.py not found"
    fi
    
    # Check hardware wallet integration
    local hardware_wallet="$PROJECT_ROOT/auth/hardware_wallet.py"
    if [ -f "$hardware_wallet" ]; then
        log_result "step6-hardware-wallet" "PASS" "Hardware wallet integration exists"
    else
        log_result "step6-hardware-wallet" "FAIL" "Hardware wallet integration not found"
    fi
    
    # Check JWT implementation
    local session_manager="$PROJECT_ROOT/auth/session_manager.py"
    if [ -f "$session_manager" ]; then
        log_result "step6-session-manager" "PASS" "Session manager exists"
    else
        log_result "step6-session-manager" "FAIL" "Session manager not found"
    fi
    
    echo ""
}

# Step 7: Phase 1 Docker Compose Generation Validation
validate_step7_docker_compose() {
    echo -e "${BLUE}=== Step 7: Phase 1 Docker Compose Generation Validation ===${NC}"
    
    # Check foundation docker-compose exists
    local foundation_compose="$PROJECT_ROOT/configs/docker/docker-compose.foundation.yml"
    if [ -f "$foundation_compose" ]; then
        log_result "step7-foundation-compose" "PASS" "Foundation docker-compose file exists"
        
        # Check for required services
        if grep -q "lucid-mongodb" "$foundation_compose"; then
            log_result "step7-mongodb-service" "PASS" "MongoDB service defined in compose"
        else
            log_result "step7-mongodb-service" "FAIL" "MongoDB service not defined in compose"
        fi
        
        if grep -q "lucid-redis" "$foundation_compose"; then
            log_result "step7-redis-service" "PASS" "Redis service defined in compose"
        else
            log_result "step7-redis-service" "FAIL" "Redis service not defined in compose"
        fi
        
        if grep -q "lucid-auth-service" "$foundation_compose"; then
            log_result "step7-auth-service" "PASS" "Auth service defined in compose"
        else
            log_result "step7-auth-service" "FAIL" "Auth service not defined in compose"
        fi
        
        # Check network configuration
        if grep -q "lucid-pi-network" "$foundation_compose"; then
            log_result "step7-network-config" "PASS" "Pi network configuration found"
        else
            log_result "step7-network-config" "FAIL" "Pi network configuration not found"
        fi
        
        # Check volumes configuration
        if grep -q "mongodb_data:" "$foundation_compose"; then
            log_result "step7-mongodb-volumes" "PASS" "MongoDB volumes configured"
        else
            log_result "step7-mongodb-volumes" "FAIL" "MongoDB volumes not configured"
        fi
        
    else
        log_result "step7-foundation-compose" "FAIL" "Foundation docker-compose file not found"
    fi
    
    echo ""
}

# Step 8: Phase 1 Deployment to Pi Validation
validate_step8_deployment() {
    echo -e "${BLUE}=== Step 8: Phase 1 Deployment to Pi Validation ===${NC}"
    
    # Check deployment script exists
    local deploy_script="$PROJECT_ROOT/scripts/deployment/deploy-phase1-pi.sh"
    if [ -f "$deploy_script" ]; then
        log_result "step8-deploy-script" "PASS" "Phase 1 deployment script exists"
        
        if grep -q "pickme@192.168.0.75" "$deploy_script"; then
            log_result "step8-pi-connection" "PASS" "Pi SSH connection configured"
        else
            log_result "step8-pi-connection" "FAIL" "Pi SSH connection not configured"
        fi
        
        if grep -q "docker-compose pull" "$deploy_script"; then
            log_result "step8-pull-images" "PASS" "Image pull step included"
        else
            log_result "step8-pull-images" "FAIL" "Image pull step not included"
        fi
        
    else
        log_result "step8-deploy-script" "FAIL" "Phase 1 deployment script not found"
    fi
    
    # Check environment configuration for Pi
    local pi_env="$PROJECT_ROOT/configs/environment/.env.pi-build"
    if [ -f "$pi_env" ]; then
        log_result "step8-pi-env" "PASS" "Pi environment configuration exists"
        
        if grep -q "PI_HOST=192.168.0.75" "$pi_env"; then
            log_result "step8-pi-host" "PASS" "Pi host configured correctly"
        else
            log_result "step8-pi-host" "FAIL" "Pi host not configured correctly"
        fi
        
    else
        log_result "step8-pi-env" "FAIL" "Pi environment configuration not found"
    fi
    
    echo ""
}

# Step 9: Phase 1 Integration Testing Validation
validate_step9_integration_testing() {
    echo -e "${BLUE}=== Step 9: Phase 1 Integration Testing Validation ===${NC}"
    
    # Check integration test directory exists
    local test_dir="$PROJECT_ROOT/tests/integration/phase1"
    if [ -d "$test_dir" ]; then
        log_result "step9-test-directory" "PASS" "Phase 1 integration test directory exists"
        
        # Check for specific test files
        local test_files=(
            "test_mongodb_connection.py"
            "test_redis_operations.py"
            "test_elasticsearch_indexing.py"
            "test_auth_service_flow.py"
            "test_jwt_token_validation.py"
            "test_cross_service_communication.py"
        )
        
        for test_file in "${test_files[@]}"; do
            if [ -f "$test_dir/$test_file" ]; then
                log_result "step9-$test_file" "PASS" "Integration test file exists: $test_file"
            else
                log_result "step9-$test_file" "FAIL" "Integration test file missing: $test_file"
            fi
        done
        
    else
        log_result "step9-test-directory" "FAIL" "Phase 1 integration test directory not found"
    fi
    
    # Check test configuration
    local pytest_config="$PROJECT_ROOT/pytest.ini"
    if [ -f "$pytest_config" ]; then
        log_result "step9-pytest-config" "PASS" "Pytest configuration exists"
    else
        log_result "step9-pytest-config" "FAIL" "Pytest configuration not found"
    fi
    
    echo ""
}

# Environment Configuration Validation
validate_environment_config() {
    echo -e "${BLUE}=== Environment Configuration Validation ===${NC}"
    
    # Check foundation environment file
    local foundation_env="$PROJECT_ROOT/configs/environment/foundation.env"
    if [ -f "$foundation_env" ]; then
        log_result "env-foundation-file" "PASS" "Foundation environment file exists"
        
        # Check for required configurations
        local required_configs=(
            "MONGODB_URI"
            "REDIS_URI"
            "ELASTICSEARCH_URI"
            "JWT_SECRET_KEY"
            "AUTH_SERVICE_PORT"
        )
        
        for config in "${required_configs[@]}"; do
            if grep -q "^$config=" "$foundation_env"; then
                log_result "env-$config" "PASS" "Configuration $config defined"
            else
                log_result "env-$config" "FAIL" "Configuration $config not defined"
            fi
        done
        
    else
        log_result "env-foundation-file" "FAIL" "Foundation environment file not found"
    fi
    
    echo ""
}

# Architecture Compliance Validation
validate_architecture_compliance() {
    echo -e "${BLUE}=== Architecture Compliance Validation ===${NC}"
    
    # Check distroless compliance
    local distroless_spec="$PROJECT_ROOT/docs/architecture/DISTROLESS-CONTAINER-SPEC.md"
    if [ -f "$distroless_spec" ]; then
        log_result "arch-distroless-spec" "PASS" "Distroless container specification exists"
    else
        log_result "arch-distroless-spec" "FAIL" "Distroless container specification not found"
    fi
    
    # Check TRON isolation compliance
    local tron_isolation="$PROJECT_ROOT/docs/architecture/TRON-PAYMENT-ISOLATION.md"
    if [ -f "$tron_isolation" ]; then
        log_result "arch-tron-isolation" "PASS" "TRON isolation specification exists"
    else
        log_result "arch-tron-isolation" "FAIL" "TRON isolation specification not found"
    fi
    
    # Check API plans alignment
    local api_plans_dir="$PROJECT_ROOT/plan/API_plans"
    if [ -d "$api_plans_dir" ]; then
        log_result "arch-api-plans" "PASS" "API plans directory exists"
        
        local required_plans=(
            "00-master-architecture/00-master-api-architecture.md"
            "08-storage-database-cluster/00-cluster-overview.md"
            "09-authentication-cluster/00-cluster-overview.md"
        )
        
        for plan in "${required_plans[@]}"; do
            if [ -f "$api_plans_dir/$plan" ]; then
                log_result "arch-$plan" "PASS" "API plan exists: $plan"
            else
                log_result "arch-$plan" "FAIL" "API plan missing: $plan"
            fi
        done
        
    else
        log_result "arch-api-plans" "FAIL" "API plans directory not found"
    fi
    
    echo ""
}

# Generate validation report
generate_report() {
    echo -e "${BLUE}=== Generating Validation Report ===${NC}"
    
    local total_tests=${#VALIDATION_RESULTS[@]}
    local passed_tests=0
    local failed_tests=0
    local warning_tests=0
    
    for result in "${VALIDATION_RESULTS[@]}"; do
        local status=$(echo "$result" | jq -r '.status')
        case "$status" in
            "PASS") ((passed_tests++)) ;;
            "FAIL") ((failed_tests++)) ;;
            "WARN") ((warning_tests++)) ;;
        esac
    done
    
    # Create JSON report
    cat > "$VALIDATION_LOG" << EOF
{
  "validation_summary": {
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "phase": "Phase 1 Foundation Services Build",
    "total_tests": $total_tests,
    "passed_tests": $passed_tests,
    "failed_tests": $failed_tests,
    "warning_tests": $warning_tests,
    "success_rate": "$(( (passed_tests * 100) / total_tests ))%"
  },
  "validation_results": [
$(IFS=','; echo "${VALIDATION_RESULTS[*]}")
  ]
}
EOF
    
    echo "Validation report generated: $VALIDATION_LOG"
    echo ""
    echo -e "${BLUE}=== Validation Summary ===${NC}"
    echo "Total Tests: $total_tests"
    echo -e "Passed: ${GREEN}$passed_tests${NC}"
    echo -e "Failed: ${RED}$failed_tests${NC}"
    echo -e "Warnings: ${YELLOW}$warning_tests${NC}"
    echo -e "Success Rate: $(( (passed_tests * 100) / total_tests ))%"
    
    if [ $failed_tests -eq 0 ]; then
        echo -e "${GREEN}✓ Phase 1 validation completed successfully!${NC}"
        return 0
    else
        echo -e "${RED}✗ Phase 1 validation failed with $failed_tests errors${NC}"
        return 1
    fi
}

# Main execution
main() {
    init_validation
    
    validate_step5_storage_database
    validate_step6_authentication
    validate_step7_docker_compose
    validate_step8_deployment
    validate_step9_integration_testing
    validate_environment_config
    validate_architecture_compliance
    
    generate_report
}

# Run main function
main "$@"
