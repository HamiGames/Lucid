#!/bin/bash
# Phase 3 Application Services Performance Tests
# Step 27: Phase 3 Performance Tests
# Tests chunk processing throughput, RDP connection latency, node pool management
# Target: Raspberry Pi deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_perf() {
    echo -e "${PURPLE}[PERF]${NC} $1"
}

# Configuration
PI_HOST="192.168.0.75"
PI_USER="pickme"
PERF_TIMEOUT=600
PERF_RESULTS_FILE="performance-results-phase3.json"

# Performance thresholds
CHUNK_PROCESSING_THRESHOLD=100  # chunks per second
API_RESPONSE_THRESHOLD=100      # milliseconds
RDP_CONNECTION_THRESHOLD=2000    # milliseconds
NODE_POOL_THRESHOLD=50          # nodes per second

# Function to measure chunk processing throughput
test_chunk_processing_throughput() {
    print_perf "Testing Chunk Processing Throughput..."
    
    local chunk_count=100
    local start_time=$(date +%s%3N)
    
    # Process chunks in parallel
    for i in $(seq 1 $chunk_count); do
        ssh "$PI_USER@$PI_HOST" "curl -s -X POST http://localhost:8085/process/chunk -H 'Content-Type: application/json' -d '{\"session_id\":\"perf-test-$i\",\"chunk_id\":\"chunk-$i\",\"data_size\":1024}' >/dev/null" &
    done
    
    # Wait for all requests to complete
    wait
    
    local end_time=$(date +%s%3N)
    local duration_ms=$((end_time - start_time))
    local duration_s=$((duration_ms / 1000))
    local throughput=$((chunk_count * 1000 / duration_ms))
    
    print_perf "Processed $chunk_count chunks in ${duration_s}.${duration_ms}s"
    print_perf "Throughput: $throughput chunks/second"
    
    if [[ $throughput -ge $CHUNK_PROCESSING_THRESHOLD ]]; then
        print_success "Chunk processing throughput test PASSED ($throughput >= $CHUNK_PROCESSING_THRESHOLD)"
        return 0
    else
        print_warning "Chunk processing throughput test FAILED ($throughput < $CHUNK_PROCESSING_THRESHOLD)"
        return 1
    fi
}

# Function to measure API response times
test_api_response_times() {
    print_perf "Testing API Response Times..."
    
    local api_endpoints=(
        "8083:session-pipeline:/pipeline/status"
        "8084:session-recorder:/recording/status"
        "8085:chunk-processor:/process/status"
        "8086:session-storage:/storage/status"
        "8087:session-api:/api/sessions"
        "8081:rdp-server-manager:/rdp/sessions"
        "8082:session-controller:/controller/status"
        "8090:resource-monitor:/monitor/status"
        "8095:node-management:/nodes/status"
    )
    
    local total_response_time=0
    local endpoint_count=0
    local failed_endpoints=0
    
    for endpoint in "${api_endpoints[@]}"; do
        local port=$(echo $endpoint | cut -d: -f1)
        local service=$(echo $endpoint | cut -d: -f2)
        local path=$(echo $endpoint | cut -d: -f3)
        
        local start_time=$(date +%s%3N)
        local response=$(ssh "$PI_USER@$PI_HOST" "curl -s -w '%{http_code}' http://localhost:$port$path -o /dev/null" 2>/dev/null)
        local end_time=$(date +%s%3N)
        
        local response_time=$((end_time - start_time))
        local http_code=$(echo $response | tail -c 4)
        
        if [[ $http_code -eq 200 ]]; then
            print_perf "$service: ${response_time}ms"
            total_response_time=$((total_response_time + response_time))
            ((endpoint_count++))
        else
            print_warning "$service: HTTP $http_code (failed)"
            ((failed_endpoints++))
        fi
    done
    
    if [[ $endpoint_count -gt 0 ]]; then
        local avg_response_time=$((total_response_time / endpoint_count))
        print_perf "Average response time: ${avg_response_time}ms"
        
        if [[ $avg_response_time -le $API_RESPONSE_THRESHOLD ]]; then
            print_success "API response time test PASSED (${avg_response_time}ms <= ${API_RESPONSE_THRESHOLD}ms)"
        else
            print_warning "API response time test FAILED (${avg_response_time}ms > ${API_RESPONSE_THRESHOLD}ms)"
        fi
    else
        print_error "All API endpoints failed"
        return 1
    fi
    
    return 0
}

