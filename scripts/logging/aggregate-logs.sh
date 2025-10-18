#!/bin/bash

# Lucid RDP System - Log Aggregation Script
# Step 49: Logging Configuration
# Document: BUILD_REQUIREMENTS_GUIDE.md Step 49

# ======================== Log Aggregation Script ========================

# ---------------------------------- Script Configuration ----------------

# Script metadata
SCRIPT_NAME="aggregate-logs.sh"
SCRIPT_VERSION="1.0.0"
SCRIPT_DESCRIPTION="Lucid RDP System Log Aggregation Script"
SCRIPT_AUTHOR="Lucid RDP Development Team"
SCRIPT_DATE="2025-01-14"

# ---------------------------------- Environment Variables --------------

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Log directories
LOG_BASE_DIR="/opt/lucid/logs"
FLUENTD_CONFIG_DIR="$PROJECT_ROOT/configs/logging"
FLUENTD_DATA_DIR="/opt/lucid/fluentd"
ELASTICSEARCH_URL="http://elasticsearch:9200"
PROMETHEUS_URL="http://prometheus:9090"
GRAFANA_URL="http://grafana:3000"

# Service configurations
SERVICES=(
    "api-gateway"
    "blockchain"
    "sessions"
    "rdp"
    "nodes"
    "admin"
    "tron-payment"
    "auth"
    "database"
    "service-mesh"
    "security"
    "performance"
    "metrics"
    "errors"
    "debug"
    "monitoring"
    "network"
)

# Log types
LOG_TYPES=(
    "application"
    "error"
    "debug"
    "security"
    "audit"
    "performance"
    "metrics"
    "access"
    "system"
    "docker"
)

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

# Check if service is running
service_running() {
    local service_name="$1"
    if command_exists docker; then
        docker ps --format "table {{.Names}}" | grep -q "^${service_name}$"
    else
        systemctl is-active --quiet "$service_name"
    fi
}

# Check if port is open
port_open() {
    local host="$1"
    local port="$2"
    timeout 5 bash -c "</dev/tcp/$host/$port" 2>/dev/null
}

# Wait for service to be ready
wait_for_service() {
    local service_name="$1"
    local host="$2"
    local port="$3"
    local max_attempts=30
    local attempt=1

    log_info "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if port_open "$host" "$port"; then
            log_success "$service_name is ready"
            return 0
        fi
        
        log_debug "Attempt $attempt/$max_attempts: $service_name not ready yet"
        sleep 2
        ((attempt++))
    done
    
    log_error "$service_name failed to start within timeout"
    return 1
}

# ---------------------------------- Directory Functions ---------------

# Create directory structure
create_directories() {
    log_info "Creating log aggregation directory structure..."
    
    # Create base directories
    mkdir -p "$LOG_BASE_DIR"/{api-gateway,blockchain,sessions,rdp,nodes,admin,tron-payment,auth,database,service-mesh,security,performance,metrics,errors,debug,monitoring,network,backup}
    
    # Create Fluentd directories
    mkdir -p "$FLUENTD_DATA_DIR"/{buffer,storage,pos}
    mkdir -p "$FLUENTD_DATA_DIR"/buffer/{elasticsearch,security,performance,security-file,audit-file}
    mkdir -p "$FLUENTD_DATA_DIR"/storage/{api-gateway,blockchain,sessions,rdp,nodes,admin,tron-payment,auth,database,service-mesh,security,performance,metrics,errors,debug,prometheus,grafana,tor,tunnels,system,docker}
    mkdir -p "$FLUENTD_DATA_DIR"/pos
    
    # Create service-specific directories
    for service in "${SERVICES[@]}"; do
        mkdir -p "$LOG_BASE_DIR/$service"
        mkdir -p "$FLUENTD_DATA_DIR/storage/$service"
    done
    
    # Create log type directories
    for log_type in "${LOG_TYPES[@]}"; do
        mkdir -p "$LOG_BASE_DIR/$log_type"
    done
    
    # Set proper permissions
    chown -R 65532:65532 "$LOG_BASE_DIR" 2>/dev/null || true
    chown -R 65532:65532 "$FLUENTD_DATA_DIR" 2>/dev/null || true
    chmod -R 755 "$LOG_BASE_DIR"
    chmod -R 755 "$FLUENTD_DATA_DIR"
    
    log_success "Directory structure created successfully"
}

