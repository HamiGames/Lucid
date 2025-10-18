#!/bin/bash

# Lucid RDP System - Log Query Script
# Step 49: Logging Configuration
# Document: BUILD_REQUIREMENTS_GUIDE.md Step 49

# ======================== Log Query Script =============================

# ---------------------------------- Script Configuration ----------------

# Script metadata
SCRIPT_NAME="query-logs.sh"
SCRIPT_VERSION="1.0.0"
SCRIPT_DESCRIPTION="Lucid RDP System Log Query Script"
SCRIPT_AUTHOR="Lucid RDP Development Team"
SCRIPT_DATE="2025-01-14"

# ---------------------------------- Environment Variables --------------

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Service configurations
ELASTICSEARCH_URL="http://elasticsearch:9200"
PROMETHEUS_URL="http://prometheus:9090"
GRAFANA_URL="http://grafana:3000"
KIBANA_URL="http://kibana:5601"

# Query configurations
DEFAULT_SIZE=100
MAX_SIZE=10000
DEFAULT_TIMEOUT=30
MAX_TIMEOUT=300

# ---------------------------------- Color Codes ------------------------

# ANSI color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# ---------------------------------- Logging Functions ------------------

# Log functions for script output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}

# ---------------------------------- Utility Functions ------------------

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if service is accessible
service_accessible() {
    local host="$1"
    local port="$2"
    timeout 5 bash -c "</dev/tcp/$host/$port" 2>/dev/null
}

# Format JSON output
format_json() {
    if command_exists jq; then
        jq .
    else
        cat
    fi
}

# Format timestamp
format_timestamp() {
    local timestamp="$1"
    if command_exists date; then
        date -d "@$timestamp" 2>/dev/null || date -r "$timestamp" 2>/dev/null || echo "$timestamp"
    else
        echo "$timestamp"
    fi
}

# ---------------------------------- Elasticsearch Functions ------------

# Check Elasticsearch connectivity
check_elasticsearch() {
    log_info "Checking Elasticsearch connectivity..."
    
    if service_accessible "elasticsearch" "9200"; then
        log_success "Elasticsearch is accessible"
        return 0
    else
        log_error "Elasticsearch is not accessible"
        return 1
    fi
}

# Get Elasticsearch cluster health
get_cluster_health() {
    log_info "Getting Elasticsearch cluster health..."
    
    if ! check_elasticsearch; then
        return 1
    fi
    
    local health_response=$(curl -s "$ELASTICSEARCH_URL/_cluster/health" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "$health_response" | format_json
    else
        log_error "Failed to get cluster health"
        return 1
    fi
}

# Get Elasticsearch indices
get_indices() {
    log_info "Getting Elasticsearch indices..."
    
    if ! check_elasticsearch; then
        return 1
    fi
    
    local indices_response=$(curl -s "$ELASTICSEARCH_URL/_cat/indices?v&s=index" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "$indices_response"
    else
        log_error "Failed to get indices"
        return 1
    fi
}

# ---------------------------------- Query Functions --------------------

# Build Elasticsearch query
build_query() {
    local query_type="$1"
    local filters="$2"
    local time_range="$3"
    local size="$4"
    local sort="$5"
    
    local query=""
    
    case "$query_type" in
        "match_all")
            query='{"query": {"match_all": {}}}'
            ;;
        "match")
            query="{\"query\": {\"match\": $filters}}"
            ;;
        "term")
            query="{\"query\": {\"term\": $filters}}"
            ;;
        "terms")
            query="{\"query\": {\"terms\": $filters}}"
            ;;
        "range")
            query="{\"query\": {\"range\": $filters}}"
            ;;
        "bool")
            query="{\"query\": {\"bool\": $filters}}"
            ;;
        "wildcard")
            query="{\"query\": {\"wildcard\": $filters}}"
            ;;
        "regexp")
            query="{\"query\": {\"regexp\": $filters}}"
            ;;
        "exists")
            query="{\"query\": {\"exists\": {\"field\": $filters}}}"
            ;;
        "missing")
            query="{\"query\": {\"bool\": {\"must_not\": {\"exists\": {\"field\": $filters}}}}}"
            ;;
        *)
            log_error "Unknown query type: $query_type"
            return 1
            ;;
    esac
    
    # Add time range filter
    if [[ -n "$time_range" ]]; then
        local start_time=$(echo "$time_range" | cut -d',' -f1)
        local end_time=$(echo "$time_range" | cut -d',' -f2)
        
        query=$(echo "$query" | jq --arg start "$start_time" --arg end "$end_time" \
            '.query.bool = (.query.bool // {}) | .query.bool.filter += [{"range": {"@timestamp": {"gte": $start, "lte": $end}}}]')
    fi
    
    # Add size and sort
    query=$(echo "$query" | jq --argjson size "$size" --arg sort "$sort" \
        '.size = $size | .sort = [($sort | split(",") | map({"@timestamp": {"order": .}}))]')
    
    echo "$query"
}

