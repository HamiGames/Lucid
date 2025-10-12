#!/bin/bash
# Lucid RDP OTA Update Script
# Handles over-the-air updates with rollback capability

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LUCID_ROOT="/opt/lucid"
BACKUP_DIR="/opt/lucid/backups"
DEPLOYMENT_DIR="/opt/lucid/deployments"
LOG_FILE="/opt/lucid/logs/ota-update.log"
COMPOSE_FILE="$LUCID_ROOT/docker-compose.yml"
SIGNATURE_FILE="$LUCID_ROOT/update-signature.sig"
PUBLIC_KEY_FILE="$LUCID_ROOT/update-public-key.pem"
MAX_BACKUPS=10
UPDATE_TIMEOUT=300

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log_error "$1"
    exit 1
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "This script must be run as root"
    fi
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed"
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose is not installed"
    fi
    
    # Check if required directories exist
    for dir in "$LUCID_ROOT" "$BACKUP_DIR" "$DEPLOYMENT_DIR"; do
        if [[ ! -d "$dir" ]]; then
            log "Creating directory: $dir"
            mkdir -p "$dir"
        fi
    done
    
    # Check disk space (require at least 2GB free)
    AVAILABLE_SPACE=$(df "$LUCID_ROOT" | awk 'NR==2 {print $4}')
    if [[ $AVAILABLE_SPACE -lt 2097152 ]]; then  # 2GB in KB
        error_exit "Insufficient disk space. At least 2GB required."
    fi
    
    log_success "System requirements check passed"
}

# Create backup of current deployment
create_backup() {
    local backup_id="backup-$(date +%Y%m%d-%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_id"
    
    log "Creating backup: $backup_id"
    
    # Create backup directory
    mkdir -p "$backup_path"
    
    # Backup docker-compose.yml
    if [[ -f "$COMPOSE_FILE" ]]; then
        cp "$COMPOSE_FILE" "$backup_path/"
    fi
    
    # Backup configuration files
    if [[ -d "$LUCID_ROOT/configs" ]]; then
        cp -r "$LUCID_ROOT/configs" "$backup_path/"
    fi
    
    # Backup environment files
    find "$LUCID_ROOT" -name "*.env" -exec cp {} "$backup_path/" \;
    
    # Create backup metadata
    cat > "$backup_path/backup-metadata.json" << EOF
{
    "backup_id": "$backup_id",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "system_info": {
        "hostname": "$(hostname)",
        "kernel": "$(uname -r)",
        "docker_version": "$(docker --version)",
        "docker_compose_version": "$(docker-compose --version)"
    },
    "services": $(docker-compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null || echo "[]")
}
EOF
    
    log_success "Backup created: $backup_id"
    echo "$backup_id"
}

# Clean up old backups
cleanup_backups() {
    log "Cleaning up old backups..."
    
    # Keep only the last MAX_BACKUPS backups
    local backup_count=$(ls -1 "$BACKUP_DIR" | wc -l)
    if [[ $backup_count -gt $MAX_BACKUPS ]]; then
        local backups_to_remove=$((backup_count - MAX_BACKUPS))
        ls -1t "$BACKUP_DIR" | tail -n "$backups_to_remove" | while read -r backup; do
            log "Removing old backup: $backup"
            rm -rf "$BACKUP_DIR/$backup"
        done
    fi
    
    log_success "Backup cleanup completed"
}

# Verify update signature using HTTP endpoint
verify_signature() {
    local update_file="$1"
    
    log "Verifying update signature via API..."
    
    # Use HTTP API for signature verification instead of OpenSSL
    local signature_data=$(base64 -w 0 "$update_file" 2>/dev/null || base64 "$update_file")
    local signature=$(cat "$SIGNATURE_FILE" 2>/dev/null || echo "")
    
    if [[ -z "$signature" ]]; then
        log_warning "No signature file found, skipping verification"
        return 0
    fi
    
    # Verify via API endpoint (distroless-compatible)
    local verify_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"data\":\"$signature_data\",\"signature\":\"$signature\"}" \
        "http://localhost:8080/api/verify-signature" 2>/dev/null || echo '{"valid":false}')
    
    if echo "$verify_response" | grep -q '"valid":true'; then
        log_success "Update signature verified via API"
    else
        error_exit "Update signature verification failed"
    fi
}