# ---------------------------------- Service Functions ------------------

# Start Fluentd service
start_fluentd() {
    log_info "Starting Fluentd log aggregation service..."
    
    # Check if Fluentd is already running
    if service_running "lucid-fluentd"; then
        log_warning "Fluentd is already running"
        return 0
    fi
    
    # Start Fluentd container
    if command_exists docker; then
        docker run -d \
            --name lucid-fluentd \
            --network lucid-network \
            -p 24224:24224 \
            -p 9880:9880 \
            -p 24220:24220 \
            -v "$LOG_BASE_DIR:/opt/lucid/logs:ro" \
            -v "$FLUENTD_DATA_DIR:/opt/lucid/fluentd" \
            -v "$FLUENTD_CONFIG_DIR/fluentd.conf:/fluentd/etc/fluent.conf:ro" \
            -e FLUENTD_CONF=fluent.conf \
            --restart unless-stopped \
            fluent/fluentd:v1.16-debian-1
    else
        # Start Fluentd as system service
        systemctl start fluentd
        systemctl enable fluentd
    fi
    
    # Wait for Fluentd to be ready
    wait_for_service "Fluentd" "localhost" "24224"
    
    log_success "Fluentd started successfully"
}

# Start Elasticsearch service
start_elasticsearch() {
    log_info "Starting Elasticsearch for log storage..."
    
    # Check if Elasticsearch is already running
    if service_running "lucid-elasticsearch"; then
        log_warning "Elasticsearch is already running"
        return 0
    fi
    
    # Start Elasticsearch container
    if command_exists docker; then
        docker run -d \
            --name lucid-elasticsearch \
            --network lucid-network \
            -p 9200:9200 \
            -p 9300:9300 \
            -v elasticsearch-data:/usr/share/elasticsearch/data \
            -e "discovery.type=single-node" \
            -e "xpack.security.enabled=false" \
            -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
            --restart unless-stopped \
            elasticsearch:8.11.0
    else
        # Start Elasticsearch as system service
        systemctl start elasticsearch
        systemctl enable elasticsearch
    fi
    
    # Wait for Elasticsearch to be ready
    wait_for_service "Elasticsearch" "localhost" "9200"
    
    # Apply Elasticsearch configuration
    apply_elasticsearch_config
    
    log_success "Elasticsearch started successfully"
}

# Apply Elasticsearch configuration
apply_elasticsearch_config() {
    log_info "Applying Elasticsearch logging configuration..."
    
    # Wait for Elasticsearch to be fully ready
    sleep 10
    
    # Apply index templates and configurations
    if command_exists curl; then
        # Apply main logs index template
        curl -X PUT "$ELASTICSEARCH_URL/_index_template/lucid-logs-template" \
            -H "Content-Type: application/json" \
            -d @<(cat <<EOF
{
  "index_patterns": ["lucid-logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0,
      "index.refresh_interval": "5s"
    },
    "mappings": {
      "properties": {
        "@timestamp": {"type": "date"},
        "service_name": {"type": "keyword"},
        "log_type": {"type": "keyword"},
        "level": {"type": "keyword"},
        "message": {"type": "text"},
        "hostname": {"type": "keyword"},
        "environment": {"type": "keyword"}
      }
    }
  }
}
EOF
        )
        
        # Apply security logs index template
        curl -X PUT "$ELASTICSEARCH_URL/_index_template/lucid-security-logs-template" \
            -H "Content-Type: application/json" \
            -d @<(cat <<EOF
{
  "index_patterns": ["lucid-security-logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0,
      "index.refresh_interval": "1s"
    },
    "mappings": {
      "properties": {
        "@timestamp": {"type": "date"},
        "service_name": {"type": "keyword"},
        "log_type": {"type": "keyword"},
        "level": {"type": "keyword"},
        "message": {"type": "text"},
        "security": {
          "properties": {
            "event_type": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "source_ip": {"type": "ip"}
          }
        }
      }
    }
  }
}
EOF
        )
        
        # Create initial indices
        curl -X PUT "$ELASTICSEARCH_URL/lucid-logs-000001" \
            -H "Content-Type: application/json" \
            -d '{"aliases": {"lucid-logs": {"is_write_index": true}}}'
        
        curl -X PUT "$ELASTICSEARCH_URL/lucid-security-logs-000001" \
            -H "Content-Type: application/json" \
            -d '{"aliases": {"lucid-security-logs": {"is_write_index": true}}}'
        
        log_success "Elasticsearch configuration applied successfully"
    else
        log_error "curl not found, cannot apply Elasticsearch configuration"
        return 1
    fi
}