# Execute Elasticsearch query
execute_query() {
    local index="$1"
    local query="$2"
    local timeout="${3:-$DEFAULT_TIMEOUT}"
    
    log_debug "Executing query on index: $index"
    log_debug "Query: $query"
    
    local response=$(curl -s --max-time "$timeout" \
        -H "Content-Type: application/json" \
        -X POST \
        "$ELASTICSEARCH_URL/$index/_search" \
        -d "$query" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "$response"
    else
        log_error "Query execution failed"
        return 1
    fi
}

# ---------------------------------- Search Functions -------------------

# Search logs by service
search_by_service() {
    local service_name="$1"
    local time_range="$2"
    local size="$3"
    local level="$4"
    
    log_info "Searching logs for service: $service_name"
    
    local filters=""
    if [[ -n "$level" ]]; then
        filters='{"must": [{"term": {"service_name": "'"$service_name"'"}}, {"term": {"level": "'"$level"'"}}]}'
    else
        filters='{"must": [{"term": {"service_name": "'"$service_name"'"}}]}'
    fi
    
    local query=$(build_query "bool" "$filters" "$time_range" "${size:-$DEFAULT_SIZE}" "desc")
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Search failed for service: $service_name"
        return 1
    fi
}

# Search logs by level
search_by_level() {
    local level="$1"
    local time_range="$2"
    local size="$3"
    local service="$4"
    
    log_info "Searching logs by level: $level"
    
    local filters=""
    if [[ -n "$service" ]]; then
        filters='{"must": [{"term": {"level": "'"$level"'"}}, {"term": {"service_name": "'"$service"'"}}]}'
    else
        filters='{"must": [{"term": {"level": "'"$level"'"}}]}'
    fi
    
    local query=$(build_query "bool" "$filters" "$time_range" "${size:-$DEFAULT_SIZE}" "desc")
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Search failed for level: $level"
        return 1
    fi
}

# Search logs by message content
search_by_message() {
    local message="$1"
    local time_range="$2"
    local size="$3"
    local service="$4"
    
    log_info "Searching logs by message: $message"
    
    local filters=""
    if [[ -n "$service" ]]; then
        filters='{"must": [{"match": {"message": "'"$message"'"}}, {"term": {"service_name": "'"$service"'"}}]}'
    else
        filters='{"must": [{"match": {"message": "'"$message"'"}}]}'
    fi
    
    local query=$(build_query "bool" "$filters" "$time_range" "${size:-$DEFAULT_SIZE}" "desc")
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Search failed for message: $message"
        return 1
    fi
}

# Search security logs
search_security_logs() {
    local event_type="$1"
    local severity="$2"
    local time_range="$3"
    local size="$4"
    
    log_info "Searching security logs"
    
    local filters=""
    if [[ -n "$event_type" && -n "$severity" ]]; then
        filters='{"must": [{"term": {"security.event_type": "'"$event_type"'"}}, {"term": {"security.severity": "'"$severity"'"}}]}'
    elif [[ -n "$event_type" ]]; then
        filters='{"must": [{"term": {"security.event_type": "'"$event_type"'"}}]}'
    elif [[ -n "$severity" ]]; then
        filters='{"must": [{"term": {"security.severity": "'"$severity"'"}}]}'
    else
        filters='{"must": [{"exists": {"field": "security"}}]}'
    fi
    
    local query=$(build_query "bool" "$filters" "$time_range" "${size:-$DEFAULT_SIZE}" "desc")
    local response=$(execute_query "lucid-security-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Search failed for security logs"
        return 1
    fi
}

# Search performance logs
search_performance_logs() {
    local metric_name="$1"
    local time_range="$2"
    local size="$3"
    local service="$4"
    
    log_info "Searching performance logs"
    
    local filters=""
    if [[ -n "$metric_name" && -n "$service" ]]; then
        filters='{"must": [{"term": {"performance.metric_name": "'"$metric_name"'"}}, {"term": {"service_name": "'"$service"'"}}]}'
    elif [[ -n "$metric_name" ]]; then
        filters='{"must": [{"term": {"performance.metric_name": "'"$metric_name"'"}}]}'
    elif [[ -n "$service" ]]; then
        filters='{"must": [{"term": {"service_name": "'"$service"'"}}, {"exists": {"field": "performance"}}]}'
    else
        filters='{"must": [{"exists": {"field": "performance"}}]}'
    fi
    
    local query=$(build_query "bool" "$filters" "$time_range" "${size:-$DEFAULT_SIZE}" "desc")
    local response=$(execute_query "lucid-performance-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Search failed for performance logs"
        return 1
    fi
}

# Search logs by time range
search_by_time_range() {
    local start_time="$1"
    local end_time="$2"
    local size="$3"
    local service="$4"
    local level="$5"
    
    log_info "Searching logs from $start_time to $end_time"
    
    local time_range="$start_time,$end_time"
    local filters=""
    
    if [[ -n "$service" && -n "$level" ]]; then
        filters='{"must": [{"term": {"service_name": "'"$service"'"}}, {"term": {"level": "'"$level"'"}}]}'
    elif [[ -n "$service" ]]; then
        filters='{"must": [{"term": {"service_name": "'"$service"'"}}]}'
    elif [[ -n "$level" ]]; then
        filters='{"must": [{"term": {"level": "'"$level"'"}}]}'
    else
        filters='{"must": []}'
    fi
    
    local query=$(build_query "bool" "$filters" "$time_range" "${size:-$DEFAULT_SIZE}" "desc")
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Search failed for time range"
        return 1
    fi
}

# Search logs by IP address
search_by_ip() {
    local ip_address="$1"
    local time_range="$2"
    local size="$3"
    
    log_info "Searching logs by IP address: $ip_address"
    
    local filters='{"must": [{"term": {"ip_address": "'"$ip_address"'"}}]}'
    local query=$(build_query "bool" "$filters" "$time_range" "${size:-$DEFAULT_SIZE}" "desc")
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Search failed for IP address: $ip_address"
        return 1
    fi
}

# Search logs by user
search_by_user() {
    local user_id="$1"
    local time_range="$2"
    local size="$3"
    
    log_info "Searching logs by user: $user_id"
    
    local filters='{"must": [{"term": {"user_id": "'"$user_id"'"}}]}'
    local query=$(build_query "bool" "$filters" "$time_range" "${size:-$DEFAULT_SIZE}" "desc")
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Search failed for user: $user_id"
        return 1
    fi
}

# ---------------------------------- Aggregation Functions -------------

# Get log statistics
get_log_statistics() {
    local time_range="$1"
    local service="$2"
    
    log_info "Getting log statistics"
    
    local filters=""
    if [[ -n "$service" ]]; then
        filters='{"must": [{"term": {"service_name": "'"$service"'"}}]}'
    else
        filters='{"must": []}'
    fi
    
    local aggregation='{
        "aggs": {
            "total_logs": {"value_count": {"field": "_id"}},
            "by_service": {
                "terms": {"field": "service_name", "size": 20}
            },
            "by_level": {
                "terms": {"field": "level", "size": 10}
            },
            "by_hour": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "hour"
                }
            }
        }
    }'
    
    local query=$(echo "$filters" | jq --argjson aggs "$aggregation" '. + {aggs: $aggs, size: 0}')
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Failed to get log statistics"
        return 1
    fi
}