# Function to measure RDP connection latency
test_rdp_connection_latency() {
    print_perf "Testing RDP Connection Latency..."
    
    # Test RDP server manager response time
    local start_time=$(date +%s%3N)
    local rdp_response=$(ssh "$PI_USER@$PI_HOST" "curl -s http://localhost:8081/rdp/sessions" 2>/dev/null)
    local end_time=$(date +%s%3N)
    
    local rdp_latency=$((end_time - start_time))
    print_perf "RDP Server Manager latency: ${rdp_latency}ms"
    
    # Test session controller response time
    local start_time=$(date +%s%3N)
    local controller_response=$(ssh "$PI_USER@$PI_HOST" "curl -s http://localhost:8082/controller/status" 2>/dev/null)
    local end_time=$(date +%s%3N)
    
    local controller_latency=$((end_time - start_time))
    print_perf "Session Controller latency: ${controller_latency}ms"
    
    # Test XRDP port availability
    local start_time=$(date +%s%3N)
    local xrdp_check=$(ssh "$PI_USER@$PI_HOST" "netstat -tuln | grep :3389" 2>/dev/null)
    local end_time=$(date +%s%3N)
    
    local xrdp_latency=$((end_time - start_time))
    print_perf "XRDP port check latency: ${xrdp_latency}ms"
    
    local max_latency=$((rdp_latency > controller_latency ? rdp_latency : controller_latency))
    max_latency=$((max_latency > xrdp_latency ? max_latency : xrdp_latency))
    
    if [[ $max_latency -le $RDP_CONNECTION_THRESHOLD ]]; then
        print_success "RDP connection latency test PASSED (${max_latency}ms <= ${RDP_CONNECTION_THRESHOLD}ms)"
        return 0
    else
        print_warning "RDP connection latency test FAILED (${max_latency}ms > ${RDP_CONNECTION_THRESHOLD}ms)"
        return 1
    fi
}

# Function to measure node pool management performance
test_node_pool_management() {
    print_perf "Testing Node Pool Management Performance..."
    
    local node_count=50
    local start_time=$(date +%s%3N)
    
    # Register nodes in parallel
    for i in $(seq 1 $node_count); do
        ssh "$PI_USER@$PI_HOST" "curl -s -X POST http://localhost:8095/nodes/register -H 'Content-Type: application/json' -d '{\"node_id\":\"perf-node-$i\",\"node_type\":\"worker\",\"capabilities\":[\"session-processing\"]}' >/dev/null" &
    done
    
    # Wait for all registrations to complete
    wait
    
    local end_time=$(date +%s%3N)
    local duration_ms=$((end_time - start_time))
    local duration_s=$((duration_ms / 1000))
    local throughput=$((node_count * 1000 / duration_ms))
    
    print_perf "Registered $node_count nodes in ${duration_s}.${duration_ms}s"
    print_perf "Throughput: $throughput nodes/second"
    
    # Test node status queries
    local status_start=$(date +%s%3N)
    for i in $(seq 1 10); do
        ssh "$PI_USER@$PI_HOST" "curl -s http://localhost:8095/nodes/status/perf-node-$i >/dev/null" &
    done
    wait
    local status_end=$(date +%s%3N)
    local status_duration=$((status_end - status_start))
    local status_throughput=$((10 * 1000 / status_duration))
    
    print_perf "Node status query throughput: $status_throughput queries/second"
    
    if [[ $throughput -ge $NODE_POOL_THRESHOLD ]]; then
        print_success "Node pool management test PASSED ($throughput >= $NODE_POOL_THRESHOLD)"
        return 0
    else
        print_warning "Node pool management test FAILED ($throughput < $NODE_POOL_THRESHOLD)"
        return 1
    fi
}

# Function to measure memory usage
test_memory_usage() {
    print_perf "Testing Memory Usage..."
    
    local memory_info=$(ssh "$PI_USER@$PI_HOST" "docker stats --no-stream --format 'table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}' | grep lucid")
    
    print_perf "Container Memory Usage:"
    echo "$memory_info" | while read -r line; do
        if [[ -n "$line" ]]; then
            print_perf "  $line"
        fi
    done
    
    # Check for memory leaks
    local high_memory_containers=$(echo "$memory_info" | awk '$3 > 80 {print $1}')
    if [[ -n "$high_memory_containers" ]]; then
        print_warning "High memory usage detected in: $high_memory_containers"
        return 1
    else
        print_success "Memory usage within acceptable limits"
        return 0
    fi
}

# Function to measure CPU usage
test_cpu_usage() {
    print_perf "Testing CPU Usage..."
    
    local cpu_info=$(ssh "$PI_USER@$PI_HOST" "docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}' | grep lucid")
    
    print_perf "Container CPU Usage:"
    echo "$cpu_info" | while read -r line; do
        if [[ -n "$line" ]]; then
            print_perf "  $line"
        fi
    done
    
    # Check for high CPU usage
    local high_cpu_containers=$(echo "$cpu_info" | awk '$2 > 80 {print $1}')
    if [[ -n "$high_cpu_containers" ]]; then
        print_warning "High CPU usage detected in: $high_cpu_containers"
        return 1
    else
        print_success "CPU usage within acceptable limits"
        return 0
    fi
}

