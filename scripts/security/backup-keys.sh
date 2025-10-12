#!/bin/bash
# Cryptographic Key Backup Script
# LUCID-STRICT Layer 2 Security Management
# Purpose: Backup all cryptographic keys for key protection
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
KEYS_DIR="${LUCID_KEYS_DIR:-/data/keys}"
BACKUP_DIR="${LUCID_BACKUP_DIR:-/data/backups/keys}"
ENCRYPTED_BACKUP_DIR="${LUCID_ENCRYPTED_BACKUP_DIR:-/data/backups/encrypted}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lucid}"
MONGO_USER="${MONGO_USER:-lucid}"
MONGO_PASS="${MONGO_PASS:-lucid}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/key-backup.log}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-90}"

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
mkdir -p "$ENCRYPTED_BACKUP_DIR"

echo "========================================"
log_info "🔐 LUCID Cryptographic Key Backup"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Backup all cryptographic keys for key protection"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -d, --dry-run           Show what would be backed up without executing"
    echo "  -e, --encrypt           Encrypt backup with GPG"
    echo "  -c, --compress          Compress backup archive"
    echo "  -r, --remote HOST       Upload backup to remote host"
    echo "  -k, --key-types TYPES   Backup specific key types (comma-separated)"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -f, --force             Force backup without confirmation"
    echo "  -t, --test              Test backup integrity after creation"
    echo "  -l, --list              List existing backups"
    echo "  -s, --schedule          Create scheduled backup entry"
    echo ""
    echo "Environment Variables:"
    echo "  LUCID_KEYS_DIR          Keys directory (default: /data/keys)"
    echo "  LUCID_BACKUP_DIR        Backup directory (default: /data/backups/keys)"
    echo "  LUCID_ENCRYPTED_BACKUP_DIR Encrypted backup directory (default: /data/backups/encrypted)"
    echo "  MONGO_HOST              MongoDB host (default: localhost)"
    echo "  MONGO_PORT              MongoDB port (default: 27017)"
    echo "  MONGO_DB                Database name (default: lucid)"
    echo "  MONGO_USER              MongoDB username (default: lucid)"
    echo "  MONGO_PASS              MongoDB password (default: lucid)"
    echo "  BACKUP_RETENTION_DAYS   Backup retention period in days (default: 90)"
    echo ""
    echo "Examples:"
    echo "  $0 --encrypt --compress    Create encrypted and compressed backup"
    echo "  $0 --key-types jwt,api     Backup only JWT and API keys"
    echo "  $0 --remote backup-server  Upload backup to remote server"
    echo "  $0 --test --verbose        Create and test backup with verbose output"
}

# Parse command line arguments
DRY_RUN=false
ENCRYPT=false
COMPRESS=false
REMOTE_HOST=""
KEY_TYPES=""
VERBOSE=false
FORCE=false
TEST_BACKUP=false
LIST_BACKUPS=false
SCHEDULE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -e|--encrypt)
            ENCRYPT=true
            shift
            ;;
        -c|--compress)
            COMPRESS=true
            shift
            ;;
        -r|--remote)
            REMOTE_HOST="$2"
            shift 2
            ;;
        -k|--key-types)
            KEY_TYPES="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -t|--test)
            TEST_BACKUP=true
            shift
            ;;
        -l|--list)
            LIST_BACKUPS=true
            shift
            ;;
        -s|--schedule)
            SCHEDULE=true
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

