#!/bin/bash
# Admin Key Rotation Script
# LUCID-STRICT Layer 2 Security Management
# Purpose: Rotate admin authentication keys for security compliance
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
LOG_FILE="${LOG_FILE:-/var/log/lucid/admin-key-rotation.log}"
ROTATION_INTERVAL="${ADMIN_ROTATION_INTERVAL:-90}" # days

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
log_info "🔐 LUCID Admin Key Rotation"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Rotate admin authentication keys for security compliance"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --force             Force rotation without confirmation"
    echo "  -d, --dry-run           Show what would be rotated without executing"
    echo "  -b, --backup-only       Only create backup of current keys"
    echo "  -r, --restore KEY_ID    Restore keys from backup"
    echo "  -l, --list              List current admin keys and their ages"
    echo "  -c, --check-expiry      Check if keys need rotation"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -i, --interval DAYS     Set rotation interval in days (default: 90)"
    echo "  -a, --admin-id ADMIN    Rotate keys for specific admin user"
    echo "  -t, --key-type TYPE     Rotate specific key type (jwt, api, ssh, all)"
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_KEYS_DIR          Keys directory (default: /data/keys)"
    echo "  LUCID_BACKUP_DIR        Backup directory (default: /data/backups/keys)"
    echo "  MONGO_HOST              MongoDB host (default: localhost)"
    echo "  MONGO_PORT              MongoDB port (default: 27017)"
    echo "  MONGO_DB                Database name (default: lucid)"
    echo "  MONGO_USER              MongoDB username (default: lucid)"
    echo "  MONGO_PASS              MongoDB password (default: lucid)"
    echo "  ADMIN_ROTATION_INTERVAL Admin rotation interval in days (default: 90)"
    echo ""
    echo "Examples:"
    echo "  $0 --check-expiry       Check if admin keys need rotation"
    echo "  $0 --admin-id admin1    Rotate keys for specific admin"
    echo "  $0 --key-type jwt       Rotate only JWT signing keys"
    echo "  $0 --interval 30        Rotate admin keys every 30 days"
}

# Parse command line arguments
FORCE=false
DRY_RUN=false
BACKUP_ONLY=false
RESTORE_KEY_ID=""
LIST_KEYS=false
CHECK_EXPIRY=false
VERBOSE=false
ADMIN_ID=""
KEY_TYPE="all"

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
        -a|--admin-id)
            ADMIN_ID="$2"
            shift 2
            ;;
        -t|--key-type)
            KEY_TYPE="$2"
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

# Validate key type
case "$KEY_TYPE" in
    "jwt"|"api"|"ssh"|"all")
        ;;
    *)
        log_error "Invalid key type: $KEY_TYPE (must be: jwt, api, ssh, all)"
        exit 1
        ;;
esac

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

# Function to generate RSA key pair
generate_rsa_key_pair() {
    local key_id="$1"
    local key_path="$2"
    local key_size="${3:-4096}"
    
    log_info "Generating RSA key pair: $key_id (${key_size} bits)"
    
    # Generate private key
    if openssl genrsa -out "${key_path}.private" "$key_size"; then
        chmod 600 "${key_path}.private"
        log_info "Generated private key: ${key_path}.private"
    else
        log_error "Failed to generate private key: $key_id"
        return 1
    fi
    
    # Generate public key
    if openssl rsa -in "${key_path}.private" -pubout -out "${key_path}.public"; then
        chmod 644 "${key_path}.public"
        log_success "Generated public key: ${key_path}.public"
    else
        log_error "Failed to generate public key: $key_id"
        return 1
    fi
    
    return 0
}

# Function to generate JWT signing key
generate_jwt_key() {
    local key_id="$1"
    local key_path="$2"
    
    log_info "Generating JWT signing key: $key_id"
    
    # Generate 256-bit key for HS256 or 512-bit for HS512
    if openssl rand -out "$key_path" 64; then
        chmod 600 "$key_path"
        log_success "Generated JWT signing key: $key_id"
        return 0
    else
        log_error "Failed to generate JWT signing key: $key_id"
        return 1
    fi
}

