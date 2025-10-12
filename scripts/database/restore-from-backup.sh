#!/bin/bash
# Database Restore from Backup Script
# LUCID-STRICT Layer 1 Core Infrastructure
# Purpose: Restore MongoDB database from backup for disaster recovery
# Compatibility: Distroless, API compliant
# Generated: 2025-01-27

set -e

# Configuration
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lucid}"
MONGO_USER="${MONGO_USER:-lucid}"
MONGO_PASS="${MONGO_PASS:-lucid}"
BACKUP_DIR="${LUCID_BACKUP_DIR:-/data/backups/mongodb}"
TEMP_RESTORE_DIR="${TEMP_RESTORE_DIR:-/tmp/lucid-restore}"
LOG_FILE="${LOG_FILE:-/var/log/lucid/restore.log}"

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

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

echo "========================================"
log_info "🔧 LUCID Database Restore from Backup"
echo "========================================"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] BACKUP_FILE"
    echo ""
    echo "Restore MongoDB database from backup archive"
    echo ""
    echo "Arguments:"
    echo "  BACKUP_FILE    Path to backup archive (.tar.gz, .zip, or .bson)"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -f, --force             Force restore without confirmation"
    echo "  -d, --dry-run           Show what would be restored without executing"
    echo "  -c, --collections       Comma-separated list of collections to restore"
    echo "  -k, --keep-existing     Keep existing data, merge with backup"
    echo "  -v, --verbose           Enable verbose output"
    echo ""
    echo "Environment Variables:"
    echo "  MONGO_HOST              MongoDB host (default: localhost)"
    echo "  MONGO_PORT              MongoDB port (default: 27017)"
    echo "  MONGO_DB                Database name (default: lucid)"
    echo "  MONGO_USER              MongoDB username (default: lucid)"
    echo "  MONGO_PASS              MongoDB password (default: lucid)"
    echo "  LUCID_BACKUP_DIR        Backup directory (default: /data/backups/mongodb)"
    echo "  TEMP_RESTORE_DIR        Temporary restore directory (default: /tmp/lucid-restore)"
    echo ""
    echo "Examples:"
    echo "  $0 /data/backups/mongodb/lucid-backup-20250127.tar.gz"
    echo "  $0 --collections sessions,authentication /data/backups/mongodb/partial-backup.tar.gz"
    echo "  $0 --dry-run --verbose /data/backups/mongodb/full-backup.tar.gz"
}

# Parse command line arguments
FORCE=false
DRY_RUN=false
COLLECTIONS=""
KEEP_EXISTING=false
VERBOSE=false
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
        -c|--collections)
            COLLECTIONS="$2"
            shift 2
            ;;
        -k|--keep-existing)
            KEEP_EXISTING=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
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

# Validate backup file argument
if [[ -z "$BACKUP_FILE" ]]; then
    log_error "Backup file is required"
    show_usage
    exit 1
fi

# Check if backup file exists
if [[ ! -f "$BACKUP_FILE" ]]; then
    log_error "Backup file does not exist: $BACKUP_FILE"
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

# Function to get backup file info
get_backup_info() {
    local backup_file="$1"
    local file_ext="${backup_file##*.}"
    
    log_info "Analyzing backup file: $backup_file"
    
    case "$file_ext" in
        "tar"|"gz")
            if [[ "$VERBOSE" == "true" ]]; then
                tar -tzf "$backup_file" | head -20
                echo "..."
                echo "Total files: $(tar -tzf "$backup_file" | wc -l)"
            fi
            ;;
        "zip")
            if [[ "$VERBOSE" == "true" ]]; then
                unzip -l "$backup_file" | head -20
                echo "..."
                echo "Total files: $(unzip -l "$backup_file" | tail -1 | awk '{print $2}')"
            fi
            ;;
        "bson")
            log_info "Single BSON file detected"
            ;;
        *)
            log_warning "Unknown backup format: $file_ext"
            ;;
    esac
}

# Function to extract backup
extract_backup() {
    local backup_file="$1"
    local extract_dir="$2"
    local file_ext="${backup_file##*.}"
    
    log_info "Extracting backup to: $extract_dir"
    
    # Clean and create extract directory
    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"
    
    case "$file_ext" in
        "tar"|"gz")
            if tar -xzf "$backup_file" -C "$extract_dir"; then
                log_success "Backup extracted successfully"
            else
                log_error "Failed to extract tar.gz backup"
                return 1
            fi
            ;;
        "zip")
            if unzip -q "$backup_file" -d "$extract_dir"; then
                log_success "Backup extracted successfully"
            else
                log_error "Failed to extract zip backup"
                return 1
            fi
            ;;
        "bson")
            cp "$backup_file" "$extract_dir/"
            log_success "BSON file copied"
            ;;
        *)
            log_error "Unsupported backup format: $file_ext"
            return 1
            ;;
    esac
}

