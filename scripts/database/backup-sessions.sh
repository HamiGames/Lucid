#!/bin/bash
# scripts/database/backup-sessions.sh
# Backup session data for data protection
# LUCID-STRICT: Distroless build method, encrypted backup

set -Eeuo pipefail

# Script metadata
SCRIPT_NAME="$(basename "$0")"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_PATH/../../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups/sessions}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lucid}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Encryption settings
ENCRYPTION_KEY="${ENCRYPTION_KEY:-}"
ENCRYPTION_ALGORITHM="${ENCRYPTION_ALGORITHM:-aes-256-cbc}"

# Logging
log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '[%s][WARN] %s\n' "$SCRIPT_NAME" "$*" >&2; }

# Check prerequisites
check_prerequisites() {
    log "Checking backup prerequisites..."
    
    # Check if mongodump is available
    if ! command -v mongodump >/dev/null 2>&1; then
        die "mongodump not found - please install MongoDB tools"
    fi
    
    # Check if MongoDB is accessible
    if ! mongosh --host "$MONGO_HOST" --port "$MONGO_PORT" --eval "db.runCommand('ping')" --quiet >/dev/null 2>&1; then
        die "Cannot connect to MongoDB at $MONGO_HOST:$MONGO_PORT"
    fi
    
    # Check if encryption tools are available
    if [[ -n "$ENCRYPTION_KEY" ]]; then
        if ! command -v openssl >/dev/null 2>&1; then
            warn "OpenSSL not found - backup will not be encrypted"
            ENCRYPTION_KEY=""
        fi
    fi
    
    log "Prerequisites check completed"
}

# Create backup directory
create_backup_directory() {
    log "Creating backup directory..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$timestamp"
    
    mkdir -p "$backup_path"
    
    log "Backup directory created: $backup_path"
    echo "$backup_path"
}

# Backup sessions collection
backup_sessions() {
    local backup_path="$1"
    
    log "Backing up sessions collection..."
    
    # Create sessions backup
    if mongodump --host "$MONGO_HOST" --port "$MONGO_PORT" \
        --db "$MONGO_DB" --collection "sessions" \
        --out "$backup_path" --gzip; then
        log "✅ Sessions collection backed up successfully"
    else
        die "Failed to backup sessions collection"
    fi
}

# Backup chunks collection
backup_chunks() {
    local backup_path="$1"
    
    log "Backing up chunks collection..."
    
    # Create chunks backup
    if mongodump --host "$MONGO_HOST" --port "$MONGO_PORT" \
        --db "$MONGO_DB" --collection "chunks" \
        --out "$backup_path" --gzip; then
        log "✅ Chunks collection backed up successfully"
    else
        die "Failed to backup chunks collection"
    fi
}

# Backup authentication collection
backup_authentication() {
    local backup_path="$1"
    
    log "Backing up authentication collection..."
    
    # Create authentication backup
    if mongodump --host "$MONGO_HOST" --port "$MONGO_PORT" \
        --db "$MONGO_DB" --collection "authentication" \
        --out "$backup_path" --gzip; then
        log "✅ Authentication collection backed up successfully"
    else
        warn "Failed to backup authentication collection"
    fi
}

# Backup work proofs collection
backup_work_proofs() {
    local backup_path="$1"
    
    log "Backing up work_proofs collection..."
    
    # Create work_proofs backup
    if mongodump --host "$MONGO_HOST" --port "$MONGO_PORT" \
        --db "$MONGO_DB" --collection "work_proofs" \
        --out "$backup_path" --gzip; then
        log "✅ Work_proofs collection backed up successfully"
    else
        warn "Failed to backup work_proofs collection"
    fi
}

# Backup encryption keys collection
backup_encryption_keys() {
    local backup_path="$1"
    
    log "Backing up encryption_keys collection..."
    
    # Create encryption_keys backup
    if mongodump --host "$MONGO_HOST" --port "$MONGO_PORT" \
        --db "$MONGO_DB" --collection "encryption_keys" \
        --out "$backup_path" --gzip; then
        log "✅ Encryption_keys collection backed up successfully"
    else
        warn "Failed to backup encryption_keys collection"
    fi
}