# Start Prometheus service
start_prometheus() {
    log_info "Starting Prometheus for metrics collection..."
    
    # Check if Prometheus is already running
    if service_running "lucid-prometheus"; then
        log_warning "Prometheus is already running"
        return 0
    fi
    
    # Start Prometheus container
    if command_exists docker; then
        docker run -d \
            --name lucid-prometheus \
            --network lucid-network \
            -p 9090:9090 \
            -v prometheus-data:/prometheus \
            -v "$PROJECT_ROOT/ops/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
            --restart unless-stopped \
            prom/prometheus:latest
    else
        # Start Prometheus as system service
        systemctl start prometheus
        systemctl enable prometheus
    fi
    
    # Wait for Prometheus to be ready
    wait_for_service "Prometheus" "localhost" "9090"
    
    log_success "Prometheus started successfully"
}

# Start Grafana service
start_grafana() {
    log_info "Starting Grafana for log visualization..."
    
    # Check if Grafana is already running
    if service_running "lucid-grafana"; then
        log_warning "Grafana is already running"
        return 0
    fi
    
    # Start Grafana container
    if command_exists docker; then
        docker run -d \
            --name lucid-grafana \
            --network lucid-network \
            -p 3000:3000 \
            -v grafana-data:/var/lib/grafana \
            -e "GF_SECURITY_ADMIN_PASSWORD=lucid_admin_password" \
            --restart unless-stopped \
            grafana/grafana:latest
    else
        # Start Grafana as system service
        systemctl start grafana-server
        systemctl enable grafana-server
    fi
    
    # Wait for Grafana to be ready
    wait_for_service "Grafana" "localhost" "3000"
    
    log_success "Grafana started successfully"
}

# ---------------------------------- Log Processing Functions -----------

# Process service logs
process_service_logs() {
    local service_name="$1"
    local log_dir="$LOG_BASE_DIR/$service_name"
    
    log_info "Processing logs for service: $service_name"
    
    if [ ! -d "$log_dir" ]; then
        log_warning "Log directory not found: $log_dir"
        return 1
    fi
    
    # Find all log files
    local log_files=($(find "$log_dir" -name "*.log" -type f 2>/dev/null))
    
    if [ ${#log_files[@]} -eq 0 ]; then
        log_warning "No log files found for service: $service_name"
        return 1
    fi
    
    # Process each log file
    for log_file in "${log_files[@]}"; do
        log_debug "Processing log file: $log_file"
        
        # Check if file is readable
        if [ ! -r "$log_file" ]; then
            log_warning "Cannot read log file: $log_file"
            continue
        fi
        
        # Get file size
        local file_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo "0")
        
        if [ "$file_size" -eq 0 ]; then
            log_debug "Log file is empty: $log_file"
            continue
        fi
        
        # Process log file based on type
        case "$log_file" in
            *error*|*error.log)
                process_error_logs "$log_file" "$service_name"
                ;;
            *debug*|*debug.log)
                process_debug_logs "$log_file" "$service_name"
                ;;
            *security*|*security.log)
                process_security_logs "$log_file" "$service_name"
                ;;
            *performance*|*performance.log)
                process_performance_logs "$log_file" "$service_name"
                ;;
            *)
                process_application_logs "$log_file" "$service_name"
                ;;
        esac
    done
    
    log_success "Processed logs for service: $service_name"
}