# Get error rate
get_error_rate() {
    local time_range="$1"
    local service="$2"
    
    log_info "Getting error rate"
    
    local filters=""
    if [[ -n "$service" ]]; then
        filters='{"must": [{"term": {"service_name": "'"$service"'"}}]}'
    else
        filters='{"must": []}'
    fi
    
    local aggregation='{
        "aggs": {
            "total_logs": {"value_count": {"field": "_id"}},
            "error_logs": {
                "filter": {"term": {"level": "ERROR"}},
                "aggs": {"count": {"value_count": {"field": "_id"}}}
            }
        }
    }'
    
    local query=$(echo "$filters" | jq --argjson aggs "$aggregation" '. + {aggs: $aggs, size: 0}')
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Failed to get error rate"
        return 1
    fi
}

# Get top errors
get_top_errors() {
    local time_range="$1"
    local service="$2"
    local size="$3"
    
    log_info "Getting top errors"
    
    local filters='{"must": [{"term": {"level": "ERROR"}}]}'
    if [[ -n "$service" ]]; then
        filters='{"must": [{"term": {"level": "ERROR"}}, {"term": {"service_name": "'"$service"'"}}]}'
    fi
    
    local aggregation='{
        "aggs": {
            "top_errors": {
                "terms": {"field": "message.keyword", "size": '"${size:-10}"'}
            }
        }
    }'
    
    local query=$(echo "$filters" | jq --argjson aggs "$aggregation" '. + {aggs: $aggs, size: 0}')
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Failed to get top errors"
        return 1
    fi
}

