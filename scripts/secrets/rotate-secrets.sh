#!/bin/bash
# Secret Rotation Script
# LUCID-STRICT Secret Management System
# Purpose: Rotate secrets for all Lucid clusters with security compliance
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
SECRETS_DIR="${LUCID_SECRETS_DIR:-configs/secrets}"
BACKUP_DIR="${LUCID_BACKUP_DIR:-/data/backups/secrets}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/secret-rotation.log}"
ROTATION_LOG_DIR="$SECRETS_DIR/rotation-log"

# Rotation intervals (in days)
JWT_ROTATION_INTERVAL="${JWT_ROTATION_INTERVAL:-90}"
DATABASE_ROTATION_INTERVAL="${DATABASE_ROTATION_INTERVAL:-180}"
TRON_ROTATION_INTERVAL="${TRON_ROTATION_INTERVAL:-365}"
ADMIN_ROTATION_INTERVAL="${ADMIN_ROTATION_INTERVAL:-90}"
SESSION_ROTATION_INTERVAL="${SESSION_ROTATION_INTERVAL:-30}"
MESH_ROTATION_INTERVAL="${MESH_ROTATION_INTERVAL:-90}"
BLOCKCHAIN_ROTATION_INTERVAL="${BLOCKCHAIN_ROTATION_INTERVAL:-180}"
RDP_ROTATION_INTERVAL="${RDP_ROTATION_INTERVAL:-90}"
NODE_ROTATION_INTERVAL="${NODE_ROTATION_INTERVAL:-90}"
MONITORING_ROTATION_INTERVAL="${MONITORING_ROTATION_INTERVAL:-180}"
EXTERNAL_ROTATION_INTERVAL="${EXTERNAL_ROTATION_INTERVAL:-365}"
BACKUP_ROTATION_INTERVAL="${BACKUP_ROTATION_INTERVAL:-180}"

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
mkdir -p "$SECRETS_DIR"
mkdir -p "$BACKUP_DIR"
mkdir -p "$ROTATION_LOG_DIR"

echo "========================================"
log_info "🔄 LUCID Secret Rotation"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Rotate secrets for Lucid clusters with security compliance"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -t, --type TYPE         Rotate specific secret type"
    echo "  -a, --all               Rotate all secret types"
    echo "  -c, --check             Check rotation status"
    echo "  -f, --force             Force rotation without confirmation"
    echo "  -d, --dry-run           Show what would be rotated without executing"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -b, --backup            Create backup before rotation"
    echo "  --verify               Verify rotation was successful"
    echo "  --history              Show rotation history"
    echo "  --cleanup              Clean up old rotation backups"
    echo ""
    echo "Secret Types:"
    echo "  jwt                     JWT signing secrets (90 days)"
    echo "  database                Database authentication secrets (180 days)"
    echo "  tron                    TRON payment secrets (365 days)"
    echo "  hardware                Hardware wallet secrets (180 days)"
    echo "  mesh                    Service mesh secrets (90 days)"
    echo "  admin                   Admin interface secrets (90 days)"
    echo "  blockchain              Blockchain consensus secrets (180 days)"
    echo "  session                 Session management secrets (30 days)"
    echo "  rdp                     RDP service secrets (90 days)"
    echo "  node                    Node management secrets (90 days)"
    echo "  monitoring              Monitoring and alerting secrets (180 days)"
    echo "  external                External service secrets (365 days)"
    echo "  backup                  Backup encryption secrets (180 days)"
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_SECRETS_DIR       Secrets directory (default: configs/secrets)"
    echo "  LUCID_BACKUP_DIR        Backup directory (default: /data/backups/secrets)"
    echo "  JWT_ROTATION_INTERVAL   JWT rotation interval in days (default: 90)"
    echo "  DATABASE_ROTATION_INTERVAL Database rotation interval in days (default: 180)"
    echo "  TRON_ROTATION_INTERVAL  TRON rotation interval in days (default: 365)"
    echo ""
    echo "Examples:"
    echo "  $0 --check              Check rotation status"
    echo "  $0 --type jwt           Rotate JWT secrets only"
    echo "  $0 --all --backup       Rotate all secrets with backup"
    echo "  $0 --verify             Verify last rotation"
    echo "  $0 --history            Show rotation history"
}

