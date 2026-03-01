#!/bin/bash
# Restart All Services Script
# LUCID-STRICT Layer 2 Service Management
# Purpose: Restart all Lucid services for service management
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
COMPOSE_FILE="${LUCID_COMPOSE_FILE:-/opt/lucid/docker-compose.yml}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/service-restart.log}"
BACKUP_DIR="${LUCID_BACKUP_DIR:-/data/backups}"
SERVICES_TIMEOUT="${SERVICES_TIMEOUT:-60}" # seconds
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-120}" # seconds
PARALLEL_RESTART="${PARALLEL_RESTART:-false}"

# Service definitions (order matters for dependencies)
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
mkdir -p "$BACKUP_DIR"

echo "========================================"
log_info "🔄 LUCID Service Restart Manager"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Restart all Lucid services for service management"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --force             Force restart without confirmation"
    echo "  -s, --stop              Stop all services"
    echo "  -r, --restart           Restart all services (default)"
    echo "  -u, --start             Start all services"
    echo "  -p, --parallel          Restart services in parallel"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -c, --check             Check all service status"
    echo "  -l, --logs              Show logs for all services"
    echo "  -b, --backup            Create backup before restart"
    echo "  --services LIST         Comma-separated list of services to restart"
    echo "  --exclude LIST          Comma-separated list of services to exclude"
    echo "  --timeout SECONDS       Timeout for service operations (default: 60)"
    echo "  --health-timeout SECONDS Health check timeout (default: 120)"
    echo ""
    echo "Available Services:"
    for service in "${SERVICES[@]}"; do
        echo "  - $service"
    done
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_COMPOSE_FILE      Docker compose file path"
    echo "  SERVICES_TIMEOUT        Service operation timeout (default: 60)"
    echo "  HEALTH_CHECK_TIMEOUT    Health check timeout (default: 120)"
    echo "  PARALLEL_RESTART        Enable parallel restart (default: false)"
    echo ""
    echo "Examples:"
    echo "  $0 --restart            Restart all services"
    echo "  $0 --services mongo,api Restart specific services"
    echo "  $0 --exclude gui        Restart all services except GUI"
    echo "  $0 --parallel --force   Parallel restart without confirmation"
    echo "  $0 --backup             Create backup before restart"
}

# Parse command line arguments
FORCE=false
ACTION="restart"
PARALLEL=false
VERBOSE=false
CHECK_STATUS=false
SHOW_LOGS=false
CREATE_BACKUP=false
SERVICES_LIST=""
EXCLUDE_LIST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -s|--stop)
            ACTION="stop"
            shift
            ;;
        -r|--restart)
            ACTION="restart"
            shift
            ;;
        -u|--start)
            ACTION="start"
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--check)
            CHECK_STATUS=true
            shift
            ;;
        -l|--logs)
            SHOW_LOGS=true
            shift
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        --services)
            SERVICES_LIST="$2"
            shift 2
            ;;
        --exclude)
            EXCLUDE_LIST="$2"
            shift 2
            ;;
        --timeout)
            SERVICES_TIMEOUT="$2"
            shift 2
            ;;
        --health-timeout)
            HEALTH_CHECK_TIMEOUT="$2"
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

# Function to check Docker availability
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not available"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not available"
        return 1
    fi
    
    log_success "Docker and Docker Compose are available"
    return 0
}

# Function to check compose file
check_compose_file() {
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        return 1
    fi
    
    # Validate compose file syntax
    if docker-compose -f "$COMPOSE_FILE" config &>/dev/null; then
        log_success "Compose file is valid: $COMPOSE_FILE"
        return 0
    else
        log_error "Compose file syntax is invalid: $COMPOSE_FILE"
        return 1
    fi
}

# Function to get services to operate on
get_services() {
    local services_to_operate=()
    
    if [[ -n "$SERVICES_LIST" ]]; then
        # Use specific services list
        IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES_LIST"
        for service in "${SERVICE_ARRAY[@]}"; do
            service=$(echo "$service" | tr -d ' ')
            if [[ " ${SERVICES[@]} " =~ " ${service} " ]]; then
                services_to_operate+=("$service")
            else
                log_warning "Unknown service: $service"
            fi
        done
    else
        # Use all services
        services_to_operate=("${SERVICES[@]}")
    fi
    
    # Remove excluded services
    if [[ -n "$EXCLUDE_LIST" ]]; then
        IFS=',' read -ra EXCLUDE_ARRAY <<< "$EXCLUDE_LIST"
        local filtered_services=()
        for service in "${services_to_operate[@]}"; do
            local exclude=false
            for exclude_service in "${EXCLUDE_ARRAY[@]}"; do
                exclude_service=$(echo "$exclude_service" | tr -d ' ')
                if [[ "$service" == "$exclude_service" ]]; then
                    exclude=true
                    break
                fi
            done
            if [[ "$exclude" == "false" ]]; then
                filtered_services+=("$service")
            fi
        done
        services_to_operate=("${filtered_services[@]}")
    fi
    
    echo "${services_to_operate[@]}"
}