# Function to generate API key
generate_api_key() {
    local key_id="$1"
    local key_path="$2"
    
    log_info "Generating API key: $key_id"
    
    # Generate 32-byte API key
    local api_key=$(openssl rand -hex 32)
    
    # Store API key with metadata
    cat > "$key_path" << EOF
{
    "api_key": "$api_key",
    "key_id": "$key_id",
    "created_at": "$(date -Iseconds)",
    "key_type": "api",
    "permissions": ["admin", "read", "write"],
    "expires_at": "$(date -d "+$ROTATION_INTERVAL days" -Iseconds)"
}
EOF
    
    chmod 600 "$key_path"
    log_success "Generated API key: $key_id"
    return 0
}

# Function to backup current keys
backup_admin_keys() {
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_path="$BACKUP_DIR/admin-keys-backup-$backup_timestamp"
    
    log_info "Creating admin key backup: $backup_path"
    
    mkdir -p "$backup_path"
    
    # Backup admin key files
    local key_patterns=("admin-*.key" "admin-*.private" "admin-*.public" "jwt-*.key" "api-*.key")
    local backed_up=0
    
    for pattern in "${key_patterns[@]}"; do
        local key_files=($(find "$KEYS_DIR" -name "$pattern" -type f))
        
        for key_file in "${key_files[@]}"; do
            local key_name=$(basename "$key_file")
            if cp "$key_file" "$backup_path/$key_name"; then
                log_info "Backed up key: $key_name"
                ((backed_up++))
            else
                log_error "Failed to backup key: $key_name"
            fi
        done
    done
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "backup_timestamp": "$backup_timestamp",
    "backup_date": "$(date -Iseconds)",
    "keys_backed_up": $backed_up,
    "rotation_interval": $ROTATION_INTERVAL,
    "key_types": ["admin", "jwt", "api"],
    "lucid_version": "$(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')"
}
EOF
    
    # Compress backup
    if tar -czf "$backup_path.tar.gz" -C "$(dirname "$backup_path")" "$(basename "$backup_path")"; then
        rm -rf "$backup_path"
        log_success "Admin key backup created: $backup_path.tar.gz"
        return 0
    else
        log_error "Failed to compress backup"
        return 1
    fi
}