# Encrypt backup
encrypt_backup() {
    local backup_path="$1"
    
    if [[ -z "$ENCRYPTION_KEY" ]]; then
        log "Skipping encryption (no key provided)"
        return 0
    fi
    
    log "Encrypting backup..."
    
    local encrypted_file="$backup_path.tar.gz.enc"
    
    # Create tar archive and encrypt
    if tar -czf - -C "$backup_path" . | \
        openssl enc -$ENCRYPTION_ALGORITHM -salt -pbkdf2 \
        -pass "pass:$ENCRYPTION_KEY" -out "$encrypted_file"; then
        
        # Remove unencrypted backup
        rm -rf "$backup_path"
        
        log "✅ Backup encrypted successfully: $encrypted_file"
    else
        die "Failed to encrypt backup"
    fi
}

# Create backup manifest
create_backup_manifest() {
    local backup_path="$1"
    
    log "Creating backup manifest..."
    
    local manifest_file="$backup_path/backup-manifest.json"
    
    cat > "$manifest_file" << EOF
{
    "backup": {
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "version": "1.0",
        "type": "session_data"
    },
    "source": {
        "host": "$MONGO_HOST",
        "port": "$MONGO_PORT",
        "database": "$MONGO_DB"
    },
    "collections": [
        "sessions",
        "chunks",
        "authentication",
        "work_proofs",
        "encryption_keys"
    ],
    "encryption": {
        "enabled": $([ -n "$ENCRYPTION_KEY" ] && echo "true" || echo "false"),
        "algorithm": "$ENCRYPTION_ALGORITHM"
    },
    "metadata": {
        "script": "$SCRIPT_NAME",
        "project": "Lucid RDP",
        "purpose": "Session data protection"
    }
}
EOF
    
    log "Backup manifest created: $manifest_file"
}

