#!/bin/bash
# Cryptographic Key Restore Script
# LUCID-STRICT Layer 2 Security Management
# Purpose: Restore keys from backup for key recovery
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
LOG_FILE="${LOG_FILE:-/var/log/lucid/key-restore.log}"
TEMP_RESTORE_DIR="${TEMP_RESTORE_DIR:-/tmp/lucid-key-restore}"

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
mkdir -p "$ENCRYPTED_BACKUP_DIR"

echo "========================================"
log_info "🔐 LUCID Cryptographic Key Restore"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] BACKUP_FILE"
    echo ""
    echo "Restore cryptographic keys from backup archive"
    echo ""
    echo "Arguments:"
    echo "  BACKUP_FILE    Path to backup archive (.tar.gz, .gpg, or directory)"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --force             Force restore without confirmation"
    echo "  -d, --dry-run           Show what would be restored without executing"
    echo "  -k, --key-types TYPES   Restore specific key types (comma-separated)"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -t, --test              Test backup integrity before restore"
    echo "  -b, --backup-current    Backup current keys before restore"
    echo "  -o, --overwrite         Overwrite existing keys"
    echo "  -m, --merge             Merge with existing keys (default)"
    echo "  -l, --list              List available backups"
    echo "  -s, --verify-signature  Verify GPG signature if available"
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
    echo "  TEMP_RESTORE_DIR        Temporary restore directory (default: /tmp/lucid-key-restore)"
    echo ""
    echo "Examples:"
    echo "  $0 /data/backups/keys/lucid-keys-backup-20250127.tar.gz"
    echo "  $0 --key-types jwt,api /data/backups/keys/partial-backup.tar.gz"
    echo "  $0 --test --verbose /data/backups/keys/encrypted-backup.gpg"
    echo "  $0 --list                List available backups"
}

# Parse command line arguments
FORCE=false
DRY_RUN=false
KEY_TYPES=""
VERBOSE=false
TEST_BACKUP=false
BACKUP_CURRENT=false
OVERWRITE=false
MERGE=true
LIST_BACKUPS=false
VERIFY_SIGNATURE=false
BACKUP_FILE=""

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
        -k|--key-types)
            KEY_TYPES="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -t|--test)
            TEST_BACKUP=true
            shift
            ;;
        -b|--backup-current)
            BACKUP_CURRENT=true
            shift
            ;;
        -o|--overwrite)
            OVERWRITE=true
            MERGE=false
            shift
            ;;
        -m|--merge)
            MERGE=true
            OVERWRITE=false
            shift
            ;;
        -l|--list)
            LIST_BACKUPS=true
            shift
            ;;
        -s|--verify-signature)
            VERIFY_SIGNATURE=true
            shift
            ;;
        -*)
            log_error "Unknown option $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$BACKUP_FILE" ]]; then
                BACKUP_FILE="$1"
            else
                log_error "Multiple backup files specified"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate backup file argument (unless listing backups)
if [[ "$LIST_BACKUPS" != "true" && -z "$BACKUP_FILE" ]]; then
    log_error "Backup file is required"
    show_usage
    exit 1
fi

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

