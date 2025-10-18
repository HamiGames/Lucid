#!/bin/bash
# Lucid Service Verification Script
# Verifies all Lucid services are running and healthy
# Based on Step 50 requirements from BUILD_REQUIREMENTS_GUIDE.md

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"

# Default parameters
ENVIRONMENT="${1:-dev}"
VERBOSE="${2:-false}"
OUTPUT_FORMAT="${3:-table}"

# Service definitions for all 10 clusters
declare -A ALL_SERVICES=(
    # Phase 1: Foundation
    [lucid-mongodb]="27017:MongoDB database service:critical"
    [lucid-redis]="6379:Redis cache service:critical"
    [lucid-elasticsearch]="9200:Elasticsearch search service:critical"
    [lucid-auth-service]="8089:Authentication service:critical"
    
    # Phase 2: Core Services
    [lucid-api-gateway]="8080:API Gateway service:critical"
    [lucid-blockchain-engine]="8084:Blockchain core engine:critical"
    [lucid-session-anchoring]="8085:Session anchoring service:high"
    [lucid-block-manager]="8086:Block manager service:high"
    [lucid-data-chain]="8087:Data chain service:high"
    [lucid-service-mesh]="8500:Service mesh controller:high"
    
    # Phase 3: Application Services
    [lucid-session-pipeline]="8083:Session pipeline manager:high"
    [lucid-session-recorder]="8088:Session recorder service:medium"
    [lucid-session-processor]="8089:Session processor service:medium"
    [lucid-session-storage]="8090:Session storage service:medium"
    [lucid-session-api]="8091:Session API service:medium"
    [lucid-rdp-server-manager]="8092:RDP server manager:medium"
    [lucid-xrdp]="8093:XRDP service:medium"
    [lucid-session-controller]="8094:Session controller:medium"
    [lucid-resource-monitor]="8095:Resource monitor:medium"
    [lucid-node-management]="8096:Node management service:medium"
    
    # Phase 4: Support Services
    [lucid-admin-interface]="8083:Admin interface:low"
    [lucid-tron-client]="8085:TRON client service:low"
    [lucid-payout-router]="8086:TRON payout router:low"
    [lucid-wallet-manager]="8087:Wallet manager:low"
    [lucid-usdt-manager]="8088:USDT manager:low"
    [lucid-trx-staking]="8089:TRX staking service:low"
    [lucid-payment-gateway]="8090:Payment gateway:low"
)

# Utility functions
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

log_header() {
    echo -e "${CYAN}===== $1 =====${NC}"
}

# Check Docker daemon
check_docker_daemon() {
    log_info "Checking Docker daemon..."
    
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    log_success "Docker daemon is running"
    return 0
}

# Check service container status
check_service_container() {
    local service_name="$1"
    
    if docker ps --filter "name=$service_name" --format "{{.Names}}" | grep -q "$service_name"; then
        return 0  # Container is running
    else
        return 1  # Container is not running
    fi
}

# Check service port connectivity
check_service_port() {
    local service_name="$1"
    local service_port="$2"
    
    # Try netcat first
    if command -v nc >/dev/null 2>&1; then
        if nc -z localhost "$service_port" 2>/dev/null; then
            return 0
        fi
    fi
    
    # Try curl as fallback
    if command -v curl >/dev/null 2>&1; then
        if curl -f --connect-timeout 5 "http://localhost:$service_port/health" >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    # Try telnet as last resort
    if command -v telnet >/dev/null 2>&1; then
        if timeout 5 bash -c "</dev/tcp/localhost/$service_port" 2>/dev/null; then
            return 0
        fi
    fi
    
    return 1
}

