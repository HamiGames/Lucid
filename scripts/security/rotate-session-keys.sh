#!/bin/bash
# Session Key Rotation Script
# LUCID-STRICT Layer 2 Security Management
# Purpose: Rotate session encryption keys for security compliance
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
KEYS_DIR="${LUCID_KEYS_DIR:-/data/keys}"
BACKUP_DIR="${LUCID_BACKUP_DIR:-/data/backups/keys}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lucid}"
MONGO_USER="${MONGO_USER:-lucid}"
MONGO_PASS="${MONGO_PASS:-lucid}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/key-rotation.log}"
ROTATION_INTERVAL="${ROTATION_INTERVAL:-30}" # days

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
mkdir -p "$KEYS_DIR"
mkdir -p "$BACKUP_DIR"

echo "========================================"
log_info "🔐 LUCID Session Key Rotation"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Rotate session encryption keys for security compliance"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --force             Force rotation without confirmation"
    echo "  -d, --dry-run           Show what would be rotated without executing"
    echo "  -b, --backup-only       Only create backup of current keys"
    echo "  -r, --restore KEY_ID    Restore keys from backup"
    echo "  -l, --list              List current keys and their ages"
    echo "  -c, --check-expiry      Check if keys need rotation"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -i, --interval DAYS     Set rotation interval in days (default: 30)"
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_KEYS_DIR          Keys directory (default: /data/keys)"
    echo "  LUCID_BACKUP_DIR        Backup directory (default: /data/backups/keys)"
    echo "  MONGO_HOST              MongoDB host (default: localhost)"
    echo "  MONGO_PORT              MongoDB port (default: 27017)"
    echo "  MONGO_DB                Database name (default: lucid)"
    echo "  MONGO_USER              MongoDB username (default: lucid)"
    echo "  MONGO_PASS              MongoDB password (default: lucid)"
    echo "  ROTATION_INTERVAL       Rotation interval in days (default: 30)"
    echo ""
    echo "Examples:"
    echo "  $0 --check-expiry       Check if keys need rotation"
    echo "  $0 --backup-only        Create backup of current keys"
    echo "  $0 --dry-run            Show what would be rotated"
    echo "  $0 --interval 7         Rotate keys every 7 days"
}

# Parse command line arguments
FORCE=false
DRY_RUN=false
BACKUP_ONLY=false
RESTORE_KEY_ID=""
LIST_KEYS=false
CHECK_EXPIRY=false
VERBOSE=false

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
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -b|--backup-only)
            BACKUP_ONLY=true
            shift
            ;;
        -r|--restore)
            RESTORE_KEY_ID="$2"
            shift 2
            ;;
        -l|--list)
            LIST_KEYS=true
            shift
            ;;
        -c|--check-expiry)
            CHECK_EXPIRY=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -i|--interval)
            ROTATION_INTERVAL="$2"
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

# Function to test MongoDB connection
test_mongodb_connection() {
    log_info "Testing MongoDB connection..."
    
    local auth_string=""
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASS" ]]; then
        auth_string="-u $MONGO_USER -p $MONGO_PASS --authenticationDatabase admin"
    fi
    
    if mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string --eval "db.runCommand({ping: 1})" &>/dev/null; then
        log_success "MongoDB connection successful"
        return 0
    else
        log_error "MongoDB connection failed"
        return 1
    fi
}

# Function to generate new session key
generate_session_key() {
    local key_id="$1"
    local key_path="$2"
    
    log_info "Generating new session key: $key_id"
    
    # Generate 32-byte (256-bit) key using OpenSSL
    if openssl rand -out "$key_path" 32; then
        # Set secure permissions
        chmod 600 "$key_path"
        log_success "Generated session key: $key_id"
        return 0
    else
        log_error "Failed to generate session key: $key_id"
        return 1
    fi
}