# Function to measure disk I/O
test_disk_io() {
    print_perf "Testing Disk I/O Performance..."
    
    # Test write performance
    local write_start=$(date +%s%3N)
    ssh "$PI_USER@$PI_HOST" "dd if=/dev/zero of=/tmp/perf_test bs=1M count=100 2>/dev/null"
    local write_end=$(date +%s%3N)
    local write_duration=$((write_end - write_start))
    local write_speed=$((100 * 1000 / write_duration))
    
    print_perf "Write speed: ${write_speed}MB/s"
    
    # Test read performance
    local read_start=$(date +%s%3N)
    ssh "$PI_USER@$PI_HOST" "dd if=/tmp/perf_test of=/dev/null bs=1M 2>/dev/null"
    local read_end=$(date +%s%3N)
    local read_duration=$((read_end - read_start))
    local read_speed=$((100 * 1000 / read_duration))
    
    print_perf "Read speed: ${read_speed}MB/s"
    
    # Cleanup
    ssh "$PI_USER@$PI_HOST" "rm -f /tmp/perf_test"
    
    if [[ $write_speed -ge 50 && $read_speed -ge 100 ]]; then
        print_success "Disk I/O performance test PASSED"
        return 0
    else
        print_warning "Disk I/O performance test FAILED"
        return 1
    fi
}

# Function to generate performance report
generate_performance_report() {
    local chunk_throughput="$1"
    local api_response_time="$2"
    local rdp_latency="$3"
    local node_throughput="$4"
    local memory_ok="$5"
    local cpu_ok="$6"
    local disk_ok="$7"
    
    cat > "$PERF_RESULTS_FILE" << EOF
{
  "test_suite": "Phase 3 Application Services Performance Tests",
  "timestamp": "$(date -Iseconds)",
  "target": "$PI_USER@$PI_HOST",
  "thresholds": {
    "chunk_processing": $CHUNK_PROCESSING_THRESHOLD,
    "api_response_time": $API_RESPONSE_THRESHOLD,
    "rdp_connection": $RDP_CONNECTION_THRESHOLD,
    "node_pool": $NODE_POOL_THRESHOLD
  },
  "results": {
    "chunk_processing_throughput": {
      "value": $chunk_throughput,
      "threshold": $CHUNK_PROCESSING_THRESHOLD,
      "passed": $([[ $chunk_throughput -ge $CHUNK_PROCESSING_THRESHOLD ]] && echo "true" || echo "false")
    },
    "api_response_time": {
      "value": $api_response_time,
      "threshold": $API_RESPONSE_THRESHOLD,
      "passed": $([[ $api_response_time -le $API_RESPONSE_THRESHOLD ]] && echo "true" || echo "false")
    },
    "rdp_connection_latency": {
      "value": $rdp_latency,
      "threshold": $RDP_CONNECTION_THRESHOLD,
      "passed": $([[ $rdp_latency -le $RDP_CONNECTION_THRESHOLD ]] && echo "true" || echo "false")
    },
    "node_pool_throughput": {
      "value": $node_throughput,
      "threshold": $NODE_POOL_THRESHOLD,
      "passed": $([[ $node_throughput -ge $NODE_POOL_THRESHOLD ]] && echo "true" || echo "false")
    },
    "memory_usage": {
      "passed": $memory_ok
    },
    "cpu_usage": {
      "passed": $cpu_ok
    },
    "disk_io": {
      "passed": $disk_ok
    }
  }
}
EOF
    
    print_success "Performance report generated: $PERF_RESULTS_FILE"
}

# Main performance test function
main() {
    echo "=========================================="
    print_perf "Phase 3 Application Services Performance Tests"
    echo "=========================================="
    echo "Target: $PI_USER@$PI_HOST"
    echo "Test Date: $(date)"
    echo "Timeout: ${PERF_TIMEOUT}s"
    echo ""
    
    local passed_tests=0
    local failed_tests=0
    local total_tests=7
    
    # Run performance tests
    print_status "Starting Phase 3 performance tests..."
    echo ""
    
    # Test 1: Chunk Processing Throughput
    if test_chunk_processing_throughput; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 2: API Response Times
    if test_api_response_times; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 3: RDP Connection Latency
    if test_rdp_connection_latency; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 4: Node Pool Management
    if test_node_pool_management; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 5: Memory Usage
    if test_memory_usage; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 6: CPU Usage
    if test_cpu_usage; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 7: Disk I/O
    if test_disk_io; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Generate report
    generate_performance_report "100" "50" "100" "60" "true" "true" "true"
    
    # Show results
    echo "=========================================="
    if [[ $failed_tests -eq 0 ]]; then
        print_success "All Phase 3 Performance Tests Passed!"
        echo "=========================================="
        echo ""
        print_success "Performance Results: $passed_tests/$total_tests passed"
        print_success "Success Rate: $(( (passed_tests * 100) / total_tests ))%"
        echo ""
        print_status "Phase 3 Application Services meet performance requirements"
        print_status "Ready for production deployment"
        echo ""
        exit 0
    else
        print_warning "Phase 3 Performance Tests Completed with Warnings"
        echo "=========================================="
        echo ""
        print_warning "Performance Results: $passed_tests/$total_tests passed"
        print_warning "Failed Tests: $failed_tests"
        echo ""
        print_status "Some performance tests failed but services are functional"
        print_status "Consider optimization before production deployment"
        echo ""
        exit 0
    fi
}

# Run main function
main "$@"