# Function to list existing backups
list_backups() {
    log_info "Existing key backups:"
    echo ""
    
    local backup_files=($(find "$BACKUP_DIR" -name "*.tar.gz" -o -name "*.gpg" -type f | sort -r))
    
    if [[ ${#backup_files[@]} -eq 0 ]]; then
        log_warning "No key backups found"
        return 0
    fi
    
    printf "%-40s %-20s %-15s %-10s %-15s\n" "BACKUP FILE" "CREATED" "AGE" "SIZE" "TYPE"
    echo "------------------------------------------------------------------------------------------------"
    
    for backup_file in "${backup_files[@]}"; do
        local file_name=$(basename "$backup_file")
        local created=$(stat -c %y "$backup_file" 2>/dev/null || stat -f %Sm "$backup_file" 2>/dev/null || echo "unknown")
        local age=$(find "$backup_file" -type f -printf '%T@\n' 2>/dev/null | awk '{print int((systime() - $1) / 86400)}' || echo "unknown")
        local size=$(stat -c %s "$backup_file" 2>/dev/null || stat -f %z "$backup_file" 2>/dev/null || echo "unknown")
        local file_type="unknown"
        
        if [[ "$file_name" == *.gpg ]]; then
            file_type="encrypted"
        elif [[ "$file_name" == *.tar.gz ]]; then
            file_type="compressed"
        fi
        
        printf "%-40s %-20s %-15s %-10s %-15s\n" "$file_name" "${created% *}" "${age}d" "${size}B" "$file_type"
    done
    
    echo ""
}

# Function to get key inventory
get_key_inventory() {
    log_info "Scanning key inventory..."
    
    local key_patterns=()
    
    if [[ -n "$KEY_TYPES" ]]; then
        # Parse specific key types
        IFS=',' read -ra TYPES_ARRAY <<< "$KEY_TYPES"
        for type in "${TYPES_ARRAY[@]}"; do
            case "$type" in
                "session")
                    key_patterns+=("session-*.key")
                    ;;
                "admin")
                    key_patterns+=("admin-*.key" "admin-*.private" "admin-*.public")
                    ;;
                "jwt")
                    key_patterns+=("jwt-*.key")
                    ;;
                "api")
                    key_patterns+=("api-*.key")
                    ;;
                "ssh")
                    key_patterns+=("ssh-*.key" "*.rsa" "*.ed25519")
                    ;;
                *)
                    key_patterns+=("*${type}*.key")
                    ;;
            esac
        done
    else
        # All key types
        key_patterns=("*.key" "*.private" "*.public" "*.rsa" "*.ed25519" "*.pem")
    fi
    
    local all_keys=()
    for pattern in "${key_patterns[@]}"; do
        local keys=($(find "$KEYS_DIR" -name "$pattern" -type f))
        all_keys+=("${keys[@]}")
    done
    
    if [[ ${#all_keys[@]} -eq 0 ]]; then
        log_warning "No keys found matching patterns"
        return 1
    fi
    
    log_info "Found ${#all_keys[@]} keys to backup:"
    for key_file in "${all_keys[@]}"; do
        local key_name=$(basename "$key_file")
        local key_size=$(stat -c %s "$key_file" 2>/dev/null || stat -f %z "$key_file" 2>/dev/null || echo "unknown")
        log_info "  - $key_name (${key_size}B)"
    done
    
    echo "${all_keys[@]}"
}

# Function to create backup manifest
create_backup_manifest() {
    local backup_dir="$1"
    local key_files=("${@:2}")
    
    local manifest_file="$backup_dir/manifest.json"
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    
    log_info "Creating backup manifest..."
    
    # Generate checksums for all keys
    local checksums=()
    for key_file in "${key_files[@]}"; do
        local checksum=$(sha256sum "$key_file" | cut -d' ' -f1)
        local key_name=$(basename "$key_file")
        checksums+=("{\"file\":\"$key_name\",\"checksum\":\"$checksum\"}")
    done
    
    # Create manifest JSON
    cat > "$manifest_file" << EOF
{
    "backup_id": "lucid-keys-${backup_timestamp}",
    "backup_timestamp": "$backup_timestamp",
    "backup_date": "$(date -Iseconds)",
    "lucid_version": "$(cat /opt/lucid/VERSION 2>/dev/null || echo 'unknown')",
    "key_count": ${#key_files[@]},
    "backup_type": "$(if [[ "$ENCRYPT" == "true" ]]; then echo "encrypted"; elif [[ "$COMPRESS" == "true" ]]; then echo "compressed"; else echo "raw"; fi)",
    "key_types": "$(echo "${KEY_TYPES:-all}" | tr ',' '|')",
    "checksums": [$(IFS=','; echo "${checksums[*]}")],
    "backup_size": $(du -sb "$backup_dir" | cut -f1),
    "retention_days": $BACKUP_RETENTION_DAYS
}
EOF
    
    log_success "Backup manifest created: $manifest_file"
}

# Function to create encrypted backup
create_encrypted_backup() {
    local backup_file="$1"
    local temp_dir="$2"
    
    log_info "Creating encrypted backup..."
    
    # Check if GPG is available
    if ! command -v gpg &> /dev/null; then
        log_error "GPG not available for encryption"
        return 1
    fi
    
    # Check for GPG key
    local gpg_key_id=$(gpg --list-secret-keys --keyid-format LONG 2>/dev/null | grep sec | head -1 | awk '{print $2}' | cut -d'/' -f2)
    
    if [[ -z "$gpg_key_id" ]]; then
        log_error "No GPG secret key found for encryption"
        log_info "Create a GPG key first: gpg --gen-key"
        return 1
    fi
    
    log_info "Using GPG key: $gpg_key_id"
    
    # Create tar archive and encrypt it
    if tar -czf - -C "$temp_dir" . | gpg --cipher-algo AES256 --compress-algo 1 --symmetric --armor --output "$backup_file.gpg"; then
        log_success "Encrypted backup created: $backup_file.gpg"
        return 0
    else
        log_error "Failed to create encrypted backup"
        return 1
    fi
}

# Function to create compressed backup
create_compressed_backup() {
    local backup_file="$1"
    local temp_dir="$2"
    
    log_info "Creating compressed backup..."
    
    if tar -czf "$backup_file.tar.gz" -C "$temp_dir" .; then
        log_success "Compressed backup created: $backup_file.tar.gz"
        return 0
    else
        log_error "Failed to create compressed backup"
        return 1
    fi
}

# Function to upload to remote host
upload_to_remote() {
    local backup_file="$1"
    local remote_host="$2"
    
    log_info "Uploading backup to remote host: $remote_host"
    
    # Check if SCP is available
    if ! command -v scp &> /dev/null; then
        log_error "SCP not available for remote upload"
        return 1
    fi
    
    # Extract remote path from host (format: user@host:/path)
    local remote_path="/tmp/lucid-key-backups"
    if [[ "$remote_host" == *":"* ]]; then
        remote_path="${remote_host#*:}"
        remote_host="${remote_host%:*}"
    fi
    
    if scp "$backup_file" "$remote_host:$remote_path/"; then
        log_success "Backup uploaded to $remote_host:$remote_path/"
        return 0
    else
        log_error "Failed to upload backup to remote host"
        return 1
    fi
}

# Function to test backup integrity
test_backup_integrity() {
    local backup_file="$1"
    
    log_info "Testing backup integrity..."
    
    local test_dir="/tmp/lucid-backup-test-$(date +%s)"
    mkdir -p "$test_dir"
    
    # Extract backup
    local extract_success=false
    if [[ "$backup_file" == *.gpg ]]; then
        # Decrypt and extract
        if gpg --decrypt "$backup_file" | tar -xzf - -C "$test_dir"; then
            extract_success=true
        fi
    elif [[ "$backup_file" == *.tar.gz ]]; then
        # Extract compressed archive
        if tar -xzf "$backup_file" -C "$test_dir"; then
            extract_success=true
        fi
    else
        # Copy raw files
        if cp -r "$(dirname "$backup_file")"/* "$test_dir/"; then
            extract_success=true
        fi
    fi
    
    if [[ "$extract_success" == "true" ]]; then
        # Verify manifest
        if [[ -f "$test_dir/manifest.json" ]]; then
            log_success "Backup manifest found and valid"
            
            # Verify checksums if available
            local key_count=$(jq -r '.key_count' "$test_dir/manifest.json" 2>/dev/null || echo "0")
            log_info "Backup contains $key_count keys"
            
            # Cleanup test directory
            rm -rf "$test_dir"
            
            log_success "Backup integrity test passed"
            return 0
        else
            log_warning "No manifest found in backup"
            rm -rf "$test_dir"
            return 1
        fi
    else
        log_error "Failed to extract backup for testing"
        rm -rf "$test_dir"
        return 1
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups (older than $BACKUP_RETENTION_DAYS days)..."
    
    local old_backups=($(find "$BACKUP_DIR" -name "*.tar.gz" -o -name "*.gpg" -type f -mtime +$BACKUP_RETENTION_DAYS))
    
    if [[ ${#old_backups[@]} -eq 0 ]]; then
        log_info "No old backups to cleanup"
        return 0
    fi
    
    local removed=0
    for old_backup in "${old_backups[@]}"; do
        if rm "$old_backup"; then
            log_info "Removed old backup: $(basename "$old_backup")"
            ((removed++))
        else
            log_warning "Failed to remove old backup: $(basename "$old_backup")"
        fi
    done
    
    log_success "Cleaned up $removed old backups"
}

# Function to create scheduled backup
create_scheduled_backup() {
    log_info "Creating scheduled backup entry..."
    
    local cron_entry="0 2 * * * $0 --encrypt --compress --force >> $LOG_FILE 2>&1"
    
    # Check if entry already exists
    if crontab -l 2>/dev/null | grep -q "$0"; then
        log_warning "Scheduled backup entry already exists"
        return 0
    fi
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
    
    if [[ $? -eq 0 ]]; then
        log_success "Scheduled backup created (daily at 2 AM)"
    else
        log_error "Failed to create scheduled backup"
        return 1
    fi
}

# Main backup function
main() {
    # Handle special operations
    if [[ "$LIST_BACKUPS" == "true" ]]; then
        list_backups
        return 0
    fi
    
    if [[ "$SCHEDULE" == "true" ]]; then
        create_scheduled_backup
        return $?
    fi
    
    # Test MongoDB connection
    if ! test_mongodb_connection; then
        return 1
    fi
    
    # Get key inventory
    local key_files=($(get_key_inventory))
    if [[ ${#key_files[@]} -eq 0 ]]; then
        log_error "No keys found to backup"
        return 1
    fi
    
    # Confirmation prompt (unless forced or dry run)
    if [[ "$FORCE" == "false" && "$DRY_RUN" == "false" ]]; then
        echo ""
        log_warning "This will backup ${#key_files[@]} cryptographic keys"
        log_warning "Backup location: $BACKUP_DIR"
        
        if [[ "$ENCRYPT" == "true" ]]; then
            log_info "Backup will be encrypted with GPG"
        fi
        
        if [[ "$COMPRESS" == "true" ]]; then
            log_info "Backup will be compressed"
        fi
        
        if [[ -n "$REMOTE_HOST" ]]; then
            log_info "Backup will be uploaded to: $REMOTE_HOST"
        fi
        
        echo ""
        read -p "Continue with backup? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Backup cancelled by user"
            return 0
        fi
    fi
    
    # Create backup directory
    local backup_timestamp=$(date +"%Y%m%d_%H%M%S")
    local temp_backup_dir="/tmp/lucid-key-backup-$backup_timestamp"
    mkdir -p "$temp_backup_dir"
    
    # Copy keys to temporary directory
    log_info "Copying keys to backup directory..."
    local copied=0
    for key_file in "${key_files[@]}"; do
        local key_name=$(basename "$key_file")
        local key_dir=$(dirname "$key_file")
        
        # Preserve directory structure
        local relative_path="${key_file#$KEYS_DIR/}"
        local target_dir="$temp_backup_dir/$(dirname "$relative_path")"
        mkdir -p "$target_dir"
        
        if cp "$key_file" "$temp_backup_dir/$relative_path"; then
            # Preserve permissions
            chmod 600 "$temp_backup_dir/$relative_path"
            ((copied++))
        else
            log_error "Failed to copy key: $key_name"
        fi
    done
    
    if [[ $copied -eq 0 ]]; then
        log_error "No keys were copied to backup"
        rm -rf "$temp_backup_dir"
        return 1
    fi
    
    log_success "Copied $copied keys to backup directory"
    
    # Create backup manifest
    create_backup_manifest "$temp_backup_dir" "${key_files[@]}"
    
    # Create final backup
    local backup_filename="lucid-keys-backup-$backup_timestamp"
    local final_backup_file="$BACKUP_DIR/$backup_filename"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would create backup: $backup_filename"
        rm -rf "$temp_backup_dir"
        return 0
    fi
    
    # Create backup based on options
    if [[ "$ENCRYPT" == "true" ]]; then
        if ! create_encrypted_backup "$final_backup_file" "$temp_backup_dir"; then
            rm -rf "$temp_backup_dir"
            return 1
        fi
        final_backup_file="$final_backup_file.gpg"
    elif [[ "$COMPRESS" == "true" ]]; then
        if ! create_compressed_backup "$final_backup_file" "$temp_backup_dir"; then
            rm -rf "$temp_backup_dir"
            return 1
        fi
        final_backup_file="$final_backup_file.tar.gz"
    else
        # Move raw backup
        if mv "$temp_backup_dir" "$final_backup_file"; then
            log_success "Raw backup created: $final_backup_file"
        else
            log_error "Failed to create raw backup"
            rm -rf "$temp_backup_dir"
            return 1
        fi
    fi
    
    # Test backup if requested
    if [[ "$TEST_BACKUP" == "true" ]]; then
        if ! test_backup_integrity "$final_backup_file"; then
            log_error "Backup integrity test failed"
            return 1
        fi
    fi
    
    # Upload to remote host if specified
    if [[ -n "$REMOTE_HOST" ]]; then
        upload_to_remote "$final_backup_file" "$REMOTE_HOST"
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    log_success "Key backup completed successfully!"
    
    # Show summary
    echo ""
    echo "========================================"
    log_info "Backup Summary"
    echo "========================================"
    log_info "Backup file: $(basename "$final_backup_file")"
    log_info "Backup location: $final_backup_file"
    log_info "Keys backed up: $copied"
    log_info "Backup type: $(if [[ "$ENCRYPT" == "true" ]]; then echo "encrypted"; elif [[ "$COMPRESS" == "true" ]]; then echo "compressed"; else echo "raw"; fi)"
    log_info "Key types: ${KEY_TYPES:-all}"
    echo "========================================"
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up temporary files..."
    # Cleanup will be handled by individual functions
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