# Process application logs
process_application_logs() {
    local log_file="$1"
    local service_name="$2"
    
    log_debug "Processing application logs: $log_file"
    
    # Extract structured data from log file
    while IFS= read -r line; do
        # Skip empty lines
        [ -z "$line" ] && continue
        
        # Parse JSON logs
        if echo "$line" | jq . >/dev/null 2>&1; then
            # Already JSON formatted
            echo "$line" | jq --arg service "$service_name" '. + {service_name: $service, log_type: "application"}'
        else
            # Convert to JSON format
            jq -n \
                --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
                --arg service "$service_name" \
                --arg message "$line" \
                --arg level "INFO" \
                '{timestamp: $timestamp, service_name: $service, log_type: "application", level: $level, message: $message}'
        fi
    done < "$log_file"
}

# Process error logs
process_error_logs() {
    local log_file="$1"
    local service_name="$2"
    
    log_debug "Processing error logs: $log_file"
    
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        
        if echo "$line" | jq . >/dev/null 2>&1; then
            echo "$line" | jq --arg service "$service_name" '. + {service_name: $service, log_type: "error"}'
        else
            jq -n \
                --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
                --arg service "$service_name" \
                --arg message "$line" \
                --arg level "ERROR" \
                '{timestamp: $timestamp, service_name: $service, log_type: "error", level: $level, message: $message}'
        fi
    done < "$log_file"
}

# Process security logs
process_security_logs() {
    local log_file="$1"
    local service_name="$2"
    
    log_debug "Processing security logs: $log_file"
    
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        
        if echo "$line" | jq . >/dev/null 2>&1; then
            echo "$line" | jq --arg service "$service_name" '. + {service_name: $service, log_type: "security"}'
        else
            jq -n \
                --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
                --arg service "$service_name" \
                --arg message "$line" \
                --arg level "WARNING" \
                '{timestamp: $timestamp, service_name: $service, log_type: "security", level: $level, message: $message}'
        fi
    done < "$log_file"
}

# Process performance logs
process_performance_logs() {
    local log_file="$1"
    local service_name="$2"
    
    log_debug "Processing performance logs: $log_file"
    
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        
        if echo "$line" | jq . >/dev/null 2>&1; then
            echo "$line" | jq --arg service "$service_name" '. + {service_name: $service, log_type: "performance"}'
        else
            jq -n \
                --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
                --arg service "$service_name" \
                --arg message "$line" \
                --arg level "INFO" \
                '{timestamp: $timestamp, service_name: $service, log_type: "performance", level: $level, message: $message}'
        fi
    done < "$log_file"
}

# Process debug logs
process_debug_logs() {
    local log_file="$1"
    local service_name="$2"
    
    log_debug "Processing debug logs: $log_file"
    
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        
        if echo "$line" | jq . >/dev/null 2>&1; then
            echo "$line" | jq --arg service "$service_name" '. + {service_name: $service, log_type: "debug"}'
        else
            jq -n \
                --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
                --arg service "$service_name" \
                --arg message "$line" \
                --arg level "DEBUG" \
                '{timestamp: $timestamp, service_name: $service, log_type: "debug", level: $level, message: $message}'
        fi
    done < "$log_file"
}

# ---------------------------------- Aggregation Functions -------------