# ---------------------------------- Export Functions -------------------

# Export logs to CSV
export_to_csv() {
    local query="$1"
    local output_file="$2"
    local fields="$3"
    
    log_info "Exporting logs to CSV: $output_file"
    
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        # Extract hits and convert to CSV
        echo "$response" | jq -r '.hits.hits[] | [.source | to_entries[] | .value] | @csv' > "$output_file"
        log_success "Export completed: $output_file"
    else
        log_error "Export failed"
        return 1
    fi
}

# Export logs to JSON
export_to_json() {
    local query="$1"
    local output_file="$2"
    
    log_info "Exporting logs to JSON: $output_file"
    
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" > "$output_file"
        log_success "Export completed: $output_file"
    else
        log_error "Export failed"
        return 1
    fi
}

# ---------------------------------- Monitoring Functions ---------------

# Get system health
get_system_health() {
    log_info "Getting system health..."
    
    # Check Elasticsearch
    if check_elasticsearch; then
        log_success "Elasticsearch: OK"
    else
        log_error "Elasticsearch: FAILED"
    fi
    
    # Check Prometheus
    if service_accessible "prometheus" "9090"; then
        log_success "Prometheus: OK"
    else
        log_error "Prometheus: FAILED"
    fi
    
    # Check Grafana
    if service_accessible "grafana" "3000"; then
        log_success "Grafana: OK"
    else
        log_error "Grafana: FAILED"
    fi
    
    # Get cluster health
    get_cluster_health
}

# Get query performance
get_query_performance() {
    log_info "Getting query performance metrics..."
    
    local query='{
        "query": {"match_all": {}},
        "size": 0,
        "aggs": {
            "avg_response_time": {
                "avg": {"field": "response_time"}
            },
            "max_response_time": {
                "max": {"field": "response_time"}
            },
            "min_response_time": {
                "min": {"field": "response_time"}
            }
        }
    }'
    
    local response=$(execute_query "lucid-logs" "$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | format_json
    else
        log_error "Failed to get query performance"
        return 1
    fi
}