# Parse command line arguments
SECRET_TYPE=""
ROTATE_ALL=false
CHECK_STATUS=false
FORCE=false
DRY_RUN=false
VERBOSE=false
CREATE_BACKUP=false
VERIFY_ROTATION=false
SHOW_HISTORY=false
CLEANUP_OLD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -t|--type)
            SECRET_TYPE="$2"
            shift 2
            ;;
        -a|--all)
            ROTATE_ALL=true
            shift
            ;;
        -c|--check)
            CHECK_STATUS=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        --verify)
            VERIFY_ROTATION=true
            shift
            ;;
        --history)
            SHOW_HISTORY=true
            shift
            ;;
        --cleanup)
            CLEANUP_OLD=true
            shift
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

# Function to get secret age in days
get_secret_age() {
    local secret_file="$1"
    local secret_name="$2"
    
    if [[ ! -f "$secret_file" ]]; then
        echo "0"
        return
    fi
    
    # Check if secret exists and get its modification time
    if grep -q "^${secret_name}=" "$secret_file"; then
        local secret_line=$(grep "^${secret_name}=" "$secret_file")
        local secret_value=$(echo "$secret_line" | cut -d'=' -f2)
        
        # Check if it's a default value
        if [[ "$secret_value" == *"your-"* ]] || [[ "$secret_value" == *"change-in-production"* ]]; then
            echo "999"  # Very old (default value)
            return
        fi
        
        # Get file modification time
        local file_time=$(stat -c %Y "$secret_file" 2>/dev/null || stat -f %m "$secret_file" 2>/dev/null || echo "0")
        local current_time=$(date +%s)
        local age_days=$(( (current_time - file_time) / 86400 ))
        echo "$age_days"
    else
        echo "999"  # Secret not found
    fi
}