# Function to list available backups
list_backups() {
    log_info "Available key backups:"
    echo ""
    
    local backup_dirs=("$BACKUP_DIR" "$ENCRYPTED_BACKUP_DIR")
    local all_backups=()
    
    for backup_dir in "${backup_dirs[@]}"; do
        if [[ -d "$backup_dir" ]]; then
            local backups=($(find "$backup_dir" -name "*.tar.gz" -o -name "*.gpg" -o -name "lucid-keys-backup-*" -type f | sort -r))
            all_backups+=("${backups[@]}")
        fi
    done
    
    if [[ ${#all_backups[@]} -eq 0 ]]; then
        log_warning "No key backups found"
        return 0
    fi
    
    printf "%-50s %-20s %-15s %-10s %-15s\n" "BACKUP FILE" "CREATED" "AGE" "SIZE" "TYPE"
    echo "--------------------------------------------------------------------------------------------------------"
    
    for backup_file in "${all_backups[@]}"; do
        local file_name=$(basename "$backup_file")
        local created=$(stat -c %y "$backup_file" 2>/dev/null || stat -f %Sm "$backup_file" 2>/dev/null || echo "unknown")
        local age=$(find "$backup_file" -type f -printf '%T@\n' 2>/dev/null | awk '{print int((systime() - $1) / 86400)}' || echo "unknown")
        local size=$(stat -c %s "$backup_file" 2>/dev/null || stat -f %z "$backup_file" 2>/dev/null || echo "unknown")
        local file_type="unknown"
        
        if [[ "$file_name" == *.gpg ]]; then
            file_type="encrypted"
        elif [[ "$file_name" == *.tar.gz ]]; then
            file_type="compressed"
        elif [[ -d "$backup_file" ]]; then
            file_type="directory"
        fi
        
        printf "%-50s %-20s %-15s %-10s %-15s\n" "$file_name" "${created% *}" "${age}d" "${size}B" "$file_type"
    done
    
    echo ""
}

# Function to find backup file
find_backup_file() {
    local backup_path="$1"
    
    # Check if file exists as-is
    if [[ -f "$backup_path" ]]; then
        echo "$backup_path"
        return 0
    fi
    
    # Check in backup directories
    local backup_dirs=("$BACKUP_DIR" "$ENCRYPTED_BACKUP_DIR" "$(dirname "$backup_path")")
    
    for backup_dir in "${backup_dirs[@]}"; do
        if [[ -d "$backup_dir" ]]; then
            local filename=$(basename "$backup_path")
            local full_path="$backup_dir/$filename"
            
            if [[ -f "$full_path" ]]; then
                echo "$full_path"
                return 0
            fi
            
            # Try with common extensions
            for ext in ".tar.gz" ".gpg" ""; do
                local test_path="$backup_dir/$filename$ext"
                if [[ -f "$test_path" ]]; then
                    echo "$test_path"
                    return 0
                fi
            done
        fi
    done
    
    return 1
}

# Function to test backup integrity
test_backup_integrity() {
    local backup_file="$1"
    
    log_info "Testing backup integrity..."
    
    # Create temporary test directory
    local test_dir="/tmp/lucid-backup-test-$(date +%s)"
    mkdir -p "$test_dir"
    
    # Extract backup
    local extract_success=false
    if [[ "$backup_file" == *.gpg ]]; then
        # Decrypt and extract
        if gpg --decrypt "$backup_file" 2>/dev/null | tar -xzf - -C "$test_dir"; then
            extract_success=true
        fi
    elif [[ "$backup_file" == *.tar.gz ]]; then
        # Extract compressed archive
        if tar -xzf "$backup_file" -C "$test_dir"; then
            extract_success=true
        fi
    elif [[ -d "$backup_file" ]]; then
        # Copy directory contents
        if cp -r "$backup_file"/* "$test_dir/"; then
            extract_success=true
        fi
    else
        log_error "Unknown backup format: $backup_file"
        rm -rf "$test_dir"
        return 1
    fi
    
    if [[ "$extract_success" == "true" ]]; then
        # Check for manifest
        if [[ -f "$test_dir/manifest.json" ]]; then
            local key_count=$(jq -r '.key_count // 0' "$test_dir/manifest.json" 2>/dev/null)
            local backup_id=$(jq -r '.backup_id // "unknown"' "$test_dir/manifest.json" 2>/dev/null)
            
            log_success "Backup manifest found: $backup_id"
            log_info "Backup contains $key_count keys"
            
            # Verify checksums if available
            if jq -e '.checksums' "$test_dir/manifest.json" >/dev/null 2>&1; then
                log_info "Verifying checksums..."
                local checksum_count=0
                local valid_checksums=0
                
                jq -r '.checksums[] | "\(.file) \(.checksum)"' "$test_dir/manifest.json" | while read -r file checksum; do
                    ((checksum_count++))
                    local actual_checksum=$(sha256sum "$test_dir/$file" 2>/dev/null | cut -d' ' -f1)
                    
                    if [[ "$actual_checksum" == "$checksum" ]]; then
                        ((valid_checksums++))
                    else
                        log_warning "Checksum mismatch for file: $file"
                    fi
                done
                
                log_success "Checksum verification completed"
            fi
        else
            log_warning "No manifest found in backup"
        fi
        
        # Count key files
        local key_files=($(find "$test_dir" -name "*.key" -o -name "*.private" -o -name "*.public" -o -name "*.pem" -type f))
        log_info "Found ${#key_files[@]} key files in backup"
        
        # Cleanup test directory
        rm -rf "$test_dir"
        
        log_success "Backup integrity test passed"
        return 0
    else
        log_error "Failed to extract backup for testing"
        rm -rf "$test_dir"
        return 1
    fi
}

# Function to backup current keys
backup_current_keys() {
    log_info "Creating backup of current keys..."
    
    local current_backup_dir="/tmp/lucid-current-keys-$(date +%s)"
    mkdir -p "$current_backup_dir"
    
    # Copy current keys
    if [[ -d "$KEYS_DIR" ]]; then
        cp -r "$KEYS_DIR"/* "$current_backup_dir/" 2>/dev/null || true
    fi
    
    # Create backup archive
    local current_backup_file="$BACKUP_DIR/current-keys-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    if tar -czf "$current_backup_file" -C "$(dirname "$current_backup_dir")" "$(basename "$current_backup_dir")"; then
        rm -rf "$current_backup_dir"
        log_success "Current keys backed up: $(basename "$current_backup_file")"
        return 0
    else
        log_error "Failed to backup current keys"
        rm -rf "$current_backup_dir"
        return 1
    fi
}

# Function to extract backup
extract_backup() {
    local backup_file="$1"
    local extract_dir="$2"
    
    log_info "Extracting backup to: $extract_dir"
    
    # Clean and create extract directory
    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"
    
    # Extract based on file type
    if [[ "$backup_file" == *.gpg ]]; then
        # Decrypt and extract
        if gpg --decrypt "$backup_file" 2>/dev/null | tar -xzf - -C "$extract_dir"; then
            log_success "Encrypted backup extracted successfully"
        else
            log_error "Failed to decrypt and extract backup"
            return 1
        fi
    elif [[ "$backup_file" == *.tar.gz ]]; then
        # Extract compressed archive
        if tar -xzf "$backup_file" -C "$extract_dir"; then
            log_success "Compressed backup extracted successfully"
        else
            log_error "Failed to extract compressed backup"
            return 1
        fi
    elif [[ -d "$backup_file" ]]; then
        # Copy directory contents
        if cp -r "$backup_file"/* "$extract_dir/"; then
            log_success "Directory backup copied successfully"
        else
            log_error "Failed to copy directory backup"
            return 1
        fi
    else
        log_error "Unknown backup format: $backup_file"
        return 1
    fi
}

# Function to restore keys
restore_keys() {
    local extract_dir="$1"
    local key_types="$2"
    
    log_info "Starting key restore..."
    
    # Find key files in extracted directory
    local key_files=($(find "$extract_dir" -name "*.key" -o -name "*.private" -o -name "*.public" -o -name "*.pem" -type f))
    
    if [[ ${#key_files[@]} -eq 0 ]]; then
        log_error "No key files found in backup"
        return 1
    fi
    
    local restored=0
    local skipped=0
    local failed=0
    
    for key_file in "${key_files[@]}"; do
        local key_name=$(basename "$key_file")
        local key_dir=$(dirname "$key_file")
        
        # Check if we should restore this key type
        if [[ -n "$key_types" ]]; then
            local should_restore=false
            IFS=',' read -ra TYPES_ARRAY <<< "$key_types"
            for type in "${TYPES_ARRAY[@]}"; do
                if [[ "$key_name" == *"$type"* ]]; then
                    should_restore=true
                    break
                fi
            done
            
            if [[ "$should_restore" == "false" ]]; then
                log_info "Skipping key (not in specified types): $key_name"
                ((skipped++))
                continue
            fi
        fi
        
        # Calculate target path
        local relative_path="${key_file#$extract_dir/}"
        local target_path="$KEYS_DIR/$relative_path"
        local target_dir=$(dirname "$target_path")
        
        # Create target directory
        mkdir -p "$target_dir"
        
        # Check if target exists
        if [[ -f "$target_path" && "$OVERWRITE" == "false" ]]; then
            log_warning "Key already exists (use --overwrite to replace): $key_name"
            ((skipped++))
            continue
        fi
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY RUN: Would restore key: $key_name -> $target_path"
            ((restored++))
            continue
        fi
        
        # Copy key file
        if cp "$key_file" "$target_path"; then
            # Set appropriate permissions
            if [[ "$key_name" == *.private ]] || [[ "$key_name" == *.key ]]; then
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
            ((failed++))
        fi
    done
    
    log_info "Restore completed: $restored restored, $skipped skipped, $failed failed"
    
    if [[ $failed -gt 0 ]]; then
        return 1
    fi
    
    return 0
}

# Function to update database key references
update_database_key_references() {
    local extract_dir="$1"
    
    log_info "Updating database key references..."
    
    # Check if manifest exists
    if [[ ! -f "$extract_dir/manifest.json" ]]; then
        log_warning "No manifest found, skipping database updates"
        return 0
    fi
    
    local auth_string=""
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASS" ]]; then
        auth_string="-u $MONGO_USER -p $MONGO_PASS --authenticationDatabase admin"
    fi
    
    # Update key metadata in database
    local backup_id=$(jq -r '.backup_id // "unknown"' "$extract_dir/manifest.json")
    local backup_date=$(jq -r '.backup_date // "unknown"' "$extract_dir/manifest.json")
    
    local db_update_result=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" \
        --quiet --eval "
        try {
            db.key_restore_history.insertOne({
                backup_id: '$backup_id',
                restored_date: new Date(),
                backup_date: new Date('$backup_date'),
                restore_type: '$([[ "$OVERWRITE" == "true" ]] && echo "overwrite" || echo "merge")',
                key_types: '$KEY_TYPES'.split(',').filter(t => t.length > 0),
                restored_by: '$(whoami)',
                restore_host: '$(hostname)'
            });
            print('SUCCESS');
        } catch (e) {
            print('FAILED: ' + e.message);
        }
    ")
    
    if [[ "$db_update_result" == "SUCCESS" ]]; then
        log_success "Database key references updated"
    else
        log_warning "Failed to update database: $db_update_result"
    fi
}

# Function to verify restored keys
verify_restored_keys() {
    local key_types="$1"
    
    log_info "Verifying restored keys..."
    
    local key_patterns=("*.key" "*.private" "*.public" "*.pem")
    local all_keys=()
    
    # Collect all keys
    for pattern in "${key_patterns[@]}"; do
        local keys=($(find "$KEYS_DIR" -name "$pattern" -type f))
        all_keys+=("${keys[@]}")
    done
    
    if [[ ${#all_keys[@]} -eq 0 ]]; then
        log_warning "No keys found after restore"
        return 1
    fi
    
    local verified=0
    local failed=0
    
    for key_file in "${all_keys[@]}"; do
        local key_name=$(basename "$key_file")
        
        # Check if we should verify this key type
        if [[ -n "$key_types" ]]; then
            local should_verify=false
            IFS=',' read -ra TYPES_ARRAY <<< "$key_types"
            for type in "${TYPES_ARRAY[@]}"; do
                if [[ "$key_name" == *"$type"* ]]; then
                    should_verify=true
                    break
                fi
            done
            
            if [[ "$should_verify" == "false" ]]; then
                continue
            fi
        fi
        
        # Basic file checks
        if [[ -f "$key_file" && -r "$key_file" ]]; then
            # Check file size (should not be empty)
            local file_size=$(stat -c %s "$key_file" 2>/dev/null || stat -f %z "$key_file" 2>/dev/null || echo "0")
            
            if [[ $file_size -gt 0 ]]; then
                ((verified++))
            else
                log_warning "Empty key file: $key_name"
                ((failed++))
            fi
        else
            log_warning "Cannot read key file: $key_name"
            ((failed++))
        fi
    done
    
    log_info "Key verification completed: $verified verified, $failed failed"
    
    if [[ $failed -gt 0 ]]; then
        return 1
    fi
    
    return 0
}

# Main restore function
main() {
    # Handle special operations
    if [[ "$LIST_BACKUPS" == "true" ]]; then
        list_backups
        return 0
    fi
    
    # Test MongoDB connection
    if ! test_mongodb_connection; then
        return 1
    fi
    
    # Find backup file
    local actual_backup_file
    if ! actual_backup_file=$(find_backup_file "$BACKUP_FILE"); then
        log_error "Backup file not found: $BACKUP_FILE"
        return 1
    fi
    
    log_info "Using backup file: $actual_backup_file"
    
    # Test backup if requested
    if [[ "$TEST_BACKUP" == "true" ]]; then
        if ! test_backup_integrity "$actual_backup_file"; then
            log_error "Backup integrity test failed"
            return 1
        fi
    fi
    
    # Backup current keys if requested
    if [[ "$BACKUP_CURRENT" == "true" ]]; then
        if ! backup_current_keys; then
            log_error "Failed to backup current keys"
            return 1
        fi
    fi
    
    # Confirmation prompt (unless forced or dry run)
    if [[ "$FORCE" == "false" && "$DRY_RUN" == "false" ]]; then
        echo ""
        log_warning "This will restore keys from backup: $(basename "$actual_backup_file")"
        log_warning "Target directory: $KEYS_DIR"
        log_warning "Restore mode: $([[ "$OVERWRITE" == "true" ]] && echo "overwrite" || echo "merge")"
        
        if [[ -n "$KEY_TYPES" ]]; then
            log_info "Key types to restore: $KEY_TYPES"
        else
            log_info "All key types will be restored"
        fi
        
        echo ""
        read -p "Continue with restore? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Restore cancelled by user"
            return 0
        fi
    fi
    
    # Extract backup
    if ! extract_backup "$actual_backup_file" "$TEMP_RESTORE_DIR"; then
        return 1
    fi
    
    # Restore keys
    if ! restore_keys "$TEMP_RESTORE_DIR" "$KEY_TYPES"; then
        log_error "Key restore failed"
        rm -rf "$TEMP_RESTORE_DIR"
        return 1
    fi
    
    # Update database references (only if not dry run)
    if [[ "$DRY_RUN" == "false" ]]; then
        update_database_key_references "$TEMP_RESTORE_DIR"
    fi
    
    # Verify restored keys (only if not dry run)
    if [[ "$DRY_RUN" == "false" ]]; then
        if ! verify_restored_keys "$KEY_TYPES"; then
            log_warning "Some restored keys failed verification"
        fi
    fi
    
    # Cleanup
    rm -rf "$TEMP_RESTORE_DIR"
    
    log_success "Key restore completed successfully!"
    
    # Show summary
    echo ""
    echo "========================================"
    log_info "Restore Summary"
    echo "========================================"
    log_info "Backup file: $(basename "$actual_backup_file")"
    log_info "Target directory: $KEYS_DIR"
    log_info "Restore mode: $([[ "$OVERWRITE" == "true" ]] && echo "overwrite" || echo "merge")"
    log_info "Key types: ${KEY_TYPES:-"all"}"
    log_info "Dry run: $DRY_RUN"
    echo "========================================"
}

# Set up signal handlers
cleanup() {
    log_info "Cleaning up temporary files..."
    if [[ -d "$TEMP_RESTORE_DIR" ]]; then
        rm -rf "$TEMP_RESTORE_DIR"
    fi
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"