# Function to restore admin keys from backup
restore_admin_keys() {
    local key_id="$1"
    
    if [[ -z "$key_id" ]]; then
        log_error "Key ID required for restore"
        return 1
    fi
    
    log_info "Restoring admin keys from backup: $key_id"
    
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
    local temp_restore_dir="/tmp/lucid-admin-key-restore-$(date +%s)"
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
    local key_dir=$(find "$temp_restore_dir" -name "*.key" -o -name "*.private" -o -name "*.public" | head -1 | xargs dirname)
    
    if [[ -n "$key_dir" ]]; then
        for key_file in "$key_dir"/*; do
            if [[ -f "$key_file" ]]; then
                local key_name=$(basename "$key_file")
                local target_path="$KEYS_DIR/$key_name"
                
                if cp "$key_file" "$target_path"; then
                    # Set appropriate permissions
                    if [[ "$key_name" == *.private ]]; then
                        chmod 600 "$target_path"
                    elif [[ "$key_name" == *.public ]]; then
                        chmod 644 "$target_path"
                    else
                        chmod 600 "$target_path"
                    fi
                    
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
    
    log_success "Admin key restore completed: $restored keys restored"
    return 0
}

# Function to list current admin keys
list_admin_keys() {
    log_info "Current admin keys:"
    echo ""
    
    local key_patterns=("admin-*.key" "admin-*.private" "admin-*.public" "jwt-*.key" "api-*.key")
    local all_keys=()
    
    # Collect all admin keys
    for pattern in "${key_patterns[@]}"; do
        local keys=($(find "$KEYS_DIR" -name "$pattern" -type f))
        all_keys+=("${keys[@]}")
    done
    
    if [[ ${#all_keys[@]} -eq 0 ]]; then
        log_warning "No admin keys found"
        return 0
    fi
    
    printf "%-40s %-15s %-20s %-10s %-15s\n" "KEY NAME" "TYPE" "CREATED" "AGE" "SIZE"
    echo "------------------------------------------------------------------------------------------------"
    
    for key_file in "${all_keys[@]}"; do
        local key_name=$(basename "$key_file")
        local created=$(stat -c %y "$key_file" 2>/dev/null || stat -f %Sm "$key_file" 2>/dev/null || echo "unknown")
        local age=$(find "$key_file" -type f -printf '%T@\n' 2>/dev/null | awk '{print int((systime() - $1) / 86400)}' || echo "unknown")
        local size=$(stat -c %s "$key_file" 2>/dev/null || stat -f %z "$key_file" 2>/dev/null || echo "unknown")
        
        # Determine key type
        local key_type="unknown"
        if [[ "$key_name" == admin-* ]]; then
            key_type="admin"
        elif [[ "$key_name" == jwt-* ]]; then
            key_type="jwt"
        elif [[ "$key_name" == api-* ]]; then
            key_type="api"
        fi
        
        printf "%-40s %-15s %-20s %-10s %-15s\n" "$key_name" "$key_type" "${created% *}" "${age}d" "${size}B"
    done
    
    echo ""
}

# Function to check admin key expiry
check_admin_key_expiry() {
    log_info "Checking admin key expiry status..."
    echo ""
    
    local expired_keys=()
    local expiring_soon=()
    local current_time=$(date +%s)
    
    local key_patterns=("admin-*.key" "admin-*.private" "jwt-*.key" "api-*.key")
    local all_keys=()
    
    # Collect all admin keys
    for pattern in "${key_patterns[@]}"; do
        local keys=($(find "$KEYS_DIR" -name "$pattern" -type f))
        all_keys+=("${keys[@]}")
    done
    
    if [[ ${#all_keys[@]} -eq 0 ]]; then
        log_warning "No admin keys found"
        return 0
    fi
    
    for key_file in "${all_keys[@]}"; do
        local key_name=$(basename "$key_file")
        local key_time=$(stat -c %Y "$key_file" 2>/dev/null || stat -f %m "$key_file" 2>/dev/null || echo "0")
        local key_age=$(( (current_time - key_time) / 86400 ))
        
        if [[ $key_age -ge $ROTATION_INTERVAL ]]; then
            expired_keys+=("$key_name")
        elif [[ $key_age -ge $((ROTATION_INTERVAL - 14)) ]]; then
            expiring_soon+=("$key_name")
        fi
    done
    
    if [[ ${#expired_keys[@]} -gt 0 ]]; then
        log_error "Expired admin keys found (${#expired_keys[@]}):"
        for key in "${expired_keys[@]}"; do
            echo "  - $key"
        done
        echo ""
    fi
    
    if [[ ${#expiring_soon[@]} -gt 0 ]]; then
        log_warning "Admin keys expiring soon (${#expiring_soon[@]}):"
        for key in "${expiring_soon[@]}"; do
            echo "  - $key"
        done
        echo ""
    fi
    
    if [[ ${#expired_keys[@]} -eq 0 && ${#expiring_soon[@]} -eq 0 ]]; then
        log_success "All admin keys are within rotation interval"
        return 0
    else
        return 1
    fi
}

# Function to rotate admin keys
rotate_admin_keys() {
    log_info "Starting admin key rotation..."
    
    # Test MongoDB connection
    if ! test_mongodb_connection; then
        return 1
    fi
    
    # Backup current keys first
    if ! backup_admin_keys; then
        log_error "Failed to backup current keys"
        return 1
    fi
    
    local generated=0
    local timestamp=$(date +%Y%m%d-%H%M%S)
    
    # Generate new admin keys based on type
    case "$KEY_TYPE" in
        "jwt"|"all")
            local jwt_key_id="jwt-admin-${timestamp}"
            local jwt_key_path="$KEYS_DIR/$jwt_key_id.key"
            
            if [[ "$DRY_RUN" == "true" ]]; then
                log_info "DRY RUN: Would generate JWT key $jwt_key_id"
            else
                if generate_jwt_key "$jwt_key_id" "$jwt_key_path"; then
                    ((generated++))
                fi
            fi
            ;;
    esac
    
    case "$KEY_TYPE" in
        "api"|"all")
            local api_key_id="api-admin-${timestamp}"
            local api_key_path="$KEYS_DIR/$api_key_id.key"
            
            if [[ "$DRY_RUN" == "true" ]]; then
                log_info "DRY RUN: Would generate API key $api_key_id"
            else
                if generate_api_key "$api_key_id" "$api_key_path"; then
                    ((generated++))
                fi
            fi
            ;;
    esac
    
    case "$KEY_TYPE" in
        "ssh"|"all")
            local admin_key_id="admin-${ADMIN_ID:-default}-${timestamp}"
            local admin_key_path="$KEYS_DIR/$admin_key_id"
            
            if [[ "$DRY_RUN" == "true" ]]; then
                log_info "DRY RUN: Would generate admin SSH key pair $admin_key_id"
            else
                if generate_rsa_key_pair "$admin_key_id" "$admin_key_path" 4096; then
                    ((generated++))
                fi
            fi
            ;;
    esac
    
    if [[ "$DRY_RUN" == "false" ]]; then
        log_success "Generated $generated new admin keys"
        
        # Update database with new key references
        update_admin_database_keys
        
        # Clean up old keys (keep last 2 versions)
        cleanup_old_admin_keys
    else
        log_info "DRY RUN: Would generate $generated new admin keys"
    fi
    
    return 0
}

# Function to update database with new admin key references
update_admin_database_keys() {
    log_info "Updating database admin key references..."
    
    local auth_string=""
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASS" ]]; then
        auth_string="-u $MONGO_USER -p $MONGO_PASS --authenticationDatabase admin"
    fi
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    
    # Update admin key metadata in database
    local key_update_result=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" \
        --quiet --eval "
        try {
            var adminId = '$ADMIN_ID' || 'default';
            db.admin_keys.updateOne(
                { admin_id: adminId },
                { 
                    \$set: { 
                        current_key_id: 'admin-' + adminId + '-$timestamp',
                        last_rotated: new Date(),
                        rotation_count: db.admin_keys.findOne({admin_id: adminId})?.rotation_count + 1 || 1,
                        key_types: '$KEY_TYPE'
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
        log_success "Database admin key references updated"
    else
        log_warning "Failed to update database: $key_update_result"
    fi
}

# Function to cleanup old admin keys
cleanup_old_admin_keys() {
    log_info "Cleaning up old admin keys..."
    
    local key_patterns=("admin-*.key" "admin-*.private" "admin-*.public" "jwt-*.key" "api-*.key")
    
    for pattern in "${key_patterns[@]}"; do
        # Find all keys matching pattern, sorted by modification time
        local keys=($(find "$KEYS_DIR" -name "$pattern" -type f -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-))
        
        # Keep only the 2 most recent keys
        if [[ ${#keys[@]} -gt 2 ]]; then
            local keys_to_remove=("${keys[@]:2}")
            
            for old_key in "${keys_to_remove[@]}"; do
                if rm "$old_key"; then
                    log_info "Removed old admin key: $(basename "$old_key")"
                else
                    log_warning "Failed to remove old admin key: $(basename "$old_key")"
                fi
            done
        fi
    done
}

# Main function
main() {
    # Handle special operations
    if [[ "$LIST_KEYS" == "true" ]]; then
        list_admin_keys
        return 0
    fi
    
    if [[ "$CHECK_EXPIRY" == "true" ]]; then
        check_admin_key_expiry
        return $?
    fi
    
    if [[ "$BACKUP_ONLY" == "true" ]]; then
        backup_admin_keys
        return $?
    fi
    
    if [[ -n "$RESTORE_KEY_ID" ]]; then
        restore_admin_keys "$RESTORE_KEY_ID"
        return $?
    fi
    
    # Check if keys need rotation
    if ! check_admin_key_expiry; then
        if [[ "$FORCE" == "false" ]]; then
            echo ""
            read -p "Admin keys need rotation. Continue? (yes/no): " confirm
            if [[ "$confirm" != "yes" ]]; then
                log_info "Admin key rotation cancelled by user"
                return 0
            fi
        fi
    else
        if [[ "$FORCE" == "false" ]]; then
            log_info "No admin keys need rotation at this time"
            return 0
        fi
    fi
    
    # Perform admin key rotation
    rotate_admin_keys
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up..."
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