# ---------------------------------- Main Functions --------------------

# Interactive query mode
interactive_mode() {
    log_info "Starting interactive query mode..."
    
    while true; do
        echo -e "\n${CYAN}Lucid Log Query Interface${NC}"
        echo "1. Search by service"
        echo "2. Search by level"
        echo "3. Search by message"
        echo "4. Search security logs"
        echo "5. Search performance logs"
        echo "6. Search by time range"
        echo "7. Get statistics"
        echo "8. Get error rate"
        echo "9. Get top errors"
        echo "10. System health"
        echo "11. Exit"
        
        read -p "Select option (1-11): " choice
        
        case $choice in
            1)
                read -p "Enter service name: " service
                read -p "Enter time range (start,end) or press Enter for all: " time_range
                read -p "Enter size (default: 100): " size
                search_by_service "$service" "$time_range" "${size:-100}"
                ;;
            2)
                read -p "Enter level (ERROR, WARNING, INFO, DEBUG): " level
                read -p "Enter time range (start,end) or press Enter for all: " time_range
                read -p "Enter size (default: 100): " size
                search_by_level "$level" "$time_range" "${size:-100}"
                ;;
            3)
                read -p "Enter message content: " message
                read -p "Enter time range (start,end) or press Enter for all: " time_range
                read -p "Enter size (default: 100): " size
                search_by_message "$message" "$time_range" "${size:-100}"
                ;;
            4)
                read -p "Enter event type (optional): " event_type
                read -p "Enter severity (optional): " severity
                read -p "Enter time range (start,end) or press Enter for all: " time_range
                read -p "Enter size (default: 100): " size
                search_security_logs "$event_type" "$severity" "$time_range" "${size:-100}"
                ;;
            5)
                read -p "Enter metric name (optional): " metric_name
                read -p "Enter time range (start,end) or press Enter for all: " time_range
                read -p "Enter size (default: 100): " size
                search_performance_logs "$metric_name" "$time_range" "${size:-100}"
                ;;
            6)
                read -p "Enter start time (ISO format): " start_time
                read -p "Enter end time (ISO format): " end_time
                read -p "Enter size (default: 100): " size
                search_by_time_range "$start_time" "$end_time" "${size:-100}"
                ;;
            7)
                read -p "Enter time range (start,end) or press Enter for all: " time_range
                read -p "Enter service (optional): " service
                get_log_statistics "$time_range" "$service"
                ;;
            8)
                read -p "Enter time range (start,end) or press Enter for all: " time_range
                read -p "Enter service (optional): " service
                get_error_rate "$time_range" "$service"
                ;;
            9)
                read -p "Enter time range (start,end) or press Enter for all: " time_range
                read -p "Enter service (optional): " service
                read -p "Enter size (default: 10): " size
                get_top_errors "$time_range" "$service" "${size:-10}"
                ;;
            10)
                get_system_health
                ;;
            11)
                log_info "Exiting interactive mode"
                break
                ;;
            *)
                log_error "Invalid option"
                ;;
        esac
    done
}

# ---------------------------------- Usage Function ---------------------

# Display usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS] COMMAND [ARGUMENTS]

Lucid RDP System Log Query Script

COMMANDS:
    search-service SERVICE     Search logs by service name
    search-level LEVEL         Search logs by level (ERROR, WARNING, INFO, DEBUG)
    search-message MESSAGE     Search logs by message content
    search-security           Search security logs
    search-performance         Search performance logs
    search-time START END     Search logs by time range
    search-ip IP              Search logs by IP address
    search-user USER         Search logs by user ID
    stats [SERVICE]           Get log statistics
    error-rate [SERVICE]      Get error rate
    top-errors [SERVICE]      Get top errors
    health                    Check system health
    interactive               Start interactive mode
    export-csv FILE           Export logs to CSV
    export-json FILE          Export logs to JSON

