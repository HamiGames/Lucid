#!/bin/bash
# System Health Check Script
# LUCID-STRICT Layer 2 Monitoring
# Purpose: Comprehensive system health check for operational monitoring
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
LOG_FILE="${LOG_FILE:-/var/log/lucid/system-health.log}"
HEALTH_REPORT_DIR="${HEALTH_REPORT_DIR:-/data/reports/health}"
COMPOSE_FILE="${LUCID_COMPOSE_FILE:-/opt/lucid/docker-compose.yml}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lucid}"
MONGO_USER="${MONGO_USER:-lucid}"
MONGO_PASS="${MONGO_PASS:-lucid}"
TRON_NODE_URL="${TRON_NODE_URL:-https://api.shasta.trongrid.io}"
TOR_SOCKS_PORT="${TOR_SOCKS_PORT:-9050}"
TOR_CONTROL_PORT="${TOR_CONTROL_PORT:-9051}"

# Service definitions
SERVICES=(
    "lucid_mongo"
    "tor-proxy"
    "lucid_api"
    "api-gateway"
    "lucid-blockchain"
    "lucid-recording"
    "lucid-storage"
    "lucid-gui"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${1}" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

# Create directories if they don't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$HEALTH_REPORT_DIR"

echo "========================================"
log_info "🏥 LUCID System Health Check"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Comprehensive system health check for operational monitoring"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -q, --quiet             Quiet mode (errors only)"
    echo "  -j, --json              Output results in JSON format"
    echo "  -r, --report            Generate detailed health report"
    echo "  -s, --services          Check only service health"
    echo "  -d, --disk              Check only disk health"
    echo "  -n, --network           Check only network health"
    echo "  -m, --memory            Check only memory health"
    echo "  -c, --cpu               Check only CPU health"
    echo "  --threshold PERCENT     Set warning threshold (default: 80)"
    echo "  --critical PERCENT      Set critical threshold (default: 90)"
    echo ""
    echo "Environment Variables:"
    echo "  HEALTH_REPORT_DIR       Health report directory (default: /data/reports/health)"
    echo "  LUCID_COMPOSE_FILE      Docker compose file path"
    echo "  MONGO_HOST              MongoDB host (default: localhost)"
    echo "  MONGO_PORT              MongoDB port (default: 27017)"
    echo "  TRON_NODE_URL           TRON node URL for blockchain checks"
    echo "  TOR_SOCKS_PORT          Tor SOCKS port (default: 9050)"
    echo "  TOR_CONTROL_PORT        Tor control port (default: 9051)"
    echo ""
    echo "Examples:"
    echo "  $0 --verbose            Detailed health check"
    echo "  $0 --json               JSON output for monitoring"
    echo "  $0 --report             Generate detailed health report"
    echo "  $0 --services           Check only service health"
    echo "  $0 --threshold 75       Set warning threshold to 75%"
}

# Parse command line arguments
VERBOSE=false
QUIET=false
JSON_OUTPUT=false
GENERATE_REPORT=false
SERVICES_ONLY=false
DISK_ONLY=false
NETWORK_ONLY=false
MEMORY_ONLY=false
CPU_ONLY=false
WARNING_THRESHOLD=80
CRITICAL_THRESHOLD=90

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -j|--json)
            JSON_OUTPUT=true
            shift
            ;;
        -r|--report)
            GENERATE_REPORT=true
            shift
            ;;
        -s|--services)
            SERVICES_ONLY=true
            shift
            ;;
        -d|--disk)
            DISK_ONLY=true
            shift
            ;;
        -n|--network)
            NETWORK_ONLY=true
            shift
            ;;
        -m|--memory)
            MEMORY_ONLY=true
            shift
            ;;
        -c|--cpu)
            CPU_ONLY=true
            shift
            ;;
        --threshold)
            WARNING_THRESHOLD="$2"
            shift 2
            ;;
        --critical)
            CRITICAL_THRESHOLD="$2"
            shift 2
            ;;
        -*)
            log_error "Unknown option $1"
            show_usage
            exit 1
            ;;
        *)
            log_error "Unexpected argument: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Initialize health status
declare -A HEALTH_STATUS
declare -A HEALTH_MESSAGES
declare -A HEALTH_METRICS