# Function to restore collections
restore_collections() {
    local restore_dir="$1"
    local collections_to_restore="$2"
    
    log_info "Starting collection restore..."
    
    local auth_string=""
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASS" ]]; then
        auth_string="-u $MONGO_USER -p $MONGO_PASS --authenticationDatabase admin"
    fi
    
    # Find BSON files in restore directory
    local bson_files=($(find "$restore_dir" -name "*.bson" -type f))
    
    if [[ ${#bson_files[@]} -eq 0 ]]; then
        log_error "No BSON files found in backup"
        return 1
    fi
    
    local restored_count=0
    local failed_count=0
    
    for bson_file in "${bson_files[@]}"; do
        local collection_name=$(basename "$bson_file" .bson)
        local collection_path="$bson_file"
        
        # Check if we should restore this collection
        if [[ -n "$collections_to_restore" ]]; then
            if [[ ! ",$collections_to_restore," =~ ",$collection_name," ]]; then
                log_info "Skipping collection: $collection_name"
                continue
            fi
        fi
        
        log_info "Restoring collection: $collection_name"
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY RUN: Would restore $collection_name from $collection_path"
            ((restored_count++))
            continue
        fi
        
        # Drop collection if not keeping existing data
        if [[ "$KEEP_EXISTING" == "false" ]]; then
            log_info "Dropping existing collection: $collection_name"
            mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" \
                --eval "db.$collection_name.drop()" &>/dev/null || true
        fi
        
        # Restore collection
        if mongorestore --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string \
            --db "$MONGO_DB" --collection "$collection_name" "$collection_path"; then
            log_success "Restored collection: $collection_name"
            ((restored_count++))
        else
            log_error "Failed to restore collection: $collection_name"
            ((failed_count++))
        fi
    done
    
    log_info "Restore completed: $restored_count successful, $failed_count failed"
    
    if [[ $failed_count -gt 0 ]]; then
        return 1
    fi
    
    return 0
}

# Function to verify restore
verify_restore() {
    local collections_to_verify="$1"
    
    log_info "Verifying restored data..."
    
    local auth_string=""
    if [[ -n "$MONGO_USER" && -n "$MONGO_PASS" ]]; then
        auth_string="-u $MONGO_USER -p $MONGO_PASS --authenticationDatabase admin"
    fi
    
    # Get all collections or specific ones
    local collections=""
    if [[ -n "$collections_to_verify" ]]; then
        collections="$collections_to_verify"
    else
        collections=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" \
            --quiet --eval "db.getCollectionNames().join(',')")
    fi
    
    local total_documents=0
    local verified_collections=0
    
    IFS=',' read -ra COLLECTION_ARRAY <<< "$collections"
    for collection in "${COLLECTION_ARRAY[@]}"; do
        collection=$(echo "$collection" | xargs) # trim whitespace
        
        if [[ -z "$collection" ]]; then
            continue
        fi
        
        local count=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" \
            --quiet --eval "db.$collection.countDocuments({})")
        
        log_info "Collection $collection: $count documents"
        total_documents=$((total_documents + count))
        ((verified_collections++))
    done
    
    log_success "Verification complete: $verified_collections collections, $total_documents total documents"
    
    # Test basic operations
    log_info "Testing basic operations..."
    local test_result=$(mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" $auth_string "$MONGO_DB" \
        --quiet --eval "
        try {
            db.runCommand({ping: 1});
            print('SUCCESS');
        } catch (e) {
            print('FAILED: ' + e.message);
        }
    ")
    
    if [[ "$test_result" == "SUCCESS" ]]; then
        log_success "Database operations verified"
        return 0
    else
        log_error "Database operations failed: $test_result"
        return 1
    fi
}

# Function to cleanup
cleanup() {
    if [[ -d "$TEMP_RESTORE_DIR" ]]; then
        log_info "Cleaning up temporary files..."
        rm -rf "$TEMP_RESTORE_DIR"
    fi
}

# Main restore function
main() {
    # Test MongoDB connection
    if ! test_mongodb_connection; then
        exit 1
    fi
    
    # Get backup info
    get_backup_info "$BACKUP_FILE"
    
    # Confirmation prompt (unless forced or dry run)
    if [[ "$FORCE" == "false" && "$DRY_RUN" == "false" ]]; then
        echo ""
        log_warning "This will restore data to MongoDB database: $MONGO_DB"
        log_warning "Host: $MONGO_HOST:$MONGO_PORT"
        
        if [[ "$KEEP_EXISTING" == "false" ]]; then
            log_warning "⚠️  EXISTING DATA WILL BE OVERWRITTEN!"
        else
            log_info "Existing data will be preserved (merged)"
        fi
        
        echo ""
        read -p "Are you sure you want to continue? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Restore cancelled by user"
            exit 0
        fi
    fi
    
    # Extract backup
    if ! extract_backup "$BACKUP_FILE" "$TEMP_RESTORE_DIR"; then
        exit 1
    fi
    
    # Restore collections
    if ! restore_collections "$TEMP_RESTORE_DIR" "$COLLECTIONS"; then
        log_error "Collection restore failed"
        cleanup
        exit 1
    fi
    
    # Verify restore (only if not dry run)
    if [[ "$DRY_RUN" == "false" ]]; then
        if ! verify_restore "$COLLECTIONS"; then
            log_error "Restore verification failed"
            cleanup
            exit 1
        fi
    fi
    
    # Cleanup
    cleanup
    
    log_success "Database restore completed successfully!"
    
    # Show summary
    echo ""
    echo "========================================"
    log_info "Restore Summary"
    echo "========================================"
    log_info "Backup file: $BACKUP_FILE"
    log_info "Database: $MONGO_DB"
    log_info "Host: $MONGO_HOST:$MONGO_PORT"
    log_info "Collections: ${COLLECTIONS:-"all"}"
    log_info "Keep existing: $KEEP_EXISTING"
    log_info "Dry run: $DRY_RUN"
    echo "========================================"
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Run main function
main "$@"