# Verify backup integrity
verify_backup_integrity() {
    local backup_path="$1"
    
    log "Verifying backup integrity..."
    
    # Check if backup files exist
    local collections=("sessions" "chunks" "authentication" "work_proofs" "encryption_keys")
    local missing_collections=()
    
    for collection in "${collections[@]}"; do
        if [[ ! -f "$backup_path/$MONGO_DB/$collection.bson.gz" ]]; then
            missing_collections+=("$collection")
        fi
    done
    
    if [[ ${#missing_collections[@]} -gt 0 ]]; then
        warn "Missing backup files for collections: ${missing_collections[*]}"
        return 1
    fi
    
    # Check backup file sizes
    local total_size
    total_size=$(du -sh "$backup_path" | cut -f1)
    log "Backup size: $total_size"
    
    # Check if backup is encrypted
    if [[ -f "$backup_path.tar.gz.enc" ]]; then
        log "✅ Backup is encrypted"
    else
        log "⚠️ Backup is not encrypted"
    fi
    
    log "✅ Backup integrity verified"
    return 0
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log "No backup directory found - skipping cleanup"
        return 0
    fi
    
    # Find backups older than retention period
    local cutoff_date
    cutoff_date=$(date -d "$BACKUP_RETENTION_DAYS days ago" +%Y%m%d)
    
    local cleaned_count=0
    
    # Remove old backup directories
    for backup_dir in "$BACKUP_DIR"/*; do
        if [[ -d "$backup_dir" ]]; then
            local backup_date
            backup_date=$(basename "$backup_dir" | cut -d'_' -f1)
            
            if [[ "$backup_date" < "$cutoff_date" ]]; then
                log "Removing old backup: $(basename "$backup_dir")"
                rm -rf "$backup_dir"
                ((cleaned_count++))
            fi
        fi
    done
    
    # Remove old encrypted backups
    for backup_file in "$BACKUP_DIR"/*.tar.gz.enc; do
        if [[ -f "$backup_file" ]]; then
            local backup_date
            backup_date=$(basename "$backup_file" | cut -d'_' -f1)
            
            if [[ "$backup_date" < "$cutoff_date" ]]; then
                log "Removing old encrypted backup: $(basename "$backup_file")"
                rm -f "$backup_file"
                ((cleaned_count++))
            fi
        fi
    done
    
    log "✅ Cleaned up $cleaned_count old backups"
}

# Create backup report
create_backup_report() {
    local backup_path="$1"
    
    log "Creating backup report..."
    
    local report_file="$BACKUP_DIR/backup-report.txt"
    
    cat > "$report_file" << EOF
Lucid RDP Session Data Backup Report
====================================
Backup Date: $(date)
Backup Path: $backup_path
Source: $MONGO_HOST:$MONGO_PORT/$MONGO_DB

Collections Backed Up:
- sessions: Session metadata and manifests
- chunks: Encrypted session chunks
- authentication: User authentication data
- work_proofs: PoOT consensus proofs
- encryption_keys: Session encryption keys

Backup Status: SUCCESS
Encryption: $([ -n "$ENCRYPTION_KEY" ] && echo "ENABLED" || echo "DISABLED")
Retention: $BACKUP_RETENTION_DAYS days

Backup Size: $(du -sh "$backup_path" 2>/dev/null | cut -f1 || echo "Unknown")

Verification: PASSED
EOF
    
    log "Backup report created: $report_file"
}

# Create restore script
create_restore_script() {
    log "Creating restore script..."
    
    local restore_script="$BACKUP_DIR/restore-sessions.sh"
    
    cat > "$restore_script" << 'EOF'
#!/bin/bash
# Session Data Restore Script
# LUCID-STRICT: Restore session data from backup

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Configuration
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lucid}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-}"

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
die() { printf '[%s][ERROR] %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }

# Restore from backup
restore_backup() {
    local backup_path="$1"
    
    log "Restoring session data from: $backup_path"
    
    # Check if backup is encrypted
    if [[ -f "$backup_path.tar.gz.enc" ]]; then
        if [[ -z "$ENCRYPTION_KEY" ]]; then
            die "Encrypted backup requires ENCRYPTION_KEY"
        fi
        
        log "Decrypting backup..."
        local temp_dir=$(mktemp -d)
        
        if openssl enc -d -aes-256-cbc -salt -pbkdf2 \
            -pass "pass:$ENCRYPTION_KEY" -in "$backup_path.tar.gz.enc" | \
            tar -xzf - -C "$temp_dir"; then
            backup_path="$temp_dir"
            log "Backup decrypted successfully"
        else
            die "Failed to decrypt backup"
        fi
    fi
    
    # Restore collections
    local collections=("sessions" "chunks" "authentication" "work_proofs" "encryption_keys")
    
    for collection in "${collections[@]}"; do
        if [[ -f "$backup_path/$MONGO_DB/$collection.bson.gz" ]]; then
            log "Restoring $collection collection..."
            if mongorestore --host "$MONGO_HOST" --port "$MONGO_PORT" \
                --db "$MONGO_DB" --collection "$collection" \
                --gzip "$backup_path/$MONGO_DB/$collection.bson.gz"; then
                log "✅ $collection collection restored"
            else
                warn "Failed to restore $collection collection"
            fi
        else
            warn "Backup file not found for $collection collection"
        fi
    done
    
    log "✅ Session data restore completed"
}

# Main function
main() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: $0 <backup_path>"
        echo "Example: $0 /path/to/backup/20240101_120000"
        exit 1
    fi
    
    restore_backup "$1"
}

main "$@"
EOF
    
    chmod +x "$restore_script"
    log "Restore script created: $restore_script"
}

# Main execution
main() {
    log "Starting session data backup..."
    log "Source: $MONGO_HOST:$MONGO_PORT/$MONGO_DB"
    log "Destination: $BACKUP_DIR"
    log "Encryption: $([ -n "$ENCRYPTION_KEY" ] && echo "ENABLED" || echo "DISABLED")"
    
    # Check prerequisites
    check_prerequisites
    
    # Create backup directory
    local backup_path
    backup_path=$(create_backup_directory)
    
    # Backup collections
    backup_sessions "$backup_path"
    backup_chunks "$backup_path"
    backup_authentication "$backup_path"
    backup_work_proofs "$backup_path"
    backup_encryption_keys "$backup_path"
    
    # Encrypt backup if key provided
    encrypt_backup "$backup_path"
    
    # Create manifest and verify
    create_backup_manifest "$backup_path"
    verify_backup_integrity "$backup_path"
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Create reports and scripts
    create_backup_report "$backup_path"
    create_restore_script
    
    log "✅ Session data backup completed successfully"
    log "Backup location: $backup_path"
    log "Restore script: $BACKUP_DIR/restore-sessions.sh"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