# Check service health endpoint
check_service_health() {
    local service_name="$1"
    local service_port="$2"
    
    if command -v curl >/dev/null 2>&1; then
        local health_url="http://localhost:$service_port/health"
        local response=$(curl -s --connect-timeout 5 "$health_url" 2>/dev/null || echo "")
        
        if [[ -n "$response" ]]; then
            # Check if response contains "healthy" or "ok"
            if echo "$response" | grep -qi "healthy\|ok\|up"; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Get service status
get_service_status() {
    local service_name="$1"
    local service_info="$2"
    local service_port="${service_info%%:*}"
    local service_description="${service_info#*:}"
    local service_priority="${service_description##*:}"
    local service_desc="${service_description%:*}"
    
    local container_status="unknown"
    local port_status="unknown"
    local health_status="unknown"
    local overall_status="unknown"
    
    # Check container status
    if check_service_container "$service_name"; then
        container_status="running"
    else
        container_status="stopped"
    fi
    
    # Check port status
    if [[ "$container_status" == "running" ]]; then
        if check_service_port "$service_name" "$service_port"; then
            port_status="open"
        else
            port_status="closed"
        fi
        
        # Check health status
        if check_service_health "$service_name" "$service_port"; then
            health_status="healthy"
        else
            health_status="unhealthy"
        fi
    else
        port_status="n/a"
        health_status="n/a"
    fi
    
    # Determine overall status
    if [[ "$container_status" == "running" && "$port_status" == "open" && "$health_status" == "healthy" ]]; then
        overall_status="healthy"
    elif [[ "$container_status" == "running" && "$port_status" == "open" ]]; then
        overall_status="degraded"
    elif [[ "$container_status" == "running" ]]; then
        overall_status="unhealthy"
    else
        overall_status="down"
    fi
    
    echo "$service_name|$service_port|$service_desc|$service_priority|$container_status|$port_status|$health_status|$overall_status"
}

# Verify all services
verify_all_services() {
    log_info "Verifying all Lucid services..."
    
    local results=()
    local healthy_count=0
    local degraded_count=0
    local unhealthy_count=0
    local down_count=0
    local critical_issues=0
    
    for service in "${!ALL_SERVICES[@]}"; do
        local service_info="${ALL_SERVICES[$service]}"
        local result=$(get_service_status "$service" "$service_info")
        results+=("$result")
        
        # Parse result
        IFS='|' read -ra fields <<< "$result"
        local service_name="${fields[0]}"
        local service_port="${fields[1]}"
        local service_desc="${fields[2]}"
        local service_priority="${fields[3]}"
        local container_status="${fields[4]}"
        local port_status="${fields[5]}"
        local health_status="${fields[6]}"
        local overall_status="${fields[7]}"
        
        # Count by status
        case "$overall_status" in
            "healthy")
                ((healthy_count++))
                ;;
            "degraded")
                ((degraded_count++))
                ;;
            "unhealthy")
                ((unhealthy_count++))
                ;;
            "down")
                ((down_count++))
                ;;
        esac
        
        # Count critical issues
        if [[ "$service_priority" == "critical" && "$overall_status" != "healthy" ]]; then
            ((critical_issues++))
        fi
    done
    
    # Display results
    display_verification_results results[@] "$healthy_count" "$degraded_count" "$unhealthy_count" "$down_count" "$critical_issues"
    
    # Return appropriate exit code
    if [[ "$critical_issues" -gt 0 ]]; then
        return 2  # Critical issues
    elif [[ "$down_count" -gt 0 || "$unhealthy_count" -gt 0 ]]; then
        return 1  # Non-critical issues
    else
        return 0  # All healthy
    fi
}

# Display verification results
display_verification_results() {
    local -n results_ref=$1
    local healthy_count=$2
    local degraded_count=$3
    local unhealthy_count=$4
    local down_count=$5
    local critical_issues=$6
    
    log_header "Service Verification Results"
    
    # Summary
    echo -e "${YELLOW}Summary:${NC}"
    echo -e "  ${GREEN}✓${NC} Healthy: $healthy_count"
    echo -e "  ${YELLOW}⚠${NC} Degraded: $degraded_count"
    echo -e "  ${RED}✗${NC} Unhealthy: $unhealthy_count"
    echo -e "  ${RED}●${NC} Down: $down_count"
    echo -e "  ${RED}🚨${NC} Critical Issues: $critical_issues"
    echo
    
    # Detailed results
    if [[ "$OUTPUT_FORMAT" == "table" ]]; then
        display_table_results results_ref
    elif [[ "$OUTPUT_FORMAT" == "json" ]]; then
        display_json_results results_ref
    else
        display_simple_results results_ref
    fi
}

# Display table results
display_table_results() {
    local -n results_ref=$1
    
    printf "%-25s %-8s %-12s %-10s %-10s %-10s %-10s %-10s\n" \
        "Service" "Port" "Priority" "Container" "Port" "Health" "Overall" "Status"
    printf "%-25s %-8s %-12s %-10s %-10s %-10s %-10s %-10s\n" \
        "-------" "----" "--------" "---------" "----" "------" "-------" "------"
    
    for result in "${results_ref[@]}"; do
        IFS='|' read -ra fields <<< "$result"
        local service_name="${fields[0]}"
        local service_port="${fields[1]}"
        local service_priority="${fields[3]}"
        local container_status="${fields[4]}"
        local port_status="${fields[5]}"
        local health_status="${fields[6]}"
        local overall_status="${fields[7]}"
        
        # Color code the overall status
        local status_color=""
        case "$overall_status" in
            "healthy") status_color="${GREEN}" ;;
            "degraded") status_color="${YELLOW}" ;;
            "unhealthy"|"down") status_color="${RED}" ;;
        esac
        
        printf "%-25s %-8s %-12s %-10s %-10s %-10s %-10s %s%-10s%s\n" \
            "$service_name" "$service_port" "$service_priority" \
            "$container_status" "$port_status" "$health_status" \
            "$overall_status" "$status_color" "$overall_status" "${NC}"
    done
}

# Display JSON results
display_json_results() {
    local -n results_ref=$1
    
    echo "{"
    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"environment\": \"$ENVIRONMENT\","
    echo "  \"services\": ["
    
    local first=true
    for result in "${results_ref[@]}"; do
        IFS='|' read -ra fields <<< "$result"
        local service_name="${fields[0]}"
        local service_port="${fields[1]}"
        local service_desc="${fields[2]}"
        local service_priority="${fields[3]}"
        local container_status="${fields[4]}"
        local port_status="${fields[5]}"
        local health_status="${fields[6]}"
        local overall_status="${fields[7]}"
        
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo ","
        fi
        
        echo "    {"
        echo "      \"name\": \"$service_name\","
        echo "      \"port\": $service_port,"
        echo "      \"description\": \"$service_desc\","
        echo "      \"priority\": \"$service_priority\","
        echo "      \"container_status\": \"$container_status\","
        echo "      \"port_status\": \"$port_status\","
        echo "      \"health_status\": \"$health_status\","
        echo "      \"overall_status\": \"$overall_status\""
        echo -n "    }"
    done
    
    echo
    echo "  ]"
    echo "}"
}