# Download and extract update using HTTP API
download_update() {
    local update_url="$1"
    local update_id="update-$(date +%Y%m%d-%H%M%S)"
    local extract_dir="$DEPLOYMENT_DIR/$update_id"
    
    log "Downloading update from: $update_url"
    
    # Create extraction directory
    mkdir -p "$extract_dir"
    
    # Download and extract via API endpoint (distroless-compatible)
    local download_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"update_url\":\"$update_url\",\"extract_path\":\"$extract_dir\"}" \
        "http://localhost:8080/api/download-update" 2>/dev/null || echo '{"success":false,"error":"API unavailable"}')
    
    if echo "$download_response" | grep -q '"success":true'; then
        log_success "Update downloaded and extracted via API"
    else
        error_exit "Failed to download update: $(echo "$download_response" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)"
    fi
    
    # Verify signature if available
    if [[ -f "$SIGNATURE_FILE" ]]; then
        verify_signature "$extract_dir"
    fi
    
    echo "$extract_dir"
}

# Stop services gracefully using HTTP API
stop_services() {
    log "Stopping Lucid RDP services..."
    
    # Stop services via API endpoint (distroless-compatible)
    local stop_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"timeout\":$UPDATE_TIMEOUT}" \
        "http://localhost:8080/api/stop-services" 2>/dev/null || echo '{"success":false,"error":"API unavailable"}')
    
    if echo "$stop_response" | grep -q '"success":true'; then
        log_success "Services stopped via API"
    else
        log_warning "API stop failed, attempting graceful shutdown"
        # Fallback to docker-compose if API unavailable
        if [[ -f "$COMPOSE_FILE" ]]; then
            docker-compose -f "$COMPOSE_FILE" down || {
                log_warning "Graceful shutdown failed, forcing stop"
                docker-compose -f "$COMPOSE_FILE" kill
            }
        fi
    fi
}

# Start services using HTTP API
start_services() {
    log "Starting Lucid RDP services..."
    
    # Start services via API endpoint (distroless-compatible)
    local start_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        "http://localhost:8080/api/start-services" 2>/dev/null || echo '{"success":false,"error":"API unavailable"}')
    
    if echo "$start_response" | grep -q '"success":true'; then
        log_success "Services started via API"
    else
        log_error "Failed to start services via API"
        return 1
    fi
    
    # Wait for services to be healthy using HTTP health checks
    log "Waiting for services to be healthy..."
    local max_attempts=60
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        local health_response=$(curl -s "http://localhost:8080/api/health" 2>/dev/null || echo '{"status":"unhealthy"}')
        if echo "$health_response" | grep -q '"status":"healthy"'; then
            log_success "Services are healthy"
            return 0
        fi
        
        sleep 5
        ((attempt++))
    done
    
    log_error "Services failed to become healthy within timeout"
    return 1
}

# Perform rollback
rollback() {
    local backup_id="$1"
    
    log "Performing rollback to backup: $backup_id"
    
    # Stop current services
    stop_services
    
    # Restore backup
    local backup_path="$BACKUP_DIR/$backup_id"
    if [[ ! -d "$backup_path" ]]; then
        error_exit "Backup not found: $backup_id"
    fi
    
    # Restore files
    if [[ -f "$backup_path/docker-compose.yml" ]]; then
        cp "$backup_path/docker-compose.yml" "$COMPOSE_FILE"
    fi
    
    if [[ -d "$backup_path/configs" ]]; then
        rm -rf "$LUCID_ROOT/configs"
        cp -r "$backup_path/configs" "$LUCID_ROOT/"
    fi
    
    # Restore environment files
    find "$backup_path" -name "*.env" -exec cp {} "$LUCID_ROOT/" \;
    
    # Start services
    if start_services; then
        log_success "Rollback completed successfully"
    else
        log_error "Rollback failed - services did not start"
        return 1
    fi
}