# Function to backup current keys
backup_keys() {
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_path="$BACKUP_DIR/session-keys-backup-$backup_timestamp"
    
    log_info "Creating key backup: $backup_path"
    
    mkdir -p "$backup_path"
    
    # Backup all key files
    local key_files=($(find "$KEYS_DIR" -name "*.key" -type f))
    
    if [[ ${#key_files[@]} -eq 0 ]]; then
        log_warning "No key files found to backup"
        return 0
    fi
    
    local backed_up=0
    for key_file in "${key_files[@]}"; do
        local key_name=$(basename "$key_file")
        if cp "$key_file" "$backup_path/$key_name"; then
            log_info "Backed up key: $key_name"
            ((backed_up++))
        else
            log_error "Failed to backup key: $key_name"
        fi
    done
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "backup_timestamp": "$backup_timestamp",
    "backup_date": "$(date -Iseconds)",
    "keys_backed_up": $backed_up,
    "rotation_interval": $ROTATION_INTERVAL,
    "lucid_version": "$(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')"
}
EOF
    
    # Compress backup
    if tar -czf "$backup_path.tar.gz" -C "$(dirname "$backup_path")" "$(basename "$backup_path")"; then
        rm -rf "$backup_path"
        log_success "Key backup created: $backup_path.tar.gz"
        return 0
    else
        log_error "Failed to compress backup"
        return 1
    fi
}

# Function to restore keys from backup
restore_keys() {
    local key_id="$1"
    
    if [[ -z "$key_id" ]]; then
        log_error "Key ID required for restore"
        return 1
    fi
    
    log_info "Restoring keys from backup: $key_id"
    
    # Find backup file
    local backup_file=""
    if [[ -f "$key_id" ]]; then
        backup_file="$key_id"
    elif [[ -f "$BACKUP_DIR/$key_id" ]]; then
        backup_file="$BACKUP_DIR/$key_id"
    elif [[ -f "$BACKUP_DIR/$key_id.tar.gz" ]]; then
        backup_file="$BACKUP_DIR/$key_id.tar.gz"
    else
        log_error "Backup file not found: $key_id"
        return 1
    fi
    
    # Extract backup
    local temp_restore_dir="/tmp/lucid-key-restore-$(date +%s)"
    mkdir -p "$temp_restore_dir"
    
    if tar -xzf "$backup_file" -C "$temp_restore_dir"; then
        log_success "Backup extracted successfully"
    else
        log_error "Failed to extract backup"
        rm -rf "$temp_restore_dir"
        return 1
    fi
    
    # Restore keys
    local restored=0
    local key_dir=$(find "$temp_restore_dir" -name "*.key" -type f -exec dirname {} \; | head -1)
    
    if [[ -n "$key_dir" ]]; then
        for key_file in "$key_dir"/*.key; do
            if [[ -f "$key_file" ]]; then
                local key_name=$(basename "$key_file")
                local target_path="$KEYS_DIR/$key_name"
                
                if cp "$key_file" "$target_path" && chmod 600 "$target_path"; then
                    log_success "Restored key: $key_name"
                    ((restored++))
                else
                    log_error "Failed to restore key: $key_name"
                fi
            fi
        done
    fi
    
    # Cleanup
    rm -rf "$temp_restore_dir"
    
    log_success "Key restore completed: $restored keys restored"
    return 0
}

# Function to list current keys
list_keys() {
    log_info "Current session keys:"
    echo ""
    
    local key_files=($(find "$KEYS_DIR" -name "*.key" -type f))
    
    if [[ ${#key_files[@]} -eq 0 ]]; then
        log_warning "No session keys found"
        return 0
    fi
    
    printf "%-30s %-20s %-15s %-10s\n" "KEY NAME" "CREATED" "AGE" "SIZE"
    echo "----------------------------------------------------------------"
    
    for key_file in "${key_files[@]}"; do
        local key_name=$(basename "$key_file")
        local created=$(stat -c %y "$key_file" 2>/dev/null || stat -f %Sm "$key_file" 2>/dev/null || echo "unknown")
        local age=$(find "$key_file" -type f -printf '%T@\n' 2>/dev/null | awk '{print int((systime() - $1) / 86400)}' || echo "unknown")
        local size=$(stat -c %s "$key_file" 2>/dev/null || stat -f %z "$key_file" 2>/dev/null || echo "unknown")
        
        printf "%-30s %-20s %-15s %-10s\n" "$key_name" "${created% *}" "${age}d" "${size}B"
    done
    
    echo ""
}

# Function to check key expiry
check_key_expiry() {
    log_info "Checking key expiry status..."
    echo ""
    
    local expired_keys=()
    local expiring_soon=()
    local current_time=$(date +%s)
    
    local key_files=($(find "$KEYS_DIR" -name "*.key" -type f))
    
    if [[ ${#key_files[@]} -eq 0 ]]; then
        log_warning "No session keys found"
        return 0
    fi
    
    for key_file in "${key_files[@]}"; do
        local key_name=$(basename "$key_file")
        local key_time=$(stat -c %Y "$key_file" 2>/dev/null || stat -f %m "$key_file" 2>/dev/null || echo "0")
        local key_age=$(( (current_time - key_time) / 86400 ))
        
        if [[ $key_age -ge $ROTATION_INTERVAL ]]; then
            expired_keys+=("$key_name")
        elif [[ $key_age -ge $((ROTATION_INTERVAL - 7)) ]]; then
            expiring_soon+=("$key_name")
        fi
    done
    
    if [[ ${#expired_keys[@]} -gt 0 ]]; then
        log_error "Expired keys found (${#expired_keys[@]}):"
        for key in "${expired_keys[@]}"; do
            echo "  - $key"
        done
        echo ""
    fi
    
    if [[ ${#expiring_soon[@]} -gt 0 ]]; then
        log_warning "Keys expiring soon (${#expiring_soon[@]}):"
        for key in "${expiring_soon[@]}"; do
            echo "  - $key"
        done
        echo ""
    fi
    
    if [[ ${#expired_keys[@]} -eq 0 && ${#expiring_soon[@]} -eq 0 ]]; then
        log_success "All keys are within rotation interval"
        return 0
    else
        return 1
    fi
}

# Function to rotate session keys
rotate_session_keys() {
    log_info "Starting session key rotation..."
    
    # Test MongoDB connection
    if ! test_mongodb_connection; then
        return 1
    fi
    
    # Backup current keys first
    if ! backup_keys; then
        log_error "Failed to backup current keys"
        return 1
    fi
    
    # Generate new keys
    local key_types=("session-master" "session-auth" "session-encrypt")
    local generated=0
    
    for key_type in "${key_types[@]}"; do
        local key_id="${key_type}-$(date +%Y%m%d-%H%M%S)"
        local key_path="$KEYS_DIR/$key_id.key"
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY RUN: Would generate key $key_id"
        else
            if generate_session_key "$key_id" "$key_path"; then
                ((generated++))
            fi
        fi
    done
    
    if [[ "$DRY_RUN" == "false" ]]; then
        log_success "Generated $generated new session keys"
        
        # Update database with new key references (if needed)
        update_database_keys
        
        # Clean up old keys (keep last 3 versions)
        cleanup_old_keys
    else
        log_info "DRY RUN: Would generate $generated new session keys"
    fi
    
    return 0
}

# Function to update database with new key references
update_database_keys() {
    log_info "Updating database key references..."
    
    local auth_string=""
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASS" ]]; then
        auth_string="-u $MONGO_USER -p $MONGO_PASS --authenticationDatabase admin"
    fi
    
    # Update key metadata in database
    local key_update_result=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" \
        --quiet --eval "
        try {
            db.key_metadata.updateOne(
                { key_type: 'session-master' },
                { 
                    \$set: { 
                        current_key_id: 'session-master-$(date +%Y%m%d-%H%M%S)',
                        last_rotated: new Date(),
                        rotation_count: db.key_metadata.findOne({key_type: 'session-master'})?.rotation_count + 1 || 1
                    }
                },
                { upsert: true }
            );
            print('SUCCESS');
        } catch (e) {
            print('FAILED: ' + e.message);
        }
    ")
    
    if [[ "$key_update_result" == "SUCCESS" ]]; then
        log_success "Database key references updated"
    else
        log_warning "Failed to update database: $key_update_result"
    fi
}

# Function to cleanup old keys
cleanup_old_keys() {
    log_info "Cleaning up old keys..."
    
    local key_types=("session-master" "session-auth" "session-encrypt")
    
    for key_type in "${key_types[@]}"; do
        # Find all keys of this type, sorted by modification time
        local keys=($(find "$KEYS_DIR" -name "${key_type}-*.key" -type f -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-))
        
        # Keep only the 3 most recent keys
        if [[ ${#keys[@]} -gt 3 ]]; then
            local keys_to_remove=("${keys[@]:3}")
            
            for old_key in "${keys_to_remove[@]}"; do
                if rm "$old_key"; then
                    log_info "Removed old key: $(basename "$old_key")"
                else
                    log_warning "Failed to remove old key: $(basename "$old_key")"
                fi
            done
        fi
    done
}

# Main function
main() {
    # Handle special operations
    if [[ "$LIST_KEYS" == "true" ]]; then
        list_keys
        return 0
    fi
    
    if [[ "$CHECK_EXPIRY" == "true" ]]; then
        check_key_expiry
        return $?
    fi
    
    if [[ "$BACKUP_ONLY" == "true" ]]; then
        backup_keys
        return $?
    fi
    
    if [[ -n "$RESTORE_KEY_ID" ]]; then
        restore_keys "$RESTORE_KEY_ID"
        return $?
    fi
    
    # Check if keys need rotation
    if ! check_key_expiry; then
        if [[ "$FORCE" == "false" ]]; then
            echo ""
            read -p "Keys need rotation. Continue? (yes/no): " confirm
            if [[ "$confirm" != "yes" ]]; then
                log_info "Key rotation cancelled by user"
                return 0
            fi
        fi
    else
        if [[ "$FORCE" == "false" ]]; then
            log_info "No keys need rotation at this time"
            return 0
        fi
    fi
    
    # Perform key rotation
    rotate_session_keys
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