# Function to check rotation status
check_rotation_status() {
    local secrets_file="$SECRETS_DIR/.secrets"
    
    log_info "Checking secret rotation status..."
    echo ""
    
    if [[ ! -f "$secrets_file" ]]; then
        log_error "No secrets file found: $secrets_file"
        return 1
    fi
    
    local expired_secrets=()
    local expiring_soon=()
    local current_time=$(date +%s)
    
    # Check JWT secrets
    local jwt_age=$(get_secret_age "$secrets_file" "JWT_SECRET_KEY")
    if [[ $jwt_age -ge $JWT_ROTATION_INTERVAL ]]; then
        expired_secrets+=("JWT secrets (${jwt_age} days old)")
    elif [[ $jwt_age -ge $((JWT_ROTATION_INTERVAL - 14)) ]]; then
        expiring_soon+=("JWT secrets (${jwt_age} days old)")
    fi
    
    # Check database secrets
    local mongodb_age=$(get_secret_age "$secrets_file" "MONGODB_PASSWORD")
    if [[ $mongodb_age -ge $DATABASE_ROTATION_INTERVAL ]]; then
        expired_secrets+=("Database secrets (${mongodb_age} days old)")
    elif [[ $mongodb_age -ge $((DATABASE_ROTATION_INTERVAL - 30)) ]]; then
        expiring_soon+=("Database secrets (${mongodb_age} days old)")
    fi
    
    # Check TRON secrets
    local tron_age=$(get_secret_age "$secrets_file" "TRON_PRIVATE_KEY_ENCRYPTED")
    if [[ $tron_age -ge $TRON_ROTATION_INTERVAL ]]; then
        expired_secrets+=("TRON secrets (${tron_age} days old)")
    elif [[ $tron_age -ge $((TRON_ROTATION_INTERVAL - 60)) ]]; then
        expiring_soon+=("TRON secrets (${tron_age} days old)")
    fi
    
    # Check admin secrets
    local admin_age=$(get_secret_age "$secrets_file" "ADMIN_JWT_SECRET")
    if [[ $admin_age -ge $ADMIN_ROTATION_INTERVAL ]]; then
        expired_secrets+=("Admin secrets (${admin_age} days old)")
    elif [[ $admin_age -ge $((ADMIN_ROTATION_INTERVAL - 14)) ]]; then
        expiring_soon+=("Admin secrets (${admin_age} days old)")
    fi
    
    # Check session secrets
    local session_age=$(get_secret_age "$secrets_file" "SESSION_ENCRYPTION_KEY")
    if [[ $session_age -ge $SESSION_ROTATION_INTERVAL ]]; then
        expired_secrets+=("Session secrets (${session_age} days old)")
    elif [[ $session_age -ge $((SESSION_ROTATION_INTERVAL - 7)) ]]; then
        expiring_soon+=("Session secrets (${session_age} days old)")
    fi
    
    # Display results
    if [[ ${#expired_secrets[@]} -gt 0 ]]; then
        log_error "Expired secrets (${#expired_secrets[@]}):"
        for secret in "${expired_secrets[@]}"; do
            echo "  ❌ $secret"
        done
        echo ""
    fi
    
    if [[ ${#expiring_soon[@]} -gt 0 ]]; then
        log_warning "Secrets expiring soon (${#expiring_soon[@]}):"
        for secret in "${expiring_soon[@]}"; do
            echo "  ⚠️  $secret"
        done
        echo ""
    fi
    
    if [[ ${#expired_secrets[@]} -eq 0 && ${#expiring_soon[@]} -eq 0 ]]; then
        log_success "All secrets are within rotation intervals"
        return 0
    else
        return 1
    fi
}

# Function to create rotation backup
create_rotation_backup() {
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/rotation-backup-$backup_timestamp.tar.gz"
    
    log_info "Creating rotation backup: $backup_file"
    
    if [[ -f "$SECRETS_DIR/.secrets" ]]; then
        if tar -czf "$backup_file" -C "$SECRETS_DIR" .secrets; then
            log_success "Rotation backup created: $backup_file"
            
            # Log backup creation
            echo "$(date -Iseconds): Backup created: $backup_file" >> "$ROTATION_LOG_DIR/rotation.log"
            return 0
        else
            log_error "Failed to create rotation backup"
            return 1
        fi
    else
        log_warning "No secrets file to backup"
        return 0
    fi
}

# Function to rotate JWT secrets
rotate_jwt_secrets() {
    local secrets_file="$SECRETS_DIR/.secrets"
    local rotation_log="$ROTATION_LOG_DIR/jwt-rotation.log"
    
    log_info "Rotating JWT secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rotate JWT secrets"
        return 0
    fi
    
    # Generate new JWT secrets
    local new_jwt_secret=$(openssl rand -base64 64)
    local new_jwt_refresh_secret=$(openssl rand -base64 64)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$new_jwt_secret/" "$secrets_file"
        sed -i "s/JWT_REFRESH_SECRET_KEY=.*/JWT_REFRESH_SECRET_KEY=$new_jwt_refresh_secret/" "$secrets_file"
    else
        log_error "No secrets file found"
        return 1
    fi
    
    # Log rotation
    echo "$(date -Iseconds): JWT secrets rotated" >> "$rotation_log"
    
    log_success "JWT secrets rotated successfully"
    return 0
}

# Function to rotate database secrets
rotate_database_secrets() {
    local secrets_file="$SECRETS_DIR/.secrets"
    local rotation_log="$ROTATION_LOG_DIR/database-rotation.log"
    
    log_info "Rotating database secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rotate database secrets"
        return 0
    fi
    
    # Generate new database passwords
    local new_mongodb_password=$(openssl rand -base64 48)
    local new_mongodb_root_password=$(openssl rand -base64 48)
    local new_redis_password=$(openssl rand -base64 48)
    local new_elasticsearch_password=$(openssl rand -base64 48)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/MONGODB_PASSWORD=.*/MONGODB_PASSWORD=$new_mongodb_password/" "$secrets_file"
        sed -i "s/MONGODB_ROOT_PASSWORD=.*/MONGODB_ROOT_PASSWORD=$new_mongodb_root_password/" "$secrets_file"
        sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$new_redis_password/" "$secrets_file"
        sed -i "s/ELASTICSEARCH_PASSWORD=.*/ELASTICSEARCH_PASSWORD=$new_elasticsearch_password/" "$secrets_file"
    else
        log_error "No secrets file found"
        return 1
    fi
    
    # Log rotation
    echo "$(date -Iseconds): Database secrets rotated" >> "$rotation_log"
    
    log_success "Database secrets rotated successfully"
    return 0
}

# Function to rotate TRON secrets
rotate_tron_secrets() {
    local secrets_file="$SECRETS_DIR/.secrets"
    local rotation_log="$ROTATION_LOG_DIR/tron-rotation.log"
    
    log_info "Rotating TRON payment secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rotate TRON payment secrets"
        return 0
    fi
    
    # Generate new TRON secrets
    local new_tron_private_key=$(openssl rand -hex 32)
    local new_tron_passphrase=$(openssl rand -base64 32)
    local new_tron_api_key=$(openssl rand -hex 32)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/TRON_PRIVATE_KEY_ENCRYPTED=.*/TRON_PRIVATE_KEY_ENCRYPTED=$new_tron_private_key/" "$secrets_file"
        sed -i "s/TRON_PRIVATE_KEY_PASSPHRASE=.*/TRON_PRIVATE_KEY_PASSPHRASE=$new_tron_passphrase/" "$secrets_file"
        sed -i "s/TRON_API_KEY=.*/TRON_API_KEY=$new_tron_api_key/" "$secrets_file"
    else
        log_error "No secrets file found"
        return 1
    fi
    
    # Log rotation
    echo "$(date -Iseconds): TRON payment secrets rotated" >> "$rotation_log"
    
    log_success "TRON payment secrets rotated successfully"
    return 0
}

# Function to rotate admin secrets
rotate_admin_secrets() {
    local secrets_file="$SECRETS_DIR/.secrets"
    local rotation_log="$ROTATION_LOG_DIR/admin-rotation.log"
    
    log_info "Rotating admin interface secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rotate admin interface secrets"
        return 0
    fi
    
    # Generate new admin secrets
    local new_admin_jwt_secret=$(openssl rand -base64 64)
    local new_admin_api_key=$(openssl rand -hex 32)
    local new_admin_session_secret=$(openssl rand -base64 64)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/ADMIN_JWT_SECRET=.*/ADMIN_JWT_SECRET=$new_admin_jwt_secret/" "$secrets_file"
        sed -i "s/ADMIN_API_KEY=.*/ADMIN_API_KEY=$new_admin_api_key/" "$secrets_file"
        sed -i "s/ADMIN_SESSION_SECRET=.*/ADMIN_SESSION_SECRET=$new_admin_session_secret/" "$secrets_file"
    else
        log_error "No secrets file found"
        return 1
    fi
    
    # Log rotation
    echo "$(date -Iseconds): Admin interface secrets rotated" >> "$rotation_log"
    
    log_success "Admin interface secrets rotated successfully"
    return 0
}

# Function to rotate session secrets
rotate_session_secrets() {
    local secrets_file="$SECRETS_DIR/.secrets"
    local rotation_log="$ROTATION_LOG_DIR/session-rotation.log"
    
    log_info "Rotating session management secrets..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would rotate session management secrets"
        return 0
    fi
    
    # Generate new session secrets
    local new_session_encryption_key=$(openssl rand -base64 64)
    local new_session_signing_key=$(openssl rand -base64 64)
    local new_chunk_encryption_key=$(openssl rand -base64 64)
    
    # Update secrets file
    if [[ -f "$secrets_file" ]]; then
        sed -i "s/SESSION_ENCRYPTION_KEY=.*/SESSION_ENCRYPTION_KEY=$new_session_encryption_key/" "$secrets_file"
        sed -i "s/SESSION_SIGNING_KEY=.*/SESSION_SIGNING_KEY=$new_session_signing_key/" "$secrets_file"
        sed -i "s/CHUNK_ENCRYPTION_KEY=.*/CHUNK_ENCRYPTION_KEY=$new_chunk_encryption_key/" "$secrets_file"
    else
        log_error "No secrets file found"
        return 1
    fi
    
    # Log rotation
    echo "$(date -Iseconds): Session management secrets rotated" >> "$rotation_log"
    
    log_success "Session management secrets rotated successfully"
    return 0
}

# Function to rotate all secrets
rotate_all_secrets() {
    log_info "Rotating all secret types..."
    
    local rotated=0
    
    # Rotate each secret type
    rotate_jwt_secrets && ((rotated++))
    rotate_database_secrets && ((rotated++))
    rotate_tron_secrets && ((rotated++))
    rotate_admin_secrets && ((rotated++))
    rotate_session_secrets && ((rotated++))
    
    # Additional secret types
    log_info "Rotating additional secret types..."
    
    # Service mesh secrets
    local mesh_jwt_secret=$(openssl rand -base64 64)
    if [[ -f "$SECRETS_DIR/.secrets" ]]; then
        sed -i "s/SERVICE_MESH_JWT_SECRET=.*/SERVICE_MESH_JWT_SECRET=$mesh_jwt_secret/" "$SECRETS_DIR/.secrets"
        echo "$(date -Iseconds): Service mesh secrets rotated" >> "$ROTATION_LOG_DIR/mesh-rotation.log"
        ((rotated++))
    fi
    
    # Blockchain secrets
    local blockchain_consensus_secret=$(openssl rand -base64 64)
    if [[ -f "$SECRETS_DIR/.secrets" ]]; then
        sed -i "s/BLOCKCHAIN_CONSENSUS_SECRET=.*/BLOCKCHAIN_CONSENSUS_SECRET=$blockchain_consensus_secret/" "$SECRETS_DIR/.secrets"
        echo "$(date -Iseconds): Blockchain secrets rotated" >> "$ROTATION_LOG_DIR/blockchain-rotation.log"
        ((rotated++))
    fi
    
    # RDP secrets
    local rdp_admin_password=$(openssl rand -base64 32)
    if [[ -f "$SECRETS_DIR/.secrets" ]]; then
        sed -i "s/RDP_ADMIN_PASSWORD=.*/RDP_ADMIN_PASSWORD=$rdp_admin_password/" "$SECRETS_DIR/.secrets"
        echo "$(date -Iseconds): RDP secrets rotated" >> "$ROTATION_LOG_DIR/rdp-rotation.log"
        ((rotated++))
    fi
    
    # Node management secrets
    local node_operator_key=$(openssl rand -hex 32)
    if [[ -f "$SECRETS_DIR/.secrets" ]]; then
        sed -i "s/NODE_OPERATOR_KEY=.*/NODE_OPERATOR_KEY=$node_operator_key/" "$SECRETS_DIR/.secrets"
        echo "$(date -Iseconds): Node management secrets rotated" >> "$ROTATION_LOG_DIR/node-rotation.log"
        ((rotated++))
    fi
    
    # Monitoring secrets
    local prometheus_secret=$(openssl rand -base64 64)
    if [[ -f "$SECRETS_DIR/.secrets" ]]; then
        sed -i "s/PROMETHEUS_SECRET=.*/PROMETHEUS_SECRET=$prometheus_secret/" "$SECRETS_DIR/.secrets"
        echo "$(date -Iseconds): Monitoring secrets rotated" >> "$ROTATION_LOG_DIR/monitoring-rotation.log"
        ((rotated++))
    fi
    
    log_success "Rotated $rotated secret types"
    return 0
}

# Function to verify rotation
verify_rotation() {
    log_info "Verifying secret rotation..."
    
    local secrets_file="$SECRETS_DIR/.secrets"
    local verification_errors=()
    
    if [[ ! -f "$secrets_file" ]]; then
        log_error "No secrets file found"
        return 1
    fi
    
    # Check if secrets are not default values
    local default_secrets=()
    
    if grep -q "your-256-bit-jwt-secret-key-here-change-in-production" "$secrets_file"; then
        default_secrets+=("JWT_SECRET_KEY")
    fi
    
    if grep -q "your-mongodb-password-here-change-in-production" "$secrets_file"; then
        default_secrets+=("MONGODB_PASSWORD")
    fi
    
    if grep -q "your-encrypted-tron-private-key-here" "$secrets_file"; then
        default_secrets+=("TRON_PRIVATE_KEY_ENCRYPTED")
    fi
    
    if [[ ${#default_secrets[@]} -gt 0 ]]; then
        log_error "Default secrets found (not rotated):"
        for secret in "${default_secrets[@]}"; do
            echo "  ❌ $secret"
        done
        return 1
    fi
    
    log_success "Secret rotation verification passed"
    return 0
}

# Function to show rotation history
show_rotation_history() {
    log_info "Secret rotation history:"
    echo ""
    
    if [[ -d "$ROTATION_LOG_DIR" ]]; then
        for log_file in "$ROTATION_LOG_DIR"/*.log; do
            if [[ -f "$log_file" ]]; then
                local log_name=$(basename "$log_file" .log)
                echo "=== $log_name ==="
                tail -10 "$log_file" 2>/dev/null || echo "No entries"
                echo ""
            fi
        done
    else
        log_warning "No rotation logs found"
    fi
}

# Function to cleanup old rotation backups
cleanup_old_backups() {
    log_info "Cleaning up old rotation backups..."
    
    local backup_count=0
    
    # Remove backups older than 30 days
    if [[ -d "$BACKUP_DIR" ]]; then
        find "$BACKUP_DIR" -name "rotation-backup-*.tar.gz" -mtime +30 -delete
        backup_count=$(find "$BACKUP_DIR" -name "rotation-backup-*.tar.gz" | wc -l)
    fi
    
    log_success "Cleanup completed. $backup_count rotation backups remaining"
    return 0
}

# Main function
main() {
    # Handle special operations
    if [[ "$CHECK_STATUS" == "true" ]]; then
        check_rotation_status
        return $?
    fi
    
    if [[ "$VERIFY_ROTATION" == "true" ]]; then
        verify_rotation
        return $?
    fi
    
    if [[ "$SHOW_HISTORY" == "true" ]]; then
        show_rotation_history
        return 0
    fi
    
    if [[ "$CLEANUP_OLD" == "true" ]]; then
        cleanup_old_backups
        return $?
    fi
    
    # Create backup if requested
    if [[ "$CREATE_BACKUP" == "true" ]]; then
        create_rotation_backup
    fi
    
    # Check if rotation is needed
    if ! check_rotation_status; then
        if [[ "$FORCE" == "false" ]]; then
            echo ""
            read -p "Secrets need rotation. Continue? (yes/no): " confirm
            if [[ "$confirm" != "yes" ]]; then
                log_info "Secret rotation cancelled by user"
                return 0
            fi
        fi
    else
        if [[ "$FORCE" == "false" ]]; then
            log_info "No secrets need rotation at this time"
            return 0
        fi
    fi
    
    # Perform rotation
    if [[ "$ROTATE_ALL" == "true" ]]; then
        rotate_all_secrets
    elif [[ -n "$SECRET_TYPE" ]]; then
        case "$SECRET_TYPE" in
            "jwt")
                rotate_jwt_secrets
                ;;
            "database")
                rotate_database_secrets
                ;;
            "tron")
                rotate_tron_secrets
                ;;
            "admin")
                rotate_admin_secrets
                ;;
            "session")
                rotate_session_secrets
                ;;
            *)
                log_error "Unknown secret type: $SECRET_TYPE"
                show_usage
                exit 1
                ;;
        esac
    else
        log_error "No rotation type specified. Use --type or --all"
        show_usage
        exit 1
    fi
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