# Aggregate all service logs
aggregate_all_logs() {
    log_info "Starting log aggregation for all services..."
    
    local total_services=${#SERVICES[@]}
    local processed_services=0
    local failed_services=0
    
    for service in "${SERVICES[@]}"; do
        log_info "Processing service $((processed_services + 1))/$total_services: $service"
        
        if process_service_logs "$service"; then
            ((processed_services++))
            log_success "Successfully processed logs for: $service"
        else
            ((failed_services++))
            log_error "Failed to process logs for: $service"
        fi
    done
    
    log_info "Log aggregation completed"
    log_info "Processed services: $processed_services"
    log_info "Failed services: $failed_services"
    
    if [ $failed_services -gt 0 ]; then
        log_warning "Some services failed to process logs"
        return 1
    fi
    
    log_success "All services processed successfully"
    return 0
}

# Aggregate logs by time range
aggregate_logs_by_time() {
    local start_time="$1"
    local end_time="$2"
    
    log_info "Aggregating logs from $start_time to $end_time"
    
    # Find log files within time range
    local log_files=($(find "$LOG_BASE_DIR" -name "*.log" -type f -newermt "$start_time" ! -newermt "$end_time" 2>/dev/null))
    
    if [ ${#log_files[@]} -eq 0 ]; then
        log_warning "No log files found in time range"
        return 1
    fi
    
    log_info "Found ${#log_files[@]} log files in time range"
    
    # Process each log file
    for log_file in "${log_files[@]}"; do
        local service_name=$(basename "$(dirname "$log_file")")
        process_service_logs "$service_name"
    done
    
    log_success "Time range aggregation completed"
}

# Aggregate logs by service
aggregate_logs_by_service() {
    local service_name="$1"
    
    log_info "Aggregating logs for service: $service_name"
    
    if process_service_logs "$service_name"; then
        log_success "Successfully aggregated logs for: $service_name"
        return 0
    else
        log_error "Failed to aggregate logs for: $service_name"
        return 1
    fi
}

# Aggregate logs by type
aggregate_logs_by_type() {
    local log_type="$1"
    
    log_info "Aggregating logs of type: $log_type"
    
    # Find log files by type
    local log_files=($(find "$LOG_BASE_DIR" -name "*$log_type*.log" -type f 2>/dev/null))
    
    if [ ${#log_files[@]} -eq 0 ]; then
        log_warning "No log files found for type: $log_type"
        return 1
    fi
    
    log_info "Found ${#log_files[@]} log files of type: $log_type"
    
    # Process each log file
    for log_file in "${log_files[@]}"; do
        local service_name=$(basename "$(dirname "$log_file")")
        process_service_logs "$service_name"
    done
    
    log_success "Log type aggregation completed"
}

# ---------------------------------- Health Check Functions ------------

# Check log aggregation health
check_aggregation_health() {
    log_info "Checking log aggregation health..."
    
    local health_status=0
    
    # Check Fluentd
    if service_running "lucid-fluentd"; then
        log_success "Fluentd is running"
    else
        log_error "Fluentd is not running"
        health_status=1
    fi
    
    # Check Elasticsearch
    if port_open "localhost" "9200"; then
        log_success "Elasticsearch is accessible"
    else
        log_error "Elasticsearch is not accessible"
        health_status=1
    fi
    
    # Check Prometheus
    if port_open "localhost" "9090"; then
        log_success "Prometheus is accessible"
    else
        log_error "Prometheus is not accessible"
        health_status=1
    fi
    
    # Check Grafana
    if port_open "localhost" "3000"; then
        log_success "Grafana is accessible"
    else
        log_error "Grafana is not accessible"
        health_status=1
    fi
    
    # Check log directories
    for service in "${SERVICES[@]}"; do
        if [ -d "$LOG_BASE_DIR/$service" ]; then
            log_debug "Log directory exists for service: $service"
        else
            log_warning "Log directory missing for service: $service"
        fi
    done
    
    if [ $health_status -eq 0 ]; then
        log_success "Log aggregation health check passed"
    else
        log_error "Log aggregation health check failed"
    fi
    
    return $health_status
}

# ---------------------------------- Statistics Functions --------------

# Get aggregation statistics
get_aggregation_stats() {
    log_info "Getting log aggregation statistics..."
    
    local total_log_files=0
    local total_log_size=0
    local service_stats=()
    
    # Count log files and size by service
    for service in "${SERVICES[@]}"; do
        local service_dir="$LOG_BASE_DIR/$service"
        if [ -d "$service_dir" ]; then
            local file_count=$(find "$service_dir" -name "*.log" -type f | wc -l)
            local dir_size=$(du -sb "$service_dir" 2>/dev/null | cut -f1)
            
            total_log_files=$((total_log_files + file_count))
            total_log_size=$((total_log_size + dir_size))
            
            service_stats+=("$service:$file_count:$dir_size")
        fi
    done
    
    # Display statistics
    log_info "Log Aggregation Statistics:"
    log_info "Total log files: $total_log_files"
    log_info "Total log size: $(numfmt --to=iec $total_log_size)"
    
    log_info "Service breakdown:"
    for stat in "${service_stats[@]}"; do
        IFS=':' read -r service files size <<< "$stat"
        log_info "  $service: $files files, $(numfmt --to=iec $size)"
    done
    
    # Check Elasticsearch indices
    if port_open "localhost" "9200"; then
        log_info "Elasticsearch indices:"
        curl -s "$ELASTICSEARCH_URL/_cat/indices?v" 2>/dev/null || log_warning "Cannot retrieve Elasticsearch indices"
    fi
}

# ---------------------------------- Cleanup Functions -----------------

# Cleanup old logs
cleanup_old_logs() {
    local retention_days="${1:-30}"
    
    log_info "Cleaning up logs older than $retention_days days..."
    
    local cleaned_files=0
    local cleaned_size=0
    
    # Clean up log files
    for service in "${SERVICES[@]}"; do
        local service_dir="$LOG_BASE_DIR/$service"
        if [ -d "$service_dir" ]; then
            # Find and remove old log files
            while IFS= read -r -d '' file; do
                local file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
                rm -f "$file"
                ((cleaned_files++))
                cleaned_size=$((cleaned_size + file_size))
            done < <(find "$service_dir" -name "*.log.*" -type f -mtime +$retention_days -print0 2>/dev/null)
        fi
    done
    
    log_info "Cleanup completed:"
    log_info "  Files removed: $cleaned_files"
    log_info "  Space freed: $(numfmt --to=iec $cleaned_size)"
}

# ---------------------------------- Main Functions --------------------

# Initialize log aggregation
initialize_aggregation() {
    log_info "Initializing log aggregation system..."
    
    # Create directories
    create_directories
    
    # Start services
    start_elasticsearch
    start_fluentd
    start_prometheus
    start_grafana
    
    # Check health
    check_aggregation_health
    
    log_success "Log aggregation system initialized"
}

# Start log aggregation
start_aggregation() {
    log_info "Starting log aggregation..."
    
    # Start services if not running
    if ! service_running "lucid-fluentd"; then
        start_fluentd
    fi
    
    if ! service_running "lucid-elasticsearch"; then
        start_elasticsearch
    fi
    
    # Start aggregation process
    aggregate_all_logs
    
    log_success "Log aggregation started"
}

# Stop log aggregation
stop_aggregation() {
    log_info "Stopping log aggregation..."
    
    # Stop Fluentd
    if service_running "lucid-fluentd"; then
        if command_exists docker; then
            docker stop lucid-fluentd
        else
            systemctl stop fluentd
        fi
        log_success "Fluentd stopped"
    fi
    
    log_success "Log aggregation stopped"
}

# Restart log aggregation
restart_aggregation() {
    log_info "Restarting log aggregation..."
    
    stop_aggregation
    sleep 5
    start_aggregation
    
    log_success "Log aggregation restarted"
}

# ---------------------------------- Usage Function ---------------------

# Display usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS] COMMAND

Lucid RDP System Log Aggregation Script

COMMANDS:
    init                    Initialize log aggregation system
    start                   Start log aggregation
    stop                    Stop log aggregation
    restart                 Restart log aggregation
    status                  Check aggregation status
    stats                   Show aggregation statistics
    aggregate [SERVICE]     Aggregate logs for specific service
    aggregate-all           Aggregate logs for all services
    aggregate-time START END Aggregate logs by time range
    aggregate-type TYPE     Aggregate logs by type
    cleanup [DAYS]          Cleanup old logs (default: 30 days)
    health                  Check aggregation health

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose            Enable verbose output
    -d, --debug             Enable debug output
    --service SERVICE       Specify service name
    --type TYPE             Specify log type
    --start-time TIME       Start time for time range
    --end-time TIME         End time for time range
    --retention-days DAYS   Log retention days

EXAMPLES:
    $0 init                          # Initialize aggregation system
    $0 start                         # Start log aggregation
    $0 aggregate api-gateway         # Aggregate API Gateway logs
    $0 aggregate-type security       # Aggregate security logs
    $0 cleanup 7                     # Cleanup logs older than 7 days
    $0 stats                         # Show aggregation statistics

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
        --type)
            LOG_TYPE="$2"
            shift 2
            ;;
        --start-time)
            START_TIME="$2"
            shift 2
            ;;
        --end-time)
            END_TIME="$2"
            shift 2
            ;;
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        init)
            COMMAND="init"
            shift
            ;;
        start)
            COMMAND="start"
            shift
            ;;
        stop)
            COMMAND="stop"
            shift
            ;;
        restart)
            COMMAND="restart"
            shift
            ;;
        status)
            COMMAND="status"
            shift
            ;;
        stats)
            COMMAND="stats"
            shift
            ;;
        aggregate)
            COMMAND="aggregate"
            if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                SERVICE_NAME="$2"
                shift
            fi
            shift
            ;;
        aggregate-all)
            COMMAND="aggregate-all"
            shift
            ;;
        aggregate-time)
            COMMAND="aggregate-time"
            START_TIME="$2"
            END_TIME="$3"
            shift 3
            ;;
        aggregate-type)
            COMMAND="aggregate-type"
            LOG_TYPE="$2"
            shift 2
            ;;
        cleanup)
            COMMAND="cleanup"
            if [[ -n "$2" && ! "$2" =~ ^- ]]; then
                RETENTION_DAYS="$2"
                shift
            fi
            shift
            ;;
        health)
            COMMAND="health"
            shift
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
    init)
        initialize_aggregation
        ;;
    start)
        start_aggregation
        ;;
    stop)
        stop_aggregation
        ;;
    restart)
        restart_aggregation
        ;;
    status)
        check_aggregation_health
        ;;
    stats)
        get_aggregation_stats
        ;;
    aggregate)
        if [[ -n "$SERVICE_NAME" ]]; then
            aggregate_logs_by_service "$SERVICE_NAME"
        else
            log_error "Service name required for aggregate command"
            exit 1
        fi
        ;;
    aggregate-all)
        aggregate_all_logs
        ;;
    aggregate-time)
        if [[ -n "$START_TIME" && -n "$END_TIME" ]]; then
            aggregate_logs_by_time "$START_TIME" "$END_TIME"
        else
            log_error "Start time and end time required for aggregate-time command"
            exit 1
        fi
        ;;
    aggregate-type)
        if [[ -n "$LOG_TYPE" ]]; then
            aggregate_logs_by_type "$LOG_TYPE"
        else
            log_error "Log type required for aggregate-type command"
            exit 1
        fi
        ;;
    cleanup)
        cleanup_old_logs "${RETENTION_DAYS:-30}"
        ;;
    health)
        check_aggregation_health
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