# Display simple results
display_simple_results() {
    local -n results_ref=$1
    
    for result in "${results_ref[@]}"; do
        IFS='|' read -ra fields <<< "$result"
        local service_name="${fields[0]}"
        local service_port="${fields[1]}"
        local service_priority="${fields[3]}"
        local overall_status="${fields[7]}"
        
        local status_icon=""
        case "$overall_status" in
            "healthy") status_icon="${GREEN}✓${NC}" ;;
            "degraded") status_icon="${YELLOW}⚠${NC}" ;;
            "unhealthy"|"down") status_icon="${RED}✗${NC}" ;;
        esac
        
        echo -e "$status_icon $service_name:$service_port ($service_priority) - $overall_status"
    done
}

# Check Docker networks
check_docker_networks() {
    log_info "Checking Docker networks..."
    
    local required_networks=("lucid-dev" "lucid-internal" "lucid-blockchain" "lucid-payment")
    local missing_networks=()
    
    for network in "${required_networks[@]}"; do
        if docker network ls --filter "name=$network" --format "{{.Name}}" | grep -q "$network"; then
            log_success "Network $network exists"
        else
            log_warning "Network $network is missing"
            missing_networks+=("$network")
        fi
    done
    
    if [[ ${#missing_networks[@]} -gt 0 ]]; then
        log_error "Missing networks: ${missing_networks[*]}"
        return 1
    fi
    
    log_success "All required networks exist"
    return 0
}

# Check Docker volumes
check_docker_volumes() {
    log_info "Checking Docker volumes..."
    
    local required_volumes=("lucid-mongo-data" "lucid-redis-data" "lucid-elasticsearch-data")
    local missing_volumes=()
    
    for volume in "${required_volumes[@]}"; do
        if docker volume ls --filter "name=$volume" --format "{{.Name}}" | grep -q "$volume"; then
            log_success "Volume $volume exists"
        else
            log_warning "Volume $volume is missing"
            missing_volumes+=("$volume")
        fi
    done
    
    if [[ ${#missing_volumes[@]} -gt 0 ]]; then
        log_warning "Missing volumes: ${missing_volumes[*]} (will be created automatically)"
    fi
    
    log_success "Volume check completed"
    return 0
}

# Generate health report
generate_health_report() {
    log_info "Generating health report..."
    
    local report_file="${LOG_DIR}/health-report-$(date +%Y%m%d-%H%M%S).json"
    
    # Ensure log directory exists
    mkdir -p "$LOG_DIR"
    
    # Generate JSON report
    OUTPUT_FORMAT="json" verify_all_services > "$report_file" 2>/dev/null
    
    if [[ $? -eq 0 ]]; then
        log_success "Health report generated: $report_file"
    else
        log_error "Failed to generate health report"
        return 1
    fi
    
    return 0
}

# Show usage
show_usage() {
    echo "Usage: $0 [environment] [verbose] [output_format]"
    echo
    echo "Environment:"
    echo "  dev       - Development environment (default)"
    echo "  test      - Test environment"
    echo "  prod      - Production environment"
    echo
    echo "Verbose:"
    echo "  true      - Verbose output"
    echo "  false     - Normal output (default)"
    echo
    echo "Output Format:"
    echo "  table     - Table format (default)"
    echo "  json      - JSON format"
    echo "  simple    - Simple format"
    echo
    echo "Exit Codes:"
    echo "  0         - All services healthy"
    echo "  1         - Some services unhealthy (non-critical)"
    echo "  2         - Critical services down"
}

# Main execution
main() {
    log_header "Lucid Service Verification"
    echo -e "${YELLOW}Environment:${NC} $ENVIRONMENT"
    echo -e "${YELLOW}Verbose:${NC} $VERBOSE"
    echo -e "${YELLOW}Output Format:${NC} $OUTPUT_FORMAT"
    echo
    
    # Check Docker daemon
    if ! check_docker_daemon; then
        exit 1
    fi
    
    # Check Docker networks
    check_docker_networks || true
    
    # Check Docker volumes
    check_docker_volumes || true
    
    # Verify all services
    local exit_code=0
    if ! verify_all_services; then
        exit_code=$?
    fi
    
    # Generate health report
    generate_health_report || true
    
    # Summary
    echo
    if [[ "$exit_code" -eq 0 ]]; then
        log_success "All services are healthy"
    elif [[ "$exit_code" -eq 1 ]]; then
        log_warning "Some services are unhealthy (non-critical)"
    else
        log_error "Critical services are down"
    fi
    
    exit $exit_code
}

# Run main function
main "$@"