# Function to check service status
check_service_status() {
    local service="$1"
    
    if docker-compose -f "$COMPOSE_FILE" ps "$service" &>/dev/null; then
        local status=$(docker-compose -f "$COMPOSE_FILE" ps "$service" --format "table {{.State}}" | tail -1)
        if [[ "$status" == "Up" ]]; then
            return 0
        else
            return 1
        fi
    else
        return 1
    fi
}

# Function to check all service status
check_all_service_status() {
    log_info "Checking all service status..."
    echo ""
    
    local services_to_check=($(get_services))
    local running_count=0
    local total_count=${#services_to_check[@]}
    
    printf "%-30s %-15s %-20s\n" "SERVICE" "STATUS" "HEALTH"
    echo "----------------------------------------------------------------"
    
    for service in "${services_to_check[@]}"; do
        local status="Unknown"
        local health="Unknown"
        
        if check_service_status "$service"; then
            status="Running"
            health="Healthy"
            ((running_count++))
        else
            status="Stopped"
            health="Unhealthy"
        fi
        
        printf "%-30s %-15s %-20s\n" "$service" "$status" "$health"
    done
    
    echo ""
    log_info "Service Summary: $running_count/$total_count services running"
    
    if [[ $running_count -eq $total_count ]]; then
        log_success "All services are running"
        return 0
    else
        log_warning "Some services are not running"
        return 1
    fi
}

# Function to show service logs
show_service_logs() {
    log_info "Showing logs for all services..."
    
    local services_to_check=($(get_services))
    
    for service in "${services_to_check[@]}"; do
        echo ""
        log_info "=== Logs for $service ==="
        docker-compose -f "$COMPOSE_FILE" logs --tail=20 "$service" 2>/dev/null || log_warning "No logs available for $service"
    done
}

# Function to create backup
create_backup() {
    log_info "Creating backup before service restart..."
    
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_path="$BACKUP_DIR/service-restart-backup-$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup compose file
    if [[ -f "$COMPOSE_FILE" ]]; then
        cp "$COMPOSE_FILE" "$backup_path/docker-compose.yml"
        log_info "Backed up compose file"
    fi
    
    # Backup service configurations
    local services_to_backup=($(get_services))
    for service in "${services_to_backup[@]}"; do
        # Get service configuration from compose
        docker-compose -f "$COMPOSE_FILE" config --services | grep -q "$service" && {
            docker-compose -f "$COMPOSE_FILE" config | grep -A 50 "^  $service:" > "$backup_path/${service}-config.yml" 2>/dev/null || true
        }
    done
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "backup_timestamp": "$backup_timestamp",
    "backup_date": "$(date -Iseconds)",
    "services_backed_up": ${#services_to_backup[@]},
    "compose_file": "$COMPOSE_FILE",
    "action": "$ACTION",
    "lucid_version": "$(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')"
}
EOF
    
    # Compress backup
    if tar -czf "$backup_path.tar.gz" -C "$(dirname "$backup_path")" "$(basename "$backup_path")"; then
        rm -rf "$backup_path"
        log_success "Backup created: $backup_path.tar.gz"
        return 0
    else
        log_error "Failed to create backup"
        rm -rf "$backup_path"
        return 1
    fi
}

# Function to stop service
stop_service() {
    local service="$1"
    
    log_info "Stopping service: $service"
    
    if docker-compose -f "$COMPOSE_FILE" stop "$service" --timeout "$SERVICES_TIMEOUT"; then
        log_success "Stopped service: $service"
        return 0
    else
        log_error "Failed to stop service: $service"
        return 1
    fi
}

# Function to start service
start_service() {
    local service="$1"
    
    log_info "Starting service: $service"
    
    if docker-compose -f "$COMPOSE_FILE" up -d "$service"; then
        # Wait for service to be ready
        log_info "Waiting for service to be ready: $service"
        local wait_time=0
        while [[ $wait_time -lt $HEALTH_CHECK_TIMEOUT ]]; do
            if check_service_status "$service"; then
                log_success "Started service: $service"
                return 0
            fi
            sleep 2
            ((wait_time += 2))
        done
        
        log_warning "Service started but health check timeout: $service"
        return 1
    else
        log_error "Failed to start service: $service"
        return 1
    fi
}

# Function to restart service
restart_service() {
    local service="$1"
    
    log_info "Restarting service: $service"
    
    # Stop service
    if stop_service "$service"; then
        sleep 2
        # Start service
        if start_service "$service"; then
            log_success "Restarted service: $service"
            return 0
        else
            log_error "Failed to start service after restart: $service"
            return 1
        fi
    else
        log_error "Failed to stop service for restart: $service"
        return 1
    fi
}

# Function to stop all services
stop_all_services() {
    log_info "Stopping all services..."
    
    local services_to_stop=($(get_services))
    local stopped_count=0
    local failed_count=0
    
    for service in "${services_to_stop[@]}"; do
        if stop_service "$service"; then
            ((stopped_count++))
        else
            ((failed_count++))
        fi
    done
    
    log_info "Stop summary: $stopped_count stopped, $failed_count failed"
    
    if [[ $failed_count -eq 0 ]]; then
        log_success "All services stopped successfully"
        return 0
    else
        log_error "Some services failed to stop"
        return 1
    fi
}

# Function to start all services
start_all_services() {
    log_info "Starting all services..."
    
    local services_to_start=($(get_services))
    local started_count=0
    local failed_count=0
    
    for service in "${services_to_start[@]}"; do
        if start_service "$service"; then
            ((started_count++))
        else
            ((failed_count++))
        fi
    done
    
    log_info "Start summary: $started_count started, $failed_count failed"
    
    if [[ $failed_count -eq 0 ]]; then
        log_success "All services started successfully"
        return 0
    else
        log_error "Some services failed to start"
        return 1
    fi
}

# Function to restart all services
restart_all_services() {
    log_info "Restarting all services..."
    
    local services_to_restart=($(get_services))
    local restarted_count=0
    local failed_count=0
    
    if [[ "$PARALLEL" == "true" ]]; then
        log_info "Using parallel restart mode"
        
        # Start background processes for parallel restart
        local pids=()
        for service in "${services_to_restart[@]}"; do
            restart_service "$service" &
            pids+=($!)
        done
        
        # Wait for all processes to complete
        for pid in "${pids[@]}"; do
            if wait "$pid"; then
                ((restarted_count++))
            else
                ((failed_count++))
            fi
        done
    else
        log_info "Using sequential restart mode"
        
        for service in "${services_to_restart[@]}"; do
            if restart_service "$service"; then
                ((restarted_count++))
            else
                ((failed_count++))
            fi
        done
    fi
    
    log_info "Restart summary: $restarted_count restarted, $failed_count failed"
    
    if [[ $failed_count -eq 0 ]]; then
        log_success "All services restarted successfully"
        return 0
    else
        log_error "Some services failed to restart"
        return 1
    fi
}

# Function to perform health check
perform_health_check() {
    log_info "Performing health check on all services..."
    
    # Wait a bit for services to stabilize
    sleep 10
    
    if check_all_service_status; then
        log_success "Health check passed - all services are running"
        return 0
    else
        log_error "Health check failed - some services are not running"
        return 1
    fi
}

# Main function
main() {
    # Handle special operations
    if [[ "$CHECK_STATUS" == "true" ]]; then
        check_all_service_status
        return $?
    fi
    
    if [[ "$SHOW_LOGS" == "true" ]]; then
        show_service_logs
        return 0
    fi
    
    # Check prerequisites
    if ! check_docker; then
        return 1
    fi
    
    if ! check_compose_file; then
        return 1
    fi
    
    # Create backup if requested
    if [[ "$CREATE_BACKUP" == "true" ]]; then
        if ! create_backup; then
            log_error "Backup creation failed"
            return 1
        fi
    fi
    
    # Confirmation prompt (unless forced)
    if [[ "$FORCE" == "false" ]]; then
        local services_to_operate=($(get_services))
        echo ""
        log_info "This will $ACTION the following services:"
        for service in "${services_to_operate[@]}"; do
            echo "  - $service"
        done
        
        if [[ "$PARALLEL" == "true" ]]; then
            log_info "Services will be restarted in parallel"
        fi
        
        echo ""
        read -p "Continue with $ACTION operation? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Operation cancelled by user"
            return 0
        fi
    fi
    
    # Perform the requested action
    local result=0
    case "$ACTION" in
        "start")
            start_all_services
            result=$?
            ;;
        "stop")
            stop_all_services
            result=$?
            ;;
        "restart")
            restart_all_services
            result=$?
            ;;
        *)
            log_error "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
    
    # Perform health check for start/restart operations
    if [[ "$ACTION" == "start" || "$ACTION" == "restart" ]]; then
        perform_health_check
        local health_result=$?
        if [[ $health_result -ne 0 ]]; then
            result=$health_result
        fi
    fi
    
    return $result
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
    # Cleanup will be handled by individual functions
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