# Main update function
perform_update() {
    local update_url="$1"
    local backup_id
    
    log "Starting OTA update process..."
    
    # Check requirements
    check_requirements
    
    # Create backup
    backup_id=$(create_backup)
    
    # Stop services
    stop_services
    
    # Download and extract update
    local update_dir
    update_dir=$(download_update "$update_url")
    
    # Apply update
    log "Applying update..."
    
    # Copy new docker-compose.yml
    if [[ -f "$update_dir/docker-compose.yml" ]]; then
        cp "$update_dir/docker-compose.yml" "$COMPOSE_FILE"
    fi
    
    # Copy new configurations
    if [[ -d "$update_dir/configs" ]]; then
        rm -rf "$LUCID_ROOT/configs"
        cp -r "$update_dir/configs" "$LUCID_ROOT/"
    fi
    
    # Copy environment files
    find "$update_dir" -name "*.env" -exec cp {} "$LUCID_ROOT/" \;
    
    # Pull new images via API
    log "Pulling new Docker images via API..."
    local pull_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        "http://localhost:8080/api/pull-images" 2>/dev/null || echo '{"success":false,"error":"API unavailable"}')
    
    if echo "$pull_response" | grep -q '"success":true'; then
        log_success "Images pulled via API"
    else
        log_warning "API pull failed, attempting direct pull"
        docker-compose -f "$COMPOSE_FILE" pull
    fi
    
    # Start services
    if start_services; then
        log_success "Update completed successfully"
        
        # Clean up old backups
        cleanup_backups
        
        # Remove update files
        rm -rf "$update_dir"
        
        # Update deployment record via API
        curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "{\"status\":\"completed\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
            "http://localhost:8080/api/log-deployment" 2>/dev/null || \
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ): Update completed successfully" >> "$LUCID_ROOT/logs/deployment.log"
        
        return 0
    else
        log_error "Update failed - performing rollback"
        rollback "$backup_id"
        return 1
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  update <URL>     Perform OTA update from URL"
    echo "  rollback <ID>    Rollback to backup ID"
    echo "  backup           Create manual backup"
    echo "  status           Show update status"
    echo "  list-backups     List available backups"
    echo ""
    echo "Examples:"
    echo "  $0 update https://releases.lucid-rdp.com/v1.2.3/update.tar.gz"
    echo "  $0 rollback backup-20231201-143022"
    echo "  $0 status"
}

# Main script logic
main() {
    case "${1:-}" in
        "update")
            if [[ -z "${2:-}" ]]; then
                error_exit "Update URL required"
            fi
            perform_update "$2"
            ;;
        "rollback")
            if [[ -z "${2:-}" ]]; then
                error_exit "Backup ID required"
            fi
            rollback "$2"
            ;;
        "backup")
            check_root
            check_requirements
            create_backup
            ;;
        "status")
            echo "Lucid RDP Update Status"
            echo "======================"
            # Get status via API
            local status_response=$(curl -s "http://localhost:8080/api/deployment-status" 2>/dev/null || echo '{"last_update":"Unknown","services":[]}')
            echo "Last update: $(echo "$status_response" | grep -o '"last_update":"[^"]*"' | cut -d'"' -f4 || echo "Unknown")"
            echo "Active services:"
            echo "$status_response" | grep -o '"services":\[[^]]*\]' | grep -o '"[^"]*"' | sed 's/"//g' | sed 's/^/  /' || echo "  No services running"
            ;;
        "list-backups")
            echo "Available backups:"
            ls -la "$BACKUP_DIR" 2>/dev/null || echo "No backups found"
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
