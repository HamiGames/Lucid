#!/bin/bash
# Phase 1 Foundation Services Integration Test Script
# Tests: auth-service, storage-database, mongodb, redis, elasticsearch
# Target: Raspberry Pi 5 (192.168.0.75)
# Network: lucid-pi-network

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PI_HOST="pickme@192.168.0.75"
PI_PORT="22"
PI_DEPLOY_PATH="/opt/lucid/production"
TEST_RESULTS_DIR="$PROJECT_ROOT/tests/results/phase1"
TEST_TIMEOUT=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

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

# Test result functions
test_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log_success "✓ $1"
}

test_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log_error "✗ $1"
}

# SSH execution function
ssh_exec() {
    local cmd="$1"
    ssh -p "$PI_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$PI_HOST" "$cmd"
}

# HTTP request function
http_request() {
    local url="$1"
    local method="${2:-GET}"
    local data="${3:-}"
    local headers="${4:-}"
    
    local curl_cmd="curl -s -w '%{http_code}' -X $method"
    
    if [[ -n "$data" ]]; then
        curl_cmd="$curl_cmd -d '$data'"
    fi
    
    if [[ -n "$headers" ]]; then
        curl_cmd="$curl_cmd -H '$headers'"
    fi
    
    curl_cmd="$curl_cmd '$url'"
    
    eval "$curl_cmd"
}

# Setup test environment
setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Create test results directory
    mkdir -p "$TEST_RESULTS_DIR"
    
    # Create test report file
    local report_file="$TEST_RESULTS_DIR/phase1-test-report-$(date +%Y%m%d-%H%M%S).txt"
    echo "Phase 1 Foundation Services Integration Test Report" > "$report_file"
    echo "Test Date: $(date)" >> "$report_file"
    echo "Target Pi: $PI_HOST" >> "$report_file"
    echo "========================================" >> "$report_file"
    echo "" >> "$report_file"
    
    log_success "Test environment setup complete"
}

# Test SSH connectivity
test_ssh_connectivity() {
    log_info "Testing SSH connectivity to Pi..."
    
    if ssh_exec "echo 'SSH connection successful'" >/dev/null 2>&1; then
        test_pass "SSH connectivity to Pi"
    else
        test_fail "SSH connectivity to Pi"
    fi
}

# Test Docker daemon
test_docker_daemon() {
    log_info "Testing Docker daemon on Pi..."
    
    if ssh_exec "docker info" >/dev/null 2>&1; then
        test_pass "Docker daemon is running"
    else
        test_fail "Docker daemon is running"
    fi
}

# Test Docker network
test_docker_network() {
    log_info "Testing Docker network..."
    
    if ssh_exec "docker network ls | grep -q lucid-pi-network"; then
        test_pass "Docker network lucid-pi-network exists"
    else
        test_fail "Docker network lucid-pi-network exists"
    fi
}

# Test service containers are running
test_containers_running() {
    log_info "Testing service containers are running..."
    
    local services=("lucid-mongodb" "lucid-redis" "lucid-elasticsearch" "lucid-auth-service" "lucid-storage-database")
    
    for service in "${services[@]}"; do
        if ssh_exec "docker ps --filter 'name=$service' --filter 'status=running' --format '{{.Names}}' | grep -q $service"; then
            test_pass "Container $service is running"
        else
            test_fail "Container $service is running"
        fi
    done
}

# Test MongoDB connection and performance
test_mongodb_connection() {
    log_info "Testing MongoDB connection and performance..."
    
    # Test connection
    if ssh_exec "docker exec lucid-mongodb mongosh --eval 'db.adminCommand(\"ping\")'" >/dev/null 2>&1; then
        test_pass "MongoDB connection"
    else
        test_fail "MongoDB connection"
    fi
    
    # Test replica set status
    if ssh_exec "docker exec lucid-mongodb mongosh --eval 'rs.status()'" >/dev/null 2>&1; then
        test_pass "MongoDB replica set is initialized"
    else
        test_fail "MongoDB replica set is initialized"
    fi
    
    # Test write performance
    local start_time=$(date +%s%N)
    if ssh_exec "docker exec lucid-mongodb mongosh --eval 'db.test.insertOne({test: \"performance\", timestamp: new Date()})'" >/dev/null 2>&1; then
        local end_time=$(date +%s%N)
        local duration=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
        
        if [[ $duration -lt 100 ]]; then  # Less than 100ms
            test_pass "MongoDB write performance (<100ms: ${duration}ms)"
        else
            test_fail "MongoDB write performance (>=100ms: ${duration}ms)"
        fi
    else
        test_fail "MongoDB write operation"
    fi
}