OPTIONS:
    -h, --help                Show this help message
    -v, --verbose             Enable verbose output
    -d, --debug               Enable debug output
    --service SERVICE         Specify service name
    --level LEVEL             Specify log level
    --time-range START,END   Specify time range
    --size SIZE               Specify result size (default: 100)
    --timeout TIMEOUT         Specify query timeout (default: 30)
    --format FORMAT           Specify output format (json, table, csv)
    --fields FIELDS           Specify fields for CSV export

EXAMPLES:
    $0 search-service api-gateway                    # Search API Gateway logs
    $0 search-level ERROR --size 50                  # Search error logs (50 results)
    $0 search-message "authentication failed"        # Search by message
    $0 search-time "2025-01-01T00:00:00Z,2025-01-02T00:00:00Z"  # Search by time
    $0 stats --service blockchain                    # Get blockchain statistics
    $0 error-rate --time-range "2025-01-01,2025-01-02"  # Get error rate for date range
    $0 top-errors --size 20                          # Get top 20 errors
    $0 health                                         # Check system health
    $0 interactive                                    # Start interactive mode
    $0 export-csv logs.csv --fields "timestamp,service_name,level,message"  # Export to CSV

TIME FORMATS:
    ISO 8601: 2025-01-14T10:30:00Z
    Relative: now-1h, now-1d, now-7d
    Date: 2025-01-14

SERVICE NAMES:
    api-gateway, blockchain, sessions, rdp, nodes, admin, tron-payment, auth, database, service-mesh

LOG LEVELS:
    ERROR, WARNING, INFO, DEBUG, FATAL, CRITICAL

OUTPUT FORMATS:
    json    - JSON format (default)
    table   - Table format
    csv     - CSV format

EOF
}

# ---------------------------------- Main Script ------------------------

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        --service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --time-range)
            TIME_RANGE="$2"
            shift 2
            ;;
        --size)
            RESULT_SIZE="$2"
            shift 2
            ;;
        --timeout)
            QUERY_TIMEOUT="$2"
            shift 2
            ;;
        --format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --fields)
            CSV_FIELDS="$2"
            shift 2
            ;;
        search-service)
            COMMAND="search-service"
            SERVICE_NAME="$2"
            shift 2
            ;;
        search-level)
            COMMAND="search-level"
            LOG_LEVEL="$2"
            shift 2
            ;;
        search-message)
            COMMAND="search-message"
            MESSAGE="$2"
            shift 2
            ;;
        search-security)
            COMMAND="search-security"
            shift
            ;;
        search-performance)
            COMMAND="search-performance"
            shift
            ;;
        search-time)
            COMMAND="search-time"
            START_TIME="$2"
            END_TIME="$3"
            shift 3
            ;;
        search-ip)
            COMMAND="search-ip"
            IP_ADDRESS="$2"
            shift 2
            ;;
        search-user)
            COMMAND="search-user"
            USER_ID="$2"
            shift 2
            ;;
        stats)
            COMMAND="stats"
            shift
            ;;
        error-rate)
            COMMAND="error-rate"
            shift
            ;;
        top-errors)
            COMMAND="top-errors"
            shift
            ;;
        health)
            COMMAND="health"
            shift
            ;;
        interactive)
            COMMAND="interactive"
            shift
            ;;
        export-csv)
            COMMAND="export-csv"
            OUTPUT_FILE="$2"
            shift 2
            ;;
        export-json)
            COMMAND="export-json"
            OUTPUT_FILE="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Execute command