# Function to add health status
add_health_status() {
    local component="$1"
    local status="$2"
    local message="$3"
    local metric="$4"
    
    HEALTH_STATUS["$component"]="$status"
    HEALTH_MESSAGES["$component"]="$message"
    if [[ -n "$metric" ]]; then
        HEALTH_METRICS["$component"]="$metric"
    fi
}

# Function to check CPU health
check_cpu_health() {
    log_info "Checking CPU health..."
    
    # Get CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    local cpu_cores=$(nproc)
    
    # Convert load average to percentage
    local load_percentage=$(echo "scale=2; ($load_avg / $cpu_cores) * 100" | bc 2>/dev/null || echo "0")
    
    local status="healthy"
    local message="CPU usage: ${cpu_usage}%, Load: ${load_percentage}%"
    
    if (( $(echo "$cpu_usage > $CRITICAL_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
        status="critical"
        message="CPU usage critical: ${cpu_usage}% (threshold: ${CRITICAL_THRESHOLD}%)"
    elif (( $(echo "$cpu_usage > $WARNING_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
        status="warning"
        message="CPU usage high: ${cpu_usage}% (threshold: ${WARNING_THRESHOLD}%)"
    fi
    
    add_health_status "cpu" "$status" "$message" "usage=${cpu_usage},load=${load_percentage},cores=${cpu_cores}"
    
    if [[ "$QUIET" == "false" ]]; then
        if [[ "$status" == "critical" ]]; then
            log_error "$message"
        elif [[ "$status" == "warning" ]]; then
            log_warning "$message"
        else
            log_success "$message"
        fi
    fi
}

# Function to check memory health
check_memory_health() {
    log_info "Checking memory health..."
    
    # Get memory usage
    local memory_info=$(free -m)
    local total_memory=$(echo "$memory_info" | awk 'NR==2{print $2}')
    local used_memory=$(echo "$memory_info" | awk 'NR==2{print $3}')
    local available_memory=$(echo "$memory_info" | awk 'NR==2{print $7}')
    
    # Calculate percentages
    local memory_usage_percent=$(echo "scale=2; ($used_memory / $total_memory) * 100" | bc 2>/dev/null || echo "0")
    local available_percent=$(echo "scale=2; ($available_memory / $total_memory) * 100" | bc 2>/dev/null || echo "0")
    
    local status="healthy"
    local message="Memory usage: ${memory_usage_percent}%, Available: ${available_percent}%"
    
    if (( $(echo "$memory_usage_percent > $CRITICAL_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
        status="critical"
        message="Memory usage critical: ${memory_usage_percent}% (threshold: ${CRITICAL_THRESHOLD}%)"
    elif (( $(echo "$memory_usage_percent > $WARNING_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
        status="warning"
        message="Memory usage high: ${memory_usage_percent}% (threshold: ${WARNING_THRESHOLD}%)"
    fi
    
    add_health_status "memory" "$status" "$message" "usage=${memory_usage_percent},available=${available_percent},total=${total_memory}MB"
    
    if [[ "$QUIET" == "false" ]]; then
        if [[ "$status" == "critical" ]]; then
            log_error "$message"
        elif [[ "$status" == "warning" ]]; then
            log_warning "$message"
        else
            log_success "$message"
        fi
    fi
}

# Function to check disk health
check_disk_health() {
    log_info "Checking disk health..."
    
    # Check root filesystem
    local root_usage=$(df -h / | awk 'NR==2{print $5}' | tr -d '%')
    local root_available=$(df -h / | awk 'NR==2{print $4}')
    local root_total=$(df -h / | awk 'NR==2{print $2}')
    
    local status="healthy"
    local message="Root filesystem: ${root_usage}% used, ${root_available} available"
    
    if [[ $root_usage -gt $CRITICAL_THRESHOLD ]]; then
        status="critical"
        message="Root filesystem critical: ${root_usage}% used (threshold: ${CRITICAL_THRESHOLD}%)"
    elif [[ $root_usage -gt $WARNING_THRESHOLD ]]; then
        status="warning"
        message="Root filesystem high usage: ${root_usage}% used (threshold: ${WARNING_THRESHOLD}%)"
    fi
    
    add_health_status "disk_root" "$status" "$message" "usage=${root_usage},available=${root_available},total=${root_total}"
    
    # Check data directory if it exists
    if [[ -d "/data" ]]; then
        local data_usage=$(df -h /data | awk 'NR==2{print $5}' | tr -d '%' 2>/dev/null || echo "0")
        local data_available=$(df -h /data | awk 'NR==2{print $4}' 2>/dev/null || echo "unknown")
        local data_total=$(df -h /data | awk 'NR==2{print $2}' 2>/dev/null || echo "unknown")
        
        local data_status="healthy"
        local data_message="Data directory: ${data_usage}% used, ${data_available} available"
        
        if [[ $data_usage -gt $CRITICAL_THRESHOLD ]]; then
            data_status="critical"
            data_message="Data directory critical: ${data_usage}% used (threshold: ${CRITICAL_THRESHOLD}%)"
        elif [[ $data_usage -gt $WARNING_THRESHOLD ]]; then
            data_status="warning"
            data_message="Data directory high usage: ${data_usage}% used (threshold: ${WARNING_THRESHOLD}%)"
        fi
        
        add_health_status "disk_data" "$data_status" "$data_message" "usage=${data_usage},available=${data_available},total=${data_total}"
    fi
    
    if [[ "$QUIET" == "false" ]]; then
        if [[ "$status" == "critical" || "$data_status" == "critical" ]]; then
            log_error "Disk usage critical"
        elif [[ "$status" == "warning" || "$data_status" == "warning" ]]; then
            log_warning "Disk usage high"
        else
            log_success "Disk usage normal"
        fi
    fi
}

# Function to check network health
check_network_health() {
    log_info "Checking network health..."
    
    # Check internet connectivity
    local internet_status="healthy"
    local internet_message="Internet connectivity: OK"
    
    if ping -c 1 8.8.8.8 &>/dev/null; then
        if [[ "$QUIET" == "false" ]]; then
            log_success "$internet_message"
        fi
    else
        internet_status="critical"
        internet_message="Internet connectivity: FAILED"
        if [[ "$QUIET" == "false" ]]; then
            log_error "$internet_message"
        fi
    fi
    
    add_health_status "network_internet" "$internet_status" "$internet_message"
    
    # Check Tor proxy
    local tor_status="healthy"
    local tor_message="Tor proxy: OK"
    
    if nc -z localhost "$TOR_SOCKS_PORT" 2>/dev/null; then
        if [[ "$QUIET" == "false" ]]; then
            log_success "$tor_message"
        fi
    else
        tor_status="critical"
        tor_message="Tor proxy: FAILED"
        if [[ "$QUIET" == "false" ]]; then
            log_error "$tor_message"
        fi
    fi
    
    add_health_status "network_tor" "$tor_status" "$tor_message"
    
    # Check TRON node connectivity
    local tron_status="healthy"
    local tron_message="TRON node: OK"
    
    if command -v curl &> /dev/null; then
        if curl -s --connect-timeout 10 "$TRON_NODE_URL/wallet/getnowblock" &>/dev/null; then
            if [[ "$QUIET" == "false" ]]; then
                log_success "$tron_message"
            fi
        else
            tron_status="warning"
            tron_message="TRON node: CONNECTION ISSUES"
            if [[ "$QUIET" == "false" ]]; then
                log_warning "$tron_message"
            fi
        fi
    else
        tron_status="warning"
        tron_message="TRON node: Cannot test (curl not available)"
        if [[ "$QUIET" == "false" ]]; then
            log_warning "$tron_message"
        fi
    fi
    
    add_health_status "network_tron" "$tron_status" "$tron_message"
}

# Function to check Docker health
check_docker_health() {
    log_info "Checking Docker health..."
    
    local docker_status="healthy"
    local docker_message="Docker: OK"
    
    if ! command -v docker &> /dev/null; then
        docker_status="critical"
        docker_message="Docker: NOT INSTALLED"
    elif ! docker info &>/dev/null; then
        docker_status="critical"
        docker_message="Docker: DAEMON NOT RUNNING"
    else
        # Check Docker system info
        local docker_info=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}" 2>/dev/null || echo "unknown")
        docker_message="Docker: OK ($(echo "$docker_info" | wc -l) containers)"
    fi
    
    add_health_status "docker" "$docker_status" "$docker_message"
    
    if [[ "$QUIET" == "false" ]]; then
        if [[ "$docker_status" == "critical" ]]; then
            log_error "$docker_message"
        else
            log_success "$docker_message"
        fi
    fi
}

# Function to check service health
check_service_health() {
    log_info "Checking service health..."
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        add_health_status "services" "critical" "Compose file not found: $COMPOSE_FILE"
        if [[ "$QUIET" == "false" ]]; then
            log_error "Compose file not found: $COMPOSE_FILE"
        fi
        return 1
    fi
    
    local running_services=0
    local total_services=${#SERVICES[@]}
    local failed_services=()
    
    for service in "${SERVICES[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps "$service" &>/dev/null; then
            local status=$(docker-compose -f "$COMPOSE_FILE" ps "$service" --format "table {{.State}}" | tail -1)
            if [[ "$status" == "Up" ]]; then
                ((running_services++))
                if [[ "$VERBOSE" == "true" && "$QUIET" == "false" ]]; then
                    log_success "Service $service: Running"
                fi
            else
                failed_services+=("$service")
                if [[ "$QUIET" == "false" ]]; then
                    log_error "Service $service: $status"
                fi
            fi
        else
            failed_services+=("$service")
            if [[ "$QUIET" == "false" ]]; then
                log_error "Service $service: Not found in compose file"
            fi
        fi
    done
    
    local services_status="healthy"
    local services_message="Services: $running_services/$total_services running"
    
    if [[ ${#failed_services[@]} -eq $total_services ]]; then
        services_status="critical"
        services_message="Services: ALL FAILED"
    elif [[ ${#failed_services[@]} -gt 0 ]]; then
        services_status="warning"
        services_message="Services: $running_services/$total_services running (${#failed_services[@]} failed)"
    fi
    
    add_health_status "services" "$services_status" "$services_message" "running=${running_services},total=${total_services},failed=${#failed_services[@]}"
    
    if [[ "$QUIET" == "false" ]]; then
        if [[ "$services_status" == "critical" ]]; then
            log_error "$services_message"
        elif [[ "$services_status" == "warning" ]]; then
            log_warning "$services_message"
        else
            log_success "$services_message"
        fi
    fi
}

# Function to check MongoDB health
check_mongodb_health() {
    log_info "Checking MongoDB health..."
    
    local mongo_status="healthy"
    local mongo_message="MongoDB: OK"
    
    # Test MongoDB connection
    local auth_string=""
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASS" ]]; then
        auth_string="-u $MONGO_USER -p $MONGO_PASS --authenticationDatabase admin"
    fi
    
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string --eval "db.runCommand({ping: 1})" &>/dev/null; then
        # Get MongoDB stats
        local mongo_stats=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" --quiet --eval "db.stats()" 2>/dev/null || echo "unknown")
        mongo_message="MongoDB: OK (connected to $MONGO_DB)"
    else
        mongo_status="critical"
        mongo_message="MongoDB: CONNECTION FAILED"
    fi
    
    add_health_status "mongodb" "$mongo_status" "$mongo_message"
    
    if [[ "$QUIET" == "false" ]]; then
        if [[ "$mongo_status" == "critical" ]]; then
            log_error "$mongo_message"
        else
            log_success "$mongo_message"
        fi
    fi
}

# Function to output JSON results
output_json() {
    echo "{"
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"system\": \"$(uname -n)\","
    echo "  \"lucid_version\": \"$(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')\","
    echo "  \"health_checks\": {"
    
    local first=true
    for component in "${!HEALTH_STATUS[@]}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo ","
        fi
        
        echo -n "    \"$component\": {"
        echo -n "\"status\": \"${HEALTH_STATUS[$component]}\","
        echo -n "\"message\": \"${HEALTH_MESSAGES[$component]}\""
        
        if [[ -n "${HEALTH_METRICS[$component]}" ]]; then
            echo -n ",\"metrics\": \"${HEALTH_METRICS[$component]}\""
        fi
        
        echo -n "}"
    done
    
    echo ""
    echo "  }"
    echo "}"
}

# Function to generate health report
generate_health_report() {
    log_info "Generating detailed health report..."
    
    local report_timestamp=$(date +"%Y%m%d_%H%M%S")
    local report_file="$HEALTH_REPORT_DIR/health-report-$report_timestamp.txt"
    
    cat > "$report_file" << EOF
========================================
LUCID System Health Report
========================================
Generated: $(date)
System: $(uname -n)
Lucid Version: $(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')
Uptime: $(uptime)

========================================
SYSTEM OVERVIEW
========================================
EOF
    
    # Add system information
    echo "Hostname: $(hostname)" >> "$report_file"
    echo "OS: $(uname -o)" >> "$report_file"
    echo "Kernel: $(uname -r)" >> "$report_file"
    echo "Architecture: $(uname -m)" >> "$report_file"
    echo "" >> "$report_file"
    
    # Add health check results
    echo "========================================" >> "$report_file"
    echo "HEALTH CHECK RESULTS" >> "$report_file"
    echo "========================================" >> "$report_file"
    
    for component in "${!HEALTH_STATUS[@]}"; do
        echo "Component: $component" >> "$report_file"
        echo "Status: ${HEALTH_STATUS[$component]}" >> "$report_file"
        echo "Message: ${HEALTH_MESSAGES[$component]}" >> "$report_file"
        if [[ -n "${HEALTH_METRICS[$component]}" ]]; then
            echo "Metrics: ${HEALTH_METRICS[$component]}" >> "$report_file"
        fi
        echo "" >> "$report_file"
    done
    
    # Add detailed system information
    echo "========================================" >> "$report_file"
    echo "DETAILED SYSTEM INFORMATION" >> "$report_file"
    echo "========================================" >> "$report_file"
    
    echo "CPU Information:" >> "$report_file"
    cat /proc/cpuinfo | grep "model name" | head -1 >> "$report_file"
    echo "CPU Cores: $(nproc)" >> "$report_file"
    echo "" >> "$report_file"
    
    echo "Memory Information:" >> "$report_file"
    free -h >> "$report_file"
    echo "" >> "$report_file"
    
    echo "Disk Information:" >> "$report_file"
    df -h >> "$report_file"
    echo "" >> "$report_file"
    
    echo "Network Interfaces:" >> "$report_file"
    ip addr show >> "$report_file"
    echo "" >> "$report_file"
    
    echo "Docker Information:" >> "$report_file"
    docker version >> "$report_file" 2>/dev/null || echo "Docker not available" >> "$report_file"
    echo "" >> "$report_file"
    
    echo "========================================" >> "$report_file"
    echo "END OF REPORT" >> "$report_file"
    echo "========================================" >> "$report_file"
    
    log_success "Health report generated: $report_file"
}

# Main function
main() {
    # Perform health checks based on options
    if [[ "$CPU_ONLY" == "true" ]]; then
        check_cpu_health
    elif [[ "$MEMORY_ONLY" == "true" ]]; then
        check_memory_health
    elif [[ "$DISK_ONLY" == "true" ]]; then
        check_disk_health
    elif [[ "$NETWORK_ONLY" == "true" ]]; then
        check_network_health
    elif [[ "$SERVICES_ONLY" == "true" ]]; then
        check_docker_health
        check_service_health
        check_mongodb_health
    else
        # Full health check
        check_cpu_health
        check_memory_health
        check_disk_health
        check_network_health
        check_docker_health
        check_service_health
        check_mongodb_health
    fi
    
    # Output results
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json
    fi
    
    # Generate report if requested
    if [[ "$GENERATE_REPORT" == "true" ]]; then
        generate_health_report
    fi
    
    # Determine overall health status
    local overall_status="healthy"
    local critical_count=0
    local warning_count=0
    
    for status in "${HEALTH_STATUS[@]}"; do
        case "$status" in
            "critical")
                ((critical_count++))
                ;;
            "warning")
                ((warning_count++))
                ;;
        esac
    done
    
    if [[ $critical_count -gt 0 ]]; then
        overall_status="critical"
    elif [[ $warning_count -gt 0 ]]; then
        overall_status="warning"
    fi
    
    # Log overall status
    echo ""
    echo "========================================"
    if [[ "$overall_status" == "critical" ]]; then
        log_error "Overall System Health: CRITICAL ($critical_count critical issues)"
    elif [[ "$overall_status" == "warning" ]]; then
        log_warning "Overall System Health: WARNING ($warning_count warnings)"
    else
        log_success "Overall System Health: HEALTHY"
    fi
    echo "========================================"
    
    # Return appropriate exit code
    case "$overall_status" in
        "critical")
            exit 2
            ;;
        "warning")
            exit 1
            ;;
        "healthy")
            exit 0
            ;;
    esac
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
    # Cleanup will be handled by individual functions
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