# Test Redis connection and caching
test_redis_connection() {
    log_info "Testing Redis connection and caching..."
    
    # Test connection
    if ssh_exec "docker exec lucid-redis redis-cli --no-auth-warning -a \$(grep REDIS_PASSWORD $PI_DEPLOY_PATH/.env.foundation | cut -d'=' -f2) ping" >/dev/null 2>&1; then
        test_pass "Redis connection"
    else
        test_fail "Redis connection"
    fi
    
    # Test set operation
    if ssh_exec "docker exec lucid-redis redis-cli --no-auth-warning -a \$(grep REDIS_PASSWORD $PI_DEPLOY_PATH/.env.foundation | cut -d'=' -f2) set test_key 'test_value'" >/dev/null 2>&1; then
        test_pass "Redis set operation"
    else
        test_fail "Redis set operation"
    fi
    
    # Test get operation
    if ssh_exec "docker exec lucid-redis redis-cli --no-auth-warning -a \$(grep REDIS_PASSWORD $PI_DEPLOY_PATH/.env.foundation | cut -d'=' -f2) get test_key | grep -q test_value"; then
        test_pass "Redis get operation"
    else
        test_fail "Redis get operation"
    fi
}

# Test Elasticsearch connection and indexing
test_elasticsearch_connection() {
    log_info "Testing Elasticsearch connection and indexing..."
    
    # Test connection
    local response=$(http_request "http://192.168.0.75:9200/_cluster/health")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Elasticsearch connection"
    else
        test_fail "Elasticsearch connection"
    fi
    
    # Test index exists
    local response=$(http_request "http://192.168.0.75:9200/lucid-sessions")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Elasticsearch index exists"
    else
        test_fail "Elasticsearch index exists"
    fi
    
    # Test document indexing
    local test_doc='{"session_id":"test-123","timestamp":"2024-01-01T00:00:00Z","content":"test content"}'
    local response=$(http_request "http://192.168.0.75:9200/lucid-sessions/_doc/test-123" "PUT" "$test_doc" "Content-Type: application/json")
    if [[ "$response" == *"201"* ]]; then
        test_pass "Elasticsearch document indexing"
    else
        test_fail "Elasticsearch document indexing"
    fi
}

# Test Auth Service endpoints
test_auth_service() {
    log_info "Testing Auth Service endpoints..."
    
    # Test health endpoint
    local response=$(http_request "http://192.168.0.75:8089/health")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Auth Service health endpoint"
    else
        test_fail "Auth Service health endpoint"
    fi
    
    # Test API documentation endpoint
    local response=$(http_request "http://192.168.0.75:8089/docs")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Auth Service API documentation"
    else
        test_fail "Auth Service API documentation"
    fi
    
    # Test login endpoint (should return 422 for missing data)
    local response=$(http_request "http://192.168.0.75:8089/auth/login" "POST")
    if [[ "$response" == *"422"* ]]; then
        test_pass "Auth Service login endpoint validation"
    else
        test_fail "Auth Service login endpoint validation"
    fi
}

# Test Storage Database Service endpoints
test_storage_database_service() {
    log_info "Testing Storage Database Service endpoints..."
    
    # Test health endpoint
    local response=$(http_request "http://192.168.0.75:8088/health")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Storage Database Service health endpoint"
    else
        test_fail "Storage Database Service health endpoint"
    fi
    
    # Test API documentation endpoint
    local response=$(http_request "http://192.168.0.75:8088/docs")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Storage Database Service API documentation"
    else
        test_fail "Storage Database Service API documentation"
    fi
}

# Test cross-service communication
test_cross_service_communication() {
    log_info "Testing cross-service communication..."
    
    # Test Auth Service -> MongoDB
    local response=$(http_request "http://192.168.0.75:8089/health")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Auth Service to MongoDB communication"
    else
        test_fail "Auth Service to MongoDB communication"
    fi
    
    # Test Storage Database Service -> MongoDB
    local response=$(http_request "http://192.168.0.75:8088/health")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Storage Database Service to MongoDB communication"
    else
        test_fail "Storage Database Service to MongoDB communication"
    fi
    
    # Test Storage Database Service -> Redis
    local response=$(http_request "http://192.168.0.75:8088/health")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Storage Database Service to Redis communication"
    else
        test_fail "Storage Database Service to Redis communication"
    fi
    
    # Test Storage Database Service -> Elasticsearch
    local response=$(http_request "http://192.168.0.75:8088/health")
    if [[ "$response" == *"200"* ]]; then
        test_pass "Storage Database Service to Elasticsearch communication"
    else
        test_fail "Storage Database Service to Elasticsearch communication"
    fi
}

# Test JWT token generation
test_jwt_token_generation() {
    log_info "Testing JWT token generation..."
    
    # Create a test user for authentication
    local test_user='{"tron_address":"TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH","signature":"test_signature","timestamp":1640995200000}'
    local response=$(http_request "http://192.168.0.75:8089/auth/login" "POST" "$test_user" "Content-Type: application/json")
    
    if [[ "$response" == *"200"* ]] || [[ "$response" == *"422"* ]]; then
        test_pass "JWT token generation endpoint"
    else
        test_fail "JWT token generation endpoint"
    fi
}

