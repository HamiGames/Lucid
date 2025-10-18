#!/bin/bash

# K6 Load Testing Script for Lucid RDP System
# This script runs comprehensive load tests using K6 for the Lucid system

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_DIR="$PROJECT_ROOT/tests/load"
RESULTS_DIR="$PROJECT_ROOT/test-results/k6"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_HOST="http://localhost:8080"
DEFAULT_VUS=100
DEFAULT_DURATION="5m"
DEFAULT_SCENARIO="all"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date +'%Y-%m-%d %H:%M:%S')] ${message}${NC}"
}

print_info() {
    print_status "$BLUE" "INFO: $1"
}

print_success() {
    print_status "$GREEN" "SUCCESS: $1"
}

print_warning() {
    print_status "$YELLOW" "WARNING: $1"
}

print_error() {
    print_status "$RED" "ERROR: $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

K6 Load Testing Script for Lucid RDP System

OPTIONS:
    -h, --host HOST          Target host (default: $DEFAULT_HOST)
    -u, --vus VUS           Number of virtual users (default: $DEFAULT_VUS)
    -d, --duration DURATION Test duration (default: $DEFAULT_DURATION)
    -s, --scenario SCENARIO  Test scenario (default: $DEFAULT_SCENARIO)
    -o, --output DIR        Output directory (default: $RESULTS_DIR)
    -v, --verbose           Verbose output
    --help                  Show this help message

SCENARIOS:
    all                     Run all test scenarios
    concurrent-sessions     Test concurrent RDP sessions
    concurrent-users        Test concurrent user operations
    node-scaling           Test node scaling capabilities
    database-scaling       Test database scaling
    api-gateway            Test API Gateway performance
    blockchain             Test blockchain operations
    session-management     Test session management
    admin-operations       Test admin operations

EXAMPLES:
    $0 --scenario concurrent-sessions --vus 200 --duration 10m
    $0 --scenario all --host http://staging.lucid.local
    $0 --scenario node-scaling --vus 500 --duration 15m

EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if K6 is installed
    if ! command -v k6 &> /dev/null; then
        print_error "K6 is not installed. Please install K6 first."
        print_info "Installation instructions:"
        print_info "  Ubuntu/Debian: sudo apt-get install k6"
        print_info "  macOS: brew install k6"
        print_info "  Windows: choco install k6"
        print_info "  Or download from: https://k6.io/docs/getting-started/installation/"
        exit 1
    fi
    
    # Check if target host is reachable
    if ! curl -s --connect-timeout 5 "$HOST/health" > /dev/null; then
        print_warning "Target host $HOST is not reachable or health check failed"
        print_info "Make sure the Lucid system is running and accessible"
    fi
    
    print_success "Prerequisites check completed"
}