case $COMMAND in
    search-service)
        if [[ -n "$SERVICE_NAME" ]]; then
            search_by_service "$SERVICE_NAME" "$TIME_RANGE" "${RESULT_SIZE:-$DEFAULT_SIZE}" "$LOG_LEVEL"
        else
            log_error "Service name required for search-service command"
            exit 1
        fi
        ;;
    search-level)
        if [[ -n "$LOG_LEVEL" ]]; then
            search_by_level "$LOG_LEVEL" "$TIME_RANGE" "${RESULT_SIZE:-$DEFAULT_SIZE}" "$SERVICE_NAME"
        else
            log_error "Log level required for search-level command"
            exit 1
        fi
        ;;
    search-message)
        if [[ -n "$MESSAGE" ]]; then
            search_by_message "$MESSAGE" "$TIME_RANGE" "${RESULT_SIZE:-$DEFAULT_SIZE}" "$SERVICE_NAME"
        else
            log_error "Message required for search-message command"
            exit 1
        fi
        ;;
    search-security)
        search_security_logs "" "" "$TIME_RANGE" "${RESULT_SIZE:-$DEFAULT_SIZE}"
        ;;
    search-performance)
        search_performance_logs "" "$TIME_RANGE" "${RESULT_SIZE:-$DEFAULT_SIZE}" "$SERVICE_NAME"
        ;;
    search-time)
        if [[ -n "$START_TIME" && -n "$END_TIME" ]]; then
            search_by_time_range "$START_TIME" "$END_TIME" "${RESULT_SIZE:-$DEFAULT_SIZE}" "$SERVICE_NAME" "$LOG_LEVEL"
        else
            log_error "Start time and end time required for search-time command"
            exit 1
        fi
        ;;
    search-ip)
        if [[ -n "$IP_ADDRESS" ]]; then
            search_by_ip "$IP_ADDRESS" "$TIME_RANGE" "${RESULT_SIZE:-$DEFAULT_SIZE}"
        else
            log_error "IP address required for search-ip command"
            exit 1
        fi
        ;;
    search-user)
        if [[ -n "$USER_ID" ]]; then
            search_by_user "$USER_ID" "$TIME_RANGE" "${RESULT_SIZE:-$DEFAULT_SIZE}"
        else
            log_error "User ID required for search-user command"
            exit 1
        fi
        ;;
    stats)
        get_log_statistics "$TIME_RANGE" "$SERVICE_NAME"
        ;;
    error-rate)
        get_error_rate "$TIME_RANGE" "$SERVICE_NAME"
        ;;
    top-errors)
        get_top_errors "$TIME_RANGE" "$SERVICE_NAME" "${RESULT_SIZE:-10}"
        ;;
    health)
        get_system_health
        ;;
    interactive)
        interactive_mode
        ;;
    export-csv)
        if [[ -n "$OUTPUT_FILE" ]]; then
            # Build query based on parameters
            local filters=""
            if [[ -n "$SERVICE_NAME" ]]; then
                filters='{"must": [{"term": {"service_name": "'"$SERVICE_NAME"'"}}]}'
            else
                filters='{"must": []}'
            fi
            local query=$(build_query "bool" "$filters" "$TIME_RANGE" "${RESULT_SIZE:-$DEFAULT_SIZE}" "desc")
            export_to_csv "$query" "$OUTPUT_FILE" "$CSV_FIELDS"
        else
            log_error "Output file required for export-csv command"
            exit 1
        fi
        ;;
    export-json)
        if [[ -n "$OUTPUT_FILE" ]]; then
            # Build query based on parameters
            local filters=""
            if [[ -n "$SERVICE_NAME" ]]; then
                filters='{"must": [{"term": {"service_name": "'"$SERVICE_NAME"'"}}]}'
            else
                filters='{"must": []}'
            fi
            local query=$(build_query "bool" "$filters" "$TIME_RANGE" "${RESULT_SIZE:-$DEFAULT_SIZE}" "desc")
            export_to_json "$query" "$OUTPUT_FILE"
        else
            log_error "Output file required for export-json command"
            exit 1
        fi
        ;;
    *)
        log_error "No command specified"
        usage
        exit 1
        ;;
esac

# ---------------------------------- End of Script ----------------------

log_info "Script execution completed"
exit 0