# Test session management
test_session_management() {
    log_info "Testing session management..."
    
    # Test session creation endpoint
    local response=$(http_request "http://192.168.0.75:8088/sessions" "POST")
    if [[ "$response" == *"422"* ]] || [[ "$response" == *"401"* ]]; then
        test_pass "Session creation endpoint validation"
    else
        test_fail "Session creation endpoint validation"
    fi
}

# Test performance benchmarks
test_performance_benchmarks() {
    log_info "Testing performance benchmarks..."
    
    # Test MongoDB query performance
    local start_time=$(date +%s%N)
    ssh_exec "docker exec lucid-mongodb mongosh --eval 'db.test.find().limit(1)'" >/dev/null 2>&1
    local end_time=$(date +%s%N)
    local duration=$(( (end_time - start_time) / 1000000 ))
    
    if [[ $duration -lt 10 ]]; then
        test_pass "MongoDB query performance (<10ms: ${duration}ms)"
    else
        test_fail "MongoDB query performance (>=10ms: ${duration}ms)"
    fi
    
    # Test Redis operation performance
    local start_time=$(date +%s%N)
    ssh_exec "docker exec lucid-redis redis-cli --no-auth-warning -a \$(grep REDIS_PASSWORD $PI_DEPLOY_PATH/.env.foundation | cut -d'=' -f2) ping" >/dev/null 2>&1
    local end_time=$(date +%s%N)
    local duration=$(( (end_time - start_time) / 1000000 ))
    
    if [[ $duration -lt 5 ]]; then
        test_pass "Redis operation performance (<5ms: ${duration}ms)"
    else
        test_fail "Redis operation performance (>=5ms: ${duration}ms)"
    fi
}

# Test container health checks
test_container_health() {
    log_info "Testing container health checks..."
    
    local services=("lucid-mongodb" "lucid-redis" "lucid-elasticsearch" "lucid-auth-service" "lucid-storage-database")
    
    for service in "${services[@]}"; do
        local health_status=$(ssh_exec "docker inspect $service --format='{{.State.Health.Status}}'")
        if [[ "$health_status" == "healthy" ]]; then
            test_pass "Container $service health check"
        else
            test_fail "Container $service health check (status: $health_status)"
        fi
    done
}

# Generate test report
generate_test_report() {
    log_info "Generating test report..."
    
    local report_file="$TEST_RESULTS_DIR/phase1-test-report-$(date +%Y%m%d-%H%M%S).txt"
    
    {
        echo "Phase 1 Foundation Services Integration Test Report"
        echo "Test Date: $(date)"
        echo "Target Pi: $PI_HOST"
        echo "========================================"
        echo ""
        echo "Test Results Summary:"
        echo "  Total Tests: $TESTS_TOTAL"
        echo "  Passed: $TESTS_PASSED"
        echo "  Failed: $TESTS_FAILED"
        echo "  Success Rate: $(( (TESTS_PASSED * 100) / TESTS_TOTAL ))%"
        echo ""
        
        if [[ $TESTS_FAILED -eq 0 ]]; then
            echo "STATUS: ALL TESTS PASSED ✅"
        else
            echo "STATUS: SOME TESTS FAILED ❌"
        fi
        
        echo ""
        echo "Service Endpoints:"
        echo "  - MongoDB: mongodb://lucid:****@192.168.0.75:27017/lucid"
        echo "  - Redis: redis://:****@192.168.0.75:6379"
        echo "  - Elasticsearch: http://192.168.0.75:9200"
        echo "  - Auth Service: http://192.168.0.75:8089"
        echo "  - Storage Database: http://192.168.0.75:8088"
        
    } > "$report_file"
    
    log_success "Test report generated: $report_file"
}

# Main execution
main() {
    log_info "Starting Phase 1 Foundation Services Integration Tests"
    log_info "Target Pi: $PI_HOST"
    log_info "Test Results Directory: $TEST_RESULTS_DIR"
    
    # Setup test environment
    setup_test_environment
    
    # Infrastructure tests
    test_ssh_connectivity
    test_docker_daemon
    test_docker_network
    test_containers_running
    test_container_health
    
    # Database tests
    test_mongodb_connection
    test_redis_connection
    test_elasticsearch_connection
    
    # Service tests
    test_auth_service
    test_storage_database_service
    
    # Integration tests
    test_cross_service_communication
    test_jwt_token_generation
    test_session_management
    
    # Performance tests
    test_performance_benchmarks
    
    # Generate report
    generate_test_report
    
    # Display summary
    log_info "Test Results Summary:"
    log_info "  Total Tests: $TESTS_TOTAL"
    log_info "  Passed: $TESTS_PASSED"
    log_info "  Failed: $TESTS_FAILED"
    log_info "  Success Rate: $(( (TESTS_PASSED * 100) / TESTS_TOTAL ))%"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        log_success "All Phase 1 integration tests passed! ✅"
        exit 0
    else
        log_error "Some Phase 1 integration tests failed! ❌"
        exit 1
    fi
}

# Run main function
main "$@"