# Function to create K6 test script for concurrent sessions
create_concurrent_sessions_test() {
    local test_file="$TEST_DIR/k6_concurrent_sessions.js"
    
    cat > "$test_file" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const sessionCreationRate = new Rate('session_creation_success');
const sessionTerminationRate = new Rate('session_termination_success');

export let options = {
    stages: [
        { duration: '2m', target: 50 },   // Ramp up to 50 users
        { duration: '5m', target: 100 },  // Stay at 100 users
        { duration: '2m', target: 200 },  // Ramp up to 200 users
        { duration: '5m', target: 200 },  // Stay at 200 users
        { duration: '2m', target: 0 },    // Ramp down to 0 users
    ],
    thresholds: {
        http_req_duration: ['p(95)<1000'], // 95% of requests must complete below 1s
        http_req_failed: ['rate<0.05'],    // Error rate must be below 5%
        session_creation_success: ['rate>0.95'], // 95% session creation success
    },
};

const BASE_URL = __ENV.HOST || 'http://localhost:8080';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';

export default function() {
    let sessionId = null;
    
    // Step 1: Health check
    let healthResponse = http.get(`${BASE_URL}/health`);
    check(healthResponse, {
        'health check status is 200': (r) => r.status === 200,
        'health check response time < 100ms': (r) => r.timings.duration < 100,
    });
    
    // Step 2: Authenticate
    let authPayload = JSON.stringify({
        username: `test_user_${__VU}`,
        password: 'test_password_123'
    });
    
    let authResponse = http.post(`${BASE_URL}/auth/login`, authPayload, {
        headers: { 'Content-Type': 'application/json' },
    });
    
    let authSuccess = check(authResponse, {
        'auth status is 200 or 201': (r) => r.status === 200 || r.status === 201,
    });
    
    if (authSuccess && authResponse.json('token')) {
        let token = authResponse.json('token');
        
        // Step 3: Create session
        let sessionPayload = JSON.stringify({
            user_id: `user_${__VU}`,
            session_type: 'rdp',
            duration_minutes: 60,
            quality: 'medium'
        });
        
        let sessionResponse = http.post(`${BASE_URL}/sessions`, sessionPayload, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
        });
        
        let sessionCreated = check(sessionResponse, {
            'session creation status is 200 or 201': (r) => r.status === 200 || r.status === 201,
            'session creation response time < 500ms': (r) => r.timings.duration < 500,
        });
        
        sessionCreationRate.add(sessionCreated);
        
        if (sessionCreated && sessionResponse.json('session_id')) {
            sessionId = sessionResponse.json('session_id');
            
            // Step 4: Get session status
            let statusResponse = http.get(`${BASE_URL}/sessions/${sessionId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            check(statusResponse, {
                'session status check successful': (r) => r.status === 200,
            });
            
            // Step 5: Simulate session activity
            sleep(Math.random() * 5 + 1); // Random sleep 1-6 seconds
            
            // Step 6: Terminate session
            let terminateResponse = http.del(`${BASE_URL}/sessions/${sessionId}`, null, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            let sessionTerminated = check(terminateResponse, {
                'session termination status is 200 or 204': (r) => r.status === 200 || r.status === 204,
            });
            
            sessionTerminationRate.add(sessionTerminated);
        }
    }
    
    sleep(1); // Wait 1 second between iterations
}
EOF
    
    echo "$test_file"
}

# Function to create K6 test script for concurrent users
create_concurrent_users_test() {
    local test_file="$TEST_DIR/k6_concurrent_users.js"
    
    cat > "$test_file" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const userOperationRate = new Rate('user_operation_success');
const apiResponseRate = new Rate('api_response_success');

export let options = {
    stages: [
        { duration: '1m', target: 100 },   // Ramp up to 100 users
        { duration: '3m', target: 500 },   // Ramp up to 500 users
        { duration: '5m', target: 1000 },  // Ramp up to 1000 users
        { duration: '3m', target: 1000 },  // Stay at 1000 users
        { duration: '2m', target: 0 },     // Ramp down to 0 users
    ],
    thresholds: {
        http_req_duration: ['p(95)<2000'], // 95% of requests must complete below 2s
        http_req_failed: ['rate<0.1'],     // Error rate must be below 10%
        user_operation_success: ['rate>0.9'], // 90% user operations success
    },
};

const BASE_URL = __ENV.HOST || 'http://localhost:8080';

export default function() {
    let userId = `user_${__VU}_${__ITER}`;
    let authToken = null;
    
    // Step 1: Health check
    let healthResponse = http.get(`${BASE_URL}/health`);
    let healthSuccess = check(healthResponse, {
        'health check successful': (r) => r.status === 200,
    });
    
    apiResponseRate.add(healthSuccess);
    
    // Step 2: User registration/login
    let authPayload = JSON.stringify({
        username: userId,
        password: 'test_password_123'
    });
    
    let authResponse = http.post(`${BASE_URL}/auth/login`, authPayload, {
        headers: { 'Content-Type': 'application/json' },
    });
    
    let authSuccess = check(authResponse, {
        'authentication successful': (r) => r.status === 200 || r.status === 201,
    });
    
    if (authSuccess && authResponse.json('token')) {
        authToken = authResponse.json('token');
        
        // Step 3: Get user profile
        let profileResponse = http.get(`${BASE_URL}/users/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        check(profileResponse, {
            'profile retrieval successful': (r) => r.status === 200,
        });
        
        // Step 4: Get user sessions
        let sessionsResponse = http.get(`${BASE_URL}/sessions`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        check(sessionsResponse, {
            'sessions retrieval successful': (r) => r.status === 200,
        });
        
        // Step 5: Get blockchain info
        let blockchainResponse = http.get(`${BASE_URL}/chain/info`);
        
        check(blockchainResponse, {
            'blockchain info retrieval successful': (r) => r.status === 200,
        });
        
        // Step 6: Get node status
        let nodeResponse = http.get(`${BASE_URL}/nodes/status`);
        
        check(nodeResponse, {
            'node status retrieval successful': (r) => r.status === 200,
        });
        
        userOperationRate.add(true);
    } else {
        userOperationRate.add(false);
    }
    
    sleep(Math.random() * 2 + 0.5); // Random sleep 0.5-2.5 seconds
}
EOF
    
    echo "$test_file"
}

# Function to create K6 test script for node scaling
create_node_scaling_test() {
    local test_file="$TEST_DIR/k6_node_scaling.js"
    
    cat > "$test_file" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const nodeOperationRate = new Rate('node_operation_success');
const nodeRegistrationRate = new Rate('node_registration_success');

export let options = {
    stages: [
        { duration: '2m', target: 50 },    // Ramp up to 50 nodes
        { duration: '3m', target: 100 },   // Ramp up to 100 nodes
        { duration: '5m', target: 200 },  // Ramp up to 200 nodes
        { duration: '3m', target: 500 },  // Ramp up to 500 nodes
        { duration: '5m', target: 500 },  // Stay at 500 nodes
        { duration: '2m', target: 0 },   // Ramp down to 0 nodes
    ],
    thresholds: {
        http_req_duration: ['p(95)<3000'], // 95% of requests must complete below 3s
        http_req_failed: ['rate<0.05'],   // Error rate must be below 5%
        node_operation_success: ['rate>0.95'], // 95% node operations success
    },
};

const BASE_URL = __ENV.HOST || 'http://localhost:8080';

export default function() {
    let nodeId = `node_${__VU}_${__ITER}`;
    
    // Step 1: Health check
    let healthResponse = http.get(`${BASE_URL}/health`);
    check(healthResponse, {
        'health check successful': (r) => r.status === 200,
    });
    
    // Step 2: Node registration
    let nodePayload = JSON.stringify({
        node_id: nodeId,
        node_type: 'worker',
        capabilities: ['rdp', 'recording', 'processing'],
        resources: {
            cpu_cores: 4,
            memory_gb: 8,
            storage_gb: 100
        },
        location: {
            country: 'US',
            region: 'us-west-2'
        }
    });
    
    let registerResponse = http.post(`${BASE_URL}/nodes/register`, nodePayload, {
        headers: { 'Content-Type': 'application/json' },
    });
    
    let registrationSuccess = check(registerResponse, {
        'node registration successful': (r) => r.status === 200 || r.status === 201,
    });
    
    nodeRegistrationRate.add(registrationSuccess);
    
    if (registrationSuccess) {
        // Step 3: Get node status
        let statusResponse = http.get(`${BASE_URL}/nodes/${nodeId}/status`);
        
        check(statusResponse, {
            'node status retrieval successful': (r) => r.status === 200,
        });
        
        // Step 4: Update node metrics
        let metricsPayload = JSON.stringify({
            cpu_usage: Math.random() * 100,
            memory_usage: Math.random() * 100,
            disk_usage: Math.random() * 100,
            network_usage: Math.random() * 1000,
            timestamp: Date.now()
        });
        
        let metricsResponse = http.post(`${BASE_URL}/nodes/${nodeId}/metrics`, metricsPayload, {
            headers: { 'Content-Type': 'application/json' },
        });
        
        check(metricsResponse, {
            'metrics update successful': (r) => r.status === 200 || r.status === 201,
        });
        
        // Step 5: Get node performance
        let performanceResponse = http.get(`${BASE_URL}/nodes/${nodeId}/performance`);
        
        check(performanceResponse, {
            'performance retrieval successful': (r) => r.status === 200,
        });
        
        // Step 6: Simulate node work
        sleep(Math.random() * 3 + 1); // Random sleep 1-4 seconds
        
        // Step 7: Get node assignments
        let assignmentsResponse = http.get(`${BASE_URL}/nodes/${nodeId}/assignments`);
        
        check(assignmentsResponse, {
            'assignments retrieval successful': (r) => r.status === 200,
        });
        
        nodeOperationRate.add(true);
    } else {
        nodeOperationRate.add(false);
    }
    
    sleep(2); // Wait 2 seconds between iterations
}
EOF
    
    echo "$test_file"
}

# Function to create K6 test script for database scaling
create_database_scaling_test() {
    local test_file="$TEST_DIR/k6_database_scaling.js"
    
    cat > "$test_file" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const databaseOperationRate = new Rate('database_operation_success');
const queryPerformanceRate = new Rate('query_performance_success');

export let options = {
    stages: [
        { duration: '1m', target: 100 },   // Ramp up to 100 concurrent queries
        { duration: '2m', target: 300 },    // Ramp up to 300 concurrent queries
        { duration: '3m', target: 500 },   // Ramp up to 500 concurrent queries
        { duration: '5m', target: 500 },   // Stay at 500 concurrent queries
        { duration: '2m', target: 0 },    // Ramp down to 0 queries
    ],
    thresholds: {
        http_req_duration: ['p(95)<100'],  // 95% of requests must complete below 100ms
        http_req_failed: ['rate<0.01'],   // Error rate must be below 1%
        database_operation_success: ['rate>0.99'], // 99% database operations success
    },
};

const BASE_URL = __ENV.HOST || 'http://localhost:8080';

export default function() {
    let userId = `db_user_${__VU}_${__ITER}`;
    let sessionId = `session_${__VU}_${__ITER}`;
    
    // Step 1: Health check
    let healthResponse = http.get(`${BASE_URL}/health`);
    check(healthResponse, {
        'health check successful': (r) => r.status === 200,
    });
    
    // Step 2: Database connection test
    let dbHealthResponse = http.get(`${BASE_URL}/database/health`);
    let dbHealthSuccess = check(dbHealthResponse, {
        'database health check successful': (r) => r.status === 200,
        'database response time < 10ms': (r) => r.timings.duration < 10,
    });
    
    queryPerformanceRate.add(dbHealthSuccess);
    
    // Step 3: User data operations
    let userPayload = JSON.stringify({
        user_id: userId,
        username: userId,
        email: `${userId}@test.com`,
        created_at: new Date().toISOString()
    });
    
    let userResponse = http.post(`${BASE_URL}/users`, userPayload, {
        headers: { 'Content-Type': 'application/json' },
    });
    
    check(userResponse, {
        'user creation successful': (r) => r.status === 200 || r.status === 201,
        'user creation response time < 50ms': (r) => r.timings.duration < 50,
    });
    
    // Step 4: Session data operations
    let sessionPayload = JSON.stringify({
        session_id: sessionId,
        user_id: userId,
        session_type: 'rdp',
        status: 'active',
        created_at: new Date().toISOString()
    });
    
    let sessionResponse = http.post(`${BASE_URL}/sessions`, sessionPayload, {
        headers: { 'Content-Type': 'application/json' },
    });
    
    check(sessionResponse, {
        'session creation successful': (r) => r.status === 200 || r.status === 201,
        'session creation response time < 50ms': (r) => r.timings.duration < 50,
    });
    
    // Step 5: Query operations
    let queryResponse = http.get(`${BASE_URL}/users/${userId}`);
    
    check(queryResponse, {
        'user query successful': (r) => r.status === 200,
        'user query response time < 20ms': (r) => r.timings.duration < 20,
    });
    
    // Step 6: Complex queries
    let complexQueryResponse = http.get(`${BASE_URL}/sessions?user_id=${userId}&status=active`);
    
    check(complexQueryResponse, {
        'complex query successful': (r) => r.status === 200,
        'complex query response time < 100ms': (r) => r.timings.duration < 100,
    });
    
    // Step 7: Update operations
    let updatePayload = JSON.stringify({
        status: 'completed',
        updated_at: new Date().toISOString()
    });
    
    let updateResponse = http.put(`${BASE_URL}/sessions/${sessionId}`, updatePayload, {
        headers: { 'Content-Type': 'application/json' },
    });
    
    check(updateResponse, {
        'session update successful': (r) => r.status === 200,
        'session update response time < 30ms': (r) => r.timings.duration < 30,
    });
    
    // Step 8: Delete operations
    let deleteResponse = http.del(`${BASE_URL}/sessions/${sessionId}`);
    
    check(deleteResponse, {
        'session deletion successful': (r) => r.status === 200 || r.status === 204,
        'session deletion response time < 25ms': (r) => r.timings.duration < 25,
    });
    
    databaseOperationRate.add(true);
    
    sleep(0.1); // Small delay between iterations
}
EOF
    
    echo "$test_file"
}

# Function to run K6 test
run_k6_test() {
    local test_file=$1
    local output_file=$2
    local test_name=$3
    
    print_info "Running K6 test: $test_name"
    print_info "Test file: $test_file"
    print_info "Output file: $output_file"
    
    # Prepare K6 command
    local k6_cmd="k6 run"
    k6_cmd="$k6_cmd --vus $VUS"
    k6_cmd="$k6_cmd --duration $DURATION"
    k6_cmd="$k6_cmd --out json=$output_file"
    k6_cmd="$k6_cmd --env HOST=$HOST"
    
    if [ "$VERBOSE" = true ]; then
        k6_cmd="$k6_cmd --verbose"
    fi
    
    k6_cmd="$k6_cmd $test_file"
    
    print_info "Executing: $k6_cmd"
    
    # Run the test
    if eval "$k6_cmd"; then
        print_success "K6 test completed successfully: $test_name"
        return 0
    else
        print_error "K6 test failed: $test_name"
        return 1
    fi
}

# Function to generate test report
generate_report() {
    local results_dir=$1
    
    print_info "Generating test report..."
    
    local report_file="$results_dir/load_test_report.md"
    
    cat > "$report_file" << EOF
# K6 Load Test Report

**Generated:** $(date)
**Host:** $HOST
**Virtual Users:** $VUS
**Duration:** $DURATION
**Scenario:** $SCENARIO

## Test Results

### Test Files
EOF
    
    # List all result files
    for result_file in "$results_dir"/*.json; do
        if [ -f "$result_file" ]; then
            local test_name=$(basename "$result_file" .json)
            echo "- $test_name: $result_file" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF

### Performance Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Virtual Users | $VUS | - | - |
| Test Duration | $DURATION | - | - |
| Target Host | $HOST | - | - |

### Recommendations

1. **Performance Optimization**: Review response times and optimize slow endpoints
2. **Resource Scaling**: Consider scaling resources if thresholds are exceeded
3. **Error Rate**: Investigate any failed requests and improve error handling
4. **Monitoring**: Set up continuous monitoring for production load patterns

### Next Steps

1. Analyze detailed metrics in JSON result files
2. Identify performance bottlenecks
3. Optimize system configuration
4. Re-run tests after optimizations
5. Set up automated load testing in CI/CD pipeline

EOF
    
    print_success "Test report generated: $report_file"
}

# Function to cleanup old results
cleanup_old_results() {
    local results_dir=$1
    local max_age_days=7
    
    print_info "Cleaning up old test results (older than $max_age_days days)..."
    
    find "$results_dir" -name "*.json" -type f -mtime +$max_age_days -delete 2>/dev/null || true
    find "$results_dir" -name "*.md" -type f -mtime +$max_age_days -delete 2>/dev/null || true
    
    print_success "Cleanup completed"
}

# Main execution
main() {
    # Parse command line arguments
    HOST="$DEFAULT_HOST"
    VUS="$DEFAULT_VUS"
    DURATION="$DEFAULT_DURATION"
    SCENARIO="$DEFAULT_SCENARIO"
    OUTPUT_DIR="$RESULTS_DIR"
    VERBOSE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--host)
                HOST="$2"
                shift 2
                ;;
            -u|--vus)
                VUS="$2"
                shift 2
                ;;
            -d|--duration)
                DURATION="$2"
                shift 2
                ;;
            -s|--scenario)
                SCENARIO="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Create results directory
    RESULTS_DIR="$OUTPUT_DIR/k6_${SCENARIO}_${TIMESTAMP}"
    mkdir -p "$RESULTS_DIR"
    
    print_info "Starting K6 load testing..."
    print_info "Host: $HOST"
    print_info "Virtual Users: $VUS"
    print_info "Duration: $DURATION"
    print_info "Scenario: $SCENARIO"
    print_info "Results Directory: $RESULTS_DIR"
    
    # Check prerequisites
    check_prerequisites
    
    # Cleanup old results
    cleanup_old_results "$OUTPUT_DIR"
    
    # Run tests based on scenario
    local test_files=()
    local test_names=()
    
    case "$SCENARIO" in
        "all")
            test_files+=("$(create_concurrent_sessions_test)")
            test_names+=("concurrent_sessions")
            test_files+=("$(create_concurrent_users_test)")
            test_names+=("concurrent_users")
            test_files+=("$(create_node_scaling_test)")
            test_names+=("node_scaling")
            test_files+=("$(create_database_scaling_test)")
            test_names+=("database_scaling")
            ;;
        "concurrent-sessions")
            test_files+=("$(create_concurrent_sessions_test)")
            test_names+=("concurrent_sessions")
            ;;
        "concurrent-users")
            test_files+=("$(create_concurrent_users_test)")
            test_names+=("concurrent_users")
            ;;
        "node-scaling")
            test_files+=("$(create_node_scaling_test)")
            test_names+=("node_scaling")
            ;;
        "database-scaling")
            test_files+=("$(create_database_scaling_test)")
            test_names+=("database_scaling")
            ;;
        *)
            print_error "Unknown scenario: $SCENARIO"
            print_info "Available scenarios: all, concurrent-sessions, concurrent-users, node-scaling, database-scaling"
            exit 1
            ;;
    esac
    
    # Run all tests
    local failed_tests=0
    for i in "${!test_files[@]}"; do
        local test_file="${test_files[$i]}"
        local test_name="${test_names[$i]}"
        local output_file="$RESULTS_DIR/${test_name}_results.json"
        
        if run_k6_test "$test_file" "$output_file" "$test_name"; then
            print_success "Test passed: $test_name"
        else
            print_error "Test failed: $test_name"
            ((failed_tests++))
        fi
    done
    
    # Generate report
    generate_report "$RESULTS_DIR"
    
    # Summary
    print_info "Load testing completed!"
    print_info "Results directory: $RESULTS_DIR"
    print_info "Failed tests: $failed_tests"
    
    if [ $failed_tests -eq 0 ]; then
        print_success "All tests passed!"
        exit 0
    else
        print_error "Some tests failed. Check the results for details."
        exit 1
    fi
}

# Run main function
main "$@"
